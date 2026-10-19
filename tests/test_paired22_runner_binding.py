"""Pure source and admission binding checks; no game or project import."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments" / "paired22"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RunnerBinding(unittest.TestCase):
    def test_closed_source_inventory(self):
        manifest = json.loads((EXP / "source-pins.json").read_bytes())
        self.assertEqual(manifest["schema"], "strategy22-source-pins-v1")
        self.assertEqual(manifest["commit"], "808457711c823a5f1d9e7469c8b057997176d63e")
        self.assertEqual(len(manifest["files"]), 39)
        self.assertEqual(sum(row["bytes"] for row in manifest["files"]), 262593)
        self.assertEqual(len({row["path"] for row in manifest["files"]}), 39)
        for row in manifest["files"]:
            raw = subprocess.check_output(["git", "show",
                                           manifest["commit"] + ":" + row["path"]],
                                          cwd=ROOT)
            self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()),
                             (row["bytes"], row["sha256"]))
            blob = b"blob " + str(len(raw)).encode() + b"\0" + raw
            self.assertEqual(hashlib.sha1(blob).hexdigest(), row["git_blob"])

    def test_new_subject_has_no_old_seed_or_admission_route(self):
        p = json.loads((EXP / "preregistration.json").read_bytes())
        self.assertEqual(p["seeds_proposed_not_allocated"], list(range(1000439, 1000447)))
        self.assertEqual(p["compressed_file_cap"], 64 * 1024 * 1024)
        self.assertEqual(p["scientific_games"], 0)
        driver = (EXP / "diagnostic.py").read_text()
        issuer = (EXP / "issuance.py").read_text()
        workflow = (ROOT / ".github/workflows/paired22.yml").read_text()
        self.assertNotRegex(driver + issuer + workflow, r"100043[1-8]")
        self.assertIn("github.event.pull_request.head.ref == 'codex/strategy22-evidence-cap'", workflow)
        self.assertIn("!contains(github.event.changes.body.from, 'PAIRED22_GO_JSON')", workflow)
        self.assertIn("github.head_ref != 'codex/strategy22-evidence-cap'",
                      (ROOT / ".github/workflows/test.yml").read_text())
        self.assertIn("ulimit -f 65536", workflow)

    def test_workflow_binds_exact_driver_and_inputs(self):
        workflow = (ROOT / ".github/workflows/paired22.yml").read_text()
        driver = (EXP / "diagnostic.py").read_text()
        for name, key in (("diagnostic.py", "DRIVER_SHA"),
                          ("source-pins.json", "MANIFEST_SHA"),
                          ("check_source_gate.py", "GATE_SHA")):
            self.assertIn(key + ": " + sha(EXP / name), workflow)
        for name in ("bounds.py", "codec.py", "issuance.py"):
            self.assertIn(sha(EXP / name), workflow)
        self.assertIn("CODEC_SHA = '" + sha(EXP / "codec.py") + "'", driver)
        self.assertIn("ISSUANCE_SHA = '" + sha(EXP / "issuance.py") + "'", driver)
        self.assertEqual(len(re.findall("PAIRED22_GO_JSON", workflow)), 4)
        self.assertEqual(subprocess.check_output(["git", "status", "--porcelain", "--",
                                                    "src/bandido_alcatraz"], cwd=ROOT), b"")


if __name__ == "__main__":
    unittest.main()
