"""Fourteen prospectively fixed literal preflight cases; no real child process."""
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

CLEAN = {'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1'}
RUNTIME = {'implementation': 'CPython', 'version': '3.11.16',
           'executable_sha256': p.c.RUNTIME['executable_sha256'], 'executable': '/literal/python',
           'effective_flags': {'dont_write_bytecode': 1, 'no_user_site': 1},
           'python_environment': CLEAN, 'gc_enabled': True, 'gc_threshold': [700, 10, 10],
           'address_space': list(p.MEMORY)}


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
        stack.enter_context(patch.dict(os.environ, CLEAN, clear=True))
        self.runtime = stack.enter_context(patch.object(p.c, 'runtime_check', return_value=copy.deepcopy(RUNTIME)))
        stack.enter_context(patch.object(p, 'limits', return_value={'RLIMIT_AS': list(pair)}))
        self.getlimit = stack.enter_context(patch.object(resource, 'getrlimit', return_value=pair))
        self.setlimit = stack.enter_context(patch.object(resource, 'setrlimit'))
        return stack

    def fake_child(self, folder, proof=None, *, returncode=0):
        process = Mock(pid=876543, returncode=returncode)
        def complete(*args, **kwargs):
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
                patch.dict(os.environ, {'PYTHONPATH': '/literal/path', 'LD_LIBRARY_PATH': '/literal/lib',
                                       'GH_TOKEN': 'literal-noncredential', 'GITHUB_TOKEN': 'literal-noncredential',
                                       'ACTIONS_RUNTIME_TOKEN': 'literal-noncredential'}):
            proof = p.spawn_probe(self.root, parent_proof())
        command = popen.call_args.args[0]
        self.assertEqual(command[:3], [str(Path(sys.executable).resolve()), '-B', '-s'])
        self.assertEqual(command[3:], [str(Path(p.__file__).resolve()), '--child', '--report', str(self.root / 'fresh-child.json')])
        env = popen.call_args.kwargs['env']
        self.assertEqual({k: v for k, v in env.items() if k.startswith('PYTHON')}, CLEAN)
        self.assertNotIn('LD_LIBRARY_PATH', env); self.assertNotIn('LD_PRELOAD', env)
        for key in ('GH_TOKEN', 'GITHUB_TOKEN', 'ACTIONS_RUNTIME_TOKEN'): self.assertNotIn(key, env)
        self.assertEqual(proof['pid'], 876543)
        process.communicate.assert_called_once_with(timeout=30)
        self.assertEqual((self.root / 'fresh-child.stdout').read_bytes(), b'literal runtime stub stdout\n')

    def test_R07_loader_failure_retained(self):
        process = self.fake_child(self.root, returncode=127)
        with patch.object(p.subprocess, 'Popen', return_value=process) as popen:
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
            with self.subTest(case=case), patch.object(p.subprocess, 'Popen', return_value=process):
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
                        'unset LD_PRELOAD LD_LIBRARY_PATH', 'export PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1',
                        '"$name" == PYTHON*', '"$executable" -B -s scripts/worker36/runner_preflight.py',
                        p.c.RUNTIME['executable_sha256'], 'parent_exit_code=%s', 'parent.stderr',
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


if __name__ == '__main__':
    unittest.main()
