"""Focused source binding checks; no project import, deck load, or game."""

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from random import Random


ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments" / "paired20"
SOURCE_HEAD = "7d740c82cd6f1be46ae01812c01de32ce2635d14"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class Paired20Bindings(unittest.TestCase):
    def test_preregistered_paired_analysis(self):
        tree = ast.parse((EXP / "diagnostic.py").read_text(encoding="utf-8"))
        target = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                      and node.name == "paired_analysis")
        scope = {}
        exec(compile(ast.Module(body=[target], type_ignores=[]), "analysis", "exec"), scope)

        def pair(control, candidate):
            return {"results": [
                {"arm": "control", "result": {"won": control},
                 "choice_changes": 0, "terminal_open_tunnels": 2},
                {"arm": "candidate", "result": {"won": candidate},
                 "choice_changes": 3, "terminal_open_tunnels": 1}]}

        analyze = scope["paired_analysis"]
        tied = analyze([pair(True, True), pair(False, False)])
        self.assertEqual(tied["exact_two_sided_binomial"],
                         {"numerator": 1, "denominator": 1})
        self.assertEqual(tied["paired_difference"], 0)
        one_sided = analyze([pair(False, True)] * 3)
        self.assertEqual(one_sided["exact_two_sided_binomial"],
                         {"numerator": 2, "denominator": 8})
        mixed = analyze([pair(True, True)] * 2 + [pair(False, False)] * 10
                        + [pair(True, False)] + [pair(False, True)] * 3)
        self.assertEqual(mixed["wins"], {"control": 3, "candidate": 5})
        self.assertEqual(mixed["paired_outcomes"],
                         {"both_win": 2, "both_loss": 10,
                          "control_only": 1, "candidate_only": 3})
        self.assertEqual(mixed["exact_two_sided_binomial"],
                         {"numerator": 10, "denominator": 16})
        self.assertEqual(mixed["choice_changes"], 48)
        self.assertEqual(mixed["terminal_open_tunnels"],
                         {"control": [2] * 16, "candidate": [1] * 16})

    def test_manifest_closed_source_inventory(self):
        manifest = json.loads((EXP / "source-pins.json").read_bytes())
        self.assertEqual((manifest["schema"], manifest["commit"]),
                         ("strategy20-source-pins-v1", SOURCE_HEAD))
        self.assertEqual(len(manifest["files"]), 35)
        self.assertEqual(sum(row["bytes"] for row in manifest["files"]), 242684)
        self.assertEqual(len({row["path"] for row in manifest["files"]}), 35)
        for row in manifest["files"]:
            self.assertTrue(row["path"].startswith("src/bandido_alcatraz/"))
            self.assertTrue(0 < row["bytes"] <= 32768)
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(row["git_blob"], r"^[0-9a-f]{40}$")
        candidate = next(row for row in manifest["files"]
                         if row["path"].endswith("/mobility_floor.py"))
        self.assertEqual(candidate["sha256"],
                         "f776d8fc96d46e800bbfeec43727aff838a820f085f30092560850db183e5548")

    def test_driver_calls_exact_mobility_policy_and_fixed_seed_population(self):
        code = (EXP / "diagnostic.py").read_text(encoding="utf-8")
        tree = ast.parse(code)
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        for cls in ("MobilityFloorPolicy", "MobilityFloorReference"):
            selected = [n for n in calls if isinstance(n.func, ast.Attribute)
                        and n.func.attr == cls]
            self.assertEqual(len(selected), 1)
            self.assertFalse(any(kw.arg == "min_open_override" for kw in selected[0].keywords))
        self.assertIn("SEEDS = tuple(range(1000423, 1000431))", code)
        self.assertIn("pairs=8, games=16", code)
        self.assertIn("WHOLE_SECONDS = 3600", code)
        self.assertIn("TOTAL_BYTES = 192 * 1024 * 1024", code)
        self.assertIn("manifest['commit'] == '" + SOURCE_HEAD + "'", code)
        self.assertNotIn("1000401", code)
        self.assertNotIn("paired18", code)

    def test_v4_counterfactual_uses_preserved_prechoice_state(self):
        tree = ast.parse((EXP / "diagnostic.py").read_text(encoding="utf-8"))
        target = next(node for node in tree.body
                      if isinstance(node, ast.FunctionDef) and node.name == "v4_counterfactual")
        scope = {"require": lambda ok, reason: ok or (_ for _ in ()).throw(ValueError(reason))}
        exec(compile(ast.Module(body=[target], type_ignores=[]), "counterfactual", "exec"), scope)
        rng = Random(31)
        before = rng.getstate()
        audit = {"roots": [{"move": {"id": "a"}, "score": 1},
                           {"move": {"id": "b"}, "score": 3},
                           {"move": {"id": "c"}, "score": 2}]}
        self.assertEqual(scope["v4_counterfactual"](audit, before), {"id": "b"})
        self.assertEqual(rng.getstate(), before)
        self.assertIsNone(scope["v4_counterfactual"]({"roots": []}, before))

    def test_one_shot_issuer_has_new_unique_allocation(self):
        code = (EXP / "issuance.py").read_text(encoding="utf-8")
        self.assertIn('ALLOCATION = "bandido-seeds-1000423-1000430"', code)
        self.assertIn('GLOBAL_BRANCH = "codex/seed-allocation-1000423-1000430"', code)
        self.assertIn("range(1000423, 1000431)", code)
        self.assertIn("PAIRED20_FIRST_ISSUE_V1", code)
        self.assertIn("PAIRED20_GO_JSON", code)
        self.assertIn('".github/workflows/paired20.yml"', code)
        self.assertIn("/actions/workflows/paired20.yml/runs?event=pull_request", code)
        self.assertIn("per_page=8", code)
        self.assertIn('listing["total_count"] <= 8', code)
        self.assertNotIn("1000401", code)
        self.assertNotIn("PAIRED18", code)

    def test_workflow_binds_current_hashes_and_skips_unadmitted_smoke(self):
        workflow = (ROOT / ".github/workflows/paired20.yml").read_text()
        old = (ROOT / ".github/workflows/test.yml").read_text()
        for filename, key in (("diagnostic.py", "DRIVER_SHA"),
                              ("source-pins.json", "MANIFEST_SHA"),
                              ("check_source_gate.py", "GATE_SHA")):
            self.assertIn(key + ": " + sha((EXP / filename).read_bytes()), workflow)
        for filename in ("bounds.py", "codec.py", "issuance.py"):
            self.assertIn(sha((EXP / filename).read_bytes()), workflow)
        self.assertIn("ISSUANCE_SHA = '" + sha((EXP / "issuance.py").read_bytes()) + "'",
                      (EXP / "diagnostic.py").read_text())
        self.assertIn("CODEC_SHA = '" + sha((EXP / "codec.py").read_bytes()) + "'",
                      (EXP / "diagnostic.py").read_text())
        self.assertIn("ref: " + SOURCE_HEAD, workflow)
        self.assertIn("head.ref == 'codex/strategy20-runner'", workflow)
        self.assertIn("timeout --signal=KILL 3620", workflow)
        self.assertIn("github.head_ref != 'codex/strategy20-runner'", old)
        self.assertNotIn("- run: python scripts/run_real_deck_smoke.py", workflow)
        self.assertEqual(len(re.findall(r"PAIRED20_GO_JSON", workflow)), 4)
        self.assertEqual(workflow.count("actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683"), 2)
        self.assertEqual(workflow.count("actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"), 1)
        self.assertNotIn("actions/checkout@v4", workflow)
        self.assertNotIn("actions/upload-artifact@v4", workflow)

    def test_reference_comparison_rejects_physical_call_divergence(self):
        tree = ast.parse((EXP / "diagnostic.py").read_text(encoding="utf-8"))
        checks = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                  and isinstance(n.func, ast.Name) and n.func.id == "require"
                  and len(n.args) == 2 and isinstance(n.args[1], ast.Constant)
                  and n.args[1].value == "FULL_REFERENCE_MISMATCH"]
        self.assertEqual(len(checks), 1)
        expr = compile(ast.Expression(checks[0].args[0]), "reference-parity", "eval")
        candidate_rng, reference_rng = Random(17), Random(17)
        values = dict(audit={"roots": []}, checked={"roots": []},
                      chosen="a", expected="a", move=lambda value: value,
                      operations={"previews": 1}, reference_operations={"previews": 1},
                      rng=candidate_rng, copied=reference_rng)
        self.assertTrue(eval(expr, {}, values))
        values["reference_operations"] = {"previews": 2}
        self.assertFalse(eval(expr, {}, values))

    def test_first_issue_uses_only_scoped_complete_workflow_history(self):
        spec = importlib.util.spec_from_file_location("paired20_issuer_pure", EXP / "issuance.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        head = "a" * 40
        nonce = "b" * 64
        pr = 53
        issue = {"id": 123, "created_at": "2026-10-17T10:00:01Z",
                 "issue_url": module.BASE + "/issues/53",
                 "user": {"login": "carabinshely"},
                 "body": "PAIRED20_FIRST_ISSUE_V1\n" + json.dumps({
                     "allocation": module.ALLOCATION, "head": head,
                     "nonce": nonce, "root_intent": "root", "pr_number": pr})}
        def row(number, path, when):
            return {"id": number, "head_sha": head, "event": "pull_request",
                    "path": ".github/workflows/" + path,
                    "created_at": when, "pull_requests": [{"number": pr}]}
        unrelated = [row(n, "test.yml", "2026-10-17T09:59:58Z")
                     for n in range(10, 18)]
        self.assertEqual(len(unrelated), 8)
        runs = [row(2, "paired20.yml", "2026-10-17T09:59:59Z"),
                row(5, "paired20.yml", "2026-10-17T10:00:03Z")]
        class Client:
            def request(self, method, path, data, label):
                assert method == "GET" and data is None
                if label == "first_issue_comments":
                    return 200, [issue]
                assert label == "first_issue_runs"
                assert path.startswith("/actions/workflows/paired20.yml/runs?")
                assert path.endswith("per_page=8")
                return 200, {"total_count": len(runs), "workflow_runs": runs}
        args = dict(head=head, run_id="5", pr_number=pr, root_intent="root",
                    comment_id=123, nonce=nonce,
                    global_created_at="2026-10-17T10:00:00Z")
        result = module.validate_first_run(Client(), **args)
        self.assertEqual(result["run_id"], "5")
        runs[0]["created_at"] = "2026-10-17T10:00:00Z"
        with self.assertRaisesRegex(ValueError, "FIRST_ISSUE_COMMENT_AFTER_RUN"):
            module.validate_first_run(Client(), **args)
        runs[0]["created_at"] = "2026-10-17T09:59:59Z"
        runs[1]["path"] = ".github/workflows/unreviewed.yml"
        with self.assertRaisesRegex(ValueError, "FIRST_ISSUE_RUN_PATH_UNKNOWN"):
            module.validate_first_run(Client(), **args)
        runs[1]["path"] = ".github/workflows/paired20.yml"
        runs[0]["created_at"] = "2026-10-17T10:00:02Z"
        with self.assertRaisesRegex(ValueError, "FIRST_RUN_ALREADY_SPENT"):
            module.validate_first_run(Client(), **args)


    def test_evidence_and_process_file_caps_fit_custody_reservation(self):
        codec = (EXP / "codec.py").read_text()
        driver = (EXP / "diagnostic.py").read_text()
        workflow = (ROOT / ".github/workflows/paired20.yml").read_text()
        prereg = json.loads((EXP / "preregistration.json").read_bytes())
        self.assertIn("COMPRESSED_BYTES = 3 * 1024 * 1024", codec)
        self.assertIn("FILE_BYTES = 3 * 1024 * 1024", driver)
        self.assertIn("TERMINAL_RESERVE = 524288", codec)
        self.assertIn("TERMINAL_RESERVE = 524288", driver)
        bounds = (EXP / "bounds.py").read_text()
        self.assertIn("TERMINAL_RESERVE = 524288", bounds)
        self.assertIn("ulimit -f 3072", workflow)
        self.assertIn("ulimit -f 128", workflow)
        self.assertIn("mkfifo", workflow)
        self.assertIn("capture-status.txt", workflow)
        self.assertIn('wait "$out_capture"', workflow)
        self.assertIn('wait "$err_capture"', workflow)
        self.assertIn('if (( out_status != 0 || err_status != 0 )); then', workflow)
        self.assertIn('exit 97', workflow)
        self.assertIn('trap \'rm -f -- "$out_fifo" "$err_fifo"\' EXIT', workflow)
        self.assertIn('> "$out_fifo" 2> "$err_fifo"', workflow)
        self.assertIn("            ulimit -f 64\n            timeout --signal=KILL 60", workflow)
        self.assertEqual(prereg["compressed_file_cap"], 3 * 1024 * 1024)
        self.assertEqual(prereg["terminal_reserve"], 524288)
        control_upper = (3 * 1024 * 1024 + 2 * 128 * 1024 + 2 * 65536 + 242684
                         + 9 * (65536 + 8192 + 1024) + 512 * 1024)
        self.assertEqual(control_upper, 4_978_684)
        self.assertIn("4,978,684-byte prospective upper", (EXP / "CONTRACT.md").read_text())
        # A private terminal packet upper needs separate proof; the 3 MiB
        # compressed evidence cap does not bound the whole packet to 3 MB.

    def test_precall_terminal_reserve_boundary(self):
        spec = importlib.util.spec_from_file_location("paired20_bounds_pure", EXP / "bounds.py")
        bounds = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bounds)
        total = 3 * 1024 * 1024
        bounds.reserve(0, total - 524288, total)
        with self.assertRaisesRegex(ValueError, "EVIDENCE_CAP_BEFORE_CALL_NO_TRUNCATION"):
            bounds.reserve(0, total - 524288 + 1, total)

    def test_terminal_reserve_accepts_maximum_journal_and_failure_context(self):
        spec = importlib.util.spec_from_file_location("paired20_codec_pure", EXP / "codec.py")
        codec = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(codec)
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / "evidence"
            evidence = codec.Evidence(folder)
            failure = {"journal": ["x" * 256 for _ in range(600)],
                       "traceback": "t" * 65536,
                       "completed_pairs": ["p" * 4096 for _ in range(8)]}
            evidence.write("failure.json", failure, terminal=True)
            evidence.finish()
            recovered = codec.decode((folder / "records.gz").read_bytes())
            self.assertEqual(json.loads(recovered["failure.json"]), failure)


if __name__ == "__main__":
    unittest.main()
