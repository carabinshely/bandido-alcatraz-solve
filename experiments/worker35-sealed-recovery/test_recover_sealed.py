"""Synthetic transport/metadata tests only. No project imports or game calls."""
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import recover_sealed as r


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.workspace = self.base / "repo"
        self.workspace.mkdir()
        self.original = self.base / "bandido-quota-closure-development" / str(r.RUN) / "1"
        self.original.mkdir(parents=True)
        self.transport = self.original.with_name("1-transport")
        self.transport.mkdir()
        self.guard = self.original.parent.parent / ".admitted-heads" / r.HEAD
        self.guard.mkdir(parents=True)
        self.dest = self.base / "recovery" / "999" / "1"
        receipt = {"expected_head": r.HEAD, "run_id": str(r.RUN), "run_attempt": "1",
                   "freeze_sha256": r.FREEZE_SHA, "status": "execution_blocked",
                   "classification": None, "research_interpretation_performed": False,
                   "elapsed": 3.5}
        for key in ("source_before", "source_at_initialization", "source_at_finalization"):
            receipt[key] = {"head": r.HEAD, "tree": "a" * 40, "python_version": "3.11.16"}
        self.receipt = r.encode(receipt)
        self.receipt += b" " * (160722 - len(self.receipt))
        self.admission = r.encode({"expected_head": r.HEAD, "run_id": str(r.RUN), "run_attempt": "1", "freeze_sha256": r.FREEZE_SHA})
        (self.original / "receipt.json").write_bytes(self.receipt)
        (self.guard / "admission.json").write_bytes(self.admission)
        self.name = "evidence.part-00001"
        self.data = b"Synthetic sealed bytes: not a game or archive re-creation.\n" * 100
        (self.transport / self.name).write_bytes(self.data)
        self.manifest = {"schema": "worker35-artifact-manifest-v1", "format": "concatenated-zip-deflate6", "shard_bytes": r.PART_LIMIT,
                         "files": {"receipt.json": {"sha256": r.digest(self.receipt), "size_bytes": len(self.receipt)}},
                         "archive": {"sha256": r.digest(self.data), "size_bytes": len(self.data)},
                         "parts": [{"name": self.name, "sha256": r.digest(self.data), "size_bytes": len(self.data)}]}
        self.save_manifest()
        self.metadata = {"recovery_job": {"run_id": 999, "head_sha": "b" * 40}}
        self.patch_receipt = patch.object(r, "RECEIPT_SHA", r.digest(self.receipt))
        self.patch_admission = patch.object(r, "ADMISSION_SHA", r.digest(self.admission))
        self.patch_receipt.start()
        self.patch_admission.start()

    def tearDown(self):
        self.patch_receipt.stop()
        self.patch_admission.stop()
        for root, dirs, files in os.walk(self.base):
            os.chmod(root, 0o700)
            for name in files:
                p = Path(root) / name
                if not p.is_symlink():
                    os.chmod(p, 0o600)
        self.tmp.cleanup()

    def save_manifest(self):
        (self.transport / "artifact-manifest.json").write_bytes(r.encode(self.manifest))

    def recover(self, **kwargs):
        return r.snapshot(self.workspace, self.dest, self.metadata, **kwargs)

    def assert_blocked(self):
        with self.assertRaises((r.Blocked, OSError)):
            self.recover()
        self.assertTrue((self.dest / "metadata/blocked-report.json").exists())

    def test_snapshot_is_byte_exact_and_preserves_sources(self):
        originals = {p: (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_mode) for p in self.transport.iterdir()}
        ready = []
        report, sha = self.recover(on_metadata=lambda *args: ready.append(args))
        self.assertEqual(report["status"], "sealed_snapshot_verified")
        self.assertFalse(report["archive_member_consistency_verified"])
        self.assertFalse(report["raw_tree_quiescence_proven"])
        self.assertIn("omit later bytes", report["known_preservation_gap"])
        self.assertEqual((self.dest / "parts" / self.name).read_bytes(), self.data)
        self.assertEqual((self.dest / "metadata/original-receipt.json").read_bytes(), self.receipt)
        self.assertEqual(r.digest((self.dest / "metadata/recovery-report.json").read_bytes()), sha)
        self.assertEqual(ready[0][0], self.dest / "metadata")
        r.check_metadata(self.dest, r.encode(ready[0][1]), json.dumps(ready[0][2]))
        self.assertEqual(stat.S_IMODE(self.dest.stat().st_mode), 0o500)
        for path, before in originals.items():
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns, path.stat().st_mode), before)

    def test_existing_destination_refused_without_writes(self):
        self.dest.mkdir(parents=True)
        with self.assertRaises(r.Blocked): self.recover()
        self.assertEqual(list(self.dest.iterdir()), [])

    def test_part_symlink_refused(self):
        (self.transport / self.name).unlink()
        (self.transport / self.name).symlink_to(self.original / "receipt.json")
        self.assert_blocked()

    def test_part_hardlink_refused(self):
        os.link(self.transport / self.name, self.base / "second-link")
        self.assert_blocked()

    def test_part_fifo_refused_without_hanging(self):
        (self.transport / self.name).unlink()
        os.mkfifo(self.transport / self.name)
        self.assert_blocked()

    def test_symlink_ancestor_refused(self):
        alias = self.base / "alias"
        alias.symlink_to(self.transport, target_is_directory=True)
        with self.assertRaises(OSError): r.open_dir(alias)

    def test_unrelated_transport_entry_refused(self):
        (self.transport / "unrelated.secret").write_bytes(b"not read")
        self.assert_blocked()

    def test_receipt_changed_since_prior_recovery_refused(self):
        (self.original / "receipt.json").write_bytes(b"changed")
        self.assert_blocked()

    def test_source_hash_mismatch_refused(self):
        (self.transport / self.name).write_bytes(b"mismatch")
        self.assert_blocked()

    def test_concatenated_hash_mismatch_refused(self):
        self.manifest["archive"]["sha256"] = "f" * 64
        self.save_manifest()
        self.assert_blocked()
        self.assertTrue((self.dest / "parts" / self.name).exists())

    def test_source_mutation_after_copy_detected_and_partial_bytes_retained(self):
        original_write = r.write_new
        def write(fd, name, data):
            original_write(fd, name, data)
            if name == self.name:
                (self.transport / name).write_bytes(b"X" * len(data))
        with patch.object(r, "write_new", write): self.assert_blocked()
        self.assertEqual((self.dest / "parts" / self.name).read_bytes(), self.data)

    def test_source_manifest_mutation_detected(self):
        original_write = r.write_new
        def write(fd, name, data):
            original_write(fd, name, data)
            if name == self.name:
                (self.transport / "artifact-manifest.json").write_bytes(r.encode(self.manifest) + b" ")
        with patch.object(r, "write_new", write): self.assert_blocked()

    def test_snapshot_rehash_detects_changed_copy(self):
        original_write = r.write_new
        def write(fd, name, data):
            original_write(fd, name, b"Y" * len(data) if name == self.name else data)
        with patch.object(r, "write_new", write): self.assert_blocked()

    def test_blocked_report_is_bounded_and_exposed_for_upload(self):
        self.manifest["archive"]["sha256"] = "f" * 64
        self.save_manifest()
        ready = []
        with self.assertRaises(r.Blocked): self.recover(on_metadata=lambda *args: ready.append(args))
        self.assertEqual(ready[0][0], self.dest / "metadata")
        report = json.loads((self.dest / "metadata/blocked-report.json").read_bytes())
        self.assertIsNone(report["classification"])
        self.assertTrue(report["partial_snapshot_must_not_be_treated_as_verified"])

    def test_upload_part_uses_report_pin_and_recovery_identity(self):
        _, sha = self.recover()
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "999", "GITHUB_SHA": "b" * 40}):
            self.assertEqual(r.check_part(self.dest, self.name, sha)["status"], "sealed_snapshot_verified")
            with self.assertRaises(r.Blocked): r.check_part(self.dest, self.name, "0" * 64)
            with self.assertRaises(r.Blocked): r.check_part(self.dest, "../receipt.json", sha)
            with patch.dict(os.environ, {"GITHUB_RUN_ID": "998"}):
                with self.assertRaises(r.Blocked): r.check_part(self.dest, self.name, sha)

    def test_post_upload_changed_part_detected(self):
        _, sha = self.recover()
        path = self.dest / "parts" / self.name
        path.chmod(0o600)
        path.write_bytes(b"bad")
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "999", "GITHUB_SHA": "b" * 40}):
            with self.assertRaises(r.Blocked): r.check_part(self.dest, self.name, sha)

    def test_post_upload_write_restore_detected_by_stamp(self):
        _, sha = self.recover()
        path = self.dest / "parts" / self.name
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "999", "GITHUB_SHA": "b" * 40}):
            r.check_part(self.dest, self.name, sha)
            path.chmod(0o600)
            path.write_bytes(b"X" * len(self.data))
            path.write_bytes(self.data)
            path.chmod(0o400)
            with self.assertRaisesRegex(r.Blocked, "stamp changed"):
                r.check_part(self.dest, self.name, sha)

    def test_metadata_write_restore_and_unexpected_file_detected(self):
        ready = []
        self.recover(on_metadata=lambda *args: ready.append(args))
        path, records, observed = ready[0]
        records, observed = r.encode(records), json.dumps(observed)
        r.check_metadata(self.dest, records, observed)
        target = path / "original-admission.json"
        data = target.read_bytes()
        target.chmod(0o600)
        target.write_bytes(b"X" * len(data))
        target.write_bytes(data)
        target.chmod(0o400)
        with self.assertRaisesRegex(r.Blocked, "metadata bytes or stamps changed"):
            r.check_metadata(self.dest, records, observed)
        path.chmod(0o700)
        (path / "unexpected.secret").write_bytes(b"not to upload")
        with self.assertRaises(r.Blocked): r.check_metadata(self.dest, records, observed)

    def test_snapshot_destination_rename_restore_detected(self):
        _, sha = self.recover()
        renamed = self.dest.with_name("old")
        self.dest.rename(renamed)
        self.dest.mkdir()
        (self.dest / "parts").mkdir()
        (self.dest / "parts" / self.name).write_bytes(b"wrong temporary upload")
        (self.dest / "parts" / self.name).unlink()
        (self.dest / "parts").rmdir()
        self.dest.rmdir()
        renamed.rename(self.dest)
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "999", "GITHUB_SHA": "b" * 40}):
            with self.assertRaisesRegex(r.Blocked, "snapshot location changed"):
                r.check_part(self.dest, self.name, sha)

    def test_manifest_rejects_path_sizes_counts_and_format(self):
        modifications = [
            lambda m: m.update(shard_bytes=31 * r.MIB),
            lambda m: m["parts"][0].update(name="../escape"),
            lambda m: m["parts"][0].update(size_bytes=r.PART_LIMIT + 1),
            lambda m: m["archive"].update(size_bytes=r.ARCHIVE_LIMIT + 1),
            lambda m: m.update(parts=[]),
            lambda m: m["parts"].append(dict(m["parts"][0], name="evidence.part-00002")),
            lambda m: m["files"].update({"../../outside": {"sha256": "a" * 64, "size_bytes": 2}}),
            lambda m: m.update(format="other"),
            lambda m: m["files"]["receipt.json"].update(sha256="f" * 64),
            lambda m: m["parts"][0].update(size_bytes=True),
        ]
        for modify in modifications:
            with self.subTest(modify=modify):
                m = copy.deepcopy(self.manifest)
                modify(m)
                with self.assertRaises(r.Blocked): r.manifest_check(m)


class Validation(unittest.TestCase):
    def test_actual_bounded_recovered_metadata_contract(self):
        path = Path("/workspace/scratch/0fc3873a7042/attachments/ec8706c7-c34e-4e5b-a891-f13ef1517712/github-actions-artifact-11266298223.zip")
        if not path.exists():
            self.skipTest("previously downloaded bounded metadata artifact unavailable")
        self.assertLessEqual(path.stat().st_size, 2 * r.MIB)
        self.assertEqual(r.digest(path.read_bytes()), "ddfb0ba99622d8ea4c30c7c7e73b02059aa43b76207e777ffad18fc590ddb6a7")
        with zipfile.ZipFile(path) as archive:
            def bounded(name):
                self.assertLessEqual(archive.getinfo(name).file_size, r.MANIFEST_LIMIT)
                return archive.read(name)
            receipt_raw = bounded("inspection/original-receipt.json")
            admission_raw = bounded("inspection/original-admission.json")
            self.assertEqual(r.digest(receipt_raw), r.RECEIPT_SHA)
            self.assertEqual(r.digest(admission_raw), r.ADMISSION_SHA)
            receipt, admission = r.parse(receipt_raw), r.parse(admission_raw)
            r.source_metadata(receipt, admission)
            metadata = r.parse(bounded("authenticated-actions-metadata.json"))
            r.validate_original(metadata["run"], metadata["job"])
            for key, value in (("run_id", r.RUN), ("run_attempt", 1), ("run_attempt", True)):
                altered = dict(receipt, **{key: value})
                with self.assertRaises(r.Blocked): r.source_metadata(altered, admission)

    def test_json_duplicate_nonfinite_rejected_finite_preserved(self):
        for value in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":1e999}'):
            with self.assertRaises(r.Blocked): r.parse(value)
        self.assertEqual(r.parse(b'{"elapsed":3.5}'), {"elapsed": 3.5})

    def test_noncanonical_paths_rejected(self):
        for path in ("relative", "/a/../b", "/a//b", "/a/./b", "/a\nb", "/a/*"):
            with self.assertRaises(r.Blocked): r.canonical_path(path)

    def job(self):
        return {"name": "sealed-snapshot", "run_id": 999, "run_attempt": 1, "head_sha": "b" * 40,
                "status": "in_progress", "runner_id": 2, "runner_name": r.RUNNER}

    def env(self):
        return {"GITHUB_REPOSITORY": r.REPO, "GITHUB_EVENT_NAME": "push", "GITHUB_REF": r.BRANCH,
                "GITHUB_ACTOR": "carabinshely", "GITHUB_RUN_ATTEMPT": "1", "RUNNER_NAME": r.RUNNER,
                "GITHUB_RUN_ID": "999", "GITHUB_SHA": "b" * 40, "EXPECTED_JOB_NAME": "sealed-snapshot"}

    def test_registered_runner_id_required(self):
        for runner_id in (2, 3):
            job = self.job(); job["runner_id"] = runner_id
            with patch.dict(os.environ, self.env()), patch.object(r, "api", return_value={"jobs": [job], "total_count": 1}):
                if runner_id == 2: self.assertEqual(r.current_job(), job)
                else:
                    with self.assertRaises(r.Blocked): r.current_job()

    def test_original_attempt_rerun_wrong_branch_wrong_actor_blocked(self):
        for key, value in (("GITHUB_RUN_ATTEMPT", "2"), ("GITHUB_REF", "refs/heads/main"), ("GITHUB_ACTOR", "someone"), ("GITHUB_RUN_ID", str(r.RUN))):
            env = self.env(); env[key] = value
            with patch.dict(os.environ, env), patch.object(r, "api") as api:
                with self.assertRaises(r.Blocked): r.current_job()
                api.assert_not_called()

    def test_current_job_pagination(self):
        pages = [{"jobs": [{"name": "other"}] * 100, "total_count": 102}, {"jobs": [self.job()], "total_count": 102}]
        with patch.dict(os.environ, self.env()), patch.object(r, "api", side_effect=pages):
            self.assertEqual(r.current_job(), self.job())

    def test_original_metadata_packaging_success_required(self):
        run = {"id": r.RUN, "run_attempt": 1, "head_sha": r.HEAD, "repository": {"full_name": r.REPO},
               "path": ".github/workflows/quota-reserve-closure-development.yml", "status": "completed", "conclusion": "failure"}
        job = {"id": r.JOB, "run_id": r.RUN, "run_attempt": 1, "head_sha": r.HEAD, "runner_id": 2,
               "runner_name": r.RUNNER, "status": "completed", "conclusion": "failure", "steps": []}
        for name, conclusion in (("Three complete fixed development phases", "cancelled"), ("Reconcile final status", "failure"), ("Preserve deterministic evidence shards", "success"), ("Upload complete or partial evidence always", "failure")):
            job["steps"].append({"name": name, "status": "completed", "conclusion": conclusion})
        r.validate_original(run, job)
        job["steps"][2]["conclusion"] = "failure"
        with self.assertRaises(r.Blocked): r.validate_original(run, job)


if __name__ == "__main__":
    unittest.main()
