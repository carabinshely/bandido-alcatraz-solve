"""Core20 plus fixed A21-A23 AST cases; no scientific source import/execution."""
import ast
from contextlib import contextmanager
import copy
import hashlib
import json
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

if __name__=='__main__':
    unittest.main()
