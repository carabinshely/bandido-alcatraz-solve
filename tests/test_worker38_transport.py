"""Finite offline tests requiring separately recorded literal-test authorization.

Only invented byte files are constructed. This file directly loads transport.py
and never imports the diagnostic driver, historical code, evaluators or a game.
Run only after the separate finite stub-test execution authorization.
"""

import copy
import hashlib
import importlib.util
import io
import os
import shutil
import stat
import struct
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "worker38" / "transport.py"
SPEC = importlib.util.spec_from_file_location("worker38_offline_transport_only", MODULE_PATH)
transport = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(transport)

PRODUCTION_OUTPUT_HOOK = None
CURRENT_PRODUCTION_SELECTOR = None


def sha(data):
    return hashlib.sha256(data).hexdigest()


class _StubSeekableSink:
    """Metadata-only writer for exact cap edges; allocates no large buffers."""
    def __init__(self, position=0):
        self.position = position
        self.closed = False

    def tell(self):
        return self.position

    def write(self, data):
        self.position += len(data)
        return len(data)

    def flush(self):
        pass


class OfflineTransportPlan(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="worker38-stub-tests-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.counter = 0
        # One original case deadline is carried through packaging/readback.
        self.deadline = time.monotonic() + 580
        # Free-space failures and exact edges are explicitly tested in T05.
        self.free_mock = mock.patch.object(transport, "_free", return_value=None)
        self.free_mock.start()
        self.addCleanup(self.free_mock.stop)

    def fresh(self, stem):
        self.counter += 1
        return self.base / f"{stem}-{self.counter}"

    def package(self, data=b"invented transport bytes\n"):
        root = self.fresh("raw")
        root.mkdir()
        (root / "receipt.json").write_bytes(data)
        (root / "nested").mkdir()
        (root / "nested" / "stub.bin").write_bytes(b"\x00\x01stub\xff")
        destination = self.fresh("package")
        result = transport.package_attempt(root, destination, deadline_monotonic=self.deadline)
        self.assertEqual(result["status"], "packaged", result)
        return root, destination, result

    def wrappers(self, result, *, member_name=None, payload=None, extra=False, duplicate=False, empty=False):
        part = result["manifest"]["parts"][0]
        wrapper = self.fresh("invented-provider-wrapper.zip")
        actual_payload = Path(result["local_paths"][part["path"]]).read_bytes()
        with zipfile.ZipFile(wrapper, "w", compression=zipfile.ZIP_STORED) as archive:
            if not empty:
                archive.writestr(member_name or part["path"], actual_payload if payload is None else payload)
                archive.writestr("transport-manifest.json", transport._manifest_bytes(result["manifest"]))
            if extra:
                archive.writestr("unexpected.txt", b"extra invented byte file")
            if duplicate:
                archive.writestr(part["path"], actual_payload)
        raw = wrapper.read_bytes()
        receipt = {"provider": "github_actions", "operation": "download",
                   "event_id": "invented-provider-event", "artifact_id": "invented-artifact",
                   "repository": "invented/repository", "run_id": "invented-run",
                   "run_attempt": "1", "completed_at": "2026-10-03T00:00:00Z",
                   "size": len(raw), "sha256": sha(raw)}
        return [{"path": wrapper, "part_path": part["path"], "member_name": part["path"],
                 "download_receipt": receipt}]

    def custody_mapping(self, result):
        mapping = {}
        for expected in result["manifest"]["parts"]:
            upload_path = Path(result["local_paths"][expected["path"]])
            download_path = self.fresh("invented-drive-download")
            shutil.copyfile(upload_path, download_path)
            file_id = f"invented-drive-id-{expected['order']}"
            common = {"provider": "google_drive", "file_id": file_id,
                      "size": expected["size"], "sha256": expected["sha256"]}
            upload = {**common, "operation": "upload", "event_id": "invented-upload-" + file_id,
                      "completed_at": "2026-10-03T00:00:00Z", "parent_folder_id": transport.CANONICAL_FOLDER_ID}
            download = {**common, "operation": "download", "event_id": "invented-download-" + file_id,
                        "completed_at": "2026-10-03T00:00:01Z"}
            mapping[expected["path"]] = {"path": download_path, "upload_input_path": upload_path,
                                         "drive_file_id": file_id,
                                         "direct_url": f"https://drive.google.com/file/d/{file_id}/view",
                                         "upload_receipt": upload, "download_receipt": download}
        return mapping

    def raw_zip(self, members, *, mode=None):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, data in members:
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = ((stat.S_IFREG | 0o600) if mode is None else mode) << 16
                archive.writestr(info, data)
        return output.getvalue()

    def malicious_transport(self, raw):
        part = self.fresh("invented-malicious-part")
        part.write_bytes(raw)
        manifest = {"schema": transport.MANIFEST_SCHEMA, "raw_size": 1,
                    "files": [{"path": "a", "size": 1, "sha256": sha(b"x")}],
                    "archive": {"path": "attempt.zip", "format": "zip-stored-v1", "size": len(raw), "sha256": sha(raw)},
                    "parts": [{"order": 1, "path": "part-001.bin", "size": len(raw), "sha256": sha(raw)}],
                    "limits": {"raw_bytes": transport.RAW_CAP, "archive_bytes": transport.ARCHIVE_CAP,
                               "part_bytes": transport.PART_CAP, "provider_zip_strictly_below_bytes": transport.PROVIDER_WRAPPER_LIMIT}}
        return transport.verify_transport(manifest, {"part-001.bin": part}, self.fresh("malicious-readback"), deadline_monotonic=self.deadline)

    def classification_wrappers(self, payloads=(b"literal first transport payload",)):
        """Literal wrapper-boundary data, not an underfilled production archive."""
        parts = [{'order': order, 'path': f'part-{order:03d}.bin', 'size': len(payload), 'sha256': sha(payload)}
                 for order, payload in enumerate(payloads, 1)]
        self.classification_manifest = {'schema': transport.MANIFEST_SCHEMA, 'raw_size': 0, 'files': [],
            'archive': {'path': 'attempt.zip', 'format': 'zip-stored-v1',
                        'size': sum(len(value) for value in payloads), 'sha256': sha(b''.join(payloads))},
            'parts': parts, 'limits': {'raw_bytes': transport.RAW_CAP, 'archive_bytes': transport.ARCHIVE_CAP,
                'part_bytes': transport.PART_CAP, 'provider_zip_strictly_below_bytes': transport.PROVIDER_WRAPPER_LIMIT}}
        manifest_raw = transport._manifest_bytes(self.classification_manifest)
        descriptors = []
        for order, (payload, part) in enumerate(zip(payloads, parts), 1):
            name = part['path']
            path = self.fresh("literal-github-download.zip")
            members = [(name, payload)] + ([('transport-manifest.json', manifest_raw)] if order == 1 else [])
            path.write_bytes(self.raw_zip(members))
            wrapper = path.read_bytes()
            receipt = {"provider": "github_actions", "operation": "download",
                       "repository": "carabinshely/bandido-alcatraz-solve", "run_id": "123",
                       "run_attempt": "1", "artifact_id": str(1000 + order),
                       "artifact_name": f"worker38-123-1-part-{order:03d}",
                       "event_id": f"literal-provider-download-{order}",
                       "completed_at": "2026-10-04T00:00:00Z",
                       "size": len(wrapper), "sha256": sha(wrapper)}
            descriptors.append({"order": order, "part_path": name, "member_name": name,
                                "path": str(path), "size": len(wrapper), "sha256": sha(wrapper),
                                "download_receipt": receipt})
        return parts, descriptors

    def classification_wrapper_check(self, parts, descriptors):
        checker = getattr(transport, "verify_provider_wrappers", None)
        self.assertTrue(callable(checker), "mandatory classification wrapper validator is missing")
        return checker(descriptors, parts, transport_manifest=self.classification_manifest, repository="carabinshely/bandido-alcatraz-solve",
                       workflow_run="123", workflow_attempt="1", deadline_monotonic=None)

    def repin_literal_wrapper(self, descriptor, raw):
        Path(descriptor["path"]).write_bytes(raw)
        descriptor.update(size=len(raw), sha256=sha(raw))
        descriptor["download_receipt"].update(size=len(raw), sha256=sha(raw))

    def seal_fixture(self, package_directory):
        cache = self.fresh('literal-cache')
        allocation = cache / 'worker38-synthetic-profile/allocations/worker38-synthetic-profile-01'
        attempt = allocation / 'run-123-attempt-1'
        for directory in (cache, cache / 'worker38-synthetic-profile', allocation.parent, allocation, attempt):
            directory.mkdir(mode=0o700)
        destination = allocation / 'transport-123-attempt-1'
        Path(package_directory).rename(destination)
        records = []
        for name in ('writer-exit-observation.json', 'startup-failure.json'):
            raw = b'{"literal":"fixed completed writer evidence"}\n'
            (attempt / name).write_bytes(raw)
            records.append({'path': name, 'size_bytes': len(raw), 'sha256': sha(raw)})
        handoff = {'schema': 'worker38-upload-writer-handoff-v1', 'attempt_id': 'worker38-123-1',
            'preservation_pid': os.getpid(), 'coordinator_state': 'never_started', 'coordinator_pid': None,
            'coordinator_start_ticks': None, 'evaluator_entries_upper_bound': 0,
            'admission_exited': True, 'owned_children_reaped': True, 'cleanup_confirmed': True,
            'no_further_writes': True, 'evidence': records}
        self.addCleanup(lambda: destination.chmod(0o700) if destination.exists() and not destination.is_symlink() else None)
        return cache, destination, handoff

    def test_PW03_mandatory_exact_ordered_wrapper_coverage(self):
        parts, descriptors = self.classification_wrappers((b"first", b"second"))
        variants = (None, [], descriptors[:1], descriptors + [copy.deepcopy(descriptors[0])],
                    [descriptors[0], copy.deepcopy(descriptors[0])], list(reversed(descriptors)))
        for index, altered in enumerate(variants):
            with self.subTest(variant=index), self.assertRaises(transport.TransportError):
                self.classification_wrapper_check(parts, altered)
        unknown = copy.deepcopy(descriptors)
        unknown[1]["part_path"] = "part-003.bin"
        with self.assertRaises(transport.TransportError):
            self.classification_wrapper_check(parts, unknown)

    def test_PW04_one_actual_part_needs_one_actual_wrapper(self):
        parts, descriptors = self.classification_wrappers()
        checked = self.classification_wrapper_check(parts, descriptors)
        self.assertEqual(len(checked), 1)
        self.assertEqual(checked[0]["part_path"], "part-001.bin")
        self.assertEqual(checked[0]["payload"], {"size": parts[0]["size"], "sha256": parts[0]["sha256"]})
        self.assertEqual(checked[0]["wrapper"], {"size": descriptors[0]["size"], "sha256": descriptors[0]["sha256"]})
        manifest_raw = transport._manifest_bytes(self.classification_manifest)
        self.assertEqual(checked[0]["manifest"], {"size": len(manifest_raw), "sha256": sha(manifest_raw)})

    def test_PW05_actual_wrapper_bytes_must_match_both_pins(self):
        for fault in ("size", "sha256", "changed-bytes"):
            parts, descriptors = self.classification_wrappers()
            if fault == "size":
                descriptors[0]["size"] += 1
            elif fault == "sha256":
                descriptors[0]["sha256"] = "f" * 64
            else:
                path = Path(descriptors[0]["path"])
                path.write_bytes(path.read_bytes() + b"changed")
            with self.subTest(fault=fault), self.assertRaises(transport.TransportError):
                self.classification_wrapper_check(parts, descriptors)

    def test_PW06_strict_provider_zip_limit_uses_actual_size(self):
        parts, descriptors = self.classification_wrappers()
        if PRODUCTION_OUTPUT_HOOK is not None:
            PRODUCTION_OUTPUT_HOOK(CURRENT_PRODUCTION_SELECTOR, [{
                'event': 'transport_input_identity',
                'boundary': 'accepted-wrapper-before-positive-check',
                'paths': [str(descriptors[0]['path'])]}])
        self.assertEqual(len(self.classification_wrapper_check(parts, descriptors)), 1)
        for size in (transport.PROVIDER_WRAPPER_LIMIT, transport.PROVIDER_WRAPPER_LIMIT + 1):
            # Fixed existing metadata-fault mechanism; no large allocation/cap edit.
            with self.subTest(size=size), mock.patch.object(transport, "_open_regular", return_value=(io.BytesIO(), SimpleNamespace(st_size=size))):
                with self.assertRaises(transport.TransportError):
                    self.classification_wrapper_check(parts, descriptors)
        # Amendment manifest_over_one_MiB: one bounded header mutation only.
        raw = bytearray(Path(descriptors[0]['path']).read_bytes())
        first = raw.index(b'PK\x01\x02')
        second = raw.index(b'PK\x01\x02', first + 4)
        struct.pack_into('<I', raw, second + 24, 1048577)
        self.repin_literal_wrapper(descriptors[0], raw)
        with self.subTest(amendment='manifest_over_one_MiB'), self.assertRaises(transport.TransportError):
            self.classification_wrapper_check(parts, descriptors)

    def test_PW07_exact_member_name_size_and_payload(self):
        payload = b"fixed payload"
        for fault in ("name", "declared-size", "payload-size", "payload-hash"):
            parts, descriptors = self.classification_wrappers((payload,))
            name = "renamed.bin" if fault == "name" else parts[0]["path"]
            altered = payload + b"x" if fault == "payload-size" else payload
            if fault == "payload-hash":
                altered = b"X" + payload[1:]
            raw = bytearray(self.raw_zip([(name, altered), ('transport-manifest.json', transport._manifest_bytes(self.classification_manifest))]))
            if fault == "declared-size":
                central = raw.index(b"PK\x01\x02")
                struct.pack_into("<I", raw, central + 24, len(payload) + 1)
            self.repin_literal_wrapper(descriptors[0], raw)
            if fault == "name":
                # Self-consistent caller-chosen alias must not bypass exact part name.
                descriptors[0]["member_name"] = name
            with self.subTest(fault=fault), self.assertRaises(transport.TransportError):
                self.classification_wrapper_check(parts, descriptors)
        for label in ('manifest_ordered_part_binding', 'manifest_archive_inventory_binding'):
            parts, descriptors = self.classification_wrappers((b'fixed payload',))
            changed = copy.deepcopy(self.classification_manifest)
            if label == 'manifest_ordered_part_binding':
                changed['parts'][0]['sha256'] = 'f' * 64
                expected_error = 'ordered part binding'
            else:
                changed['archive']['sha256'] = 'f' * 64
                changed['files'] = [{'path': 'invented-extra.bin', 'size': 1, 'sha256': sha(b'x')}]
                changed['raw_size'] = 1
                expected_error = 'archive inventory binding'
            raw = self.raw_zip([('part-001.bin', b'fixed payload'),
                                ('transport-manifest.json', transport._manifest_bytes(changed))])
            self.repin_literal_wrapper(descriptors[0], raw)
            with self.subTest(amendment=label), self.assertRaisesRegex(transport.TransportError, expected_error):
                self.classification_wrapper_check(parts, descriptors)

    def test_PW08_extra_or_duplicate_wrapper_members_reject(self):
        for second_name in ("unexpected.bin", "part-001.bin"):
            parts, descriptors = self.classification_wrappers((b"first",))
            with mock.patch("warnings.warn"):
                raw = self.raw_zip([("part-001.bin", b"first"), ("transport-manifest.json", transport._manifest_bytes(self.classification_manifest)), (second_name, b"second")])
            self.repin_literal_wrapper(descriptors[0], raw)
            with self.subTest(second_name=second_name), self.assertRaises(transport.TransportError):
                self.classification_wrapper_check(parts, descriptors)
        for label in ('first_missing_manifest', 'first_duplicate_manifest', 'later_extra_manifest'):
            parts, descriptors = self.classification_wrappers((b'first', b'second'))
            manifest_raw = transport._manifest_bytes(self.classification_manifest)
            if label == 'first_missing_manifest':
                index, members = 0, [('part-001.bin', b'first')]
            elif label == 'first_duplicate_manifest':
                index, members = 0, [('part-001.bin', b'first'),
                    ('transport-manifest.json', manifest_raw), ('transport-manifest.json', manifest_raw)]
            else:
                index, members = 1, [('part-002.bin', b'second'), ('transport-manifest.json', manifest_raw)]
            with mock.patch('warnings.warn'):
                raw = self.raw_zip(members)
            self.repin_literal_wrapper(descriptors[index], raw)
            with self.subTest(amendment=label), self.assertRaises(transport.TransportError):
                self.classification_wrapper_check(parts, descriptors)

    def test_PW09_provider_identity_binds_verified_attempt(self):
        cases = (("provider", "other-provider"), ("operation", "upload"),
                 ("repository", "other/repository"), ("run_id", "124"), ("run_attempt", "2"),
                 ("artifact_name", "worker38-123-1-part-002"), ("artifact_id", ""),
                 ("event_id", ""), ("artifact_id", None), ("event_id", None))
        for key, value in cases:
            parts, descriptors = self.classification_wrappers()
            if value is None:
                del descriptors[0]["download_receipt"][key]
            else:
                descriptors[0]["download_receipt"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(transport.TransportError):
                self.classification_wrapper_check(parts, descriptors)

    def test_PW10_unique_artifact_and_download_event_per_part(self):
        for field in ("artifact_id", "event_id"):
            parts, descriptors = self.classification_wrappers((b"first", b"second"))
            descriptors[1]["download_receipt"][field] = descriptors[0]["download_receipt"][field]
            with self.subTest(field=field), self.assertRaises(transport.TransportError):
                self.classification_wrapper_check(parts, descriptors)

    def test_PW11_actual_retained_file_required_not_verified_flags(self):
        for fault in ("flag-only", "missing-path", "missing-file", "unreadable-file", "symlink"):
            parts, descriptors = self.classification_wrappers()
            if fault == "flag-only":
                descriptors = [{"verified": True}]
            elif fault == "missing-path":
                descriptors[0].pop("path")
                descriptors[0]["verified"] = True
            elif fault == "missing-file":
                Path(descriptors[0]["path"]).unlink()
            elif fault == "symlink":
                link = self.fresh("wrapper-link")
                link.symlink_to(descriptors[0]["path"])
                descriptors[0]["path"] = str(link)
            with self.subTest(fault=fault):
                if fault == "unreadable-file":
                    with mock.patch.object(transport, "_open_regular", side_effect=PermissionError("literal unreadable wrapper")):
                        with self.assertRaises((transport.TransportError, OSError)):
                            self.classification_wrapper_check(parts, descriptors)
                else:
                    with self.assertRaises((transport.TransportError, OSError)):
                        self.classification_wrapper_check(parts, descriptors)

    def test_PW12_original_archive_or_raw_part_is_not_outer_wrapper(self):
        for wrong_layer in (self.raw_zip([("receipt.json", b"{}")]), b"a raw split payload"):
            parts, descriptors = self.classification_wrappers()
            self.repin_literal_wrapper(descriptors[0], wrong_layer)
            with self.subTest(size=len(wrong_layer)), self.assertRaises((transport.TransportError, zipfile.BadZipFile)):
                self.classification_wrapper_check(parts, descriptors)

    def test_PW16_local_checks_never_authenticate_provider_origin(self):
        parts, descriptors = self.classification_wrappers()
        checked = self.classification_wrapper_check(parts, descriptors)
        self.assertIs(checked[0]["external_origin_authenticated"], False)
        self.assertEqual(checked[0]["asserted_download_receipt"]["artifact_name"], "worker38-123-1-part-001")

    def test_T01_round_trip_inventory_and_raw_readback(self):
        root, package_directory, package = self.package()
        wrappers = self.wrappers(package)
        result = transport.verify_transport(package["manifest"], package["local_paths"], self.fresh("readback"),
            provider_wrappers=wrappers, deadline_monotonic=self.deadline)
        self.assertEqual(result["status"], "local_transport_verified", result)
        self.assertEqual(result["files"], package["manifest"]["files"])
        self.assertEqual(result["custody"], "pending")
        for entry in result["files"]:
            self.assertEqual((Path(result["destination"]) / "raw" / entry["path"]).read_bytes(),
                             (root / entry["path"]).read_bytes())
        self.assertEqual([p["order"] for p in result["parts"]], [1])
        with zipfile.ZipFile(Path(result["destination"]) / "attempt.zip") as archive:
            for info in archive.infolist():
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                self.assertEqual(info.external_attr >> 16, stat.S_IFREG | 0o600)
        manifest_raw = (package_directory / 'transport-manifest.json').read_bytes()
        self.assertEqual(result['provider_wrappers'][0]['manifest'], {'size': len(manifest_raw), 'sha256': sha(manifest_raw)})
        cache, destination, writers = self.seal_fixture(package_directory)
        ready = transport.seal_upload(cache, '123', deadline_monotonic=self.deadline, writer_handoff=writers)
        self.assertEqual(ready['status'], 'upload_ready', ready)
        self.assertEqual(len((destination / 'upload-plan.txt').read_bytes().splitlines()), 17)
        self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o500)
        self.assertEqual(stat.S_IMODE((destination / 'part-001.bin').stat().st_mode), 0o400)
        self.assertEqual((destination / 'transport-manifest.json').read_bytes(), manifest_raw)
        self.assertNotIn('transport-manifest.json', [entry['path'] for entry in package['manifest']['files']])

    def test_T02_determinism_across_different_roots(self):
        _, first_dir, first = self.package()
        _, second_dir, second = self.package()
        self.assertEqual(first["manifest"], second["manifest"])
        self.assertEqual((first_dir / "attempt.zip").read_bytes(), (second_dir / "attempt.zip").read_bytes())

    def test_T03_exclusive_destinations_preserve_existing_data(self):
        root, destination, package = self.package()
        before = {p.relative_to(destination).as_posix(): p.read_bytes() for p in destination.iterdir() if p.is_file()}
        self.assertEqual(transport.package_attempt(root, destination, deadline_monotonic=self.deadline)["status"], "blocked")
        self.assertEqual(transport.verify_transport(package["manifest"], package["local_paths"], destination, deadline_monotonic=self.deadline)["status"], "blocked")
        after = {p.relative_to(destination).as_posix(): p.read_bytes() for p in destination.iterdir() if p.is_file()}
        self.assertEqual(before, after)

    def test_T04_unsafe_sources_and_containment(self):
        for kind in ("symlink", "fifo", "unsafe-name", "nested-destination"):
            with self.subTest(kind=kind):
                root = self.fresh("unsafe-source")
                root.mkdir()
                (root / "keep").write_bytes(b"preserve")
                destination = self.fresh("unsafe-output")
                if kind == "symlink":
                    (root / "link").symlink_to(root / "keep")
                elif kind == "fifo":
                    os.mkfifo(root / "pipe")
                elif kind == "unsafe-name":
                    (root / "bad\\name").write_bytes(b"bad")
                else:
                    destination = root / "transport"
                result = transport.package_attempt(root, destination, deadline_monotonic=self.deadline)
                self.assertEqual(result["status"], "blocked", result)
                self.assertEqual((root / "keep").read_bytes(), b"preserve")
        path_cases = (('canonical_bracket_cache', '/literal/cache[1]'),
                      ('canonical_question_cache', '/literal/cache?'),
                      ('canonical_star_cache', '/literal/cache*'),
                      ('newline_path', '/literal/cache\nother'))
        for label, path in path_cases:
            provider = mock.Mock()
            result = transport.seal_upload(path, '123', deadline_monotonic=self.deadline, writer_handoff={})
            if result.get('upload_ready'): provider()
            with self.subTest(amendment=label):
                self.assertFalse(result['upload_ready']); provider.assert_not_called()
                self.assertIn('eligible literal', result['error'])
        for label in ('redirected_part', 'redirected_component'):
            _, package_directory, _ = self.package()
            cache, destination, writers = self.seal_fixture(package_directory)
            sibling = self.fresh('invented-sibling')
            if label == 'redirected_part':
                (destination / 'part-001.bin').rename(sibling)
                (destination / 'part-001.bin').symlink_to(sibling)
            else:
                destination.rename(sibling)
                destination.symlink_to(sibling, target_is_directory=True)
            provider = mock.Mock()
            result = transport.seal_upload(cache, '123', deadline_monotonic=self.deadline, writer_handoff=writers)
            if result.get('upload_ready'): provider()
            with self.subTest(amendment=label):
                self.assertFalse(result['upload_ready']); provider.assert_not_called()
                self.assertTrue(sibling.exists())

    def test_T05_exact_one_gib_storage_floor(self):
        self.free_mock.stop()
        for available, blocked in ((transport.REQUIRED_FREE_BYTES - 1, True), (transport.REQUIRED_FREE_BYTES, False)):
            with self.subTest(available=available), mock.patch.object(transport.os, "fstatvfs", return_value=SimpleNamespace(f_bavail=available, f_frsize=1)):
                if blocked:
                    with self.assertRaises(OSError) as observed:
                        transport._free(self.base)
                    self.assertEqual(transport._typed_failure(observed.exception, 'storage_preflight')['status'],
                                     'execution_incomplete')
                else:
                    transport._free(self.base)
        self.free_mock.start()

    def test_T06_cap_edges_without_large_files(self):
        sink = _StubSeekableSink(transport.ARCHIVE_CAP - 1)
        bounded = transport._BoundedArchive(sink, time.monotonic() + 60)
        self.assertEqual(bounded.write(b"x"), 1)
        with self.assertRaises(transport.TransportError):
            bounded.write(b"y")
        self.assertEqual(sink.position, transport.ARCHIVE_CAP)
        self.assertEqual(transport._int(transport.RAW_CAP, "raw", transport.RAW_CAP), transport.RAW_CAP)
        self.assertEqual(transport._int(transport.PART_CAP, "part", transport.PART_CAP), transport.PART_CAP)
        for cap in (transport.RAW_CAP, transport.ARCHIVE_CAP, transport.PART_CAP):
            with self.assertRaises(transport.TransportError):
                transport._int(cap + 1, "fixed bound", cap)
        # Exercise a full-sized first-part descriptor without allocating its bytes.
        manifest = {"schema": transport.MANIFEST_SCHEMA, "raw_size": 0, "files": [],
                    "archive": {"path": "attempt.zip", "format": "zip-stored-v1", "size": transport.PART_CAP + 1, "sha256": "0" * 64},
                    "parts": [{"order": 1, "path": "part-001.bin", "size": transport.PART_CAP, "sha256": "0" * 64},
                              {"order": 2, "path": "part-002.bin", "size": 1, "sha256": "1" * 64}],
                    "limits": {"raw_bytes": transport.RAW_CAP, "archive_bytes": transport.ARCHIVE_CAP,
                               "part_bytes": transport.PART_CAP, "provider_zip_strictly_below_bytes": transport.PROVIDER_WRAPPER_LIMIT}}
        self.assertEqual(len(transport._manifest(manifest)[1]), 2)
        manifest["parts"][0]["size"] += 1
        with self.assertRaises(transport.TransportError):
            transport._manifest(manifest)

    def test_T07_overflow_and_write_failure_keep_partial_evidence(self):
        for error in (transport.TransportResourceExceeded("invented cap failure"), OSError("invented write failure")):
            root = self.fresh("prefix-source")
            root.mkdir()
            (root / "a").write_bytes(b"original")
            destination = self.fresh("prefix-output")
            def fail_archive(source_root, files, path, deadline):
                path.write_bytes(b"surviving partial archive")
                raise error
            with mock.patch.object(transport, "_archive", side_effect=fail_archive):
                result = transport.package_attempt(root, destination, deadline_monotonic=self.deadline)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual((root / "a").read_bytes(), b"original")
            self.assertEqual((destination / "attempt.zip.partial").read_bytes(), b"surviving partial archive")
            self.assertTrue((destination / "transport-failure.json").is_file())
            expected = "resource_incomplete" if isinstance(error, transport.TransportResourceExceeded) else "execution_incomplete"
            self.assertEqual(result["primary_failure"]["status"], expected)
            self.assertEqual(result["failure"]["status"], expected)
            self.assertEqual(result["secondary_failures"], [])

    def test_T08_manifest_and_part_corruption(self):
        _, _, package = self.package()
        cases = ("missing", "extra", "duplicate", "order", "size", "hash", "limits", "raw-order")
        for case in cases:
            with self.subTest(case=case):
                manifest = copy.deepcopy(package["manifest"])
                paths = dict(package["local_paths"])
                if case == "missing":
                    paths.clear()
                elif case == "extra":
                    paths["extra.bin"] = next(iter(paths.values()))
                elif case == "duplicate":
                    manifest["parts"].append(copy.deepcopy(manifest["parts"][0]))
                elif case == "order":
                    manifest["parts"][0]["order"] = 2
                elif case == "size":
                    manifest["parts"][0]["size"] += 1
                elif case == "hash":
                    manifest["parts"][0]["sha256"] = "0" * 64
                elif case == "limits":
                    manifest["limits"]["raw_bytes"] += 1
                else:
                    manifest["files"].reverse()
                result = transport.verify_transport(manifest, paths, self.fresh("corrupt-readback"), deadline_monotonic=self.deadline)
                self.assertEqual(result["status"], "blocked", result)

    def test_T09_zip_attacks(self):
        raw = self.raw_zip([("a", b"x")])
        encrypted = bytearray(raw)
        central = encrypted.index(b"PK\x01\x02")
        struct.pack_into("<H", encrypted, central + 8, 1)
        bomb = bytearray(raw)
        struct.pack_into("<I", bomb, central + 24, transport.RAW_CAP + 1)
        corrupted = bytearray(raw)
        corrupted[31] ^= 0x01  # One-byte filename means payload begins at offset 31.
        cases = {
            "traversal": self.raw_zip([("../escape", b"x")]),
            "absolute": self.raw_zip([("/escape", b"x")]),
            "backslash": self.raw_zip([("bad\\name", b"x")]),
            "duplicate": self.raw_zip([("a", b"x"), ("a", b"x")]),
            "symlink": self.raw_zip([("a", b"x")], mode=stat.S_IFLNK | 0o777),
            "special": self.raw_zip([("a", b"x")], mode=stat.S_IFIFO | 0o600),
            "encrypted": bytes(encrypted), "bomb": bytes(bomb), "corrupt-data": bytes(corrupted),
            "inventory": self.raw_zip([("unexpected", b"x")]),
        }
        for case, contents in cases.items():
            with self.subTest(case=case):
                result = self.malicious_transport(contents)
                self.assertEqual(result["status"], "blocked", result)
        self.assertFalse((self.base / "escape").exists())

    def test_T10_wrapper_limit_and_unverified_origin(self):
        _, _, package = self.package()
        descriptors = self.wrappers(package)
        result = transport.verify_transport(package["manifest"], package["local_paths"], self.fresh("wrapper-readback"), provider_wrappers=descriptors, deadline_monotonic=self.deadline)
        self.assertEqual(result["status"], "local_transport_verified", result)
        self.assertFalse(result["provider_origin_authenticated"])
        self.assertFalse(result["provider_wrappers"][0]["external_origin_authenticated"])
        # A fabricated wrapper and complete fabricated receipt never prove origin.
        oversized = SimpleNamespace(st_size=transport.PROVIDER_WRAPPER_LIMIT)
        with mock.patch.object(transport, "_open_regular", return_value=(io.BytesIO(), oversized)):
            with self.assertRaises(transport.TransportError):
                transport._file_hash(Path("stub"), transport.PROVIDER_WRAPPER_LIMIT - 1, time.monotonic() + 60)
        descriptors[0].pop("download_receipt")
        result = transport.verify_transport(package["manifest"], package["local_paths"], self.fresh("missing-wrapper-receipt"), provider_wrappers=descriptors, deadline_monotonic=self.deadline)
        self.assertEqual(result["status"], "blocked")

    def test_T11_wrapper_payload_must_match_exact_part(self):
        _, _, package = self.package()
        for options in ({"member_name": "renamed.bin"}, {"payload": b"wrong"}, {"extra": True}, {"duplicate": True}, {"empty": True}):
            with self.subTest(options=options):
                descriptors = self.wrappers(package, **options)
                result = transport.verify_transport(package["manifest"], package["local_paths"], self.fresh("bad-wrapper"), provider_wrappers=descriptors, deadline_monotonic=self.deadline)
                self.assertEqual(result["status"], "blocked", result)
        descriptors = self.wrappers(package)
        wrapper_path = descriptors[0]["path"]
        raw = bytearray(wrapper_path.read_bytes())
        central = raw.index(b"PK\x01\x02")
        struct.pack_into("<I", raw, central + 24, transport.PART_CAP + 1)
        if PRODUCTION_OUTPUT_HOOK is not None:
            PRODUCTION_OUTPUT_HOOK(CURRENT_PRODUCTION_SELECTOR, [{
                'event': 'preserve_observed_version', 'path': str(wrapper_path),
                'label': 't11-01-before-existing-mutation', 'maximum_bytes': 1185}])
        wrapper_path.write_bytes(raw)
        descriptors[0]["download_receipt"].update(size=len(raw), sha256=sha(raw))
        result = transport.verify_transport(package["manifest"], package["local_paths"], self.fresh("oversized-wrapper-payload"), provider_wrappers=descriptors, deadline_monotonic=self.deadline)
        self.assertEqual(result["status"], "blocked", result)

    def test_T12_complete_readback_rehashes_actual_downloads(self):
        _, _, package = self.package()
        mapping = self.custody_mapping(package)
        result = transport.verify_custody(package["manifest"], mapping, deadline_monotonic=self.deadline)
        self.assertEqual(result["status"], "local_canonical_readback_verified", result)
        self.assertTrue(result["local_readback_verified"])
        self.assertEqual(result["files"], package["manifest"]["files"])
        if PRODUCTION_OUTPUT_HOOK is not None:
            PRODUCTION_OUTPUT_HOOK(CURRENT_PRODUCTION_SELECTOR, [{
                'event': 'preserve_observed_version', 'path': str(mapping['part-001.bin']['path']),
                'label': 't12-01-before-existing-mutation', 'maximum_bytes': 260}])
        Path(mapping["part-001.bin"]["path"]).write_bytes(b"tampered")
        self.assertEqual(transport.verify_custody(package["manifest"], mapping, deadline_monotonic=self.deadline)["status"], "blocked")

    def test_T13_custody_provenance_consistency_failures(self):
        _, _, package = self.package()
        for case in ("missing-id", "wrong-url", "same-path", "same-inode", "old-download", "missing-receipt", "same-event", "wrong-folder", "incomplete"):
            with self.subTest(case=case):
                mapping = self.custody_mapping(package)
                descriptor = mapping["part-001.bin"]
                if case == "missing-id":
                    descriptor.pop("drive_file_id")
                elif case == "wrong-url":
                    descriptor["direct_url"] = "https://example.com/file"
                elif case == "same-path":
                    descriptor["path"] = descriptor["upload_input_path"]
                elif case == "same-inode":
                    alias = self.fresh("download-hardlink")
                    os.link(descriptor["upload_input_path"], alias)
                    descriptor["path"] = alias
                elif case == "old-download":
                    descriptor["download_receipt"]["completed_at"] = "2026-10-02T00:00:00Z"
                elif case == "missing-receipt":
                    descriptor.pop("upload_receipt")
                elif case == "same-event":
                    descriptor["download_receipt"]["event_id"] = descriptor["upload_receipt"]["event_id"]
                elif case == "wrong-folder":
                    descriptor["upload_receipt"]["parent_folder_id"] = "another-folder"
                else:
                    mapping.clear()
                self.assertEqual(transport.verify_custody(package["manifest"], mapping, deadline_monotonic=self.deadline)["status"], "blocked")
        # Duplicate Drive IDs across two virtual parts; no 30 MiB byte fixture.
        manifest = copy.deepcopy(package["manifest"])
        manifest["archive"].update(size=transport.PART_CAP + 1, sha256="0" * 64)
        manifest["parts"] = [
            {"order": 1, "path": "part-001.bin", "size": transport.PART_CAP, "sha256": "0" * 64},
            {"order": 2, "path": "part-002.bin", "size": 1, "sha256": "0" * 64},
        ]
        mapping = {}
        for expected in manifest["parts"]:
            original = self.custody_mapping(package)["part-001.bin"]
            for receipt_key in ("upload_receipt", "download_receipt"):
                original[receipt_key].update(size=expected["size"], sha256=expected["sha256"])
            mapping[expected["path"]] = original
        with mock.patch.object(transport, "_file_hash", return_value={"size": transport.PART_CAP, "sha256": "0" * 64}):
            result = transport.verify_custody(manifest, mapping, deadline_monotonic=self.deadline)
        self.assertEqual(result["status"], "blocked", result)
        self.assertIn("duplicate Drive file ID", result["error"])

    def test_T14_strings_never_authenticate_canonical_custody(self):
        _, _, package = self.package()
        result = transport.verify_custody(package["manifest"], self.custody_mapping(package), deadline_monotonic=self.deadline)
        self.assertEqual(result["status"], "local_canonical_readback_verified", result)
        self.assertEqual(result["custody"], "pending")
        self.assertFalse(result["external_provenance_authenticated"])
        self.assertTrue(result["requirements_before_custody_verified"])

    def test_T15_source_mutation_is_rejected_and_preserved(self):
        root = self.fresh("mutable-source")
        root.mkdir()
        (root / "a").write_bytes(b"before")
        original_inventory = transport._inventory
        def mutate_after_inventory(source, deadline):
            value = original_inventory(source, deadline)
            if PRODUCTION_OUTPUT_HOOK is not None:
                PRODUCTION_OUTPUT_HOOK(CURRENT_PRODUCTION_SELECTOR, [{
                    'event': 'transport_input_identity',
                    'boundary': 'after-original-inventory-before-mutation',
                    'paths': [str(root / 'a')]}])
            (root / "a").write_bytes(b"after!")
            return value
        destination = self.fresh("mutated-output")
        with mock.patch.object(transport, "_inventory", side_effect=mutate_after_inventory):
            result = transport.package_attempt(root, destination, deadline_monotonic=self.deadline)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual((root / "a").read_bytes(), b"after!")
        self.assertTrue((destination / "attempt.zip.partial").exists())

    def test_T16_io_failures_and_expired_deadline(self):
        root, _, package = self.package()
        destination = self.fresh("io-failed-readback")
        def fail_copy(archive, info, output, expected, deadline):
            output.write(b"retained-prefix")
            raise OSError("invented extraction failure")
        with mock.patch.object(transport, "_copy_zip_member", side_effect=fail_copy):
            result = transport.verify_transport(package["manifest"], package["local_paths"], destination, deadline_monotonic=self.deadline)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stage"], "raw_extraction")
        first_file = package["manifest"]["files"][0]["path"]
        self.assertEqual((destination / "raw" / first_file).read_bytes(), b"retained-prefix")
        result = transport.verify_transport(package["manifest"], package["local_paths"], self.fresh("expired"), deadline_monotonic=time.monotonic() - 1)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stage"], "transport_preflight")
        mapping = self.custody_mapping(package)
        with mock.patch.object(transport, "_file_hash", side_effect=OSError("invented readback failure")):
            result = transport.verify_custody(package["manifest"], mapping, deadline_monotonic=self.deadline)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stage"], "canonical_readback_preflight")
        self.assertEqual(result["failure"]["status"], "execution_incomplete")
        # Explicit original authority is required; absence never grants600s.
        with self.assertRaises(transport.TransportError):
            transport._deadline(None)
        # One additional fixed literal boundary: the actual archive cleanup's
        # fsync fails after a body MemoryError, retaining both typed causes.
        with mock.patch.object(transport, "_open_regular", side_effect=MemoryError("invented archive memory")), \
             mock.patch.object(transport.os, "fsync", side_effect=OSError("invented late fsync")):
            with self.assertRaises(MemoryError) as captured:
                transport._archive(root, package["manifest"]["files"], self.fresh("archive-body-memory.partial"), self.deadline)
        failure = transport._failure("deterministic_archive", captured.exception, None)
        self.assertEqual(failure["primary_failure"]["status"], "resource_incomplete")
        self.assertEqual(failure["failure"]["status"], "resource_incomplete")
        self.assertEqual([(item["status"], item["phase"]) for item in failure["secondary_failures"]],
                         [("execution_incomplete", "archive_final_fsync")])


if __name__ == "__main__":
    unittest.main()
