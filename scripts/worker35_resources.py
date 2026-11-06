"""Worker35-only resource/evidence gates. No deck loading or policy execution.

All production ceilings come from a reviewed, hashed freeze. This module has no
permissive production configuration. A failed write leaves the durable prefix;
receipts use a separately reserved bound so resource failure remains recordable.
"""
from __future__ import annotations
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time
import zipfile

OPS = ('legal_enumerations', 'previews', 'exit_geometry_checks')
SCOPES = ('control', 'candidate', 'reference')
MIB = 1024 ** 2


class ResourceExceeded(RuntimeError):
    pass


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key: ' + key)
            result[key] = value
        return result
    def number(raw):
        value = float(raw)
        require(math.isfinite(value), 'nonfinite JSON number')
        return value
    def constant(raw):
        raise ValueError('nonfinite JSON constant: ' + raw)
    return json.loads(data, object_pairs_hook=pairs, parse_float=number, parse_constant=constant)


def exact_keys(value, keys, label):
    require(type(value) is dict and set(value) == set(keys), label + ': exact keys required')


def positive(value, label):
    require(type(value) is int and value > 0, label + ': positive integer required')


def hexadecimal(value, size, label):
    require(type(value) is str and len(value) == size and set(value) <= set('0123456789abcdef')
            and value != '0' * size, label + ': hash required')


def validate_freeze(value):
    exact_keys(value, ('schema', 'preregistration_url', 'baseline_commit', 'baseline_source_blobs',
        'execution_source_sha256', 'runtime', 'resources', 'reviews', 'synthetic_preflight_sha256'), 'freeze')
    require(value['schema'] == 'worker35-execution-freeze-v1', 'freeze schema')
    hexadecimal(value['baseline_commit'], 40, 'baseline commit')
    for field, length in (('baseline_source_blobs', 40), ('execution_source_sha256', 64)):
        pins = value[field]
        require(type(pins) is dict and pins, field + ': missing pins')
        for name, pin in pins.items():
            require(type(name) is str and name and not name.startswith('/') and
                    all(p not in ('', '.', '..') for p in name.split('/')), 'unsafe source path')
            hexadecimal(pin, length, name)
    exact_keys(value['runtime'], ('implementation', 'version', 'executable_sha256'), 'runtime')
    require(value['runtime']['implementation'] == 'CPython' and value['runtime']['version'] == '3.11.16',
            'exact CPython 3.11.16 runtime required')
    hexadecimal(value['runtime']['executable_sha256'], 64, 'interpreter digest')
    exact_keys(value['reviews'], ('candidate', 'reference', 'harness', 'independent_a', 'independent_b'), 'reviews')
    require(all(v == 'required-clean-exact-head-before-go' for v in value['reviews'].values()),
            'freeze must declare required review roles; actual approvals belong in external exact-head go')
    hexadecimal(value['synthetic_preflight_sha256'], 64, 'synthetic preflight receipt')
    limits = value['resources']
    exact_keys(limits, ('per_call', 'total_operations', 'cohort_wall_seconds', 'verification_wall_seconds',
        'address_space_bytes', 'evidence_bytes', 'trace_bytes', 'line_bytes', 'receipt_bytes',
        'shard_bytes', 'archive_bytes'), 'resource ceilings')
    exact_keys(limits['per_call'], SCOPES, 'per-call scopes')
    for scope, caps in limits['per_call'].items():
        exact_keys(caps, (*OPS, 'roots', 'wall_seconds', 'cpu_seconds'), scope + ' ceilings')
        for key, n in caps.items():
            positive(n, scope + '.' + key)
    exact_keys(limits['total_operations'], OPS, 'whole-run operations')
    for key, n in limits['total_operations'].items():
        positive(n, 'total.' + key)
    for key in set(limits) - {'per_call', 'total_operations'}:
        positive(limits[key], key)
    require(limits['shard_bytes'] <= 30 * MIB, 'shard payload must leave ZIP transport overhead below32MiB')
    require(limits['archive_bytes'] <= 256 * limits['shard_bytes'], 'archive cap exceeds256transport parts')
    require(limits['line_bytes'] <= limits['trace_bytes'] <= limits['evidence_bytes'], 'inconsistent evidence limits')
    require(limits['receipt_bytes'] <= limits['evidence_bytes'], 'receipt reserve exceeds evidence budget')
    return value


def read_freeze(path, expected_sha256=None):
    raw = Path(path).read_bytes()
    require(len(raw) <= MIB, 'freeze exceeds1MiB administration limit')
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None:
        require(digest == expected_sha256, 'freeze byte hash mismatch')
    return validate_freeze(strict_json(raw)), digest


@contextmanager
def deadline(seconds, label):
    """Linux main-thread wall limit, nested without extending an outer deadline."""
    require(sys.platform == 'linux', 'Linux deadlines required')
    old_handler = signal.getsignal(signal.SIGALRM)
    old_timer = signal.getitimer(signal.ITIMER_REAL)
    start = time.monotonic()
    seconds = min(seconds, old_timer[0]) if old_timer[0] else seconds
    def expired(signum, frame):
        raise ResourceExceeded(label + ': wall deadline exceeded')
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
        if time.monotonic() - start > seconds:
            raise ResourceExceeded(label + ': wall deadline exceeded')
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
        if old_timer[0]:
            remaining = old_timer[0] - (time.monotonic() - start)
            # Do not turn an elapsed outer timer off during unwinding.
            signal.setitimer(signal.ITIMER_REAL, max(remaining, 0.000001), old_timer[1])


@contextmanager
def cpu_deadline(seconds, label):
    """ITIMER_PROF bounds process user+system CPU during one decision."""
    old_handler = signal.getsignal(signal.SIGPROF)
    old_timer = signal.getitimer(signal.ITIMER_PROF)
    start = time.process_time()
    seconds = min(seconds, old_timer[0]) if old_timer[0] else seconds
    def expired(signum, frame):
        raise ResourceExceeded(label + ': CPU deadline exceeded')
    signal.signal(signal.SIGPROF, expired)
    signal.setitimer(signal.ITIMER_PROF, seconds)
    try:
        yield
        if time.process_time() - start > seconds:
            raise ResourceExceeded(label + ': CPU deadline exceeded')
    finally:
        signal.setitimer(signal.ITIMER_PROF, 0)
        signal.signal(signal.SIGPROF, old_handler)
        if old_timer[0]:
            signal.setitimer(signal.ITIMER_PROF, max(old_timer[0] - (time.process_time() - start), .000001), old_timer[1])


def enforce_memory(limit):
    old = resource.getrlimit(resource.RLIMIT_AS)
    require(old[1] == resource.RLIM_INFINITY or old[1] >= limit,
            'inherited address-space limit is lower than frozen ceiling')
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    require(resource.getrlimit(resource.RLIMIT_AS) == (limit, limit), 'memory ceiling not effective')
    return {'mechanism': 'RLIMIT_AS', 'soft': limit, 'hard': limit}


class Meter:
    """Passive function-entry meter; existing Python profilers are preserved.

    Candidate/reference own scoped hooks forward this hook. No canonical module
    is patched. Control scored roots are observed from its actual choose frame.
    """
    def __init__(self, *, total_caps=None, call_caps=None, rng=None, capture_control=False):
        self.total_caps, self.call_caps = total_caps, call_caps
        self.rng, self.capture_control = rng, capture_control
        self.counts = {k: 0 for k in OPS}
        self.choice_tiers = []
        self.control_roots = None
        self.old = None

    def __enter__(self):
        from bandido_alcatraz import moves, strategy
        from random import Random
        self.codes = {moves.legal_moves.__code__: 'legal_enumerations',
            moves.placement_moves.__code__: 'legal_enumerations',
            strategy.preview_move_without_draw.__code__: 'previews',
            strategy.standalone_exit_legal_move_count.__code__: 'exit_geometry_checks'}
        self.control_code = strategy.WeightedGreedyPolicy.choose.__code__
        self.choice_code = Random.choice.__code__
        self.old = sys.getprofile()
        require(self.old is None or callable(self.old), 'native profile hook cannot safely be forwarded')
        try:
            sys.setprofile(self.profile)
            return self
        except BaseException:
            sys.setprofile(self.old)
            raise

    def profile(self, frame, event, arg):
        if self.old is not None:
            self.old(frame, event, arg)
        if event == 'call':
            key = self.codes.get(frame.f_code)
            if key:
                self.counts[key] += 1
                for caps in (self.total_caps, self.call_caps):
                    if caps is not None and self.counts[key] > caps[key]:
                        raise ResourceExceeded(key + ': physical operation ceiling exceeded')
            if frame.f_code is self.choice_code and frame.f_locals.get('self') is self.rng:
                from bandido_alcatraz.worker32.evidence import move
                self.choice_tiers.append([move(m) for m in frame.f_locals['seq']])
        elif event == 'return' and self.capture_control and frame.f_code is self.control_code:
            from bandido_alcatraz.worker32.evidence import move
            self.control_roots = [{'move': move(m), 'score': score} for score, m in frame.f_locals.get('scored', [])]

    def __exit__(self, kind, value, tb):
        sys.setprofile(self.old)


def jsonl_limit(path, limits):
    """Only decision traces have a per-game cap; other journals share raw cap."""
    return limits['trace_bytes'] if 'decision-traces' in Path(path).parts else limits['evidence_bytes']


class EvidenceBudget:
    """Exact prospective raw-byte ceilings; no truncation and no silent rollover."""
    def __init__(self, root, limits):
        self.root, self.limits = Path(root), limits
        self.bytes = sum(p.stat().st_size for p in self.root.rglob('*') if p.is_file()
                         and p.name != 'receipt.json' and not p.name.endswith('.tmp'))
        self.reserved = limits['receipt_bytes']

    def check(self, path, incoming, *, replace=False):
        path = Path(path)
        if path.name == 'receipt.json' or path.name.startswith('recovery-receipt-'):
            if incoming > self.limits['receipt_bytes']:
                raise ResourceExceeded('receipt reserve exceeded')
            return
        previous = path.stat().st_size if path.exists() else 0
        after = incoming if replace else previous + incoming
        if incoming > self.limits['line_bytes']:
            raise ResourceExceeded('one complete evidence event exceeds frozen line limit')
        if 'decision-traces' in path.parts and after > self.limits['trace_bytes']:
            raise ResourceExceeded('game trace byte limit exceeded')
        growth = incoming - previous if replace else incoming
        if self.bytes + growth + self.reserved > self.limits['evidence_bytes']:
            raise ResourceExceeded('whole evidence byte limit exceeded')
        self.bytes += growth


def file_hash(path):
    h, size = hashlib.sha256(), 0
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(MIB), b''):
            h.update(chunk)
            size += len(chunk)
    return {'sha256': h.hexdigest(), 'size_bytes': size}


class ShardWriter:
    """Unseekable ZIP sink, bounded as bytes are emitted, with durable prefixes."""
    def __init__(self, destination, limits):
        self.destination, self.limits = destination, limits
        self.size, self.part_size, self.number = 0, 0, 0
        self.stream = None
        self.digest = hashlib.sha256()

    def tell(self):
        return self.size

    def write(self, value):
        if self.size + len(value) > self.limits['archive_bytes']:
            raise ResourceExceeded('compressed archive byte ceiling exceeded')
        view = memoryview(value)
        length = len(view)
        while view:
            if self.stream is None or self.part_size == self.limits['shard_bytes']:
                self.flush_close()
                if self.number >= 256:
                    raise ResourceExceeded('transport shard population exceeds256')
                self.number += 1
                self.stream = (self.destination / f'evidence.part-{self.number:05d}').open('xb')
                self.part_size = 0
            count = min(len(view), self.limits['shard_bytes'] - self.part_size)
            self.stream.write(view[:count])
            self.digest.update(view[:count])
            self.size += count
            self.part_size += count
            view = view[count:]
        return length

    def flush(self):
        if self.stream is not None:
            self.stream.flush()
            os.fsync(self.stream.fileno())

    def flush_close(self):
        if self.stream is not None:
            self.flush()
            self.stream.close()
            self.stream = None


def package_evidence(root, destination, limits):
    """Sorted fixed-metadata ZIP_DEFLATED(level6), split without truncation.

    Every part is a separate upload artifact. No temporary giant archive or
    aggregate upload can reintroduce the32MiB download bottleneck. A failed
    package retains every already written part and all original raw evidence.
    """
    root, destination = Path(root), Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    files = {}
    expanded_bytes = 0
    sink = ShardWriter(destination, limits)
    try:
        with zipfile.ZipFile(sink, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as output:
            for path in sorted(root.rglob('*')):
                require(not path.is_symlink(), 'symlinked evidence forbidden')
                if not path.is_file():
                    continue
                relative = path.relative_to(root).as_posix()
                files[relative] = file_hash(path)
                expanded_bytes += files[relative]['size_bytes']
                if expanded_bytes > limits['evidence_bytes']:
                    raise ResourceExceeded('raw evidence exceeds frozen expanded byte ceiling')
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                info._compresslevel = 6
                with path.open('rb') as source, output.open(info, 'w', force_zip64=True) as target:
                    for chunk in iter(lambda: source.read(MIB), b''):
                        target.write(chunk)
        sink.flush_close()
        parts = [{'name': path.name, **file_hash(path)} for path in sorted(destination.glob('evidence.part-*'))]
        manifest = {'schema': 'worker35-artifact-manifest-v1', 'files': files,
                    'archive': {'sha256': sink.digest.hexdigest(), 'size_bytes': sink.size}, 'parts': parts,
                    'format': 'concatenated-zip-deflate6', 'shard_bytes': limits['shard_bytes']}
        with (destination / 'artifact-manifest.json').open('xb') as stream:
            stream.write(canonical(manifest)); stream.flush(); os.fsync(stream.fileno())
        return manifest
    finally:
        sink.flush_close()
