"""Pure runner binding checks. No Bandido imports or local games."""

import ast
import hashlib
import json
from pathlib import Path
from random import Random
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "paired23"


class Paired23Engineering(unittest.TestCase):
    def test_exact_source_manifest_matches_committed_git_blobs(self):
        manifest = json.loads((EXPERIMENT / "source-pins.json").read_bytes())
        self.assertEqual(manifest["schema"], "strategy23-source-pins-v1")
        self.assertEqual(manifest["commit"], "854bfbedbf80f79e88940cb3f7504ae11a4b2110")
        self.assertEqual(len(manifest["files"]), 41)
        self.assertEqual(sum(row["bytes"] for row in manifest["files"]), 272553)
        tree = subprocess.check_output(
            ["git", "show", "-s", "--format=%T", manifest["commit"]], cwd=ROOT
        ).decode().strip()
        self.assertEqual(tree, manifest["tree"])
        for row in manifest["files"]:
            blob = subprocess.check_output(["git", "cat-file", "blob", row["git_blob"]], cwd=ROOT)
            self.assertEqual(len(blob), row["bytes"])
            self.assertEqual(hashlib.sha256(blob).hexdigest(), row["sha256"])

    def test_counterfactual_changes_only_late_safe_domain_scoring(self):
        tree = ast.parse((EXPERIMENT / "diagnostic.py").read_text())
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                        and n.name == "late_counterfactual")
        scope = {"require": lambda condition, reason: condition or (_ for _ in ()).throw(ValueError(reason))}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "diagnostic.py", "exec"), scope)
        audit = {
            "roots": [
                {"move": {"hand_index": 0}, "score": 0},
                {"move": {"hand_index": 1}, "score": 10},
                {"move": {"hand_index": 2}, "score": 100000},
            ],
            "mobility": [
                {"after_open": 2}, {"after_open": 3}, {"after_open": 1},
            ],
            "tiers": {"safe": [0, 1]},
        }
        state = Random(7).getstate()
        self.assertEqual(scope["late_counterfactual"](audit, state, 3, 19),
                         {"hand_index": 1})
        self.assertEqual(scope["late_counterfactual"](audit, state, 3, 20),
                         {"hand_index": 0})

    def test_new_workflow_is_inert_without_exact_go(self):
        workflow = (ROOT / ".github" / "workflows" / "paired23.yml").read_text()
        issuance = (EXPERIMENT / "issuance.py").read_text()
        diagnostic = (EXPERIMENT / "diagnostic.py").read_text()
        self.assertIn("github.event.action == 'edited'", workflow)
        self.assertIn("PAIRED23_GO_JSON", workflow)
        self.assertIn("codex/strategy23-floor-ablation", workflow)
        self.assertIn("strategy23-source-pins-v1", diagnostic)
        self.assertIn("SEEDS = tuple(range(1000447, 1000463))", diagnostic)
        self.assertIn('ALLOCATION = "bandido-seeds-1000447-1000462"', issuance)
        self.assertNotIn("PAIRED22_GO_JSON", workflow)


if __name__ == "__main__":
    unittest.main()
