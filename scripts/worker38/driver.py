"""One branch-safe, externally admitted Worker38 allocation; no default GO."""
from __future__ import annotations
import argparse
import math
import stat
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
                     strict_json, update_receipt, write_failure_receipt, loader_identity, loader_pin,
                     CONTRACT_SHA256, FINITE_PLAN_SHA256, SOURCE_MANIFEST_SHA256, STARTUP_RESOURCES, _runtime_details,
                     UPLOAD_AMENDMENT_SHA256, UPLOAD_CONTRACT_SHA256, UPLOAD_FINITE_PLAN_SHA256, UPLOAD_ADOPTION)
from .sources import read_manifest, restore, verify_files

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / 'experiments/worker38-synthetic-profile'
TEST_RECEIPT = EXPERIMENT / 'focused-preparation-receipt.json'
EXIT_CODES = {'integrity_invalid': 65, 'execution_incomplete': 74,
              'resource_incomplete': 75, 'execution_blocked': 78}
SUPERVISION_LIMITS = {'wall_seconds': 720, 'cpu_seconds': 720, 'address_space_bytes': 512 * 1024 ** 2,
                     'call_wall_seconds': 360, 'call_cpu_seconds': 360, 'output_log_limit_bytes': 63 * 1024 ** 2}


PRODUCTION_PATHS = frozenset({
    '.github/workflows/worker38-synthetic-profile.yml',
    '.github/actions/worker38-upload/action.yml',
    'scripts/worker_bootstrap_shared.sh', 'scripts/worker_bootstrap_shared.py',
    'scripts/worker37-bootstrap.sh', 'scripts/worker37_bootstrap.py',
    'scripts/worker38-bootstrap.sh', 'scripts/run_worker38_synthetic.py',
    'scripts/worker38/__init__.py', 'scripts/worker38/admission.py', 'scripts/worker38/common.py',
    'scripts/worker38/sources.py', 'scripts/worker38/supervision.py', 'scripts/worker38/cell.py',
    'scripts/worker38/driver.py', 'scripts/worker38/transport.py', 'scripts/worker38/verify.py',
})
TEST_PATHS = frozenset({'tests/test_worker37_bootstrap.py', 'tests/worker38_literal_fixtures.py',
    'tests/worker38_constructor_source.txt', 'tests/test_worker38_bootstrap_integration.py',
    'tests/test_worker38_core.py', 'tests/test_worker38_driver_integration.py',
    'tests/test_worker38_cell_integration.py', 'tests/test_worker38_supervision.py',
    'tests/test_worker38_transport.py', 'tests/test_worker38_verify_integration.py',
    'evidence-design/run-worker38-fixed-preparation.py',
    'evidence-design/worker38-fixed-fixtures.json'})


def required_diagnostic_paths(repo):
    repo = Path(repo)
    prefix = 'experiments/worker38-synthetic-profile/'
    manifest = read_manifest(repo / (prefix + 'comparator-source-manifest.json'))
    records = {prefix + name for name in ('PROTOCOL.md', 'INTEGRATION-CONTRACT.json',
        'FINITE-PREPARATION-PLAN.json', 'SOURCE-GROUNDING.json', 'comparator-source-manifest.json')}
    records |= {prefix + 'upload-amendment/' + name for name in ('AMENDMENT.md',
        'AMENDMENT-CONTRACT.json', 'FINITE-COVERAGE-AMENDMENT.json', 'SOURCE-OBSERVATION.json',
        'REPAIR-DISPOSITION.json', 'HANDOFF.json')}
    blobs = {prefix + 'inputs/comparator-7ac2f62c/' + entry['path'] + '.blob'
             for entry in manifest['files']}
    return set(PRODUCTION_PATHS) | records | blobs


def checked_source_paths(repo):
    return required_diagnostic_paths(repo) | set(TEST_PATHS)


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


def verify_checkout_binding(repo, head, tree):
    """Read the fixed detached HEAD; only shared shell invokes Git commands."""
    repo = Path(repo).resolve()
    metadata = repo / '.git'
    path = metadata / 'HEAD'
    require(metadata.is_dir() and not metadata.is_symlink() and path.is_file() and
            not path.is_symlink() and path.stat().st_size == 41, 'fixed detached checkout HEAD required')
    before = file_info(path)
    raw = path.read_bytes()
    require(raw == (head + '\n').encode('ascii') and file_info(path) == before,
            'detached checkout head changed')
    require(os.environ.get('WORKER38_HEAD') == head and os.environ.get('WORKER38_TREE') == tree and
            os.environ.get('WORKER38_SOURCE_DIRECTORY') == str(repo), 'retained shared-shell checkout binding')
    return head, tree


def read_admission(path, expected_sha256, repo, provenance_path=None, provenance_sha256=None):
    """Replay externally authenticated input semantics; create no reservation."""
    from .admission import verify_provenance, validate_descriptor
    raw = Path(path).read_bytes()
    require(len(raw) <= 65536 and sha(raw) == expected_sha256, 'external admission raw hash')
    go = strict_json(raw)
    validate_descriptor(go)
    require(provenance_path is not None, 'authenticated PR-event/API provenance required')
    require(re.fullmatch('[a-f0-9]{64}', provenance_sha256 or '') is not None and
            file_info(provenance_path)['sha256'] == provenance_sha256, 'authenticated provenance bytes drift')
    provenance = verify_provenance(provenance_path, path, expected_sha256)
    require(go['repository'] == REPOSITORY and go['preregistration_url'] == PREREGISTRATION and
            go['protocol_sha256'] == PROTOCOL_SHA256 and go['contract_sha256'] == CONTRACT_SHA256 and
            go['finite_plan_sha256'] == FINITE_PLAN_SHA256 and go['maximum_evaluator_calls'] == 40 and
            go['games'] == 0 and go['schedule'] == list(SCHEDULE), 'admission allocation mismatch')
    require(go['upload_amendment_sha256'] == UPLOAD_AMENDMENT_SHA256 and
            go['upload_contract_sha256'] == UPLOAD_CONTRACT_SHA256 and
            go['upload_finite_plan_sha256'] == UPLOAD_FINITE_PLAN_SHA256 and
            type(go['upload_adoption_comment_id']) is int and
            go['upload_adoption_comment_id'] == UPLOAD_ADOPTION, 'adopted upload supplement mismatch')
    require(go['runtime'] == RUNTIME and go['resources'] == RESOURCES and
            go['startup_resources'] == STARTUP_RESOURCES, 'frozen resource/runtime mismatch')
    require(go['loader_pin'] == loader_pin(go['loader_pin']), 'exact external loader pin required')
    require(go['runner'] == 'bandido-alcatraz-ci' and go['branch'] == 'research/worker38-synthetic-profile',
            'admission destination mismatch')
    require(os.environ.get('GITHUB_EVENT_NAME') == 'pull_request' and os.environ.get('GITHUB_RUN_ATTEMPT') == '1' and
            os.environ.get('GITHUB_RUN_ID') == provenance['workflow_run'] and
            provenance['workflow_attempt'] == '1' and provenance['admission_url'] == go['admission_url'],
            'first authenticated PR-body admission run required')
    head, tree = verify_checkout_binding(repo, go['head'], go['tree'])
    require(head == provenance['head'] and tree == provenance['tree'], 'exact diagnostic head/tree mismatch')
    expected_records = {'PROTOCOL.md': PROTOCOL_SHA256, 'INTEGRATION-CONTRACT.json': CONTRACT_SHA256,
                        'FINITE-PREPARATION-PLAN.json': FINITE_PLAN_SHA256,
                        'comparator-source-manifest.json': SOURCE_MANIFEST_SHA256,
                        'upload-amendment/AMENDMENT.md': UPLOAD_AMENDMENT_SHA256,
                        'upload-amendment/AMENDMENT-CONTRACT.json': UPLOAD_CONTRACT_SHA256,
                        'upload-amendment/FINITE-COVERAGE-AMENDMENT.json': UPLOAD_FINITE_PLAN_SHA256}
    for name, pin in expected_records.items():
        require(file_info(EXPERIMENT / name)['sha256'] == pin, 'registered metadata bytes drift: ' + name)
    require(go['source_manifest_sha256'] == SOURCE_MANIFEST_SHA256, 'comparator manifest pin')
    require(set(go['diagnostic_files_sha256']) == required_diagnostic_paths(repo), 'exact complete diagnostic pins required')
    for name, pin in go['diagnostic_files_sha256'].items():
        require(file_info(Path(repo) / name)['sha256'] == pin, 'diagnostic source drift: ' + name)
    tested = verify_test_receipt(repo, go['stub_test_receipt_sha256'])
    receipt_name = TEST_RECEIPT.relative_to(ROOT).as_posix()
    require(go['focused_source_receipt'] == {'path': receipt_name, **file_info(Path(repo) / receipt_name)},
            'focused source receipt exact path/size/hash mismatch')
    require(go['checked_file_sha256'] == tested['checked_file_sha256'], 'authenticated full checked-source map')
    require(go['postmerge_ci'] == provenance['postmerge_ci'] and
            go['current_source_ci'] == provenance['current_source_ci'], 'authenticated routine CI prerequisites')
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
            if key == 'phase' and value.get('schema') == 'worker38.supervision.v1' and type(value.get(key)) is dict:
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


def terminalize(root, primary, *, counts=None, secondary=(), deadline=None, failure_state=None):
    """Reduce surviving evidence first; persistence errors cannot erase it."""
    preservation_check(deadline)
    failure_state = {} if failure_state is None else failure_state
    failure_state.update(primary=primary, counts=counts)
    root = Path(root); counts = counts if counts is not None else reconcile_prefix(root)
    failure_state['counts'] = counts
    preservation_check(deadline)
    current, state = _prefix_read(root, root / 'receipt.json', counts['corrupt_evidence'], counts['unavailable_evidence'])
    failure_state['current'] = current
    preservation_check(deadline)
    primary, other = reduce_failure(primary, counts, current=current, additional=secondary)
    failure_state.update(primary=primary, counts=counts, secondary=other)
    require(primary is not None, 'terminal failure cause required')
    prior = {'prior_status': current.get('prior_status', current.get('status')),
             'prior_phase': current.get('prior_phase', current.get('phase'))} if isinstance(current, dict) else {}
    try:
        if state != 'present':
            raise OSError('main receipt unavailable for replacement: ' + state)
        update = {**current, **counts, **prior, 'status': primary['status'], 'phase': primary['phase'], 'failure': primary,
                  'secondary_errors': other, 'error_type': primary['error_type'], 'error': primary['error'],
                  'custody': 'pending', 'classification': None}
        preservation_check(deadline)
        Budget(root).write(root / 'receipt.json', update, replace=True)
        preservation_check(deadline)
        return update
    except Exception as write_error:
        primary, other = reduce_failure(primary, counts, current=current,
            additional=[*other, error_record(write_error, 'terminal_receipt_persistence')])
        failure_state.update(primary=primary, counts=counts, secondary=other)
        preservation_check(deadline)
        record = {'schema': 'worker38-terminal-failure-v1', **counts, **prior, **primary, 'failure': primary,
                  'secondary_errors': other[:12],
                  'custody': 'pending', 'classification': None, 'original_receipt_bytes_preserved': True}
        try:
            preservation_check(deadline)
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
    root = Path(root).absolute()
    cache = Path(os.environ.get('RUNNER_TOOL_CACHE', ''))
    durable = cache / 'worker38-synthetic-profile'
    allocation = durable / 'allocations' / 'worker38-synthetic-profile-01'
    run = provenance['workflow_run']
    require(type(run) is str and re.fullmatch('[1-9][0-9]{0,19}', run), 'workflow run identity')
    require(cache.is_absolute() and cache.resolve() == cache and
            durable == Path(provenance['durable_root']) and root == Path(provenance['attempt_path']) and
            root == allocation / ('run-' + run + '-attempt-1'),
            'authenticated fixed allocation attempt path required')
    for directory in (durable, durable / 'allocations', allocation, root):
        observed = directory.stat()
        require(directory.is_dir() and not directory.is_symlink() and directory.resolve() == directory and
                observed.st_uid == os.getuid() and stat.S_IMODE(observed.st_mode) == 0o700,
                'authenticated private runner-owned evidence directory required')
    require((allocation / 'reservation.txt').is_file() and not (allocation / 'reservation.txt').is_symlink(),
            'existing consumed reservation required')
    require(not root.is_relative_to(ROOT.resolve()), 'attempt must be outside checkout')
    # RUNNER_TEMP need not cross the credential-free boundary: shared startup
    # proved nonoverlap; provenance retains the authenticated original path.
    temporary = provenance.get('runner_temp') or provenance.get('temporary')
    if temporary is not None:
        require(not root.is_relative_to(Path(temporary).resolve()), 'attempt must be outside runner temp')


class PreservationExpired(BaseException):
    """One-shot preservation expiry must bypass ordinary receipt retry handlers."""
    def __init__(self):
        super().__init__('original preservation deadline exhausted')
        self.worker38_failure = error_record(ResourceExceeded(str(self)), 'preservation_deadline')


def preservation_check(deadline):
    if deadline is not None and time.monotonic() >= deadline:
        raise PreservationExpired()


def arm_preservation_until(deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise PreservationExpired()
    signal.setitimer(signal.ITIMER_REAL, remaining)


def incoming_preservation_deadline(value):
    if type(value) is not str or re.fullmatch('[1-9][0-9]{0,17}', value) is None:
        raise OSError('original preservation monotonic cutoff in milliseconds unavailable or invalid')
    deadline = int(value) / 1000
    now = time.monotonic()
    if not math.isfinite(deadline) or deadline > now + 600:
        raise OSError('preservation handoff cannot establish the original600-second bound')
    preservation_check(deadline)
    return deadline


def publish_preservation_handoff(deadline):
    """Pair clock origins conservatively, then append one fixed output record."""
    boot = time.clock_gettime(time.CLOCK_BOOTTIME)
    monotonic = time.monotonic()
    require(type(deadline) in (int, float) and math.isfinite(deadline) and
            0 < deadline - monotonic <= 600, 'live original preservation cutoff required')
    mono_ms = math.floor(deadline * 1000)
    boot_ms = math.floor((boot + deadline - monotonic) * 1000)
    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip()
    require(re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', boot_id) is not None,
            'verified boot identity required for preservation handoff')
    raw_path = os.environ.get('GITHUB_OUTPUT')
    require(type(raw_path) is str and Path(raw_path).is_absolute(), 'GitHub step output path required')
    path = Path(raw_path)
    require(path.is_file() and not path.is_symlink() and path.parent.resolve() == path.parent,
            'existing non-symlink GitHub output file required')
    values = {'preservation_deadline_monotonic_ms': str(mono_ms),
              'preservation_deadline_boottime_ms': str(boot_ms), 'preservation_boot_id': boot_id}
    raw = ''.join(key + '=' + value + '\n' for key, value in values.items()).encode('ascii')
    preservation_check(deadline)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), 'regular GitHub output descriptor required')
        require(os.write(fd, raw) == len(raw), 'complete preservation handoff append required')
        os.fsync(fd)
    finally:
        os.close(fd)
    preservation_check(deadline)
    return values


def restore_timer_state(old_handler, phase, *, confirmation=None):
    """Attempt both restorations and both observations independently."""
    errors = []; timer_disabled = handler_restored = False
    for operation in (lambda: signal.setitimer(signal.ITIMER_REAL, 0),
                      lambda: signal.signal(signal.SIGALRM, old_handler)):
        try:
            operation()
        except BaseException as exc:
            errors.append(getattr(exc, 'worker38_failure', None) or error_record(exc, phase))
    try:
        timer_disabled = signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
    except BaseException as exc:
        errors.append(getattr(exc, 'worker38_failure', None) or error_record(exc, phase))
    try:
        handler_restored = signal.getsignal(signal.SIGALRM) == old_handler
    except BaseException as exc:
        errors.append(getattr(exc, 'worker38_failure', None) or error_record(exc, phase))
    confirmed = timer_disabled and handler_restored
    if confirmation is not None:
        confirmation.update(timer_disabled=timer_disabled, alarm_handler_restored=handler_restored,
                            alarm_restoration_confirmed=confirmed)
    if not confirmed:
        errors.append(error_record(IntegrityError('timer/handler restoration failed or unconfirmed'), phase))
    return [{**item, 'timer_disabled': timer_disabled, 'handler_restored': handler_restored,
             'restoration_confirmed': confirmed} for item in errors]


def failure_sidecar(root, primary, *, counts=None, secondary=(), deadline=None, current=None):
    """Reserved bounded marker only: never read, hash or reconcile raw evidence."""
    available = counts is not None
    saved = dict(counts or {})
    primary, other = reduce_failure(primary, saved, current=current, additional=secondary)
    require(primary is not None, 'failure marker requires a terminal cause')
    record = {'schema': 'worker38-terminal-failure-v1', **saved, **primary, 'failure': primary,
              'secondary_errors': other[:12], 'custody': 'pending', 'classification': None,
              'original_receipt_bytes_preserved': True,
              'count_evidence': 'last_available_reconciliation' if available else 'unavailable',
              'preservation_deadline_monotonic': deadline}
    try:
        write_failure_receipt(root, record, name='failure-receipt-parent-' + str(time.monotonic_ns()) + '.json')
    except BaseException as exc:
        later = getattr(exc, 'worker38_failure', None) or error_record(exc, 'terminal_sidecar_persistence')
        primary, other = reduce_failure(primary, saved, additional=[*other, later])
        record.update(**primary, failure=primary, secondary_errors=other[:12], terminal_durability='unconfirmed')
        try:
            print(canonical(record).decode(), file=sys.stderr, end='')
        except BaseException:
            pass
    return record


_COORDINATOR_SCOPE_TOKEN = object()


class CoordinatorTimerScope:
    """One privately acquired coordinator control scope, never a descriptor flag."""
    def __init__(self, deadline, runtime, token):
        require(token is _COORDINATOR_SCOPE_TOKEN, 'private coordinator acquisition required')
        require(type(deadline) in (int, float) and math.isfinite(deadline), 'original measurement deadline')
        self.deadline = deadline
        self.measurement_deadline = deadline
        self.preservation_deadline = None
        self.pid = os.getpid()
        self.runtime = runtime
        self.original_alarm = signal.getsignal(signal.SIGALRM)
        self.original_usr1 = signal.getsignal(signal.SIGUSR1)
        self.owned = False
        self.armed = False
        self.observations = []
        self.handler = self._expired

    def _expired(self, signum, frame):
        if self.preservation_deadline is not None:
            raise PreservationExpired()
        raise ResourceExceeded('independent original measurement deadline exhausted')

    def acquire(self):
        require(all(signal.getitimer(k) == (0.0, 0.0) for k in
                    (signal.ITIMER_REAL, signal.ITIMER_VIRTUAL, signal.ITIMER_PROF)),
                'occupied timer after idle runtime gate')
        self.owned = True
        signal.signal(signal.SIGALRM, self.handler)
        signal.signal(signal.SIGUSR1, self.handler)
        self._arm(self.measurement_deadline)

    def _arm(self, deadline):
        now = time.monotonic()
        remaining = deadline - now
        if remaining <= 0:
            if self.preservation_deadline is not None: raise PreservationExpired()
            raise ResourceExceeded('original measurement deadline exhausted before timer arm')
        # Millisecond floor plus one millisecond margin is conservative. It
        # cannot authorize any work after the independently checked deadline.
        duration = (math.floor(remaining * 1000) - 1) / 1000
        if duration <= 0:
            if self.preservation_deadline is not None: raise PreservationExpired()
            raise ResourceExceeded('no conservatively positive timer remainder')
        self.deadline = deadline
        self.last_requested = duration
        signal.setitimer(signal.ITIMER_REAL, duration)
        self.armed = True
        control = self.check_control()
        self.observations.append({'deadline': deadline, 'before': now,
                                  'after': time.monotonic(), 'requested': duration, **control})

    def check_control(self):
        require(self.owned and self.armed and os.getpid() == self.pid, 'coordinator timer ownership unavailable')
        before = time.monotonic()
        if before >= self.deadline:
            if self.preservation_deadline is not None: raise PreservationExpired()
            raise ResourceExceeded('original measurement deadline exhausted')
        countdown, interval = signal.getitimer(signal.ITIMER_REAL)
        after = time.monotonic()
        if after >= self.deadline:
            if self.preservation_deadline is not None: raise PreservationExpired()
            raise ResourceExceeded('original measurement deadline exhausted during timer observation')
        require(type(countdown) in (int, float) and math.isfinite(countdown) and
                0 < countdown <= self.last_requested and interval == 0 and before + countdown <= self.deadline,
                'owned countdown changed or cannot confirm original remaining bound')
        require(signal.getsignal(signal.SIGALRM) is self.handler and
                signal.getsignal(signal.SIGUSR1) is self.handler and
                signal.getitimer(signal.ITIMER_VIRTUAL) == (0.0, 0.0) and
                signal.getitimer(signal.ITIMER_PROF) == (0.0, 0.0), 'foreign coordinator timer or handler')
        return {'observed_countdown': countdown, 'observed_interval': interval,
                'observed_before': before, 'observed_after': after,
                'alarm_handler_confirmed': True, 'usr1_handler_confirmed': True,
                'other_timers_idle': True, 'owner_pid': self.pid}

    def check_runtime(self):
        self.check_control()
        result = _runtime_details()
        self.check_control()
        require(loader_pin(result['loader']) == loader_pin(self.runtime['loader']), 'coordinator runtime drift')
        return result

    def arm_preservation(self, deadline):
        require(self.owned, 'no timer scope for preservation')
        if self.preservation_deadline is not None:
            require(deadline == self.preservation_deadline, 'preservation interval cannot renew')
            self.check_control()
            return
        self.preservation_deadline = deadline
        self._arm(deadline)

    def close(self):
        if not self.owned: return []
        proof = {}
        errors = restore_timer_state(self.original_alarm, 'coordinator_timer_restoration', confirmation=proof)
        try:
            signal.signal(signal.SIGUSR1, self.original_usr1)
        except BaseException as exc:
            errors.append(error_record(exc, 'coordinator_usr1_restoration'))
        confirmed = False
        try:
            confirmed = signal.getsignal(signal.SIGUSR1) == self.original_usr1
        except BaseException as exc:
            errors.append(error_record(exc, 'coordinator_usr1_restoration'))
        if not confirmed:
            errors.append(error_record(IntegrityError('SIGUSR1 restoration failed or unconfirmed'),
                                       'coordinator_usr1_restoration'))
        proof.update(usr1_handler_restored=confirmed, restoration_confirmed=bool(proof.get('alarm_restoration_confirmed') and confirmed),
                     schema='worker38-coordinator-restoration-v1', owner_pid=self.pid,
                     measurement_deadline_monotonic=self.measurement_deadline,
                     preservation_deadline_monotonic=self.preservation_deadline,
                     measurement_work_after_close=False, no_measurement_after_close=True)
        self.restoration_proof = proof
        self.owned = False
        return errors


def enter_measurement_runtime(original_deadline):
    """Full idle shared gate under the already active external deadline."""
    if time.monotonic() >= original_deadline:
        raise ResourceExceeded('original measurement deadline exhausted before runtime gate')
    runtime = runtime_check()
    if time.monotonic() >= original_deadline:
        raise ResourceExceeded('original measurement deadline exhausted during runtime gate')
    scope = CoordinatorTimerScope(original_deadline, runtime, _COORDINATOR_SCOPE_TOKEN)
    try:
        scope.acquire()
    except BaseException as exc:
        exc.worker38_timer_scope = scope
        raise
    return runtime, scope


def read_startup_handoff(root, admission_hash, provenance_hash):
    path = root / 'startup-handoff.json'
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 4096,
            'bounded committed startup handoff required')
    raw = path.read_bytes(); require(len(raw) <= 4096, 'startup handoff bound')
    require(re.fullmatch('[0-9a-f]{64}', os.environ.get('WORKER38_HANDOFF_SHA256', '')) is not None and
            sha(raw) == os.environ['WORKER38_HANDOFF_SHA256'], 'shell-validated startup handoff bytes drift')
    value = strict_json(raw)
    keys = {'schema', 'consumer', 'boot_id', 'measurement_monotonic_ns', 'measurement_boottime_ns',
        'measurement_deadline_monotonic_ns', 'measurement_deadline_boottime_ns', 'attempt_path',
        'source_path', 'head', 'tree', 'workflow_run', 'workflow_attempt', 'admission_sha256',
        'provenance_sha256', 'runtime_sha256', 'source_map_sha256', 'restored_inventory_sha256',
        'startup_receipt_sha256'}
    require(type(value) is dict and set(value) == keys and value['schema'] == 'worker38-startup-handoff-v1'
            and value['consumer'] == 'worker38-synthetic-profile-v1', 'startup handoff schema')
    require(value['attempt_path'] == str(root) and value['source_path'] == str(ROOT) and
            value['admission_sha256'] == admission_hash and value['provenance_sha256'] == provenance_hash and
            value['workflow_run'] == os.environ.get('GITHUB_RUN_ID') and value['workflow_attempt'] == '1',
            'startup handoff destination binding')
    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip()
    require(value['boot_id'] == boot_id, 'startup handoff boot identity changed')
    for clock in ('monotonic', 'boottime'):
        start, end = value['measurement_' + clock + '_ns'], value['measurement_deadline_' + clock + '_ns']
        require(type(start) is int and type(end) is int and 0 < start < end < 10 ** 20 and
                end - start == 1800 * 10 ** 9, 'exact original measurement clock interval')
    mono_before = time.monotonic_ns()
    boot = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    now = time.monotonic_ns()
    require(mono_before <= now and value['measurement_monotonic_ns'] <= mono_before and
            value['measurement_boottime_ns'] <= boot, 'future measurement anchor')
    from .supervision import process_identity
    pid, start_ticks = process_identity(os.getpid())
    ticks = os.sysconf('SC_CLK_TCK')
    require(pid == os.getpid() and type(ticks) is int and ticks > 0 and type(start_ticks) is int and start_ticks > 0,
            'coordinator birth identity unavailable')
    birth_boot_floor = start_ticks * 10 ** 9 // ticks
    offset_upper = boot - mono_before
    anchor_offset = value['measurement_boottime_ns'] - value['measurement_monotonic_ns']
    require(value['measurement_boottime_ns'] <= birth_boot_floor and
            value['measurement_monotonic_ns'] <= birth_boot_floor - offset_upper,
            'measurement anchor cannot be proved earlier than coordinator birth')
    # BOOTTIME was sampled before MONOTONIC in the <=90s admission leaf.
    # Later suspension can tighten the shell deadline; never infer an extended
    # monotonic origin or silently accept an unrelated clock pair.
    require(0 <= offset_upper - anchor_offset <= 90 * 10 ** 9 and
            process_identity(os.getpid()) == (pid, start_ticks),
            'startup clock pair or coordinator birth identity inconsistent')
    if now >= value['measurement_deadline_monotonic_ns'] or boot >= value['measurement_deadline_boottime_ns']:
        raise ResourceExceeded('original handoff measurement deadline already exhausted')
    return value


def measure(attempt, admission, admission_sha256, admission_provenance, admission_provenance_sha256):
    from .admission import INPUT_NAMES
    from .supervision import PhaseBudget, run_cell_child, process_identity
    root = Path(attempt).absolute()
    require(root.is_dir() and not root.is_symlink() and root.resolve() == root and not (root / 'receipt.json').exists(),
            'existing reserved exclusive startup attempt required')
    budget = Budget(root)
    receipt = {'schema': 'worker38-attempt-v1', 'status': 'execution_blocked', 'phase': 'admission',
        'attempt_id': 'worker38-' + os.environ.get('GITHUB_RUN_ID', '') + '-1', 'attempt_path': str(root), 'preregistration_url': PREREGISTRATION,
        'admission_verified': False, 'admission_sha256': admission_sha256,
        'diagnostic_head': None, 'runner': os.environ.get('RUNNER_NAME'), 'workflow_run': os.environ.get('GITHUB_RUN_ID'),
        'workflow_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'), 'source_manifest_sha256': SOURCE_MANIFEST_SHA256,
        'resources': RESOURCES, 'schedule': list(SCHEDULE), 'maximum_evaluator_calls': 40, 'games': 0,
        'actual_starts': 0, 'actual_starts_upper_bound': 0, 'actual_returns': 0, 'confirmed_captures': 0,
        'current_cell': None, 'completed_prefix': [], 'custody': 'pending', 'classification': None,
        'supervisor_pid': os.getpid(), 'supervisor_start_ticks': process_identity(os.getpid())[1],
        'supervisor_clock_ticks': os.sysconf('SC_CLK_TCK')}
    phase_name = 'admission'; old_handler = None; primary_failure = None; pending_supervisor_failures = []
    timer_restoration_required = measurement_timer_owned = False
    preservation_deadline = None
    timer_scope = None
    preservation_timer_attempted = preservation_timer_confirmed = False
    handoff_attempted = False
    last_counts = {'actual_starts': 0, 'actual_starts_upper_bound': 0, 'pre_call_markers': 0,
                   'actual_returns': 0, 'confirmed_captures': 0, 'capture_gaps': [],
                   'corrupt_evidence': [], 'unavailable_evidence': [], 'retained_failures': []}

    def begin_preservation(first_failure_monotonic=None):
        nonlocal preservation_deadline, preservation_timer_attempted, preservation_timer_confirmed
        if preservation_timer_confirmed:
            preservation_check(preservation_deadline)
            return preservation_deadline
        if preservation_timer_attempted:
            raise OSError('original preservation timer installation is unconfirmed; no retry')
        preservation_timer_attempted = True
        now = time.monotonic()
        start = now if first_failure_monotonic is None else first_failure_monotonic
        require(type(start) in (int, float) and math.isfinite(start) and 0 < start <= now,
                'first preservation boundary must be an observed past monotonic instant')
        preservation_deadline = start + 600
        preservation_check(preservation_deadline)
        require(timer_scope is not None and timer_scope.owned, 'owned preservation control scope required')
        timer_scope.arm_preservation(preservation_deadline)
        preservation_timer_confirmed = True
        return preservation_deadline

    def supervisor_failure(observed):
        nonlocal pending_supervisor_failures, preservation_timer_attempted
        try:
            require(type(observed) is dict and 'first_failure_monotonic' in observed,
                    'supervisor original first-failure timestamp required')
            deadline = begin_preservation(observed['first_failure_monotonic'])
            pending_supervisor_failures.extend(_retained_failures(observed, 'first_supervisor_failure'))
            return deadline
        except BaseException as exc:
            preservation_timer_attempted = True
            try:
                exc.worker38_preservation_deadline = preservation_deadline
            except BaseException:
                pass
            raise

    def publish_once():
        nonlocal handoff_attempted
        if handoff_attempted:
            return
        handoff_attempted = True
        require(preservation_timer_confirmed and preservation_deadline is not None,
                'confirmed original preservation interval required for handoff')
        publish_preservation_handoff(preservation_deadline)

    def terminal_failure(primary, *, counts=None, secondary=()):
        nonlocal primary_failure, last_counts
        if counts is not None:
            last_counts = counts
        primary_failure, other = reduce_failure(primary, last_counts, additional=secondary)
        discovered = {'primary': primary_failure, 'counts': last_counts, 'secondary': other}
        try:
            if measurement_timer_owned:
                begin_preservation()
                publish_once()
            elif timer_restoration_required:
                raise OSError('measurement timer installation unconfirmed; bounded marker only')
            result = terminalize(root, primary_failure, counts=counts,
                                 secondary=other, deadline=preservation_deadline, failure_state=discovered)
            last_counts = {key: result[key] for key in last_counts if key in result}
        except BaseException as exc:
            primary_failure = discovered.get('primary') or primary_failure
            last_counts = discovered.get('counts') or last_counts
            other = discovered.get('secondary', other)
            later = getattr(exc, 'worker38_failure', None) or error_record(exc, 'failure_preservation')
            result = failure_sidecar(root, primary_failure, counts=last_counts,
                                     secondary=[*other, later], deadline=preservation_deadline, current=discovered.get('current'))
        primary_failure = result['failure']
        return result
    try:
        handoff = read_startup_handoff(root, admission_sha256, admission_provenance_sha256)
        phase = PhaseBudget.for_measurement(handoff['measurement_monotonic_ns'] / 10 ** 9)
        phase_name = 'source_runtime_preflight'
        runtime, timer_scope = enter_measurement_runtime(handoff['measurement_deadline_monotonic_ns'] / 10 ** 9)
        timer_restoration_required = timer_scope.owned
        measurement_timer_owned = timer_scope.armed
        old_handler = timer_scope.original_alarm
        receipt['measurement_anchor'] = handoff
        receipt['runtime_scope'] = {'idle_gate_passed': True, 'timer_owned': True,
                                    'original_deadline': timer_scope.measurement_deadline}
        budget.write(root / 'receipt.json', receipt)
        go, provenance = read_admission(admission, admission_sha256, ROOT, admission_provenance, admission_provenance_sha256)
        durable_location(root, provenance)
        require(go['head'] == handoff['head'] and go['tree'] == handoff['tree'], 'handoff head/tree drift')
        budget.write(root / 'external-admission.json', Path(admission).read_bytes(), raw=True)
        for name in (*INPUT_NAMES, Path(admission).name, Path(admission_provenance).name):
            require((root / 'admission-inputs' / name).read_bytes() == (Path(admission).parent / name).read_bytes(),
                    'retained authenticated input drift')
        budget.write(root / 'stub-test-receipt.json', TEST_RECEIPT.read_bytes(), raw=True)
        update_receipt(root, admission_verified=True, diagnostic_head=go['head'], diagnostic_tree=go['tree'])
        if shutil.disk_usage(root).free < 1024 ** 3:
            raise OSError('1GiB free attempt storage required')
        require(loader_pin(runtime['loader']) == go['loader_pin'], 'actual coordinator loader differs from external freeze')
        inherited = runtime['inherited_limits']
        require(inherited == go['inherited_limits'], 'unexpected inherited resource limits')
        require(resource.getrlimit(resource.RLIMIT_AS) == (512 * 1024 ** 2,) * 2, 'exact coordinator address-space ceiling')
        manifest = read_manifest(root / 'source-manifest.json')
        verify_files(root / 'restored', manifest)
        require(digest(manifest['files']) == handoff['restored_inventory_sha256'] and
                digest(go['checked_file_sha256']) == handoff['source_map_sha256'] and
                file_info(root / 'startup-receipt.json')['sha256'] == handoff['startup_receipt_sha256'] and
                file_info(root / 'runtime.json')['sha256'] == handoff['runtime_sha256'], 'retained startup evidence drift')
        budget.write(root / 'source-runtime-preflight.json', {'evaluator_starts': 0, 'runtime': runtime,
            'coordinator_address_space': list(resource.getrlimit(resource.RLIMIT_AS)), 'phase': phase_name,
            'restored_source_inventory': manifest['files'], 'diagnostic_files_sha256': go['diagnostic_files_sha256'],
            'measurement_anchor': handoff, 'timer_control': timer_scope.observations})
        phase_name = 'measurement'
        completed = []; total = dict.fromkeys(('legal_enumerations', 'previews', 'exit_geometry_checks'), 0)
        env = clean_environment(loader=runtime['loader'])
        for key in ('GH_TOKEN', 'GITHUB_TOKEN', 'ACTIONS_RUNTIME_TOKEN'):
            env.pop(key, None)
        last_result = None
        for identity in SCHEDULE:
            phase_name = 'measurement_source_check'
            timer_scope.check_runtime()
            verify_files(root / 'restored', manifest)
            for name, pin in go['diagnostic_files_sha256'].items():
                require(file_info(ROOT / name)['sha256'] == pin, 'diagnostic source drift after initial preflight')
            folder = root / 'cells' / f"{identity['cell']:02d}"
            require(not folder.exists(), 'cell cannot be retried'); budget.mkdir(folder)
            update_receipt(root, status='measuring', phase='measurement', current_cell=identity['cell'], completed_prefix=completed)
            phase_name = 'measurement'
            result = run_cell_child(root, identity['cell'], env, phase,
                output_budget_check=budget.check_raw_log, output_budget_exceptions=(ResourceExceeded,),
                on_terminal_failure=supervisor_failure,
                expected_inherited_limits={**go['inherited_limits'], 'RLIMIT_AS': [512 * 1024 ** 2] * 2})
            # Recover the child's typed failure or exit BEFORE any ordinary
            # parent evidence publication. A later cap/I/O error is secondary.
            if result.get('preservation_transition_attempted') is True and not preservation_timer_attempted:
                preservation_timer_attempted = True
            pending_supervisor_failures.extend(_retained_failures(result, 'current_supervisor_result'))
            if pending_supervisor_failures:
                begin_preservation()
            counts = reconcile_prefix(root); last_counts = counts
            primary_failure, secondary = reduce_failure(None, counts, additional=pending_supervisor_failures)
            result['limits'] = dict(SUPERVISION_LIMITS)
            if phase.exhausted(phase.snapshot()):
                result.update(status='resource_incomplete', reason='measurement_phase_ceiling')
                primary_failure, secondary = reduce_failure(primary_failure, counts,
                    additional=_retained_failures(result, 'current_supervisor_result'))
            if primary_failure is not None:
                begin_preservation()
            budget.write(root / f"supervisor-cell-{identity['cell']:02d}.json", result)
            last_result = result
            if primary_failure is not None:
                terminal_failure(primary_failure, counts=counts, secondary=secondary)
                return 1
            child, _ = _prefix_read(root, folder / 'cell-receipt.json', counts['corrupt_evidence'], counts['unavailable_evidence'])
            if child is None or child.get('status') != 'complete':
                terminal_failure({'status': 'execution_incomplete', 'category': 'supervision', 'phase': phase_name,
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
        counts = reconcile_prefix(root); last_counts = counts
        primary_failure, secondary = reduce_failure(None, counts)
        if primary_failure is not None:
            terminal_failure(primary_failure, counts=counts, secondary=secondary)
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
        phase_name = 'closing_proof_preservation'
        begin_preservation(preservation_started)
        publish_once()
        budget.write(root / 'measurement-phase-close.json', {
            'schema': 'worker38-measurement-phase-close-v1', 'phase': closed,
            'computational_receipt': {'path': 'receipt.json', **file_info(root / 'receipt.json')},
            'includes_computational_receipt_publication': True, 'closing_proof_included_in_measurement': False,
            'measurement_work_after_close': False, 'no_measurement_after_close': True,
            'preservation_started_monotonic': preservation_started,
            'preservation_deadline_monotonic': preservation_deadline})
        if time.monotonic() >= preservation_deadline:
            raise ResourceExceeded('closing proof preservation deadline exhausted')
        return 0
    except BaseException as caught:
        timer_scope = getattr(caught, 'worker38_timer_scope', timer_scope)
        if timer_scope is not None:
            timer_restoration_required = timer_scope.owned
            measurement_timer_owned = timer_scope.armed
        later = getattr(caught, 'worker38_failure', None) or error_record(caught, phase_name)
        if not measurement_timer_owned:
            # No acquired timer means no safe authority for bulk reconciliation
            # or persistence. Keep admission's durable prefix; emit one bounded
            # fixed last-known record and let the shell retain its exit outcome.
            marker = {'schema': 'worker38-coordinator-early-failure-v1', **later, 'failure': later,
                      'actual_starts': 0, 'actual_starts_upper_bound': 0,
                      'classification': None, 'custody': 'pending',
                      'preservation_authority': 'unconfirmed_no_bulk_work'}
            try: os.write(2, canonical(marker))
            except BaseException: pass
            return 1
        terminal_failure(primary_failure or later,
            secondary=[*pending_supervisor_failures, *getattr(caught, 'worker38_secondary_errors', []),
                       *([later] if primary_failure else [])])
        return 1
    finally:
        if timer_restoration_required:
            restoration = timer_scope.close() if timer_scope is not None else []
            if restoration:
                terminal = failure_sidecar(root, primary_failure or restoration[0], counts=last_counts,
                    secondary=[*pending_supervisor_failures, *restoration], deadline=preservation_deadline)
                primary_failure = terminal['failure']
                return 1
            # One bounded positive restoration marker, never a recursive bulk
            # reconciliation after disabling the timer. Its absence blocks
            # offline completeness; it does not certify earlier custody.
            if primary_failure is None and timer_scope is not None and preservation_deadline is not None:
                try:
                    preservation_check(preservation_deadline)
                    proof = timer_scope.restoration_proof
                    require(proof['restoration_confirmed'] is True, 'positive restoration confirmation missing')
                    Budget(root).write(root / 'coordinator-restoration.json', proof)
                    preservation_check(preservation_deadline)
                except BaseException as exc:
                    later = getattr(exc, 'worker38_failure', None) or error_record(exc, 'coordinator_restoration_proof')
                    failure_sidecar(root, primary_failure or later, counts=last_counts,
                        secondary=[*pending_supervisor_failures, *([later] if primary_failure else [])],
                        deadline=preservation_deadline)
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
    return (current.get('schema') == 'worker38-attempt-v1' and
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


def preservation_writer_handoff(root, admission_exit_status, coordinator_exit_status, deadline,
                                 *, existing_observation=False):
    """Bind the closed shell's observed waits before any archive is produced."""
    from .supervision import process_identity
    from .verify import read
    root = Path(root)
    preservation_check(deadline)
    require(type(admission_exit_status) is int and 0 <= admission_exit_status <= 255,
            'observed admission wait status required')
    exit_path = root / 'admission-process-exit.txt'
    require(exit_path.is_file() and not exit_path.is_symlink() and exit_path.stat().st_size <= 512,
            'bounded admission process-exit observation required')
    exit_raw = exit_path.read_bytes()
    expected = ('schema=worker38-admission-process-exit-v1\nexit_status=' +
                str(admission_exit_status) + '\nadmission_process_returned=true\n').encode('ascii')
    require(exit_raw == expected, 'admission exit observation differs from actual shell wait')
    parent = process_identity(os.getppid())
    evidence = []
    if coordinator_exit_status == 'not_started':
        require(admission_exit_status != 0 and not (root / 'receipt.json').exists() and
                not (root / 'cells').exists(), 'zero-entry startup failure cannot have a coordinator prefix')
        startup_name = 'startup-failure.json'
        failure = read(root / startup_name)
        require(failure['evaluator_starts'] == failure['actual_starts_upper_bound'] == 0 and
                failure['admission_verified'] is False, 'startup failure zero-entry evidence required')
        coordinator_state = 'never_started'; coordinator_pid = coordinator_ticks = None
        coordinator_status = None; entries = 0
    else:
        require(type(coordinator_exit_status) is int and 0 <= coordinator_exit_status <= 255 and
                admission_exit_status == 0, 'observed coordinator wait status required')
        startup_name = 'startup-receipt.json'
        current = read(root / 'receipt.json')
        coordinator_pid, coordinator_ticks = current['supervisor_pid'], current['supervisor_start_ticks']
        require(type(coordinator_pid) is int and coordinator_pid > 1 and
                type(coordinator_ticks) is int and coordinator_ticks > 0 and coordinator_pid != os.getpid(),
                'original coordinator identity required')
        try:
            current_identity = process_identity(coordinator_pid)
        except FileNotFoundError:
            current_identity = None
        require(current_identity != (coordinator_pid, coordinator_ticks), 'original coordinator still live')
        coordinator_state = 'exited'; coordinator_status = coordinator_exit_status
        entries = current['actual_starts_upper_bound']
        require(type(entries) is int and 0 <= entries <= 40, 'bounded retained entry uncertainty required')
        evidence.append({'path': 'receipt.json', **file_info(root / 'receipt.json')})
        restoration_path = root / 'coordinator-restoration.json'
        if restoration_path.exists():
            restoration = read(restoration_path)
            require(restoration.get('restoration_confirmed') is True and restoration.get('timer_disabled') is True,
                    'coordinator restoration remains unconfirmed')
            evidence.append({'path': restoration_path.name, **file_info(restoration_path)})
        folders = sorted((root / 'cells').iterdir()) if (root / 'cells').exists() else []
        for folder in folders:
            require(folder.name in {f'{i:02d}' for i in range(1, 21)} and
                    folder.is_dir() and not folder.is_symlink(), 'unexpected owned-cell prefix')
            name = 'supervisor-cell-' + folder.name + '.json'
            supervisor = read(root / name)
            cleanup = supervisor.get('cleanup')
            require(type(cleanup) is dict and cleanup.get('complete') is True and
                    cleanup.get('remaining_pids') == [] and cleanup.get('errors') == [] and
                    supervisor.get('spawn_ownership_uncertain') is False and
                    type(supervisor.get('spawned')) is bool and
                    (supervisor['spawned'] is False or type(supervisor.get('returncode')) is int),
                    'owned cell cleanup or construction remains uncertain')
            evidence.append({'path': name, **file_info(root / name)})
    observation = {'schema': 'worker38-writer-exit-observation-v1',
        'workflow_run': os.environ.get('GITHUB_RUN_ID'), 'workflow_attempt': '1',
        'admission_exit_receipt': {'path': exit_path.name, **file_info(exit_path)},
        'admission_exit_status': admission_exit_status, 'coordinator_exit_status': coordinator_status,
        'coordinator_state': coordinator_state, 'coordinator_pid': coordinator_pid,
        'coordinator_start_ticks': coordinator_ticks, 'parent_pid': parent[0],
        'parent_start_ticks': parent[1], 'no_measurement_after_close': True,
        'preservation_deadline_monotonic': deadline}
    require(process_identity(os.getppid()) == parent, 'preservation parent identity changed')
    if existing_observation:
        require(read(root / 'writer-exit-observation.json') == observation,
                'preserved writer-exit observation changed')
    else:
        Budget(root).write(root / 'writer-exit-observation.json', observation)
    evidence = [{'path': 'writer-exit-observation.json', **file_info(root / 'writer-exit-observation.json')},
                {'path': startup_name, **file_info(root / startup_name)}, *evidence]
    preservation_check(deadline)
    return {'schema': 'worker38-upload-writer-handoff-v1',
        'attempt_id': 'worker38-' + os.environ.get('GITHUB_RUN_ID', '') + '-1',
        'preservation_pid': os.getpid(), 'coordinator_state': coordinator_state,
        'coordinator_pid': coordinator_pid, 'coordinator_start_ticks': coordinator_ticks,
        'evaluator_entries_upper_bound': entries, 'admission_exited': True,
        'owned_children_reaped': True, 'cleanup_confirmed': True,
        'no_further_writes': True, 'evidence': evidence}


def transport_failure(result):
    """Carry the transport's typed first/secondary causes across orchestration."""
    primary = result.get('primary_failure') or result.get('failure')
    require(type(primary) is dict and primary.get('status') in EXIT_CODES,
            'transport failure has no typed original cause')
    caught = RuntimeError('bounded transport operation failed')
    caught.worker38_failure = primary
    caught.worker38_secondary_errors = result.get('secondary_failures', [])
    raise caught


def startup_failure_causes(failure):
    observed = []
    require(type(failure) is dict and type(failure.get('secondary_failures')) is list,
            'typed startup failure record required')
    for item in [failure.get('primary_failure'), *failure['secondary_failures']]:
        require(type(item) is dict and type(item.get('classification')) is str and
                item['classification'] in EXIT_CODES and type(item.get('phase')) is str and
                type(item.get('code')) is str, 'typed startup failure cause required')
        status = item['classification']
        observed.append({'status': status, 'category': 'resource' if status == 'resource_incomplete' else
            'integrity' if status == 'integrity_invalid' else 'infrastructure',
            'phase': item['phase'], 'error_type': item.get('error_type', 'AdmissionFailure'),
            'error': item['code']})
    counts = {'actual_starts': 0, 'actual_starts_upper_bound': 0, 'actual_returns': 0,
              'confirmed_captures': 0, 'pre_call_markers': 0, 'capture_gaps': [],
              'corrupt_evidence': [], 'unavailable_evidence': [], 'retained_failures': []}
    primary, secondary = reduce_failure(None, counts, additional=observed)
    require(primary is not None, 'startup failure cannot fabricate a clean outcome')
    return primary, secondary, counts


def read_startup_failure_handoff(root, expected_sha256, deadline, expected_head, expected_tree, workflow_run,
                                 *, failure_state=None):
    """Recover the immutable zero-entry failure authority, never a new cutoff."""
    from .verify import read
    path = root / 'startup-failure-handoff.json'
    require(re.fullmatch('[0-9a-f]{64}', expected_sha256 or '') is not None and
            path.is_file() and not path.is_symlink() and path.stat().st_size <= 4096,
            'bounded committed startup failure handoff required')
    raw = path.read_bytes()
    require(len(raw) <= 4096 and sha(raw) == expected_sha256, 'startup failure handoff hash mismatch')
    value = strict_json(raw)
    keys = {'schema', 'consumer', 'origin', 'allocation_id', 'workflow_run', 'workflow_attempt',
        'attempt_path', 'source_path', 'head', 'tree', 'boot_id', 'first_failure_monotonic_ns',
        'preservation_deadline_monotonic_ns', 'clock_pair_boottime_ns', 'clock_pair_monotonic_ns',
        'preservation_deadline_boottime_ns', 'failure_receipt', 'shell_runtime',
        'runtime_observation_sha256', 'loader_pin', 'http_descriptors_closed', 'body_descriptors_closed',
        'failure_timer_restored', 'admitted', 'measurement_started', 'actual_entry_lower_bound',
        'actual_entry_upper_bound'}
    require(type(value) is dict and set(value) == keys and
            value['schema'] == 'worker38-startup-failure-handoff-v1' and
            value['consumer'] == 'worker38-synthetic-profile-v1' and value['origin'] == 'admission_failure' and
            value['allocation_id'] == 'worker38-synthetic-profile-01' and
            value['workflow_run'] == workflow_run == os.environ.get('GITHUB_RUN_ID') and
            value['workflow_attempt'] == '1' and value['attempt_path'] == str(root) and
            value['source_path'] == str(ROOT) and value['head'] == expected_head and value['tree'] == expected_tree,
            'startup failure identity mismatch')
    require(all(value[k] is True for k in ('http_descriptors_closed', 'body_descriptors_closed', 'failure_timer_restored'))
            and value['admitted'] is False and value['measurement_started'] is False and
            type(value['actual_entry_lower_bound']) is int and value['actual_entry_lower_bound'] == 0 and
            type(value['actual_entry_upper_bound']) is int and value['actual_entry_upper_bound'] == 0,
            'unconfirmed startup failure close/zero-entry boundary')
    clock_keys = ('first_failure_monotonic_ns', 'preservation_deadline_monotonic_ns',
        'clock_pair_boottime_ns', 'clock_pair_monotonic_ns', 'preservation_deadline_boottime_ns')
    require(all(type(value[k]) is int and 0 < value[k] < 10 ** 20 for k in clock_keys),
            'invalid startup failure clock type')
    first = value['first_failure_monotonic_ns']; cutoff = value['preservation_deadline_monotonic_ns']
    paired = value['clock_pair_monotonic_ns']
    require(cutoff - first == 600 * 10 ** 9 and first <= paired < cutoff and
            value['preservation_deadline_boottime_ns'] == value['clock_pair_boottime_ns'] + cutoff - paired and
            abs(deadline - cutoff // 10 ** 6 / 1000) < 1e-8,
            'startup failure original deadline mismatch')
    require(value['boot_id'] == Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip(),
            'startup failure boot identity changed')
    now = time.monotonic_ns(); boot = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    require(now >= paired and boot >= value['clock_pair_boottime_ns'], 'future startup failure clock pair')
    if now >= cutoff or boot >= value['preservation_deadline_boottime_ns']:
        raise PreservationExpired()
    for key, name, maximum in (('failure_receipt', 'startup-failure.json', 1024 ** 2),
                                ('shell_runtime', 'shell-runtime.txt', 4096)):
        bound = value[key]
        require(type(bound) is dict and set(bound) == {'path', 'size_bytes', 'sha256'} and
                bound['path'] == name and type(bound['size_bytes']) is int and 0 < bound['size_bytes'] <= maximum and
                (root / name).is_file() and not (root / name).is_symlink() and
                (root / name).stat().st_size == bound['size_bytes'] and
                file_info(root / name) == {k: bound[k] for k in ('size_bytes', 'sha256')},
                'startup failure retained evidence mismatch')
    failure = read(root / 'startup-failure.json')
    primary, secondary, counts = startup_failure_causes(failure)
    if failure_state is not None:
        failure_state.update(primary=primary, secondary=secondary, counts=counts)
    require(digest(failure['runtime']) == value['runtime_observation_sha256'] and
            loader_pin(loader_identity()) == loader_pin(value['loader_pin']),
            'startup failure exact runtime/loader binding mismatch')
    verify_checkout_binding(ROOT, expected_head, expected_tree)
    preservation_check(deadline)
    return value, failure


def _preserve_startup_failure(root, destination, report, recovery_report, *, handoff_sha256,
                              expected_head, expected_tree, expected_workflow_run, deadline,
                              admission_exit_status, coordinator_exit_status, failure_state):
    from .transport import package_attempt, seal_upload
    require(admission_exit_status == 79 and coordinator_exit_status == 'not_started',
            'only confirmed current startup-failure handoff may preserve without science admission')
    anchor, failure = read_startup_failure_handoff(root, handoff_sha256, deadline,
        expected_head, expected_tree, expected_workflow_run, failure_state=failure_state)
    recovery = {'schema': 'worker38-durable-preservation-v1', 'status': 'in_progress',
        'origin': 'admission_failure', 'raw_attempt': str(root), 'transport_directory': str(destination),
        'deadline_monotonic': deadline, 'startup_failure_handoff_sha256': handoff_sha256,
        'classification': None, 'custody': 'pending', 'no_cleanup': True,
        'scientific_verification': 'inapplicable_zero_entries'}
    write_report(recovery_report, recovery)
    writer = preservation_writer_handoff(root, admission_exit_status, coordinator_exit_status, deadline)
    primary, secondary, counts = failure_state['primary'], failure_state['secondary'], failure_state['counts']
    gate = {'schema': 'worker38-startup-preservation-gate-v1', 'failure': primary,
        'secondary_errors': secondary, 'scientific_verification': 'inapplicable_zero_entries',
        'actual_starts': 0, 'actual_starts_upper_bound': 0, 'classification': None, 'custody': 'pending'}
    Budget(root).write(root / 'startup-preservation-gate.json', gate)
    write_report(report, gate)
    preservation_check(deadline)
    packaged = package_attempt(root, Path(destination), deadline_monotonic=deadline)
    preservation_check(deadline)
    recovery.update(status='failed', transport=packaged, failure=primary, secondary_errors=secondary)
    write_report(recovery_report, recovery, replace=True)
    if packaged['status'] != 'packaged':
        transport_failure(packaged)
    sealed = seal_upload(os.environ['RUNNER_TOOL_CACHE'], expected_workflow_run,
                         deadline_monotonic=deadline, writer_handoff=writer)
    preservation_check(deadline)
    if sealed.get('status') != 'upload_ready':
        transport_failure(sealed)
    failure_state.update(upload_ready=True, sealed_incomplete=True)
    return 1


def _preserve(attempt, destination, report, recovery_report, *, admission, admission_sha256,
             admission_provenance, admission_provenance_sha256, expected_head, expected_tree,
             expected_workflow_run, deadline_monotonic, failure_state,
             admission_exit_status=None, coordinator_exit_status=None,
             startup_failure_handoff_sha256=None):
    from .verify import verify_retained_attempt, closing_phase
    from .transport import package_attempt, seal_upload
    install_memory_cap(); root = Path(attempt).resolve(); deadline = deadline_monotonic
    if startup_failure_handoff_sha256 is not None:
        return _preserve_startup_failure(root, destination, report, recovery_report,
            handoff_sha256=startup_failure_handoff_sha256, expected_head=expected_head,
            expected_tree=expected_tree, expected_workflow_run=expected_workflow_run,
            deadline=deadline, admission_exit_status=admission_exit_status,
            coordinator_exit_status=coordinator_exit_status, failure_state=failure_state)
    gate = None; bound_confirmed = False; recovery_started = False; counts = None; preservation_stopped = False
    writer_handoff = None

    def retain(caught, phase):
        nonlocal gate, counts, preservation_stopped
        preservation_stopped = preservation_stopped or isinstance(caught, PreservationExpired)
        later = getattr(caught, 'worker38_failure', None) or error_record(caught, phase)
        # Capture typed causes now; normalize an initial prerequisite only when
        # terminalize/sidecar knows what entry evidence is actually available.
        secondary = [*failure_state.get('secondary', []), *getattr(caught, 'worker38_secondary_errors', []),
                     *([later] if gate else [])]
        gate = gate or later
        failure_state.update(primary=gate, counts=counts, secondary=secondary, deadline=deadline)
        try:
            if preservation_stopped:
                raise PreservationExpired()
            if not bound_confirmed:
                raise OSError('original preservation bound unavailable; marker only')
            preservation_check(deadline)
            counts = reconcile_prefix(root)
            failure_state['counts'] = counts
            terminal = terminalize(root, gate, counts=counts, secondary=secondary, deadline=deadline, failure_state=failure_state)
        except BaseException as persistence_error:
            gate = failure_state.get('primary') or gate
            counts = failure_state.get('counts') or counts
            secondary = failure_state.get('secondary', secondary)
            preservation_stopped = preservation_stopped or isinstance(persistence_error, PreservationExpired)
            extra = getattr(persistence_error, 'worker38_failure', None) or error_record(persistence_error, 'offline_failure_persistence')
            terminal = failure_sidecar(root, gate, counts=counts,
                secondary=[*secondary, extra], deadline=deadline, current=failure_state.get('current'))
        gate = terminal['failure']
        failure_state.update(primary=gate, counts=counts, secondary=terminal.get('secondary_errors', secondary))
        return terminal

    try:
        preservation_check(deadline)
        # Recover immutable final/staged timing before mutable receipt binding,
        # loader/admission hashing or optional preservation-report publication.
        anchor = recover_closing_anchor(root)
        if anchor is not None:
            deadline = min(deadline, anchor['preservation_deadline_monotonic'])
        failure_state['deadline'] = deadline
        preservation_check(deadline)
        arm_preservation_until(deadline)
        bound_confirmed = True
        preservation_check(deadline)
        go, _ = read_admission(admission, admission_sha256, ROOT,
                               admission_provenance, admission_provenance_sha256)
        require(loader_pin(loader_identity()) == go['loader_pin'],
                'actual offline loader differs from external freeze')
        if admission_exit_status is not None:
            writer_handoff = preservation_writer_handoff(root, admission_exit_status,
                                                         coordinator_exit_status, deadline)
        preservation_check(deadline)
        recovery_initial = {'schema': 'worker38-durable-preservation-v1', 'status': 'in_progress',
            'raw_attempt': str(root), 'transport_directory': str(Path(destination).absolute()),
            'retained_until': 'parent-verified-canonical-custody', 'no_cleanup': True,
            'custody': 'pending', 'classification': None, 'deadline_monotonic': deadline,
            'deadline_state': 'original_handoff_reconciled_with_anchor'}
        write_report(recovery_report, recovery_initial); recovery_started = True
        preservation_check(deadline)
        try:
            if shutil.disk_usage(root).free < 1024 ** 3:
                raise OSError('1GiB free preservation storage required')
        except OSError as storage_error:
            storage_error.worker38_failure = error_record(storage_error, 'preservation_storage_preflight')
            raise
        current = strict_json((root / 'receipt.json').read_bytes())
        if current.get('status') != 'execution_complete':
            blocked = RuntimeError('complete-evidence verification not applicable to incomplete execution')
            blocked.worker38_failure = current.get('failure') or {'status': current.get('status', 'execution_incomplete'),
                'category': 'incomplete_execution', 'phase': 'offline_verification',
                'error_type': 'IncompleteExecution', 'error': 'execution did not complete',
                'prior_status': current.get('status'), 'prior_phase': current.get('phase')}
            raise blocked
        closing_phase(root, current)
        preservation_check(deadline)
        verification = verify_retained_attempt(root, admission_sha256=admission_sha256,
            provenance_sha256=admission_provenance_sha256, expected_head=expected_head,
            expected_tree=expected_tree, expected_workflow_run=expected_workflow_run)
        preservation_check(deadline)
        write_report(report, verification)
        preservation_check(deadline)
    except BaseException as caught:
        retain(caught, 'offline_verification')
        if preservation_stopped or not bound_confirmed or time.monotonic() >= deadline:
            return 1
        record = {'schema': 'worker38-offline-gate-v1', 'complete': False, 'failure': gate,
                  'custody': 'pending', 'classification': None}
        try:
            preservation_check(deadline)
            Budget(root).write(root / 'verification-gate-failure.json', record)
            preservation_check(deadline)
            write_report(report, record)
            preservation_check(deadline)
        except BaseException as failure:
            retain(failure, 'verification_failure_persistence')
            if preservation_stopped or time.monotonic() >= deadline:
                return 1
    # The same original remaining interval bounds the separate packaging gate.
    preservation_check(deadline)
    if writer_handoff is not None and gate is not None:
        # Our terminal reducer may have updated the main receipt. Reconfirm
        # its exact current bytes and all cleanup facts before sealing failure
        # evidence, while preserving the original immutable exit observation.
        writer_handoff = preservation_writer_handoff(root, admission_exit_status,
            coordinator_exit_status, deadline, existing_observation=True)
    packaged = package_attempt(root, Path(destination), deadline_monotonic=deadline)
    preservation_check(deadline)
    failed = gate is not None or packaged['status'] != 'packaged'
    if packaged['status'] != 'packaged' and gate is None:
        observed = [packaged.get('primary_failure'), *packaged.get('secondary_failures', [])]
        observed = [item for item in observed if item is not None]
        if not observed:
            observed = [packaged.get('failure') or error_record(IntegrityError('transport lacks typed failure evidence'), 'offline_preservation')]
        gate, later = reduce_failure(gate, counts or {}, additional=observed)
        failure_state.update(primary=gate, secondary=[*failure_state.get('secondary', []), *later])
    recovery = {'schema': 'worker38-durable-preservation-v1', 'status': 'failed' if failed else 'preserved_locally',
        'raw_attempt': str(root), 'transport_directory': str(Path(destination).absolute()),
        'retained_until': 'parent-verified-canonical-custody', 'no_cleanup': True,
        'verification_failed': gate is not None, 'transport': packaged, 'deadline_monotonic': deadline,
        'classification': None, 'custody': 'blocked' if failed else 'pending'}
    if failed:
        preservation_check(deadline)
        try:
            recovery['retained_inventory'] = recovery_inventory(root, destination)
        except Exception as failure:
            recovery['inventory_error'] = {'error_type': type(failure).__name__, 'error': str(failure)[:1024]}
        preservation_check(deadline)
    write_report(recovery_report, recovery, replace=recovery_started)
    preservation_check(deadline)
    if writer_handoff is not None and packaged['status'] == 'packaged':
        # The seal precedes final restoration. Only preserve() can turn its
        # positive result into an exit accepted by the fixed shell caller.
        sealed = seal_upload(os.environ['RUNNER_TOOL_CACHE'], expected_workflow_run,
                             deadline_monotonic=deadline, writer_handoff=writer_handoff)
        preservation_check(deadline)
        if sealed.get('status') != 'upload_ready':
            transport_failure(sealed)
        failure_state['upload_ready'] = True
        failure_state['sealed_incomplete'] = failed
    return int(failed)


def preserve(*args, preservation_deadline_monotonic_ms=None, **kwargs):
    root = Path(args[0] if args else kwargs['attempt'])
    old_handler = None; timer_owned = False; result = 1; deadline = None
    state = {'primary': None, 'counts': None, 'deadline': None}
    def expired(signum, frame):
        raise PreservationExpired()
    try:
        deadline = incoming_preservation_deadline(preservation_deadline_monotonic_ms)
        state['deadline'] = deadline
        if kwargs.get('admission_exit_status') is not None:
            # The shell's original remaining-time timeout already bounds this
            # idle shared gate. No timer owned by this process exists yet.
            runtime_check()
            preservation_check(deadline)
        old_handler = signal.getsignal(signal.SIGALRM)
        timer_owned = True
        signal.signal(signal.SIGALRM, expired)
        preservation_check(deadline)
        arm_preservation_until(deadline)
        result = _preserve(*args, **kwargs, deadline_monotonic=deadline, failure_state=state)
    except BaseException as caught:
        later = getattr(caught, 'worker38_failure', None) or error_record(caught, 'preservation_boundary')
        state['upload_ready'] = False
        terminal = failure_sidecar(root, state['primary'] or later, counts=state['counts'],
            secondary=[*state.get('secondary', []), *getattr(caught, 'worker38_secondary_errors', []),
                       *([later] if state['primary'] else [])],
            deadline=state['deadline'], current=state.get('current'))
        state['primary'] = terminal['failure']
    finally:
        if timer_owned:
            restoration = restore_timer_state(old_handler, 'preservation_timer_restoration')
            if restoration:
                terminal = failure_sidecar(root, state['primary'] or restoration[0], counts=state['counts'],
                    secondary=[*state.get('secondary', []), *restoration], deadline=state['deadline'], current=state.get('current'))
                state['primary'] = terminal['failure']; result = 1
                state['upload_ready'] = False
    if state.get('upload_ready') is True:
        preservation_check(state['deadline'])
        return 2 if state.get('sealed_incomplete') else 0
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    measure_parser = commands.add_parser('measure')
    for name in ('attempt', 'admission', 'admission-sha256', 'admission-provenance', 'admission-provenance-sha256'):
        measure_parser.add_argument('--' + name, required=True)
    child = commands.add_parser('_cell'); child.add_argument('--attempt', required=True); child.add_argument('--cell', type=int, required=True)
    preserving = commands.add_parser('preserve')
    for name in ('attempt', 'destination', 'report', 'recovery-report',
                 'expected-head', 'expected-tree', 'expected-workflow-run',
                 'preservation-deadline-monotonic-ms', 'coordinator-exit-status'):
        preserving.add_argument('--' + name, required=True)
    preserving.add_argument('--admission-exit-status', required=True, type=int)
    for name in ('admission', 'admission-sha256', 'admission-provenance',
                 'admission-provenance-sha256', 'startup-failure-handoff-sha256'):
        preserving.add_argument('--' + name)
    for command in ('verify', 'timing-report'):
        checking = commands.add_parser(command, help='read-only externally supervised evidence verification')
        for name in ('attempt', 'trusted-admission', 'trusted-admission-sha256',
                     'trusted-provenance', 'trusted-provenance-sha256',
                     'expected-head', 'expected-tree', 'expected-workflow-run'):
            checking.add_argument('--' + name, required=True)
        if command == 'timing-report':
            checking.add_argument('--trusted-custody', required=True)
            checking.add_argument('--trusted-custody-sha256', required=True)
    args = parser.parse_args(argv)
    if args.command in ('verify', 'timing-report'):
        # External evidence work has no launch capability and creates no new
        # runner preservation allowance. Its caller supplies its own bound.
        install_memory_cap()
        from .verify import verify_attempt, timing_report, read
        try:
            result = verify_attempt(args.attempt,
                trusted_admission_path=args.trusted_admission,
                trusted_admission_sha256=args.trusted_admission_sha256,
                trusted_provenance_path=args.trusted_provenance,
                trusted_provenance_sha256=args.trusted_provenance_sha256,
                expected_head=args.expected_head, expected_tree=args.expected_tree,
                expected_workflow_run=args.expected_workflow_run)
            if args.command == 'timing-report':
                result = timing_report(result,
                    authenticated_custody_receipt=read(Path(args.trusted_custody)),
                    trusted_custody_path=args.trusted_custody,
                    trusted_custody_sha256=args.trusted_custody_sha256)
            raw = canonical(result)
            if len(raw) > RESOURCES['line_bytes']:
                raise ResourceExceeded('read-only verification report exceeds existing record cap')
            sys.stdout.buffer.write(raw)
            return 0
        except BaseException as caught:
            failure = error_record(caught, 'external_evidence_verification')
            print(canonical({'schema': 'worker38-offline-cli-failure-v1',
                'failure': failure, 'classification': None}).decode(), file=sys.stderr, end='')
            return EXIT_CODES[failure['status']]
    if args.command == 'measure':
        return measure(args.attempt, args.admission, args.admission_sha256, args.admission_provenance, args.admission_provenance_sha256)
    if args.command == '_cell':
        from .cell import run_cell
        try:
            run_cell(args.attempt, args.cell)
            return 0
        except BaseException as caught:
            failure = getattr(caught, 'worker38_failure', None) or error_record(caught, 'cell_source_runtime_preflight')
            print(canonical({'schema': 'worker38-child-boundary-failure-v1', 'failure': failure,
                             'cell': args.cell, 'classification': None}).decode(), file=sys.stderr, end='')
            return EXIT_CODES[failure['status']]
    coordinator_exit = args.coordinator_exit_status
    if coordinator_exit != 'not_started':
        require(re.fullmatch('[0-9]{1,3}', coordinator_exit) is not None,
                'fixed observed coordinator wait status required')
        coordinator_exit = int(coordinator_exit)
    admission_fields = (args.admission, args.admission_sha256, args.admission_provenance,
                        args.admission_provenance_sha256)
    require((args.startup_failure_handoff_sha256 is not None and all(x is None for x in admission_fields)) or
            (args.startup_failure_handoff_sha256 is None and all(type(x) is str and x for x in admission_fields)),
            'one closed preservation origin required')
    return preserve(args.attempt, args.destination, args.report, args.recovery_report,
        admission=args.admission, admission_sha256=args.admission_sha256, admission_provenance=args.admission_provenance, admission_provenance_sha256=args.admission_provenance_sha256,
        expected_head=args.expected_head, expected_tree=args.expected_tree, expected_workflow_run=args.expected_workflow_run,
        preservation_deadline_monotonic_ms=args.preservation_deadline_monotonic_ms,
        admission_exit_status=args.admission_exit_status, coordinator_exit_status=coordinator_exit,
        startup_failure_handoff_sha256=args.startup_failure_handoff_sha256)
