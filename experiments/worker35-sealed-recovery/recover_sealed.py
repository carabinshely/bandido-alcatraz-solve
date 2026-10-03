"""Preserve Worker35's already sealed transport; never execute project code.

This does not establish original raw-tree quiescence, archive member consistency,
scientific validity, or a completed experiment. All source opens are read-only.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
import sys
import urllib.request

REPO = "carabinshely/bandido-alcatraz-solve"
HEAD = "7ac2f62c9c5c9dcac9ec9b8770382960f985acc2"
RUN = 36990202101
JOB = 110784375570
RUNNER = "bandido-alcatraz-ci"
BRANCH = "refs/heads/research/worker35-sealed-recovery-36990202101"
RECEIPT_SHA = "027b6b35d75983ecf1760395418ff00d2df2a7fab63afee617bc73e4d8e3b3af"
ADMISSION_SHA = "c60ff9cd1813729fdad2c99ef337fd4727fc24bd5855114027cf64fc34cd3c76"
FREEZE_SHA = "f630a40f3f4fd1bf3135045ba5428e26e1f597937a49c67791f094830c2b025d"
MIB = 1024 * 1024
PART_LIMIT = 30 * MIB
ARCHIVE_LIMIT = 4 * 1024 * MIB
MANIFEST_LIMIT = 8 * MIB
METADATA_LIMIT = 29 * MIB
PARTS_LIMIT = (ARCHIVE_LIMIT + PART_LIMIT - 1) // PART_LIMIT


class Blocked(RuntimeError):
    pass


def require(ok, reason):
    if not ok:
        raise Blocked(reason)


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def parse(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "duplicate JSON key")
            value[key] = item
        return value
    def finite(value):
        result = float(value)
        require(math.isfinite(result), "nonfinite JSON number")
        return result
    value = json.loads(raw, object_pairs_hook=pairs, parse_float=finite, parse_constant=finite)
    require(type(value) is dict, "JSON object required")
    return value


def canonical_path(path):
    text = str(path)
    require(text.startswith("/") and os.path.normpath(text) == text, "noncanonical absolute path")
    require(not any(c in text for c in "\n\r\x00*?[]"), "unsafe path characters")
    return Path(text)


def open_dir(path, fresh=False):
    path = canonical_path(path)
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for index, part in enumerate(path.parts[1:]):
            if fresh:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=fd)
                except FileExistsError:
                    require(index != len(path.parts) - 2, "snapshot already exists")
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = new
        return fd
    except BaseException:
        os.close(fd)
        raise


def stamp(s):
    return [s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_gid, s.st_nlink,
            s.st_size, s.st_mtime_ns, s.st_ctime_ns]


def verify_dir(path, fd):
    check = open_dir(path)
    try:
        require(stamp(os.fstat(check)) == stamp(os.fstat(fd)), "directory path identity changed")
    finally:
        os.close(check)


def read_file(fd, name, limit):
    require(type(name) is str and re.fullmatch(r"[A-Za-z0-9_.-]+", name) and name not in (".", ".."), "unsafe basename")
    handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    try:
        before = os.fstat(handle)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, "single-link regular file required")
        require(before.st_uid == os.geteuid() and 0 <= before.st_size <= limit, "file owner/size mismatch")
        with os.fdopen(os.dup(handle), "rb") as stream:
            raw = stream.read(limit + 1)
        after = os.fstat(handle)
        require(len(raw) == before.st_size and len(raw) <= limit, "file size changed")
        require(stamp(before) == stamp(after) == stamp(os.stat(name, dir_fd=fd, follow_symlinks=False)), "file changed during read")
        return raw, stamp(after)
    finally:
        os.close(handle)


def write_new(fd, name, raw):
    require(re.fullmatch(r"[A-Za-z0-9_.-]+", name) and name not in (".", ".."), "unsafe output name")
    handle = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    with os.fdopen(handle, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.fsync(fd)


def names(fd, limit):
    result = []
    with os.scandir(fd) as items:
        for item in items:
            result.append(item.name)
            require(len(result) <= limit, "directory population exceeded")
    return sorted(result)


def hash_record(value, limit):
    require(type(value) is dict and set(value) == {"sha256", "size_bytes"}, "invalid hash record")
    require(type(value["size_bytes"]) is int and 0 <= value["size_bytes"] <= limit, "size exceeds bound")
    require(type(value["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]), "invalid SHA256")


def manifest_check(value):
    require(set(value) == {"schema", "files", "archive", "parts", "format", "shard_bytes"}, "manifest fields differ")
    require(value["schema"] == "worker35-artifact-manifest-v1" and value["format"] == "concatenated-zip-deflate6", "manifest format differs")
    require(type(value["shard_bytes"]) is int and value["shard_bytes"] == PART_LIMIT, "frozen shard size differs")
    hash_record(value["archive"], ARCHIVE_LIMIT)
    parts = value["parts"]
    require(type(parts) is list and 1 <= len(parts) <= PARTS_LIMIT, "part count out of bounds")
    total = 0
    for index, part in enumerate(parts, 1):
        require(type(part) is dict and set(part) == {"name", "sha256", "size_bytes"}, "invalid part fields")
        require(part["name"] == f"evidence.part-{index:05d}", "noncanonical or unordered part")
        hash_record({k: part[k] for k in ("sha256", "size_bytes")}, PART_LIMIT)
        require(part["size_bytes"] > 0, "empty shard")
        require(index == len(parts) or part["size_bytes"] == PART_LIMIT, "short nonfinal shard")
        total += part["size_bytes"]
    require(0 < total <= ARCHIVE_LIMIT and total == value["archive"]["size_bytes"], "archive size mismatch")
    files = value["files"]
    require(type(files) is dict and 1 <= len(files) <= 20000, "invalid file inventory size")
    expanded = 0
    for path, record in files.items():
        relative = PurePosixPath(path)
        require(not relative.is_absolute() and str(relative) == path and len(path.encode()) <= 4096 and ".." not in relative.parts, "unsafe manifest member")
        require(not any(c in path for c in "\n\r\x00\\") and path not in ("", "."), "unsafe member name")
        hash_record(record, 16 * 1024 * MIB)
        expanded += record["size_bytes"]
    require(expanded <= 16 * 1024 * MIB, "expanded bytes exceed frozen bound")
    require(files.get("receipt.json") == {"sha256": RECEIPT_SHA, "size_bytes": 160722}, "manifest original receipt differs from preserved receipt")
    return parts


def source_metadata(receipt, admission):
    require(receipt.get("expected_head") == HEAD and receipt.get("run_id") == str(RUN) and receipt.get("run_attempt") == "1", "receipt source identity differs")
    require(receipt.get("status") == "execution_blocked" and receipt.get("classification") is None and receipt.get("research_interpretation_performed") is False, "receipt terminal state differs")
    require(admission.get("expected_head") == HEAD and admission.get("run_id") == str(RUN) and admission.get("run_attempt") == "1", "admission identity differs")
    require(receipt.get("freeze_sha256") == admission.get("freeze_sha256") == FREEZE_SHA, "freeze identity differs")
    result = {}
    for key in ("source_at_initialization", "source_before", "source_at_finalization"):
        value = receipt.get(key)
        require(type(value) is dict and value.get("head") == HEAD, "missing original source provenance")
        result[key] = {k: value.get(k) for k in ("head", "tree", "python_version", "python_implementation", "executable_sha256")}
    return result


def validate_original(run, job):
    require(run.get("id") == RUN and run.get("run_attempt") == 1 and run.get("head_sha") == HEAD, "original run identity changed")
    require(run.get("repository", {}).get("full_name") == REPO and run.get("path") == ".github/workflows/quota-reserve-closure-development.yml", "original repository/workflow differs")
    require(run.get("status") == "completed" and run.get("conclusion") == "failure", "original run is not terminal failure")
    require(job.get("id") == JOB and job.get("run_id") == RUN and job.get("run_attempt") == 1 and job.get("head_sha") == HEAD, "original job identity differs")
    require(job.get("runner_id") == 2 and job.get("runner_name") == RUNNER, "original registered runner differs")
    require(job.get("status") == "completed" and job.get("conclusion") == "failure", "original job is not terminal failure")
    for label, outcome in (("Three complete fixed development phases", "cancelled"), ("Reconcile final status", "failure"), ("Preserve deterministic evidence shards", "success"), ("Upload complete or partial evidence always", "failure")):
        found = [s for s in job.get("steps", []) if s.get("name") == label]
        require(len(found) == 1 and found[0].get("status") == "completed" and found[0].get("conclusion") == outcome, "original packaging sequence differs")


def metadata_safe(fd):
    allowed = {"artifact-manifest.json", "original-receipt.json", "original-admission.json",
               "authenticated-actions-metadata.json", "recovery-report.json", "blocked-report.json"}
    listed = names(fd, len(allowed))
    require(set(listed) <= allowed, "unexpected recovery metadata file")
    total = 0
    records = {}
    for name in listed:
        data, observed = read_file(fd, name, MANIFEST_LIMIT)
        total += len(data)
        records[name] = {"sha256": digest(data), "size_bytes": len(data), "stat": observed}
    require(total <= METADATA_LIMIT, "metadata payload too large")
    return records


def seal_metadata(fd):
    records = metadata_safe(fd)
    for name in records:
        os.chmod(name, 0o400, dir_fd=fd, follow_symlinks=False)
    os.fchmod(fd, 0o500)
    return metadata_safe(fd), stamp(os.fstat(fd))


def location_stamps(destination):
    result = {}
    for name, path in (("destination", destination), ("run_directory", destination.parent)):
        fd = open_dir(path)
        try:
            result[name] = stamp(os.fstat(fd))
        finally:
            os.close(fd)
    return result


def snapshot(workspace, destination, metadata, on_metadata=None):
    workspace, destination = canonical_path(workspace), canonical_path(destination)
    original = workspace.parent / "bandido-quota-closure-development" / str(RUN) / "1"
    transport = original.with_name("1-transport")
    admission_path = original.parent.parent / ".admitted-heads" / HEAD
    require(not destination.is_relative_to(workspace) and not destination.is_relative_to(original.parent.parent), "snapshot overlaps original evidence")
    handles = []
    meta = None
    def opened(path, fresh=False):
        fd = open_dir(path, fresh=fresh)
        handles.append(fd)
        return fd
    try:
        out = opened(destination, fresh=True)
        meta_path = destination / "metadata"
        meta = opened(meta_path, fresh=True)
        chunks_path = destination / "parts"
        chunks = opened(chunks_path, fresh=True)
        source = opened(transport)
        origin = opened(original)
        guard = opened(admission_path)
        require(os.fstat(source).st_uid == os.fstat(origin).st_uid == os.geteuid(), "source owner differs")
        start = stamp(os.fstat(source))
        receipt_raw, receipt_stat = read_file(origin, "receipt.json", 8 * MIB)
        admission_raw, admission_stat = read_file(guard, "admission.json", MIB)
        require(digest(receipt_raw) == RECEIPT_SHA and digest(admission_raw) == ADMISSION_SHA, "original metadata changed since metadata recovery")
        provenance = source_metadata(parse(receipt_raw), parse(admission_raw))
        raw, manifest_stat = read_file(source, "artifact-manifest.json", MANIFEST_LIMIT)
        manifest = parse(raw)
        parts = manifest_check(manifest)
        expected_names = sorted(["artifact-manifest.json"] + [p["name"] for p in parts])
        require(names(source, PARTS_LIMIT + 1) == expected_names, "transport contains missing or unrelated entries")
        space = os.fstatvfs(out)
        require(space.f_bavail * space.f_frsize >= manifest["archive"]["size_bytes"] + METADATA_LIMIT, "insufficient snapshot disk space")
        write_new(meta, "artifact-manifest.json", raw)
        write_new(meta, "original-receipt.json", receipt_raw)
        write_new(meta, "original-admission.json", admission_raw)
        write_new(meta, "authenticated-actions-metadata.json", encode(metadata))
        first_stats = {}
        archive = hashlib.sha256()
        for part in parts:
            data, first_stats[part["name"]] = read_file(source, part["name"], PART_LIMIT)
            require(len(data) == part["size_bytes"] and digest(data) == part["sha256"], "source part hash/size differs")
            archive.update(data)
            write_new(chunks, part["name"], data)
        require(archive.hexdigest() == manifest["archive"]["sha256"], "concatenated source hash differs")
        # Re-read every original part after the entire copy, then read every copy.
        # This proves bytes stable across this bounded observation, not quiescence.
        for fd in (source, chunks):
            archive = hashlib.sha256()
            for part in parts:
                data, observed = read_file(fd, part["name"], PART_LIMIT)
                require(digest(data) == part["sha256"] and len(data) == part["size_bytes"], "post-copy part mismatch")
                if fd == source:
                    require(observed == first_stats[part["name"]], "source part identity changed")
                archive.update(data)
            require(archive.hexdigest() == manifest["archive"]["sha256"], "post-copy archive hash differs")
        require(read_file(source, "artifact-manifest.json", MANIFEST_LIMIT) == (raw, manifest_stat), "manifest changed")
        require(read_file(origin, "receipt.json", 8 * MIB) == (receipt_raw, receipt_stat), "receipt changed")
        require(read_file(guard, "admission.json", MIB) == (admission_raw, admission_stat), "admission changed")
        require(names(source, PARTS_LIMIT + 1) == expected_names and stamp(os.fstat(source)) == start, "transport membership changed")
        for path, fd in ((workspace, None), (transport, source), (original, origin), (admission_path, guard), (destination, out), (meta_path, meta), (chunks_path, chunks)):
            if fd is None:
                os.close(open_dir(path))
            else:
                verify_dir(path, fd)
        # Pin destination ctime after the final permission change, so a
        # same-UID write-and-restore during upload cannot pass the postcheck.
        for part in parts:
            os.chmod(part["name"], 0o400, dir_fd=chunks, follow_symlinks=False)
        os.fchmod(chunks, 0o500)
        os.fchmod(out, 0o500)
        copy_stats = {p["name"]: stamp(os.stat(p["name"], dir_fd=chunks, follow_symlinks=False)) for p in parts}
        report = {"schema": "worker35-sealed-transport-recovery-v1", "status": "sealed_snapshot_verified", "created_at": utc(),
            "original_run_id": RUN, "original_attempt": 1, "original_head": HEAD, "original_job_id": JOB,
            "registered_runner_id": 2, "original_transport_path": str(transport),
            "recovery_run_id": metadata["recovery_job"]["run_id"], "recovery_head": metadata["recovery_job"]["head_sha"],
            "manifest_sha256": digest(raw), "archive": manifest["archive"], "parts": parts,
            "source_part_stats": first_stats, "source_manifest_stat": manifest_stat, "source_transport_stat": start,
            "snapshot_part_stats": copy_stats, "snapshot_parts_directory_stat": stamp(os.fstat(chunks)),
            "snapshot_location_stamps": location_stamps(destination),
            "original_receipt_sha256": digest(receipt_raw), "original_admission_sha256": digest(admission_raw),
            "original_runtime_provenance": provenance,
            "classification": None, "research_interpretation_performed": False, "original_receipt_rewritten": False,
            "project_code_imported": False, "raw_research_files_opened": False, "repackaging_performed": False,
            "raw_tree_quiescence_proven": False, "archive_member_consistency_verified": False,
            "remote_artifact_bytes_verified": False,
            "known_preservation_gap": "Recovered raw-file mtimes extend beyond original packaging; this sealed archive may omit later bytes. Original packager did not verify per-member stability.",
            "scope": "Byte-preserving snapshot of existing sealed transport only; no scientific verdict"}
        report_raw = encode(report)
        write_new(meta, "recovery-report.json", report_raw)
        metadata_records, metadata_stat = seal_metadata(meta)
        if on_metadata:
            on_metadata(meta_path, metadata_records, {"metadata": metadata_stat, **location_stamps(destination)})
        return report, digest(report_raw)
    except Exception as error:
        if meta is not None:
            # Preserve every already written byte. No repair, deletion or retry.
            try:
                failure = {"schema": "worker35-sealed-recovery-blocked-v1", "status": "recovery_blocked",
                    "error_type": type(error).__name__, "reason": str(error)[:2048], "at": utc(),
                    "original_run_id": RUN, "original_head": HEAD, "classification": None,
                    "research_interpretation_performed": False, "original_bytes_modified": False,
                    "partial_snapshot_must_not_be_treated_as_verified": True}
                write_new(meta, "blocked-report.json", encode(failure))
                metadata_records, metadata_stat = seal_metadata(meta)
                verify_dir(meta_path, meta)
                if on_metadata:
                    on_metadata(meta_path, metadata_records, {"metadata": metadata_stat, **location_stamps(destination)})
            except Exception:
                print("Blocked metadata report could not be safely emitted; all existing bytes retained")
        raise
    finally:
        for fd in reversed(handles):
            os.close(fd)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Blocked("GitHub metadata redirect refused")


def api(tail):
    require(re.fullmatch(r"(?:runs|jobs)/[0-9]+(?:/jobs\?filter=latest&per_page=100&page=[1-3])?", tail), "unexpected metadata endpoint")
    request = urllib.request.Request("https://api.github.com/repos/" + REPO + "/actions/" + tail,
        headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"], "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
        raw = response.read(2 * MIB + 1)
    require(len(raw) <= 2 * MIB, "GitHub metadata exceeds limit")
    return parse(raw)


def current_job():
    require(os.environ.get("GITHUB_REPOSITORY") == REPO and os.environ.get("GITHUB_EVENT_NAME") == "push", "wrong recovery repository/event")
    require(os.environ.get("GITHUB_REF") == BRANCH and os.environ.get("GITHUB_ACTOR") == "carabinshely", "wrong branch/actor")
    require(os.environ.get("GITHUB_RUN_ATTEMPT") == "1" and os.environ.get("RUNNER_NAME") == RUNNER, "wrong attempt/runner")
    run = os.environ["GITHUB_RUN_ID"]
    require(run.isdecimal() and int(run) != RUN, "wrong recovery run")
    found = []
    for page in range(1, 4):
        response = api("runs/" + run + "/jobs?filter=latest&per_page=100&page=" + str(page))
        jobs = response.get("jobs", [])
        require(type(jobs) is list and response.get("total_count", 1000) <= PARTS_LIMIT + 1, "unexpected recovery jobs")
        found += [j for j in jobs if j.get("name") == os.environ["EXPECTED_JOB_NAME"] and j.get("status") == "in_progress"]
        if len(jobs) < 100:
            break
    require(len(found) == 1, "current job identity unavailable")
    job = found[0]
    require(job.get("runner_id") == 2 and job.get("runner_name") == RUNNER, "not original registered runner")
    require(job.get("head_sha") == os.environ["GITHUB_SHA"] and job.get("run_id") == int(run) and job.get("run_attempt") == 1, "current job source differs")
    return job


def output(values):
    with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
        for key, value in values.items():
            require("\n" not in str(value) and "\r" not in str(value), "unsafe step output")
            stream.write(key + "=" + str(value) + "\n")


def check_part(destination, part_name, expected_report_sha):
    require(re.fullmatch(r"evidence\.part-[0-9]{5}", part_name), "unsafe selected part")
    meta = open_dir(destination / "metadata")
    chunks = open_dir(destination / "parts")
    try:
        raw, _ = read_file(meta, "recovery-report.json", MANIFEST_LIMIT)
        require(digest(raw) == expected_report_sha, "snapshot report hash differs from admitted output")
        report = parse(raw)
        require(report.get("status") == "sealed_snapshot_verified" and report.get("original_head") == HEAD and report.get("original_run_id") == RUN, "snapshot report identity differs")
        require(report.get("recovery_run_id") == int(os.environ["GITHUB_RUN_ID"]) and report.get("recovery_head") == os.environ["GITHUB_SHA"], "snapshot belongs to another recovery")
        matches = [p for p in report["parts"] if p["name"] == part_name]
        require(len(matches) == 1, "selected part not in snapshot")
        data, observed = read_file(chunks, part_name, PART_LIMIT)
        require(len(data) == matches[0]["size_bytes"] and digest(data) == matches[0]["sha256"], "selected snapshot part hash differs")
        require(observed == report["snapshot_part_stats"][part_name], "snapshot part stamp changed")
        require(stamp(os.fstat(chunks)) == report["snapshot_parts_directory_stat"], "snapshot parts directory changed")
        require(location_stamps(destination) == report["snapshot_location_stamps"], "snapshot location changed")
        verify_dir(destination / "metadata", meta)
        verify_dir(destination / "parts", chunks)
        return report
    finally:
        os.close(meta)
        os.close(chunks)


def check_metadata(destination, expected_records, expected_stat):
    fd = open_dir(destination / "metadata")
    try:
        require(metadata_safe(fd) == parse(expected_records), "metadata bytes or stamps changed")
        require({"metadata": stamp(os.fstat(fd)), **location_stamps(destination)} == parse(expected_stat), "metadata location changed")
        verify_dir(destination / "metadata", fd)
    finally:
        os.close(fd)


def main():
    def deadline(signum, frame):
        raise Blocked("bounded recovery deadline exceeded")
    signal.signal(signal.SIGALRM, deadline)
    mode = os.environ["RECOVERY_MODE"]
    signal.alarm(600 if mode == "snapshot" else 90)
    workspace = canonical_path(os.environ["GITHUB_WORKSPACE"])
    destination = workspace.parent / "bandido-worker35-sealed-recovery" / os.environ["GITHUB_RUN_ID"] / "1"
    job = current_job()
    if mode == "snapshot":
        run, original = api("runs/" + str(RUN)), api("jobs/" + str(JOB))
        validate_original(run, original)
        os.environ.pop("GH_TOKEN", None)
        metadata = {"run": run, "job": original, "recovery_job": job, "fetched_at": utc()}
        report, report_sha = snapshot(workspace, destination, metadata,
            on_metadata=lambda path, records, observed: output({"metadata_path": path, "metadata_ready": "true",
                "metadata_records": encode(records).decode().strip(), "metadata_stat": json.dumps(observed, separators=(",", ":"))}))
        output({"parts": json.dumps([p["name"] for p in report["parts"]], separators=(",", ":")), "report_sha": report_sha})
        print(json.dumps({"status": report["status"], "report_sha256": report_sha, "part_count": len(report["parts"]), "archive_bytes": report["archive"]["size_bytes"], "classification": None}))
    elif mode == "metadata":
        os.environ.pop("GH_TOKEN", None)
        check_metadata(destination, os.environ["EXPECTED_METADATA_RECORDS"], os.environ["EXPECTED_METADATA_STAT"])
        print("Snapshot metadata bytes and stamps verified")
    elif mode == "part":
        os.environ.pop("GH_TOKEN", None)
        part = os.environ["SELECTED_PART"]
        check_part(destination, part, os.environ["EXPECTED_REPORT_SHA"])
        output({"part_path": destination / "parts" / part})
        print("Snapshot part hash verified: " + part)
    else:
        raise Blocked("unsupported recovery mode")
    signal.alarm(0)


if __name__ == "__main__":
    main()
