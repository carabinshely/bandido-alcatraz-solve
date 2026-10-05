"""Worker37's leaf, standard-library-only metadata client.

The external owner-event freeze authorizes execution. This client verifies the
fixed descriptor and seven input bindings; it does not infer scientific authority.
All dependency seams are ordinary standard-library calls. There are no runtime
test switches, children, background workers, retries, or alternate input clients.
"""

import argparse
import gc
import hashlib
import http.client
import io
import json
import math
import os
import re
import resource
import signal
import ssl
import stat
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

try:
    from . import worker_bootstrap_shared as bootstrap_shared
except ImportError:
    import worker_bootstrap_shared as bootstrap_shared


REPOSITORY = "carabinshely/bandido-alcatraz-solve"
ACTOR = "carabinshely"
RUNNER = "bandido-alcatraz-ci"
ALLOCATION = "worker37-bootstrap-readiness-01"
API = "https://api.github.com/repos/" + REPOSITORY
MARKER = "WORKER37_ENGINEERING_ADMISSION"
BEGIN = MARKER + "_JSON"
END = "END_" + BEGIN
DIGEST = MARKER + "_SHA256"
EXECUTABLE_SHA256 = "a15ccdaf07655a8667a3687b13171486c9a265d92273ba3ad820fbb64d2cfecc"
LIBRARY_SHA256 = "ba4450817186fbe1e3c477f6aefeee7c353cba3593cc9950382ad9d1f5e62896"
LIBRARY_SIZE = 23041360
FIXED_BASE = {"head": "2b00e0d1e76364ae287946f7c0e3dc2baac4653f",
              "tree": "a40cceee052f97141275cb44bd0a86a1a52c76a6", "run_id": 37227213235}
FIXED_HISTORICAL = {
    "run_id": 37221141227, "run_attempt": 1, "artifact_id": 11310585783,
    "artifact_name": "worker36-zero-evaluator-preflight-37221141227-1", "pr_number": 40,
    "head": "78506a6647b0163c93bda086501f4f45927abf65",
    "tree": "5c3800f42fc30ec51715768d0d00161685887769",
    "zip_size_bytes": 83342,
    "zip_sha256": "f7447bc2c7d8bd8c84fc940b83567d0c4f1c1ba34523310b75046916883ea971",
    "report_size_bytes": 65931,
    "report_sha256": "4a85c454fcc2f82a00be91f23c720959890d77381f28d27f75c44b7fad9e1ec6",
}
REQUIRED_SOURCE_PATHS = (
    ".github/workflows/worker37-bootstrap-readiness.yml", "scripts/worker37-bootstrap.sh",
    "scripts/worker37_bootstrap.py", "tests/test_worker37_bootstrap.py",
    "scripts/worker_bootstrap_shared.sh", "scripts/worker_bootstrap_shared.py",
    "experiments/worker37-bootstrap-readiness/PROTOCOL.md",
    "experiments/worker37-bootstrap-readiness/literal-test-plan.json",
    "experiments/worker37-bootstrap-readiness/source-manifest.json",
    "experiments/worker37-bootstrap-readiness/preparation-receipt.json",
)
BUDGETS = {
    "memory_bytes": 536870912,
    "scope_seconds": 120,
    "socket_seconds": 10,
    "response_body_bytes": 16777216,
    "input_bytes": 2097152,
    "expanded_zip_bytes": 2097152,
    "evidence_bytes": 31457280,
    "terminal_reserve_bytes": 1048576,
}
MAX_INPUT = BUDGETS["input_bytes"]
MAX_BODY = BUDGETS["response_body_bytes"]
MEMORY = BUDGETS["memory_bytes"]
FLAGS = {"optimize": 0, "ignore_environment": 0, "isolated": 0,
         "no_site": 0, "no_user_site": 1, "dont_write_bytecode": 1}
ZIP_MEMBERS = frozenset({
    "fresh-child-process.json", "fresh-child.stderr", "fresh-child.json",
    "fresh-child.stdout", "launcher.txt", "parent-runtime.json",
    "parent.stderr", "parent.stdout", "runner-preflight.json", "shell-loader.json",
})
INPUT_NAMES = ("pull-request.json", "postmerge-ci.json", "review-exhaustive.json",
               "review-adversarial.json", "preflight-run.json", "preflight-artifact.json",
               "preflight.zip")
OUTPUT_NAMES = frozenset(INPUT_NAMES + (
    "event.json", "request-context.json", "reservation-admission.json",
    "result.json", "inventory.json", "terminal.json",
))
EXIT_CODES = {"bootstrap_ready": 0, "execution_blocked": 2,
              "resource_incomplete": 3, "integrity_invalid": 4,
              "evidence_incomplete": 5}


class Failure(Exception):
    """Only fixed local codes, never remote text or paths, enter diagnostics."""

    def __init__(self, classification, code):
        self.classification = classification
        self.code = code
        super().__init__(code)


def require(condition, code, classification="integrity_invalid"):
    if not condition:
        raise Failure(classification, code)


def record_failure(report, classification, code, phase, error=None):
    """The first cause owns the result; subsequent causes keep their own phase."""
    failure = {"classification": classification, "code": code, "phase": phase}
    if report["primary_failure"] is None:
        report["primary_failure"] = failure
        report["classification"] = classification
        report["error_code"] = code
        report["failed_phase"] = phase
    else:
        report["secondary_failures"].append(failure)
    for cleanup in (*getattr(error, "_worker37_cleanup_failures", ()),
                    *getattr(error, "_bootstrap_cleanup_failures", ())):
        report["secondary_failures"].append({**cleanup, "phase": phase})




def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result

    def nonfinite(_value):
        raise Failure("integrity_invalid", "nonfinite_json")

    def finite_float(value):
        number = float(value)
        require(math.isfinite(number), "nonfinite_json")
        return number

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=nonfinite, parse_float=finite_float)
    except (UnicodeError, ValueError, RecursionError):
        raise Failure("integrity_invalid", "invalid_json") from None


def keys(value, expected, code="descriptor_schema"):
    require(type(value) is dict and set(value) == set(expected), code,
            "execution_blocked")
    return value


def object_at(value, key):
    require(type(value) is dict and type(value.get(key)) is dict, "object_shape")
    return value[key]


def integer(value, code="positive_integer", maximum=9223372036854775807):
    require(type(value) is int and 0 < value <= maximum, code, "execution_blocked")
    return value


def hexdigest(value, width=64):
    require(type(value) is str and re.fullmatch("[0-9a-f]{" + str(width) + "}", value),
            "digest_syntax", "execution_blocked")
    return value


def text_bytes(value, maximum=65536):
    require(type(value) is str, "body_type")
    try:
        raw = value.encode("utf-8")
    except UnicodeError:
        raise Failure("integrity_invalid", "body_utf8") from None
    require(len(raw) <= maximum, "body_cap", "resource_incomplete")
    return raw


def env_integer(name):
    value = os.environ.get(name, "")
    require(re.fullmatch(r"[1-9][0-9]{0,18}", value) is not None,
            "shell_identifier", "execution_blocked")
    return integer(int(value))















def _runtime_failure(error):
    failure = Failure(error.classification, error.code)
    failure._bootstrap_cleanup_failures = list(
        getattr(error, "_bootstrap_cleanup_failures", ()))
    return failure


def close_descriptor(fd, operation, record=None, *, pending=None):
    try:
        return bootstrap_shared.close_descriptor(fd, operation, record, pending=pending)
    except bootstrap_shared.RuntimeFailure as error:
        raise _runtime_failure(error) from None


def bounded_read(path, cap):
    try:
        return bootstrap_shared.bounded_read(path, cap)
    except bootstrap_shared.RuntimeFailure as error:
        raise _runtime_failure(error) from None


file_tuple = bootstrap_shared.file_tuple
shell_stat = bootstrap_shared.shell_stat
limits_snapshot = bootstrap_shared.limits_snapshot
state_snapshot = bootstrap_shared.state_snapshot


def runtime_start(observation):
    try:
        return bootstrap_shared.runtime_start(observation, "worker37-preparation-v1")
    except bootstrap_shared.RuntimeFailure as error:
        raise _runtime_failure(error) from None


def descriptor_from_body(body):
    raw_body = text_bytes(body)
    require("WORKER36" not in body, "historical_admission_marker", "execution_blocked")
    # Only LF marker delimiters are accepted. Do not normalize descriptor bytes
    # before comparing their digest to the digest line outside the JSON block.
    lines = body.split("\n")
    require(lines.count(BEGIN) == 1 and lines.count(END) == 1,
            "first_marker_delimiters", "execution_blocked")
    start, finish = lines.index(BEGIN), lines.index(END)
    require(start < finish and body.count(MARKER) == 3,
            "duplicate_admission_marker", "execution_blocked")
    raw = "\n".join(lines[start + 1:finish]).encode("utf-8")
    require(len(raw) <= 60000, "descriptor_cap", "resource_incomplete")
    digest_lines = [line for line in lines if line.startswith(DIGEST + " ")]
    require(len(digest_lines) == 1 and digest_lines[0] == DIGEST + " " + sha(raw),
            "descriptor_digest", "execution_blocked")
    require(lines.index(digest_lines[0]) not in range(start, finish + 1),
            "descriptor_digest_location", "execution_blocked")
    return strict_json(raw), raw, raw_body


def validate_descriptor(d):
    keys(d, ("schema", "preparation_only", "measurement_admitted", "allocation_id",
             "repository", "actor", "runner", "pr_number", "branch", "head", "tree",
             "base", "preregistration", "reviews", "historical_fixture", "runtime",
             "budgets", "source_files"))
    require(d["schema"] == "worker37-engineering-admission-v1"
            and d["preparation_only"] is True and d["measurement_admitted"] is False
            and d["allocation_id"] == ALLOCATION and d["repository"] == REPOSITORY
            and d["actor"] == ACTOR and d["runner"] == RUNNER,
            "descriptor_identity", "execution_blocked")
    integer(d["pr_number"])
    require(type(d["branch"]) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,199}", d["branch"])
            and ".." not in d["branch"] and "//" not in d["branch"], "branch", "execution_blocked")
    hexdigest(d["head"], 40); hexdigest(d["tree"], 40)
    keys(d["base"], ("head", "tree", "run_id"))
    hexdigest(d["base"]["head"], 40); hexdigest(d["base"]["tree"], 40)
    integer(d["base"]["run_id"])
    require(d["base"] == FIXED_BASE, "fixed_base", "execution_blocked")
    keys(d["preregistration"], ("protocol_sha256", "record_sha256"))
    for value in d["preregistration"].values():
        hexdigest(value)
    require(type(d["reviews"]) is list and len(d["reviews"]) == 2, "reviews", "execution_blocked")
    for review, role in zip(d["reviews"], ("exhaustive", "adversarial")):
        keys(review, ("role", "comment_id", "author", "head", "tree", "body_sha256"))
        integer(review["comment_id"]); hexdigest(review["body_sha256"])
        require(review["role"] == role and review["author"] == ACTOR
                and review["head"] == d["head"] and review["tree"] == d["tree"],
                "review_descriptor_source", "execution_blocked")
    require(d["reviews"][0]["comment_id"] != d["reviews"][1]["comment_id"],
            "distinct_reviews", "execution_blocked")
    fixture = keys(d["historical_fixture"], (
        "run_id", "run_attempt", "artifact_id", "artifact_name", "pr_number", "head", "tree",
        "zip_size_bytes", "zip_sha256", "report_size_bytes", "report_sha256"))
    for field in ("run_id", "artifact_id", "pr_number"):
        integer(fixture[field])
    require(type(fixture["run_attempt"]) is int and fixture["run_attempt"] == 1,
            "fixture_attempt", "execution_blocked")
    require(type(fixture["artifact_name"]) is str and re.fullmatch(r"[A-Za-z0-9._-]{1,200}", fixture["artifact_name"]),
            "fixture_name", "execution_blocked")
    for field in ("head", "tree"):
        hexdigest(fixture[field], 40)
    require(fixture["head"] != d["head"], "separate_source_domains", "execution_blocked")
    for prefix in ("zip", "report"):
        integer(fixture[prefix + "_size_bytes"], maximum=MAX_INPUT)
        hexdigest(fixture[prefix + "_sha256"])
    require(fixture == FIXED_HISTORICAL, "fixed_historical_fixture", "execution_blocked")
    runtime = keys(d["runtime"], ("executable_sha256", "library_sha256", "library_size_bytes", "inherited_limits"))
    require(runtime["executable_sha256"] == EXECUTABLE_SHA256
            and runtime["library_sha256"] == LIBRARY_SHA256
            and type(runtime["library_size_bytes"]) is int and runtime["library_size_bytes"] == LIBRARY_SIZE,
            "runtime_descriptor", "execution_blocked")
    require(type(runtime["inherited_limits"]) is dict, "inherited_limits_schema", "execution_blocked")
    for name, value in runtime["inherited_limits"].items():
        require(name.startswith("RLIMIT_") and type(value) is list and len(value) == 2
                and all(type(item) is int and item >= -1 for item in value),
                "inherited_limits_schema", "execution_blocked")
    require(canonical(d["budgets"]) == canonical(BUDGETS), "budget_descriptor", "execution_blocked")
    require(type(d["source_files"]) is dict and 1 <= len(d["source_files"]) <= 256,
            "source_map_count", "execution_blocked")
    for path, binding in d["source_files"].items():
        require(type(path) is str and 0 < len(path) <= 240 and not path.startswith("/")
                and "\\" not in path and all(part not in ("", ".", "..") for part in path.split("/"))
                and not any(ord(char) < 32 for char in path), "source_path", "execution_blocked")
        keys(binding, ("sha256", "size_bytes")); hexdigest(binding["sha256"])
        integer(binding["size_bytes"], maximum=MAX_INPUT)
    require(set(REQUIRED_SOURCE_PATHS) <= set(d["source_files"]), "required_source_bindings", "execution_blocked")
    protocol_path = "experiments/worker37-bootstrap-readiness/PROTOCOL.md"
    if protocol_path in d["source_files"]:
        require(d["source_files"][protocol_path]["sha256"] == d["preregistration"]["protocol_sha256"],
                "protocol_source_binding", "execution_blocked")


def validate_pr(value, descriptor, body):
    require(type(value) is dict, "pr_object")
    require(type(value.get("number")) is int and value["number"] == descriptor["pr_number"]
            and value.get("state") == "open" and value.get("merged") is False,
            "pr_identity")
    require(object_at(value, "user").get("login") == ACTOR, "pr_owner")
    for side, ref, head in (("head", descriptor["branch"], descriptor["head"]),
                            ("base", "main", descriptor["base"]["head"])):
        item = object_at(value, side)
        require(item.get("sha") == head and item.get("ref") == ref
                and object_at(item, "repo").get("full_name") == REPOSITORY, "pr_" + side)
    require(text_bytes(value.get("body")) == body, "pr_body")


def validate_context(event, descriptor, body, source):
    expected_env = {"GITHUB_REPOSITORY": REPOSITORY, "GITHUB_ACTOR": ACTOR,
                    "RUNNER_NAME": RUNNER, "GITHUB_SERVER_URL": "https://github.com",
                    "GITHUB_API_URL": "https://api.github.com", "GITHUB_EVENT_NAME": "pull_request",
                    "GITHUB_RUN_ATTEMPT": "1", "WORKER37_ALLOCATION_ID": ALLOCATION}
    require(all(os.environ.get(name) == value for name, value in expected_env.items()),
            "shell_identity", "execution_blocked")
    require(re.fullmatch(r"[A-Za-z0-9_-]{1,100}", os.environ.get("WORKER37_JOB", "")) is not None,
            "shell_job", "execution_blocked")
    require(env_integer("WORKER37_PR_NUMBER") == descriptor["pr_number"]
            and env_integer("WORKER37_RUN_ID") == env_integer("GITHUB_RUN_ID")
            and os.environ.get("WORKER37_HEAD") == descriptor["head"]
            and os.environ.get("WORKER37_TREE") == descriptor["tree"]
            and os.environ.get("WORKER37_BRANCH", os.environ.get("WORKER37_HEAD_REF")) == descriptor["branch"],
            "shell_descriptor_agreement", "execution_blocked")
    require(event.get("action") == "edited" and type(event.get("number")) is int
            and event["number"] == descriptor["pr_number"]
            and object_at(event, "sender").get("login") == ACTOR
            and object_at(event, "repository").get("full_name") == REPOSITORY,
            "event_identity", "execution_blocked")
    previous = object_at(object_at(event, "changes"), "body").get("from")
    require(type(previous) is str and MARKER not in previous and "WORKER36" not in previous,
            "first_marker_transition", "execution_blocked")
    text_bytes(previous)
    validate_pr(event.get("pull_request"), descriptor, body)
    require(os.path.isabs(source) and os.path.realpath(source) == source, "source_directory")
    for relative, binding in descriptor["source_files"].items():
        path = os.path.join(source, relative)
        require(os.path.realpath(path) == path, "source_symlink")
        raw = bounded_read(path, MAX_INPUT)
        require(len(raw) == binding["size_bytes"] and sha(raw) == binding["sha256"], "source_digest")


def request_map(descriptor):
    fixture = descriptor["historical_fixture"]
    return list(zip(INPUT_NAMES, (
        "/pulls/" + str(descriptor["pr_number"]),
        "/actions/runs/" + str(descriptor["base"]["run_id"]),
        "/issues/comments/" + str(descriptor["reviews"][0]["comment_id"]),
        "/issues/comments/" + str(descriptor["reviews"][1]["comment_id"]),
        "/actions/runs/" + str(fixture["run_id"]),
        "/actions/artifacts/" + str(fixture["artifact_id"]),
        "/actions/artifacts/" + str(fixture["artifact_id"]) + "/zip",
    )))


def validate_response(index, raw, descriptor, body):
    value = strict_json(raw)
    require(type(value) is dict, "response_object")
    if index == 0:
        validate_pr(value, descriptor, body)
    elif index in (1, 4):
        expected = descriptor["base"] if index == 1 else descriptor["historical_fixture"]
        require(type(value.get("id")) is int and value["id"] == expected["run_id"]
                and object_at(value, "repository").get("full_name") == REPOSITORY,
                "run_identity")
        # GET5's actual API head_sha is the immediate historical-source check.
        require(value.get("head_sha") == expected["head"], "run_head_sha")
        require(value.get("status") == "completed" and value.get("conclusion") == "success",
                "run_not_successful", "execution_blocked")
        require(value.get("event") == ("push" if index == 1 else "pull_request"), "run_event")
        if index == 4:
            require(type(value.get("run_attempt")) is int and value["run_attempt"] == 1, "prior_run_attempt")
            pulls = value.get("pull_requests")
            require(type(pulls) is list and len(pulls) in (0, 1), "prior_pr")
            if pulls:
                require(type(pulls[0]) is dict and type(pulls[0].get("number")) is int
                        and pulls[0]["number"] == expected["pr_number"]
                        and object_at(pulls[0], "head").get("sha") == expected["head"], "prior_pr")
    elif index in (2, 3):
        review = descriptor["reviews"][index - 2]
        review_raw = text_bytes(value.get("body"))
        require(type(value.get("id")) is int and value["id"] == review["comment_id"]
                and object_at(value, "user").get("login") == review["author"]
                and value.get("issue_url") == API + "/issues/" + str(descriptor["pr_number"]), "review_identity")
        require(sha(review_raw) == review["body_sha256"] and descriptor["head"].encode() in review_raw
                and descriptor["tree"].encode() in review_raw, "review_source")
    elif index == 5:
        fixture = descriptor["historical_fixture"]
        require(type(value.get("id")) is int and value["id"] == fixture["artifact_id"]
                and value.get("name") == fixture["artifact_name"] and value.get("expired") is False
                and type(value.get("size_in_bytes")) is int and value["size_in_bytes"] == fixture["zip_size_bytes"]
                and value.get("digest") == "sha256:" + fixture["zip_sha256"], "artifact_identity")
        run = object_at(value, "workflow_run")
        require(type(run.get("id")) is int and run["id"] == fixture["run_id"]
                and run.get("head_sha") == fixture["head"], "artifact_source")
    return value


def validate_zip(raw, fixture):
    require(len(raw) == fixture["zip_size_bytes"] and sha(raw) == fixture["zip_sha256"], "archive_hash")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            names = [member.filename for member in members]
            require(len(names) == len(set(names)), "archive_duplicate_member")
            require(set(names) == ZIP_MEMBERS, "archive_member_allowlist")
            require(sum(member.file_size for member in members) <= MAX_INPUT, "archive_expanded_cap")
            components = {}
            expanded = 0
            for member in members:
                require(not member.is_dir() and stat.S_IFMT(member.external_attr >> 16) in (0, stat.S_IFREG)
                        and not member.external_attr & 0x10
                        and not member.flag_bits & 1
                        and member.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                        and 0 <= member.file_size <= MAX_INPUT and 0 <= member.compress_size <= MAX_INPUT,
                        "archive_member_type")
                with archive.open(member) as stream:
                    component = stream.read(MAX_INPUT - expanded + 1)
                expanded += len(component)
                require(expanded <= MAX_INPUT and len(component) == member.file_size, "archive_expanded_cap")
                components[member.filename] = component
        report_raw = components["runner-preflight.json"]
        require(len(report_raw) == fixture["report_size_bytes"] and sha(report_raw) == fixture["report_sha256"],
                "archive_report_hash")
        report = strict_json(report_raw)
        require(type(report) is dict and report.get("repository") == REPOSITORY
                and report.get("diagnostic_head") == fixture["head"]
                and report.get("diagnostic_tree") == fixture["tree"]
                and report.get("workflow_run") == str(fixture["run_id"])
                and report.get("workflow_attempt") == "1", "archive_report_source")
        parent, child = report.get("parent"), report.get("fresh_child")
        require(type(parent) is dict and type(child) is dict and type(parent.get("shell_loader")) is dict,
                "archive_report_components")
        require(components["parent-runtime.json"] == canonical(parent)
                and components["fresh-child.json"] == canonical(child)
                and components["shell-loader.json"] == canonical(parent["shell_loader"]),
                "archive_component_bytes")
        return {"members": sorted(names), "expanded_bytes": expanded,
                "report_sha256": sha(report_raw), "historical_fixture_only": True}
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, UnicodeError, EOFError):
        raise Failure("integrity_invalid", "invalid_archive") from None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def storage_target(location):
    require(type(location) is str and 0 < len(location) <= 16384
            and location.isascii() and not any(ord(char) <= 32 or ord(char) == 127 for char in location),
            "storage_location", "execution_blocked")
    try:
        parsed = urllib.parse.urlsplit(location)
        host = parsed.hostname
        authority = parsed.netloc
        require(parsed.scheme == "https" and parsed.port in (None, 443)
                and parsed.username is None and parsed.password is None and "#" not in location
                and host is not None and "%" not in authority and "\\" not in location,
                "storage_origin", "execution_blocked")
        label = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
        require(re.fullmatch(label + r"\.blob\.core\.windows\.net(?::443)?", authority,
                             flags=re.IGNORECASE) is not None
                and host.lower().endswith(".blob.core.windows.net"), "storage_host", "execution_blocked")
    except ValueError:
        raise Failure("execution_blocked", "storage_origin") from None
    return location


class Evidence:
    def __init__(self, output):
        self.output = Path(output)
        self.files = {}
        self.payload_bytes = 0
        self.terminal_bytes = 0
        self.directory_fd = None

    def open(self):
        require(self.output.is_absolute() and os.path.realpath(self.output) == str(self.output), "output_path")
        fd = os.open(self.output, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700, "output_custody")
        except Exception as error:
            close_descriptor(fd, "custody_open", pending=error)
            raise
        self.directory_fd = fd

    def close(self):
        if self.directory_fd is not None:
            close_descriptor(self.directory_fd, "custody_directory_close")
            self.directory_fd = None

    def adopt_event(self, path, raw):
        """Verify the launcher's P03 snapshot; never replace an existing input."""
        require(str(path) == str(self.output / "event.json"), "event_snapshot_path")
        record = {"size_bytes": len(raw), "sha256": sha(raw), "file_fsync_confirmed": False,
                  "directory_fsync_confirmed": False, "readback_confirmed": False,
                  "write_complete": True, "origin": "launcher_P03_snapshot"}
        self.files["event.json"] = record
        self.payload_bytes += len(raw)
        fd = os.open("event.json", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=self.directory_fd)
        try:
            info = os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_size == len(raw)
                    and shell_stat(info) == os.environ.get("WORKER37_EVENT_STAT")
                    and sha(raw) == os.environ.get("WORKER37_EVENT_SHA256")
                    and os.environ.get("WORKER37_EVENT_FSYNC_CONFIRMED") == "1",
                    "event_snapshot_agreement")
            os.fsync(fd)
            record["file_fsync_confirmed"] = True
            os.fsync(self.directory_fd)
            record["directory_fsync_confirmed"] = True
        finally:
            close_descriptor(fd, "event_snapshot", record, pending=sys.exc_info()[1])
        require(bounded_read(path, MAX_INPUT) == raw, "event_snapshot_readback")
        record["readback_confirmed"] = True

    def write(self, name, raw, terminal=False):
        require(self.directory_fd is not None, "output_not_open", "evidence_incomplete")
        require(name in OUTPUT_NAMES and name not in self.files, "output_allowlist")
        limit = BUDGETS["evidence_bytes"] - (0 if terminal else BUDGETS["terminal_reserve_bytes"])
        require(self.payload_bytes + len(raw) <= limit, "evidence_budget", "resource_incomplete")
        require(not terminal or self.terminal_bytes + len(raw) <= BUDGETS["terminal_reserve_bytes"],
                "terminal_budget", "resource_incomplete")
        if terminal:
            self.terminal_bytes += len(raw)
        record = {"size_bytes": 0, "sha256": None, "file_fsync_confirmed": False,
                  "directory_fsync_confirmed": False, "readback_confirmed": False,
                  "write_complete": False}
        self.files[name] = record
        fd = None
        try:
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=self.directory_fd)
            offset = 0
            while offset < len(raw):
                count = os.write(fd, raw[offset:])
                require(type(count) is int and 0 < count <= len(raw) - offset,
                        "persistence_short_write", "evidence_incomplete")
                offset += count
                record["size_bytes"] = offset
                self.payload_bytes += count
            record["write_complete"] = True
            record["sha256"] = sha(raw)
            os.fsync(fd)
            record["file_fsync_confirmed"] = True
            os.fsync(self.directory_fd)
            record["directory_fsync_confirmed"] = True
        except OSError:
            if fd is not None:
                # fstat observes the actual surviving prefix if a writer accepted
                # bytes and subsequently raised instead of returning its count.
                try:
                    actual = os.fstat(fd).st_size
                    self.payload_bytes += max(0, actual - record["size_bytes"])
                    record["size_bytes"] = actual
                except OSError:
                    record["size_unconfirmed"] = True
            raise Failure("evidence_incomplete", "persistence_failed") from None
        finally:
            if fd is not None:
                close_descriptor(fd, "evidence_write", record, pending=sys.exc_info()[1])
        return record

    def verify(self):
        for name, record in self.files.items():
            record["readback_confirmed"] = False
            raw = bounded_read(self.output / name, MAX_INPUT)
            require(len(raw) == record["size_bytes"], "readback_size")
            if record["write_complete"]:
                require(sha(raw) == record["sha256"], "readback_digest")
                record["readback_confirmed"] = True
            else:
                record["prefix_sha256"] = sha(raw)


class Client:
    def __init__(self, evidence, token, started, report):
        self.evidence, self.token, self.started, self.report = evidence, token, started, report
        require(not any(name in os.environ for name in
                        ("SSL_CERT_FILE", "SSL_CERT_DIR", "OPENSSL_CONF", "OPENSSL_MODULES", "SSLKEYLOGFILE")),
                "alternate_tls_configuration", "execution_blocked")
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()))

    def remaining(self):
        remaining = BUDGETS["scope_seconds"] - (time.monotonic() - self.started)
        require(remaining > 0, "scope_deadline", "resource_incomplete")
        return min(BUDGETS["socket_seconds"], remaining)

    def fetch(self, url, name, *, authenticated, allowance=MAX_INPUT):
        timeout = self.remaining()
        record = {"name": name, "transport": "api" if authenticated else "storage",
                  "status": None, "received_bytes": 0, "retained_bytes": 0,
                  "buffered_bytes": 0, "complete": False, "truncated": False}
        self.report["requests"].append(record)
        headers = {"Accept-Encoding": "identity", "User-Agent": "worker37-bootstrap-readiness"}
        if authenticated:
            headers.update({"Authorization": "Bearer " + self.token,
                            "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
        request = urllib.request.Request(url, headers=headers, method="GET")
        response = None
        try:
            try:
                response = self.opener.open(request, timeout=timeout)
            except urllib.error.HTTPError as error:
                response = error
            status = response.status if hasattr(response, "status") else response.code
            record["status"] = status
            omit = ("redirect_body_may_contain_signed_url" if status in (301, 302, 303, 307, 308)
                    else "storage_error_body_may_contain_signed_url" if not authenticated and status != 200 else None)
            if omit:
                record["omission_reason"] = omit
            require(response.headers.get("Content-Encoding", "identity").lower() in ("identity", ""),
                    "content_encoding", "execution_blocked")
            length = response.headers.get("Content-Length")
            require(length is None or re.fullmatch(r"[0-9]+", length) is not None,
                    "content_length", "evidence_incomplete")
            declared = int(length) if length is not None else None
            pieces = []
            body_failure = None
            while True:
                available = MAX_BODY - self.report["response_body_bytes"]
                if available <= 0:
                    body_failure = Failure("resource_incomplete", "aggregate_body_budget")
                    break
                size = min(65536, allowance + 1 - record["received_bytes"], available)
                incomplete = False
                try:
                    part = response.read(size)
                except http.client.IncompleteRead as error:
                    # These bytes have already been read by the HTTP parser.
                    # Its message/expected count can contain untrusted context;
                    # retain only the actual bytes and a fixed incomplete flag.
                    part = error.partial
                    incomplete = True
                    record["incomplete_read"] = True
                    record["unknown_remainder"] = True
                except MemoryError:
                    body_failure = Failure("resource_incomplete", "response_memory_exhausted")
                    break
                except Exception:
                    # Transport exceptions may contain credentials or signed URLs.
                    body_failure = Failure("evidence_incomplete", "response_read_failed")
                    break
                require(type(part) is bytes, "response_read_contract")
                if not part and not incomplete:
                    record["complete"] = True
                    break
                self.report["response_body_bytes"] += len(part)
                prior = record["received_bytes"]
                record["received_bytes"] += len(part)
                if not omit and prior < allowance:
                    retained = part[:min(allowance - prior, available)]
                    pieces.append(retained)
                    record["buffered_bytes"] += len(retained)
                if self.report["response_body_bytes"] > MAX_BODY:
                    record["truncated"] = True
                    body_failure = Failure("resource_incomplete", "aggregate_body_budget")
                    break
                if record["received_bytes"] > allowance:
                    record["truncated"] = True
                    body_failure = Failure("resource_incomplete", "input_body_overflow")
                    break
                if len(part) > size:
                    body_failure = Failure("integrity_invalid", "response_read_contract")
                    break
                if incomplete:
                    body_failure = Failure("evidence_incomplete", "response_incomplete_read")
                    break
            raw = b"".join(pieces)
            if not omit:
                try:
                    self.evidence.write(name, raw)
                except Failure as error:
                    if body_failure is not None:
                        self.report.setdefault("input_persistence_failures", []).append({
                            "classification": error.classification, "code": error.code,
                            "phase": "P07", "name": name})
                        self.report["input_persistence_failures"].extend(
                            {**cleanup, "phase": "P07", "name": name}
                            for cleanup in getattr(error, "_worker37_cleanup_failures", ()))
                        raise body_failure from None
                    raise
                except MemoryError as error:
                    if body_failure is not None:
                        self.report.setdefault("input_persistence_failures", []).append({
                            "classification": "resource_incomplete", "code": "persistence_memory_exhausted",
                            "phase": "P07", "name": name})
                        self.report["input_persistence_failures"].extend(
                            {**cleanup, "phase": "P07", "name": name}
                            for cleanup in getattr(error, "_worker37_cleanup_failures", ()))
                        raise body_failure from None
                    raise
                finally:
                    # A short/failed write must not count buffered bytes as
                    # retained evidence. Durability is a separate file record.
                    record["retained_bytes"] = self.evidence.files.get(name, {}).get("size_bytes", 0)
            if body_failure:
                raise body_failure
            require(declared is None or declared == record["received_bytes"],
                    "response_length_mismatch", "evidence_incomplete")
            location = response.headers.get("Location") if status == 302 else None
            return status, raw, location, record["received_bytes"]
        except Failure:
            raise
        except MemoryError:
            raise
        except Exception:
            raise Failure("execution_blocked", "transport_failed") from None
        finally:
            if response is not None:
                pending = sys.exc_info()[1]
                close_failure = None
                try:
                    response.close()
                    # Confirm restoration of an actual opened transport resource.
                    # No timer, hook, GC or working-directory mutation is needed.
                    require(response.closed is True, "response_close_unconfirmed", "evidence_incomplete")
                    record["close_confirmed"] = True
                except Failure as error:
                    close_failure = error
                except MemoryError:
                    close_failure = Failure("resource_incomplete", "response_close_memory_exhausted")
                except Exception:
                    close_failure = Failure("evidence_incomplete", "response_close_failed")
                if close_failure is not None:
                    record["close_confirmed"] = False
                    self.report.setdefault("transport_restoration_failures", []).append({
                        "classification": close_failure.classification, "code": close_failure.code,
                        "phase": "P07", "name": name})
                    # Retain an established body/transport/memory cause; closure
                    # trouble is separate evidence and never permits readiness.
                    if pending is None:
                        raise close_failure from None

    def inputs(self, descriptor, body):
        zip_raw = None
        for index, (name, path) in enumerate(request_map(descriptor)):
            self.report["requested_prefix"].append(name)
            status, raw, location, received = self.fetch(API + path, name, authenticated=True)
            if index == 6 and status == 302:
                target = storage_target(location)
                status, raw, _location, _received = self.fetch(
                    target, name, authenticated=False, allowance=MAX_INPUT - received)
            require(status == 200, "http_status", "execution_blocked")
            if index < 6:
                value = validate_response(index, raw, descriptor, body)
                if index == 4:
                    # An absent provider association is not new proof of PR40.
                    # The historical relation remains frozen provenance; the
                    # immutable run/artifact/ZIP/report bindings still apply.
                    count = len(value["pull_requests"])
                    self.report["historical_pr_association"] = {
                        "live_array_count": count,
                        "live_array_binding": "validated" if count else "absent",
                        "frozen_pr_number": descriptor["historical_fixture"]["pr_number"],
                        "association_basis": ("frozen_historical_provenance_and_live_array"
                                              if count else "frozen_historical_provenance"),
                        "absence_cause": None if count else "not_established",
                    }
            else:
                zip_raw = raw
            self.report["completed_prefix"].append(name)
        return zip_raw


def main(argv=None):
    parser = argparse.ArgumentParser(description="Worker37 metadata readiness leaf")
    parser.add_argument("--event", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--source", required=True)
    args = parser.parse_args(argv)
    started = time.monotonic()
    report = {"schema": "worker37-bootstrap-result-v1", "preparation_only": True,
              "measurement_admitted": False, "scientific_classification": None,
              "allocation_id": ALLOCATION, "classification": "execution_blocked",
              "phase": "P05", "phases_completed": [], "error_code": None,
              "primary_failure": None, "secondary_failures": [], "failed_phase": None,
              "requested_prefix": [], "completed_prefix": [], "requests": [],
              "response_body_bytes": 0, "restoration": {"confirmed": False},
              "runtime": {},
              "timeout": {"external_scope_seconds": 120, "external_launcher_seconds": 600,
                          "hard_kill_observed": False, "exit_137_cause": "not_observed_by_leaf"},
              "zero_science_scope": "leaf_has_no_historical_import_or_scientific_entrypoint",
              "artifact_custody": "requires_separate_provider_wrapper_readback"}
    evidence = Evidence(args.output)
    runtime = None
    client = None
    try:
        evidence.open()
        runtime = runtime_start(report["runtime"])
        event_raw = bounded_read(args.event, MAX_INPUT)
        evidence.adopt_event(args.event, event_raw)
        event = strict_json(event_raw)
        require(type(event) is dict, "event_object", "execution_blocked")
        descriptor, descriptor_raw, body = descriptor_from_body(object_at(event, "pull_request").get("body"))
        require(type(descriptor) is dict and type(descriptor.get("runtime")) is dict
                and canonical(runtime["inherited_limits"]) == canonical(descriptor["runtime"].get("inherited_limits")),
                "frozen_inherited_limits", "execution_blocked")
        report["runtime"] = runtime
        report["phases_completed"].append("P05")
        report["phase"] = "P06"
        validate_descriptor(descriptor)
        validate_context(event, descriptor, body, args.source)
        token = os.environ.get("GH_TOKEN", "")
        require(bool(token) and token.isascii() and all(32 < ord(char) < 127 for char in token),
                "missing_or_invalid_token", "execution_blocked")
        context = {"schema": "worker37-request-context-v1", "repository": REPOSITORY,
                   "allocation_id": ALLOCATION, "run_id": env_integer("WORKER37_RUN_ID"),
                   "run_attempt": 1, "job": os.environ.get("WORKER37_JOB", ""),
                   "descriptor_sha256": sha(descriptor_raw), "body_sha256": sha(body),
                   "preregistration": descriptor["preregistration"],
                   "new_source": {"pr_number": descriptor["pr_number"], "head": descriptor["head"],
                                  "tree": descriptor["tree"], "files": descriptor["source_files"]},
                   "historical_fixture": descriptor["historical_fixture"],
                   "requests": [{"name": name, "path": path, "method": "GET"}
                                for name, path in request_map(descriptor)], "runtime": runtime}
        report["context"] = {key: value for key, value in context.items() if key not in ("requests", "runtime")}
        evidence.write("request-context.json", canonical(context))
        evidence.write("reservation-admission.json", canonical({
            "schema": "worker37-preparation-reservation-binding-v1", "allocation_id": ALLOCATION,
            "run_id": context["run_id"], "run_attempt": 1,
            "descriptor_sha256": context["descriptor_sha256"], "body_sha256": context["body_sha256"],
            "preparation_only": True, "measurement_admitted": False}))
        report["phases_completed"].append("P06")
        report["phase"] = "P07"
        client = Client(evidence, token, started, report)
        zip_raw = client.inputs(descriptor, body)
        client.token = None
        token = None
        report["phases_completed"].append("P07")
        report["phase"] = "P08"
        report["archive"] = validate_zip(zip_raw, descriptor["historical_fixture"])
        report["phases_completed"].append("P08")
        report["classification"] = "bootstrap_ready"
    except Failure as error:
        record_failure(report, error.classification, error.code, report["phase"], error)
    except MemoryError as error:
        record_failure(report, "resource_incomplete", "memory_exhausted", report["phase"], error)
    except Exception as error:
        record_failure(report, "evidence_incomplete", "local_operation_failed", report["phase"], error)
    finally:
        if client is not None:
            client.token = None
    report["secondary_failures"].extend(item for item in report.get("transport_restoration_failures", [])
                                         if item["code"] != report["error_code"])
    report["secondary_failures"].extend(report.get("input_persistence_failures", []))
    try:
        report["phase"] = "P09"
        if runtime is not None:
            restored = state_snapshot() == runtime["state"]
            report["restoration"] = {"confirmed": restored,
                                     "memory_limit": "retained_until_leaf_process_exit",
                                     "hooks_gc_timers_limits_unchanged": restored,
                                     "responses_closed": all(item.get("close_confirmed", True)
                                                             for item in report["requests"])}
            report["restoration"]["confirmed"] = restored and report["restoration"]["responses_closed"]
            require(restored, "restoration_mismatch", "evidence_incomplete")
        evidence.verify()
    except Failure as error:
        record_failure(report, error.classification, error.code, "P09", error)
    except MemoryError as error:
        record_failure(report, "resource_incomplete", "terminal_memory_exhausted", "P09", error)
    except Exception as error:
        record_failure(report, "evidence_incomplete", "terminal_readback_failed", "P09", error)
    report["inputs"] = {name: dict(record) for name, record in evidence.files.items()}
    report["terminal_state"] = "candidate_requires_terminal_receipt"
    exit_code = EXIT_CODES[report["classification"]]
    terminal_confirmed = False
    terminal_error = "none"
    try:
        evidence.write("result.json", canonical(report), terminal=True)
        evidence.verify()
        inventory = {"schema": "worker37-output-inventory-v1", "files": evidence.files.copy(),
                     "size_bytes": evidence.payload_bytes,
                     "coverage": "module_outputs_before_inventory_and_terminal"}
        evidence.write("inventory.json", canonical(inventory), terminal=True)
        evidence.verify()
        terminal = {"schema": "worker37-durable-terminal-v1", "terminal_candidate": True,
                    "confirmation": "requires_matching_metadata_exit_and_terminal_confirmed_stdout_and_shell_readback",
                    "classification": report["classification"], "exit_code": exit_code,
                    "preparation_only": True, "measurement_admitted": False,
                    "scientific_classification": None,
                    "result_sha256": evidence.files["result.json"]["sha256"],
                    "inventory_sha256": evidence.files["inventory.json"]["sha256"],
                    "restoration_confirmed": report["restoration"]["confirmed"],
                    "provider_wrapper_custody": "pending_external_readback"}
        evidence.write("terminal.json", canonical(terminal), terminal=True)
        evidence.verify()
        terminal_confirmed = True
    except Failure as error:
        record_failure(report, error.classification, error.code, "P09", error)
        terminal_error = error.code
    except MemoryError as error:
        record_failure(report, "resource_incomplete", "terminal_memory_exhausted", "P09", error)
        terminal_error = "terminal_memory_exhausted"
    except Exception as error:
        record_failure(report, "evidence_incomplete", "terminal_write_or_readback_failed", "P09", error)
        terminal_error = "terminal_write_or_readback_failed"
    finally:
        try:
            evidence.close()
        except Failure as error:
            terminal_confirmed = False
            record_failure(report, error.classification, error.code, "P09", error)
            if terminal_error == "none":
                terminal_error = error.code
        except MemoryError as error:
            terminal_confirmed = False
            record_failure(report, "resource_incomplete", "custody_close_memory_exhausted", "P09", error)
            if terminal_error == "none":
                terminal_error = "custody_close_memory_exhausted"
        except Exception as error:
            terminal_confirmed = False
            record_failure(report, "evidence_incomplete", "custody_close_failed", "P09", error)
            if terminal_error == "none":
                terminal_error = "custody_close_failed"
    exit_code = EXIT_CODES[report["classification"]]
    # Fixed scalars follow the final readback AND descriptor close. JSON is a
    # candidate until these and the shell's actual exit/custody agree. A kill or
    # late failure cannot be mistaken for a self-attested successful receipt.
    print("WORKER37_TERMINAL_CONFIRMED=" + str(int(terminal_confirmed)))
    print("WORKER37_TERMINAL_ERROR=" + terminal_error)
    if report["primary_failure"] is not None:
        print("WORKER37_PRIMARY_CLASSIFICATION=" + report["classification"])
        print("WORKER37_PRIMARY_ERROR=" + report["error_code"])
        print("WORKER37_PRIMARY_PHASE=" + report["failed_phase"])
    for failure in report["secondary_failures"]:
        print("WORKER37_SECONDARY_FAILURE=" + failure["phase"] + ":"
              + failure["classification"] + ":" + failure["code"])
    print("WORKER37_METADATA_EXIT=" + str(exit_code))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
