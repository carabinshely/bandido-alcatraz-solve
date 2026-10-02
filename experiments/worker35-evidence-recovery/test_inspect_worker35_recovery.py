"""Invented filesystem/process fixtures only. No project code, data, or games."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("recovery", Path(__file__).with_name("inspect_worker35_recovery.py"))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def process(self, pid=123, command=b"invented-idle\0", cwd=None, target=None, flags="0"):
        path = self.root / "proc" / str(pid)
        (path / "fd").mkdir(parents=True)
        (path / "fdinfo").mkdir()
        (path / "status").write_text(f"Name:\tinvented\nUid:\t{os.geteuid()}\t{os.geteuid()}\t{os.geteuid()}\t{os.geteuid()}\n")
        (path / "cmdline").write_bytes(command)
        (path / "cwd").symlink_to(cwd or self.root / "outside")
        (path / "maps").write_text("")
        if target:
            (path / "fd/4").symlink_to(target)
            (path / "fdinfo/4").write_text(f"flags:\t{flags}\n")
        return path

    def scan(self):
        return r.scan_processes(self.root / "proc", self.root / "checkout", self.root / "evidence", os.geteuid())

    def test_inventory_never_reads_contents_or_follows_symlink(self):
        evidence = self.root / "evidence"
        evidence.mkdir()
        (evidence / "unreadable-raw").write_bytes(b"invented raw evidence")
        (evidence / "unreadable-raw").chmod(0)
        (evidence / "outside-link").symlink_to(self.root / "outside")
        result = r.inventory(evidence)
        self.assertEqual(result["unreadable-raw"]["size_bytes"], 21)
        self.assertEqual(result["outside-link"]["type"], "symlink")
        self.assertEqual(len(result), 3)

    def test_receipt_bytes_unchanged(self):
        path = self.root / "receipt.json"
        raw = b'{"invented": true}\n'
        path.write_bytes(raw)
        result, before = r.read_bounded_regular(path, 100)
        self.assertEqual(result, raw)
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(before, r.stamp(path.lstat()))

    def test_reject_receipt_symlink_and_ancestor_symlink(self):
        real = self.root / "real"
        real.mkdir()
        (real / "receipt").write_text("{}")
        (self.root / "link").symlink_to(real, target_is_directory=True)
        (self.root / "receipt-link").symlink_to(real / "receipt")
        for path in (self.root / "link/receipt", self.root / "receipt-link"):
            with self.assertRaises(r.Blocked):
                r.read_bounded_regular(path, 100)

    def test_reject_oversize_without_truncation(self):
        path = self.root / "receipt"
        path.write_bytes(b"x" * 101)
        with self.assertRaises(r.Blocked):
            r.read_bounded_regular(path, 100)
        self.assertEqual(path.stat().st_size, 101)

    def test_exclusive_recovery_writes(self):
        path = self.root / "new-receipt"
        r.write_new(path, b"first")
        with self.assertRaises(FileExistsError):
            r.write_new(path, b"second")
        self.assertEqual(path.read_bytes(), b"first")

    def test_live_producer_detected_without_command_disclosure(self):
        self.process(command=b"python\0" + r.PRODUCER + b"\0run\0secret-argument")
        result = self.scan()
        self.assertEqual(result["finding"], "possible_live_writer")
        self.assertNotIn("secret-argument", json.dumps(result))
        self.assertIn("frozen_producer_entrypoint", result["matches"][0]["reasons"])

    def test_cwd_open_write_and_mapping_detected(self):
        process = self.process(cwd=self.root / "checkout", target=self.root / "evidence/receipt.json", flags="100002")
        (process / "maps").write_text(f"0-1 rw-s 0 0:0 0 {self.root}/evidence/raw.jsonl\n")
        result = self.scan()
        self.assertEqual(set(result["matches"][0]["reasons"]),
                         {"original_checkout_or_output_cwd", "output_writable_fd", "output_memory_mapping"})

    def test_missing_relevant_process_state_is_unknown(self):
        process = self.process()
        (process / "maps").unlink()
        self.assertEqual(self.scan()["finding"], "unknown")

    def test_negative_scan_does_not_claim_proof(self):
        self.process()
        result = self.scan()
        self.assertEqual(result["finding"], "no_scoped_writer_observed")
        self.assertIs(result["quiescence_proven"], False)

    def test_deadline_is_not_swallowed_by_process_scan(self):
        self.process()
        with patch.object(r, "proc_bytes", side_effect=r.InspectionDeadline("invented")):
            with self.assertRaises(r.InspectionDeadline):
                self.scan()

    def test_missing_boot_and_namespace_still_preserves_receipt(self):
        workspace = self.root / "checkout"
        workspace.mkdir()
        output = self.root / "bandido-quota-closure-development" / str(r.RUN_ID) / "1"
        output.mkdir(parents=True)
        receipt = json.dumps({"expected_head": r.HEAD, "run_id": str(r.RUN_ID), "run_attempt": "1", "status": "running"}).encode()
        (output / "receipt.json").write_bytes(receipt)
        proc = self.root / "proc"
        proc.mkdir()
        run = {"id": r.RUN_ID, "run_attempt": 1, "head_sha": r.HEAD,
               "repository": {"full_name": r.REPOSITORY}, "status": "completed", "conclusion": "failure",
               "path": ".github/workflows/quota-reserve-closure-development.yml"}
        job = {"id": r.JOB_ID, "run_id": r.RUN_ID, "run_attempt": 1, "head_sha": r.HEAD,
               "status": "completed", "conclusion": "failure", "runner_name": r.RUNNER, "runner_id": 456}
        result = r.inspect(workspace, self.root / "recovery", {"run": run, "job": job}, 456, proc)
        self.assertEqual(result["status"], "metadata_preserved_no_packaging_authorized_by_this_script")
        self.assertIsNone(result["boot_id"])
        self.assertIsNone(result["pid_namespace_matches_pid1"])
        self.assertEqual((self.root / "recovery/original-receipt.json").read_bytes(), receipt)
        self.assertEqual(sorted(p.name for p in output.iterdir()), ["receipt.json"])

    def test_different_uid_not_read_for_command(self):
        process = self.process(command=b"unrelated secret")
        (process / "status").write_text("Uid:\t123456\t123456\t123456\t123456\n")
        (process / "cmdline").unlink()
        result = self.scan()
        self.assertEqual(result["checked_relevant_processes"], 0)
        self.assertEqual(result["unknown"], [])

    def test_json_duplicate_keys_rejected(self):
        with self.assertRaises(r.Blocked):
            r.parse_object(b'{"same":1,"same":2}')

    def test_nonfinite_exponent_rejected(self):
        with self.assertRaises(r.Blocked):
            r.parse_object(b'{"value":1e999}')

    def test_inventory_symlink_swap_cannot_escape(self):
        evidence = self.root / "evidence"
        (evidence / "child").mkdir(parents=True)
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "private-name").write_text("invented")
        real_open = os.open
        def swap_open(path, flags, *args, **kwargs):
            if path == "child" and flags & os.O_DIRECTORY:
                (evidence / "child").rmdir()
                (evidence / "child").symlink_to(outside)
            return real_open(path, flags, *args, **kwargs)
        with patch.object(r.os, "open", swap_open):
            with self.assertRaises(OSError):
                r.inventory(evidence)

    def test_anchored_recovery_write_ignores_path_swap(self):
        recovery = self.root / "recovery"
        original = self.root / "original"
        original.mkdir()
        fd = r.open_directory(recovery, create=True)
        try:
            recovery.rename(self.root / "moved-recovery")
            recovery.symlink_to(original)
            r.write_new(recovery / "diagnostic.json", b"invented", directory_fd=fd)
        finally:
            os.close(fd)
        self.assertEqual(list(original.iterdir()), [])
        self.assertEqual((self.root / "moved-recovery/diagnostic.json").read_bytes(), b"invented")

    def test_fresh_directory_rejects_symlink_ancestor(self):
        original = self.root / "original"
        original.mkdir()
        (self.root / "redirect").symlink_to(original)
        with self.assertRaises(r.Blocked):
            r.open_directory(self.root / "redirect/recovery", create=True)
        self.assertEqual(list(original.iterdir()), [])

    def test_wrong_runner_or_run_rejected(self):
        run = {"id": r.RUN_ID, "run_attempt": 1, "head_sha": r.HEAD,
               "repository": {"full_name": r.REPOSITORY}, "status": "completed", "conclusion": "failure",
               "path": ".github/workflows/quota-reserve-closure-development.yml"}
        job = {"id": r.JOB_ID, "run_id": r.RUN_ID, "run_attempt": 1, "head_sha": r.HEAD,
               "status": "completed", "conclusion": "failure", "runner_name": r.RUNNER, "runner_id": 456}
        r.validate_metadata({"run": run, "job": job}, 456)
        with self.assertRaises(r.Blocked):
            r.validate_metadata({"run": run, "job": job}, 789)
        run["id"] += 1
        with self.assertRaises(r.Blocked):
            r.validate_metadata({"run": run, "job": job}, 456)


if __name__ == "__main__":
    unittest.main()
