"""Semantic/platform validation of the rendered Actions contract."""
import ast
from pathlib import Path
import subprocess
import unittest
import yaml

import build_workflow as b


class Workflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        b.build()
        cls.workflow = yaml.safe_load((b.ROOT / "worker35-sealed-recovery.yml").read_text())

    def test_exact_trigger_permissions_and_no_checkout(self):
        w = self.workflow
        self.assertEqual(w["on"], {"push": {"branches": ["research/worker35-sealed-recovery-36990202101"]}})
        self.assertEqual(w["permissions"], {"contents": "read", "actions": "read"})
        self.assertFalse(w["concurrency"]["cancel-in-progress"])
        self.assertEqual(set(w["jobs"]), {"snapshot", "upload-part"})
        for job in w["jobs"].values():
            self.assertEqual(job["runs-on"], ["self-hosted", "Linux", "X64", "bandido-alcatraz-ci"])
            self.assertIn("github.run_attempt == 1", job["if"])
            for step in job["steps"]:
                if "uses" in step:
                    self.assertEqual(step["uses"], "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02")
                    self.assertEqual(step["with"]["if-no-files-found"], "error")
                    self.assertEqual(step["with"]["compression-level"], 0)
                    self.assertNotIn("..", step["with"]["path"])

    def test_run_limits_python_compile_and_shell_syntax(self):
        for job in self.workflow["jobs"].values():
            for step in job["steps"]:
                if "run" not in step:
                    continue
                run = step["run"]
                self.assertLessEqual(len(run), 21000)
                self.assertEqual(run[:len("set -euo pipefail\npython3 -I -B - <<'PY'\n")], "set -euo pipefail\npython3 -I -B - <<'PY'\n")
                source = run.split("<<'PY'\n", 1)[1].rsplit("PY\n", 1)[0]
                compile(source, "inline-recovery", "exec")
                result = subprocess.run(["bash", "-n"], input=run, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                tree = ast.parse(source)
                modules = [n.module if isinstance(n, ast.ImportFrom) else n.names[0].name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
                self.assertFalse(any(m and (m.startswith("bandido") or m.startswith("scripts")) for m in modules))
                self.assertNotIn("${{", run)

    def test_runner_context_only_in_step_keys(self):
        w = self.workflow
        for key, value in w.items():
            if key != "jobs": self.assertNotIn("runner.", str(value))
        for job in w["jobs"].values():
            for key, value in job.items():
                if key != "steps": self.assertNotIn("runner.", str(value))
            for step in job["steps"]:
                if "run" in step:
                    self.assertEqual(step["working-directory"], "${{ runner.temp }}")
                    self.assertEqual(step["env"]["GH_TOKEN"], "${{ github.token }}")

    def test_fail_closed_matrix_and_post_upload_recheck(self):
        snap = self.workflow["jobs"]["snapshot"]
        upload = self.workflow["jobs"]["upload-part"]
        self.assertEqual(upload["needs"], "snapshot")
        self.assertIn("needs.snapshot.result == 'success'", upload["if"])
        self.assertEqual(upload["strategy"]["matrix"], {"part": "${{ fromJSON(needs.snapshot.outputs.parts) }}"})
        self.assertFalse(upload["strategy"]["fail-fast"])
        self.assertEqual(upload["strategy"]["max-parallel"], 1)
        self.assertEqual(upload["steps"][0]["run"], upload["steps"][2]["run"])
        self.assertEqual(upload["steps"][2]["if"], "always() && steps.verify.outcome == 'success'")
        self.assertEqual(snap["steps"][1]["if"], "always() && steps.snapshot.outputs.metadata_ready == 'true'")
        self.assertEqual(snap["steps"][2]["if"], "always() && steps.metaverify.outcome == 'success'")
        self.assertEqual(snap["steps"][1]["run"], snap["steps"][3]["run"])
        paths = snap["steps"][2]["with"]["path"].splitlines()
        self.assertEqual(len(paths), 6)
        self.assertTrue(all("*" not in path and path.endswith(".json") for path in paths))


if __name__ == "__main__":
    unittest.main()
