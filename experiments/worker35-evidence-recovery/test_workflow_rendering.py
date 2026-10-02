"""Pure syntax/semantic regression tests for GitHub's documented workflow gates."""
import ast
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parent


class WorkflowRenderingTests(unittest.TestCase):
    def test_step_context_and_run_limit(self):
        workflow = (ROOT / "worker35-evidence-recovery.yml").read_text()
        parsed = yaml.safe_load(workflow)
        job = parsed["jobs"]["metadata-recovery"]
        self.assertEqual(job["defaults"], {"run": {"shell": "bash"}})
        self.assertEqual(job["steps"][0]["working-directory"], "${{ runner.temp }}")
        self.assertLessEqual(len(job["steps"][0]["run"]), 21000)
        defaults = workflow.split("    defaults:\n", 1)[1].split("    steps:\n", 1)[0]
        self.assertNotIn("runner.", defaults)
        self.assertIn("        id: inspect\n        working-directory: ${{ runner.temp }}\n", workflow)
        block = workflow.split("        run: |\n", 1)[1].split("      - name: Upload", 1)[0]
        command = "\n".join(line[10:] for line in block.splitlines()) + "\n"
        self.assertEqual(command, job["steps"][0]["run"])
        self.assertLessEqual(len(command), 21000)
        self.assertTrue(command.startswith("set -euo pipefail\npython3 -I -B - <<'PY'\n"))

    def test_compaction_preserves_entire_python_ast(self):
        source = (ROOT / "inspect_worker35_recovery.py").read_text().rsplit('if __name__ == "__main__":', 1)[0]
        builder = ast.parse((ROOT / "build_workflow.py").read_text())
        assignment = next(node for node in builder.body if isinstance(node, ast.Assign)
                          and any(isinstance(target, ast.Name) and target.id == "bootstrap" for target in node.targets))
        bootstrap = ast.literal_eval(assignment.value)
        workflow = (ROOT / "worker35-evidence-recovery.yml").read_text()
        block = workflow.split("          python3 -I -B - <<'PY'\n", 1)[1].split("          PY\n", 1)[0]
        actual = "\n".join(line[10:] for line in block.splitlines())
        self.assertEqual(ast.dump(ast.parse(source + bootstrap), include_attributes=False),
                         ast.dump(ast.parse(actual), include_attributes=False))


if __name__ == "__main__":
    unittest.main()
