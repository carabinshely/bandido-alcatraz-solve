"""Closed397-method native preparation entrypoint; never a research launcher.

This file is inert until the separately reviewed exact map hash is supplied.
The map pins all source, fixture, command, retention and output definitions.
"""
from __future__ import annotations

import builtins
import fnmatch
import gc
import hashlib
import importlib.abc
import importlib.util
import io
import json
import os
from pathlib import Path
import resource
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / 'evidence-design/worker38-fixed-fixtures.json'
OUTPUT = Path('/workspace/shared/worker38-native-batch-01')
LOG_CAP = 8 * 1024 ** 2
PREFIX_CAP = 24 * 1024 ** 2
MEMORY_CAP = 512 * 1024 ** 2
GLOBAL_RESERVE = 65536
GLOBAL_RECORD_LIMITS = {'start.json': 4096, 'receipt.json': 16384, 'index.json': 45056}
# Tests deliberately mock these modules. Capture real observations beforehand.
NOW = time.monotonic
BOOT_NS = time.clock_gettime_ns
OPEN = builtins.open
LSTAT = os.lstat
LISTDIR = os.listdir
READLINK = os.readlink
GETPID = os.getpid
GETRLIMIT = resource.getrlimit
FSYNC = os.fsync
OS_WRITE = os.write
OS_OPEN = os.open
OS_CLOSE = os.close
FSTAT = os.fstat
GET_PROFILE = sys.getprofile
GET_TRACE = sys.gettrace
GET_TIMER = signal.getitimer
GET_HANDLER = signal.getsignal
GC_ENABLED = gc.isenabled
GC_THRESHOLDS = gc.get_threshold
THREAD_COUNT = threading.active_count
ORIGINAL_TEMPORARY_DIRECTORY = tempfile.TemporaryDirectory


class BatchStopped(BaseException):
    def __init__(self, reason, status='execution_incomplete'):
        super().__init__(reason)
        self.reason = reason
        self.status = status


FAILURE_PRIORITY = {'execution_blocked': 0, 'execution_incomplete': 1,
                    'resource_incomplete': 2, 'integrity_invalid': 3}
FAILURE_SEQUENCE = 0


def typed_failure_status(error):
    if isinstance(error, BatchStopped):
        return error.status
    if isinstance(error, (MemoryError, RecursionError, subprocess.TimeoutExpired)):
        return 'resource_incomplete'
    # Only exact classes from the already pinned, lazily loaded modules count.
    # Arbitrary similarly named exceptions or free-form text do not classify.
    admission = sys.modules.get('worker38.admission')
    admission_error = getattr(admission, 'AdmissionError', None)
    if isinstance(admission_error, type) and isinstance(error, admission_error):
        status = error.classification
        return 'execution_incomplete' if status == 'evidence_incomplete' else (
            status if type(status) is str and status in FAILURE_PRIORITY else 'integrity_invalid')
    common = sys.modules.get('worker38.common')
    if common is not None:
        resource_error = getattr(common, 'ResourceExceeded', None)
        integrity_error = getattr(common, 'IntegrityError', None)
        if isinstance(resource_error, type) and isinstance(error, resource_error):
            return 'resource_incomplete'
        if isinstance(integrity_error, type) and isinstance(error, integrity_error):
            return 'integrity_invalid'
    return 'execution_incomplete'


def retain_failure(state, error, phase, code=None):
    """Fixed bounded typed evidence, strongest cause wins; equal keeps first."""
    global FAILURE_SEQUENCE
    FAILURE_SEQUENCE += 1
    status = typed_failure_status(error)
    record = {'error_type': type(error).__name__[:64], 'status': status,
              'code': (code or (error.reason if isinstance(error, BatchStopped) else
                       'native_unexpected_exception'))[:160], 'phase': phase,
              'observed_order': FAILURE_SEQUENCE}
    return retain_failure_record(state, record)


def retain_failure_record(state, record):
    status = record['status']
    if state is None:
        return {**record, 'primary_failure': record, 'secondary_failures': [],
                'additional_failure_records_omitted': 0}
    old = state['primary_failure']
    if (FAILURE_PRIORITY[status] > FAILURE_PRIORITY[old['status']] or
            FAILURE_PRIORITY[status] == FAILURE_PRIORITY[old['status']] and
            record['observed_order'] < old['observed_order']):
        state.update(record)
        state['primary_failure'] = record
        record = old
    if len(state['secondary_failures']) < 12:
        state['secondary_failures'].append(record)
        state['secondary_failures'].sort(key=lambda item: item['observed_order'])
    else:
        state['additional_failure_records_omitted'] += 1
    return state


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def sync_directory(path):
    fd = OS_OPEN(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        FSYNC(fd)
    finally:
        OS_CLOSE(fd)


def runtime_isolation_snapshot():
    return (GET_PROFILE(), GET_TRACE(), GC_ENABLED(), GC_THRESHOLDS(), THREAD_COUNT(),
            tuple(GET_TIMER(item) for item in (signal.ITIMER_REAL, signal.ITIMER_VIRTUAL, signal.ITIMER_PROF)),
            GET_HANDLER(signal.SIGALRM), GET_HANDLER(signal.SIGUSR1), GETRLIMIT(resource.RLIMIT_AS))


def verify_project_namespace(tree, deadline):
    policy = {'recursive': True, 'follow_symlinks': False, 'symlinks_allowed': False,
              'special_nodes_allowed': False, 'non_ascii_names_allowed': False,
              'candidate_file_suffixes': ['.py', '.pyc', '.so'],
              'directory_rule': 'name.isidentifier() (includes __pycache__)'}
    root = Path(tree['root'])
    if (tree['schema'] != 'worker38-project-import-namespace-v2' or
            tree['exists'] is not True or tree['root_type'] != 'directory' or
            tree['policy'] != policy or not root.is_absolute()):
        raise BatchStopped('native project namespace schema differs', 'execution_blocked')
    ancestors = []
    for path in [*reversed(root.parents), root]:
        if not stat.S_ISDIR(LSTAT(path).st_mode):
            raise BatchStopped('native project root ancestry differs', 'execution_blocked')
        ancestors.append([str(path), 'directory', None])
    entries = []
    def visit(path, prefix=''):
        if NOW() >= deadline:
            raise BatchStopped('native cooperative cutoff expired during namespace check', 'resource_incomplete')
        for name in sorted(LISTDIR(path)):
            if not name.isascii():
                raise BatchStopped('native project entry domain differs', 'execution_blocked')
            child = path / name
            info = LSTAT(child)
            is_dir, is_link = stat.S_ISDIR(info.st_mode), stat.S_ISLNK(info.st_mode)
            if not (name.endswith(('.py', '.pyc', '.so')) or
                    name.isidentifier() and (is_dir or is_link)):
                continue
            kind = ('symlink' if is_link else 'directory' if is_dir else
                    'file' if stat.S_ISREG(info.st_mode) else 'special')
            relative = prefix + name
            entries.append([relative, kind, READLINK(child) if is_link else None])
            if kind in ('symlink', 'special'):
                raise BatchStopped('native project candidate alias or special node', 'execution_blocked')
            if is_dir and name.isidentifier():
                visit(child, relative + '/')
    visit(root)
    entries.sort(key=lambda row: row[0])
    if (ancestors != tree['ancestor_entries'] or entries != tree['entries'] or
            sha(canonical(entries)) != tree['entries_sha256']):
        raise BatchStopped('native project namespace changed', 'execution_blocked')


def verify_native_environment(binding, expected_environment, deadline):
    """Recheck the one frozen native metadata manifest; never launch a probe."""
    path = ROOT / binding['path']
    size, digest = hash_file(path)
    if size != binding['size_bytes'] or digest != binding['sha256']:
        raise BatchStopped('native environment manifest changed', 'execution_blocked')
    actual = dict(os.environ)
    for name in ('WORKER38_FIXED_MAP_SHA256', 'WORKER38_NATIVE_DEADLINE_CS'):
        actual.pop(name, None)
    if (actual != expected_environment or not sys.dont_write_bytecode or
            not sys.flags.safe_path or sys.pycache_prefix is not None):
        raise BatchStopped('native positive environment differs', 'execution_blocked')
    with OPEN(path, 'rb') as stream:
        metadata = json.load(stream)
    checked = set()
    def check_file(record):
        name = record['path']
        if name in checked:
            return
        if NOW() >= deadline:
            raise BatchStopped('original native deadline expired during metadata checks', 'resource_incomplete')
        try:
            info = LSTAT(name)
        except FileNotFoundError:
            if record.get('exists') is False:
                checked.add(name); return
            raise
        if record.get('exists') is False:
            raise BatchStopped('native absent-path binding changed', 'execution_blocked')
        if record.get('type') == 'symlink':
            if not stat.S_ISLNK(info.st_mode) or READLINK(name) != record['target']:
                raise BatchStopped('native symlink binding changed', 'execution_blocked')
            if 'resolved' in record and str(Path(name).resolve()) != record['resolved']:
                raise BatchStopped('native resolved target changed', 'execution_blocked')
        elif record.get('type') == 'file' and not stat.S_ISREG(info.st_mode):
            raise BatchStopped('native regular-file binding changed', 'execution_blocked')
        if 'mode' in record and stat.S_IMODE(info.st_mode) != record['mode']:
            raise BatchStopped('native mode binding changed', 'execution_blocked')
        if 'mtime_ns' in record and Path(name).stat().st_mtime_ns != record['mtime_ns']:
            raise BatchStopped('native cache/source timestamp binding changed', 'execution_blocked')
        if 'sha256' in record:
            got_size, got_hash = hash_file(name)
            if got_size != record['size_bytes'] or got_hash != record['sha256']:
                raise BatchStopped('native file bytes changed', 'execution_blocked')
        checked.add(name)
    def walk(value):
        if isinstance(value, dict):
            if 'path' in value and 'exists' in value:
                check_file(value)
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
    walk(metadata)
    for key in ('stdlib_complete_tree', 'SSL_default_certificate_tree'):
        tree = metadata[key]
        actual_names = []
        def names_below(directory, prefix=''):
            for leaf in sorted(LISTDIR(directory)):
                relative = prefix + leaf
                child = str(Path(directory) / leaf)
                if stat.S_ISDIR(LSTAT(child).st_mode):
                    names_below(child, relative + '/')
                else:
                    actual_names.append(relative)
        names_below(tree['root'])
        if sorted(actual_names) != sorted(row[0] for row in tree['entries']):
            raise BatchStopped('native library namespace changed', 'execution_blocked')
        for relative, kind, length, pin, mtime, target, resolved in tree['entries']:
            name = str(Path(tree['root']) / relative)
            check_file({'path': name, 'exists': True, 'type': kind, 'size_bytes': length,
                        'sha256': pin, 'mtime_ns': mtime,
                        **({'target': target, 'resolved': resolved} if kind == 'symlink' else {})})
    for tree in metadata['site']['global_site_directory_namespaces']:
        if tree['exists'] is False:
            try:
                LSTAT(tree['root'])
            except FileNotFoundError:
                continue
            raise BatchStopped('native absent site directory appeared', 'execution_blocked')
        if tree['exists'] is not True or not stat.S_ISDIR(LSTAT(tree['root']).st_mode):
            raise BatchStopped('native site directory binding differs', 'execution_blocked')
        names = sorted(LISTDIR(tree['root']))
        if names != [row[0] for row in tree['entries']]:
            raise BatchStopped('native site namespace changed', 'execution_blocked')
    namespaces = metadata['project_import_roots']
    if [tree['root'] for tree in namespaces] != [str(ROOT / name) for name in ('evidence-design', 'tests', 'scripts')]:
        raise BatchStopped('native project namespace roots differ', 'execution_blocked')
    for tree in namespaces:
        verify_project_namespace(tree, deadline)
    return len(checked)


def hash_file(path, durable=False):
    total = 0
    digest = hashlib.sha256()
    with OPEN(path, 'rb') as stream:
        while block := stream.read(65536):
            total += len(block)
            digest.update(block)
        if durable:
            FSYNC(stream.fileno())
    return total, digest.hexdigest()


def inventory(root, durable=False):
    """No-follow observations of the retained finite scratch tree."""
    root = os.fspath(root)
    rows = []
    def visit(directory, prefix=''):
        for name in sorted(LISTDIR(directory)):
            path = directory + '/' + name
            relative = prefix + name
            if len(path.encode('ascii')) > 512:
                raise BatchStopped('native path outside frozen scalar domain')
            info = LSTAT(path)
            if stat.S_ISDIR(info.st_mode):
                visit(path, relative + '/')
            elif stat.S_ISREG(info.st_mode):
                size, digest = hash_file(path, durable=durable)
                rows.append({'path': relative, 'type': 'file', 'size_bytes': size,
                             'sha256': digest, 'mode': stat.S_IMODE(info.st_mode),
                             'device': info.st_dev, 'inode': info.st_ino, 'nlink': info.st_nlink})
            elif stat.S_ISLNK(info.st_mode):
                target = os.fsencode(READLINK(path))
                rows.append({'path': relative, 'type': 'symlink', 'size_bytes': len(target),
                             'sha256': sha(target), 'mode': stat.S_IMODE(info.st_mode),
                             'device': info.st_dev, 'inode': info.st_ino, 'nlink': info.st_nlink})
            else:
                rows.append({'path': relative, 'type': 'special', 'size_bytes': 0,
                             'mode': stat.S_IMODE(info.st_mode),
                             'device': info.st_dev, 'inode': info.st_ino, 'nlink': info.st_nlink})
        if durable:
            sync_directory(directory)
    visit(root)
    return rows


class DenyScientificImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('bandido_alcatraz', 'worker36', 'scripts.worker36')) or fullname in (
                'benchmark_worker35_synthetic', 'worker35_resources',
                'run_quota_reserve_closure_development', 'worker31_geometry'):
            raise BatchStopped('historical scientific import outside fixed literal preparation: ' + fullname)
        return None


def deny_network(*args, **kwargs):
    raise BatchStopped('live network outside fixed literal preparation')


class LogStream(io.TextIOBase):
    def __init__(self, path):
        self.stream = OPEN(path, 'xb', buffering=0)
        self.size = 0
        self.case_started = 0
        self.case_limit = 0
        self.overflow = False
        self.write_failure = False
        self.size_complete = True
        self.failure = None
    def writable(self):
        return True
    @property
    def buffer(self):
        return self
    def write(self, value):
        if self.write_failure:
            raise BatchStopped('native log capture already failed')
        raw = value if isinstance(value, bytes) else value.encode('utf-8', errors='backslashreplace')
        remaining = min(LOG_CAP - self.size, self.case_limit - (self.size - self.case_started))
        if len(raw) > remaining:
            self.overflow = True
            self.failure = retain_failure(self.failure,
                BatchStopped('native stdout/stderr allowance exhausted', 'resource_incomplete'), 'log_write')
            if remaining:
                self._write_once(raw[:remaining])
            raise BatchStopped('native stdout/stderr allowance exhausted; prefix retained', 'resource_incomplete')
        self._write_once(raw)
        return len(value)
    def _write_once(self, raw):
        try:
            count = self.stream.write(raw)
        except BaseException as error:
            self.write_failure = True
            self.size_complete = False
            self.failure = retain_failure(self.failure, error, 'log_write')
            # A failed unbuffered write may leave a prefix. This one bounded
            # size observation never authorizes another write or loses cause.
            try:
                observed = FSTAT(self.stream.fileno()).st_size
                if self.size <= observed <= self.size + len(raw):
                    self.size = observed
                    self.size_complete = True
            except BaseException as observation_error:
                self.failure = retain_failure(self.failure, observation_error, 'log_size_observation')
            raise
        if type(count) is not int or not 0 <= count <= len(raw):
            self.write_failure = True
            self.size_complete = False
            raise BatchStopped('native log write count is unconfirmed')
        self.size += count
        if count != len(raw):
            self.write_failure = True
            raise BatchStopped('native log short write; actual prefix retained')
    def flush(self):
        self.stream.flush()
    def durable(self):
        self.flush(); FSYNC(self.stream.fileno())


class Capture:
    def __init__(self, plan, started, deadline, boottime_deadline_ns):
        self.plan = plan
        self.started = started
        self.deadline = deadline
        self.boottime_deadline_ns = boottime_deadline_ns
        self.current = None
        self.current_row = None
        self.case_root = None
        self.temp_count = 0
        self.roots = []
        self.hooks = []
        self.output_files = {}
        self.input_files = {}
        self.records_bytes = 0
        self.method_results = []
        self.observations = []
        self.stopped = None
        self.settled_prefix_bytes = 0
        self.active_prefix_reservation = 0
        self.active_log_reservation = 0
        self.case_record_bytes = 0
        self.global_record_bytes = 0
        self.global_record_attempts = set()
        self.collect_attempted = False
        self.inventory_index = []
        self.started_selectors = []
        self.log = None
        self.failure = None

    def fail(self, error, phase, code=None):
        self.failure = retain_failure(self.failure, error, phase, code)
        # One closed helper interface: unexpected A-case cause survives a
        # later prefix-retention error, whose type still participates here.
        if self.current_row and self.current_row.get('literal_case_id', '').startswith('A'):
            retention_error = getattr(error, 'worker38_prefix_retention_exception', None)
            if isinstance(retention_error, BaseException):
                self.failure = retain_failure(self.failure, retention_error, 'admission_prefix_retention')

    def merge_failure(self, state):
        if state is not None:
            for record in [state['primary_failure'], *state['secondary_failures']]:
                self.failure = retain_failure_record(self.failure, record)
            self.failure['additional_failure_records_omitted'] += state['additional_failure_records_omitted']

    def check_time(self):
        if NOW() >= self.deadline or BOOT_NS(time.CLOCK_BOOTTIME) >= self.boottime_deadline_ns:
            raise BatchStopped('conservative native cooperative cutoff exhausted', 'resource_incomplete')

    def write_record(self, path, value, maximum):
        self.check_time()
        raw = canonical(value)
        if self.current is None or len(raw) > maximum:
            raise BatchStopped('native case record outside its fixed writer boundary')
        if self.case_record_bytes + len(raw) > self.current_row['capture_record_bytes_upper']:
            raise BatchStopped('native case capture reservation exhausted')
        # Charge before the exclusive open. A partial/unknown write never
        # releases this allowance or authorizes a second publication.
        self.case_record_bytes += len(raw)
        self.records_bytes += len(raw)
        with OPEN(path, 'xb') as stream:
            stream.write(raw); stream.flush(); FSYNC(stream.fileno())
        sync_directory(path.parent)

    def write_global(self, name, value):
        self.check_time()
        if name not in GLOBAL_RECORD_LIMITS or name in self.global_record_attempts:
            raise BatchStopped('global evidence publication is not an exclusive fixed slot')
        self.global_record_attempts.add(name)
        raw = canonical(value)
        if len(raw) > GLOBAL_RECORD_LIMITS[name] or self.global_record_bytes + len(raw) > GLOBAL_RESERVE:
            raise BatchStopped('native global diagnostic reserve exhausted')
        self.global_record_bytes += len(raw)
        with OPEN(OUTPUT / name, 'xb') as stream:
            stream.write(raw); stream.flush(); FSYNC(stream.fileno())
        sync_directory(OUTPUT)

    def prefix_bytes(self):
        return self.records_bytes + sum(row['size_bytes'] for row in self.output_files.values())

    def begin(self, index, row):
        self.check_time()
        if self.current is not None or row.get('reservation_certified') is not True:
            raise BatchStopped('next fixed selector reservation is unproved',
                               'execution_incomplete' if self.started_selectors else 'execution_blocked')
        prefix = row['reservation_upper_bytes']
        logs = row['log_reservation_upper_bytes']
        controls = row['capture_record_bytes_upper']
        if any(type(value) is not int or value < 0 for value in (prefix, logs, controls)) or controls > prefix:
            raise BatchStopped('fixed selector reservation schema differs')
        if self.settled_prefix_bytes + prefix + GLOBAL_RESERVE > PREFIX_CAP:
            raise BatchStopped('next fixed selector lacks its frozen output headroom', 'resource_incomplete')
        if self.log is None or self.log.size + logs > LOG_CAP:
            raise BatchStopped('next fixed selector lacks its frozen log headroom', 'resource_incomplete')
        self.current = row['selector']; self.current_row = row
        self.active_prefix_reservation = prefix
        self.active_log_reservation = logs
        self.case_log_started = self.log.size
        self.log.case_started = self.log.size
        self.log.case_limit = logs
        self.case_record_bytes = 0
        self.collect_attempted = False
        self.case_root = OUTPUT / f'c{index:04d}'
        self.case_root.mkdir(mode=0o700)
        sync_directory(OUTPUT)
        self.temp_count = 0; self.roots = []; self.hooks = []; self.observations = []
        self.case_started = NOW()
        self.case_runtime_before = runtime_isolation_snapshot()
        self.write_record(self.case_root / 'start.json',
            {'schema': 'worker38-native-case-start-v1', 'ordinal': index,
             'selector': self.current, 'reservation_upper_bytes': prefix,
             'log_reservation_upper_bytes': logs}, 512)
        self.started_selectors.append(self.current)

    def temporary(self, suffix=None, prefix=None, dir=None, ignore_cleanup_errors=False, *, delete=True):
        if self.current is None:
            raise BatchStopped('temporary fixture outside fixed selector')
        if suffix not in (None, '') or prefix not in self.plan['allowed_temporary_prefixes']:
            raise BatchStopped('unregistered temporary fixture shape')
        if dir is not None and not Path(dir).absolute().is_relative_to(self.case_root):
            raise BatchStopped('temporary fixture escaped the current fixed case')
        self.temp_count += 1
        if self.temp_count > self.current_row['maximum_temporary_roots'] or self.temp_count > 99:
            raise BatchStopped('temporary fixture count exceeds frozen selector')
        path = self.case_root / f't{self.temp_count:02d}'
        path.mkdir(mode=0o700)
        sync_directory(self.case_root)
        self.roots.append({'root': str(path), 'requested_prefix': prefix, 'ordinal': self.temp_count})
        class RetainedTemporaryDirectory:
            name = str(path)
            def __enter__(self):
                return self.name
            def __exit__(self, *args):
                self.cleanup()
            def cleanup(self):
                # No finalizer is created. Owner kill cannot erase a prefix.
                return None
        return RetainedTemporaryDirectory()

    def hook(self, selector, records):
        # Some tests still have mocked low-level I/O at this callback. Only
        # retain these plain records in memory; inspect after all cleanups.
        if selector != self.current or type(records) is not list:
            raise BatchStopped('native capture selector mismatch')
        for record in records:
            if record.get('event') == 'preserve_observed_version':
                self.preserve_version(record)
            else:
                self.hooks.append(record)

    def preserve_version(self, record):
        """Only explicitly registered before-overwrite fixture boundaries."""
        self.check_time()
        path = Path(record['path']).absolute()
        if not path.is_relative_to(self.case_root):
            raise BatchStopped('version witness outside current retained case')
        relative = path.relative_to(self.case_root).as_posix()
        allowed = self.current_row['version_witnesses']
        matches = [item for item in allowed if item['label'] == record['label'] and
                   fnmatch.fnmatchcase(relative, item['source_pattern'])]
        if len(matches) != 1 or record['maximum_bytes'] != matches[0]['maximum_bytes']:
            raise BatchStopped('unregistered observed version boundary')
        rule = matches[0]
        target = self.case_root / ('version-' + rule['slot'] + '.bin')
        info = LSTAT(path)
        if not stat.S_ISREG(info.st_mode) or info.st_size > rule['maximum_bytes']:
            raise BatchStopped('observed version is not a bounded regular file')
        with OPEN(path, 'rb') as stream:
            raw = stream.read(rule['maximum_bytes'] + 1)
        if len(raw) != info.st_size or len(raw) > rule['maximum_bytes']:
            raise BatchStopped('observed version changed during capture')
        # This exclusive slot's full maximum is already inside the case's
        # producer reservation. It is not taken from diagnostic reserves.
        with OPEN(target, 'xb') as stream:
            stream.write(raw); stream.flush(); FSYNC(stream.fileno())
        sync_directory(self.case_root)

    def observe(self, status, label):
        self.check_time()
        encoded = label.encode('utf-8')
        record = {'ordinal': len(self.observations) + 1, 'status': status,
                  'label_sha256': sha(encoded), 'label_bytes': len(encoded)}
        if len(self.observations) >= self.current_row['maximum_observation_records']:
            raise BatchStopped('native observation count exceeds frozen selector')
        self.write_record(self.case_root / f'observation-{len(self.observations)+1:04d}.json', record, 256)
        self.observations.append(record)

    def collect(self):
        self.check_time()
        if self.collect_attempted:
            raise BatchStopped('native case reconciliation is not retried')
        self.collect_attempted = True
        explicit = set()
        observed_inputs = set()
        for record in self.hooks:
            if 'native_writer_state' in record and record['native_writer_state'] != 'confirmed':
                raise BatchStopped('native literal writer completion is unconfirmed')
            root = Path(record['root']).absolute()
            if not root.is_relative_to(self.case_root):
                raise BatchStopped('hook root escaped fixed case')
            setup = record.get('setup_inventory', {})
            paths = record.get('explicit_produced_paths', [])
            subtrees = record.get('explicit_produced_subtrees', [])
            for item in inventory(root):
                name = item['path']; absolute = str(root / name)
                named = name in paths or any(name == stem or name.startswith(stem.rstrip('/') + '/')
                                             for stem in subtrees)
                produced = (named or (record.get('setup_complete', True) is True and (
                    name in record.get('surviving_produced_paths', []) or
                    (record.get('all_new_paths_are_output') is True and name not in setup))))
                if produced:
                    explicit.add(absolute)
                else:
                    observed_inputs.add(absolute)
        rows = inventory(self.case_root, durable=True)
        if len(rows) > self.current_row['maximum_inventory_rows']:
            raise BatchStopped('native retained path count contradicts its fixed reservation', 'integrity_invalid')
        out_rows, input_rows = [], []
        control_names = {'start.json'} | {f'observation-{i+1:04d}.json' for i in range(len(self.observations))}
        output_rules = self.current_row['output_rules']
        input_rules = self.current_row['input_rules']
        for item in rows:
            relative = item['path']; absolute = str(self.case_root / relative)
            compact = [relative, item['type'], item['size_bytes'], item.get('sha256'),
                       item['mode'], item['device'], item['inode'], item['nlink']]
            if len(canonical(compact)) > 192 + 6 * len(relative.encode('ascii')):
                raise BatchStopped('inventory scalar domain differs', 'integrity_invalid')
            if relative in control_names:
                out_rows.append(compact)
                continue
            matched_output = [rule for rule in output_rules if fnmatch.fnmatchcase(relative, rule['pattern'])]
            if absolute in explicit and not matched_output:
                raise BatchStopped('hook names output absent from frozen sink map', 'integrity_invalid')
            if matched_output:
                if (len(matched_output) != 1 or
                        item['type'] != matched_output[0]['expected_type'] or
                        item['size_bytes'] > matched_output[0]['maximum_bytes']):
                    raise BatchStopped('produced file contradicts frozen sink type or size', 'integrity_invalid')
                self.output_files[absolute] = {**item, 'absolute_path': absolute, 'selector': self.current}
                out_rows.append(compact)
                continue
            matched_input = [rule for rule in input_rules if fnmatch.fnmatchcase(relative, rule['pattern'])]
            if len(matched_input) != 1:
                raise BatchStopped('unclassified retained fixture path', 'integrity_invalid')
            rule = matched_input[0]
            if (item['type'] != rule['expected_type'] or
                    item.get('sha256') not in rule['allowed_sha256'] or
                    item['size_bytes'] > rule['maximum_bytes']):
                # An interrupted/divergent setup file is not an immutable
                # input. Its possible prefix was reserved before setup.
                if item['size_bytes'] <= rule['maximum_bytes']:
                    self.output_files[absolute] = {**item, 'absolute_path': absolute,
                                                   'selector': self.current, 'setup_prefix': True}
                raise BatchStopped('retained literal setup is incomplete or differs from fixed pins', 'integrity_invalid')
            self.input_files[absolute] = {**item, 'absolute_path': absolute, 'selector': self.current}
            input_rows.append(compact)
        case_payload = sum(item['size_bytes'] for item in self.output_files.values()
                           if item['selector'] == self.current)
        for group, ceiling in self.current_row.get('output_groups', {}).items():
            members = {rule['pattern'] for rule in output_rules if rule.get('group') == group}
            actual = sum(item['size_bytes'] for item in self.output_files.values()
                         if item['selector'] == self.current and
                         Path(item['absolute_path']).relative_to(self.case_root).as_posix() in members)
            if actual > ceiling:
                raise BatchStopped('produced group contradicts certified sink allowance', 'integrity_invalid')
        if case_payload + self.case_record_bytes > self.active_prefix_reservation:
            raise BatchStopped('observed native bytes contradict certified reservation', 'integrity_invalid')
        record = {'schema': 'worker38-native-case-inventory-v1', 'selector': self.current,
                  'input_rows': input_rows, 'produced_rows': out_rows,
                  'produced_payload_bytes': case_payload, 'input_bytes': sum(row[2] for row in input_rows),
                  'logical_paths_are_charged_individually': True,
                  'excluded_later_native_records': ['inventory.json', 'method.json']}
        self.write_record(self.case_root / 'inventory.json', record,
                          self.current_row['inventory_record_bytes_upper'])
        raw = canonical(record)
        self.pending_inventory_pin = [int(self.case_root.name[1:]), sha(raw), len(raw)]
        self.case_payload_bytes = case_payload

    def end(self, status):
        if runtime_isolation_snapshot() != self.case_runtime_before:
            raise BatchStopped('native process state restoration is unconfirmed', 'integrity_invalid')
        self.collect()
        if self.log.overflow or self.log.write_failure or self.log.size - self.case_log_started > self.active_log_reservation:
            raise BatchStopped('native case log capture is incomplete')
        result = {'selector': self.current, 'status': status,
            'elapsed_seconds': NOW() - self.case_started, 'temporary_roots': self.temp_count,
            'observation_records': len(self.observations),
            'produced_files': sum(x['selector'] == self.current for x in self.output_files.values()),
            'produced_bytes': sum(x['size_bytes'] for x in self.output_files.values() if x['selector'] == self.current)}
        if not (0 <= result['elapsed_seconds'] < 600 and result['observation_records'] <= 9999 and
                result['produced_files'] <= 999999 and result['produced_bytes'] <= PREFIX_CAP):
            raise BatchStopped('native method observation outside frozen scalar domain')
        self.write_record(self.case_root / 'method.json', result, 512)
        if self.case_payload_bytes + self.case_record_bytes > self.active_prefix_reservation:
            raise BatchStopped('settled case exceeds certified reservation', 'integrity_invalid')
        self.method_results.append(result)
        if status != 'passed':
            raise BatchStopped('fixed preparation case failed; reservation remains committed')
        self.settled_prefix_bytes += self.case_payload_bytes + self.case_record_bytes
        self.inventory_index.append(self.pending_inventory_pin)
        self.active_prefix_reservation = 0
        self.active_log_reservation = 0
        self.current = None


def main():
    # GNU timeout owns the hard600-second interval from its actual invocation.
    # The trusted shell samples earlier only for a conservative cooperative
    # cutoff; this is not a claim that the two start instants are identical.
    # Pair monotonic first and boottime second; floor and subtract1ms so this
    # conversion can only shorten the cooperative interval, including suspend.
    raw_deadline = os.environ.get('WORKER38_NATIVE_DEADLINE_CS', '')
    if not raw_deadline.isascii() or not raw_deadline.isdigit() or not 1 <= len(raw_deadline) <= 20:
        raise SystemExit('original shell boottime deadline is required')
    mono_before = time.monotonic_ns()
    remaining_ns = int(raw_deadline) * 10000000 - time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    if not 0 < remaining_ns <= 600000000000:
        raise SystemExit('original native wall interval is unavailable or expired')
    deadline = ((mono_before + remaining_ns) // 1000000 - 1) / 1000.0
    started = deadline - 600.0
    before_as = GETRLIMIT(resource.RLIMIT_AS)
    if before_as not in ((resource.RLIM_INFINITY,) * 2, (MEMORY_CAP,) * 2):
        raise SystemExit('native inherited address-space limit differs')
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP,) * 2)
    if GETRLIMIT(resource.RLIMIT_AS) != (MEMORY_CAP,) * 2:
        raise SystemExit('native512MiB installation unconfirmed')
    expected = os.environ.get('WORKER38_FIXED_MAP_SHA256', '')
    if len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
        raise SystemExit('explicit independently approved fixed map SHA256 required')
    with OPEN(MAP_PATH, 'rb') as stream:
        raw = stream.read(8 * 1024 ** 2 + 1)
    if len(raw) > 8 * 1024 ** 2 or sha(raw) != expected:
        raise SystemExit('fixed preparation map bytes differ')
    plan = json.loads(raw)
    if plan['schema'] != 'worker38-fixed-preparation-map-v1' or len(plan['cases']) != 397:
        raise SystemExit('exact397-method map required')
    if plan['caps'] != {'wall_seconds': 600, 'address_space_bytes': MEMORY_CAP,
                        'case_prefix_bytes': PREFIX_CAP, 'log_bytes': LOG_CAP}:
        raise SystemExit('native cap map differs')
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise SystemExit('exclusive native output destination already exists')
    for name, info in plan['source_files'].items():
        path = ROOT / name
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise SystemExit('source path is not a contained regular file')
        size, digest = hash_file(path)
        if size != info['size_bytes'] or digest != info['sha256']:
            raise SystemExit('source pin mismatch: ' + name)
    for name, info in plan['support_files'].items():
        size, digest = hash_file(ROOT / name)
        if size != info['size_bytes'] or digest != info['sha256']:
            raise SystemExit('preparation support pin mismatch: ' + name)
    native_environment_files = verify_native_environment(plan['native_environment'], plan['environment'], deadline)
    OUTPUT.mkdir(mode=0o700)
    sync_directory(OUTPUT.parent)
    capture = Capture(plan, started, deadline, int(raw_deadline) * 10000000)
    log = LogStream(OUTPUT / 'stdout-stderr.log')
    capture.log = log
    original_stdout, original_stderr = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = log
    modules = {}
    stopped = None
    capture.write_global('start.json', {'schema': 'worker38-native-batch-start-v1',
        'fixed_map_sha256': expected, 'planned_methods': 397,
        'global_prefix_reserve_bytes': GLOBAL_RESERVE,
        'cooperative_deadline_monotonic': capture.deadline,
        'cooperative_deadline_boottime_ns': capture.boottime_deadline_ns,
        'external_hard_timeout_seconds': 600,
        'clock_boundary': 'GNU timeout owns its invocation interval; earlier cooperative cutoff may only shorten work',
        'native_pid': GETPID(), 'status': 'started_no_completion_claim'})
    try:
        def bounded_os_write(fd, raw):
            if fd in (1, 2):
                return log.write(bytes(raw))
            return OS_WRITE(fd, raw)
        os.write = bounded_os_write
        sys.meta_path.insert(0, DenyScientificImports())
        socket.socket.connect = deny_network
        socket.create_connection = deny_network
        socket.getaddrinfo = deny_network
        tempfile.TemporaryDirectory = capture.temporary
        sys.path.insert(0, str(ROOT / 'tests'))
        sys.path.insert(0, str(ROOT / 'scripts'))
        def load_literal_module(name):
            if name not in plan['test_modules']:
                raise BatchStopped('unregistered lazy test-module dependency')
            module_name = Path(name).stem
            if module_name in sys.modules:
                module = sys.modules[module_name]
            else:
                spec = importlib.util.spec_from_file_location(module_name, ROOT / name)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
            modules[name] = module
            if hasattr(module, 'PRODUCTION_OUTPUT_HOOK'):
                module.PRODUCTION_OUTPUT_HOOK = capture.hook
            if hasattr(module, 'NATIVE_BATCH_DEADLINE_MONOTONIC'):
                module.NATIVE_BATCH_DEADLINE_MONOTONIC = capture.deadline
            if hasattr(module, 'NATIVE_CURRENT_SELECTOR'):
                module.NATIVE_CURRENT_SELECTOR = capture.current
            if hasattr(module, 'CURRENT_PRODUCTION_SELECTOR'):
                module.CURRENT_PRODUCTION_SELECTOR = capture.current
            return module
        for index, row in enumerate(plan['cases'], 1):
            capture.begin(index, row)
            observation_root = capture.case_root / 'retained-observations'
            observation_root.mkdir(mode=0o700)
            legacy_directory = observation_root / 'worker37'
            modern_directory = observation_root / 'worker38'
            legacy_directory.mkdir(mode=0o700)
            modern_directory.mkdir(mode=0o700)
            os.environ['WORKER37_LITERAL_EVIDENCE_DIRECTORY'] = str(legacy_directory)
            os.environ['WORKER38_LITERAL_EVIDENCE_DIRECTORY'] = str(modern_directory)
            # All literal module construction is inside this selector's
            # certified reservation, before setUp and after its durable start.
            for name in row['test_module_dependencies']:
                load_literal_module(name)
            for module in modules.values():
                if hasattr(module, 'EVIDENCE_DIRECTORY'):
                    module.EVIDENCE_DIRECTORY = str(legacy_directory)
                if hasattr(module, 'NATIVE_CURRENT_SELECTOR'):
                    module.NATIVE_CURRENT_SELECTOR = capture.current
                if hasattr(module, 'CURRENT_PRODUCTION_SELECTOR'):
                    module.CURRENT_PRODUCTION_SELECTOR = capture.current
            path, qualified = row['selector'].split(':', 1)
            class_name, method_name = qualified.split('.', 1)
            test = getattr(modules[path], class_name)(method_name)
            class Result(unittest.TextTestResult):
                def addError(self, test, err):
                    capture.fail(err[1], 'unittest_setup_body_or_cleanup')
                    super().addError(test, err)
                def addFailure(self, test, err):
                    capture.fail(err[1], 'unittest_assertion')
                    super().addFailure(test, err)
                def addSubTest(self, test, subtest, err):
                    if err is not None:
                        capture.fail(err[1], 'unittest_subtest')
                    capture.observe('success' if err is None else 'failure', str(subtest))
                    super().addSubTest(test, subtest, err)
            result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=Result).run(test)
            status = 'passed' if result.wasSuccessful() and not result.skipped else 'failed'
            if not capture.observations:
                capture.observe('success' if status == 'passed' else 'failure', 'fixed whole-method outcome')
            capture.end(status)
        capture.check_time()
    except BaseException as caught:
        capture.fail(caught, 'case_or_schedule')
        # Never repeat a full scan/hash/fsync pass after a failed scan or an
        # exhausted one-shot deadline. Original files already remain owned.
        if capture.current is not None and not capture.collect_attempted and NOW() < capture.deadline:
            try:
                capture.collect()
            except BaseException as capture_error:
                capture.fail(capture_error, 'failure_reconciliation')
    finally:
        os.write = OS_WRITE
        tempfile.TemporaryDirectory = ORIGINAL_TEMPORARY_DIRECTORY
        sys.stdout, sys.stderr = original_stdout, original_stderr
        try:
            log.durable()
        except BaseException as log_error:
            capture.fail(log_error, 'log_finalization', 'native_log_durability_unconfirmed')
        if log.overflow:
            capture.fail(BatchStopped('native stdout/stderr allowance exhausted', 'resource_incomplete'),
                         'log_finalization')
        if log.write_failure:
            capture.fail(BatchStopped('native log capture is incomplete'), 'log_finalization')
        capture.merge_failure(log.failure)
    stopped = capture.failure
    if stopped is not None:
        stopped['active_reservation_retained'] = capture.active_prefix_reservation
    success = stopped is None and len(capture.method_results) == 397 and all(
        row['status'] == 'passed' for row in capture.method_results)
    counters = {path: {key: getattr(module, key) for key in (
        'STUB_CALLS', 'STUB_PROCESS_STARTS', 'STUB_SUPERVISOR_INVOCATIONS', 'STUB_MOCKED_PROCESS_STARTS')
        if hasattr(module, key)} for path, module in modules.items()}
    receipt = {'schema': 'worker38-fixed-preparation-receipt-v1', 'success': success,
        'success_scope': 'observed_method_outcomes_and_local_publication_only',
        'acceptance_requires_original_outer_command_exit_zero': True,
        'no_full_pass_on_timeout_or_unknown_outer_exit': True,
        'status': 'execution_complete' if success else (stopped or {}).get('status', 'execution_incomplete'),
        'fixed_map_sha256': expected, 'testsRun': len(capture.started_selectors),
        'completed_methods': len(capture.method_results),
        'passed_methods': sum(x['status'] == 'passed' for x in capture.method_results),
        'planned_prefix_completed': len(capture.method_results) == plan['certified_fixed_prefix_methods'] and
            all(x['status'] == 'passed' for x in capture.method_results),
        'unexecuted_methods': 397 - len(capture.started_selectors),
        'unexecuted_suffix_first_ordinal': len(capture.started_selectors) + 1 if len(capture.started_selectors) < 397 else None,
        'failures': sum(x['status'] == 'failed' for x in capture.method_results),
        'errors': int(stopped is not None), 'stopped': stopped, 'elapsed_seconds': NOW() - started,
        'native_executable': sys.executable, 'native_version': sys.version, 'native_argv': sys.orig_argv,
        'native_pid': GETPID(), 'address_space': list(GETRLIMIT(resource.RLIMIT_AS)),
        'log_bytes': log.size, 'log_bytes_complete': log.size_complete,
        'produced_prefix_bytes_before_receipt': capture.prefix_bytes(),
        'settled_prefix_bytes': capture.settled_prefix_bytes,
        'active_prefix_reservation_bytes': capture.active_prefix_reservation,
        'global_reserve_bytes': GLOBAL_RESERVE,
        'active_case_bytes_are_complete': capture.current is None,
        'literal_counters': counters, 'candidate_evaluator_calls': 0, 'reference_evaluator_calls': 0,
        'games': 0, 'measurement_fixture_constructions': 0, 'historical_source_imports': 0,
        'checked_file_sha256': {**{name: info['sha256'] for name, info in plan['source_files'].items()},
                                'evidence-design/worker38-fixed-fixtures.json': expected}}
    # These two exclusive slots are the only final publication. Their cost is
    # inside the original64KiB reserve and original600-second deadline.
    capture.write_global('index.json', {'schema': 'worker38-native-index-v1',
        'fixed_map_sha256': expected, 'settled_case_inventories': capture.inventory_index})
    capture.write_global('receipt.json', receipt)
    if NOW() >= capture.deadline:
        return 1
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
