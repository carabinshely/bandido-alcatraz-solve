"""GitHub platform semantics and literal-inline source checks."""
import ast
import subprocess
import unittest
import yaml

import build_workflow as b


class Workflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        b.build(); cls.w = yaml.safe_load((b.ROOT / 'worker35-tail-recovery.yml').read_text())

    def test_exact_branch_one_job_read_only_permissions(self):
        self.assertEqual(self.w['on'], {'push': {'branches': ['research/worker35-tail-recovery-36990202101']}})
        self.assertEqual(self.w['permissions'], {'contents': 'read', 'actions': 'read'})
        self.assertFalse(self.w['concurrency']['cancel-in-progress'])
        self.assertEqual(set(self.w['jobs']), {'preserve'})
        job = self.w['jobs']['preserve']
        self.assertEqual(job['runs-on'], ['self-hosted', 'Linux', 'X64', 'bandido-alcatraz-ci'])
        self.assertEqual(job['timeout-minutes'], 15)
        self.assertIn('github.run_attempt == 1', job['if'])

    def test_script_compile_shell_syntax_and_run_limits(self):
        for step in self.w['jobs']['preserve']['steps']:
            if 'run' not in step: continue
            run = step['run']; self.assertLessEqual(len(run), 21000)
            self.assertTrue(run.startswith("set -euo pipefail\npython3 -I -B - <<'PY'\n"))
            source = run.split("<<'PY'\n", 1)[1].rsplit('PY\n', 1)[0]
            compile(source, 'inline', 'exec')
            result = subprocess.run(['bash', '-n'], input=run, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('${{', source)
            imported = [a.name for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Import) for a in n.names]
            self.assertFalse(any(name.startswith(('bandido', 'scripts')) for name in imported))

    def test_no_checkout_one_explicit_upload_and_failure_preservation(self):
        steps = self.w['jobs']['preserve']['steps']
        uses = [s for s in steps if 'uses' in s]
        self.assertEqual(len(uses), 1)
        upload = uses[0]
        self.assertEqual(upload['uses'], 'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02')
        paths = upload['with']['path'].splitlines()
        self.assertEqual(len(paths), 7)
        self.assertTrue(all('*' not in p and '..' not in p for p in paths))
        self.assertEqual(upload['with']['compression-level'], 0)
        self.assertEqual(upload['with']['if-no-files-found'], 'error')
        self.assertEqual(steps[1]['if'], "always() && steps.snapshot.outputs.upload_ready == 'true'")
        self.assertEqual(steps[2]['if'], "always() && steps.verify.outcome == 'success'")
        self.assertEqual(steps[3]['if'], "always() && steps.verify.outcome == 'success'")
        self.assertEqual(steps[1]['run'], steps[3]['run'])

    def test_runner_context_step_only(self):
        for key, value in self.w.items():
            if key != 'jobs': self.assertNotIn('runner.', str(value))
        for key, value in self.w['jobs']['preserve'].items():
            if key != 'steps': self.assertNotIn('runner.', str(value))
        for step in self.w['jobs']['preserve']['steps']:
            if 'run' in step: self.assertEqual(step['working-directory'], '${{ runner.temp }}')


if __name__ == '__main__':
    unittest.main()
