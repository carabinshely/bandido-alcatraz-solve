"""Pure runner binding checks. No Bandido imports or local games."""

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
from random import Random
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "paired24"


class Paired24Engineering(unittest.TestCase):
    def test_first_issue_rejects_earlier_failed_run_despite_future_commit_time(self):
        self._first_issue_case(
            comment_updated="2026-10-19T16:00:00Z",
            runs=[(41, "2026-10-19T16:00:10Z", "completed", "failure"),
                  (42, "2026-10-19T16:00:20Z", "in_progress", None)],
            error="FIRST_RUN_ALREADY_SPENT",
        )

    def test_first_issue_ignores_only_completed_skipped_pre_go_runs(self):
        self._first_issue_case(
            comment_updated="2026-10-19T16:00:00Z",
            runs=[(40, "2026-10-19T15:50:00Z", "completed", "skipped"),
                  (42, "2026-10-19T16:00:20Z", "in_progress", None)],
            error=None,
        )

    def test_first_issue_rejects_comment_rewritten_after_run(self):
        self._first_issue_case(
            comment_updated="2026-10-19T16:00:30Z",
            runs=[(42, "2026-10-19T16:00:20Z", "in_progress", None)],
            error="FIRST_ISSUE_COMMENT_AFTER_RUN",
        )

    def test_first_issue_rejects_skipped_retry_of_prior_failed_run(self):
        self._first_issue_case(
            comment_updated="2026-10-19T16:00:00Z",
            runs=[(41, "2026-10-19T16:00:10Z", "completed", "skipped", 2),
                  (42, "2026-10-19T16:00:20Z", "in_progress", None)],
            error="FIRST_RUN_ALREADY_SPENT",
        )

    def _first_issue_case(self, *, comment_updated, runs, error):
        spec = importlib.util.spec_from_file_location("paired24_issuance", EXPERIMENT / "issuance.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        head = "a" * 40
        nonce = "b" * 64
        comment = dict(id=7, user={"login": "carabinshely"},
                       issue_url=module.BASE + "/issues/57",
                       created_at="2026-10-19T15:59:59Z", updated_at=comment_updated,
                       body="PAIRED24_FIRST_ISSUE_V1\n" + module.canonical(dict(
                           allocation=module.ALLOCATION, head=head, nonce=nonce,
                           root_intent="root", pr_number=57)).decode())
        rows = [dict(id=row[0], created_at=row[1], status=row[2], conclusion=row[3],
                     run_attempt=row[4] if len(row) == 5 else 1,
                     head_sha=head, event="pull_request", pull_requests=[{"number": 57}],
                     path=".github/workflows/paired24.yml")
                for row in runs]
        class Client:
            def request(self, method, path, data, label):
                return (200, [comment]) if label == "first_issue_comments" else (
                    200, dict(total_count=len(rows), workflow_runs=rows))
        call = lambda: module.validate_first_run(
            Client(), head=head, run_id="42", pr_number=57, root_intent="root",
            comment_id=7, nonce=nonce, global_created_at="2026-10-20T00:00:00Z")
        if error is None:
            self.assertEqual(call()["run_id"], "42")
        else:
            with self.assertRaisesRegex(ValueError, error):
                call()

    def test_exact_source_manifest_matches_committed_git_blobs(self):
        manifest = json.loads((EXPERIMENT / "source-pins.json").read_bytes())
        self.assertEqual(manifest["schema"], "strategy24-source-pins-v1")
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

    def test_counterfactual_reconstructs_unfiltered_v4_choice(self):
        tree = ast.parse((EXPERIMENT / "diagnostic.py").read_text())
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                        and n.name == "v4_counterfactual")
        scope = {"require": lambda condition, reason: condition or (_ for _ in ()).throw(ValueError(reason))}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "diagnostic.py", "exec"), scope)
        audit = {
            "roots": [
                {"move": {"hand_index": 0}, "score": 0},
                {"move": {"hand_index": 1}, "score": 10},
                {"move": {"hand_index": 2}, "score": 100000},
            ],
        }
        state = Random(7).getstate()
        self.assertEqual(scope["v4_counterfactual"](audit, state),
                         {"hand_index": 2})

    def test_new_workflow_is_inert_without_exact_go(self):
        workflow = (ROOT / ".github" / "workflows" / "paired24.yml").read_text()
        issuance = (EXPERIMENT / "issuance.py").read_text()
        diagnostic = (EXPERIMENT / "diagnostic.py").read_text()
        self.assertIn("github.event.action == 'edited'", workflow)
        self.assertIn("PAIRED24_GO_JSON", workflow)
        self.assertIn("codex/strategy24-fourpair", workflow)
        self.assertIn("strategy24-source-pins-v1", diagnostic)
        self.assertIn("SEEDS = tuple(range(1000463, 1000467))", diagnostic)
        self.assertIn('ALLOCATION = "bandido-seeds-1000463-1000466"', issuance)
        self.assertNotIn("PAIRED22_GO_JSON", workflow)

    def test_general_ci_skips_this_branch_before_science_go(self):
        workflow = (ROOT / ".github" / "workflows" / "test.yml").read_text()
        self.assertIn("github.head_ref != 'codex/strategy24-fourpair'", workflow)

    def test_four_pair_subject_and_checked_runtime_hashes(self):
        workflow = (ROOT / ".github" / "workflows" / "paired24.yml").read_text()
        driver = (EXPERIMENT / "diagnostic.py").read_text()
        prereg = json.loads((EXPERIMENT / "preregistration.json").read_bytes())
        self.assertEqual(prereg["seeds_proposed_not_allocated"],
                         [1000463, 1000464, 1000465, 1000466])
        self.assertEqual((prereg["pairs"], prereg["games"]), (4, 8))
        self.assertIn("SEEDS = tuple(range(1000463, 1000467))", driver)
        self.assertIn("BoundedMergeV4Policy(setup_weight=250)", driver)
        self.assertNotIn("LateClosurePolicy", driver)
        for name in ("diagnostic.py", "source-pins.json", "check_source_gate.py",
                     "issuance.py", "codec.py", "bounds.py"):
            committed = subprocess.check_output(
                ["git", "show", "HEAD:experiments/paired24/" + name], cwd=ROOT)
            sha = hashlib.sha256(committed).hexdigest()
            self.assertIn(sha, workflow if name in ("diagnostic.py", "source-pins.json",
                                                 "check_source_gate.py") else workflow + driver)


if __name__ == "__main__":
    unittest.main()
