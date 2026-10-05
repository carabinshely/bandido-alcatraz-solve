"""Offline, fail-closed Worker38 evidence transport; never runs scientific code.

The packaging and local readback functions return reports, including failures.
A failure never deletes source evidence or a destination's surviving prefix. Destinations must
not already exist. ``manifest`` means the ``manifest`` returned by
``package_attempt``, not its surrounding report.

``local_paths`` maps every part's manifest path to a regular local file. Optional
``provider_wrappers`` are actual downloaded GitHub ZIPs, each described by
``path``, ``part_path``, ``member_name`` and ``download_receipt``. The first
wrapper additionally contains the exact original compact transport manifest;
later wrappers contain only their part. Receipt strings
are retained as assertions; they cannot authenticate the ZIP's external origin.

``downloaded_mapping`` maps every part path to a dictionary containing ``path``,
``upload_input_path``, ``drive_file_id``, ``direct_url``, ``upload_receipt`` and
``download_receipt``. Receipts require operation, provider, file_id, event_id,
completed_at (UTC ISO-8601), size, and sha256. Upload/download event IDs must
differ. Readback paths/inodes must differ from upload inputs. This module checks
actual bytes and causal timestamp/identity consistency, NOT external authenticity.
Consequently verify_custody NEVER returns custody='verified'. The parent must
independently bind those receipts to successful authorized Drive tool operations
and the canonical folder, and require the second-stage byte checks reported here.

``verify_provider_wrappers`` is the read-only mandatory classification-facing
check. It raises on missing/invalid evidence, binds each actual downloaded outer
ZIP to its exact part and externally authenticated workflow identity, and still
reports external_origin_authenticated=False. It never uploads a wrapper as if it
were a canonical part. ``deadline_monotonic=None`` on this helper allocates no
time window: external time supervision remains the caller's responsibility.

For package_attempt, verify_transport and verify_custody, pass the SAME
``deadline_monotonic`` to all calls in one preservation phase. A missing
deadline fails closed; this module never creates or renews a preservation
interval. Off-runner read-only wrapper checking remains separately supervised.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import stat
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Mapping, Sequence
from urllib.parse import parse_qs, urlsplit


MIB = 1024 * 1024
RAW_CAP = 64 * MIB
ARCHIVE_CAP = 64 * MIB
PART_CAP = 30 * MIB
PROVIDER_WRAPPER_LIMIT = 32 * MIB  # Strictly less than, not <=.
REQUIRED_FREE_BYTES = 1024 * MIB
VERIFICATION_SECONDS = 600
CANONICAL_FOLDER_ID = "1sQhQY3aKuHvQfyOTUIQjJGANCKOwKgEd"
CHUNK_SIZE = MIB
MANIFEST_SCHEMA = "worker38.transport.v1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_DRIVE_ID = re.compile(r"[A-Za-z0-9_-]+\Z")
_ZIP_DATE = (1980, 1, 1, 0, 0, 0)


class TransportError(Exception):
    """A closed transport gate; surviving output is intentionally retained."""


class TransportResourceExceeded(TransportError):
    """Observed transport/preservation budget exhaustion, kept typed."""


def _deadline(value: float | None) -> float:
    now = time.monotonic()
    if value is None:
        raise TransportError("original preservation deadline required")
    if type(value) not in (float, int):
        raise TransportError("invalid preservation deadline")
    try:
        finite = math.isfinite(value)
    except (OverflowError, ValueError):
        finite = False
    if not finite or value > now + VERIFICATION_SECONDS:
        raise TransportError("preservation deadline invalid or exceeds fixed limit")
    if value <= now:
        raise TransportResourceExceeded("original preservation deadline expired")
    return float(value)


def _tick(deadline: float | None) -> None:
    if deadline is not None and time.monotonic() >= deadline:
        raise TransportResourceExceeded("600-second preservation-phase deadline reached")


def _name(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise TransportError("invalid relative evidence name")
    parts = value.split("/")
    if any(p in ("", ".", "..") or ":" in p for p in parts):
        raise TransportError("unsafe relative evidence name")
    if PurePosixPath(value).is_absolute():
        raise TransportError("absolute evidence name")
    try:
        encoded = value.encode("utf-8")
    except UnicodeError as exc:
        raise TransportError("non-UTF-8 evidence name") from exc
    if len(encoded) > 65535:
        raise TransportError("evidence name exceeds ZIP name bound")
    return value


def _int(value: Any, name: str, cap: int) -> int:
    if type(value) is not int or not 0 <= value <= cap:
        raise TransportError(f"invalid {name}")
    return value


def _hash(value: Any) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise TransportError("invalid SHA256")
    return value


def _absolute(path: Path | str) -> Path:
    p = Path(path)
    if ".." in p.parts:
        raise TransportError("local path contains parent traversal")
    return Path(os.path.abspath(p))


def _directory_fd(path: Path) -> int:
    """Open every ancestor without following links, retaining an anchored fd."""
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise TransportError("no-follow directory opens unavailable")
    path = _absolute(path)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(path.anchor, flags)
    try:
        for component in path.parts[1:]:
            child = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _open_regular(path: Path | str) -> tuple[BinaryIO, os.stat_result]:
    path = _absolute(path)
    parent_fd = _directory_fd(path.parent)
    try:
        # Nonblocking open prevents a malicious FIFO from hanging before fstat.
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
    finally:
        os.close(parent_fd)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise TransportError("non-regular evidence file")
        return os.fdopen(fd, "rb"), info
    except BaseException:
        os.close(fd)
        raise


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _file_hash(path: Path | str, cap: int, deadline: float | None) -> dict[str, Any]:
    source, before = _open_regular(path)
    with source:
        if before.st_size > cap:
            raise TransportError("local evidence file exceeds fixed size bound")
        digest = hashlib.sha256()
        size = 0
        while True:
            _tick(deadline)
            block = source.read(min(CHUNK_SIZE, cap - size + 1))
            if not block:
                break
            size += len(block)
            if size > cap:
                raise TransportError("evidence grew beyond fixed size bound")
            digest.update(block)
        if _identity(before) != _identity(os.fstat(source.fileno())) or size != before.st_size:
            raise TransportError("evidence changed while reading")
    return {"size": size, "sha256": digest.hexdigest()}


def _free(path: Path) -> None:
    fd = _directory_fd(path)
    try:
        usage = os.fstatvfs(fd)
        if usage.f_bavail * usage.f_frsize < REQUIRED_FREE_BYTES:
            raise OSError("less than 1 GiB free preservation storage")
    finally:
        os.close(fd)


def _fsync_dir(path: Path) -> None:
    fd = _directory_fd(path)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _new_destination(path: Path) -> Path:
    path = _absolute(path)
    _free(path.parent)
    # mkdir is deliberately exclusive, including broken links and empty dirs.
    os.mkdir(path, 0o700)
    _fsync_dir(path.parent)
    return path


def _finalize(partial: Path, final: Path) -> None:
    # link refuses an existing final path rather than replacing its evidence.
    os.link(partial, final, follow_symlinks=False)
    _fsync_dir(final.parent)
    os.unlink(partial)
    _fsync_dir(final.parent)


def _json_file(path: Path, value: Mapping[str, Any], cap: int = ARCHIVE_CAP) -> None:
    encoder = json.JSONEncoder(sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                               allow_nan=False)
    count = 0
    with path.open("xb") as handle:
        for piece in encoder.iterencode(value):
            block = piece.encode("ascii")
            count += len(block)
            if count + 1 > cap:  # Include the final newline in the cap.
                raise TransportResourceExceeded("JSON evidence exceeds bounded output")
            handle.write(block)
        handle.write(b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    _fsync_dir(path.parent)


def _typed_failure(exc: BaseException, stage: str) -> dict[str, Any]:
    if isinstance(exc, (TransportResourceExceeded, MemoryError, RecursionError)):
        status, category = 'resource_incomplete', 'resource'
    elif isinstance(exc, (TransportError, ValueError, TypeError, KeyError, zipfile.BadZipFile)):
        status, category = 'integrity_invalid', 'integrity'
    else:
        status, category = 'execution_incomplete', 'infrastructure'
    return {'status': status, 'category': category, 'phase': stage,
            'error_type': type(exc).__name__, 'error': str(exc)[:2048]}


def _failure(stage: str, exc: Exception, destination: Path | None) -> dict[str, Any]:
    # A close/flush exception can become the active exception while its body
    # failure survives as __context__. Preserve that ordered chain instead of
    # assigning the entire failed operation the last cleanup exception's type.
    chain, seen, current = [], set(), exc
    while current is not None and id(current) not in seen and len(chain) < 16:
        seen.add(id(current)); chain.append(current)
        current = current.__context__
    causes = []
    for error in reversed(chain):
        causes.append(_typed_failure(error, stage))
        causes.extend(getattr(error, 'transport_secondary_failures', ()))
    priority = {'execution_incomplete': 1, 'resource_incomplete': 2, 'integrity_invalid': 3}
    selected = max(causes, key=lambda value: priority[value['status']])
    report: dict[str, Any] = {
        "schema": "worker38.transport-report.v1", "status": "blocked",
        "stage": stage, "error_type": selected['error_type'], "error": selected['error'],
        "failure": selected, "primary_failure": causes[0], "secondary_failures": causes[1:],
        "custody": "blocked", "surviving_prefix_preserved": True,
        "source_evidence_untouched": True,
    }
    if destination is not None:
        report["destination"] = str(destination)
        try:
            _json_file(destination / "transport-failure.json", report, MIB)
            report["failure_sidecar_durable"] = True
        except Exception as sidecar_exc:
            report["failure_sidecar_durable"] = False
            report["sidecar_error_type"] = type(sidecar_exc).__name__
            secondary = _typed_failure(sidecar_exc, 'transport_failure_persistence')
            report['secondary_failures'].append(secondary)
            if priority[secondary['status']] > priority[report['failure']['status']]:
                report['failure'] = secondary
    return report


def _inventory(root: Path, deadline: float) -> list[dict[str, Any]]:
    fd = _directory_fd(root)
    entries: list[dict[str, Any]] = []
    total = 0
    minimum_zip_size = 22
    # Traverse anchored directory descriptors, never following a replaced link.
    def walk(directory_fd: int, prefix: str) -> None:
        nonlocal total, minimum_zip_size
        _tick(deadline)
        with os.scandir(directory_fd) as iterator:
            children = sorted(iterator, key=lambda item: item.name)
        for child in children:
            _tick(deadline)
            info = child.stat(follow_symlinks=False)
            relative = _name(prefix + child.name)
            if stat.S_ISDIR(info.st_mode):
                child_fd = os.open(child.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                   dir_fd=directory_fd)
                try:
                    walk(child_fd, relative + "/")
                finally:
                    os.close(child_fd)
            elif stat.S_ISREG(info.st_mode):
                total += info.st_size
                minimum_zip_size += 76 + 2 * len(relative.encode("utf-8")) + info.st_size
                if total > RAW_CAP:
                    raise TransportResourceExceeded("raw attempt exceeds exact 64 MiB cap")
                if minimum_zip_size > ARCHIVE_CAP:
                    raise TransportResourceExceeded("deterministic archive cannot fit exact 64 MiB cap")
                record = {"path": relative, **_file_hash(root / relative, RAW_CAP, deadline)}
                if record["size"] != info.st_size:
                    raise TransportError("source changed during inventory")
                entries.append(record)
            else:
                raise TransportError("attempt contains a symlink or special file")
    try:
        walk(fd, "")
    finally:
        os.close(fd)
    return sorted(entries, key=lambda item: item["path"])


class _BoundedArchive(io.BufferedIOBase):
    """A seekable ZIP writer that never writes past the archive cap."""
    def __init__(self, handle: BinaryIO, deadline: float):
        self.handle = handle
        self.deadline = deadline
        self.failed = False

    def tell(self) -> int:
        return self.handle.tell()

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        return self.handle.seek(offset, whence)

    def seekable(self) -> bool:
        return True

    def writable(self) -> bool:
        return True

    def write(self, data: bytes) -> int:
        _tick(self.deadline)
        if self.failed or self.tell() + len(data) > ARCHIVE_CAP:
            self.failed = True
            raise TransportResourceExceeded("transport archive exceeds exact 64 MiB cap")
        try:
            written = self.handle.write(data)
            if written != len(data):
                raise OSError("short archive write")
            return written
        except Exception:
            self.failed = True
            raise

    def flush(self) -> None:
        if not self.handle.closed:
            self.handle.flush()


def _archive(root: Path, files: Sequence[Mapping[str, Any]], path: Path, deadline: float) -> None:
    with path.open("xb") as handle:
        bounded = _BoundedArchive(handle, deadline)
        archive = zipfile.ZipFile(bounded, "w", compression=zipfile.ZIP_STORED,
                                  allowZip64=False, strict_timestamps=True)
        try:
            for record in files:
                _tick(deadline)
                info = zipfile.ZipInfo(record["path"], _ZIP_DATE)
                info.create_system = 3
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = (stat.S_IFREG | 0o600) << 16
                info.file_size = record["size"]
                digest = hashlib.sha256()
                size = 0
                source, before = _open_regular(root / record["path"])
                with source, archive.open(info, "w", force_zip64=False) as member:
                    while True:
                        _tick(deadline)
                        block = source.read(min(CHUNK_SIZE, record["size"] - size + 1))
                        if not block:
                            break
                        size += len(block)
                        if size > record["size"]:
                            raise TransportError("source grew after inventory")
                        member.write(block)
                        digest.update(block)
                    if _identity(before) != _identity(os.fstat(source.fileno())):
                        raise TransportError("source changed during packaging")
                if size != record["size"] or digest.hexdigest() != record["sha256"]:
                    raise TransportError("source bytes changed after inventory")
            archive.close()
            handle.flush()
            os.fsync(handle.fileno())
        except Exception as error:
            # No central-directory cleanup may append after a failed write/cap.
            # Flush and fsync remain independent cleanup attempts, and neither
            # may erase the body's resource or integrity evidence.
            archive.fp = None
            secondary = list(getattr(error, 'transport_secondary_failures', ()))
            for phase, operation in (('archive_final_flush', handle.flush),
                                     ('archive_final_fsync', lambda: os.fsync(handle.fileno()))):
                try:
                    operation()
                except Exception as later:
                    secondary.append(_typed_failure(later, phase))
            error.transport_secondary_failures = secondary
            raise


def _split(archive_path: Path, destination: Path, deadline: float) -> list[dict[str, Any]]:
    parts = []
    source, _ = _open_regular(archive_path)
    with source:
        order = 1
        while True:
            _tick(deadline)
            first = source.read(min(CHUNK_SIZE, PART_CAP))
            if not first:
                break
            name = f"part-{order:03d}.bin"
            partial = destination / (name + ".partial")
            digest = hashlib.sha256()
            size = 0
            with partial.open("xb") as output:
                block = first
                while block:
                    _tick(deadline)
                    output.write(block)
                    digest.update(block)
                    size += len(block)
                    block = source.read(min(CHUNK_SIZE, PART_CAP - size)) if size < PART_CAP else b""
                output.flush()
                os.fsync(output.fileno())
            _finalize(partial, destination / name)
            parts.append({"order": order, "path": name, "size": size, "sha256": digest.hexdigest()})
            order += 1
    return parts


def package_attempt(root: Path, destination: Path, *, deadline_monotonic: float | None = None) -> dict[str, Any]:
    """Package existing evidence only; never imports any attempt source."""
    created = None
    stage = "packaging_preflight"
    try:
        deadline = _deadline(deadline_monotonic)
        root = _absolute(root)
        destination = _absolute(destination)
        if root == destination or root in destination.parents or destination in root.parents:
            raise TransportError("source and destination must be disjoint")
        fd = _directory_fd(root)
        os.close(fd)
        created = _new_destination(destination)
        stage = "raw_inventory"
        files = _inventory(root, deadline)
        stage = "deterministic_archive"
        partial = created / "attempt.zip.partial"
        _archive(root, files, partial, deadline)
        _finalize(partial, created / "attempt.zip")
        archive_record = {"path": "attempt.zip", "format": "zip-stored-v1",
                          **_file_hash(created / "attempt.zip", ARCHIVE_CAP, deadline)}
        stage = "ordered_parts"
        parts = _split(created / "attempt.zip", created, deadline)
        # Detect added/deleted/changed files across the complete source capture.
        if _inventory(root, deadline) != files:
            raise TransportError("raw inventory changed during packaging")
        manifest = {
            "schema": MANIFEST_SCHEMA, "raw_size": sum(item["size"] for item in files),
            "files": files, "archive": archive_record, "parts": parts,
            "limits": {"raw_bytes": RAW_CAP, "archive_bytes": ARCHIVE_CAP,
                       "part_bytes": PART_CAP, "provider_zip_strictly_below_bytes": PROVIDER_WRAPPER_LIMIT},
        }
        _json_file(created / "transport-manifest.json", manifest, MIB)
        return {"schema": "worker38.transport-report.v1", "status": "packaged",
                "manifest": manifest, "manifest_path": str(created / "transport-manifest.json"),
                "local_paths": {part["path"]: str(created / part["path"]) for part in parts},
                "custody": "pending", "provider_origin_authenticated": False}
    except Exception as exc:
        return _failure(stage, exc, created)


def _manifest(value: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if (not isinstance(value, Mapping) or set(value) != {"schema", "raw_size", "files", "archive", "parts", "limits"}
            or value.get("schema") != MANIFEST_SCHEMA):
        raise TransportError("unsupported transport manifest schema")
    if value.get("limits") != {"raw_bytes": RAW_CAP, "archive_bytes": ARCHIVE_CAP,
                              "part_bytes": PART_CAP,
                              "provider_zip_strictly_below_bytes": PROVIDER_WRAPPER_LIMIT}:
        raise TransportError("manifest changes frozen transport limits")
    files = value.get("files")
    parts = value.get("parts")
    archive = value.get("archive")
    if not isinstance(files, list) or not isinstance(parts, list) or not isinstance(archive, Mapping):
        raise TransportError("invalid transport manifest inventory")
    names = set()
    total = 0
    for entry in files:
        if not isinstance(entry, Mapping) or set(entry) != {"path", "size", "sha256"}:
            raise TransportError("invalid raw inventory record")
        name = _name(entry["path"])
        if name in {"transport-manifest.json", "upload-plan.txt", "upload-seal.json"}:
            raise TransportError("post-archive transport metadata cannot be a raw archive member")
        if name in names:
            raise TransportError("duplicate raw inventory path")
        names.add(name)
        total += _int(entry["size"], "raw file size", RAW_CAP)
        _hash(entry["sha256"])
    if files != sorted(files, key=lambda item: item["path"]):
        raise TransportError("raw inventory is not ordered")
    for name in names:
        if any(parent.as_posix() in names for parent in PurePosixPath(name).parents if str(parent) != "."):
            raise TransportError("file/directory path collision")
    if total > RAW_CAP or _int(value.get("raw_size"), "raw total", RAW_CAP) != total:
        raise TransportError("raw total mismatch or cap overflow")
    if (archive.get("path") != "attempt.zip" or archive.get("format") != "zip-stored-v1"
            or set(archive) != {"path", "format", "size", "sha256"}):
        raise TransportError("invalid archive descriptor")
    archive_size = _int(archive["size"], "archive size", ARCHIVE_CAP)
    if archive_size < 22:
        raise TransportError("archive smaller than ZIP end record")
    _hash(archive["sha256"])
    if not parts or len(parts) != (archive_size + PART_CAP - 1) // PART_CAP:
        raise TransportError("invalid ordered part count")
    for index, entry in enumerate(parts, 1):
        if not isinstance(entry, Mapping) or set(entry) != {"order", "path", "size", "sha256"}:
            raise TransportError("invalid transport part record")
        if type(entry["order"]) is not int or entry["order"] != index or entry["path"] != f"part-{index:03d}.bin":
            raise TransportError("transport part order/name mismatch")
        size = _int(entry["size"], "part size", PART_CAP)
        expected = PART_CAP if index < len(parts) else archive_size - PART_CAP * (len(parts) - 1)
        if size != expected:
            raise TransportError("transport part length mismatch")
        _hash(entry["sha256"])
    return files, parts, dict(archive)


def _zip_members(archive: zipfile.ZipFile, *, raw: bool, manifest_allowed: bool = False) -> list[zipfile.ZipInfo]:
    members = archive.infolist()
    seen = set()
    total = 0
    for info in members:
        name = _name(info.filename)
        if _name(info.orig_filename) != name:
            raise TransportError("ZIP filename was normalized or truncated")
        if name in seen or info.is_dir():
            raise TransportError("duplicate ZIP member or unexpected directory entry")
        seen.add(name)
        mode = info.external_attr >> 16
        kind = stat.S_IFMT(mode)
        if kind not in (0, stat.S_IFREG) or info.flag_bits & (1 | 64) or info.external_attr & 0x10:
            raise TransportError("special/symlink/encrypted ZIP member")
        if info.compress_type not in ((zipfile.ZIP_STORED,) if raw else (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
            raise TransportError("unsupported ZIP compression")
        cap = RAW_CAP if raw else (MIB if name == "transport-manifest.json" and manifest_allowed else PART_CAP)
        total += _int(info.file_size, "ZIP member size", cap)
        if total > (RAW_CAP if raw else PART_CAP + (MIB if manifest_allowed else 0)):
            raise TransportError("ZIP uncompressed size overflow")
    return members


def _copy_zip_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo, output: BinaryIO | None,
                     expected: Mapping[str, Any], deadline: float | None) -> dict[str, Any]:
    digest = hashlib.sha256()
    size = 0
    with archive.open(info, "r") as source:
        while True:
            _tick(deadline)
            block = source.read(min(CHUNK_SIZE, expected["size"] - size + 1))
            if not block:
                break
            size += len(block)
            if size > expected["size"]:
                raise TransportError("ZIP member exceeds declared inventory")
            if output is not None:
                output.write(block)
            digest.update(block)
    result = {"size": size, "sha256": digest.hexdigest()}
    if result != {"size": expected["size"], "sha256": expected["sha256"]}:
        raise TransportError("ZIP member bytes differ from inventory")
    return result


def _manifest_bytes(value):
    raw = (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False) + '\n').encode('ascii')
    if not 0 < len(raw) <= MIB:
        raise TransportError('compact transport manifest exceeds1MiB')
    return raw


def _provider_manifest(raw, expected):
    """Strict bounded JSON only after exact member/expanded-byte/CRC checks."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise TransportError('duplicate provider manifest key')
            result[key] = value
        return result
    def constant(value):
        raise TransportError('nonfinite provider manifest')
    try:
        actual = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
        if type(actual) is not dict or set(actual) != {'schema', 'raw_size', 'files', 'archive', 'parts', 'limits'}:
            raise TransportError('provider manifest schema')
        if actual['parts'] != expected['parts']:
            raise TransportError('provider manifest ordered part binding mismatch')
        if any(actual[key] != expected[key] for key in ('archive', 'files', 'raw_size')):
            raise TransportError('provider manifest archive inventory binding mismatch')
        if raw != _manifest_bytes(expected):
            raise TransportError('provider original manifest bytes or frozen schema differ')
    except (UnicodeError, json.JSONDecodeError, ValueError, TypeError, KeyError) as error:
        if isinstance(error, TransportError): raise
        raise TransportError('invalid original compact manifest') from error
    return {'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _wrappers(descriptors: Sequence[Mapping[str, Any]] | None, parts: Sequence[Mapping[str, Any]],
              deadline: float | None, manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    if descriptors is None:
        return []
    if not isinstance(descriptors, (list, tuple)) or len(descriptors) != len(parts):
        raise TransportError("one supplied provider wrapper required for every part")
    if not isinstance(manifest, Mapping) or manifest.get("schema") != MANIFEST_SCHEMA or manifest.get("parts") != list(parts):
        raise TransportError("original manifest and wrapper parts must agree")
    _manifest_bytes(manifest)
    expected_parts = {part["path"]: part for part in parts}
    checked = []
    seen = set()
    for descriptor in descriptors:
        _tick(deadline)
        if not isinstance(descriptor, Mapping):
            raise TransportError("invalid provider wrapper descriptor")
        part_name = descriptor.get("part_path")
        if part_name not in expected_parts or part_name in seen:
            raise TransportError("missing/duplicate/unknown provider wrapper part")
        seen.add(part_name)
        member_name = _name(descriptor.get("member_name"))
        if member_name != part_name:
            raise TransportError("exact literal provider part member required")
        first = part_name == "part-001.bin"
        manifest_record = None
        wrapper_path = _absolute(descriptor["path"])
        wrapper_bytes = _file_hash(wrapper_path, PROVIDER_WRAPPER_LIMIT - 1, deadline)
        receipt = descriptor.get("download_receipt")
        if not isinstance(receipt, Mapping) or receipt.get("provider") != "github_actions" or receipt.get("operation") != "download":
            raise TransportError("missing asserted external provider download receipt")
        for field in ("event_id", "artifact_id", "repository", "run_id", "run_attempt", "completed_at"):
            if not isinstance(receipt.get(field), str) or not receipt[field]:
                raise TransportError("provider download receipt is incomplete")
        _timestamp(receipt["completed_at"])
        if receipt.get("sha256") != wrapper_bytes["sha256"] or receipt.get("size") != wrapper_bytes["size"]:
            raise TransportError("provider wrapper differs from asserted download receipt")
        source, before = _open_regular(wrapper_path)
        with source, zipfile.ZipFile(source, "r") as archive:
            members = _zip_members(archive, raw=False, manifest_allowed=first)
            expected_names = {part_name, 'transport-manifest.json'} if first else {part_name}
            if {info.filename for info in members} != expected_names or len(members) != len(expected_names):
                raise TransportError('provider wrapper exact ordinal member set mismatch')
            by_name = {info.filename: info for info in members}
            part_member = by_name[part_name]
            if part_member.file_size != expected_parts[part_name]['size']:
                raise TransportError('provider wrapper member size differs from exact part')
            payload = _copy_zip_member(archive, part_member, None, expected_parts[part_name], deadline)
            if first:
                _tick(deadline)
                member = by_name['transport-manifest.json']
                if not 0 < member.file_size <= MIB:
                    raise TransportError('compact provider manifest exceeds1MiB')
                raw_manifest = archive.read(member)
                if len(raw_manifest) != member.file_size:
                    raise TransportError('compact provider manifest expanded length mismatch')
                manifest_record = _provider_manifest(raw_manifest, manifest)
            # Bind structural/payload checks to these same opened wrapper bytes,
            # not only a prior pathname-based hash that could race replacement.
            source.seek(0)
            checked_digest = hashlib.sha256()
            checked_size = 0
            while True:
                _tick(deadline)
                block = source.read(min(CHUNK_SIZE, PROVIDER_WRAPPER_LIMIT - checked_size))
                if not block:
                    break
                checked_size += len(block)
                if checked_size >= PROVIDER_WRAPPER_LIMIT:
                    raise TransportError("provider wrapper reaches 32 MiB download limit")
                checked_digest.update(block)
            if {"size": checked_size, "sha256": checked_digest.hexdigest()} != wrapper_bytes:
                raise TransportError("opened provider wrapper differs from download bytes")
            if _identity(before) != _identity(os.fstat(source.fileno())):
                raise TransportError("provider wrapper changed during verification")
        checked.append({"part_path": part_name, "wrapper_path": str(wrapper_path),
                        "wrapper": wrapper_bytes, "payload": payload, "manifest": manifest_record,
                        "asserted_download_receipt": {key: receipt[key] for key in
                            ("provider", "operation", "event_id", "artifact_id", "repository",
                             "run_id", "run_attempt", "completed_at", "size", "sha256")},
                        "external_origin_authenticated": False})
    return sorted(checked, key=lambda item: item["part_path"])


def verify_provider_wrappers(descriptors: Sequence[Mapping[str, Any]],
                             parts: Sequence[Mapping[str, Any]], *, transport_manifest: Mapping[str, Any], repository: str,
                             workflow_run: str, workflow_attempt: str,
                             deadline_monotonic: float | None = None) -> list[dict[str, Any]]:
    """Require ordinal-specific outer ZIP and original manifest proof before classification.

    The caller must authenticate and externally pin GitHub download events along
    with the Drive events. These local checks cannot authenticate their origin.
    No directory is created and no fresh time allowance is started here. An
    optional supplied deadline is carried unchanged; None means caller-owned
    external time supervision, not proof of a completed preservation time gate.
    Lower-level verify_transport may still omit wrappers for local-only checks.
    """
    deadline = None if deadline_monotonic is None else _deadline(deadline_monotonic)
    if (repository != "carabinshely/bandido-alcatraz-solve" or
            type(workflow_run) is not str or not re.fullmatch(r"[1-9][0-9]*", workflow_run) or
            workflow_attempt != "1"):
        raise TransportError("invalid authenticated provider workflow identity")
    if (not isinstance(parts, (list, tuple)) or not parts or
            len(parts) > (ARCHIVE_CAP + PART_CAP - 1) // PART_CAP or
            not isinstance(descriptors, (list, tuple)) or len(descriptors) != len(parts)):
        raise TransportError("mandatory provider wrapper coverage differs from actual parts")
    seen_artifacts = set()
    seen_events = set()
    total_bytes = 0
    for order, (part, descriptor) in enumerate(zip(parts, descriptors), 1):
        _tick(deadline)
        if (not isinstance(part, Mapping) or type(part.get("order")) is not int or
                part["order"] != order or part.get("path") != f"part-{order:03d}.bin"):
            raise TransportError("provider proof requires exact ordered part descriptors")
        size = _int(part.get("size"), "part size", PART_CAP)
        if size == 0:
            raise TransportError("empty transport payload part")
        _hash(part.get("sha256"))
        total_bytes += size
        if total_bytes > ARCHIVE_CAP:
            raise TransportError("provider parts exceed exact archive cap")
        required = {"order", "part_path", "member_name", "path", "size", "sha256", "download_receipt"}
        if not isinstance(descriptor, Mapping) or not required <= descriptor.keys():
            raise TransportError("actual retained provider wrapper descriptor required")
        if (type(descriptor["order"]) is not int or descriptor["order"] != order or
                descriptor["part_path"] != part["path"] or descriptor["member_name"] != part["path"]):
            raise TransportError("provider wrapper order/part/member identity mismatch")
        if not isinstance(descriptor["path"], (str, Path)) or not str(descriptor["path"]):
            raise TransportError("retained provider ZIP path required")
        wrapper_size = _int(descriptor["size"], "provider ZIP size", PROVIDER_WRAPPER_LIMIT - 1)
        if wrapper_size == 0:
            raise TransportError("empty provider ZIP")
        wrapper_hash = _hash(descriptor["sha256"])
        receipt = descriptor["download_receipt"]
        if not isinstance(receipt, Mapping):
            raise TransportError("authenticated provider download receipt required")
        if (receipt.get("provider") != "github_actions" or receipt.get("operation") != "download" or
                receipt.get("repository") != repository or receipt.get("run_id") != workflow_run or
                receipt.get("run_attempt") != workflow_attempt or
                receipt.get("artifact_name") != f"worker38-{workflow_run}-1-part-{order:03d}"):
            raise TransportError("provider artifact does not match authenticated workflow/part")
        artifact_id = receipt.get("artifact_id")
        event_id = receipt.get("event_id")
        if (type(artifact_id) is not str or not re.fullmatch(r"[1-9][0-9]*", artifact_id) or
                artifact_id in seen_artifacts or type(event_id) is not str or not event_id or
                event_id in seen_events):
            raise TransportError("unique provider artifact/download event identity required")
        seen_artifacts.add(artifact_id)
        seen_events.add(event_id)
        if (type(receipt.get("size")) is not int or receipt["size"] != wrapper_size or
                receipt.get("sha256") != wrapper_hash):
            raise TransportError("provider ZIP pins differ from authenticated download receipt")
        _timestamp(receipt.get("completed_at"))
    checked = _wrappers(descriptors, parts, deadline, transport_manifest)
    for item, descriptor in zip(checked, descriptors):
        item["order"] = descriptor["order"]
        item["asserted_download_receipt"]["artifact_name"] = descriptor["download_receipt"]["artifact_name"]
    return checked


def verify_transport(manifest: Mapping[str, Any], local_paths: Mapping[str, Path | str],
                     destination: Path, *, provider_wrappers: Sequence[Mapping[str, Any]] | None = None,
                     deadline_monotonic: float | None = None) -> dict[str, Any]:
    """Stage 1: independently reassemble supplied bytes, extract and rehash them."""
    created = None
    stage = "transport_preflight"
    try:
        deadline = _deadline(deadline_monotonic)
        files, parts, archive_record = _manifest(manifest)
        if not isinstance(local_paths, Mapping) or set(local_paths) != {part["path"] for part in parts}:
            raise TransportError("supplied part mapping differs from exact manifest")
        destination = _absolute(destination)
        for source in local_paths.values():
            if destination == _absolute(source) or destination in _absolute(source).parents:
                raise TransportError("readback destination contains transport source")
        created = _new_destination(destination)
        stage = "provider_wrapper_bytes"
        wrapper_checks = _wrappers(provider_wrappers, parts, deadline, manifest)
        stage = "part_reassembly"
        partial = created / "attempt.zip.partial"
        archive_digest = hashlib.sha256()
        total = 0
        with partial.open("xb") as output:
            for expected in parts:
                source, before = _open_regular(local_paths[expected["path"]])
                digest = hashlib.sha256()
                size = 0
                with source:
                    if before.st_size != expected["size"]:
                        raise TransportError("transport part size mismatch")
                    while True:
                        _tick(deadline)
                        block = source.read(min(CHUNK_SIZE, expected["size"] - size + 1))
                        if not block:
                            break
                        size += len(block)
                        total += len(block)
                        if size > expected["size"] or total > ARCHIVE_CAP:
                            raise TransportError("transport part/archive overflow")
                        digest.update(block)
                        archive_digest.update(block)
                        output.write(block)
                    if _identity(before) != _identity(os.fstat(source.fileno())):
                        raise TransportError("transport part changed during readback")
                if size != expected["size"] or digest.hexdigest() != expected["sha256"]:
                    raise TransportError("transport part hash mismatch")
            output.flush()
            os.fsync(output.fileno())
        if total != archive_record["size"] or archive_digest.hexdigest() != archive_record["sha256"]:
            raise TransportError("reassembled archive size/hash mismatch")
        _finalize(partial, created / "attempt.zip")
        stage = "raw_extraction"
        raw_dir = created / "raw"
        os.mkdir(raw_dir, 0o700)
        source, before = _open_regular(created / "attempt.zip")
        with source, zipfile.ZipFile(source, "r") as archive:
            members = _zip_members(archive, raw=True)
            if [info.filename for info in members] != [item["path"] for item in files]:
                raise TransportError("archive raw file inventory/order mismatch")
            for info, expected in zip(members, files):
                _tick(deadline)
                if info.file_size != expected["size"]:
                    raise TransportError("archive raw file size mismatch")
                target = raw_dir / expected["path"]
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with target.open("xb") as output:
                    _copy_zip_member(archive, info, output, expected, deadline)
                    output.flush()
                    os.fsync(output.fileno())
                _fsync_dir(target.parent)
            if _identity(before) != _identity(os.fstat(source.fileno())):
                raise TransportError("reassembled archive changed during extraction")
        _fsync_dir(raw_dir)
        stage = "independent_raw_readback"
        archive_readback = _file_hash(created / "attempt.zip", ARCHIVE_CAP, deadline)
        if archive_readback != {"size": archive_record["size"], "sha256": archive_record["sha256"]}:
            raise TransportError("persisted archive changed after reassembly")
        # A second open/read pass verifies actual newly persisted extraction bytes.
        observed = _inventory(raw_dir, deadline)
        if observed != files:
            raise TransportError("persisted raw readback differs from manifest")
        report = {"schema": "worker38.transport-report.v1", "status": "local_transport_verified",
                  "stage": "local_transport_readback", "destination": str(created),
                  "archive": archive_record, "parts": parts, "files": observed,
                  "raw_size": sum(item["size"] for item in observed),
                  "provider_wrappers": wrapper_checks,
                  "provider_wrappers_supplied": provider_wrappers is not None,
                  "provider_origin_authenticated": False,
                  "custody": "pending"}
        _json_file(created / "local-transport-verification.json", report)
        return report
    except Exception as exc:
        return _failure(stage, exc, created)


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise TransportError("missing external operation timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TransportError("invalid external operation timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise TransportError("external operation timestamp must be UTC")
    return parsed


def _drive_url(value: Any, file_id: str) -> str:
    if not isinstance(value, str):
        raise TransportError("missing Drive direct URL")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.netloc != "drive.google.com" or parsed.fragment:
        raise TransportError("Drive direct URL has untrusted origin")
    valid_path = parsed.path == f"/file/d/{file_id}/view" and not parsed.query
    query = parse_qs(parsed.query, keep_blank_values=True)
    valid_download = parsed.path in ("/uc", "/open") and query.get("id") == [file_id] and set(query) <= {"id", "export"}
    if not (valid_path or valid_download):
        raise TransportError("Drive URL does not identify exact file ID")
    return value


def _drive_receipt(value: Any, operation: str, expected: Mapping[str, Any], file_id: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TransportError("missing external Drive operation receipt")
    if value.get("provider") != "google_drive" or value.get("operation") != operation or value.get("file_id") != file_id:
        raise TransportError("Drive operation receipt identity mismatch")
    if not isinstance(value.get("event_id"), str) or not value["event_id"]:
        raise TransportError("Drive operation receipt missing independent event ID")
    _timestamp(value.get("completed_at"))
    if value.get("size") != expected["size"] or value.get("sha256") != expected["sha256"]:
        raise TransportError("Drive operation receipt byte identity mismatch")
    if operation == "upload" and value.get("parent_folder_id") != CANONICAL_FOLDER_ID:
        raise TransportError("Drive upload receipt does not target canonical Raw folder")
    keys = ("provider", "operation", "file_id", "event_id", "completed_at", "size", "sha256", "parent_folder_id")
    return {key: value[key] for key in keys if key in value}


def verify_custody(manifest: Mapping[str, Any], downloaded_mapping: Mapping[str, Mapping[str, Any]],
                   *, deadline_monotonic: float | None = None) -> dict[str, Any]:
    """Stage 2: verify fresh supplied Drive downloads; external custody stays pending.

    Freshness here is consistency checking only. Parent authorization/provenance
    validation is indispensable and is never inferred from IDs, URLs or receipts.
    A fresh exclusive verification directory is retained next to the downloads.
    """
    created = None
    stage = "canonical_readback_preflight"
    try:
        deadline = _deadline(deadline_monotonic)
        _, parts, _ = _manifest(manifest)
        if not isinstance(downloaded_mapping, Mapping) or set(downloaded_mapping) != {part["path"] for part in parts}:
            raise TransportError("fresh Drive download mapping must cover exactly all parts")
        local_paths = {}
        drive_files = []
        file_ids = set()
        download_inodes = set()
        for expected in parts:
            _tick(deadline)
            descriptor = downloaded_mapping[expected["path"]]
            if not isinstance(descriptor, Mapping):
                raise TransportError("invalid Drive readback descriptor")
            local_path = _absolute(descriptor["path"])
            upload_input = _absolute(descriptor["upload_input_path"])
            _free(local_path.parent)
            if local_path == upload_input:
                raise TransportError("fresh download cannot reuse upload-input path")
            download_handle, downloaded_stat = _open_regular(local_path)
            download_handle.close()
            upload_handle, uploaded_stat = _open_regular(upload_input)
            upload_handle.close()
            inode = (downloaded_stat.st_dev, downloaded_stat.st_ino)
            if inode == (uploaded_stat.st_dev, uploaded_stat.st_ino) or inode in download_inodes:
                raise TransportError("fresh downloads cannot alias upload input or each other")
            download_inodes.add(inode)
            file_id = descriptor.get("drive_file_id")
            if not isinstance(file_id, str) or not _DRIVE_ID.fullmatch(file_id) or file_id in file_ids:
                raise TransportError("missing/invalid/duplicate Drive file ID")
            file_ids.add(file_id)
            direct_url = _drive_url(descriptor.get("direct_url"), file_id)
            upload = _drive_receipt(descriptor.get("upload_receipt"), "upload", expected, file_id)
            download = _drive_receipt(descriptor.get("download_receipt"), "download", expected, file_id)
            if upload["event_id"] == download["event_id"] or _timestamp(download["completed_at"]) <= _timestamp(upload["completed_at"]):
                raise TransportError("fresh Drive download must follow a distinct completed upload")
            for path in (upload_input, local_path):
                actual = _file_hash(path, PART_CAP, deadline)
                if actual != {"size": expected["size"], "sha256": expected["sha256"]}:
                    raise TransportError("Drive upload input or readback bytes differ from transport part")
            local_paths[expected["path"]] = local_path
            drive_files.append({"order": expected["order"], "path": expected["path"],
                                "drive_file_id": file_id, "direct_url": direct_url,
                                "size": expected["size"], "sha256": expected["sha256"],
                                "asserted_upload_receipt": upload, "asserted_download_receipt": download})
        stage = "canonical_byte_reassembly"
        parent = next(iter(local_paths.values())).parent
        _free(parent)
        created = Path(tempfile.mkdtemp(prefix="worker38-custody-readback-", dir=parent))
        _fsync_dir(parent)
        readback = verify_transport(manifest, local_paths, created / "verification", deadline_monotonic=deadline)
        if readback.get("status") != "local_transport_verified":
            # Preserve the nested byte verifier's already typed primary and
            # ordered secondary evidence. A new generic error would turn a
            # resource interruption into a false integrity attribution.
            return {**readback, 'stage': 'canonical_byte_reassembly',
                    'readback_stage': readback.get('stage'), 'custody': 'blocked'}
        report = {"schema": "worker38.custody-report.v1", "status": "local_canonical_readback_verified",
                  "custody": "pending", "local_readback_verified": True,
                  "external_provenance_authenticated": False,
                  "canonical_folder_id": CANONICAL_FOLDER_ID, "drive_files": drive_files,
                  "readback_report": str(created / "verification" / "local-transport-verification.json"),
                  "archive": readback["archive"], "files": readback["files"],
                  "requirements_before_custody_verified": [
                      "Independently authenticate each cited upload/download event against actual successful authorized Drive tool results",
                      "Verify each upload's canonical Raw parent folder and every returned Drive ID/direct URL",
                      "Establish each local readback path came from a fresh download of that stored Drive ID after upload completed",
                      "Bind the independently authenticated events to every locally checked size/SHA256 and exact frozen manifest",
                      "Verify all actual GitHub provider ZIP wrappers are strictly below 32 MiB and match their payload parts",
                      "Keep failed and incomplete evidence; custody never changes execution outcome or grants a rerun",
                  ]}
        _json_file(created / "canonical-readback-verification.json", report)
        return report
    except Exception as exc:
        return _failure(stage, exc, created)


UPLOAD_PLAN_LIMIT = 4096
UPLOAD_SEAL_LIMIT = 16384
UPLOAD_ALLOCATION = 'worker38-synthetic-profile-01'


def literal_upload_path(value):
    """Literal ASCII selection only; never escape or expand glob syntax."""
    value = str(value)
    if (len(value) > 4096 or re.fullmatch(r'/[A-Za-z0-9._/-]+', value, re.ASCII) is None
            or any(part in ('', '.', '..') for part in value.split('/')[1:])):
        raise TransportError('upload path is not an eligible literal absolute path')
    return Path(value)


def _seal_stat(info):
    return {'device': info.st_dev, 'inode': info.st_ino, 'mode': stat.S_IMODE(info.st_mode),
            'uid': info.st_uid, 'gid': info.st_gid, 'nlink': info.st_nlink,
            'size_bytes': info.st_size, 'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns}


def _sealed_file(path, expected, cap, deadline, *, seal=False):
    """Hold a no-follow regular single-link file through hash/fsync/seal/readback."""
    source, before = _open_regular(literal_upload_path(path))
    with source:
        _tick(deadline)
        if 'sealed' in expected and _seal_stat(before) != expected['sealed']:
            raise TransportError('sealed upload file stat identity changed')
        if before.st_uid != os.getuid() or before.st_nlink != 1 or stat.S_IMODE(before.st_mode) & 0o022:
            raise TransportError('upload payload owner/link/private-write proof failed')
        if not 0 < before.st_size <= cap or before.st_size != expected['size']:
            raise TransportError('upload payload size differs from its fixed manifest')
        digest = hashlib.sha256(); count = 0
        while True:
            _tick(deadline)
            data = source.read(min(CHUNK_SIZE, before.st_size - count + 1))
            if not data: break
            count += len(data)
            if count > before.st_size: raise TransportError('upload payload grew during sealing')
            digest.update(data)
        if count != expected['size'] or digest.hexdigest() != expected['sha256']:
            raise TransportError('upload payload bytes differ from original manifest')
        current = os.fstat(source.fileno())
        if _seal_stat(current) != _seal_stat(before) or _seal_stat(path.lstat()) != _seal_stat(before):
            raise TransportError('upload payload identity changed before seal')
        if seal:
            _tick(deadline)
            os.fsync(source.fileno())
            os.fchmod(source.fileno(), 0o400)
            os.fsync(source.fileno())
        after = os.fstat(source.fileno())
        if (stat.S_IMODE(after.st_mode) != 0o400 or after.st_nlink != 1 or
                _seal_stat(path.lstat()) != _seal_stat(after) or
                (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) !=
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
            raise TransportError('upload payload seal or retained identity unconfirmed')
        _tick(deadline)
        return {'path': path.name, 'size': count, 'sha256': digest.hexdigest(),
                'before': _seal_stat(before), 'sealed': _seal_stat(after)}


def _writer_handoff(value, attempt, run, deadline):
    fields = {'schema', 'attempt_id', 'preservation_pid', 'coordinator_state', 'coordinator_pid',
        'coordinator_start_ticks', 'evaluator_entries_upper_bound', 'admission_exited',
        'owned_children_reaped', 'cleanup_confirmed', 'no_further_writes', 'evidence'}
    if (type(value) is not dict or set(value) != fields or
            value['schema'] != 'worker38-upload-writer-handoff-v1' or
            value['attempt_id'] != 'worker38-' + run + '-1' or
            type(value['preservation_pid']) is not int or value['preservation_pid'] != os.getpid() or
            any(value[key] is not True for key in ('admission_exited', 'owned_children_reaped',
                                                  'cleanup_confirmed', 'no_further_writes'))):
        raise TransportError('confirmed fixed writer custody handoff required')
    count = value['evaluator_entries_upper_bound']
    if type(count) is not int or not 0 <= count <= 40:
        raise TransportError('writer handoff entry bounds unavailable')
    if value['coordinator_state'] == 'never_started':
        if value['coordinator_pid'] is not None or value['coordinator_start_ticks'] is not None or count != 0:
            raise TransportError('never-started coordinator needs proven zero entries')
    elif value['coordinator_state'] == 'exited':
        if (type(value['coordinator_pid']) is not int or value['coordinator_pid'] <= 0 or
                value['coordinator_pid'] == os.getpid() or
                type(value['coordinator_start_ticks']) is not int or value['coordinator_start_ticks'] <= 0):
            raise TransportError('exited coordinator identity unavailable')
    else:
        raise TransportError('unknown coordinator writer state')
    records = value['evidence']; seen = set()
    if type(records) is not list or not 2 <= len(records) <= 24:
        raise TransportError('bounded committed writer evidence required')
    allowed = {'writer-exit-observation.json', 'startup-receipt.json', 'startup-failure.json',
               'receipt.json', 'coordinator-restoration.json'}
    allowed |= {f'supervisor-cell-{index:02d}.json' for index in range(1, 21)}
    for record in records:
        if type(record) is not dict or set(record) != {'path', 'size_bytes', 'sha256'}:
            raise TransportError('writer evidence binding schema')
        name = record['path']
        _hash(record['sha256'])
        if type(record['size_bytes']) is not int or not 0 < record['size_bytes'] <= 2 * MIB:
            raise TransportError('bounded typed writer proof size required')
        if name not in allowed or name in seen: raise TransportError('fixed unique writer proof paths required')
        seen.add(name)
        actual = _file_hash(attempt / name, 2 * MIB, deadline)
        if actual != {'size': record['size_bytes'], 'sha256': record['sha256']}:
            raise TransportError('committed writer proof changed before seal')
    if ('writer-exit-observation.json' not in seen or
            not ({'startup-receipt.json', 'startup-failure.json'} & seen) or
            (value['coordinator_state'] == 'exited' and 'receipt.json' not in seen) or
            (value['coordinator_state'] == 'never_started' and 'startup-failure.json' not in seen)):
        raise TransportError('writer closure proof does not cover its claimed lifecycle')
    return value


def _upload_plan(manifest, run):
    parts = manifest['parts']; raw = _manifest_bytes(manifest)
    values = [('version', 'worker38-upload-plan-v1'), ('allocation_id', UPLOAD_ALLOCATION),
              ('run_id', run), ('run_attempt', '1'), ('part_count', str(len(parts))),
              ('manifest_name', 'transport-manifest.json'), ('manifest_size_bytes', str(len(raw))),
              ('manifest_sha256', hashlib.sha256(raw).hexdigest())]
    for index in range(1, 4):
        part = parts[index - 1] if index <= len(parts) else {'size': 0, 'sha256': '0' * 64}
        values.extend([(f'part_{index:03d}_name', f'part-{index:03d}.bin'),
                       (f'part_{index:03d}_size_bytes', str(part['size'])),
                       (f'part_{index:03d}_sha256', part['sha256'])])
    plan = ''.join(key + '=' + value + '\n' for key, value in values).encode('ascii')
    if len(plan) > UPLOAD_PLAN_LIMIT: raise TransportError('fixed upload plan exceeds4096bytes')
    return plan


def _new_control(path, raw, cap, deadline):
    if not 0 < len(raw) <= cap: raise TransportError('bounded upload control bytes required')
    _tick(deadline)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        offset = 0
        while offset < len(raw):
            _tick(deadline)
            count = os.write(fd, raw[offset:])
            if type(count) is not int or not 0 < count <= len(raw) - offset:
                raise OSError('upload control write made no progress')
            offset += count
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_dir(path.parent)
    return _sealed_file(path, {'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
                        cap, deadline, seal=True)


def seal_upload(cache_root, workflow_run, *, deadline_monotonic, writer_handoff):
    """Seal fixed existing output only; never launch, upload or renew authority.

    The trusted driver must establish actual writer exits/cleanup from bounded
    shell/process evidence before constructing the closed handoff. This function
    rebinds those exact committed records and seals only generated transport
    objects. A readable plan alone never implies this function returned ready.
    """
    destination = None
    try:
        cache = literal_upload_path(cache_root)
        if type(workflow_run) is not str or re.fullmatch('[1-9][0-9]{0,18}', workflow_run) is None:
            raise TransportError('fixed decimal upload run identity required')
        run = workflow_run
        durable = cache / 'worker38-synthetic-profile'
        allocation = durable / 'allocations' / UPLOAD_ALLOCATION
        attempt = allocation / ('run-' + run + '-attempt-1')
        destination = literal_upload_path(allocation / ('transport-' + run + '-attempt-1'))
        deadline = _deadline(deadline_monotonic)
        directories = []
        for path in (cache, durable, durable / 'allocations', allocation, attempt, destination):
            literal_upload_path(path)
            fd = _directory_fd(path)
            try:
                info = os.fstat(fd)
                if (info.st_mode & 0o022 or (path != cache and
                        (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700))):
                    raise TransportError('private owned upload directory custody required')
                if _seal_stat(path.lstat()) != _seal_stat(info):
                    raise TransportError('upload directory component identity changed')
                directories.append({'path': str(path), 'observed': _seal_stat(info)})
            finally:
                os.close(fd)
        _free(destination)
        handoff = _writer_handoff(writer_handoff, attempt, run, deadline)
        manifest_path = destination / 'transport-manifest.json'
        handle, info = _open_regular(manifest_path)
        with handle:
            if not 0 < info.st_size <= MIB: raise TransportError('original compact manifest bound')
            raw = handle.read(MIB + 1)
        manifest = json.loads(raw)
        files, parts, archive = _manifest(manifest)
        if raw != _manifest_bytes(manifest): raise TransportError('original canonical manifest bytes required')
        expected_names = {'attempt.zip', 'transport-manifest.json'} | {part['path'] for part in parts}
        actual_names = set()
        with os.scandir(destination) as children:
            for child in children:
                _tick(deadline)
                actual_names.add(child.name)
                if len(actual_names) > len(expected_names):
                    raise TransportError('unexpected transport writer output or partial file')
        if actual_names != expected_names:
            raise TransportError('unexpected transport writer output or partial file')
        records = []
        for record, cap in [(archive, ARCHIVE_CAP), *[(part, PART_CAP) for part in parts],
                            ({'path': 'transport-manifest.json', 'size': len(raw),
                              'sha256': hashlib.sha256(raw).hexdigest()}, MIB)]:
            path = literal_upload_path(destination / record['path'])
            records.append(_sealed_file(path, record, cap, deadline, seal=True))
        plan_raw = _upload_plan(manifest, run)
        proof = {'schema': 'worker38-upload-seal-v1', 'attempt_id': 'worker38-' + run + '-1',
                 'original_preservation_deadline_monotonic': deadline, 'writer_handoff': handoff,
                 'directories_before_seal': directories, 'files': records,
                 'plan': {'path': 'upload-plan.txt', 'size_bytes': len(plan_raw),
                          'sha256': hashlib.sha256(plan_raw).hexdigest()},
                 'transport_mode_after_confirmation': 0o500,
                 'custody_model': 'private trusted runner, completed or transferred writers; no atomic vendor fd handoff'}
        proof_raw = (json.dumps(proof, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('ascii')
        _new_control(destination / 'upload-seal.json', proof_raw, UPLOAD_SEAL_LIMIT, deadline)
        _new_control(destination / 'upload-plan.txt', plan_raw, UPLOAD_PLAN_LIMIT, deadline)
        fd = _directory_fd(destination)
        try:
            _tick(deadline)
            os.fchmod(fd, 0o500); os.fsync(fd)
            if stat.S_IMODE(os.fstat(fd).st_mode) != 0o500:
                raise TransportError('readonly transport directory seal unconfirmed')
        finally:
            os.close(fd)
        for record in records:
            _sealed_file(destination / record['path'], record,
                         ARCHIVE_CAP if record['path'] == 'attempt.zip' else
                         MIB if record['path'] == 'transport-manifest.json' else PART_CAP, deadline)
        for name, payload, cap in (('upload-plan.txt', plan_raw, UPLOAD_PLAN_LIMIT),
                                   ('upload-seal.json', proof_raw, UPLOAD_SEAL_LIMIT)):
            _sealed_file(destination / name, {'size': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}, cap, deadline)
        _tick(deadline)
        return {'schema': 'worker38-upload-readiness-v1', 'status': 'upload_ready', 'upload_ready': True,
                'plan_path': str(destination / 'upload-plan.txt'), 'part_count': len(parts),
                'manifest': {'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
                'original_preservation_deadline_monotonic': deadline,
                'control_output_bytes': len(plan_raw) + len(proof_raw), 'custody': 'pending', 'classification': None}
    except Exception as error:
        result = _failure('upload_seal', error, None)
        return {**result, 'upload_ready': False, 'transport_directory': str(destination) if destination else None}
