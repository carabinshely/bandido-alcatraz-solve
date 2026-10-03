"""Bounded byte preservation of three original raw tails; no project imports."""
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
import urllib.request
REPO = 'carabinshely/bandido-alcatraz-solve'
HEAD = '7ac2f62c9c5c9dcac9ec9b8770382960f985acc2'
RUN = 36990202101
JOB = 110784375570
RUNNER = 'bandido-alcatraz-ci'
BRANCH = 'refs/heads/research/worker35-tail-recovery-36990202101'
RECEIPT_SHA = '027b6b35d75983ecf1760395418ff00d2df2a7fab63afee617bc73e4d8e3b3af'
FREEZE_SHA = 'f630a40f3f4fd1bf3135045ba5428e26e1f597937a49c67791f094830c2b025d'
MIB = 1024 * 1024
MANIFEST_LIMIT = 8 * MIB

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
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()

def parse(raw):

    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'duplicate JSON key')
            value[key] = item
        return value

    def finite(value):
        result = float(value)
        require(math.isfinite(result), 'nonfinite JSON number')
        return result
    value = json.loads(raw, object_pairs_hook=pairs, parse_float=finite, parse_constant=finite)
    require(type(value) is dict, 'JSON object required')
    return value

def canonical_path(path):
    text = str(path)
    require(text.startswith('/') and os.path.normpath(text) == text, 'noncanonical absolute path')
    require(not any((c in text for c in '\n\r\x00*?[]')), 'unsafe path characters')
    return Path(text)

def open_dir(path, fresh=False):
    path = canonical_path(path)
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for index, part in enumerate(path.parts[1:]):
            if fresh:
                try:
                    os.mkdir(part, mode=448, dir_fd=fd)
                except FileExistsError:
                    require(index != len(path.parts) - 2, 'snapshot already exists')
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = new
        return fd
    except BaseException:
        os.close(fd)
        raise

def stamp(s):
    return [s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_gid, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns]

def verify_dir(path, fd):
    check = open_dir(path)
    try:
        require(stamp(os.fstat(check)) == stamp(os.fstat(fd)), 'directory path identity changed')
    finally:
        os.close(check)

def read_file(fd, name, limit):
    require(type(name) is str and re.fullmatch('[A-Za-z0-9_.-]+', name) and (name not in ('.', '..')), 'unsafe basename')
    handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    try:
        before = os.fstat(handle)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'single-link regular file required')
        require(before.st_uid == os.geteuid() and 0 <= before.st_size <= limit, 'file owner/size mismatch')
        with os.fdopen(os.dup(handle), 'rb') as stream:
            raw = stream.read(limit + 1)
        after = os.fstat(handle)
        require(len(raw) == before.st_size and len(raw) <= limit, 'file size changed')
        require(stamp(before) == stamp(after) == stamp(os.stat(name, dir_fd=fd, follow_symlinks=False)), 'file changed during read')
        return (raw, stamp(after))
    finally:
        os.close(handle)

def write_new(fd, name, raw):
    require(re.fullmatch('[A-Za-z0-9_.-]+', name) and name not in ('.', '..'), 'unsafe output name')
    handle = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 384, dir_fd=fd)
    with os.fdopen(handle, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.fsync(fd)

def names(fd, limit):
    result = []
    with os.scandir(fd) as items:
        for item in items:
            result.append(item.name)
            require(len(result) <= limit, 'directory population exceeded')
    return sorted(result)

def validate_original(run, job):
    require(run.get('id') == RUN and run.get('run_attempt') == 1 and (run.get('head_sha') == HEAD), 'original run identity changed')
    require(run.get('repository', {}).get('full_name') == REPO and run.get('path') == '.github/workflows/quota-reserve-closure-development.yml', 'original repository/workflow differs')
    require(run.get('status') == 'completed' and run.get('conclusion') == 'failure', 'original run is not terminal failure')
    require(job.get('id') == JOB and job.get('run_id') == RUN and (job.get('run_attempt') == 1) and (job.get('head_sha') == HEAD), 'original job identity differs')
    require(job.get('runner_id') == 2 and job.get('runner_name') == RUNNER, 'original registered runner differs')
    require(job.get('status') == 'completed' and job.get('conclusion') == 'failure', 'original job is not terminal failure')
    for label, outcome in (('Three complete fixed development phases', 'cancelled'), ('Reconcile final status', 'failure'), ('Preserve deterministic evidence shards', 'success'), ('Upload complete or partial evidence always', 'failure')):
        found = [s for s in job.get('steps', []) if s.get('name') == label]
        require(len(found) == 1 and found[0].get('status') == 'completed' and (found[0].get('conclusion') == outcome), 'original packaging sequence differs')

def location_stamps(destination):
    result = {}
    for name, path in (('destination', destination), ('run_directory', destination.parent)):
        fd = open_dir(path)
        try:
            result[name] = stamp(os.fstat(fd))
        finally:
            os.close(fd)
    return result

class NoRedirect(urllib.request.HTTPRedirectHandler):

    def redirect_request(self, *args, **kwargs):
        raise Blocked('GitHub metadata redirect refused')

def api(tail):
    require(re.fullmatch('(?:runs|jobs)/[0-9]+(?:/jobs\\?filter=latest&per_page=100&page=[1-3])?', tail), 'unexpected metadata endpoint')
    request = urllib.request.Request('https://api.github.com/repos/' + REPO + '/actions/' + tail, headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
        raw = response.read(2 * MIB + 1)
    require(len(raw) <= 2 * MIB, 'GitHub metadata exceeds limit')
    return parse(raw)

def current_job():
    require(os.environ.get('GITHUB_REPOSITORY') == REPO and os.environ.get('GITHUB_EVENT_NAME') == 'push', 'wrong recovery repository/event')
    require(os.environ.get('GITHUB_REF') == BRANCH and os.environ.get('GITHUB_ACTOR') == 'carabinshely', 'wrong branch/actor')
    require(os.environ.get('GITHUB_RUN_ATTEMPT') == '1' and os.environ.get('RUNNER_NAME') == RUNNER, 'wrong attempt/runner')
    run = os.environ['GITHUB_RUN_ID']
    require(run.isdecimal() and int(run) != RUN, 'wrong recovery run')
    response = api('runs/' + run + '/jobs?filter=latest&per_page=100&page=1')
    jobs = response.get('jobs', [])
    require(type(jobs) is list and response.get('total_count') == len(jobs) == 1, 'unexpected recovery jobs')
    found = [j for j in jobs if j.get('name') == os.environ['EXPECTED_JOB_NAME'] and j.get('status') == 'in_progress']
    require(len(found) == 1, 'current job identity unavailable')
    job = found[0]
    require(job.get('runner_id') == 2 and job.get('runner_name') == RUNNER, 'not original registered runner')
    require(job.get('head_sha') == os.environ['GITHUB_SHA'] and job.get('run_id') == int(run) and (job.get('run_attempt') == 1), 'current job source differs')
    return job

def output(values):
    with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
        for key, value in values.items():
            require('\n' not in str(value) and '\r' not in str(value), 'unsafe step output')
            stream.write(key + '=' + str(value) + '\n')


SEALED_RUN = 37104113098
SEALED_HEAD = 'f10138c716246929ac3f3a752f555c3b17ee8327'
MANIFEST_SHA = 'eaa4f9360aea9bc51a726cd02fb342217cb02381047cfcbdc1b67a559fd2be72'
ARCHIVE_SHA = '47b3f93e8825936c5106820bc536f8e7dfbfb4781ab9680bf495c15593767ba1'
FILE_COUNT = 2162
TAILS = {
    'call-results/pass-2/1000319.jsonl': (208945, 'call-results-pass-2-1000319.jsonl'),
    'decision-traces/pass-2/1000319.jsonl': (133757, 'decision-traces-pass-2-1000319.jsonl'),
    'resource-metrics.jsonl': (14404454, 'resource-metrics.jsonl'),
}
READ_LIMIT = 16 * 1024 * MIB - 128 * MIB
UPLOAD_LIMIT = 29 * MIB


def relative_parts(path):
    value = PurePosixPath(path)
    require(type(path) is str and str(value) == path and not value.is_absolute() and
            path not in ('', '.') and '..' not in value.parts and len(path) <= 4096, 'unsafe relative source path')
    require(not any(c in path for c in '\n\r\x00\\'), 'unsafe relative source characters')
    return value.parts


def relative_parent(root, path):
    parts = relative_parts(path)
    fd = os.dup(root)
    try:
        for name in parts[:-1]:
            new = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = new
        return fd, parts[-1]
    except BaseException:
        os.close(fd)
        raise


def tree_inventory(root):
    files, directories = {}, {'.': stamp(os.fstat(root))}
    def visit(fd, prefix, depth):
        require(depth <= 8, 'source directory depth exceeds bound')
        for name in names(fd, FILE_COUNT + 100):
            path = prefix + name
            relative_parts(path)
            value = os.stat(name, dir_fd=fd, follow_symlinks=False)
            require(value.st_uid == os.geteuid(), 'source entry owner differs')
            if stat.S_ISDIR(value.st_mode):
                require(len(directories) < 100, 'source directory count exceeds bound')
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    require(stamp(value) == stamp(os.fstat(child)), 'directory identity changed')
                    directories[path] = stamp(value)
                    visit(child, path + '/', depth + 1)
                finally:
                    os.close(child)
            else:
                require(stat.S_ISREG(value.st_mode) and value.st_nlink == 1, 'nonregular or linked source entry')
                files[path] = stamp(value)
                require(len(files) <= FILE_COUNT, 'source file count exceeds exact population')
    visit(root, '', 0)
    return {'files': files, 'directories': directories}


def hash_one(root, path, expected_size, budget, copy_fd=None, copy_name=None, prefix_size=0):
    parent, name = relative_parent(root, path)
    fd, destination = None, None
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_uid == os.geteuid(), 'unsafe source file')
        require(before.st_size == expected_size, 'source file size differs: ' + path)
        require(budget[0] + expected_size <= READ_LIMIT, 'total read budget exceeded')
        if copy_fd is not None:
            require(copy_name in [v[1] for v in TAILS.values()], 'unapproved tail copy name')
            destination = os.open(copy_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=copy_fd)
        full, prefix = hashlib.sha256(), hashlib.sha256()
        count = 0
        with os.fdopen(os.dup(fd), 'rb') as stream:
            while True:
                block = stream.read(min(MIB, expected_size - count + 1))
                if not block:
                    break
                budget[0] += len(block)
                require(budget[0] <= READ_LIMIT and count + len(block) <= expected_size, 'file grew or total read cap exceeded')
                full.update(block)
                if count < prefix_size:
                    prefix.update(block[:prefix_size - count])
                count += len(block)
                if destination is not None:
                    view = memoryview(block)
                    while view:
                        written = os.write(destination, view)
                        require(written > 0, 'tail snapshot short write')
                        view = view[written:]
        require(count == expected_size, 'source file shrank')
        require(stamp(before) == stamp(os.fstat(fd)) == stamp(os.stat(name, dir_fd=parent, follow_symlinks=False)), 'source file changed during read')
        if destination is not None:
            os.fsync(destination)
            os.fsync(copy_fd)
        return {'sha256': full.hexdigest(), 'size_bytes': count, 'stat': stamp(before), 'prefix_sha256': prefix.hexdigest() if prefix_size else None}
    finally:
        if destination is not None:
            os.close(destination)
        if fd is not None:
            os.close(fd)
        os.close(parent)


def capture_upload(destination, fd, expected, allow_partial):
    allowed = {'source-manifest.json', 'source-inventory.json', 'recovery-report.json', 'authenticated-actions-metadata.json'} | {v[1] for v in TAILS.values()}
    listed = names(fd, len(allowed))
    require('recovery-report.json' in expected and set(expected) <= set(listed) <= allowed, 'unsafe upload files')
    records, total = {}, 0
    os.fchmod(fd, 0o500)
    for name in listed:
        data, observed = read_file(fd, name, UPLOAD_LIMIT)
        total += len(data)
        require(total <= UPLOAD_LIMIT, 'single upload exceeds bound')
        identity = {'sha256': digest(data), 'size_bytes': len(data)}
        if name in expected:
            require(identity == expected[name], 'staged bytes differ from observed source: ' + name)
        else:
            require(allow_partial and name in [v[1] for v in TAILS.values()], 'unverified staged file')
        records[name] = {'sha256': digest(data), 'size_bytes': len(data), 'stat': observed}
    verify_dir(destination, fd)
    return records, location_stamps(destination)


def verify_upload(destination, expected_records, expected_location):
    expected_records, expected_location = parse(expected_records), parse(expected_location)
    fd = open_dir(destination)
    try:
        require(names(fd, 7) == sorted(expected_records), 'upload file population changed')
        total = 0
        for name, expected in expected_records.items():
            data, observed = read_file(fd, name, UPLOAD_LIMIT)
            total += len(data)
            require(total <= UPLOAD_LIMIT, 'upload exceeded byte bound')
            require({'sha256': digest(data), 'size_bytes': len(data), 'stat': observed} == expected, 'upload bytes or stamp changed')
        require(location_stamps(destination) == expected_location, 'upload location changed')
        verify_dir(destination, fd)
    finally:
        os.close(fd)


def snapshot_tails(workspace, destination, metadata, on_ready=None):
    workspace, destination = canonical_path(workspace), canonical_path(destination)
    source_path = workspace.parent / 'bandido-quota-closure-development' / str(RUN) / '1'
    transport_path = source_path.with_name('1-transport')
    require(not destination.is_relative_to(workspace) and not destination.is_relative_to(source_path.parent.parent), 'snapshot overlaps source')
    handles, budget, records, issues, expected_upload = [], [0], {}, [], {}
    report = {'schema': 'worker35-three-tail-preservation-v1', 'started_at': utc(), 'status': 'snapshot_incomplete',
        'original_run_id': RUN, 'original_attempt': 1, 'original_head': HEAD, 'registered_runner_id': 2,
        'recovery_run_id': metadata['recovery_job']['run_id'], 'recovery_head': metadata['recovery_job']['head_sha'],
        'authenticated_metadata_sha256': digest(encode(metadata)),
        'accepted_sealed_run_id': SEALED_RUN, 'accepted_manifest_sha256': MANIFEST_SHA,
        'project_code_imported': False, 'repackaging_performed': False,
        'raw_tree_quiescence_proven': False, 'research_interpretation_performed': False,
        'classification': None, 'remote_artifact_bytes_verified': False, 'original_evidence_writes': False,
        'scope': 'Three file copies and local hash observations; remote readback required'}
    out = None
    def opened(path, fresh=False):
        value = open_dir(path, fresh=fresh)
        handles.append(value)
        return value
    def written(name, data):
        write_new(out, name, data)
        expected_upload[name] = {'sha256': digest(data), 'size_bytes': len(data)}
    try:
        out = opened(destination, fresh=True)
        root = opened(source_path)
        sealed = opened(transport_path)
        manifest_raw, manifest_stat = read_file(sealed, 'artifact-manifest.json', MANIFEST_LIMIT)
        require(digest(manifest_raw) == MANIFEST_SHA, 'accepted sealed manifest changed')
        manifest = parse(manifest_raw)
        require(manifest.get('schema') == 'worker35-artifact-manifest-v1' and len(manifest.get('files', {})) == FILE_COUNT, 'sealed manifest population differs')
        require(manifest.get('archive') == {'sha256': ARCHIVE_SHA, 'size_bytes': 29742478}, 'sealed archive identity differs')
        expected = manifest['files']
        for path in expected:
            relative_parts(path)
        require(set(TAILS) <= set(expected), 'sealed manifest lacks a named tail')
        receipt_raw, receipt_stat = read_file(root, 'receipt.json', MANIFEST_LIMIT)
        require(digest(receipt_raw) == RECEIPT_SHA, 'original receipt changed')
        receipt = parse(receipt_raw)
        require(receipt.get('expected_head') == HEAD and receipt.get('run_id') == str(RUN) and receipt.get('run_attempt') == '1' and receipt.get('freeze_sha256') == FREEZE_SHA, 'receipt identity differs')
        require(receipt.get('status') == 'execution_blocked' and receipt.get('classification') is None, 'original receipt status differs')
        report['runtime_provenance'] = {k: {f: receipt[k].get(f) for f in ('head', 'tree', 'python_version', 'executable_sha256')} for k in ('source_before', 'source_at_finalization')}
        written('source-manifest.json', manifest_raw)
        written('authenticated-actions-metadata.json', encode(metadata))
        first = tree_inventory(root)
        require(set(first['files']) == set(expected), 'raw population differs from exact sealed manifest')
        report['initial_population_matches'] = True
        space = os.fstatvfs(out)
        require(space.f_bavail * space.f_frsize >= UPLOAD_LIMIT, 'insufficient recovery disk space')
        # Copy only the three explicitly named files first, preserving them even
        # if a later unrelated-file hash contradicts the sealed inventory.
        order = list(TAILS) + sorted(set(expected) - set(TAILS))
        for path in order:
            tail = TAILS.get(path)
            size = tail[0] if tail else expected[path]['size_bytes']
            result = hash_one(root, path, size, budget, out if tail else None, tail[1] if tail else None,
                              expected[path]['size_bytes'] if tail else 0)
            require(result['stat'] == first['files'][path], 'source changed since inventory: ' + path)
            records[path] = result
            if tail:
                matches = result['prefix_sha256'] == expected[path]['sha256']
                result['sealed_prefix_matches'] = matches
                result['snapshot_name'] = tail[1]
                if not matches:
                    issues.append({'path': path, 'reason': 'sealed_prefix_hash_mismatch'})
            elif result['sha256'] != expected[path]['sha256']:
                issues.append({'path': path, 'reason': 'non_tail_hash_differs_from_sealed_manifest'})
        report['first_pass_complete'] = True
        for path in sorted(expected):
            before = records[path]
            after = hash_one(root, path, before['size_bytes'], budget)
            require(all(after[k] == before[k] for k in ('sha256', 'size_bytes', 'stat')), 'raw hash or stamp changed between passes: ' + path)
        report['second_pass_stable'] = True
        require(tree_inventory(root) == first, 'raw tree inventory changed between passes')
        require(read_file(sealed, 'artifact-manifest.json', MANIFEST_LIMIT) == (manifest_raw, manifest_stat), 'sealed manifest changed during recovery')
        require(read_file(root, 'receipt.json', MANIFEST_LIMIT) == (receipt_raw, receipt_stat), 'receipt changed during recovery')
        for path, tail in TAILS.items():
            data, _ = read_file(out, tail[1], UPLOAD_LIMIT)
            require(len(data) == records[path]['size_bytes'] and digest(data) == records[path]['sha256'], 'tail copy bytes differ')
        verify_dir(source_path, root)
        verify_dir(transport_path, sealed)
        verify_dir(destination, out)
        report['status'] = 'local_tail_snapshot_verified' if not issues else 'preserved_with_contradictions'
    except Exception as error:
        report['status'] = 'preservation_blocked'
        report['blocker_type'] = type(error).__name__
        report['reason'] = str(error)[:2048]
    finally:
        report.update(finished_at=utc(), raw_bytes_read=budget[0], files_hashed=len(records), issues=issues)
        try:
            if out is not None:
                written('source-inventory.json', encode(records))
                report['source_inventory_sha256'] = digest(encode(records))
                written('recovery-report.json', encode(report))
                for path in records.keys() & TAILS.keys():
                    expected_upload[TAILS[path][1]] = {k: records[path][k] for k in ('sha256', 'size_bytes')}
                records_for_upload, locations = capture_upload(destination, out, expected_upload, report['status'] != 'local_tail_snapshot_verified')
                if on_ready:
                    on_ready(destination, records_for_upload, locations)
        finally:
            for fd in reversed(handles):
                os.close(fd)
    return report, digest(encode(report))


def main():
    def deadline(signum, frame):
        raise Blocked('bounded recovery deadline exceeded')
    signal.signal(signal.SIGALRM, deadline)
    mode = os.environ['RECOVERY_MODE']
    signal.alarm(600 if mode == 'snapshot' else 90)
    workspace = canonical_path(os.environ['GITHUB_WORKSPACE'])
    destination = workspace.parent / 'bandido-worker35-tail-recovery' / os.environ['GITHUB_RUN_ID'] / '1'
    job = current_job()
    if mode == 'snapshot':
        run, original = api('runs/' + str(RUN)), api('jobs/' + str(JOB))
        validate_original(run, original)
        sealed = api('runs/' + str(SEALED_RUN))
        require(sealed.get('id') == SEALED_RUN and sealed.get('run_attempt') == 1 and sealed.get('head_sha') == SEALED_HEAD and sealed.get('status') == 'completed' and sealed.get('conclusion') == 'success', 'sealed recovery run identity/status differs')
        require(sealed.get('repository', {}).get('full_name') == REPO, 'sealed repository differs')
        os.environ.pop('GH_TOKEN', None)
        metadata = {'run': run, 'job': original, 'sealed_run': sealed, 'recovery_job': job, 'fetched_at': utc()}
        report, sha = snapshot_tails(workspace, destination, metadata,
            on_ready=lambda path, records, locations: output({'upload_path': path, 'upload_ready': 'true',
                'upload_records': encode(records).decode().strip(), 'upload_locations': encode(locations).decode().strip()}))
        print(json.dumps({'status': report['status'], 'report_sha256': sha, 'files_hashed': report['files_hashed'], 'classification': None}))
        require(report['status'] == 'local_tail_snapshot_verified', 'preserved bytes require contradiction/blocker review')
    elif mode == 'verify':
        os.environ.pop('GH_TOKEN', None)
        verify_upload(destination, os.environ['EXPECTED_UPLOAD_RECORDS'], os.environ['EXPECTED_UPLOAD_LOCATIONS'])
        print('Local upload bytes and stamps verified; remote readback still required')
    else:
        raise Blocked('unsupported recovery mode')
    signal.alarm(0)


if __name__ == '__main__':
    main()
