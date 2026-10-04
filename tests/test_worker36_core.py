"""Core20 plus fixed A21-A23 AST cases; no scientific source import/execution."""
import ast
from contextlib import contextmanager
import copy
import hashlib
import json
import os
from pathlib import Path
from random import Random
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from worker36 import common as c
from worker36 import sources as s
from worker36.cell import equality
from worker36.driver import read_admission
from worker36.verify import normalized_journal

STUB_CALLS = 0

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.budget = c.Budget(self.root); self.captures = {}
    def tearDown(self):
        self.tmp.cleanup()
    def delegate(self, method, scope='candidate', condition='U', budget=None):
        return c.TimingDelegate(method, scope=scope, condition=condition, budget=budget or self.budget,
            folder=self.root, cell={'cell': 'fault-stub', 'condition': condition},
            observation_wire=lambda o: o, move_wire=lambda x: x, captures=self.captures,
            guard_path=self.root / 'active-call.json', verify_sources=lambda: None)
    def stub(self, value=None, fail=False):
        def method(observation, rng, *, limits):
            global STUB_CALLS
            STUB_CALLS += 1
            if fail: raise ValueError('fixed stub failure')
            return value
        return method
    def test_01_schedule_exact_20(self):
        self.assertEqual(len(c.SCHEDULE), 20)
        self.assertEqual([(x['size'], x['condition']) for x in c.SCHEDULE[:10]],
                         [(n, v) for n in (0,4,8,40,48) for v in ('P','U')])
        self.assertEqual([(x['size'], x['condition']) for x in c.SCHEDULE[10:]],
                         [(n, v) for n in (48,40,8,4,0) for v in ('U','P')])
    def test_02_constants_exact(self):
        self.assertEqual(c.OP_CAPS, {'legal_enumerations':32768,'previews':32768,'exit_geometry_checks':16384})
        self.assertEqual(c.CALL_CAPS['roots'], 16384)
        self.assertEqual([c.RESOURCES[x] for x in ('whole_cell_wall_seconds','measurement_wall_seconds','verification_wall_seconds')], [720,1800,600])
        self.assertEqual(c.RESOURCES['address_space_bytes'], 512*1024**2)
    def test_03_json_rejects(self):
        for data in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":1e999}'):
            with self.assertRaises(c.IntegrityError):c.strict_json(data)
    def test_04_raw_blob_newline(self):
        raw=b'fixed stub\n'; entry={'path':'stub.py','size_bytes':len(raw),'sha256':c.sha(raw),
            'git_blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}
        s.verify_blob(raw,entry)
        with self.assertRaises(c.IntegrityError):s.verify_blob(raw+b'\n',entry)
    def test_05_static_closure_complete(self):
        manifest=s.read_manifest(ROOT/'experiments/synthetic-profile-overhead/source-manifest.json')
        names={e['module'] for e in manifest['files']}
        self.assertEqual(len(names),21)
        self.assertTrue(all(set(e['imports'])<=names for e in manifest['files']))
        self.assertTrue(set(manifest['roots'])<=names)
        self.assertTrue(all(e['path'].endswith('.py') for e in manifest['files']))
    def test_06_constructor_ast_exact(self):
        source=(ROOT/'tests/worker36_constructor_source.txt').read_bytes()
        manifest=s.read_manifest(ROOT/'experiments/synthetic-profile-overhead/source-manifest.json')
        s.verify_blob(source,next(e for e in manifest['files'] if e['module']=='benchmark_worker35_synthetic'))
        self.assertEqual(len(s.verify_constructor(source,manifest['constructor'])),19)
        self.assertEqual(len(s.fixture_ast(source)),19)
    def test_07_exclusive_writes(self):
        p=self.root/'exclusive.json';self.budget.write(p,{'a':1})
        with self.assertRaises(FileExistsError):self.budget.write(p,{'a':2})
        self.assertEqual(c.strict_json(p.read_bytes()),{'a':1})
    def test_08_durable_capture_tuple_identity(self):
        result=(None,{'roots':[]},{'unmeasured_internal_stub':0})
        returned=self.delegate(self.stub(result)).evaluate({'fault':1},Random(7),limits=None)
        self.assertIs(returned,result)
        self.assertTrue(self.captures['candidate']['durable_capture_confirmed'])
        payload=c.strict_json((self.root/'candidate-return.json').read_bytes())
        self.assertEqual(payload['physical_cost'],None)
        self.assertEqual(c.file_info(self.root/'candidate-return.json')['sha256'],
                         c.strict_json((self.root/'candidate-capture-confirmed.json').read_bytes())['sha256'])
        # Reference starts only after all candidate bytes and marker exist.
        self.delegate(self.stub(result),scope='reference').evaluate({'fault':1},Random(7),limits=None)
    def test_09_capture_failure_stops_reference(self):
        result=(None,{'roots':[]},{})
        original=self.budget.write
        def fail_capture(path,value,**kwargs):
            if Path(path).name=='candidate-return.json':raise OSError('fixed write fault')
            return original(path,value,**kwargs)
        with patch.object(self.budget,'write',side_effect=fail_capture):
            with self.assertRaises(OSError):self.delegate(self.stub(result)).evaluate({'fault':1},Random(7),limits=None)
        self.assertTrue(self.captures['candidate']['returned'])
        self.assertFalse(self.captures['candidate']['durable_capture_confirmed'])
        with self.assertRaises(c.IntegrityError):
            self.delegate(self.stub(result),scope='reference').evaluate({'fault':1},Random(7),limits=None)
    def test_10_method_failure_no_success(self):
        with self.assertRaises(ValueError):self.delegate(self.stub(fail=True)).evaluate({},Random(7),limits=None)
        self.assertFalse(self.captures['candidate']['returned'])
        self.assertFalse((self.root/'candidate-return.json').exists())
    def test_11_shim_restores_success(self):
        setter=sys.setprofile
        with c.suppress_profile() as getter:
            sys.setprofile(lambda *args:None)
            self.assertIsNone(getter())
        self.assertIs(sys.setprofile,setter);self.assertIsNone(sys.getprofile())
    def test_12_shim_restores_exception(self):
        setter=sys.setprofile
        with self.assertRaises(ValueError):
            with c.suppress_profile():raise ValueError('fixed fault')
        self.assertIs(sys.setprofile,setter);self.assertIsNone(sys.getprofile())
    def test_13_occupied_hooks_threads(self):
        for target, value in (('sys.getprofile',object()),('sys.gettrace',object()),('threading.active_count',2)):
            with patch(target,return_value=value):
                with self.assertRaises(c.IntegrityError):c.idle_hooks()
    def test_14_U_flags_exact(self):
        self.assertEqual(c.U_FLAGS,{'physical_cost':None,'physical_operation_caps_enforced':False,
                                   'choice_events_observed':False,'production_admissible':False})
    def test_15_corrupt_receipt_preserved(self):
        p=self.root/'receipt.json';p.write_bytes(b'broken original')
        with self.assertRaises(c.IntegrityError):c.update_receipt(self.root,status='success')
        self.assertEqual(p.read_bytes(),b'broken original')
        self.assertEqual(len(list(self.root.glob('failure-receipt-*.json'))),1)
    def test_16_budget_no_truncation(self):
        p=self.root/'payload';p.write_bytes(b'prefix')
        with self.assertRaises(c.ResourceExceeded):self.budget.check(p,8*c.MIB+1)
        self.assertEqual(p.read_bytes(),b'prefix')
    def test_17_missing_admission_blocked(self):
        p=self.root/'go.json';p.write_bytes(c.canonical({'admitted':False}))
        with self.assertRaises(c.IntegrityError):read_admission(p,c.sha(p.read_bytes()),ROOT)
    def test_18_wrong_runtime_runner(self):
        with patch('platform.python_version',return_value='0.0.0'):
            with self.assertRaises(c.IntegrityError):c.runtime_check()
        with patch('platform.python_version',return_value='3.11.16'),patch.object(c,'file_info',return_value={'sha256':c.RUNTIME['executable_sha256']}),patch.dict('os.environ',{'GITHUB_ACTIONS':'false'}):
            with self.assertRaises(c.IntegrityError):c.runtime_check()
    def test_19_complete_science_rng_equality(self):
        # Fixed literal fault objects, not generated/fuzzed scientific outcomes.
        first={'chosen':None,'scientific':{'fixed':'stub'},'rng_initial':[1],'rng_final':[2]}
        equality(first,dict(first))
        for key in first:
            other=dict(first);other[key]='different'
            with self.assertRaises(c.IntegrityError):equality(first,other)
    def test_20_journal_only_directory_map(self):
        p=self.root/'journal';p.write_bytes((str(self.root)+' {"timing":7,"untouched":"a"}\n').encode())
        self.assertEqual(normalized_journal(p,self.root),b'<CELL> {"timing":7,"untouched":"a"}\n')


    def versioned_ast_form(self, node, *, type_params):
        # Explicit inert representations of the 3.11 and 3.12 field layouts;
        # no constructor compilation or code execution is involved.
        result = copy.deepcopy(node)
        for child in ast.walk(result):
            if isinstance(child, ast.FunctionDef):
                child._fields = s.CONSTRUCTOR_AST_FIELDS['FunctionDef']
                if type_params:
                    child._fields += ('type_params',)
                    child.type_params = []
                elif hasattr(child, 'type_params'):
                    del child.type_params
        return result

    def test_21_ast_canonical_fixed_version_forms(self):
        node = ast.parse('def literal(value):\n    return value + 1\n').body[0]
        first = self.versioned_ast_form(node, type_params=False)
        second = self.versioned_ast_form(node, type_params=True)
        before = (ast.dump(first, include_attributes=True), ast.dump(second, include_attributes=True))
        first_bytes = s.constructor_ast_bytes(first)
        second_bytes = s.constructor_ast_bytes(second)
        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(c.strict_json(first_bytes)['schema'], s.CONSTRUCTOR_AST_SCHEMA)
        self.assertEqual(before, (ast.dump(first, include_attributes=True), ast.dump(second, include_attributes=True)))
        changed = copy.deepcopy(second)
        changed.body[0].value.right.value = 2
        self.assertNotEqual(c.sha(second_bytes), c.sha(s.constructor_ast_bytes(changed)))

    def test_22_ast_canonical_rejects_semantic_extensions(self):
        literal = ast.parse('def literal(value):\n    return value + 1\n').body[0]
        type_parameters = self.versioned_ast_form(literal, type_params=True)
        type_parameters.type_params = [ast.Name(id='T', ctx=ast.Load())]
        declared_field = self.versioned_ast_form(literal, type_params=False)
        declared_field._fields += ('future_semantic_field',)
        declared_field.future_semantic_field = None
        instance_field = self.versioned_ast_form(literal, type_params=False)
        instance_field.future_semantic_field = 'fixed'
        for name, node in (('nonempty_type_params', type_parameters),
                           ('declared_field', declared_field), ('instance_field', instance_field),
                           ('unknown_node', ast.Pass())):
            with self.subTest(variant=name):
                with self.assertRaises(c.IntegrityError):
                    s.constructor_ast_bytes(node)

    def test_23_constructor_pins_fixed_version_forms(self):
        source = (ROOT/'tests/worker36_constructor_source.txt').read_bytes()
        manifest = s.read_manifest(ROOT/'experiments/synthetic-profile-overhead/source-manifest.json')
        expected = manifest['constructor']
        entry = next(item for item in manifest['files'] if item['module'] == 'benchmark_worker35_synthetic')
        self.assertEqual(entry['git_blob'], 'c552da477744f0f0984204bb3078331ab48cfb54')
        self.assertEqual(entry['sha256'], 'eae10578a56b0a94857b9d9b6132ce6d0772706e57c1f11df1573cd0112fa6cf')
        self.assertEqual(entry['size_bytes'], 8645)
        s.verify_blob(source, entry)
        nodes = s.fixture_ast(source)
        self.assertEqual(len(nodes), 19)
        for type_params in (False, True):
            with self.subTest(version='3.12' if type_params else '3.11'):
                represented = [self.versioned_ast_form(node, type_params=type_params) for node in nodes]
                with patch.object(s, 'fixture_ast', return_value=represented):
                    self.assertEqual(s.verify_constructor(source, expected), expected['selected_nodes'])
        for name in ('schema', 'ast_hash', 'raw_span_hash'):
            altered = copy.deepcopy(expected)
            if name == 'schema':
                altered['ast_canonical_schema'] = 'unrecognized-literal-schema'
            elif name == 'ast_hash':
                altered['selected_nodes'][0]['ast_sha256'] = '0'*64
            else:
                altered['selected_nodes'][0]['raw_span_sha256'] = '1'*64
            with self.subTest(variant=name):
                with self.assertRaises(c.IntegrityError):
                    s.verify_constructor(source, altered)

    @contextmanager
    def literal_loader(self):
        # Entirely invented file bytes and proc-map text. No child process,
        # platform interpreter, historical source or evaluator is executed.
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary).resolve() / 'toolcache'
            executable = cache / 'Python/3.11.16/x64/bin/python3.11'
            library = cache / 'Python/3.11.16/x64/lib/libpython3.11.so.1.0'
            executable.parent.mkdir(parents=True)
            library.parent.mkdir()
            executable.write_bytes(b'literal executable bytes\n')
            library.write_bytes(b'literal library bytes\n')
            status = library.stat()
            device = {'major': os.major(status.st_dev), 'minor': os.minor(status.st_dev)}
            devtext = '%x:%x' % (device['major'], device['minor'])
            maps = ('1000-2000 r--p 00000000 %s %s %s\n'
                    '2000-3000 r-xp 00001000 %s %s %s\n') % (
                        devtext, status.st_ino, library, devtext, status.st_ino, library)
            environment = {'RUNNER_TOOL_CACHE': str(cache), 'LD_LIBRARY_PATH': str(library.parent),
                           'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1'}
            identity = {'schema': 'worker36-loader-identity-v1', 'tool_cache': str(cache),
                        'executable_path': str(executable),
                        'executable_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
                        'library_relative_path': 'Python/3.11.16/x64/lib/libpython3.11.so.1.0',
                        'library_path': str(library), 'library_directory': str(library.parent),
                        'library_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
                        'library_size_bytes': len(b'literal library bytes\n'),
                        'library_device': device, 'library_inode': status.st_ino,
                        'mapped_library': {'path': str(library), 'device': dict(device), 'inode': status.st_ino},
                        'loader_environment': {'LD_LIBRARY_PATH': str(library.parent)}}
            with patch.dict(c.RUNTIME, executable_sha256=identity['executable_sha256']), \
                 patch.object(c.sys, 'executable', str(executable)), \
                 patch.dict(os.environ, environment, clear=True), \
                 patch.object(c, '_loader_maps', return_value=maps):
                yield cache, executable, library, maps, identity

    def test_24_loader_identity_literal_files_and_maps(self):
        with self.literal_loader() as (_, _, _, _, expected):
            self.assertEqual(c.loader_identity(), expected)

    def test_25_loader_rejects_noncanonical_paths(self):
        for name in ('relative_cache', 'dotdot_cache', 'wrong_executable', 'symlink_library',
                     'symlink_directory', 'missing_library', 'directory_library'):
            with self.subTest(variant=name), self.literal_loader() as (cache, executable, library, _, _):
                if name == 'relative_cache':
                    os.environ['RUNNER_TOOL_CACHE'] = 'relative/cache'
                elif name == 'dotdot_cache':
                    os.environ['RUNNER_TOOL_CACHE'] = str(cache) + '/../toolcache'
                elif name == 'wrong_executable':
                    other = executable.with_name('other-python')
                    other.write_bytes(executable.read_bytes())
                    c.sys.executable = str(other)
                elif name == 'symlink_library':
                    target = library.with_name('target')
                    library.rename(target)
                    library.symlink_to(target)
                elif name == 'symlink_directory':
                    target = library.parent.with_name('other-lib')
                    library.parent.rename(target)
                    library.parent.symlink_to(target, target_is_directory=True)
                elif name == 'missing_library':
                    library.unlink()
                else:
                    library.unlink()
                    library.mkdir()
                with self.assertRaises((c.IntegrityError, OSError)):
                    c.loader_identity()

    def test_26_loader_file_identity_stays_stable(self):
        literal = self.root / 'literal-library'
        literal.write_bytes(b'fixed literal file')
        self.assertEqual(c._stable_loader_file(literal)['sha256'], hashlib.sha256(b'fixed literal file').hexdigest())
        for variant in ('same_size_change', 'path_replacement'):
            literal.write_bytes(b'fixed literal file')
            original = os.read
            changed = False
            def mutating_read(descriptor, size):
                nonlocal changed
                result = original(descriptor, size)
                if not changed:
                    changed = True
                    if variant == 'same_size_change':
                        literal.write_bytes(b'other literal file')
                    else:
                        replacement = literal.with_name('replacement')
                        replacement.write_bytes(b'fixed literal file')
                        os.replace(replacement, literal)
                return result
            with self.subTest(variant=variant), patch.object(c.os, 'read', side_effect=mutating_read):
                with self.assertRaises(c.IntegrityError):
                    c._stable_loader_file(literal)

    def test_27_loader_rejects_mapping_variants(self):
        with self.literal_loader() as (_, _, library, maps, identity):
            device = identity['library_device']
            devtext = '%x:%x' % (device['major'], device['minor'])
            inode = identity['library_inode']
            variants = (
                ('absent', '1000-2000 rw-p 00000000 00:00 0\n'),
                ('alias_path', maps.replace(str(library), str(library.parent / 'alias-libpython.so'))),
                ('deleted', maps.replace(str(library), str(library) + ' (deleted)')),
                ('wrong_device', maps.replace(' ' + devtext + ' ', ' ff:ff ')),
                ('wrong_inode', maps.replace(' %s ' % inode, ' %s ' % (inode + 1))),
                ('other_version', maps + '3000-4000 r-xp 00000000 00:01 987 /other/libpython3.12.so.1.0\n'),
                ('malformed', maps + 'not a proc map\n'),
                ('same_inode_alias', maps + '3000-4000 r-xp 00000000 %s %s /other/alias.so\n' % (devtext, inode)))
            for name, raw in variants:
                with self.subTest(variant=name), patch.object(c, '_loader_maps', return_value=raw):
                    with self.assertRaises(c.IntegrityError):
                        c.loader_identity()
            with self.subTest(variant='changed_mapping'), patch.object(c, '_loader_maps',
                    side_effect=(maps, maps.replace('2000-3000', '2000-4000'))):
                with self.assertRaises(c.IntegrityError):
                    c.loader_identity()

    def test_28_loader_rejects_ambient_loader_settings(self):
        for key, value in (('LD_PRELOAD', '/literal.so'), ('LD_AUDIT', '/literal.so'),
                           ('LD_DEBUG', 'libs'), ('LD_UNKNOWN', 'literal'),
                           ('LD_LIBRARY_PATH', None), ('LD_LIBRARY_PATH', '/one:/two'),
                           ('LD_LIBRARY_PATH', '/wrong/library')):
            with self.subTest(key=key, value=value), self.literal_loader():
                if value is None:
                    os.environ.pop(key)
                else:
                    os.environ[key] = value
                with self.assertRaises(c.IntegrityError):
                    c.loader_identity()

    def test_29_loader_portable_pin_exact_fields(self):
        with self.literal_loader() as (_, _, _, _, identity):
            expected = {'schema': 'worker36-loader-pin-v1',
                        'executable_sha256': identity['executable_sha256'],
                        'library_relative_path': identity['library_relative_path'],
                        'library_sha256': identity['library_sha256'],
                        'library_size_bytes': identity['library_size_bytes']}
            self.assertEqual(c.loader_pin(identity), expected)
            self.assertEqual(c.loader_pin(expected), expected)
            invalid = [dict(expected), {**expected, 'extra': 1}, {**expected, 'schema': 'other'},
                       {**expected, 'library_size_bytes': True}, {**expected, 'library_size_bytes': 0},
                       {**expected, 'library_size_bytes': -1}, {**expected, 'library_sha256': 'f' * 63},
                       {**expected, 'executable_sha256': '0' * 64},
                       {**expected, 'library_relative_path': '../libpython3.11.so.1.0'}]
            invalid[0].pop('library_sha256')
            for index, value in enumerate(invalid):
                with self.subTest(variant=index), self.assertRaises(c.IntegrityError):
                    c.loader_pin(value)

    def test_30_loader_full_identity_consistency(self):
        with self.literal_loader() as (_, _, _, _, identity):
            for variant in ('extra', 'missing', 'cache', 'executable', 'library', 'directory',
                            'mapped_path', 'device', 'inode', 'environment'):
                value = copy.deepcopy(identity)
                if variant == 'extra': value['extra'] = 1
                elif variant == 'missing': value.pop('mapped_library')
                elif variant == 'cache': value['tool_cache'] += '/..'
                elif variant == 'executable': value['executable_path'] += '-other'
                elif variant == 'library': value['library_path'] += '-other'
                elif variant == 'directory': value['library_directory'] += '-other'
                elif variant == 'mapped_path': value['mapped_library']['path'] += '-other'
                elif variant == 'device': value['mapped_library']['device']['minor'] += 1
                elif variant == 'inode': value['mapped_library']['inode'] += 1
                else: value['loader_environment']['LD_PRELOAD'] = '/literal.so'
                with self.subTest(variant=variant), self.assertRaises(c.IntegrityError):
                    c.loader_pin(value)

    def test_31_clean_environment_requires_verified_loader(self):
        with self.literal_loader() as (_, _, library, _, identity):
            dirty = {'KEEP': 'yes', 'LD_LIBRARY_PATH': '/wrong', 'LD_AUDIT': '/wrong',
                     'LD_UNKNOWN': 'yes', 'PYTHONPATH': '/wrong', 'PYTHONUNKNOWN': 'yes'}
            original = dict(dirty)
            clean = {'KEEP': 'yes', 'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1'}
            self.assertEqual(c.clean_environment(dirty), clean)
            expected = {**clean, 'LD_LIBRARY_PATH': str(library.parent)}
            self.assertEqual(c.clean_environment(dirty, loader=identity), expected)
            self.assertEqual(c.clean_environment(dirty, loader=c.loader_pin(identity)), expected)
            different = copy.deepcopy(identity)
            different['library_inode'] += 1
            different['mapped_library']['inode'] += 1
            different_pin = c.loader_pin(identity)
            different_pin['library_sha256'] = '0' * 64
            for variant in (different, different_pin, '/arbitrary/library'):
                with self.subTest(loader=variant), self.assertRaises(c.IntegrityError):
                    c.clean_environment(dirty, loader=variant)
            with patch.object(c, 'loader_identity', side_effect=c.IntegrityError('literal local verification failure')):
                with self.assertRaises(c.IntegrityError):
                    c.clean_environment(dirty, loader=identity)
            self.assertEqual(dirty, original)

    def test_32_runtime_binds_loader_identity(self):
        with self.literal_loader() as (_, executable, _, _, identity), \
             patch.object(c, 'idle_hooks'), \
             patch.object(c.platform, 'python_implementation', return_value='CPython'), \
             patch.object(c.platform, 'python_version', return_value='3.11.16'), \
             patch.object(c.sys, 'platform', 'linux'), \
             patch.object(c.sys, 'flags', types.SimpleNamespace(dont_write_bytecode=1,
                 no_user_site=1, ignore_environment=0, isolated=0, optimize=0, no_site=0)), \
             patch.object(c.gc, 'isenabled', return_value=True), \
             patch.object(c.gc, 'get_threshold', return_value=(700, 10, 10)), \
             patch.object(c.signal, 'getitimer', return_value=(0, 0)), \
             patch.object(c.resource, 'getrlimit', return_value=(512 * c.MIB, 512 * c.MIB)), \
             patch.dict(os.environ, {'GITHUB_ACTIONS': 'true', 'GITHUB_REPOSITORY': c.REPOSITORY,
                                     'RUNNER_NAME': 'bandido-alcatraz-ci'}), \
             patch.object(c, 'loader_identity', return_value=identity) as observe:
            actual = c.runtime_check(child=True)
            self.assertEqual(actual['loader'], identity)
            self.assertEqual(actual['executable'], str(executable))
            observe.side_effect = c.IntegrityError('fixed loader verification failure')
            with self.assertRaises(c.IntegrityError): c.runtime_check()
            observe.side_effect = None
            with patch.dict(os.environ, PYTHONUNEXPECTED='literal'):
                with self.assertRaises(c.IntegrityError): c.runtime_check()

    def test_33_loader_shell_static_contract(self):
        shell = (ROOT / 'scripts/worker36-loader.sh').read_text()
        for token in ('worker36_loader_setup()', 'WORKER36_PYTHON', 'WORKER36_LOADER_DIRECTORY',
                      'WORKER36_LOADER_LIBRARY', 'WORKER36_LOADER_SHA256', 'WORKER36_LOADER_SIZE_BYTES',
                      'RUNNER_TOOL_CACHE', 'Python/3.11.16/x64/bin/python3.11',
                      'Python/3.11.16/x64/lib/libpython3.11.so.1.0', c.RUNTIME['executable_sha256'],
                      '"$name" == LD* || "$name" == PYTHON*', '! -L "$library"',
                      '! -L "$directory"', '"$before" == "$after"', 'return 1',
                      'export LD_LIBRARY_PATH="$directory" PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1'):
            self.assertIn(token, shell)
        self.assertLess(shell.index('unset "$name"'), shell.index('readlink -f'))
        active = '\n'.join(line for line in shell.splitlines() if not line.lstrip().startswith('#'))
        for forbidden in ('python -', '"$executable" -', 'eval ', 'pip install', 'apt-get',
                          'sudo ', 'chmod ', 'GITHUB_TOKEN', 'LD_PRELOAD='):
            self.assertNotIn(forbidden, active)

if __name__=='__main__':
    unittest.main()
