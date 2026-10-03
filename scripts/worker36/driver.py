"""One branch-safe, externally admitted Worker36 allocation; no default GO."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import sys
import time
from .common import (Budget, IntegrityError, PREREGISTRATION, PROTOCOL_SHA256, REPOSITORY,
                     RESOURCES, RUNTIME, SCHEDULE, ResourceExceeded, canonical, clean_environment,
                     digest, error_record, file_info, fsync_directory, require, runtime_check, sha,
                     strict_json, update_receipt, write_failure_receipt)
from .sources import git, read_manifest, restore, verify_files

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / 'experiments/synthetic-profile-overhead'
TEST_RECEIPT = EXPERIMENT / 'focused-sixth-repair-test-receipt.json'
EXIT_CODES = {'integrity_invalid': 65, 'execution_incomplete': 74,
              'resource_incomplete': 75, 'execution_blocked': 78}
SUPERVISION_LIMITS = {'wall_seconds': 720, 'cpu_seconds': 720, 'address_space_bytes': 512 * 1024 ** 2,
                     'call_wall_seconds': 360, 'call_cpu_seconds': 360, 'output_log_limit_bytes': 63 * 1024 ** 2}


def required_diagnostic_paths(repo):
    repo = Path(repo)
    return {p.relative_to(repo).as_posix() for p in (repo / 'scripts/worker36').glob('*.py')} | {
        'scripts/run_worker36_synthetic.py', '.github/workflows/worker36-synthetic-profile.yml',
        '.github/workflows/worker36-runner-preflight.yml',
        'experiments/synthetic-profile-overhead/PROTOCOL.md',
        'experiments/synthetic-profile-overhead/source-manifest.json',
        'experiments/synthetic-profile-overhead/fault-test-manifest.json'}


def checked_source_paths(repo):
    repo = Path(repo)
    return required_diagnostic_paths(repo) | {p.relative_to(repo).as_posix() for p in (repo / 'tests').glob('test_worker36_*.py')} | {
        'tests/worker36_constructor_source.txt', 'evidence-design/supervisor-test-plan.json',
        'evidence-design/transport-test-plan.json', 'evidence-design/driver-integration-test-plan.json',
        'evidence-design/cell-integration-test-plan.json', 'evidence-design/verifier-integration-test-plan.json',
        'evidence-design/admission-integration-test-plan.json', 'evidence-design/failure-state-test-plan.json',
        'evidence-design/runner-preflight-test-plan.json', 'evidence-design/driver-third-repair-test-plan.json',
        'evidence-design/cell-third-repair-test-plan.json', 'evidence-design/supervisor-third-repair-test-plan.json',
        'evidence-design/driver-fourth-repair-test-plan.json', 'evidence-design/cell-fourth-repair-test-plan.json',
        'evidence-design/supervisor-fourth-repair-test-plan.json', 'evidence-design/ast-fifth-repair-test-plan.json',
        'evidence-design/supervisor-fifth-repair-test-plan.json', 'evidence-design/driver-fifth-repair-test-plan.json',
        'evidence-design/supervisor-sixth-repair-test-plan.json', 'evidence-design/driver-sixth-repair-test-plan.json'}


def verify_test_receipt(repo, expected_hash):
    path = Path(repo) / TEST_RECEIPT.relative_to(ROOT)
    require(re.fullmatch('[a-f0-9]{64}', expected_hash or '') is not None and
            file_info(path)['sha256'] == expected_hash, 'actual focused test receipt hash mismatch')
    record = strict_json(path.read_bytes())
    require(record['success'] is True and record['failures'] == record['errors'] == 0 and
            record['candidate_evaluator_calls'] == record['reference_evaluator_calls'] == record['games'] ==
            record['measurement_fixture_constructions'] == record['historical_source_imports'] == 0,
            'focused receipt is not successful bounded stub-only verification')
    pins = record['checked_file_sha256']
    require(set(pins) == checked_source_paths(repo), 'complete focused checked-source map required')
    for name, pin in pins.items():
        require(file_info(Path(repo) / name)['sha256'] == pin, 'checked source differs from tested bytes: ' + name)
    return record


def read_admission(path, expected_sha256, repo, provenance_path=None, provenance_sha256=None):
    from .admission import verify_provenance
    raw = Path(path).read_bytes()
    require(len(raw) <= 1024 ** 2 and sha(raw) == expected_sha256, 'external admission raw hash')
    go = strict_json(raw)
    require(go.get('schema') == 'worker36-one-shot-admission-v1' and go.get('admitted') is True,
            'separately recorded one-shot admission required')
    require(provenance_path is not None, 'authenticated PR-event/API provenance required')
    require(re.fullmatch('[a-f0-9]{64}', provenance_sha256 or '') is not None and
            file_info(provenance_path)['sha256'] == provenance_sha256, 'authenticated provenance bytes drift')
    provenance = verify_provenance(provenance_path, path, expected_sha256)
    require(go['repository'] == REPOSITORY and go['preregistration_url'] == PREREGISTRATION and
            go['protocol_sha256'] == PROTOCOL_SHA256 and go['maximum_evaluator_calls'] == 40 and
            go['games'] == 0 and go['schedule'] == list(SCHEDULE), 'admission allocation mismatch')
    require(go['runtime'] == RUNTIME and go['resources'] == RESOURCES, 'frozen resource/runtime mismatch')
    require(go['runner'] == 'bandido-alcatraz-ci' and go['branch'] == 'research/worker36-synthetic-profile-overhead',
            'admission destination mismatch')
    require(os.environ.get('GITHUB_EVENT_NAME') == 'pull_request' and os.environ.get('GITHUB_RUN_ATTEMPT') == '1' and
            os.environ.get('GITHUB_RUN_ID') == provenance['workflow_run'] and
            provenance['workflow_attempt'] == '1' and provenance['admission_url'] == go['admission_url'],
            'first authenticated PR-body admission run required')
    head = git(repo, 'rev-parse', 'HEAD').decode().strip()
    tree = git(repo, 'rev-parse', 'HEAD^{tree}').decode().strip()
    require(head == go['head'] == provenance['head'] and tree == go['tree'] == provenance['tree'],
            'exact diagnostic head/tree mismatch')
    require(not git(repo, 'status', '--porcelain', '--untracked-files=no'), 'tracked checkout drift')
    require(go['source_manifest_sha256'] == file_info(EXPERIMENT / 'source-manifest.json')['sha256'] and
            file_info(EXPERIMENT / 'PROTOCOL.md')['sha256'] == PROTOCOL_SHA256, 'source manifest/protocol pin')
    require(set(go['diagnostic_files_sha256']) == required_diagnostic_paths(repo), 'exact complete diagnostic pins required')
    for name, pin in go['diagnostic_files_sha256'].items():
        require(file_info(Path(repo) / name)['sha256'] == pin, 'diagnostic source drift: ' + name)
    reviews = go['reviews']
    require(type(reviews) is list and len(reviews) >= 2 and all(r.get('head') == head and r.get('tree') == tree and
            r.get('verdict') == 'clean' and r.get('url', '').startswith('https://github.com/' + REPOSITORY + '/')
            for r in reviews) and len({r['reviewer'] for r in reviews}) >= 2, 'two independent exact-head clean reviews required')
    require(go['postmerge_ci'] == provenance['postmerge_ci'], 'authenticated postmerge CI prerequisite')
    verify_test_receipt(repo, go['stub_test_receipt_sha256'])
    return go, provenance


def _prefix_read(root, path, corrupt, unavailable):
    """Optional bounded record; absent paths differ from unavailable bytes."""
    name = path.relative_to(root).as_posix()
    def gap(exc):
        if len(unavailable) < 160:
            unavailable.append(_unavailable(name, exc))
        return None, 'unavailable'
    try:
        path.lstat()
    except FileNotFoundError:
        return None, 'absent'
    except (OSError, MemoryError) as exc:
        return gap(exc)
    try:
        with path.open('rb') as stream:
            raw = stream.read(8 * 1024 ** 2 + 1)
    except (OSError, MemoryError, RecursionError) as exc:
        return gap(exc)
    try:
        require(len(raw) <= 8 * 1024 ** 2, 'bounded prefix record')
        value = strict_json(raw)
        require(type(value) is dict, 'prefix object required')
        return value, 'present'
    except (ValueError, UnicodeError) as exc:
        if len(corrupt) < 160:
            corrupt.append({'path': name, 'error_type': type(exc).__name__, 'error': str(exc)[:256],
                            'bytes_preserved': True})
        return None, 'malformed'
    except (MemoryError, RecursionError) as exc:
        return gap(exc)


def _unavailable(path, error):
    return {'path': path, 'error_type': type(error).__name__, 'error': str(error)[:256],
            'evidence_state': 'unavailable', 'method_entry': 'unknown',
            'failure': {**error_record(error, 'prefix_reconciliation', resource_types=(RecursionError,)),
                        'evidence_path': path}}


def _malformed(path, detail):
    return {**error_record(IntegrityError('malformed retained evidence: ' + detail), 'prefix_reconciliation'),
            'evidence_path': path}


def _checked_failure(value, path, *, terminal=True):
    require(type(value) is dict, 'failure must be an object')
    require(type(value.get('status')) is str and value['status'] in
            (set(EXIT_CODES) if terminal else set(EXIT_CODES) | {'measuring', 'execution_complete', 'complete', 'completed', 'in_progress'}),
            'failure status must be a recognized string')
    for key in ('category', 'phase', 'error_type', 'error'):
        require(type(value.get(key)) is str, 'failure ' + key + ' must be a string')
    return {**value, 'evidence_path': value.get('evidence_path', path)}


def _retained_failures(value, path):
    """Validate committed status metadata before any membership or reduction."""
    if value is None:
        return []
    causes = []
    try:
        require(type(value) is dict, 'retained record must be an object')
        allowed = set(EXIT_CODES) | {'measuring', 'execution_complete', 'complete', 'completed', 'in_progress'}
        status = value.get('status')
        if 'status' in value:
            require(type(status) is str and status in allowed, 'invalid retained status')
        for key in ('reason', 'phase', 'error_type', 'error'):
            if key == 'phase' and value.get('schema') == 'worker36.supervision.v1' and type(value.get(key)) is dict:
                continue
            if value.get(key) is not None:
                require(type(value[key]) is str, 'invalid retained ' + key)
        failure = value.get('failure')
        if failure is not None:
            failure = _checked_failure(failure, path)
            require(status is None or status == failure['status'], 'status/failure contradiction')
            causes.append(failure)
        secondary = value.get('secondary_errors', [])
        require(type(secondary) is list and len(secondary) <= 80, 'invalid secondary_errors list')
        causes.extend(_checked_failure(item, path) for item in secondary)
        def outcome(item, label, *, secondary=False):
            require(type(item) is dict and type(item.get('status')) is str and
                    item['status'] in (set(EXIT_CODES) if secondary else set(EXIT_CODES) | {'completed'}),
                    'invalid supervisor outcome status')
            require(type(item.get('reason')) is str, 'invalid supervisor outcome reason')
            for key in ('phase', 'exception_type', 'message'):
                if key in item:
                    require(type(item[key]) is str, 'invalid supervisor outcome ' + key)
            if item['status'] in EXIT_CODES:
                causes.append({'status': item['status'], 'category': label,
                    'phase': item.get('phase', 'supervision'), 'error_type': item.get('exception_type', 'SupervisorOutcome'),
                    'error': item.get('message', item['reason']), 'reason': item['reason'], 'evidence_path': path})
        if 'primary_outcome' in value:
            outcome(value['primary_outcome'], 'supervisor_primary')
        extra = value.get('secondary_failures', [])
        require(type(extra) is list and len(extra) <= 80, 'invalid secondary_failures list')
        for item in extra:
            outcome(item, 'supervisor_secondary', secondary=True)
        if status in EXIT_CODES and failure is None:
            causes.append({'status': status, 'category': 'retained_failure', 'phase': value.get('phase') if type(value.get('phase')) is str else 'supervision',
                'error_type': value.get('error_type') or 'RetainedFailure',
                'error': value.get('error') or value.get('reason') or status, 'evidence_path': path})
        exit_code = value.get('exit_code')
        require(exit_code is None or type(exit_code) is int, 'invalid child exit code')
        if status == 'completed':
            require(exit_code == 0, 'completed supervisor contradicts child exit')
        if exit_code in EXIT_CODES.values():
            child_status = next(k for k, v in EXIT_CODES.items() if exit_code == v)
            causes.append({'status': child_status, 'category': 'typed_child_exit', 'phase': 'child_exit',
                'error_type': 'TypedChildExit', 'error': 'child exit code ' + str(exit_code),
                'exit_code': exit_code, 'evidence_path': path})
    except (IntegrityError, TypeError, ValueError) as exc:
        causes.append(_malformed(path, str(exc)[:256]))
    return causes


def reconcile_prefix(root):
    """Bounded nonthrowing reconciliation of entry bounds and surviving failures."""
    root = Path(root); lower = upper = returns = confirmed = markers = 0
    gaps = []; corrupt = []; unavailable = []; failures = []
    def read(path):
        value, state = _prefix_read(root, path, corrupt, unavailable)
        failures.extend(_retained_failures(value, path.relative_to(root).as_posix()))
        return value, state
    for identity in SCHEDULE:
        folder = root / 'cells' / f"{identity['cell']:02d}"
        child, child_state = read(folder / 'cell-receipt.json')
        sidecar, sidecar_state = read(root / f"failure-receipt-cell-{identity['cell']:02d}.json")
        if child is None or isinstance(sidecar, dict) and sidecar.get('calls'):
            child = sidecar
        complete_claim = isinstance(child, dict) and child.get('status') == 'complete'
        if complete_claim:
            required = ['source-runtime-preflight.json', 'cell-start.json', 'cell-boundaries.json', 'active-call.json']
            required += ['unmeasured-accounting.json'] if identity['condition'] == 'U' else ['whole-wrapper-resources.json']
            for name in required:
                record, state = read(folder / name)
                if state == 'absent':
                    corrupt.append({'path': (folder / name).relative_to(root).as_posix(),
                                    'error': 'complete child claims missing required committed record'})
                if name == 'active-call.json' and state == 'present' and record != {'active': False}:
                    corrupt.append({'path': (folder / name).relative_to(root).as_posix(),
                                    'error': 'complete child retains an active or invalid control record'})
            if identity['condition'] == 'P':
                for name in ('resource-metrics.jsonl', 'call-results/pass-2/11.jsonl', 'decision-traces/pass-2/11.jsonl'):
                    path = folder / name
                    try:
                        require(path.is_file() and not path.is_symlink() and path.stat().st_size > 0,
                                'complete child requires a nonempty committed P journal')
                    except IntegrityError as exc:
                        corrupt.append({'path': path.relative_to(root).as_posix(), 'error': str(exc)})
                    except (OSError, MemoryError, RecursionError) as exc:
                        unavailable.append(_unavailable(path.relative_to(root).as_posix(), exc))
            for key in ('actual_starts', 'actual_starts_upper_bound', 'actual_returns', 'confirmed_captures', 'pre_call_markers'):
                if type(child.get(key)) is not int or child[key] != 2:
                    corrupt.append({'path': (folder / 'cell-receipt.json').relative_to(root).as_posix(),
                                    'error': 'complete child has invalid ' + key})
        calls = child.get('calls', {}) if isinstance(child, dict) else {}
        if not isinstance(calls, dict):
            corrupt.append({'path': str(folder.relative_to(root) / 'cell-receipt.json'), 'error': 'invalid calls map'})
            calls = {}
        read(root / f"supervisor-cell-{identity['cell']:02d}.json")
        for scope in ('candidate', 'reference'):
            call = calls.get(scope)
            if not isinstance(call, dict):
                call = {}
            start_path = folder / (scope + '-start.json'); start, start_state = read(start_path)
            temporary = start_path.with_name(start_path.name + '.tmp')
            try:
                temporary.lstat()
                temporary_state = 'uncommitted'
                unavailable.append({'path': temporary.relative_to(root).as_posix(), 'evidence_state': 'uncommitted',
                    'method_entry': 'unknown', 'bytes_preserved': True,
                    'failure': {'status': 'execution_incomplete', 'category': 'uncommitted_publication',
                        'phase': 'prefix_reconciliation', 'error_type': 'UncommittedEvidence',
                        'error': 'atomic staging bytes are uncommitted; contents not parsed'}})
            except FileNotFoundError:
                temporary_state = 'absent'
            except (OSError, MemoryError) as exc:
                temporary_state = 'unavailable'
                unavailable.append(_unavailable(temporary.relative_to(root).as_posix(), exc))
            returned_path = folder / (scope + '-return.json'); returned, return_state = read(returned_path)
            capture_path = folder / (scope + '-capture-confirmed.json'); capture, capture_state = read(capture_path)
            marker = call.get('start_marker_durable') is True and start_state == 'present'
            markers += int(marker)
            if complete_claim:
                for name, state in ((scope + '-start.json', start_state), (scope + '-return.json', return_state),
                                    (scope + '-capture-confirmed.json', capture_state)):
                    if state == 'absent':
                        corrupt.append({'path': (folder / name).relative_to(root).as_posix(),
                                        'error': 'complete child claims missing required committed event'})
                if any(call.get(key) is not True for key in ('start_marker_durable', 'invocation_attempted',
                        'method_entered', 'returned', 'durable_capture_confirmed')):
                    corrupt.append({'path': (folder / 'cell-receipt.json').relative_to(root).as_posix(),
                                    'error': 'complete child has inconsistent call claims: ' + scope})
            observed_return = call.get('returned') is True or returned is not None
            entry_known = call.get('method_entered') is True or observed_return
            uncertain = 'unavailable' in (child_state, sidecar_state, start_state, temporary_state, return_state, capture_state)
            if call and call.get('invocation_attempted') is False and not observed_return and not uncertain:
                possible = False
            else:
                possible = entry_known or call.get('invocation_attempted') is True or start_state != 'absent' or temporary_state != 'absent' or uncertain
            lower += int(entry_known); upper += int(possible); returns += int(observed_return)
            good_capture = False
            if capture is not None:
                try:
                    require(returned is not None, 'capture confirmation without available return bytes')
                    actual = {'path': returned_path.relative_to(root).as_posix(), **file_info(returned_path)}
                    require(capture == actual, 'capture confirmation does not bind complete return bytes')
                    good_capture = True; confirmed += 1
                except (OSError, MemoryError, RecursionError) as exc:
                    unavailable.append(_unavailable(returned_path.relative_to(root).as_posix(), exc))
                except IntegrityError as exc:
                    # A read failure does not prove that the surviving capture
                    # contradicts its return; keep that boundary uncertain.
                    if return_state != 'unavailable':
                        corrupt.append({'path': capture_path.relative_to(root).as_posix(), 'error': str(exc)[:256], 'bytes_preserved': True})
            if possible and (not entry_known or not good_capture or not marker):
                gaps.append({'cell': identity['cell'], 'scope': scope, 'method_entry': 'known' if entry_known else 'unknown',
                             'durable_start_marker_confirmed': marker, 'observed_return': observed_return,
                             'durable_capture': 'confirmed' if good_capture else 'missing_or_unconfirmed'})
    # Parent sidecars can survive a failed main-receipt publication. Never make
    # successful recovery depend on the continued readability of the main file.
    try:
        sidecars = sorted(root.glob('failure-receipt-parent-*.json'))
        if len(sidecars) > 80:
            unavailable.append(_unavailable('.', ResourceExceeded('parent-sidecar inventory exceeds bounded recovery scan')))
        for path in sidecars[:80]:
            read(path)
    except (OSError, MemoryError, RecursionError) as exc:
        unavailable.append(_unavailable('.', exc))
    return {'actual_starts': lower, 'actual_starts_upper_bound': upper, 'pre_call_markers': markers,
            'actual_starts_semantics': 'observed method-entry lower bound; upper bound includes uncertain pre-call boundaries',
            'actual_returns': returns, 'actual_returns_semantics': 'observed lower bound; absent return evidence is unknown',
            'confirmed_captures': confirmed, 'capture_gaps': gaps[:80], 'corrupt_evidence': corrupt[:160],
            'unavailable_evidence': unavailable[:160], 'retained_failures': failures[:80]}


def reduce_failure(primary, counts, *, current=None, additional=()):
    """One attempt-wide reducer for live supervision and post-kill recovery."""
    candidates = []
    def add(value, path):
        if value is None:
            return
        try:
            # Primary progress-state normalization is intentional, but malformed
            # fields are integrity evidence rather than an escaping TypeError.
            require(type(value) is dict, 'failure must be an object')
            item = dict(value)
            for key, default in (('category', 'incomplete_execution'), ('phase', 'recovery'),
                                 ('error_type', 'IncompleteExecution'), ('error', 'execution did not complete')):
                item.setdefault(key, default)
            candidates.append(_checked_failure(item, path, terminal=False))
        except (IntegrityError, TypeError, ValueError) as exc:
            candidates.append(_malformed(path, str(exc)[:256]))
    add(primary, 'primary_failure')
    candidates.extend(_retained_failures(current, 'receipt.json'))
    for item in counts.get('retained_failures', ()):
        add(item, 'retained_failure')
    for item in additional:
        add(item, 'additional_failure')
    for item in counts.get('unavailable_evidence', ()):
        add(item.get('failure') if isinstance(item, dict) and item.get('failure') else {
            'status': 'execution_incomplete', 'category': 'unavailable_evidence', 'phase': 'prefix_reconciliation',
            'error_type': 'UnavailableEvidence', 'error': 'required evidence remains unavailable'}, 'unavailable_evidence')
    if counts.get('capture_gaps'):
        add({'status': 'execution_incomplete', 'category': 'capture_gap', 'phase': 'prefix_reconciliation',
             'error_type': 'RequiredEvidenceGap', 'error': 'required committed start/return/capture evidence is incomplete'}, 'capture_gaps')
    if counts.get('corrupt_evidence'):
        candidates.append(error_record(IntegrityError('corrupted required evidence'), 'prefix_reconciliation'))
    if not candidates:
        return None, []
    zero_known = (counts.get('actual_starts_upper_bound') == 0 and not counts.get('unavailable_evidence') and
                  not counts.get('capture_gaps'))
    if isinstance(current, dict):
        zero_known = zero_known and not current.get('actual_starts') and not current.get('actual_starts_upper_bound') and not current.get('completed_prefix')
    for item in candidates:
        prior = item.get('status')
        if prior not in EXIT_CODES or prior == 'execution_blocked' and not zero_known:
            item.update(status='execution_incomplete', prior_status=prior)
        item.setdefault('category', 'incomplete_execution')
        item.setdefault('phase', 'recovery')
        item.setdefault('error_type', 'IncompleteExecution')
        item.setdefault('error', 'execution did not complete')
    priority = {'integrity_invalid': 3, 'resource_incomplete': 2, 'execution_incomplete': 1, 'execution_blocked': 0}
    winner = max(range(len(candidates)), key=lambda i: priority[candidates[i]['status']])
    return candidates[winner], [x for i, x in enumerate(candidates) if i != winner][:12]


def terminalize(root, primary, *, counts=None, secondary=()):
    """Reduce surviving evidence first; persistence errors cannot erase it."""
    root = Path(root); counts = counts if counts is not None else reconcile_prefix(root)
    current, state = _prefix_read(root, root / 'receipt.json', counts['corrupt_evidence'], counts['unavailable_evidence'])
    primary, other = reduce_failure(primary, counts, current=current, additional=secondary)
    require(primary is not None, 'terminal failure cause required')
    prior = {'prior_status': current.get('prior_status', current.get('status')),
             'prior_phase': current.get('prior_phase', current.get('phase'))} if isinstance(current, dict) else {}
    try:
        if state != 'present':
            raise OSError('main receipt unavailable for replacement: ' + state)
        update = {**current, **counts, **prior, 'status': primary['status'], 'phase': primary['phase'], 'failure': primary,
                  'secondary_errors': other, 'error_type': primary['error_type'], 'error': primary['error'],
                  'custody': 'pending', 'classification': None}
        Budget(root).write(root / 'receipt.json', update, replace=True)
        return update
    except Exception as write_error:
        primary, other = reduce_failure(primary, counts, current=current,
            additional=[*other, error_record(write_error, 'terminal_receipt_persistence')])
        record = {'schema': 'worker36-terminal-failure-v1', **counts, **prior, **primary, 'failure': primary,
                  'secondary_errors': other[:12],
                  'custody': 'pending', 'classification': None, 'original_receipt_bytes_preserved': True}
        try:
            write_failure_receipt(root, record, name='failure-receipt-parent-' + str(time.monotonic_ns()) + '.json')
        except Exception as sidecar_error:
            primary, other = reduce_failure(primary, counts, additional=[*other, error_record(sidecar_error, 'terminal_sidecar_persistence')])
            record.update(**primary, failure=primary, secondary_errors=other[:12], terminal_durability='unconfirmed')
            print(canonical({**record, 'terminal_durability': 'unconfirmed',
                             'sidecar_error': type(sidecar_error).__name__}).decode(), file=sys.stderr, end='')
        return record


def install_memory_cap():
    pair = resource.getrlimit(resource.RLIMIT_AS); frozen = (512 * 1024 ** 2,) * 2
    require(pair in ((resource.RLIM_INFINITY,) * 2, frozen), 'unexpected inherited address-space limit')
    resource.setrlimit(resource.RLIMIT_AS, frozen)
    require(resource.getrlimit(resource.RLIMIT_AS) == frozen, 'exact512MiB process memory cap required')


def durable_location(root, provenance):
    root = Path(root).absolute(); durable = Path(provenance['durable_root'])
    require(root == Path(provenance['attempt_path']) and root.parent == durable and
            durable.is_dir() and not durable.is_symlink() and durable.stat().st_uid == os.getuid(),
            'authenticated durable runner-owned attempt path required')
    for excluded in (ROOT, Path(os.environ.get('RUNNER_TEMP', '/tmp'))):
        require(not root.resolve().is_relative_to(excluded.resolve()), 'attempt must be outside checkout/temp')


def measure(attempt, admission, admission_sha256, admission_provenance, admission_provenance_sha256):
    from .admission import INPUT_NAMES
    from .supervision import PhaseBudget, run_child
    root = Path(attempt).absolute(); require(not root.exists() and root.parent.is_dir(), 'exclusive attempt path required')
    root.mkdir(); fsync_directory(root); fsync_directory(root.parent); budget = Budget(root)
    receipt = {'schema': 'worker36-attempt-v1', 'status': 'execution_blocked', 'phase': 'admission',
        'attempt_id': root.name, 'attempt_path': str(root), 'preregistration_url': PREREGISTRATION,
        'admission_verified': False, 'admission_sha256': admission_sha256,
        'diagnostic_head': None, 'runner': os.environ.get('RUNNER_NAME'), 'workflow_run': os.environ.get('GITHUB_RUN_ID'),
        'workflow_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'), 'source_manifest_sha256': file_info(EXPERIMENT / 'source-manifest.json')['sha256'],
        'resources': RESOURCES, 'schedule': list(SCHEDULE), 'maximum_evaluator_calls': 40, 'games': 0,
        'actual_starts': 0, 'actual_starts_upper_bound': 0, 'actual_returns': 0, 'confirmed_captures': 0,
        'current_cell': None, 'completed_prefix': [], 'custody': 'pending', 'classification': None,
        'supervisor_pid': os.getpid()}
    phase_name = 'admission'; old_handler = None; primary_failure = None; pending_supervisor_failures = []
    try:
        budget.write(root / 'receipt.json', receipt)
        go, provenance = read_admission(admission, admission_sha256, ROOT, admission_provenance, admission_provenance_sha256)
        durable_location(root, provenance)
        budget.write(root / 'external-admission.json', Path(admission).read_bytes(), raw=True)
        for name in (*INPUT_NAMES, Path(admission).name, Path(admission_provenance).name):
            budget.write(root / 'admission-inputs' / name, (Path(admission).parent / name).read_bytes(), raw=True)
        budget.write(root / 'stub-test-receipt.json', TEST_RECEIPT.read_bytes(), raw=True)
        update_receipt(root, admission_verified=True, diagnostic_head=go['head'], diagnostic_tree=go['tree'])
        claim_root = Path(os.environ['WORKER36_CLAIM_DIRECTORY']).resolve()
        require(claim_root.is_dir() and not claim_root.is_symlink(), 'persistent claim directory unavailable')
        claim = claim_root / (digest(PREREGISTRATION) + '.claimed.json')
        with claim.open('xb') as f:
            f.write(canonical({'head': go['head'], 'attempt_id': root.name, 'workflow_run': provenance['workflow_run'],
                               'admission_sha256': admission_sha256})); f.flush(); os.fsync(f.fileno())
        fsync_directory(claim_root)
        phase_name = 'source_runtime_preflight'
        require(shutil.disk_usage(root).free >= 1024 ** 3, '1GiB free attempt storage required')
        runtime = runtime_check()
        inherited = {n: list(resource.getrlimit(getattr(resource, n))) for n in dir(resource) if n.startswith('RLIMIT_')}
        require(inherited == go['inherited_limits'], 'unexpected inherited resource limits')
        runtime['inherited_limits'] = inherited
        require(resource.getrlimit(resource.RLIMIT_AS) == (resource.RLIM_INFINITY,) * 2, 'unexpected initial coordinator address-space ceiling')
        install_memory_cap()
        budget.write(root / 'source-manifest.json', (EXPERIMENT / 'source-manifest.json').read_bytes(), raw=True)
        manifest = read_manifest(root / 'source-manifest.json')
        restore(ROOT, root / 'restored', manifest, budget)
        budget.write(root / 'source-runtime-preflight.json', {'evaluator_starts': 0, 'runtime': runtime,
            'coordinator_address_space': list(resource.getrlimit(resource.RLIMIT_AS)), 'phase': phase_name,
            'restored_source_inventory': manifest['files'], 'diagnostic_files_sha256': go['diagnostic_files_sha256']})
        phase_name = 'measurement'; phase = PhaseBudget(wall_seconds=1800, cpu_seconds=1800)
        old_handler = signal.getsignal(signal.SIGALRM)
        def expired(signum, frame):
            raise ResourceExceeded('kernel ' + phase_name + ' wall deadline')
        signal.signal(signal.SIGALRM, expired); signal.setitimer(signal.ITIMER_REAL, 1800)
        completed = []; total = dict.fromkeys(('legal_enumerations', 'previews', 'exit_geometry_checks'), 0)
        env = clean_environment()
        for key in ('GH_TOKEN', 'GITHUB_TOKEN', 'ACTIONS_RUNTIME_TOKEN'):
            env.pop(key, None)
        last_result = None
        for identity in SCHEDULE:
            phase_name = 'measurement_source_check'
            verify_files(root / 'restored', manifest)
            for name, pin in go['diagnostic_files_sha256'].items():
                require(file_info(ROOT / name)['sha256'] == pin, 'diagnostic source drift after initial preflight')
            folder = root / 'cells' / f"{identity['cell']:02d}"
            require(not folder.exists(), 'cell cannot be retried'); budget.mkdir(folder)
            update_receipt(root, status='measuring', phase='measurement', current_cell=identity['cell'], completed_prefix=completed)
            phase_name = 'measurement'
            command = [sys.executable, '-B', '-s', str(ROOT / 'scripts/run_worker36_synthetic.py'),
                       '_cell', '--attempt', str(root), '--cell', str(identity['cell'])]
            result = run_child(command, env, ROOT, root / f"supervisor-cell-{identity['cell']:02d}.log",
                folder / 'active-call.json', phase, **SUPERVISION_LIMITS, output_budget_check=budget.check_raw_log,
                output_budget_exceptions=(ResourceExceeded,),
                expected_inherited_limits={**go['inherited_limits'], 'RLIMIT_AS': [512 * 1024 ** 2] * 2})
            # Recover the child's typed failure or exit BEFORE any ordinary
            # parent evidence publication. A later cap/I/O error is secondary.
            pending_supervisor_failures = _retained_failures(result, 'current_supervisor_result')
            counts = reconcile_prefix(root)
            primary_failure, secondary = reduce_failure(None, counts, additional=pending_supervisor_failures)
            result['limits'] = dict(SUPERVISION_LIMITS)
            if phase.exhausted(phase.snapshot()):
                result.update(status='resource_incomplete', reason='measurement_phase_ceiling')
                primary_failure, secondary = reduce_failure(primary_failure, counts,
                    additional=_retained_failures(result, 'current_supervisor_result'))
            budget.write(root / f"supervisor-cell-{identity['cell']:02d}.json", result)
            last_result = result
            if primary_failure is not None:
                terminalize(root, primary_failure, counts=counts, secondary=secondary)
                return 1
            child, _ = _prefix_read(root, folder / 'cell-receipt.json', counts['corrupt_evidence'], counts['unavailable_evidence'])
            if child is None or child.get('status') != 'complete':
                terminalize(root, {'status': 'execution_incomplete', 'category': 'supervision', 'phase': phase_name,
                    'error_type': 'ChildIncomplete', 'error': result.get('reason') or 'missing complete child receipt'}, counts=counts)
                return 1
            require(child['actual_starts'] == child['actual_starts_upper_bound'] == child['actual_returns'] == child['confirmed_captures'] == 2,
                    'complete child entry/return accounting')
            if identity['condition'] == 'P':
                whole = strict_json((folder / 'whole-wrapper-resources.json').read_bytes())
                for key in total:
                    total[key] += whole['operations'][key]
                    if total[key] > 1000000:
                        raise ResourceExceeded('sum across P cells: ' + key)
            completed.append(identity['cell'])
            update_receipt(root, completed_prefix=completed, resource_totals={'supervision': result, 'P_operations': total, 'phase': phase.snapshot()}, **counts)
        counts = reconcile_prefix(root)
        primary_failure, secondary = reduce_failure(None, counts)
        if primary_failure is not None:
            terminalize(root, primary_failure, counts=counts, secondary=secondary)
            return 1
        final_before = phase.snapshot()
        if phase.exhausted(final_before):
            raise ResourceExceeded('measurement phase exhausted before computational receipt publication')
        update_receipt(root, status='execution_complete', phase='verification_pending', current_cell=None,
            resource_totals={'supervision': last_result, 'P_operations': total, 'phase': final_before},
            file_inventory=[f for f in budget.inventory() if f['path'] != 'receipt.json'], **counts)
        # This fresh check includes the computational completion receipt's
        # durable publication. No measurement work occurs after this boundary.
        closed = phase.snapshot()
        if phase.exhausted(closed):
            raise ResourceExceeded('measurement phase exhausted during computational receipt publication')
        preservation_started = phase.wall_started + closed['wall_seconds']
        preservation_deadline = preservation_started + 600
        phase_name = 'closing_proof_preservation'
        remaining = preservation_deadline - time.monotonic()
        if remaining <= 0:
            raise ResourceExceeded('closing proof preservation deadline exhausted')
        signal.setitimer(signal.ITIMER_REAL, remaining)
        budget.write(root / 'measurement-phase-close.json', {
            'schema': 'worker36-measurement-phase-close-v1', 'phase': closed,
            'computational_receipt': {'path': 'receipt.json', **file_info(root / 'receipt.json')},
            'includes_computational_receipt_publication': True, 'closing_proof_included_in_measurement': False,
            'measurement_work_after_close': False, 'preservation_started_monotonic': preservation_started,
            'preservation_deadline_monotonic': preservation_deadline})
        if time.monotonic() >= preservation_deadline:
            raise ResourceExceeded('closing proof preservation deadline exhausted')
        return 0
    except BaseException as caught:
        later = getattr(caught, 'worker36_failure', None) or error_record(caught, phase_name)
        terminalize(root, primary_failure or later,
            secondary=[*pending_supervisor_failures, *getattr(caught, 'worker36_secondary_errors', []),
                       *([later] if primary_failure else [])])
        return 1
    finally:
        if old_handler is not None:
            try:
                signal.setitimer(signal.ITIMER_REAL, 0); signal.signal(signal.SIGALRM, old_handler)
            except BaseException as restoration_error:
                terminalize(root, error_record(restoration_error, 'coordinator_timer_restoration'),
                            secondary=pending_supervisor_failures)
                return 1


def write_report(path, value, *, replace=False):
    path = Path(path); raw = canonical(value)
    require(len(raw) <= 1024 ** 2, 'bounded external report')
    require(path.parent.is_dir() and (replace or not path.exists()), 'exclusive report under existing durable root')
    target = path.with_name(path.name + '.tmp') if replace else path
    with target.open('xb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())
    if replace:
        os.replace(target, path)
    fsync_directory(path.parent)


def recovery_inventory(root, destination):
    files = []; total = 0
    for label, base in (('raw', Path(root)), ('transport', Path(destination))):
        if not base.exists():
            continue
        for path in sorted(base.rglob('*')):
            if path.is_file() and not path.is_symlink():
                if len(files) >= 2048:
                    return {'files': files, 'total_bytes': total, 'inventory_complete': False}
                info = file_info(path); total += info['size_bytes']
                files.append({'tree': label, 'path': path.relative_to(base).as_posix(), **info})
    return {'files': files, 'total_bytes': total, 'inventory_complete': True}



def proven_preclosing(root):
    """Positive surviving progress evidence only; absence alone proves nothing."""
    root = Path(root)
    try:
        (root / 'receipt.json.tmp').lstat()
    except FileNotFoundError:
        pass
    else:
        return False
    raw = (root / 'receipt.json').read_bytes()
    require(len(raw) <= RESOURCES['receipt_bytes'], 'bounded recovery receipt required')
    current = strict_json(raw)
    require(type(current) is dict, 'recovery receipt must be an object')
    prefix = current.get('completed_prefix')
    status = current.get('prior_status', current.get('status'))
    phase = current.get('prior_phase', current.get('phase'))
    # Every final-cell update and the computational completion publication
    # precedes the closing anchor. A full prefix or any ambiguous receipt is
    # insufficient authority to start another preservation interval.
    return (current.get('schema') == 'worker36-attempt-v1' and
            type(status) is str and status in {'execution_blocked', 'measuring'} and
            type(phase) is str and phase in {'admission', 'source_runtime_preflight',
                                            'measurement', 'measurement_source_check'} and
            type(prefix) is list and len(prefix) < len(SCHEDULE) and
            all(type(value) is int for value in prefix) and
            prefix == [item['cell'] for item in SCHEDULE[:len(prefix)]])


def recover_closing_anchor(root):
    """Use final/staged original deadline or positively prove preclosing."""
    from .verify import closing_anchor
    try:
        anchor = closing_anchor(root)
    except FileNotFoundError:
        try:
            anchor = closing_anchor(root, staged=True)
        except FileNotFoundError:
            if proven_preclosing(root):
                return None
            raise OSError('closing deadline unavailable after possible computational completion')
        except (IntegrityError, ValueError, KeyError, TypeError) as exc:
            # Atomic staging may be torn. Preserve those bytes as uncertainty,
            # not a committed-record contradiction or a replacement budget.
            raise OSError('uncommitted closing anchor cannot establish original deadline') from exc
        if anchor['preservation_started_monotonic'] > time.monotonic():
            raise OSError('uncommitted closing anchor start is not a past boundary')
    if anchor['preservation_started_monotonic'] > time.monotonic():
        raise IntegrityError('committed closing anchor start is not a past boundary')
    return anchor


def _preserve(attempt, destination, report, recovery_report, *, admission, admission_sha256,
             admission_provenance, admission_provenance_sha256, expected_head, expected_tree, expected_workflow_run):
    from .verify import verify_attempt, closing_phase
    from .transport import package_attempt
    install_memory_cap(); root = Path(attempt).resolve(); deadline = time.monotonic() + 600
    recovery_initial = {'schema': 'worker36-durable-preservation-v1', 'status': 'in_progress',
        'raw_attempt': str(root), 'transport_directory': str(Path(destination).absolute()),
        'retained_until': 'parent-verified-canonical-custody', 'no_cleanup': True,
        'custody': 'pending', 'classification': None, 'deadline_monotonic': None,
        'deadline_state': 'original_anchor_not_yet_recovered'}
    write_report(recovery_report, recovery_initial)
    failed = False; gate = None
    try:
        # Recover the original immutable deadline before status or mutable
        # receipt binding checks. Later terminalization never grants a new600.
        try:
            anchor = recover_closing_anchor(root)
        except Exception:
            # Existing but unreadable/invalid closing evidence cannot authorize
            # a replacement preservation budget when its anchor is unknown.
            deadline = time.monotonic()
            raise
        if anchor is not None:
            deadline = min(deadline, anchor['preservation_deadline_monotonic'])
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ResourceExceeded('shared preservation deadline exhausted before offline verification')
            signal.setitimer(signal.ITIMER_REAL, remaining)
        try:
            if shutil.disk_usage(root).free < 1024 ** 3:
                raise OSError('1GiB free preservation storage required')
        except OSError as storage_error:
            storage_error.worker36_failure = error_record(storage_error, 'preservation_storage_preflight')
            raise
        current = strict_json((root / 'receipt.json').read_bytes())
        if current.get('status') != 'execution_complete':
            blocked = RuntimeError('complete-evidence verification not applicable to incomplete execution')
            blocked.worker36_failure = current.get('failure') or {'status': current.get('status', 'execution_incomplete'),
                'category': 'incomplete_execution', 'phase': 'offline_verification',
                'error_type': 'IncompleteExecution', 'error': 'execution did not complete',
                'prior_status': current.get('status'), 'prior_phase': current.get('phase')}
            raise blocked
        closing_phase(root, current)
        verification = verify_attempt(root, trusted_admission_path=admission, trusted_admission_sha256=admission_sha256,
            expected_head=expected_head, expected_tree=expected_tree, trusted_provenance_path=admission_provenance,
            trusted_provenance_sha256=admission_provenance_sha256, expected_workflow_run=expected_workflow_run)
        write_report(report, verification)
    except BaseException as caught:
        failed = True; gate = getattr(caught, 'worker36_failure', None) or error_record(caught, 'offline_verification')
        terminal = terminalize(root, gate, secondary=getattr(caught, 'worker36_secondary_errors', []))
        gate = terminal['failure']
        record = {'schema': 'worker36-offline-gate-v1', 'complete': False, 'failure': gate,
                  'custody': 'pending', 'classification': None}
        try:
            Budget(root).write(root / 'verification-gate-failure.json', record)
        except Exception as failure:
            terminalize(root, gate, secondary=[error_record(failure, 'verification_failure_persistence')])
        try:
            write_report(report, record)
        except Exception as failure:
            terminalize(root, gate, secondary=[error_record(failure, 'external_verification_report')])
    # Independent preservation always follows; an offline gate failure is never
    # discarded into a successful step even if packaging succeeds.
    packaged = package_attempt(root, Path(destination), deadline_monotonic=deadline)
    if packaged['status'] != 'packaged':
        failed = True
    recovery = {'schema': 'worker36-durable-preservation-v1', 'status': 'failed' if failed else 'preserved_locally', 'raw_attempt': str(root),
                'transport_directory': str(Path(destination).absolute()), 'retained_until': 'parent-verified-canonical-custody',
                'no_cleanup': True, 'verification_failed': gate is not None, 'transport': packaged, 'deadline_monotonic': deadline,
                'classification': None, 'custody': 'pending' if not failed else 'blocked'}
    if failed and time.monotonic() < deadline:
        try:
            recovery['retained_inventory'] = recovery_inventory(root, destination)
        except Exception as failure:
            recovery['inventory_error'] = {'error_type': type(failure).__name__, 'error': str(failure)[:1024]}
    elif failed:
        recovery['retained_inventory'] = {'inventory_complete': False,
            'reason': 'original preservation deadline unavailable or exhausted; raw paths retained without rescanning'}
    write_report(recovery_report, recovery, replace=True)
    return int(failed)


def preserve(*args, **kwargs):
    root = Path(args[0] if args else kwargs['attempt'])
    old_handler = None; timer_owned = False; result = 1
    def expired(signum, frame):
        raise ResourceExceeded('local verification/preservation600-second deadline')
    try:
        old_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, expired); timer_owned = True
        signal.setitimer(signal.ITIMER_REAL, 600)
        result = _preserve(*args, **kwargs)
    except BaseException as caught:
        terminalize(root, getattr(caught, 'worker36_failure', None) or error_record(caught, 'preservation_boundary'),
                    secondary=getattr(caught, 'worker36_secondary_errors', []))
    finally:
        if timer_owned:
            try:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, old_handler)
            except BaseException as caught:
                terminalize(root, error_record(caught, 'preservation_timer_restoration'))
                result = 1
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('plan')
    measure_parser = commands.add_parser('measure')
    for name in ('attempt', 'admission', 'admission-sha256', 'admission-provenance', 'admission-provenance-sha256'):
        measure_parser.add_argument('--' + name, required=True)
    child = commands.add_parser('_cell'); child.add_argument('--attempt', required=True); child.add_argument('--cell', type=int, required=True)
    preserving = commands.add_parser('preserve')
    for name in ('attempt', 'destination', 'report', 'recovery-report', 'admission', 'admission-sha256',
                 'admission-provenance', 'admission-provenance-sha256', 'expected-head', 'expected-tree', 'expected-workflow-run'):
        preserving.add_argument('--' + name, required=True)
    args = parser.parse_args(argv)
    if args.command == 'plan':
        print(canonical({'admitted': False, 'schedule': SCHEDULE, 'resources': RESOURCES,
                         'maximum_evaluator_calls': 40, 'actual_evaluator_calls': 0, 'games': 0}).decode(), end='')
        return 0
    if args.command == 'measure':
        return measure(args.attempt, args.admission, args.admission_sha256, args.admission_provenance, args.admission_provenance_sha256)
    if args.command == '_cell':
        from .cell import run_cell
        try:
            run_cell(args.attempt, args.cell)
            return 0
        except BaseException as caught:
            failure = getattr(caught, 'worker36_failure', None) or error_record(caught, 'cell_source_runtime_preflight')
            print(canonical({'schema': 'worker36-child-boundary-failure-v1', 'failure': failure,
                             'cell': args.cell, 'classification': None}).decode(), file=sys.stderr, end='')
            return EXIT_CODES[failure['status']]
    return preserve(args.attempt, args.destination, args.report, args.recovery_report,
        admission=args.admission, admission_sha256=args.admission_sha256, admission_provenance=args.admission_provenance, admission_provenance_sha256=args.admission_provenance_sha256,
        expected_head=args.expected_head, expected_tree=args.expected_tree, expected_workflow_run=args.expected_workflow_run)
