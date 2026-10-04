"""Non-policy primitives. No historical imports, fixtures, or implicit execution."""
from __future__ import annotations
from contextlib import contextmanager
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import resource
import signal
import stat
import sys
import threading
import time

MIB = 1024 ** 2
REPOSITORY = 'carabinshely/bandido-alcatraz-solve'
HISTORICAL = '7ac2f62c9c5c9dcac9ec9b8770382960f985acc2'
PREREGISTRATION = 'https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5967160389'
PROTOCOL_SHA256 = '8eec0f7e7418fba0e58ab5aee09226cab30555338b4e21f5761509648bfaaa6b'
RUNTIME = {'implementation': 'CPython', 'version': '3.11.16',
           'executable_sha256': 'a15ccdaf07655a8667a3687b13171486c9a265d92273ba3ad820fbb64d2cfecc'}
LOADER_IDENTITY_SCHEMA = 'worker36-loader-identity-v1'
LOADER_PIN_SCHEMA = 'worker36-loader-pin-v1'
LOADER_RELATIVE_PATH = 'Python/3.11.16/x64/lib/libpython3.11.so.1.0'
LOADER_EXECUTABLE_RELATIVE_PATH = 'Python/3.11.16/x64/bin/python3.11'
OPS = ('legal_enumerations', 'previews', 'exit_geometry_checks')
OP_CAPS = dict(zip(OPS, (32768, 32768, 16384)))
CALL_CAPS = {**OP_CAPS, 'roots': 16384, 'wall_seconds': 360, 'cpu_seconds': 360}
RESOURCES = {'per_call': {k: dict(CALL_CAPS) for k in ('control', 'candidate', 'reference')},
             'whole_cell_wall_seconds': 720, 'whole_cell_cpu_seconds': 720,
             'whole_wrapper_operations': {k: 2 * v for k, v in OP_CAPS.items()},
             'total_operations': dict.fromkeys(OPS, 1000000),
             'measurement_wall_seconds': 1800, 'measurement_cpu_seconds': 1800,
             'address_space_bytes': 512 * MIB, 'evidence_bytes': 64 * MIB,
             'receipt_bytes': MIB, 'trace_bytes': 16 * MIB, 'line_bytes': 8 * MIB,
             'archive_bytes': 64 * MIB, 'part_bytes': 30 * MIB,
             'verification_wall_seconds': 600, 'workflow_minutes': 45,
             'free_storage_bytes': 1024 * MIB}
U_FLAGS = {'physical_cost': None, 'physical_operation_caps_enforced': False,
           'choice_events_observed': False, 'production_admissible': False}
SCHEDULE = tuple({'cell': i + 1, 'repetition': rep, 'size': n, 'condition': condition}
                 for i, (rep, n, condition) in enumerate(
                     [(1, n, c) for n in (0, 4, 8, 40, 48) for c in ('P', 'U')] +
                     [(2, n, c) for n in (48, 40, 8, 4, 0) for c in ('U', 'P')]))

class IntegrityError(ValueError): pass
class ResourceExceeded(RuntimeError): pass
class AdmissionBlocked(RuntimeError): pass


def error_record(error, phase, *, observed_drift=False, resource_types=()):
    """Typed failure classification; initial prerequisites are not observed drift."""
    preflight = phase == 'admission' or phase.endswith('preflight')
    if isinstance(error, (ResourceExceeded, MemoryError, RecursionError, *resource_types)):
        # An actual exhausted resource is distinct from an unmet prerequisite,
        # even if it occurs while checking admission/runtime or parsing evidence.
        status, category = 'resource_incomplete', 'resource'
    elif observed_drift:
        status, category = 'integrity_invalid', 'integrity'
    elif preflight:
        status, category = 'execution_blocked', 'preflight'
    elif isinstance(error, IntegrityError):
        status, category = 'integrity_invalid', 'integrity'
    elif isinstance(error, OSError):
        status, category = 'execution_incomplete', 'infrastructure'
    elif isinstance(error, AdmissionBlocked):
        status, category = 'execution_blocked', 'preflight'
    else:
        status, category = 'integrity_invalid', 'unexpected_exception'
    return {'status': status, 'category': category, 'error_type': type(error).__name__,
            'error': str(error)[:4096], 'phase': phase}


def require(ok, message):
    if not ok:
        raise IntegrityError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                       allow_nan=False) + '\n').encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(canonical(value))


def strict_json(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result, 'duplicate JSON key')
            result[k] = v
        return result
    def number(value):
        n = float(value)
        require(math.isfinite(n), 'nonfinite JSON value')
        return n
    def constant(value):
        raise IntegrityError('nonfinite JSON constant')
    return json.loads(raw, object_pairs_hook=pairs, parse_float=number, parse_constant=constant)


def file_info(path):
    p = Path(path)
    require(p.is_file() and not p.is_symlink(), 'regular non-symlink file required: ' + str(p))
    return {'size_bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}


def fsync_directory(path):
    fd = os.open(Path(path), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Budget:
    """Prospective shared raw cap; every writer uses this same on-disk accounting."""
    def __init__(self, root):
        self.root = Path(root).resolve()

    def inventory(self):
        entries = []
        for p in sorted(self.root.rglob('*')):
            require(not p.is_symlink(), 'symlink in raw evidence')
            if p.is_file():
                entries.append({'path': p.relative_to(self.root).as_posix(), **file_info(p)})
            else:
                require(p.is_dir(), 'special file in raw evidence')
        return entries

    def check(self, path, incoming, *, replace=False):
        path = Path(path)
        require(path.resolve().is_relative_to(self.root), 'write outside attempt')
        require(type(incoming) is int and incoming >= 0, 'invalid write size')
        files = self.inventory()
        total = sum(x['size_bytes'] for x in files)
        previous = path.stat().st_size if path.exists() else 0
        growth = incoming - previous if replace else incoming
        terminal = path.parent.resolve() == self.root and (
            path.name == 'receipt.json' or path.name.startswith('failure-receipt-'))
        terminal_bytes = sum(x['size_bytes'] for x in files
                             if '/' not in x['path'] and (x['path'] == 'receipt.json'
                             or x['path'].startswith('failure-receipt-')))
        if terminal:
            if terminal_bytes + growth > MIB or total + growth > 64 * MIB:
                raise ResourceExceeded('terminal receipt reserve exceeded')
        else:
            if incoming > 8 * MIB or total - terminal_bytes + growth > 63 * MIB:
                raise ResourceExceeded('raw evidence or complete line cap exceeded')
        if 'decision-traces' in path.parts and previous + growth > 16 * MIB:
            raise ResourceExceeded('decision trace cap exceeded')

    def check_raw_log(self, path, incoming):
        path = Path(path)
        require(path.resolve().is_relative_to(self.root), 'raw log outside attempt')
        files = self.inventory()
        normal = sum(x['size_bytes'] for x in files if not ('/' not in x['path'] and
                     (x['path'] == 'receipt.json' or x['path'].startswith('failure-receipt-'))))
        if incoming < 0 or normal + incoming > 63 * MIB:
            raise ResourceExceeded('shared raw log/evidence cap exceeded')

    def mkdir(self, path):
        """Persist every newly created directory and its parent entry."""
        path = Path(path)
        require(path.resolve().is_relative_to(self.root), 'mkdir outside attempt')
        missing = []
        cursor = path
        while not cursor.exists():
            missing.append(cursor)
            cursor = cursor.parent
        require(cursor.is_dir() and not cursor.is_symlink(), 'unsafe directory ancestor')
        for directory in reversed(missing):
            directory.mkdir(exist_ok=False)
            fsync_directory(directory)
            fsync_directory(directory.parent)
        require(path.is_dir() and not path.is_symlink(), 'unsafe evidence directory')

    def write(self, path, value, *, replace=False, raw=False):
        path = Path(path)
        data = value if raw else canonical(value)
        self.check(path, len(data), replace=replace)
        self.mkdir(path.parent)
        # Stage complete bytes before any observer can see the final filename.
        # The exclusive temporary file also makes a failed previous write fatal;
        # its unconfirmed prefix is never removed or reused on a retry.
        _atomic_publish(path, data, replace=replace, budget=self)
        return {'path': path.relative_to(self.root).as_posix(), 'size_bytes': len(data), 'sha256': sha(data)}

    def append(self, path, value):
        path = Path(path); data = canonical(value)
        self.check(path, len(data))
        self.mkdir(path.parent)
        with path.open('ab') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        fsync_directory(path.parent)


def _atomic_publish(path, data, *, replace, budget):
    temp = path.with_name(path.name + '.tmp')
    # Both old and staged bytes survive until replacement is durable. Preserve
    # the 1 MiB terminal reserve even while an ordinary replacement is staged.
    files = budget.inventory()
    total = sum(item['size_bytes'] for item in files)
    terminal = path.parent.resolve() == budget.root and (
        path.name == 'receipt.json' or path.name.startswith('failure-receipt-'))
    terminal_total = sum(item['size_bytes'] for item in files if '/' not in item['path'] and
                         (item['path'] == 'receipt.json' or item['path'].startswith('failure-receipt-')))
    # An exclusive hard-link publication briefly exposes both names. A crash
    # can preserve both, and the raw inventory counts paths, not unique inodes.
    transient = len(data) if replace else 2 * len(data)
    if total + transient > 64 * MIB or (not terminal and total - terminal_total + transient > 63 * MIB):
        raise ResourceExceeded('atomic publication transient raw cap')
    if terminal and terminal_total + transient > MIB:
        raise ResourceExceeded('atomic publication terminal reserve exceeded')
    with temp.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    # Persist the staged name too, so a later publication failure leaves a
    # recoverable complete temporary file rather than an unlinked crash gap.
    fsync_directory(path.parent)
    if replace:
        os.replace(temp, path)
        fsync_directory(path.parent)
    else:
        # link is atomic and fails if target already exists; unlike rename it
        # cannot clobber the first marker/record in a competing publication.
        os.link(temp, path)
        fsync_directory(path.parent)
        temp.unlink()
        fsync_directory(path.parent)


def write_failure_receipt(root, value, *, name):
    """Independent bounded terminal writer, including when normal evidence is full."""
    root = Path(root).resolve()
    require(Path(name).name == name and name.startswith('failure-receipt-') and
            name.endswith('.json'), 'reserved failure sidecar name')
    data = canonical(value)
    if len(data) > 64 * 1024:
        raise ResourceExceeded('bounded failure sidecar exceeded')
    class TerminalBudget(Budget):
        def inventory(self):
            # Recovery requires sizes for cap enforcement, not readable content.
            # A denied data read must not prevent an independent sidecar. Failed
            # directory/stat access still blocks rather than guessing raw size.
            entries = []
            def visit(directory):
                with os.scandir(directory) as listing:
                    for entry in listing:
                        require(not entry.is_symlink(), 'symlink in raw evidence')
                        path = Path(entry.path)
                        if entry.is_dir(follow_symlinks=False):
                            visit(path)
                        else:
                            require(entry.is_file(follow_symlinks=False), 'special file in raw evidence')
                            entries.append({'path': path.relative_to(self.root).as_posix(),
                                            'size_bytes': entry.stat(follow_symlinks=False).st_size})
            visit(self.root)
            return entries
    budget = TerminalBudget(root)
    path = root / name
    budget.check(path, len(data))
    budget.mkdir(root)
    _atomic_publish(path, data, replace=False, budget=budget)
    return {'path': name, 'size_bytes': len(data), 'sha256': sha(data)}


def update_receipt(root, **updates):
    root = Path(root); budget = Budget(root); path = root / 'receipt.json'
    # Reading unavailable bytes cannot establish corruption. Resource failures
    # from either the read or parser must propagate with their actual type.
    raw = path.read_bytes()
    try:
        value = strict_json(raw)
        require(type(value) is dict, 'receipt must be object')
    except (IntegrityError, json.JSONDecodeError, UnicodeDecodeError) as parse_error:
        primary = IntegrityError('main receipt malformed; original bytes preserved')
        primary.worker36_failure = error_record(primary, 'receipt_parse', observed_drift=True)
        primary.worker36_secondary_errors = []
        try:
            sidecar = 'failure-receipt-' + str(time.monotonic_ns()) + '.json'
            write_failure_receipt(root, {
                'schema': 'worker36-receipt-corrupt-v1', 'status': 'integrity_invalid',
                'custody': 'pending', 'classification': None, 'original_bytes_preserved': True,
                'error_type': type(parse_error).__name__, 'error': str(parse_error)[:4096],
                'failure': primary.worker36_failure, 'requested_update': updates}, name=sidecar)
        except BaseException as preservation_error:
            # Proven malformed committed bytes stay the primary finding even
            # when independent preservation subsequently exhausts a resource.
            primary.worker36_secondary_errors.append(
                error_record(preservation_error, 'receipt_corruption_sidecar_persistence'))
        raise primary from parse_error
    if value.get('status') == 'integrity_invalid' and 'status' in updates:
        updates['status'] = 'integrity_invalid'
    value.update(updates)
    budget.write(path, value, replace=True)
    return value


def _loader_path(value):
    require(type(value) is str and value.startswith('/') and
            not any(character in value for character in (':', '\\', '\x00', '\n', '\r')) and
            all(part not in ('', '.', '..') for part in value.split('/')[1:]),
            'absolute canonical loader path required')
    return Path(value)


def _loader_device(value):
    require(type(value) is dict and set(value) == {'major', 'minor'} and
            all(type(value[key]) is int and value[key] >= 0 for key in value),
            'invalid loader device identity')


def loader_pin(value):
    """Validate recorded identity or portable pin; never infer a library digest."""
    require(type(value) is dict, 'explicit loader identity or pin required')
    pin_keys = {'schema', 'executable_sha256', 'library_relative_path',
                'library_sha256', 'library_size_bytes'}
    if value.get('schema') == LOADER_IDENTITY_SCHEMA:
        require(set(value) == pin_keys | {'tool_cache', 'executable_path', 'library_path',
                'library_directory', 'library_device', 'library_inode', 'mapped_library',
                'loader_environment'}, 'unexpected loader identity fields')
        cache = _loader_path(value['tool_cache'])
        executable = _loader_path(value['executable_path'])
        library = _loader_path(value['library_path'])
        directory = _loader_path(value['library_directory'])
        require(executable == cache / LOADER_EXECUTABLE_RELATIVE_PATH and
                library == cache / LOADER_RELATIVE_PATH and directory == library.parent,
                'loader paths do not match the pinned toolcache layout')
        _loader_device(value['library_device'])
        require(type(value['library_inode']) is int and value['library_inode'] > 0,
                'invalid loader inode')
        mapped = value['mapped_library']
        require(type(mapped) is dict and set(mapped) == {'path', 'device', 'inode'},
                'invalid mapped loader identity fields')
        _loader_device(mapped['device'])
        require(type(mapped['inode']) is int and mapped['inode'] > 0 and
                mapped['path'] == str(library) and mapped['device'] == value['library_device'] and
                mapped['inode'] == value['library_inode'], 'mapped loader identity mismatch')
        require(type(value['loader_environment']) is dict and
                value['loader_environment'] == {'LD_LIBRARY_PATH': str(directory)},
                'unexpected recorded loader environment')
    else:
        require(value.get('schema') == LOADER_PIN_SCHEMA and set(value) == pin_keys,
                'unexpected loader pin schema or fields')
    require(value['executable_sha256'] == RUNTIME['executable_sha256'] and
            value['library_relative_path'] == LOADER_RELATIVE_PATH,
            'loader pin differs from the pinned executable or library layout')
    require(type(value['library_sha256']) is str and
            re.fullmatch('[0-9a-f]{64}', value['library_sha256']) is not None and
            type(value['library_size_bytes']) is int and value['library_size_bytes'] > 0,
            'explicit library SHA256 and positive integer byte size required')
    return {'schema': LOADER_PIN_SCHEMA, **{key: value[key] for key in pin_keys - {'schema'}}}


def _loader_stat_signature(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns, value.st_nlink)


def _stable_loader_file(path):
    """Hash one non-symlink regular file through its held, rechecked descriptor."""
    path = Path(path)
    require(path.resolve(strict=True) == path, 'noncanonical loader file path')
    initial = path.lstat()
    require(stat.S_ISREG(initial.st_mode) and initial.st_size > 0,
            'nonempty regular non-symlink loader file required')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(descriptor)
        require(_loader_stat_signature(before) == _loader_stat_signature(initial),
                'loader file changed before hashing')
        hasher = hashlib.sha256()
        count = 0
        while True:
            block = os.read(descriptor, MIB)
            if not block:
                break
            count += len(block)
            require(count <= before.st_size, 'loader file grew during hashing')
            hasher.update(block)
        after = os.fstat(descriptor)
        current = path.lstat()
        require(count == before.st_size and _loader_stat_signature(before) ==
                _loader_stat_signature(after) == _loader_stat_signature(current) and
                path.resolve(strict=True) == path, 'loader file changed while hashing')
        return {'sha256': hasher.hexdigest(), 'size_bytes': count,
                'device': {'major': os.major(before.st_dev), 'minor': os.minor(before.st_dev)},
                'inode': before.st_ino, '_stat': _loader_stat_signature(before)}
    finally:
        os.close(descriptor)


def _loader_maps():
    return Path('/proc/self/maps').read_text(encoding='utf-8')


def _mapped_loader(raw, *, path, device, inode):
    """All libpython mappings must name exactly the held library inode/path."""
    require(type(raw) is str, 'proc maps text required')
    found = False
    segments = []
    for line in raw.splitlines():
        fields = line.split(maxsplit=5)
        require(len(fields) in (5, 6) and
                re.fullmatch('[0-9a-f]+-[0-9a-f]+', fields[0]) is not None and
                re.fullmatch('[r-][w-][x-][ps]', fields[1]) is not None and
                re.fullmatch('[0-9a-f]+', fields[2]) is not None and
                re.fullmatch('[0-9a-f]+:[0-9a-f]+', fields[3]) is not None and
                re.fullmatch('[0-9]+', fields[4]) is not None, 'malformed proc maps')
        mapped_device = dict(zip(('major', 'minor'), (int(x, 16) for x in fields[3].split(':'))))
        mapped_inode = int(fields[4])
        mapped_path = fields[5] if len(fields) == 6 else ''
        same_inode = mapped_device == device and mapped_inode == inode
        if 'libpython' in mapped_path or same_inode:
            require(mapped_path == path and same_inode, 'unexpected, aliased or deleted libpython mapping')
            found = True
            segments.append(tuple(fields))
    require(found, 'mapped libpython identity unavailable')
    return {'path': path, 'device': dict(device), 'inode': inode}, tuple(segments)


def loader_identity():
    """Observe the exact trusted-toolcache library actually mapped in this process."""
    cache = _loader_path(os.environ.get('RUNNER_TOOL_CACHE'))
    require(cache.is_dir() and not cache.is_symlink() and cache.resolve(strict=True) == cache,
            'canonical trusted RUNNER_TOOL_CACHE required')
    executable = Path(sys.executable).resolve(strict=True)
    require(executable == cache / LOADER_EXECUTABLE_RELATIVE_PATH,
            'interpreter is outside its pinned toolcache location')
    executable_info = _stable_loader_file(executable)
    require(executable_info['sha256'] == RUNTIME['executable_sha256'], 'wrong pinned executable bytes')
    library = cache / LOADER_RELATIVE_PATH
    directory = library.parent
    require(directory.is_dir() and not directory.is_symlink() and
            directory.resolve(strict=True) == directory, 'canonical loader directory required')
    environment = {key: value for key, value in os.environ.items() if key.startswith('LD')}
    require(environment == {'LD_LIBRARY_PATH': str(directory)}, 'unexpected dynamic-loader environment')
    info = _stable_loader_file(library)
    mapped, segments = _mapped_loader(_loader_maps(), path=str(library),
                                     device=info['device'], inode=info['inode'])
    # Rehash through a fresh descriptor after reading mappings, then check the
    # mapping segments again. Replacement, mutation, aliases and unmapping fail.
    require(_stable_loader_file(library) == info, 'mapped library bytes changed during verification')
    repeated, repeated_segments = _mapped_loader(_loader_maps(), path=str(library),
                                                device=info['device'], inode=info['inode'])
    require(repeated == mapped and repeated_segments == segments, 'libpython mappings changed during verification')
    require(_stable_loader_file(executable) == executable_info, 'executable changed during loader verification')
    identity = {'schema': LOADER_IDENTITY_SCHEMA, 'tool_cache': str(cache),
                'executable_path': str(executable), 'executable_sha256': executable_info['sha256'],
                'library_relative_path': LOADER_RELATIVE_PATH, 'library_path': str(library),
                'library_directory': str(directory), 'library_sha256': info['sha256'],
                'library_size_bytes': info['size_bytes'], 'library_device': info['device'],
                'library_inode': info['inode'], 'mapped_library': mapped,
                'loader_environment': environment}
    loader_pin(identity)
    return identity


def clean_environment(environ=None, *, loader=None):
    env = dict(os.environ if environ is None else environ)
    for k in tuple(env):
        if k.startswith(('PYTHON', 'LD')):
            env.pop(k)
    if loader is not None:
        pin = loader_pin(loader)
        actual = loader_identity()
        require(loader_pin(actual) == pin, 'explicit loader pin differs from verified local loader')
        if loader['schema'] == LOADER_IDENTITY_SCHEMA:
            require(loader == actual, 'explicit loader identity differs from verified local loader')
        env.update(actual['loader_environment'])
    env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1')
    return env


def idle_hooks():
    require(sys.getprofile() is None and sys.gettrace() is None, 'occupied profile/trace hook')
    require(threading.active_count() == 1, 'single-threaded process required')


def runtime_check(*, child=False):
    idle_hooks()
    actual = {'implementation': platform.python_implementation(), 'version': platform.python_version(),
              'executable_sha256': file_info(Path(sys.executable).resolve())['sha256']}
    require(actual == RUNTIME, 'wrong pinned interpreter')
    require(sys.platform == 'linux', 'Linux required')
    require(os.environ.get('GITHUB_ACTIONS') == 'true' and
            os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and
            os.environ.get('RUNNER_NAME') == 'bandido-alcatraz-ci', 'wrong runner or repository')
    require(sys.flags.dont_write_bytecode == 1 and sys.flags.no_user_site == 1 and
            sys.flags.ignore_environment == 0 and sys.flags.isolated == 0 and
            sys.flags.optimize == 0 and sys.flags.no_site == 0,
            'exact -B -s interpreter flags required')
    require({k: v for k, v in os.environ.items() if k.startswith('PYTHON')} ==
            {'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1'}, 'unexpected Python environment')
    require(gc.isenabled() and gc.get_threshold() == (700, 10, 10), 'default GC policy required')
    require(not signal.getitimer(signal.ITIMER_REAL)[0] and not signal.getitimer(signal.ITIMER_PROF)[0],
            'occupied wall/CPU timers')
    if child:
        require(resource.getrlimit(resource.RLIMIT_AS) == (512 * MIB, 512 * MIB), 'exact child address-space limit')
    loader = loader_identity()
    return {**actual, 'executable': str(Path(sys.executable).resolve()), 'flags': list(sys.orig_argv),
            'loader': loader,
            'effective_flags': {name: getattr(sys.flags, name) for name in (
                'dont_write_bytecode', 'no_user_site', 'ignore_environment', 'isolated', 'optimize', 'no_site')},
            'python_environment': {k: v for k, v in os.environ.items() if k.startswith('PYTHON')},
            'gc_enabled': gc.isenabled(), 'gc_threshold': list(gc.get_threshold()),
            'address_space': list(resource.getrlimit(resource.RLIMIT_AS))}


@contextmanager
def suppress_profile():
    """U-only shim. No callbacks, synthetic events, or substitute counters."""
    idle_hooks()
    original_setter, original_getter = sys.setprofile, sys.getprofile
    def ignored_profile_setter(callback):
        return None
    try:
        sys.setprofile = ignored_profile_setter
        yield original_getter
    finally:
        sys.setprofile = original_setter
        require(sys.setprofile is original_setter and sys.getprofile is original_getter and
                original_getter() is None and sys.gettrace() is None, 'profile shim restoration failed')


class TimingDelegate:
    """Identical P/U method interval, unchanged returned tuple, durable sidecar."""
    def __init__(self, method, *, scope, condition, budget, folder, cell, observation_wire,
                 move_wire, captures, guard_path, verify_sources):
        self.method, self.scope, self.condition = method, scope, condition
        self.budget, self.folder, self.cell = budget, Path(folder), cell
        self.observation_wire, self.move_wire = observation_wire, move_wire
        self.captures, self.guard_path, self.verify_sources = captures, Path(guard_path), verify_sources

    def evaluate(self, observation, rng, *, limits):
        require(self.scope not in self.captures, 'evaluator cannot start twice')
        if self.scope == 'reference':
            require(self.captures.get('candidate', {}).get('durable_capture_confirmed') is True,
                    'reference prohibited before candidate durable capture')
        source_modules = self.verify_sources()
        initial = rng.getstate(); public = self.observation_wire(observation)
        identity = {**self.cell, 'scope': self.scope, 'observation_sha256': digest(public),
                    'initial_rng_sha256': digest(initial), 'source_modules': source_modules}
        record = {'start_marker_durable': False, 'invocation_attempted': False,
                  'method_entered': False, 'returned': False, 'durable_capture_confirmed': False}
        self.captures[self.scope] = record
        self.budget.write(self.guard_path, {'active': True, 'scope': self.scope,
                          'wall_started': time.monotonic(), 'cpu_started': time.process_time()},
                          replace=self.guard_path.exists())
        self.budget.write(self.folder / (self.scope + '-start.json'), identity)
        record['start_marker_durable'] = True
        sentinel = object()
        returned = sentinel
        try:
            # Pre-call intent is deliberately outside the matched clock window;
            # a kill after this point does not establish actual method entry.
            record['invocation_attempted'] = True
            record['method_entered'] = None
            # Do not insert serialization, I/O, validation, or other work here.
            wall_before = time.monotonic()
            cpu_before = time.process_time()
            returned = self.method(observation, rng, limits=limits)
            wall_after = time.monotonic()
            cpu_after = time.process_time()
            record.update(method_entered=True, returned=True)
            elapsed = {'wall_seconds': wall_after - wall_before, 'cpu_seconds': cpu_after - cpu_before}
            payload = {**identity, 'chosen': self.move_wire(returned[0]), 'scientific': returned[1],
                       'rng_initial': initial, 'rng_final': rng.getstate(),
                       'initial_rng_sha256': digest(initial), 'final_rng_sha256': digest(rng.getstate()),
                       'scientific_sha256': digest(returned[1]), 'timing': elapsed,
                       'physical_cost': returned[2] if self.condition == 'P' else None,
                       'physical_operation_caps_enforced': self.condition == 'P',
                       'choice_events_observed': self.condition == 'P', 'production_admissible': False}
            info = self.budget.write(self.folder / (self.scope + '-return.json'), payload)
            self.budget.write(self.folder / (self.scope + '-capture-confirmed.json'), info)
            record.update(durable_capture_confirmed=True, evidence=info)
            # U root checks intentionally occur in the caller after this capture.
            return returned
        except BaseException as error:
            if returned is not sentinel:
                # A clock/capture failure after the assignment cannot erase an
                # observed return, even though no successful timing is available.
                record.update(method_entered=True, returned=True)
            else:
                method = getattr(self.method, '__func__', self.method)
                code = getattr(method, '__code__', None)
                traceback = error.__traceback__
                while traceback is not None:
                    if code is not None and traceback.tb_frame.f_code is code:
                        record['method_entered'] = True
                        break
                    traceback = traceback.tb_next
            record['error_type'] = type(error).__name__
            record['error'] = str(error)[:4096]
            raise
        # The caller clears the protection marker after its immediate durable
        # handling/postchecks. P keeps candidate active until reference starts,
        # then keeps reference active through the unchanged AuditPolicy return.
