"""Invented bytes only, plus bounded previously preserved metadata integration."""
import copy
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import recover_tails as r


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.workspace = self.base / 'repo'; self.workspace.mkdir()
        self.raw = self.base / 'bandido-quota-closure-development' / str(r.RUN) / '1'
        self.raw.mkdir(parents=True)
        self.transport = self.raw.with_name('1-transport'); self.transport.mkdir()
        self.dest = self.base / 'tail-recovery' / '999' / '1'
        self.sealed = {
            'call-results/pass-2/1000319.jsonl': b'invented call prefix\n',
            'decision-traces/pass-2/1000319.jsonl': b'invented trace prefix\n',
            'resource-metrics.jsonl': b'invented resource prefix\n',
            'unchanged.jsonl': b'opaque invented bytes, never parsed\n',
        }
        receipt = {'run_id': str(r.RUN), 'run_attempt': '1', 'expected_head': r.HEAD,
                   'freeze_sha256': r.FREEZE_SHA, 'status': 'execution_blocked', 'classification': None,
                   'source_before': {'head': r.HEAD, 'python_version': '3.11.16'},
                   'source_at_finalization': {'head': r.HEAD, 'python_version': '3.11.16'}}
        self.sealed['receipt.json'] = r.encode(receipt)
        self.current = dict(self.sealed)
        self.tails = {}
        for path, (_, name) in r.TAILS.items():
            self.current[path] += b'append-only invented tail\n'
            self.tails[path] = (len(self.current[path]), name)
        for path, data in self.current.items():
            target = self.raw / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        self.manifest = {'schema': 'worker35-artifact-manifest-v1', 'archive': {'sha256': r.ARCHIVE_SHA, 'size_bytes': 29742478},
                         'files': {p: {'sha256': r.digest(data), 'size_bytes': len(data)} for p, data in self.sealed.items()}}
        self.manifest_bytes = r.encode(self.manifest)
        (self.transport / 'artifact-manifest.json').write_bytes(self.manifest_bytes)
        self.patches = [patch.object(r, 'TAILS', self.tails), patch.object(r, 'FILE_COUNT', len(self.sealed)),
                        patch.object(r, 'MANIFEST_SHA', r.digest(self.manifest_bytes)),
                        patch.object(r, 'RECEIPT_SHA', r.digest(self.sealed['receipt.json']))]
        for p in self.patches: p.start()
        self.ready = []

    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        for root, _, files in os.walk(self.base):
            os.chmod(root, 0o700)
            for name in files:
                path = Path(root) / name
                if not path.is_symlink(): os.chmod(path, 0o600)
        self.tmp.cleanup()

    def recover(self):
        return r.snapshot_tails(self.workspace, self.dest, {'recovery_job': {'run_id': 999, 'head_sha': 'b' * 40}}, on_ready=lambda *args: self.ready.append(args))

    def test_exact_three_copies_all_other_hashes_and_two_passes(self):
        before = {p: ((self.raw / p).read_bytes(), r.stamp((self.raw / p).stat())) for p in self.current}
        report, sha = self.recover()
        self.assertEqual(report['status'], 'local_tail_snapshot_verified')
        self.assertEqual(report['files_hashed'], 5)
        self.assertEqual(report['raw_bytes_read'], 2 * sum(map(len, self.current.values())))
        self.assertEqual(report['issues'], [])
        self.assertFalse(report['raw_tree_quiescence_proven'])
        self.assertFalse(report['remote_artifact_bytes_verified'])
        self.assertEqual(r.digest((self.dest / 'recovery-report.json').read_bytes()), sha)
        for path, (_, name) in self.tails.items(): self.assertEqual((self.dest / name).read_bytes(), self.current[path])
        self.assertFalse((self.dest / 'unchanged.jsonl').exists())
        self.assertFalse((self.dest / 'receipt.json').exists())
        for path, value in before.items(): self.assertEqual(((self.raw / path).read_bytes(), r.stamp((self.raw / path).stat())), value)
        self.assertEqual(len(list(self.dest.iterdir())), 7)
        path, records, locations = self.ready[0]
        r.verify_upload(path, r.encode(records), r.encode(locations))

    def test_prefix_mismatch_preserves_all_three_and_reports_contradiction(self):
        path = next(iter(self.tails))
        (self.raw / path).write_bytes(b'X' + self.current[path][1:])
        report, _ = self.recover()
        self.assertEqual(report['status'], 'preserved_with_contradictions')
        self.assertIn({'path': path, 'reason': 'sealed_prefix_hash_mismatch'}, report['issues'])
        self.assertTrue(all((self.dest / name).exists() for _, name in self.tails.values()))
        self.assertEqual(len(self.ready), 1)
        self.assertIsNone(report['classification'])

    def test_other_file_hash_mismatch_preserves_copies_and_reports(self):
        (self.raw / 'unchanged.jsonl').write_bytes(b'X' * len(self.current['unchanged.jsonl']))
        report, _ = self.recover()
        self.assertEqual(report['status'], 'preserved_with_contradictions')
        self.assertEqual(report['issues'], [{'path': 'unchanged.jsonl', 'reason': 'non_tail_hash_differs_from_sealed_manifest'}])
        self.assertTrue(all((self.dest / name).exists() for _, name in self.tails.values()))

    def test_wrong_tail_size_fails_closed_and_reports(self):
        path = next(iter(self.tails)); (self.raw / path).write_bytes(b'wrong size')
        report, _ = self.recover()
        self.assertEqual(report['status'], 'preservation_blocked')
        self.assertIn('size differs', report['reason'])
        self.assertTrue((self.dest / 'recovery-report.json').exists())

    def test_extra_file_population_blocked_without_read(self):
        (self.raw / 'unrelated.secret').write_bytes(b'never open')
        report, _ = self.recover()
        self.assertEqual(report['status'], 'preservation_blocked')
        self.assertEqual(report['raw_bytes_read'], 0)

    def test_missing_file_population_blocked(self):
        (self.raw / 'unchanged.jsonl').unlink()
        report, _ = self.recover()
        self.assertEqual(report['status'], 'preservation_blocked')
        self.assertEqual(report['raw_bytes_read'], 0)

    def test_symlink_hardlink_fifo_refused(self):
        path = self.raw / 'unchanged.jsonl'; path.unlink(); path.symlink_to(self.raw / 'receipt.json')
        report, _ = self.recover()
        self.assertEqual(report['status'], 'preservation_blocked')
        self.assertEqual(report['raw_bytes_read'], 0)

    def test_hardlink_refused(self):
        os.link(self.raw / 'unchanged.jsonl', self.base / 'outside')
        report, _ = self.recover()
        self.assertEqual(report['status'], 'preservation_blocked')

    def test_fifo_refused_without_hanging(self):
        path = self.raw / 'unchanged.jsonl'; path.unlink(); os.mkfifo(path)
        report, _ = self.recover()
        self.assertEqual(report['status'], 'preservation_blocked')

    def test_manifest_identity_mismatch(self):
        (self.transport / 'artifact-manifest.json').write_bytes(self.manifest_bytes + b' ')
        report, _ = self.recover()
        self.assertEqual(report['status'], 'preservation_blocked')
        self.assertEqual(report['raw_bytes_read'], 0)

    def test_original_receipt_identity_mismatch(self):
        (self.raw / 'receipt.json').write_bytes(b'changed')
        report, _ = self.recover()
        self.assertEqual(report['status'], 'preservation_blocked')
        self.assertEqual(report['raw_bytes_read'], 0)

    def test_mutation_between_passes_keeps_first_copies(self):
        original_hash = r.hash_one
        trigger = next(iter(self.tails))
        def hashing(root, path, *args, **kwargs):
            value = original_hash(root, path, *args, **kwargs)
            if path == trigger and kwargs.get('not_used') is None:
                target = self.raw / path
                target.write_bytes(b'X' * len(self.current[path]))
            return value
        with patch.object(r, 'hash_one', hashing): report, _ = self.recover()
        self.assertEqual(report['status'], 'preservation_blocked')
        self.assertEqual((self.dest / self.tails[trigger][1]).read_bytes(), self.current[trigger])
        self.assertTrue(self.ready)

    def test_read_cap_is_enforced_and_existing_copies_retained(self):
        with patch.object(r, 'READ_LIMIT', sum(map(len, self.current.values())) + 1): report, _ = self.recover()
        self.assertEqual(report['status'], 'preservation_blocked')
        self.assertIn('budget', report['reason'])
        self.assertTrue(all((self.dest / name).exists() for _, name in self.tails.values()))

    def test_existing_destination_not_overwritten(self):
        self.dest.mkdir(parents=True); sentinel = self.dest / 'keep'; sentinel.write_bytes(b'keep')
        report, _ = self.recover()
        self.assertEqual(report['status'], 'preservation_blocked')
        self.assertEqual(sentinel.read_bytes(), b'keep')
        self.assertEqual(list(self.dest.iterdir()), [sentinel])

    def test_upload_restore_attack_detected(self):
        self.recover()
        path, records, locations = self.ready[0]
        target = path / next(iter(self.tails.values()))[1]
        original = target.read_bytes(); mode = stat.S_IMODE(target.stat().st_mode)
        target.chmod(0o600)
        target.write_bytes(b'X' * len(original)); target.write_bytes(original); target.chmod(mode)
        with self.assertRaisesRegex(r.Blocked, 'stamp changed'):
            r.verify_upload(path, r.encode(records), r.encode(locations))

    def test_injected_hardlink_never_changes_original_mode_or_bytes(self):
        source = self.raw / next(iter(self.tails))
        source.chmod(0o640)
        before = source.read_bytes(), stat.S_IMODE(source.stat().st_mode)
        original_capture = r.capture_upload
        def capture(destination, fd, expected, allow_partial):
            target = destination / next(iter(self.tails.values()))[1]
            target.unlink(); os.link(source, target)
            return original_capture(destination, fd, expected, allow_partial)
        with patch.object(r, 'capture_upload', capture):
            with self.assertRaisesRegex(r.Blocked, 'single-link'):
                self.recover()
        self.assertEqual((source.read_bytes(), stat.S_IMODE(source.stat().st_mode)), before)
        self.assertEqual(self.ready, [])

    def test_staging_overwrite_before_capture_cannot_create_new_baseline(self):
        original_capture = r.capture_upload
        def capture(destination, fd, expected, allow_partial):
            target = destination / next(iter(self.tails.values()))[1]
            target.write_bytes(b'X' * target.stat().st_size)
            return original_capture(destination, fd, expected, allow_partial)
        with patch.object(r, 'capture_upload', capture):
            with self.assertRaisesRegex(r.Blocked, 'staged bytes differ'):
                self.recover()
        self.assertEqual(self.ready, [])

    def test_expected_tail_missing_before_capture_rejected(self):
        original_capture = r.capture_upload
        def capture(destination, fd, expected, allow_partial):
            (destination / 'resource-metrics.jsonl').unlink()
            return original_capture(destination, fd, expected, allow_partial)
        with patch.object(r, 'capture_upload', capture):
            with self.assertRaisesRegex(r.Blocked, 'unsafe upload files'):
                self.recover()
        self.assertEqual(self.ready, [])

    def test_expected_metadata_missing_before_capture_rejected(self):
        original_capture = r.capture_upload
        def capture(destination, fd, expected, allow_partial):
            (destination / 'authenticated-actions-metadata.json').unlink()
            return original_capture(destination, fd, expected, allow_partial)
        with patch.object(r, 'capture_upload', capture):
            with self.assertRaisesRegex(r.Blocked, 'unsafe upload files'):
                self.recover()
        self.assertEqual(self.ready, [])


class Metadata(unittest.TestCase):
    def test_real_accepted_manifest_contract_only(self):
        path = Path('/workspace/scratch/0fc3873a7042/attachments/73488263-c5b2-4339-9a34-8b269e405968/github-actions-artifact-11267680208.zip')
        if not path.exists(): self.skipTest('bounded metadata artifact unavailable')
        self.assertLess(path.stat().st_size, 2 * r.MIB)
        self.assertEqual(r.digest(path.read_bytes()), '997b08dfc564d4f87784e17a8e1b826df1acfb2a55700510ab61ff646508c6b5')
        with zipfile.ZipFile(path) as z:
            self.assertLess(z.getinfo('artifact-manifest.json').file_size, r.MANIFEST_LIMIT)
            raw = z.read('artifact-manifest.json'); manifest = r.parse(raw)
            self.assertEqual(r.digest(raw), r.MANIFEST_SHA)
            self.assertEqual(len(manifest['files']), r.FILE_COUNT)
            self.assertEqual(manifest['archive'], {'sha256': r.ARCHIVE_SHA, 'size_bytes': 29742478})
            self.assertEqual([manifest['files'][p]['size_bytes'] for p in r.TAILS], [164314, 124263, 14403921])
            for p, (size, _) in r.TAILS.items(): self.assertGreater(size, manifest['files'][p]['size_bytes'])
            receipt = r.parse(z.read('original-receipt.json'))
            self.assertEqual(receipt['run_id'], str(r.RUN)); self.assertEqual(receipt['run_attempt'], '1')

    def test_relative_paths_and_json_rejected(self):
        for value in ('../outside', '/outside', 'a//b', 'a/./b', '', '.', 'a\nb'):
            with self.assertRaises(r.Blocked): r.relative_parts(value)
        with self.assertRaises(r.Blocked): r.parse(b'{"a":1,"a":2}')


if __name__ == '__main__':
    unittest.main()
