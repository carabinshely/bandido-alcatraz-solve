#!/usr/bin/env python3
"""Bounded Worker34 administration only; no scientific derivation.

Production CLI requires --artifact, --frozen, --accepted-evidence, --output-dir,
--execution-freeze. Optional source/protocol locations default to this repository.
Output directory must not exist. The freeze JSON is administrative authority:
  schema: worker34-execution-freeze-v1
  execution_go: nonempty immutable authority reference
  sources: {a,b,supervisor,protocol: SHA256}
  runtime: the object printed by --describe-runtime
  reviews: {a,b,supervisor: nonempty exact-source independent review references}
  resource_test_receipt: {path: existing test receipt, sha256: SHA256}
The root coordinator creates this only after reviewing exact source/test evidence.

The Linux child-subreaper is a process-local reaping attribute, not a system or
security configuration. /proc PPid ancestry plus pidfds contain even detached
unexpected descendants. No RSS ceiling or aggregate memory guarantee is claimed.
Only stdlib is imported. Internal short-budget arguments exist for synthetic
unit tests; the production CLI never exposes alternative resource ceilings.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import resource
import signal
import stat
import subprocess
import sys
import time
from dataclasses import dataclass

PROTOCOL_SHA256 = 'cad7dc56e16b6f12d34fac7cb5b5aa8c3c5e791cb18536880e9170b162e7258e'
ADDRESS_SPACE_BYTES = 2_147_483_648
BUDGET_SECONDS = 600.0
GRACE_SECONDS = 30.0
SCIENTIFIC_FILES = ('leaves.jsonl', 'observations.jsonl', 'summary.json')
SUCCESS_STATES = frozenset(('recorded_component_tradeoff_present',
    'recorded_component_tradeoff_absent_with_unmatched_strata',
    'recorded_component_tradeoff_absent'))
FAILURES = ('integrity_invalid', 'resource_incomplete', 'execution_blocked')


class Boundary(Exception):
    def __init__(self, message, established_receipt=None):
        super().__init__(message)
        self.established_receipt = established_receipt


class Blocked(Exception):
    pass


class Integrity(Exception):
    pass


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def read_json(path, maximum=131072):
    with open(path, 'rb') as handle:
        data = handle.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError('administrative JSON exceeds size bound')
    return json.loads(data, object_pairs_hook=strict_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_exclusive(path, value):
    """Close and durably preserve one new administrative file, never overwrite."""
    with open(path, 'xb') as handle:
        handle.write(canonical(value))
        handle.flush()
        os.fsync(handle.fileno())
    fsync_directory(Path(path).parent)


def runtime_fingerprint():
    executable = str(Path(sys.executable).resolve())
    return dict(executable=executable, executable_sha256=sha256(executable),
                version=sys.version, implementation=platform.python_implementation(),
                platform=sys.platform, machine=platform.machine(),
                kernel=platform.release())


def failure_label(causes):
    """Preserve all causes; choose only the fixed deterministic precedence."""
    labels = {cause['status'] for cause in causes}
    return next((label for label in FAILURES if label in labels), None)


@dataclass
class Config:
    artifact: Path
    frozen: Path
    accepted_evidence: Path
    output_dir: Path
    execution_freeze: Path
    parser_a: Path
    parser_b: Path
    protocol: Path


class Containment:
    """One isolated supervisor owns all descendants; unrelated children forbidden."""
    def __init__(self):
        if sys.platform != 'linux' or not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
            raise Blocked('Linux /proc, child subreaper and pidfds are required')
        self.libc = ctypes.CDLL(None, use_errno=True)
        if self.libc.prctl(36, 1, 0, 0, 0) != 0:
            raise Blocked('PR_SET_CHILD_SUBREAPER unavailable')
        value = ctypes.c_int()
        if self.libc.prctl(37, ctypes.byref(value), 0, 0, 0) != 0 or value.value != 1:
            raise Blocked('child-subreaper effective state could not be verified')
        self.self_pid = os.getpid()
        self.handles = {}
        self.observed = set()
        self.reaped = []
        self.sent = []
        self.current = None
        self.proc = None
        if self.descendants():
            raise Blocked('supervisor must start with no child processes')

    @staticmethod
    def identity(pid):
        try:
            tail = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
            return int(tail[1]), int(tail[19])
        except FileNotFoundError:
            return None

    def descendants(self):
        rows = {}
        for path in Path('/proc').iterdir():
            if path.name.isdecimal():
                row = self.identity(int(path.name))
                if row is not None:
                    rows[int(path.name)] = row
        if self.self_pid not in rows:
            raise Blocked('/proc process ancestry is unavailable')
        owned = {self.self_pid}
        while True:
            added = {pid for pid, (ppid, _) in rows.items() if ppid in owned} - owned
            if not added:
                break
            owned.update(added)
        owned.remove(self.self_pid)
        for pid in owned:
            identity = rows[pid]
            key = (pid, identity[1])
            self.observed.add(key)
            if key not in self.handles:
                try:
                    fd = os.pidfd_open(pid)
                except ProcessLookupError:
                    continue
                if self.identity(pid) == identity:
                    self.handles[key] = fd
                else:
                    os.close(fd)
        return owned

    def reap(self):
        while True:
            try:
                pid, status, usage = os.wait4(-1, os.WNOHANG)
            except ChildProcessError:
                break
            if not pid:
                break
            row = dict(pid=pid, returncode=os.waitstatus_to_exitcode(status),
                       maxrss_kib=usage.ru_maxrss, user_seconds=usage.ru_utime,
                       system_seconds=usage.ru_stime)
            self.reaped.append(row)
            if pid == self.current and self.proc is not None:
                self.proc.returncode = row['returncode']

    def send(self, signum):
        self.descendants()
        for (pid, start), fd in self.handles.items():
            try:
                signal.pidfd_send_signal(fd, signum)
                self.sent.append(dict(pid=pid, start_ticks=start, signal=signum))
            except ProcessLookupError:
                pass

    def cleanup(self, grace_deadline):
        self.send(signal.SIGTERM)
        kill_at = min(time.monotonic() + 0.20, grace_deadline)
        while True:
            self.reap()
            remaining = self.descendants()
            if not remaining:
                # Reap again after the empty snapshot to close the exit race.
                self.reap()
                return True
            if time.monotonic() >= kill_at:
                self.send(signal.SIGKILL)
            if time.monotonic() >= grace_deadline:
                return False
            time.sleep(min(0.01, max(0, grace_deadline - time.monotonic())))

    def close(self):
        for fd in self.handles.values():
            os.close(fd)
        self.handles.clear()


def probe_production_limit():
    """Harmless process: verifies the effective production ceiling; no allocation."""
    code = ('import json,resource; n=2147483648; '
            'resource.setrlimit(resource.RLIMIT_AS,(n,n)); '
            'print(json.dumps(list(resource.getrlimit(resource.RLIMIT_AS))))')
    proc = subprocess.run([sys.executable, '-I', '-B', '-c', code],
                          capture_output=True, timeout=5, check=False)
    if proc.returncode or json.loads(proc.stdout) != [ADDRESS_SPACE_BYTES] * 2:
        raise Blocked('harmless effective 2GiB RLIMIT_AS check failed')
    return dict(soft=ADDRESS_SPACE_BYTES, hard=ADDRESS_SPACE_BYTES,
                mechanism='resource.RLIMIT_AS', allocated_test_payload_bytes=0)


def verify_freeze(config):
    try:
        frozen = read_json(config.execution_freeze)
    except (OSError, ValueError) as exc:
        raise Blocked('execution freeze missing or unreadable') from exc
    freeze_keys = {'schema', 'execution_go', 'sources', 'runtime', 'reviews', 'resource_test_receipt'}
    if not isinstance(frozen, dict) or set(frozen) != freeze_keys:
        raise Blocked('execution freeze must be an exact administrative JSON object')
    if (frozen.get('schema') != 'worker34-execution-freeze-v1' or
            not isinstance(frozen.get('execution_go'), str) or not frozen['execution_go'].strip()):
        raise Blocked('exact execution-go authority is missing')
    reviews = frozen.get('reviews')
    if not isinstance(reviews, dict) or set(reviews) != {'a', 'b', 'supervisor'}:
        raise Blocked('independent review records must be an exact mapping')
    if any(not isinstance(reviews.get(k), str) or not reviews[k].strip()
           for k in ('a', 'b', 'supervisor')):
        raise Blocked('independent exact-source review records are required')
    sources = frozen.get('sources')
    if (not isinstance(sources, dict) or set(sources) != {'a', 'b', 'supervisor', 'protocol'} or
            any(not isinstance(value, str) or len(value) != 64 or
                any(c not in '0123456789abcdef' for c in value) for value in sources.values())):
        raise Blocked('source pins must be an exact SHA256 mapping')
    claimed_runtime = frozen.get('runtime')
    runtime_keys = {'executable', 'executable_sha256', 'version', 'implementation', 'platform', 'machine', 'kernel'}
    if (not isinstance(claimed_runtime, dict) or set(claimed_runtime) != runtime_keys or
            any(not isinstance(value, str) or not value for value in claimed_runtime.values())):
        raise Blocked('runtime must be an exact string-valued mapping')
    evidence = frozen.get('resource_test_receipt')
    if (not isinstance(evidence, dict) or set(evidence) != {'path', 'sha256'} or
            not isinstance(evidence['path'], str) or not evidence['path'] or
            not isinstance(evidence['sha256'], str) or len(evidence['sha256']) != 64 or
            any(c not in '0123456789abcdef' for c in evidence['sha256'])):
        raise Blocked('verified synthetic resource-test receipt must be an exact mapping')
    actual = {'a': sha256(config.parser_a), 'b': sha256(config.parser_b),
              'supervisor': sha256(Path(__file__)), 'protocol': sha256(config.protocol)}
    if actual['protocol'] != PROTOCOL_SHA256 or frozen.get('sources') != actual:
        raise Integrity('protocol or implementation source hash differs from execution freeze')
    runtime = runtime_fingerprint()
    if frozen.get('runtime') != runtime:
        raise Blocked('interpreter/environment differs from verified execution freeze')
    if sha256(evidence['path']) != evidence['sha256']:
        raise Integrity('resource preflight evidence hash mismatch')
    if not config.artifact.is_file() or not config.frozen.is_dir() or not config.accepted_evidence.is_dir():
        raise Blocked('a required input location is unavailable before admission')
    return frozen, actual, runtime


def preserve_sources(config, hashes):
    root = config.output_dir / 'frozen-sources'
    (root / 'scripts').mkdir(parents=True)
    (root / 'experiments' / 'recorded-endpoint-decomposition').mkdir(parents=True)
    copies = {}
    for key, original, destination in (
        ('a', config.parser_a, root / 'scripts' / 'worker34_parser_a.py'),
        ('b', config.parser_b, root / 'scripts' / 'worker34_parser_b.py'),
        ('supervisor', Path(__file__), root / 'scripts' / 'worker34_supervise.py'),
        ('protocol', config.protocol, root / 'experiments' / 'recorded-endpoint-decomposition' / 'PROTOCOL.md')):
        with open(original, 'rb') as src, open(destination, 'xb') as dst:
            while block := src.read(1024 * 1024):
                dst.write(block)
            dst.flush()
            os.fsync(dst.fileno())
        if sha256(destination) != hashes[key]:
            raise Integrity('source changed while preserving frozen bytes: ' + key)
        copies[key] = destination
    for directory in (root / 'scripts', root / 'experiments' / 'recorded-endpoint-decomposition',
                      root / 'experiments', root, config.output_dir):
        fsync_directory(directory)
    return copies


def inspect_parser_receipt(path, parser_id, expected_source, runtime, pid):
    """Only administrative evidence, never derived leaves or observation fields."""
    receipt = read_json(path)
    needed = {'parser_id', 'source_sha256', 'interpreter_executable', 'interpreter_version',
              'pid', 'rlimit_as_soft', 'rlimit_as_hard', 'status', 'completed',
              'elapsed_seconds', 'maxrss_kib', 'established_integrity_failure', 'errors'}
    if not isinstance(receipt, dict) or not needed <= receipt.keys():
        raise Boundary('missing or malformed parser completion/resource receipt')
    if receipt['parser_id'] != parser_id or receipt['source_sha256'] != expected_source:
        raise Integrity('completed parser identity/source receipt mismatch')
    for key in ('completed', 'established_integrity_failure'):
        if type(receipt[key]) is not bool:
            raise Boundary('unverified Boolean parser receipt field: ' + key)
    if receipt['status'] not in {*FAILURES, 'complete'}:
        raise Boundary('unrecognized parser receipt status')
    if (not isinstance(receipt['errors'], list) or
            any(not isinstance(item, str) for item in receipt['errors'])):
        raise Boundary('malformed parser diagnostic list')
    established = receipt if (receipt['established_integrity_failure'] and
                               receipt['status'] == 'integrity_invalid') else None
    if (type(receipt['pid']) is not int or receipt['pid'] != pid or
        type(receipt['rlimit_as_soft']) is not int or type(receipt['rlimit_as_hard']) is not int or
        receipt['rlimit_as_soft'] != ADDRESS_SPACE_BYTES or receipt['rlimit_as_hard'] != ADDRESS_SPACE_BYTES or
        not isinstance(receipt['interpreter_executable'], str) or
        str(Path(receipt['interpreter_executable']).resolve()) != runtime['executable'] or
        receipt['interpreter_version'] != runtime['version']):
        raise Boundary('parser runtime identity or effective 2GiB limit is unverified', established)
    for key in ('elapsed_seconds', 'maxrss_kib'):
        value = receipt[key]
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise Boundary('invalid parser accounting field: ' + key, established)
    if (not isinstance(receipt['errors'], list) or
            any(not isinstance(item, str) for item in receipt['errors'])):
        raise Boundary('malformed parser diagnostic list')
    if receipt['status'] == 'complete' and (not receipt['completed'] or receipt['established_integrity_failure']):
        raise Boundary('inconsistent parser completion receipt')
    if receipt['status'] == 'integrity_invalid' and not receipt['established_integrity_failure']:
        raise Boundary('integrity claim lacks completed validation evidence')
    return receipt


def compare_streams(left, right):
    """Compare every byte; return both file hashes even when streams differ."""
    hleft, hright = hashlib.sha256(), hashlib.sha256()
    size_left = size_right = 0
    equal = True
    with open(left, 'rb') as lhs, open(right, 'rb') as rhs:
        while True:
            a, b = lhs.read(1024 * 1024), rhs.read(1024 * 1024)
            if not a and not b:
                break
            hleft.update(a)
            hright.update(b)
            size_left += len(a)
            size_right += len(b)
            equal = equal and a == b
    return dict(equal=equal, a_sha256=hleft.hexdigest(), b_sha256=hright.hexdigest(),
                a_bytes=size_left, b_bytes=size_right)


def run_supervisor(config, *, _budget_seconds=BUDGET_SECONDS, _grace_seconds=GRACE_SECONDS):
    """Internal timing injection is exclusively for harmless synthetic unit tests."""
    config.output_dir.mkdir(parents=False, exist_ok=False)
    fsync_directory(config.output_dir.parent)
    causes, parser_records, comparisons = [], [], {}
    hashes = runtime = copies = frozen = None
    containment = None
    admitted = False
    cleanup_confirmed = True
    cleanup_errors = []
    cleanup_recovery_confirmed = None
    start = deadline = abort_started = None
    scope = ('Controlled serial launch, source/runtime freeze, monotonic watchdog, '
             'per-process status/rusage, streaming byte comparison and receipts only; '
             'no scientific decomposition; no aggregate RSS ceiling.')
    receipt = dict(schema='worker34-supervisor-receipt-v1', scope=scope,
                   production_budget_seconds=BUDGET_SECONDS,
                   budget_seconds=_budget_seconds, grace_seconds=_grace_seconds,
                   parser_address_space_bytes=ADDRESS_SPACE_BYTES,
                   scientific_outputs_accepted=False)

    def cause(status, message):
        causes.append(dict(status=status, message=str(message)))
        # No potentially blocking persistence before the workload is stopped.
        # Completed validation facts remain captured here for abort precedence.

    def grace_expired(_signum, _frame):
        if containment is not None:
            containment.send(signal.SIGKILL)
        os._exit(75)  # Missing completion receipt itself means resource failure.

    def begin_abort():
        nonlocal abort_started
        first_abort = abort_started is None
        if first_abort:
            abort_started = time.monotonic()
        signal.signal(signal.SIGALRM, grace_expired)
        signal.setitimer(signal.ITIMER_REAL,
                         max(0.000001, abort_started + _grace_seconds - time.monotonic()))
        if first_abort and containment is not None:
            # No parser gets a grace-period computation window. Signal first;
            # persistence and reaping follow under this same, never-reset grace.
            containment.send(signal.SIGTERM)
            containment.send(signal.SIGKILL)

    def expired(_signum, _frame):
        begin_abort()
        raise Boundary('whole-workload monotonic deadline reached')

    previous_handler = signal.getsignal(signal.SIGALRM)
    try:
        frozen, hashes, runtime = verify_freeze(config)
        copies = preserve_sources(config, hashes)
        write_exclusive(config.output_dir / 'admitted-freeze.json', frozen)
        receipt['production_limit_probe'] = probe_production_limit()
        containment = Containment()
        # All preflight is source/admin-only. This starts before the first real
        # input byte is read by either parser and is never reset between passes.
        start = time.monotonic()
        deadline = start + _budget_seconds
        admitted = True
        signal.signal(signal.SIGALRM, expired)
        signal.setitimer(signal.ITIMER_REAL, _budget_seconds)
        for parser_id in ('a', 'b'):
            out = config.output_dir / ('parser-' + parser_id)
            # Parser owns its exclusive directory creation.
            log = config.output_dir / ('parser-' + parser_id + '.log')
            command = [runtime['executable'], '-I', '-B', str(copies[parser_id]),
                       '--artifact', str(config.artifact.resolve()),
                       '--frozen', str(config.frozen.resolve()),
                       '--accepted-evidence', str(config.accepted_evidence.resolve()),
                       '--output-dir', str(out.resolve())]
            with open(log, 'xb', buffering=0) as logs:
                proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=logs,
                                        stderr=subprocess.STDOUT, start_new_session=True,
                                        cwd=config.output_dir, close_fds=True,
                                        env={'PATH': os.defpath, 'LANG': 'C.UTF-8'})
                containment.current, containment.proc = proc.pid, proc
                while proc.returncode is None:
                    descendants = containment.descendants()
                    if descendants - {proc.pid}:
                        raise Boundary('unexpected parser descendant observed')
                    containment.reap()
                    if proc.returncode is None:
                        time.sleep(min(0.01, max(0, deadline - time.monotonic())))
                os.fsync(logs.fileno())
            # Capture completed receipt before cleanup checks so established
            # integrity failure is not erased by subsequent resource failures.
            record = dict(parser_id=parser_id, pid=proc.pid, returncode=proc.returncode,
                          command=command, output_dir=str(out.resolve()))
            parser_records.append(record)
            try:
                parsed = inspect_parser_receipt(out / 'parser-receipt.json', parser_id,
                                                hashes[parser_id], runtime, proc.pid)
            except (OSError, ValueError, TypeError) as exc:
                raise Boundary('parser completion receipt unavailable or malformed: ' + str(exc)) from exc
            record['receipt'] = parsed
            record['receipt_sha256'] = sha256(out / 'parser-receipt.json')
            if parsed['established_integrity_failure']:
                cause('integrity_invalid', 'parser ' + parser_id + ': ' + '; '.join(parsed['errors']))
            if parsed['status'] in FAILURES:
                cause(parsed['status'], 'parser ' + parser_id + ' reported ' + parsed['status'])
            if proc.returncode < 0 or (parsed['status'] == 'complete' and
                                        (proc.returncode != 0 or not parsed['completed'])):
                cause('resource_incomplete', 'parser did not supply normal complete-output closure')
            if containment.descendants():
                cause('resource_incomplete', 'unexpected descendant survived parser exit')
            if causes:
                break
            for name in SCIENTIFIC_FILES:
                file = out / name
                if not file.is_file() or file.is_symlink():
                    raise Boundary('complete scientific output missing or not a regular file: ' + name)
                with open(file, 'rb') as handle:
                    if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                        raise Boundary('non-regular scientific file')
                    os.fsync(handle.fileno())
            fsync_directory(out)
        if not causes:
            for name in SCIENTIFIC_FILES:
                comparisons[name] = compare_streams(config.output_dir / 'parser-a' / name,
                                                     config.output_dir / 'parser-b' / name)
                if not comparisons[name]['equal']:
                    cause('integrity_invalid', 'completed parser output bytes disagree: ' + name)
            if not causes:
                # Only the status label is consumed; no N/U/leaf/scientific logic.
                status = read_json(config.output_dir / 'parser-a' / 'summary.json').get('status')
                if status not in SUCCESS_STATES:
                    raise Integrity('completed common summary has unsupported status metadata')
                receipt['status'] = status
                receipt['scientific_outputs_accepted'] = True
        if time.monotonic() >= deadline:
            raise Boundary('deadline reached during output comparison/closure')
    except Integrity as exc:
        cause('integrity_invalid', exc)
    except Boundary as exc:
        # Stop the workload timer now; the separate grace is exclusively cleanup
        # and abort-receipt preservation, never parser or comparison work.
        begin_abort()
        if exc.established_receipt is not None:
            cause('integrity_invalid', '; '.join(exc.established_receipt['errors']))
        cause('resource_incomplete', exc)
    except (Blocked, OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        cause('resource_incomplete' if admitted else 'execution_blocked', exc)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        # Normal completion's closure is still charged to the original budget.
        remaining = max(0.0, deadline - time.monotonic()) if deadline is not None else None
        if admitted and remaining == 0 and not any(c['status'] == 'resource_incomplete' for c in causes):
            cause('resource_incomplete', 'whole-workload budget exhausted before final closure')
        if causes:
            receipt['scientific_outputs_accepted'] = False
        grace_deadline = (abort_started if abort_started is not None else time.monotonic()) + _grace_seconds
        if causes:
            begin_abort()
        else:
            signal.signal(signal.SIGALRM, expired)
            signal.setitimer(signal.ITIMER_REAL, remaining or _grace_seconds)
        def refresh_administration():
            # Provenance must not depend on a successful cleanup call. This is
            # captured before cleanup and refreshed after every recovery path.
            process_control = None
            if containment is not None:
                process_control = dict(
                    child_subreaper=True, descendant_detection='/proc PPid ancestry and pidfds',
                    observed_pids=[dict(pid=p, start_ticks=s) for p, s in sorted(containment.observed)],
                    reaped=containment.reaped, signals=containment.sent)
            receipt.update(admitted=admitted, cleanup_confirmed=cleanup_confirmed,
                           cleanup_errors=cleanup_errors,
                           cleanup_recovery_confirmed=cleanup_recovery_confirmed,
                           process_control=process_control,
                           causes=causes, parser_executions=parser_records,
                           source_sha256=hashes, runtime=runtime, comparisons=comparisons,
                           elapsed_seconds_before_receipt_close=(time.monotonic() - start if start else 0),
                           supervisor_maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)

        cleanup_confirmed = containment is None
        refresh_administration()
        try:
            if containment is not None:
                try:
                    if causes:
                        cleanup_confirmed = containment.cleanup(grace_deadline)
                    else:
                        containment.reap()
                        cleanup_confirmed = not containment.descendants()
                except (OSError, Blocked) as error:
                    cleanup_confirmed = False
                    cleanup_errors.append(str(error))
                    cause('resource_incomplete', 'cleanup unconfirmed: ' + str(error))
                    begin_abort()
                    # Never restart the grace. Recover only termination/reaping;
                    # no parser, input read, or scientific comparison is retried.
                    recovery_deadline = abort_started + _grace_seconds
                    cleanup_recovery_confirmed = False
                    try:
                        while time.monotonic() < recovery_deadline:
                            containment.send(signal.SIGKILL)
                            containment.reap()
                            if not containment.descendants():
                                containment.reap()
                                cleanup_recovery_confirmed = True
                                break
                            time.sleep(min(.01, max(0, recovery_deadline - time.monotonic())))
                    except (OSError, Blocked) as recovery_error:
                        cleanup_errors.append('recovery unconfirmed: ' + str(recovery_error))
                    # Keep primary cleanup explicitly unconfirmed even when the
                    # separately recorded recovery establishes no survivors.
                if not cleanup_confirmed:
                    cause('resource_incomplete', 'cleanup could not establish no surviving descendants')
            refresh_administration()
            label = failure_label(causes)
            if label:
                receipt['status'] = label
                receipt['scientific_outputs_accepted'] = False
            def mark_incomplete():
                for parser_id in ('a', 'b'):
                    directory = config.output_dir / ('parser-' + parser_id)
                    marker = directory / 'ATTEMPT-INCOMPLETE.json'
                    if directory.exists() and not marker.exists():
                        write_exclusive(marker, dict(status=receipt['status'], accepted=False))

            def publish_receipt():
                # A canonical success name is exposed only after its bytes and
                # staging directory entry have been flushed and closed.
                pending = config.output_dir / 'supervisor-receipt.pending.json'
                write_exclusive(pending, receipt)
                pending.rename(config.output_dir / 'supervisor-receipt.json')
                fsync_directory(config.output_dir)

            if causes:
                write_exclusive(config.output_dir / 'events.jsonl', dict(causes=causes))
                mark_incomplete()
            receipt['elapsed_seconds_before_receipt_close'] = time.monotonic() - start if start else 0
            publish_receipt()
            if receipt['scientific_outputs_accepted'] and time.monotonic() >= deadline:
                raise Boundary('deadline reached while closing final result receipt')
        except (Boundary, OSError) as exc:
            # Fail closed for write/flush/fsync/rename/directory-closure failure,
            # not only deadline exceptions. Stop children before any persistence.
            begin_abort()
            cause('resource_incomplete', exc)
            refresh_administration()
            receipt.update(status=failure_label(causes), causes=causes,
                           elapsed_seconds_before_receipt_close=(time.monotonic() - start if start else 0),
                           scientific_outputs_accepted=False)
            preservation_errors = []
            # Invalidate every possibly published success before attempting
            # another write. Rename preserves exact partial bytes. If rename is
            # unavailable, truncation prevents an apparently valid success.
            for name in ('supervisor-receipt.json', 'supervisor-receipt.pending.json'):
                source = config.output_dir / name
                if source.exists():
                    destination = config.output_dir / (name + '.incomplete')
                    try:
                        source.rename(destination)
                    except OSError as error:
                        preservation_errors.append(str(error))
                        try:
                            with open(source, 'wb'):
                                pass
                        except OSError as error:
                            preservation_errors.append('could not invalidate ' + name + ': ' + str(error))
            # Abort preservation is best-effort under the same grace. A missing
            # final receipt remains an explicit complete-output resource failure;
            # no failed persistence operation restarts scientific computation.
            receipt['receipt_preservation_errors'] = preservation_errors
            for parser_id in ('a', 'b'):
                directory = config.output_dir / ('parser-' + parser_id)
                marker = directory / 'ATTEMPT-INCOMPLETE.json'
                try:
                    if directory.exists() and not marker.exists():
                        write_exclusive(marker, dict(status=receipt['status'], accepted=False))
                except OSError as error:
                    preservation_errors.append(str(error))
            try:
                final = config.output_dir / 'supervisor-receipt.json'
                # If emergency invalidation left an empty original, preserve it
                # separately before exclusive abort publication where possible.
                if final.exists():
                    final.rename(config.output_dir / 'supervisor-receipt.invalidated')
                receipt['elapsed_seconds_before_receipt_close'] = time.monotonic() - start if start else 0
                write_exclusive(final, receipt)
            except OSError as error:
                preservation_errors.append(str(error))
                # Separate fallback is an abort receipt, never a success retry.
                try:
                    write_exclusive(config.output_dir / 'supervisor-abort-receipt.json', receipt)
                except OSError as error:
                    preservation_errors.append(str(error))
        finally:
            if containment is not None:
                containment.close()
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--describe-runtime', action='store_true')
    for name in ('artifact', 'frozen', 'accepted-evidence', 'output-dir', 'execution-freeze'):
        parser.add_argument('--' + name, type=Path)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument('--parser-a', type=Path, default=root / 'scripts' / 'worker34_parser_a.py')
    parser.add_argument('--parser-b', type=Path, default=root / 'scripts' / 'worker34_parser_b.py')
    parser.add_argument('--protocol', type=Path,
                        default=root / 'experiments' / 'recorded-endpoint-decomposition' / 'PROTOCOL.md')
    args = parser.parse_args()
    if args.describe_runtime:
        print(canonical(runtime_fingerprint()).decode(), end='')
        return 0
    if any(getattr(args, key) is None for key in ('artifact', 'frozen', 'accepted_evidence', 'output_dir', 'execution_freeze')):
        parser.error('all input/output and execution-freeze arguments are required')
    values = vars(args)
    values.pop('describe_runtime')
    result = run_supervisor(Config(**{key: value.resolve() for key, value in values.items()}))
    print(canonical({'status': result['status'], 'receipt': str(args.output_dir / 'supervisor-receipt.json')}).decode(), end='')
    return 0 if result['scientific_outputs_accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
