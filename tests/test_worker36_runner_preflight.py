"""R1 finite preflight/loader/bootstrap cases; no pinned or scientific execution."""
from contextlib import ExitStack
import copy
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from worker36 import runner_preflight as p

STUB_POPEN_CALLS = 0
STUB_SHELL_PROCESS_STARTS = 0
STUB_TIMEOUT_INVOCATIONS = 0
STUB_EXECUTABLE_ENTRIES = 0
STUB_SLEEP_INVOCATIONS = 0
CLEAN = {'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1'}
PREFIX = '/literal/toolcache/Python/3.11.16/x64'
LOADER = {'schema': 'worker36-loader-identity-v1', 'tool_cache': '/literal/toolcache',
          'executable_path': PREFIX + '/bin/python3.11', 'executable_sha256': p.c.RUNTIME['executable_sha256'],
          'library_relative_path': 'Python/3.11.16/x64/lib/libpython3.11.so.1.0',
          'library_path': PREFIX + '/lib/libpython3.11.so.1.0', 'library_directory': PREFIX + '/lib',
          'library_sha256': 'a' * 64, 'library_size_bytes': 123456,
          'library_device': {'major': 8, 'minor': 1}, 'library_inode': 123,
          'mapped_library': {'path': PREFIX + '/lib/libpython3.11.so.1.0',
                             'device': {'major': 8, 'minor': 1}, 'inode': 123},
          'loader_environment': {'LD_LIBRARY_PATH': PREFIX + '/lib'}}
SHELL_ENV = {'WORKER36_PYTHON': LOADER['executable_path'], 'WORKER36_LOADER_DIRECTORY': LOADER['library_directory'],
             'WORKER36_LOADER_LIBRARY': LOADER['library_path'], 'WORKER36_LOADER_SHA256': LOADER['library_sha256'],
             'WORKER36_LOADER_SIZE_BYTES': str(LOADER['library_size_bytes'])}
SANITIZED = {**CLEAN, **SHELL_ENV, **LOADER['loader_environment']}
RUNTIME = {'implementation': 'CPython', 'version': '3.11.16',
           'executable_sha256': p.c.RUNTIME['executable_sha256'], 'executable': LOADER['executable_path'],
           'effective_flags': {'dont_write_bytecode': 1, 'no_user_site': 1},
           'python_environment': CLEAN, 'gc_enabled': True, 'gc_threshold': [700, 10, 10],
           'address_space': list(p.MEMORY), 'loader': LOADER}


def parent_proof():
    return {'runtime': copy.deepcopy(RUNTIME), 'capped_limits': {'RLIMIT_AS': list(p.MEMORY)}}


def child_proof():
    return {'pid': 876543, 'parent_pid': os.getpid(), 'runtime': copy.deepcopy(RUNTIME),
            'inherited_limits': {'RLIMIT_AS': list(p.MEMORY)},
            'capped_limits': {'RLIMIT_AS': list(p.MEMORY)},
            'sanitized_environment': True, **p.ZERO}


class RunnerPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='worker36-preflight-literal-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def runtime_mocks(self, pair):
        stack = ExitStack()
        stack.enter_context(patch.dict(os.environ, SANITIZED, clear=True))
        stack.enter_context(patch.object(p.c, 'loader_identity', return_value=copy.deepcopy(LOADER)))
        self.runtime = stack.enter_context(patch.object(p.c, 'runtime_check', return_value=copy.deepcopy(RUNTIME)))
        stack.enter_context(patch.object(p, 'limits', return_value={'RLIMIT_AS': list(pair)}))
        self.getlimit = stack.enter_context(patch.object(resource, 'getrlimit', return_value=pair))
        self.setlimit = stack.enter_context(patch.object(resource, 'setrlimit'))
        return stack

    def fake_child(self, folder, proof=None, *, returncode=0):
        process = Mock(pid=876543, returncode=returncode)
        communicated = False
        def complete(*args, **kwargs):
            global STUB_POPEN_CALLS
            nonlocal communicated
            if not communicated:
                STUB_POPEN_CALLS += 1
                communicated = True
            if proof is not None:
                raw = proof if isinstance(proof, bytes) else p.c.canonical(proof)
                (folder / 'fresh-child.json').write_bytes(raw)
            return (b'literal runtime stub stdout\n',
                    b'error while loading shared libraries: libpython3.11.so.1.0\n' if returncode else b'')
        process.communicate.side_effect = complete
        return process

    def test_R01_environment_exact(self):
        with self.runtime_mocks(p.MEMORY):
            self.assertTrue(p.runtime_probe(child=True)['sanitized_environment'])
        for key, value in (('PYTHONPATH', '/literal/path'), ('LD_LIBRARY_PATH', '/literal/lib'),
                           ('LD_PRELOAD', '/literal/preload')):
            with self.runtime_mocks(p.MEMORY), patch.dict(os.environ, {key: value}):
                with self.assertRaisesRegex(p.c.IntegrityError, 'not sanitized'):
                    p.runtime_probe(child=True)
                self.runtime.assert_not_called()

    def test_R02_parent_exact_cap(self):
        with self.runtime_mocks((-1, -1)):
            self.getlimit.side_effect = [(-1, -1), p.MEMORY]
            proof = p.runtime_probe()
            self.setlimit.assert_called_once_with(resource.RLIMIT_AS, p.MEMORY)
            self.assertEqual(proof['inherited_limits']['RLIMIT_AS'], [-1, -1])
            self.assertEqual(self.runtime.call_args_list[-1].kwargs, {'child': True})
            self.assertEqual(proof['runtime']['address_space'], list(p.MEMORY))

    def test_R03_unexpected_initial_cap(self):
        with self.runtime_mocks((268435456, 268435456)):
            with self.assertRaisesRegex(p.c.IntegrityError, 'unexpected initial'):
                p.runtime_probe()
            self.setlimit.assert_not_called()

    def test_R04_child_inherits_exact_cap(self):
        with self.runtime_mocks(p.MEMORY):
            p.runtime_probe(child=True)
            self.setlimit.assert_not_called()
        with self.runtime_mocks((268435456, 268435456)):
            with self.assertRaisesRegex(p.c.IntegrityError, 'exact512MiB'):
                p.runtime_probe(child=True)
            self.setlimit.assert_not_called()

    def test_R05_runtime_failure_blocks(self):
        with self.runtime_mocks((-1, -1)), patch.object(p, 'spawn_probe') as spawn, \
                patch.object(p, 'run_focused_tests') as run:
            self.runtime.side_effect = p.c.IntegrityError('wrong pinned interpreter')
            with self.assertRaisesRegex(p.c.IntegrityError, 'wrong pinned'):
                p.preflight(self.root, 'a' * 40, 'b' * 40, {})
            spawn.assert_not_called(); run.assert_not_called(); self.setlimit.assert_not_called()

    def test_R06_child_command_and_proof(self):
        process = self.fake_child(self.root, child_proof())
        with patch.object(p.subprocess, 'Popen', return_value=process) as popen, \
                patch.object(p.c, 'loader_identity', return_value=copy.deepcopy(LOADER)), \
                patch.dict(os.environ, {'PYTHONPATH': '/literal/path', 'LD_LIBRARY_PATH': '/literal/lib',
                                       'GH_TOKEN': 'literal-noncredential', 'GITHUB_TOKEN': 'literal-noncredential',
                                       'ACTIONS_RUNTIME_TOKEN': 'literal-noncredential'}):
            proof = p.spawn_probe(self.root, parent_proof())
        command = popen.call_args.args[0]
        self.assertEqual(command[:3], [str(Path(sys.executable).resolve()), '-B', '-s'])
        self.assertEqual(command[3:], [str(Path(p.__file__).resolve()), '--child', '--report', str(self.root / 'fresh-child.json')])
        env = popen.call_args.kwargs['env']
        self.assertEqual({k: v for k, v in env.items() if k.startswith('PYTHON')}, CLEAN)
        self.assertEqual({k: v for k, v in env.items() if k.startswith('LD')}, LOADER['loader_environment'])
        for key in ('GH_TOKEN', 'GITHUB_TOKEN', 'ACTIONS_RUNTIME_TOKEN'): self.assertNotIn(key, env)
        self.assertEqual(proof['pid'], 876543)
        process.communicate.assert_called_once_with(timeout=30)
        self.assertEqual((self.root / 'fresh-child.stdout').read_bytes(), b'literal runtime stub stdout\n')

    def test_R07_loader_failure_retained(self):
        process = self.fake_child(self.root, returncode=127)
        with patch.object(p.subprocess, 'Popen', return_value=process) as popen, \
                patch.object(p.c, 'loader_identity', return_value=copy.deepcopy(LOADER)):
            with self.assertRaisesRegex(p.c.IntegrityError, 'startup failed'):
                p.spawn_probe(self.root, parent_proof())
        self.assertEqual(popen.call_count, 1)
        self.assertIn(b'libpython3.11.so.1.0', (self.root / 'fresh-child.stderr').read_bytes())
        self.assertEqual(json.loads((self.root / 'fresh-child-process.json').read_bytes())['returncode'], 127)

    def test_R08_bad_child_proofs(self):
        for index, case in enumerate(('absent', '{torn', 'wrong-pid', 'wrong-parent', 'wrong-executable', 'wrong-runtime')):
            folder = self.root / str(index); folder.mkdir()
            proof = child_proof()
            if case == 'wrong-pid': proof['pid'] = 1
            if case == 'wrong-parent': proof['parent_pid'] = -1
            if case == 'wrong-executable': proof['runtime']['executable'] = '/wrong/python'
            if case == 'wrong-runtime': proof['runtime']['version'] = '0.0.0'
            value = None if case == 'absent' else (b'{torn' if case == '{torn' else proof)
            process = self.fake_child(folder, value)
            with self.subTest(case=case), patch.object(p.subprocess, 'Popen', return_value=process), \
                    patch.object(p.c, 'loader_identity', return_value=copy.deepcopy(LOADER)):
                with self.assertRaises((OSError, ValueError, KeyError)):
                    p.spawn_probe(folder, parent_proof())

    def test_R09_only_explicit_tests_and_no_history(self):
        test_paths = {name for name in p.checked_paths(ROOT) if name.startswith('tests/test_')}
        self.assertEqual(test_paths, {'tests/' + name + '.py' for name in p.TEST_MODULES})
        (self.root / 'tests').mkdir()
        (self.root / 'tests/test_worker36_unlisted.py').write_text('pass\n')
        with self.assertRaisesRegex(p.c.IntegrityError, 'explicit allowlist'):
            p.checked_paths(self.root)
        guard = p.NoHistoricalImports({'literal_historical_module'})
        self.assertIsNone(guard.find_spec('unittest'))
        for name in ('literal_historical_module', 'bandido_alcatraz.game'):
            with self.assertRaisesRegex(p.c.IntegrityError, 'prohibited'):
                guard.find_spec(name)
        with patch.dict(sys.modules, {'literal_historical_module': types.ModuleType('literal_historical_module')}):
            with self.assertRaisesRegex(p.c.IntegrityError, 'already imported'):
                guard.check_loaded()

    def test_R10_static_only_source_checks(self):
        pins = {p.EXPERIMENT + 'PROTOCOL.md': p.c.PROTOCOL_SHA256}
        manifest = {'files': [{'module': 'benchmark_worker35_synthetic', 'path': 'scripts/stub.py',
                              'git_blob': 'c' * 40, 'imports': []}],
                    'roots': ['benchmark_worker35_synthetic'], 'constructor': {'literal': True}}
        raw = b'pass\n'
        with patch.object(p, 'snapshot', return_value=pins), patch.object(p.c, 'file_info', return_value={'sha256': 'd' * 64}), \
                patch.object(p.d, 'verify_test_receipt') as receipt, \
                patch.object(p.s, 'git', side_effect=[b'a' * 40, b'b' * 40, b'', b'c' * 40, raw]), \
                patch.object(p.s, 'read_manifest', return_value=manifest), \
                patch.object(p.s, 'verify_blob') as blob, patch.object(p.s, 'verify_constructor') as constructor, \
                patch.object(p.s, 'restore') as restore, patch.object(p.s, 'isolated_imports') as imports, \
                patch.object(p.s, 'construct_fixture') as fixture:
            observed, names = p.static_check(ROOT, 'a' * 40, 'b' * 40)
        self.assertEqual(observed, pins); self.assertEqual(names, {'benchmark_worker35_synthetic'})
        receipt.assert_called_once_with(ROOT, 'd' * 64)
        blob.assert_called_once_with(raw, manifest['files'][0]); constructor.assert_called_once_with(raw, manifest['constructor'])
        restore.assert_not_called(); imports.assert_not_called(); fixture.assert_not_called()
        path = self.root / 'literal.py'; path.write_text('pass\n')
        with patch.object(p, 'checked_paths', return_value=['literal.py']):
            self.assertEqual(p.snapshot(self.root), {'literal.py': p.c.sha(b'pass\n')})
            path.write_text('bad syntax !\n')
            with self.assertRaises(SyntaxError): p.snapshot(self.root)

    def preflight_mocks(self, result, *, changed=False):
        stack = ExitStack()
        stack.enter_context(patch.object(p, 'runtime_probe', return_value=parent_proof()))
        stack.enter_context(patch.object(p, 'spawn_probe', return_value=child_proof()))
        stack.enter_context(patch.object(p, 'static_check', return_value=({'literal.py': 'a' * 64}, set())))
        stack.enter_context(patch.object(p.c, 'file_info', return_value={'sha256': 'c' * 64, 'size_bytes': 1}))
        stack.enter_context(patch.object(p, 'run_focused_tests', return_value=result))
        stack.enter_context(patch.object(p, 'snapshot', return_value={'literal.py': ('b' if changed else 'a') * 64}))
        return stack

    def test_R11_changed_source_blocks(self):
        result = {'success': True, 'tests_run': 1, 'failures': 0, 'errors': 0, 'skipped': 0}
        with self.preflight_mocks(result, changed=True):
            with self.assertRaisesRegex(p.c.IntegrityError, 'sources changed'):
                p.preflight(self.root, 'a' * 40, 'b' * 40, dict(p.ZERO))

    def test_R12_stub_result_is_not_admission(self):
        for index, fault in enumerate((None, 'failures', 'errors', 'skipped')):
            folder = self.root / str(index); folder.mkdir()
            result = {'success': fault is None, 'tests_run': 1, 'failures': 0, 'errors': 0, 'skipped': 0}
            if fault: result[fault] = 1
            literal_result = Mock(testsRun=1, failures=[('literal', 'fault')] if fault == 'failures' else [],
                                  errors=[('literal', 'fault')] if fault == 'errors' else [],
                                  skipped=[('literal', 'skip')] if fault == 'skipped' else [])
            literal_result.wasSuccessful.return_value = fault not in ('failures', 'errors')
            with patch.object(p.unittest.defaultTestLoader, 'loadTestsFromNames', return_value='literal-suite') as load, \
                    patch.object(p.unittest, 'TextTestRunner') as runner, \
                    patch.object(p, 'NoHistoricalImports') as guard, \
                    patch.dict(sys.modules, {'bandido_alcatraz': types.ModuleType('bandido_alcatraz')}):
                runner.return_value.run.return_value = literal_result
                observed = p.run_focused_tests(ROOT, {'literal_historical_module'})
                load.assert_called_once_with(p.TEST_MODULES)
                self.assertEqual(guard.return_value.check_loaded.call_count, 2)
                runner.return_value.run.assert_called_once_with('literal-suite')
                self.assertEqual(observed['success'], fault is None)
                self.assertEqual(observed['test_modules'], list(p.TEST_MODULES))
            record = dict(p.ZERO)
            with self.preflight_mocks(result):
                if fault:
                    with self.assertRaisesRegex(p.c.IntegrityError, 'did not pass'):
                        p.preflight(folder, 'a' * 40, 'b' * 40, record)
                else:
                    p.preflight(folder, 'a' * 40, 'b' * 40, record)
                    self.assertTrue(record['success']); self.assertEqual(record['status'], 'preparation_passed')
                    self.assertFalse(record['measurement_admitted'])
                    self.assertTrue(all(record[k] == v for k, v in p.ZERO.items()))

    def test_R13_branch_workflow_contract(self):
        workflow = (ROOT / '.github/workflows/worker36-runner-preflight.yml').read_text()
        for literal in ('types: [opened, synchronize, reopened]', 'branches: [main]',
                        "github.repository == 'carabinshely/bandido-alcatraz-solve'",
                        "github.event.pull_request.head.ref == 'research/worker36-synthetic-profile-overhead'",
                        "github.event.pull_request.base.ref == 'main'",
                        "github.event.pull_request.base.sha == '9c1eeeb8a26868d41f8d8d89b17fc897a60cb38b'",
                        "github.event.sender.login == 'carabinshely'", "python-version: '3.11.16'",
                        'source "$GITHUB_WORKSPACE/scripts/worker36-loader.sh"', 'worker36_loader_setup',
                        '"$WORKER36_PYTHON" -B -s scripts/worker36/runner_preflight.py',
                        'library_sha256=%s', 'parent_exit_code=%s', 'parent.stderr',
                        "if: always() && env.WORKER36_PREFLIGHT_OUTPUT != ''"):
            self.assertIn(literal, workflow)
        for forbidden in ('workflow_dispatch:', 'pull_request_target:', 'run_worker36_synthetic.py',
                          'admission.py authenticate', 'test.yml', 'unittest discover'):
            self.assertNotIn(forbidden, workflow)

    def test_R14_failed_main_preserves_completed_phase(self):
        report = self.root / 'report.json'
        def blocked(folder, head, tree, record):
            record['parent'] = parent_proof()
            raise p.c.IntegrityError('literal fresh-child blocker')
        with patch.object(p, 'preflight', side_effect=blocked):
            self.assertEqual(p.main(['--report', str(report), '--expected-head', 'a' * 40,
                                     '--expected-tree', 'b' * 40]), 1)
        record = json.loads(report.read_bytes())
        self.assertEqual(record['status'], 'execution_blocked')
        self.assertFalse(record['success']); self.assertEqual(record['parent'], parent_proof())
        self.assertFalse(record['measurement_admitted']); self.assertEqual(record['games'], 0)
        self.assertEqual(record['error'], 'literal fresh-child blocker')


    def test_L01_shell_identity_matches_runtime(self):
        with patch.dict(os.environ, SHELL_ENV, clear=True):
            self.assertEqual(p.shell_loader_identity(LOADER),
                             {key: LOADER[key] for key in p.SHELL_LOADER_FIELDS.values()})
        for name in SHELL_ENV:
            for absent in (True, False):
                environment = dict(SHELL_ENV)
                if absent: environment.pop(name)
                else: environment[name] = 'fixed-mismatch'
                with self.subTest(name=name, absent=absent), patch.dict(os.environ, environment, clear=True):
                    with self.assertRaisesRegex(p.c.IntegrityError, 'shell/runtime loader identity mismatch'):
                        p.shell_loader_identity(LOADER)

    def test_L02_child_loader_drift_blocks(self):
        for index, field in enumerate(('executable_path', 'library_path', 'library_directory',
                                       'library_sha256', 'library_size_bytes')):
            folder = self.root / str(index); folder.mkdir()
            proof = child_proof(); proof['runtime']['loader'][field] = 'fixed-mismatch'
            process = self.fake_child(folder, proof)
            with self.subTest(field=field), patch.object(p.subprocess, 'Popen', return_value=process), \
                    patch.object(p.c, 'loader_identity', return_value=copy.deepcopy(LOADER)):
                with self.assertRaisesRegex(p.c.IntegrityError, 'fresh child runtime differs'):
                    p.spawn_probe(folder, parent_proof())

    def test_L03_shared_loader_workflow_contract(self):
        preflight = (ROOT / '.github/workflows/worker36-runner-preflight.yml').read_text()
        diagnostic = (ROOT / '.github/workflows/worker36-synthetic-profile.yml').read_text()
        source = 'source "$GITHUB_WORKSPACE/scripts/worker36-loader.sh"'
        self.assertEqual(preflight.count(source), 1)
        self.assertEqual(diagnostic.count(source), 2)
        self.assertIn('worker36_loader_setup "$expected_library_sha256" "$expected_library_size_bytes"', diagnostic)
        self.assertIn('"$WORKER36_PYTHON" -B -s scripts/worker36/admission.py authenticate', diagnostic)
        self.assertIn('"$WORKER36_PYTHON" -B -s "$GITHUB_WORKSPACE/scripts/run_worker36_synthetic.py" measure', diagnostic)
        self.assertIn('"$WORKER36_PRESERVE_EXECUTABLE" -B -s "$GITHUB_WORKSPACE/scripts/run_worker36_synthetic.py" preserve', diagnostic)
        self.assertIn('> "$output/shell-loader.json"', preflight)
        self.assertIn('types: [edited]', diagnostic)
        self.assertNotIn('workflow_dispatch:', diagnostic)
        for name in ('WORKER36_PRESERVE_EXECUTABLE', 'WORKER36_PRESERVE_LIBRARY_DIRECTORY',
                     'WORKER36_PRESERVE_LIBRARY_SHA256', 'WORKER36_PRESERVE_LIBRARY_SIZE_BYTES'):
            self.assertIn(name + '=%s', diagnostic)

    def test_L04_shell_and_plan_in_checked_inventory(self):
        paths = p.checked_paths(ROOT)
        self.assertIn('scripts/worker36-loader.sh', paths)
        self.assertIn('evidence-design/recovery-r1-preflight-shell-test-plan.json', paths)
        self.assertEqual(len(p.TEST_MODULES), 8)
        path = self.root / 'literal.sh'; path.write_text('true\n')
        with patch.object(p, 'checked_paths', return_value=['literal.sh']), patch.object(p.subprocess, 'run') as run:
            self.assertEqual(p.snapshot(self.root), {'literal.sh': p.c.sha(b'true\n')})
            run.assert_called_once_with(['bash', '-n', str(path)], check=True,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_L05_verified_loader_is_recorded_before_work(self):
        with self.runtime_mocks(p.MEMORY):
            proof = p.runtime_probe(child=True)
        self.assertEqual(proof['runtime']['loader'], LOADER)
        self.assertEqual(proof['shell_loader'], {key: LOADER[key] for key in p.SHELL_LOADER_FIELDS.values()})
        result = {'success': True, 'tests_run': 1, 'failures': 0, 'errors': 0, 'skipped': 0}
        record = dict(p.ZERO)
        with self.preflight_mocks(result): p.preflight(self.root, 'a' * 40, 'b' * 40, record)
        self.assertEqual(record['loader_pin'], p.c.loader_pin(LOADER))
        with patch.object(p.c, 'loader_identity', side_effect=p.c.IntegrityError('literal identity failure')), \
                patch.object(p, 'spawn_probe') as spawn, patch.object(p, 'run_focused_tests') as tests:
            with self.assertRaisesRegex(p.c.IntegrityError, 'literal identity failure'):
                p.preflight(self.root, 'a' * 40, 'b' * 40, {})
            spawn.assert_not_called(); tests.assert_not_called()

    def test_L06_explicit_loader_environment_only(self):
        for key in ('LD_AUDIT', 'LD_DEBUG'):
            with self.runtime_mocks(p.MEMORY), patch.dict(os.environ, {key: 'fixed-ambient'}):
                with self.assertRaisesRegex(p.c.IntegrityError, 'not sanitized'):
                    p.runtime_probe(child=True)
                self.runtime.assert_not_called()
        with patch.object(p.c, 'loader_identity', return_value=copy.deepcopy(LOADER)):
            environment = p.c.clean_environment({'LD_AUDIT': 'bad', 'LD_DEBUG': 'bad',
                'LD_LIBRARY_PATH': '/wrong', 'PYTHONPATH': '/wrong'}, loader=LOADER)
        self.assertEqual(environment, {**CLEAN, **LOADER['loader_environment']})

    def preservation_shell(self):
        workflow = (ROOT / '.github/workflows/worker36-synthetic-profile.yml').read_text()
        step = workflow.split('      - name: Preserve verification result and all partial transport without retry\n', 1)[1]
        block = step.split('        run: |\n', 1)[1].split('      - uses:', 1)[0]
        return '\n'.join(line[10:] for line in block.splitlines())

    def run_shell_stub(self, *, changes=None, uptime='123.45 0.00\n', boot_id=None,
                       hang=False, absent=False, collision=False):
        global STUB_SHELL_PROCESS_STARTS, STUB_TIMEOUT_INVOCATIONS, STUB_EXECUTABLE_ENTRIES, STUB_SLEEP_INVOCATIONS
        folder = self.root / ('shell-' + str(len(list(self.root.iterdir())))); folder.mkdir()
        boot = '12345678-1234-1234-1234-123456789abc'
        (folder / 'uptime').write_text(uptime)
        (folder / 'boot-id').write_text((boot_id or boot) + '\n')
        (folder / 'raw-prefix').write_bytes(b'literal retained prefix\n')
        stub = folder / 'inert-shell'
        # Only this finite literal program can be launched as the fake runtime.
        source = "#!/bin/bash\nprintf 'entered\n' > \"$ENTRY\"\nprintf '%s\n' \"$@\" > \"$ARGUMENTS\"\n"
        source += "printf '%s\n' \"$LD_LIBRARY_PATH\" \"$PYTHONHASHSEED\" \"$PYTHONDONTWRITEBYTECODE\" \"${LD_FAKE-unset}\" \"${PYTHONPATH-unset}\" > \"$ENVIRONMENT\"\n"
        source += "if [[ \"$HANG\" == yes ]]; then\n  printf 'sleep\n' > \"$SLEEP\"\n  /bin/sleep 1\n  printf 'returned\n' > \"$RETURNED\"\nfi\nexit 0\n"
        with os.fdopen(os.open(stub, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o700), 'w') as stream:
            stream.write(source)
        environment = {'PATH': os.defpath, 'LANG': 'C', 'LC_ALL': 'C',
            'DURABLE': str(folder), 'ATTEMPT': str(folder / 'attempt'), 'TRANSPORT': str(folder / 'transport'),
            'AUTH': str(folder / 'auth'), 'GITHUB_WORKSPACE': str(ROOT), 'GITHUB_RUN_ID': '1',
            'ADMISSION_SHA256': 'a' * 64, 'ADMISSION_PROVENANCE_SHA256': 'b' * 64,
            'EXPECTED_HEAD': 'a' * 40, 'EXPECTED_TREE': 'b' * 40,
            'PRESERVATION_MONOTONIC_DEADLINE_MS': '124460', 'PRESERVATION_BOOTTIME_DEADLINE_MS': '124460',
            'PRESERVATION_BOOT_ID': boot, 'WORKER36_PRESERVE_EXECUTABLE': str(folder / 'absent' if absent else stub),
            'WORKER36_PRESERVE_LIBRARY_DIRECTORY': '/literal/stub-lib',
            'WORKER36_PRESERVE_LIBRARY_SHA256': 'a' * 64, 'WORKER36_PRESERVE_LIBRARY_SIZE_BYTES': '123456',
            'ENTRY': str(folder / 'entry'), 'ARGUMENTS': str(folder / 'arguments'),
            'ENVIRONMENT': str(folder / 'environment'), 'SLEEP': str(folder / 'sleep'),
            'RETURNED': str(folder / 'returned'), 'HANG': 'yes' if hang else 'no',
            'LD_FAKE': 'ambient', 'PYTHONPATH': '/literal/ambient'}
        environment.update(changes or {})
        report = folder / 'preservation-shell-outcome.json'
        if collision: report.write_bytes(b'{"original":"unchanged"}\n')
        code = self.preservation_shell().replace('/proc/sys/kernel/random/boot_id', str(folder / 'boot-id'))
        code = code.replace('/proc/uptime', str(folder / 'uptime'))
        STUB_SHELL_PROCESS_STARTS += 1
        result = subprocess.run(['/bin/bash', '-c', code], env=environment, cwd=folder,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        outcome = json.loads(report.read_bytes())
        entered = (folder / 'entry').exists()
        STUB_EXECUTABLE_ENTRIES += int(entered)
        STUB_SLEEP_INVOCATIONS += int((folder / 'sleep').exists())
        STUB_TIMEOUT_INVOCATIONS += int(entered or outcome.get('launch_attempted') is True)
        self.assertEqual((folder / 'raw-prefix').read_bytes(), b'literal retained prefix\n')
        return result, outcome, folder

    def test_B01_builtin_original_deadline_contract(self):
        workflow = (ROOT / '.github/workflows/worker36-synthetic-profile.yml').read_text()
        code = self.preservation_shell()
        before = code.split('if timeout ', 1)[0]
        before = '\n'.join(line for line in before.splitlines() if not line.lstrip().startswith('#')).replace('$((', '')
        for forbidden in ('jq ', 'sha256sum', 'source ', 'realpath ', 'python -', '$(', '600s'):
            self.assertNotIn(forbidden, before)
        for name in ('preservation_deadline_monotonic_ms', 'preservation_deadline_boottime_ms', 'preservation_boot_id'):
            self.assertIn('steps.measurement.outputs.' + name, workflow)
        self.assertIn('timeout --signal=KILL "$duration"', code)
        self.assertNotIn('--kill-after', code); self.assertNotIn('--foreground', code)
        self.assertIn('--preservation-deadline-monotonic-ms "$PRESERVATION_MONOTONIC_DEADLINE_MS"', code)
        self.assertIn('remaining_ms <= 600000', code)
        self.assertIn('${!LD@}', code); self.assertIn('${!PYTHON@}', code)

    def test_B02_success_has_original_deadline_and_environment(self):
        result, outcome, folder = self.run_shell_stub()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(outcome['remaining_ms_at_launch'], 1000)
        self.assertEqual(outcome['original_monotonic_deadline_ms'], 124460)
        self.assertEqual(outcome['original_boottime_deadline_ms'], 124460)
        self.assertEqual(outcome['original_boot_id'], '12345678-1234-1234-1234-123456789abc')
        self.assertTrue(outcome['boot_id_verified']); self.assertFalse(outcome['fsync_confirmed'])
        self.assertEqual((folder / 'environment').read_text().splitlines(), ['/literal/stub-lib', '0', '1', 'unset', 'unset'])
        args = (folder / 'arguments').read_text().splitlines()
        self.assertEqual(args[:2], ['-B', '-s'])
        self.assertEqual(args[-2:], ['--preservation-deadline-monotonic-ms', '124460'])

    def test_B03_loader_start_failure_retains_exit127(self):
        result, outcome, folder = self.run_shell_stub(absent=True)
        self.assertEqual(result.returncode, 127)
        self.assertEqual(outcome['exit_code'], 127)
        self.assertTrue(outcome['launch_attempted']); self.assertFalse(outcome['fsync_confirmed'])
        self.assertFalse((folder / 'entry').exists())

    def test_B04_invalid_handoffs_block_before_launch(self):
        cases = (({'PRESERVATION_MONOTONIC_DEADLINE_MS': ''}, {}, 78),
                 ({'PRESERVATION_BOOTTIME_DEADLINE_MS': 'literal'}, {}, 78),
                 ({'PRESERVATION_BOOTTIME_DEADLINE_MS': '1' * 16}, {}, 78),
                 ({'PRESERVATION_BOOTTIME_DEADLINE_MS': '0'}, {}, 78),
                 ({'PRESERVATION_BOOTTIME_DEADLINE_MS': '123460'}, {}, 75),
                 ({}, {'boot_id': '87654321-4321-4321-4321-cba987654321'}, 78),
                 ({'PRESERVATION_BOOTTIME_DEADLINE_MS': '999000'}, {}, 78),
                 ({}, {'uptime': 'literal-invalid\n'}, 78))
        for changes, options, expected in cases:
            with self.subTest(changes=changes, options=options):
                result, outcome, folder = self.run_shell_stub(changes=changes, **options)
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertFalse(outcome['launch_attempted']); self.assertFalse((folder / 'entry').exists())
                self.assertFalse(outcome['fsync_confirmed'])

    def test_B05_hang_uses_remaining_hard_kill(self):
        result, outcome, folder = self.run_shell_stub(hang=True, changes={'PRESERVATION_BOOTTIME_DEADLINE_MS': '123960'})
        self.assertEqual(result.returncode, 137, result.stderr)
        self.assertEqual(outcome['status'], 'deadline_exhausted')
        self.assertEqual(outcome['remaining_ms_at_launch'], 500)
        self.assertTrue((folder / 'entry').exists()); self.assertTrue((folder / 'sleep').exists())
        self.assertFalse((folder / 'returned').exists())

    def test_B06_prior_suspend_uses_paired_boottime(self):
        result, outcome, folder = self.run_shell_stub(changes={'PRESERVATION_MONOTONIC_DEADLINE_MS': '24460'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(outcome['remaining_ms_at_launch'], 1000)
        self.assertEqual(outcome['original_monotonic_deadline_ms'], 24460)
        self.assertEqual(outcome['original_boottime_deadline_ms'], 124460)
        self.assertEqual((folder / 'arguments').read_text().splitlines()[-1], '24460')

    def test_B07_invalid_loader_handoff_blocks(self):
        cases = ({'WORKER36_PRESERVE_EXECUTABLE': ''}, {'WORKER36_PRESERVE_LIBRARY_DIRECTORY': ''},
                 {'WORKER36_PRESERVE_LIBRARY_SHA256': 'wrong'}, {'WORKER36_PRESERVE_LIBRARY_SIZE_BYTES': '0'})
        for changes in cases:
            with self.subTest(changes=changes):
                result, outcome, folder = self.run_shell_stub(changes=changes)
                self.assertEqual(result.returncode, 78, result.stderr)
                self.assertEqual(outcome['reason'], 'invalid_carried_loader')
                self.assertFalse(outcome['launch_attempted']); self.assertFalse((folder / 'entry').exists())

    def test_B08_existing_report_is_preserved(self):
        result, outcome, folder = self.run_shell_stub(collision=True)
        self.assertEqual(result.returncode, 74)
        self.assertEqual(outcome, {'original': 'unchanged'})
        self.assertTrue((folder / 'entry').exists())
        self.assertEqual((folder / 'preservation-shell-outcome.json').read_bytes(), b'{"original":"unchanged"}\n')


if __name__ == '__main__':
    unittest.main()
