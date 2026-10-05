"""Fixed C01-C20 plus recovery-R1 C21-C22; no historical imports or measurements."""
from contextlib import ExitStack, contextmanager
import copy
import os
from pathlib import Path
from random import Random
import stat
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from worker38 import common as c
from worker38 import cell as subject

STUB_CALLS = 0
PUBLIC = {'literal_stub': 'public', 'items': ['fixed']}
COST = {'legal_enumerations': 1, 'previews': 0, 'exit_geometry_checks': 0, 'roots': 0}
EXPECTED_CALLS = {1: 2, 2: 2, 3: 1, 4: 0, 5: 0, 6: 0, 7: 1,
                  8: 0, 9: 0, 10: 0, 11: 0, 12: 1, 13: 1, 14: 1, 15: 0, 16: 0, 17: 0, 18: 0, 19: 0, 20: 0,
                  21: 0, 22: 0}


class CellIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.events = []
        self.start_calls = STUB_CALLS
        self.method_error = None
        self.loader_pin = {'schema': 'worker38-loader-pin-v1',
            'executable_sha256': c.RUNTIME['executable_sha256'],
            'library_relative_path': 'Python/3.11.16/x64/lib/libpython3.11.so.1.0',
            'library_sha256': '4' * 64, 'library_size_bytes': 4096}
        cache = '/literal-runner/tool-cache'
        library = cache + '/' + self.loader_pin['library_relative_path']
        directory = library.rsplit('/', 1)[0]
        self.loader = {**self.loader_pin, 'schema': 'worker38-loader-identity-v1',
            'tool_cache': cache, 'executable_path': cache + '/Python/3.11.16/x64/bin/python3.11',
            'library_path': library, 'library_directory': directory,
            'library_device': {'major': 8, 'minor': 1}, 'library_inode': 101,
            'mapped_library': {'path': library, 'device': {'major': 8, 'minor': 1}, 'inode': 101},
            'loader_environment': {'LD_LIBRARY_PATH': directory}}
        self.runtime = {**c.RUNTIME, 'executable': '/literal/python',
                        'flags': ['/literal/python', '-B', '-s', 'literal-entry', '_cell'],
                        'effective_flags': {'dont_write_bytecode': 1, 'no_user_site': 1,
                            'ignore_environment': 0, 'isolated': 0, 'optimize': 0, 'no_site': 0},
                        'python_environment': {'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1'},
                        'gc_enabled': True, 'gc_threshold': [700, 10, 10],
                        'address_space': [512*c.MIB, 512*c.MIB], 'loader': self.loader}
        self.module_evidence = {'literal_stub': {'path': '/literal/stub.py',
                                'sha256': 'a'*64, 'git_blob': 'b'*40, 'size_bytes': 1}}

    def tearDown(self):
        case = int(self._testMethodName.split('_')[1][1:])
        self.assertEqual(STUB_CALLS - self.start_calls, EXPECTED_CALLS[case])
        self.tmp.cleanup()

    def prepare(self, index=2, name='attempt'):
        root = self.root / name
        folder = root / 'cells' / f'{index:02d}'
        folder.mkdir(parents=True)
        (root / 'receipt.json').write_bytes(c.canonical({'admission_verified': True,
            'status': 'measuring', 'current_cell': index, 'supervisor_pid': os.getppid(),
            'supervisor_start_ticks': 1001}))
        (root / 'external-admission.json').write_bytes(c.canonical(
            {'cell_preflight_modules': list(self.module_evidence), 'loader_pin': self.loader_pin}))
        return root, folder

    def literal_method(self, scope):
        def evaluate(observation, rng, *, limits):
            global STUB_CALLS
            STUB_CALLS += 1
            self.events.append(scope)
            if self.method_error is not None:
                raise self.method_error
            before = c.digest(observation)
            rng_hash = c.digest(rng.getstate())
            science = {'input_before': before, 'input_after': before,
                       'rng_before': rng_hash, 'rng_after': rng_hash,
                       'chosen': None, 'roots': [], 'literal_stub': 'science'}
            return None, science, dict(COST)
        return evaluate

    def modules(self):
        outer = self
        @contextmanager
        def protection(*args):
            yield
        class StubResourceExceeded(RuntimeError):
            pass
        class CandidateResourceExceeded(RuntimeError):
            pass
        class ReferenceResourceExceeded(RuntimeError):
            pass
        class Policy:
            def __init__(self, **inputs):
                self.evaluate = outer.literal_method('candidate')
        class Reference:
            def __init__(self, **inputs):
                self.evaluate = outer.literal_method('reference')
        class Limits:
            def __init__(self, **limits):
                self.values = limits
        harness = types.SimpleNamespace(FREEZE=None, BUDGET=None,
            state_witness=lambda state, catalog: ({'literal_engine': 'unchanged'},
                                                 {'inventory_count': 69, 'literal': 'witness'}),
            iter_jsonl=lambda path: (c.strict_json(line) for line in Path(path).read_bytes().splitlines()))
        class AuditPolicy:
            def __init__(self, policy, *, reference, catalog, output, pass_number, seed,
                         limits, candidate_limits, reference_limits, state_provider):
                self.policy, self.reference, self.output = policy, reference, output
                self.candidate_limits, self.reference_limits = candidate_limits, reference_limits
                outer.assertEqual((pass_number, seed), (2, 11))
                for directory in ('call-results', 'decision-traces'):
                    parent = output / directory / 'pass-2'
                    outer.assertTrue(parent.is_dir())
                    # Mirror the unchanged AuditPolicy constructor's exclusive
                    # journal creation, then let run_cell fsync the parents.
                    with (parent / '11.jsonl').open('x') as stream:
                        stream.flush()
                        os.fsync(stream.fileno())
            def choose(self, observation, rng):
                outer.events.append('audit_choose')
                detached = copy.deepcopy(observation)
                other_rng = Random(); other_rng.setstate(rng.getstate())
                outer.assertIsNot(other_rng, rng)
                first = self.policy.evaluate(observation, rng, limits=self.candidate_limits)
                harness.BUDGET.append(self.output / 'resource-metrics.jsonl',
                    {'scope': 'candidate', 'status': 'returned', 'cost': first[2]})
                second = self.reference.evaluate(detached, other_rng, limits=self.reference_limits)
                harness.BUDGET.append(self.output / 'resource-metrics.jsonl',
                    {'scope': 'reference', 'status': 'returned', 'cost': second[2]})
                harness.BUDGET.append(self.output / 'call-results' / 'pass-2' / '11.jsonl',
                                     {'literal_stub': 'call journal'})
                harness.BUDGET.append(self.output / 'decision-traces' / 'pass-2' / '11.jsonl',
                                     {'literal_stub': 'decision journal'})
                return first[0]
        harness.AuditPolicy = AuditPolicy
        def measure_wrapper(audited, state, limits, seconds):
            outer.events.append('wrapper_enter')
            outer.assertEqual(seconds, 720)
            audited.choose(copy.deepcopy(PUBLIC), Random(11))
            outer.events.append('wrapper_exit')
            return {'operations': {key: 2*COST[key] for key in c.OP_CAPS}}
        return {'worker35_resources': types.SimpleNamespace(deadline=protection,
                    cpu_deadline=protection, ResourceExceeded=StubResourceExceeded),
                'run_quota_reserve_closure_development': harness,
                'benchmark_worker35_synthetic': types.SimpleNamespace(measure_wrapper=measure_wrapper),
                'bandido_alcatraz.quota_reserve_closure': types.SimpleNamespace(
                    QuotaReserveClosurePolicy=Policy, OperationLimits=Limits,
                    ResourceExceeded=CandidateResourceExceeded),
                'bandido_alcatraz.quota_reserve_closure_reference': types.SimpleNamespace(
                    QuotaReserveClosureReference=Reference, OperationLimits=Limits,
                    ResourceExceeded=ReferenceResourceExceeded),
                'bandido_alcatraz.worker32.evidence': types.SimpleNamespace(
                    observation=lambda value: copy.deepcopy(value), move=lambda value: value)}

    @contextmanager
    def injected(self, **overrides):
        replacements = {'_admitted_attempt_path': lambda attempt: Path(attempt).resolve(),
                        'process_identity': lambda pid: (pid, 1001),
                        'runtime_check': lambda **kwargs: copy.deepcopy(self.runtime),
                        'read_manifest': lambda path: {'files': []},
                        'verify_files': lambda *args: None,
                        'isolated_imports': lambda *args: self.modules(),
                        'verify_modules': lambda *args: copy.deepcopy(self.module_evidence),
                        'construct_fixture': lambda *args: ({'literal_stub': 'state'}, {}, {}, copy.deepcopy(PUBLIC))}
        replacements.update(overrides)
        with ExitStack() as stack:
            for name, replacement in replacements.items():
                stack.enter_context(patch.object(subject, name, side_effect=replacement))
            yield

    def read(self, path):
        return c.strict_json(Path(path).read_bytes())

    def test_C01_U_direct_cell(self):
        root, folder = self.prepare()
        setter = sys.setprofile
        with self.injected():
            result = subject.run_cell(root, 2)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(self.events, ['candidate', 'reference'])
        for key in ('actual_starts', 'actual_starts_upper_bound', 'actual_returns',
                    'confirmed_captures', 'pre_call_markers', 'invocation_attempts'):
            self.assertEqual(result[key], 2)
        self.assertIs(sys.setprofile, setter)
        self.assertIsNone(sys.getprofile())
        self.assertEqual(self.read(folder/'unmeasured-accounting.json'), c.U_FLAGS)
        self.assertEqual(self.read(folder/'source-runtime-preflight.json'),
                         {'phase': 'source_runtime_preflight', 'evaluator_starts': 0,
                          'runtime': self.runtime, 'modules': self.module_evidence})
        for scope in ('candidate', 'reference'):
            self.assertIsNone(self.read(folder/(scope+'-return.json'))['physical_cost'])
            self.assertTrue(result['calls'][scope]['method_entered'])
            self.assertEqual(self.read(folder/(scope+'-start.json'))['source_modules'], self.module_evidence)

    def test_C02_P_original_looking_wrapper(self):
        root, folder = self.prepare(index=1)
        with self.injected():
            result = subject.run_cell(root, 1)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(self.events, ['wrapper_enter', 'audit_choose', 'candidate', 'reference', 'wrapper_exit'])
        self.assertEqual(result['actual_starts'], 2)
        self.assertTrue((folder/'call-results/pass-2/11.jsonl').is_file())
        self.assertTrue((folder/'decision-traces/pass-2/11.jsonl').is_file())
        self.assertEqual(self.read(folder/'candidate-return.json')['physical_cost'], COST)

    def test_C03_capture_failure_prevents_reference(self):
        root, folder = self.prepare()
        original = c.Budget.write
        def writer(budget, path, value, **kwargs):
            if Path(path).name == 'candidate-return.json':
                raise PermissionError('literal capture write failure')
            return original(budget, path, value, **kwargs)
        with self.injected(), patch.object(c.Budget, 'write', new=writer):
            with self.assertRaises(PermissionError):
                subject.run_cell(root, 2)
        result = self.read(folder/'cell-receipt.json')
        self.assertEqual(result['status'], 'execution_incomplete')
        self.assertEqual((result['actual_starts'], result['actual_returns'], result['confirmed_captures']), (1,1,0))
        self.assertEqual(self.events, ['candidate'])
        self.assertFalse((folder/'reference-start.json').exists())

    def test_C04_atomic_first_and_later_marker(self):
        budget = c.Budget(self.root); target = self.root/'active-call.json'
        real_link, real_fsync = c.os.link, c.os.fsync
        fsynced = []
        def fsync(fd):
            fsynced.append(os.fstat(fd).st_ino)
            return real_fsync(fd)
        def link(temp, path):
            self.assertFalse(Path(path).exists())
            self.assertEqual(self.read(temp), {'active': True})
            self.assertIn(Path(temp).stat().st_ino, fsynced)
            return real_link(temp, path)
        with patch.object(c.os, 'fsync', side_effect=fsync), patch.object(c.os, 'link', side_effect=link):
            budget.write(target, {'active': True})
        self.assertFalse(target.with_name(target.name+'.tmp').exists())
        budget.write(target, {'active': False}, replace=True)
        self.assertEqual(self.read(target), {'active': False})
        # A crash between link and unlink may retain both complete filenames.
        # Reserve both path sizes before the first write, including terminal files.
        for terminal in (False, True):
            root = self.root / ('terminal-cap' if terminal else 'ordinary-cap')
            root.mkdir()
            name = 'failure-receipt-bound.json' if terminal else 'active-call.json'
            value = {'fixed': 'boundary'}
            size = len(c.canonical(value))
            cap = c.MIB if terminal else 63*c.MIB
            filler = {'path': 'failure-receipt-old.json' if terminal else 'ordinary-prefix',
                      'size_bytes': cap-size, 'sha256': 'd'*64}
            bounded = c.Budget(root)
            with patch.object(bounded, 'inventory', return_value=[filler]):
                with self.assertRaises(c.ResourceExceeded):
                    bounded.write(root/name, value)
            self.assertFalse((root/name).exists())
            self.assertFalse((root/(name+'.tmp')).exists())

    def test_C05_failed_publication_preserves_prefix(self):
        real_fsync = c.os.fsync
        for name in ('file_fsync', 'link', 'no_clobber'):
            folder = self.root/name; folder.mkdir()
            target = folder/'active-call.json'; budget = c.Budget(folder)
            if name == 'no_clobber':
                target.write_bytes(b'original')
                with self.assertRaises(FileExistsError):
                    budget.write(target, {'active': True})
                self.assertEqual(target.read_bytes(), b'original')
            elif name == 'link':
                with patch.object(c.os, 'link', side_effect=PermissionError('literal link failure')):
                    with self.assertRaises(PermissionError):
                        budget.write(target, {'active': True})
                self.assertFalse(target.exists())
            else:
                def fsync(fd):
                    if stat.S_ISREG(os.fstat(fd).st_mode):
                        raise OSError('literal file fsync failure')
                    return real_fsync(fd)
                with patch.object(c.os, 'fsync', side_effect=fsync):
                    with self.assertRaises(OSError):
                        budget.write(target, {'active': True})
                self.assertFalse(target.exists())
            self.assertEqual(self.read(target.with_name(target.name+'.tmp')), {'active': True})

    def test_C06_nested_directory_fsync(self):
        real = c.fsync_directory
        for method in ('write', 'append'):
            events = []
            def fsync(path):
                events.append(Path(path))
                return real(path)
            parent = self.root/method
            with patch.object(c, 'fsync_directory', side_effect=fsync):
                getattr(c.Budget(self.root), method)(parent/'nested'/'record.json', {'fixed': True})
            self.assertEqual(events[:4], [parent, self.root, parent/'nested', parent])

    def receipt_failure(self, root, folder, *, sidecar_fails=False):
        primary = c.IntegrityError('literal primary integrity failure')
        self.method_error = primary
        original_write, original_inventory, original_fsync = c.Budget.write, c.Budget.inventory, c.os.fsync
        full = False
        def writer(budget, path, value, **kwargs):
            nonlocal full
            if Path(path).name == 'cell-receipt.json':
                full = True
                raise c.ResourceExceeded('literal ordinary evidence cap full')
            return original_write(budget, path, value, **kwargs)
        def inventory(budget):
            entries = original_inventory(budget)
            if full:
                ordinary = sum(item['size_bytes'] for item in entries if '/' in item['path'] or
                               not (item['path'] == 'receipt.json' or item['path'].startswith('failure-receipt-')))
                entries.append({'path': 'literal-full-budget', 'size_bytes': 63*c.MIB-ordinary, 'sha256': 'c'*64})
            return entries
        def fsync(fd):
            if sidecar_fails and full and stat.S_ISREG(os.fstat(fd).st_mode):
                raise PermissionError('literal reserved sidecar fsync failure')
            return original_fsync(fd)
        with self.injected(), patch.object(c.Budget, 'write', new=writer), \
                patch.object(c.Budget, 'inventory', new=inventory), patch.object(c.os, 'fsync', side_effect=fsync):
            with self.assertRaises(c.IntegrityError) as caught:
                subject.run_cell(root, 2)
        self.assertIs(caught.exception, primary)
        self.assertEqual(primary.worker38_failure['status'], 'integrity_invalid')
        return primary

    def test_C07_integrity_survives_receipt_failure(self):
        root, folder = self.prepare()
        self.receipt_failure(root, folder)
        sidecar = self.read(root/'failure-receipt-cell-02.json')
        self.assertEqual(sidecar['status'], 'integrity_invalid')
        self.assertEqual(sidecar['failure']['error'], 'literal primary integrity failure')
        self.assertEqual(sidecar['secondary_errors'][0]['status'], 'resource_incomplete')
        self.assertFalse(sidecar['receipt_write_confirmed'])
        self.assertLess((root/'failure-receipt-cell-02.json').stat().st_size, 64*1024)

    def test_C08_typed_error_categories(self):
        for error in (PermissionError('fixed'), FileNotFoundError('fixed'), BrokenPipeError('fixed')):
            detail = c.error_record(error, 'cell_measurement')
            self.assertEqual((detail['status'], detail['category']), ('execution_incomplete', 'infrastructure'))
        for error in (c.ResourceExceeded('fixed'), MemoryError('fixed')):
            self.assertEqual(c.error_record(error, 'cell_measurement')['status'], 'resource_incomplete')
        self.assertEqual(c.error_record(c.IntegrityError('fixed'), 'cell_measurement')['status'], 'integrity_invalid')
        modules = self.modules()
        resource_types = tuple(modules[name].ResourceExceeded for name in (
            'worker35_resources', 'bandido_alcatraz.quota_reserve_closure',
            'bandido_alcatraz.quota_reserve_closure_reference'))
        self.assertEqual(len(set(resource_types)), 3)
        for resource_type in resource_types:
            detail = c.error_record(resource_type('fixed'), 'cell_measurement', resource_types=resource_types)
            self.assertEqual((detail['status'], detail['category']), ('resource_incomplete', 'resource'))

    def test_C09_initial_runtime_import_blocked(self):
        for name, target, error in (('runtime', 'runtime_check', c.IntegrityError('wrong pinned interpreter')),
                                    ('imports', 'isolated_imports', ImportError('literal missing module'))):
            root, folder = self.prepare(name=name)
            def fail(*args, **kwargs):
                raise error
            with self.injected(**{target: fail}):
                with self.assertRaises(type(error)) as caught:
                    subject.run_cell(root, 2)
            result = self.read(folder/'cell-receipt.json')
            self.assertEqual(result['status'], 'execution_blocked')
            self.assertEqual((result['actual_starts'], result['actual_starts_upper_bound']), (0,0))
            self.assertEqual(caught.exception.worker38_failure['status'], 'execution_blocked')

    def test_C10_later_source_drift_integrity(self):
        root, folder = self.prepare()
        calls = 0
        def verify(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise c.IntegrityError('literal source drift after preflight')
        with self.injected(verify_files=verify):
            with self.assertRaises(c.IntegrityError):
                subject.run_cell(root, 2)
        result = self.read(folder/'cell-receipt.json')
        self.assertEqual(result['status'], 'integrity_invalid')
        self.assertEqual(result['failure']['phase'], 'evaluator_source_check')
        self.assertEqual((result['actual_starts'], result['actual_starts_upper_bound']), (0,0))

    def test_C11_marker_failure_no_method_entry(self):
        root, folder = self.prepare()
        original = c.Budget.write
        def writer(budget, path, value, **kwargs):
            if Path(path).name == 'candidate-start.json':
                raise PermissionError('literal marker write failure')
            return original(budget, path, value, **kwargs)
        with self.injected(), patch.object(c.Budget, 'write', new=writer):
            with self.assertRaises(PermissionError):
                subject.run_cell(root, 2)
        result = self.read(folder/'cell-receipt.json')
        self.assertEqual((result['actual_starts'], result['actual_starts_upper_bound']), (0,0))
        self.assertFalse(result['calls']['candidate']['start_marker_durable'])
        self.assertFalse(result['calls']['candidate']['invocation_attempted'])
        self.assertTrue(self.read(folder/'active-call.json')['active'])

    def test_C12_method_exception_proves_entry(self):
        root, folder = self.prepare()
        self.method_error = ValueError('literal method exception')
        with self.injected():
            with self.assertRaises(ValueError):
                subject.run_cell(root, 2)
        result = self.read(folder/'cell-receipt.json')
        self.assertEqual((result['actual_starts'], result['actual_starts_upper_bound'], result['actual_returns']), (1,1,0))
        call = result['calls']['candidate']
        self.assertTrue(call['start_marker_durable'] and call['invocation_attempted'] and call['method_entered'])
        self.assertFalse(call['returned'])

    def test_C13_return_known_after_clock_failure(self):
        root, folder = self.prepare()
        original = c.time.monotonic
        calls = 0
        def clock():
            nonlocal calls
            calls += 1
            if calls == 3:  # guard, wall-before, then wall-after
                raise OSError('literal post-return clock failure')
            return original()
        with self.injected(), patch.object(c.time, 'monotonic', side_effect=clock):
            with self.assertRaises(OSError):
                subject.run_cell(root, 2)
        result = self.read(folder/'cell-receipt.json')
        self.assertEqual((result['actual_starts'], result['actual_returns'], result['confirmed_captures']), (1,1,0))
        self.assertFalse((folder/'candidate-return.json').exists())

    def test_C14_sidecar_failure_keeps_primary(self):
        root, folder = self.prepare()
        self.receipt_failure(root, folder, sidecar_fails=True)
        self.assertFalse((root/'failure-receipt-cell-02.json').exists())
        temporary = root/'failure-receipt-cell-02.json.tmp'
        self.assertEqual(self.read(temporary)['status'], 'integrity_invalid')
        self.assertLess(temporary.stat().st_size, 64*1024)


    def test_C15_occupied_countdown_stays_preflight_blocked(self):
        for timer_name in ('ITIMER_REAL', 'ITIMER_PROF'):
            with self.subTest(timer=timer_name):
                root, folder = self.prepare(name=timer_name)
                timer = getattr(subject.signal, timer_name)
                remaining = iter(((9.0, 0.0), (8.0, 0.0), (7.0, 0.0)))
                primary = c.IntegrityError('occupied wall/CPU timers')
                def countdown(which):
                    return next(remaining) if which == timer else (0.0, 0.0)
                def reject_occupied_timer(**kwargs):
                    self.assertTrue(kwargs['child'])
                    if subject.signal.getitimer(timer)[0]:
                        raise primary
                    self.fail('literal occupied prerequisite unexpectedly passed')
                with self.injected(runtime_check=reject_occupied_timer), \
                        patch.object(subject.signal, 'getitimer', side_effect=countdown) as get_timer, \
                        patch.object(subject.signal, 'getsignal') as get_handler, \
                        patch.object(subject, 'isolated_imports') as imports, \
                        patch.object(subject, 'construct_fixture') as fixture:
                    with self.assertRaises(c.IntegrityError) as caught:
                        subject.run_cell(root, 2)
                    get_timer.assert_called_once_with(timer)
                    get_handler.assert_not_called()
                    imports.assert_not_called()
                    fixture.assert_not_called()
                self.assertIs(caught.exception, primary)
                self.assertEqual(primary.worker38_failure['status'], 'execution_blocked')
                result = self.read(folder/'cell-receipt.json')
                self.assertEqual(result['status'], 'execution_blocked')
                self.assertEqual(result['phase'], 'cell_source_runtime_preflight')
                self.assertEqual(result['failure']['error'], 'occupied wall/CPU timers')
                self.assertEqual(result['secondary_errors'], [])
                self.assertIsNone(result['hook_restored'])
                self.assertIsNone(result['timer_restored'])
                for field in ('actual_starts', 'actual_starts_upper_bound', 'actual_returns',
                              'confirmed_captures', 'pre_call_markers', 'invocation_attempts'):
                    self.assertEqual(result[field], 0)
                self.assertEqual(result['calls'], {})
                self.assertEqual(self.events, [])


    def test_C16_receipt_resource_and_io_propagate(self):
        variants = (
            ('read_memory', 'read', MemoryError('literal receipt read exhaustion')),
            ('parse_memory', 'parse', MemoryError('literal parser allocation exhaustion')),
            ('parse_resource', 'parse', c.ResourceExceeded('literal parser resource cap')),
            ('parse_recursion', 'parse', RecursionError('literal parser recursion exhaustion')),
            ('read_permission', 'read', PermissionError('literal unreadable receipt')),
        )
        for name, stage, primary in variants:
            with self.subTest(variant=name):
                root = self.root/name; root.mkdir()
                path = root/'receipt.json'
                original = c.canonical({'status': 'measuring', 'literal': 'preserved'})
                path.write_bytes(original)
                target = patch.object(Path, 'read_bytes', side_effect=primary) if stage == 'read' else \
                         patch.object(c, 'strict_json', side_effect=primary)
                with target, patch.object(c, 'write_failure_receipt') as sidecar:
                    with self.assertRaises(type(primary)) as caught:
                        c.update_receipt(root, status='execution_incomplete')
                    sidecar.assert_not_called()
                self.assertIs(caught.exception, primary)
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(list(root.glob('failure-receipt-*')), [])
                expected = 'execution_incomplete' if isinstance(primary, OSError) else 'resource_incomplete'
                self.assertEqual(c.error_record(primary, 'receipt_update')['status'], expected)

    def test_C17_malformed_bytes_keep_integrity(self):
        for name, raw in (('syntax', b'{'), ('duplicate', b'{"status":1,"status":2}'),
                          ('encoding', b'\xff'), ('nonobject', b'[]')):
            with self.subTest(variant=name):
                root = self.root/name; root.mkdir()
                path = root/'receipt.json'; path.write_bytes(raw)
                with self.assertRaises(c.IntegrityError) as caught:
                    c.update_receipt(root, status='execution_incomplete')
                self.assertEqual(path.read_bytes(), raw)
                self.assertEqual(caught.exception.worker38_failure['status'], 'integrity_invalid')
                sidecars = list(root.glob('failure-receipt-*.json'))
                self.assertEqual(len(sidecars), 1)
                self.assertEqual(self.read(sidecars[0])['status'], 'integrity_invalid')
        for name, secondary in (('sidecar_memory', MemoryError('literal sidecar exhaustion')),
                                ('sidecar_io', PermissionError('literal sidecar denied'))):
            with self.subTest(variant=name):
                root = self.root/name; root.mkdir()
                path = root/'receipt.json'; path.write_bytes(b'{')
                with patch.object(c, 'write_failure_receipt', side_effect=secondary):
                    with self.assertRaises(c.IntegrityError) as caught:
                        c.update_receipt(root, status='resource_incomplete')
                self.assertEqual(path.read_bytes(), b'{')
                self.assertEqual(caught.exception.worker38_failure['status'], 'integrity_invalid')
                detail, = caught.exception.worker38_secondary_errors
                expected = 'resource_incomplete' if isinstance(secondary, MemoryError) else 'execution_incomplete'
                self.assertEqual(detail['status'], expected)
                self.assertEqual(detail['error_type'], type(secondary).__name__)

    def test_C18_resource_types_precede_preflight_block(self):
        modules = self.modules()
        resource_types = tuple(modules[name].ResourceExceeded for name in (
            'worker35_resources', 'bandido_alcatraz.quota_reserve_closure',
            'bandido_alcatraz.quota_reserve_closure_reference'))
        errors = (MemoryError('fixed'), c.ResourceExceeded('fixed'), RecursionError('fixed'),
                  resource_types[0]('fixed'), resource_types[1]('fixed'), resource_types[2]('fixed'))
        for phase in ('cell_source_runtime_preflight', 'cell_measurement'):
            for error in errors:
                with self.subTest(phase=phase, error_type=type(error).__name__):
                    detail = c.error_record(error, phase, resource_types=resource_types)
                    self.assertEqual((detail['status'], detail['category']), ('resource_incomplete', 'resource'))
        prerequisite = c.IntegrityError('wrong literal runtime/source prerequisite')
        self.assertEqual(c.error_record(prerequisite, 'cell_source_runtime_preflight')['status'], 'execution_blocked')
        self.assertEqual(c.error_record(prerequisite, 'cell_source_runtime_preflight',
                         observed_drift=True)['status'], 'integrity_invalid')

    def test_C19_preflight_memory_then_receipt_io(self):
        root, folder = self.prepare()
        primary = MemoryError('literal runtime allocation exhaustion')
        original = c.Budget.write
        def fail_runtime(**kwargs):
            raise primary
        def writer(budget, path, value, **kwargs):
            if Path(path).name == 'cell-receipt.json':
                raise PermissionError('literal receipt I/O failure after resource exhaustion')
            return original(budget, path, value, **kwargs)
        with self.injected(runtime_check=fail_runtime), patch.object(c.Budget, 'write', new=writer), \
                patch.object(subject, 'isolated_imports') as imports, \
                patch.object(subject, 'construct_fixture') as fixture:
            with self.assertRaises(MemoryError) as caught:
                subject.run_cell(root, 2)
            imports.assert_not_called()
            fixture.assert_not_called()
        self.assertIs(caught.exception, primary)
        self.assertEqual(primary.worker38_failure['status'], 'resource_incomplete')
        result = self.read(root/'failure-receipt-cell-02.json')
        self.assertEqual(result['status'], 'resource_incomplete')
        self.assertEqual(result['failure']['phase'], 'cell_source_runtime_preflight')
        self.assertEqual(result['secondary_errors'][0]['status'], 'execution_incomplete')
        self.assertEqual((result['actual_starts'], result['actual_starts_upper_bound'], result['actual_returns']), (0,0,0))

    def test_C20_cell_primary_failure_precedence(self):
        variants = (
            ('resource_then_io', MemoryError('literal source-check exhaustion'),
             PermissionError('literal later accounting I/O'), 'resource_incomplete', False),
            ('io_then_resource', PermissionError('literal source-check I/O'),
             MemoryError('literal later accounting exhaustion'), 'resource_incomplete', True),
            ('integrity_then_resource', c.IntegrityError('literal observed source drift'),
             MemoryError('literal later accounting exhaustion'), 'integrity_invalid', False),
        )
        for name, first, later, expected, promote in variants:
            with self.subTest(variant=name):
                root, folder = self.prepare(name=name)
                checks = 0
                def source_check(*args):
                    nonlocal checks
                    checks += 1
                    if checks == 2:
                        raise first
                with self.injected(verify_files=source_check), \
                        patch.object(subject.resource, 'getrusage', side_effect=later):
                    with self.assertRaises(type(later if promote else first)) as caught:
                        subject.run_cell(root, 2)
                self.assertIs(caught.exception, later if promote else first)
                result = self.read(folder/'cell-receipt.json')
                self.assertEqual(result['status'], expected)
                self.assertEqual(result['failure']['error_type'], type(later if promote else first).__name__)
                self.assertEqual(len(result['secondary_errors']), 1)
                self.assertEqual(result['secondary_errors'][0]['error_type'], type(first if promote else later).__name__)
                self.assertEqual((result['actual_starts'], result['actual_starts_upper_bound'], result['actual_returns']), (0,0,0))
                self.assertEqual(self.events, [])


    def test_C21_loader_binding_precedes_historical_access(self):
        root, folder = self.prepare()
        order = []
        actual_pin = subject.loader_pin
        sentinel = c.IntegrityError('literal stop before manifest or historical access')
        def pin(value):
            order.append('admitted_pin' if value.get('schema') == 'worker38-loader-pin-v1' else 'observed_pin')
            return actual_pin(value)
        def stop_manifest(path):
            order.append('manifest_boundary')
            raise sentinel
        with self.injected(read_manifest=stop_manifest), patch.object(subject, 'loader_pin', side_effect=pin), \
                patch.object(subject, 'verify_files') as files, patch.object(subject, 'isolated_imports') as imports, \
                patch.object(subject, 'construct_fixture') as fixture:
            with self.assertRaises(c.IntegrityError) as caught:
                subject.run_cell(root, 2)
            self.assertIs(caught.exception, sentinel)
            files.assert_not_called(); imports.assert_not_called(); fixture.assert_not_called()
        self.assertEqual(order, ['admitted_pin', 'observed_pin', 'manifest_boundary'])
        result = self.read(folder/'cell-receipt.json')
        self.assertEqual(result['status'], 'execution_blocked')
        self.assertEqual(result['actual_starts'], 0)
        self.assertEqual(result['actual_returns'], 0)
        self.assertEqual(self.events, [])

    def test_C22_loader_mismatch_blocks_before_import(self):
        for variant in ('missing_pin', 'bad_pin', 'missing_observation', 'library_hash', 'library_size'):
            with self.subTest(variant=variant):
                root, folder = self.prepare(name=variant)
                admission = self.read(root/'external-admission.json')
                runtime = copy.deepcopy(self.runtime)
                if variant == 'missing_pin': del admission['loader_pin']
                if variant == 'bad_pin': admission['loader_pin']['extra'] = 'forbidden'
                if variant == 'missing_observation': del runtime['loader']
                if variant == 'library_hash': runtime['loader']['library_sha256'] = '5' * 64
                if variant == 'library_size': runtime['loader']['library_size_bytes'] = 4097
                (root/'external-admission.json').write_bytes(c.canonical(admission))
                with self.injected(runtime_check=lambda **kwargs: runtime), \
                        patch.object(subject, 'read_manifest') as manifest, \
                        patch.object(subject, 'verify_files') as files, \
                        patch.object(subject, 'isolated_imports') as imports, \
                        patch.object(subject, 'construct_fixture') as fixture:
                    with self.assertRaises(c.IntegrityError): subject.run_cell(root, 2)
                    manifest.assert_not_called(); files.assert_not_called()
                    imports.assert_not_called(); fixture.assert_not_called()
                result = self.read(folder/'cell-receipt.json')
                self.assertEqual(result['status'], 'execution_blocked')
                self.assertEqual(result['phase'], 'cell_source_runtime_preflight')
                self.assertEqual(result['secondary_errors'], [])
                self.assertIsNone(result['hook_restored'])
                self.assertIsNone(result['timer_restored'])
                for field in ('actual_starts', 'actual_starts_upper_bound', 'actual_returns',
                              'confirmed_captures', 'pre_call_markers', 'invocation_attempts'):
                    self.assertEqual(result[field], 0)
                self.assertEqual(result['calls'], {})
                self.assertEqual(self.events, [])


if __name__ == '__main__':
    unittest.main()
