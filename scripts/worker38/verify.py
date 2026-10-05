"""Offline byte/equality/accounting verification. Never imports scientific code."""
from __future__ import annotations
import math
import os
import io
import re
import stat
import zipfile
from datetime import datetime, timezone
from urllib.parse import urlsplit
from pathlib import Path
from .common import (Budget, OP_CAPS, RESOURCES, RUNTIME, SCHEDULE, U_FLAGS, canonical, digest,
                     file_info, require, strict_json, sha, loader_pin, ResourceExceeded, HISTORICAL, REPOSITORY, PREREGISTRATION, PROTOCOL_SHA256,
                     CONTRACT_SHA256, FINITE_PLAN_SHA256, STARTUP_RESOURCES,
                     UPLOAD_AMENDMENT_SHA256, UPLOAD_CONTRACT_SHA256, UPLOAD_FINITE_PLAN_SHA256, UPLOAD_ADOPTION)
from .sources import read_manifest, verify_files
from .admission import (verify_provenance, validate_descriptor, INPUT_NAMES,
                        REQUIRED_PRODUCTION_PATHS, METADATA_PATHS, validate_handoff, HANDOFF_LINES)
from .transport import verify_provider_wrappers


def read(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= RESOURCES['line_bytes'],
            'bounded regular offline evidence file required')
    raw = path.read_bytes()
    require(len(raw) <= 8 * 1024 ** 2, 'offline JSON record exceeds frozen line bound')
    return strict_json(raw)


def rows(path):
    path = Path(path)
    cap = RESOURCES['trace_bytes'] if 'decision-traces' in path.parts else RESOURCES['evidence_bytes']
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= cap,
            'bounded regular JSONL evidence required')
    raw = path.read_bytes()
    require(len(raw) <= cap, 'JSONL artifact exceeds its frozen bound')
    lines = raw.splitlines()
    require(all(len(line) <= RESOURCES['line_bytes'] for line in lines), 'oversized JSONL record')
    return [strict_json(line) for line in lines]


def normalized_journal(path, folder):
    # Directory mapping is the ONLY normalization. Never remove arbitrary fields.
    return Path(path).read_bytes().replace(str(Path(folder)).encode(), b'<CELL>')


# Evidence validation below never imports or executes a restored module. The
# trusted files and their hashes are caller-supplied trust anchors, not evidence
# of remote authentication by themselves.
PRIMARY_MODULES = {'worker35_resources', 'run_quota_reserve_closure_development',
                   'benchmark_worker35_synthetic', 'bandido_alcatraz.quota_reserve_closure',
                   'bandido_alcatraz.quota_reserve_closure_reference', 'bandido_alcatraz.worker32.evidence'}
INITIAL_MODULES = ('bandido_alcatraz', 'bandido_alcatraz.board', 'bandido_alcatraz.game', 'bandido_alcatraz.model', 'bandido_alcatraz.moves', 'bandido_alcatraz.policies', 'bandido_alcatraz.quota_reserve_closure', 'bandido_alcatraz.quota_reserve_closure_reference', 'bandido_alcatraz.rules', 'bandido_alcatraz.setup', 'bandido_alcatraz.strategy', 'bandido_alcatraz.worker32', 'bandido_alcatraz.worker32.evidence', 'benchmark_worker35_synthetic', 'run_quota_reserve_closure_development', 'worker35_resources')
INHERITED_LIMITS = {'RLIMIT_AS': [-1, -1], 'RLIMIT_CORE': [0, -1], 'RLIMIT_CPU': [-1, -1], 'RLIMIT_DATA': [-1, -1], 'RLIMIT_FSIZE': [-1, -1], 'RLIMIT_MEMLOCK': [67108864, 67108864], 'RLIMIT_MSGQUEUE': [819200, 819200], 'RLIMIT_NICE': [0, 0], 'RLIMIT_NOFILE': [1048576, 1048576], 'RLIMIT_NPROC': [127622, 127622], 'RLIMIT_OFILE': [1048576, 1048576], 'RLIMIT_RSS': [-1, -1], 'RLIMIT_RTPRIO': [0, 0], 'RLIMIT_RTTIME': [-1, -1], 'RLIMIT_SIGPENDING': [127622, 127622], 'RLIMIT_STACK': [8388608, -1]}
CANONICAL_FOLDER = '1sQhQY3aKuHvQfyOTUIQjJGANCKOwKgEd'
FOCUSED_SOURCE_RECEIPT = 'experiments/worker38-synthetic-profile/focused-preparation-receipt.json'
CHECKED_TEST_PATHS = frozenset({
    'tests/test_worker37_bootstrap.py', 'tests/worker38_literal_fixtures.py',
    'tests/worker38_constructor_source.txt', 'tests/test_worker38_bootstrap_integration.py',
    'tests/test_worker38_core.py', 'tests/test_worker38_driver_integration.py',
    'tests/test_worker38_cell_integration.py', 'tests/test_worker38_supervision.py',
    'tests/test_worker38_transport.py', 'tests/test_worker38_verify_integration.py',
    'evidence-design/run-worker38-fixed-preparation.py', 'evidence-design/worker38-fixed-fixtures.json'})


def _number(value, maximum=None, *, positive=False):
    finite = False
    if type(value) in (int, float):
        try:
            finite = math.isfinite(value)
        except (OverflowError, ValueError):
            pass
    require(finite and (value > 0 if positive else value >= 0), 'invalid resource evidence')
    if maximum is not None and value >= maximum:
        raise ResourceExceeded('observed resource boundary exhausted: ' + str(maximum))
    return value



def _rss(value):
    """Descriptive same-process KiB high-water; never an RLIMIT_AS-derived cap."""
    require(type(value) is int and value >= 0, 'nonnegative integer high-water RSS required')
    return value


def _decision_metric(metric, *, scope):
    """Validate the unchanged original decision record, not a method interval."""
    keys = {'kind', 'pass', 'seed', 'ordinal', 'scope', 'wall_seconds', 'cpu_seconds',
            'peak_rss_kib', 'cost', 'status'}
    require(type(metric) is dict and set(metric) == keys, 'exact original P decision metric schema required')
    require(scope in ('candidate', 'reference') and
            canonical({key: metric[key] for key in ('kind', 'pass', 'seed', 'ordinal', 'scope', 'status')}) ==
            canonical({'kind': 'decision', 'pass': 2, 'seed': 11, 'ordinal': 1,
                       'scope': scope, 'status': 'returned'}), 'original P decision metric identity mismatch')
    for key in ('wall_seconds', 'cpu_seconds'):
        value = _number(metric[key])
        # Original artifact acceptance is inclusive at the fixed decision cap.
        # Its window encloses delegate/persistence/restoration work and is not
        # interchangeable with the narrower matched evaluator timing window.
        if value > RESOURCES['per_call'][scope][key]:
            raise ResourceExceeded('original P decision time ceiling exceeded: ' + key)
    return _rss(metric['peak_rss_kib'])


def _hash(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), 'invalid SHA256 pin')
    return value


def _external(path, expected_hash, root, bound):
    path = Path(path).absolute()
    require(not path.is_symlink() and not path.resolve().is_relative_to(root),
            'trust anchor must be external to raw attempt')
    require(path.is_file() and path.stat().st_size <= bound, 'external trust-anchor byte cap')
    info = file_info(path)
    require(info['size_bytes'] <= bound and info['sha256'] == _hash(expected_hash),
            'external trust-anchor bytes/hash mismatch')
    return path.resolve(), path.read_bytes()


def _anchor(path, expected_hash, root, bound, *, retained=False):
    if not retained:
        return _external(path, expected_hash, root, bound)
    # Only the two fixed, already committed same-attempt anchor copies are
    # allowed for preliminary local computation checks. No external trust or
    # final timing/custody classification follows from this path.
    path = Path(path).absolute()
    require(path in (root / 'admission-inputs' / 'admission.json',
                     root / 'admission-inputs' / 'provenance.json') and path.resolve() == path,
            'fixed retained admission/provenance path required')
    info = file_info(path)
    require(info['size_bytes'] <= bound and info['sha256'] == _hash(expected_hash),
            'retained startup anchor bytes/hash mismatch')
    raw = path.read_bytes()
    require(len(raw) == info['size_bytes'] and sha(raw) == expected_hash,
            'retained startup anchor changed during reading')
    return path, raw


def _admission(root, trusted_path, trusted_hash, head, tree, *, retained=False):
    path, raw = _anchor(trusted_path, trusted_hash, root, RESOURCES['receipt_bytes'], retained=retained)
    require((root / 'external-admission.json').read_bytes() == raw,
            'attempt admission differs from externally authenticated bytes')
    go = strict_json(raw)
    # Replay the closed Worker38 descriptor gate; it accepts no old readiness
    # workflow, artifact, source receipt or runtime authority.
    validate_descriptor(go)
    require(go['protocol_sha256'] == PROTOCOL_SHA256 and
            go['contract_sha256'] == CONTRACT_SHA256 and go['finite_plan_sha256'] == FINITE_PLAN_SHA256 and
            go['preregistration_url'] == PREREGISTRATION and
            canonical(go['startup_resources']) == canonical(STARTUP_RESOURCES) and
            canonical(go['inherited_limits']) == canonical(INHERITED_LIMITS) and
            go['cell_preflight_modules'] == sorted(INITIAL_MODULES), 'registered integration freeze mismatch')
    require(go['upload_amendment_sha256'] == UPLOAD_AMENDMENT_SHA256 and
            go['upload_contract_sha256'] == UPLOAD_CONTRACT_SHA256 and
            go['upload_finite_plan_sha256'] == UPLOAD_FINITE_PLAN_SHA256 and
            type(go['upload_adoption_comment_id']) is int and go['upload_adoption_comment_id'] == UPLOAD_ADOPTION,
            'adopted upload supplement binding mismatch')
    expected_metadata = {
        'experiments/worker38-synthetic-profile/PROTOCOL.md': PROTOCOL_SHA256,
        'experiments/worker38-synthetic-profile/INTEGRATION-CONTRACT.json': CONTRACT_SHA256,
        'experiments/worker38-synthetic-profile/FINITE-PREPARATION-PLAN.json': FINITE_PLAN_SHA256,
        'experiments/worker38-synthetic-profile/comparator-source-manifest.json': go['source_manifest_sha256'],
        'experiments/worker38-synthetic-profile/upload-amendment/AMENDMENT.md': UPLOAD_AMENDMENT_SHA256,
        'experiments/worker38-synthetic-profile/upload-amendment/AMENDMENT-CONTRACT.json': UPLOAD_CONTRACT_SHA256,
        'experiments/worker38-synthetic-profile/upload-amendment/FINITE-COVERAGE-AMENDMENT.json': UPLOAD_FINITE_PLAN_SHA256}
    require(all(go['diagnostic_files_sha256'].get(name) == pin for name, pin in expected_metadata.items()),
            'registered metadata source map mismatch')
    require(type(head) is str and re.fullmatch('[0-9a-f]{40}', head) and
            type(tree) is str and re.fullmatch('[0-9a-f]{40}', tree) and
            go['head'] == head and go['tree'] == tree, 'authenticated exact head/tree mismatch')
    stub_info = file_info(root / 'stub-test-receipt.json')
    require(stub_info['sha256'] == _hash(go['stub_test_receipt_sha256']) and
            go['focused_source_receipt'] == {'path': FOCUSED_SOURCE_RECEIPT, **stub_info},
            'frozen literal-stub test receipt bytes mismatch')
    require(file_info(root / 'source-manifest.json')['sha256'] == go['source_manifest_sha256'],
            'authenticated source-manifest pin mismatch')
    pins = go['diagnostic_files_sha256']
    checked = go['checked_file_sha256']
    manifest = read(root / 'source-manifest.json')
    staged_paths = {'experiments/worker38-synthetic-profile/inputs/comparator-7ac2f62c/' +
                    entry['path'] + '.blob' for entry in manifest['files']}
    require(set(pins) == set(REQUIRED_PRODUCTION_PATHS + METADATA_PATHS) | staged_paths and
            set(checked) == set(pins) | CHECKED_TEST_PATHS,
            'complete new diagnostic and preparation checked-source maps required')
    require(all(pins['experiments/worker38-synthetic-profile/inputs/comparator-7ac2f62c/' +
                    entry['path'] + '.blob'] == entry['sha256'] for entry in manifest['files']),
            'inert staged source pins differ from restored closure')
    stub = read(root / 'stub-test-receipt.json')
    require(stub['success'] is True and stub['checked_file_sha256'] == checked and
            FOCUSED_SOURCE_RECEIPT not in checked and
            all(checked.get(name) == value for name, value in pins.items()) and
            all(type(stub[key]) is int and stub[key] == 0 for key in
                ('candidate_evaluator_calls', 'reference_evaluator_calls', 'games',
                 'measurement_fixture_constructions', 'historical_source_imports', 'failures', 'errors')),
            'test receipt does not cover authenticated diagnostic sources')
    return go, {'trusted_admission_path': str(path), 'trusted_admission_sha256': trusted_hash,
                'expected_head': head, 'expected_tree': tree}


def _startup(root, admission, provenance, binding, manifest):
    """Authenticate the same-attempt zero-entry startup without running it."""
    for name, cap in (('startup-handoff.json', 4096), ('measurement-handoff.txt', 4096),
                      ('reservation.txt', 4096), ('startup-receipt.json', 2097152),
                      ('runtime.json', 2097152), ('restored-inventory.json', 2097152)):
        require(file_info(root / name)['size_bytes'] <= cap, 'bounded startup metadata required')
    handoff = validate_handoff(read(root / 'startup-handoff.json'))
    reservation = ('schema=worker38-observed-reservation-v1\nallocation_id=worker38-synthetic-profile-01\nrun_id=' +
                   provenance['workflow_run'] + '\nrun_attempt=1\nobserved_head=' + admission['head'] +
                   '\ndescriptor_binding=not_yet_validated\nevaluator_starts=0\nscientific_classification=null\n').encode()
    require((root / 'reservation.txt').read_bytes() == reservation, 'retained consumed reservation differs')
    startup = read(root / 'startup-receipt.json')
    runtime = read(root / 'runtime.json')
    require(handoff['head'] == binding['expected_head'] and handoff['tree'] == binding['expected_tree'] and
            handoff['workflow_run'] == provenance['workflow_run'] and handoff['workflow_attempt'] == '1' and
            handoff['attempt_path'] == provenance['attempt_path'] and
            handoff['admission_sha256'] == binding['trusted_admission_sha256'] and
            handoff['provenance_sha256'] == binding['trusted_provenance_sha256'] and
            handoff['runtime_sha256'] == file_info(root / 'runtime.json')['sha256'] and
            handoff['source_map_sha256'] == digest(admission['checked_file_sha256']) and
            handoff['restored_inventory_sha256'] == digest(manifest['files']) and
            handoff['startup_receipt_sha256'] == file_info(root / 'startup-receipt.json')['sha256'],
            'same-attempt startup handoff binding mismatch')
    require(read(root / 'restored-inventory.json') == manifest['files'], 'retained restoration inventory mismatch')
    handoff_raw = (root / 'startup-handoff.json').read_bytes()
    expected_text = 'version=worker38-handoff-v1\nhandoff_sha256=' + sha(handoff_raw) + '\n'
    expected_text += ''.join(name + '=' + str(handoff[name]) + '\n' for name in HANDOFF_LINES)
    require((root / 'measurement-handoff.txt').read_bytes() == expected_text.encode('ascii'),
            'shell startup handoff differs from authenticated original anchor')
    require(startup['schema'] == 'worker38-startup-receipt-v1' and
            startup['allocation_id'] == 'worker38-synthetic-profile-01' and
            startup['admission_verified'] is True and startup['classification'] is None and
            startup['scientific_classification'] is None and startup['phase'] == 'admission_complete' and
            startup['primary_failure'] is None and startup['secondary_failures'] == [] and
            startup['transition_attempted'] is False and startup['first_failure_monotonic'] is None and
            startup['preservation_deadline_monotonic'] is None and
            all(type(startup[key]) is int and startup[key] == 0 for key in
                ('evaluator_starts', 'actual_starts_upper_bound', 'historical_source_imports',
                 'measurement_fixture_constructions', 'games')) and
            startup['runtime'] == runtime and startup['restored_source_inventory'] == manifest['files'],
            'startup receipt is not a completed zero-entry admission')
    _number(startup['admission_CPU_seconds'], 90)
    require(canonical(startup['admission_CPU_limit']) == canonical([90, 90]),
            'admission leaf CPU backstop differs from90seconds')
    administrative = startup['administrative_deadlines']
    administrative_keys = {'startup_boottime_ns', 'startup_deadline_boottime_ns',
        'admission_deadline_boottime_ns', 'observed_leaf_entry_boottime_ns'}
    require(type(administrative) is dict and set(administrative) == administrative_keys and
            all(type(administrative[key]) is int and administrative[key] > 0 for key in administrative_keys),
            'complete typed original administrative deadline observations required')
    started = administrative['startup_boottime_ns']
    outer = administrative['startup_deadline_boottime_ns']
    leaf = administrative['admission_deadline_boottime_ns']
    entered = administrative['observed_leaf_entry_boottime_ns']
    anchor = handoff['measurement_boottime_ns']
    require(outer == started + 120 * 10 ** 9 and started <= entered <= anchor and
            entered < leaf <= outer and leaf <= entered + 90 * 10 ** 9,
            'administrative120/90second deadlines changed or are inconsistent')
    if anchor >= leaf or anchor >= outer:
        raise ResourceExceeded('admission handoff reached original administrative deadline')
    require(type(startup['free_bytes_before_source']) is int and
            startup['free_bytes_before_source'] >= 1024 ** 3, 'startup free-storage evidence missing')
    require(startup['requested_prefix'] == startup['completed_prefix'] == list(INPUT_NAMES) and
            type(startup['requests']) is list and len(startup['requests']) == 7 and
            set(startup['input_persistence']) == set(INPUT_NAMES), 'complete ordered seven-input startup required')
    total = 0
    for name, record in zip(INPUT_NAMES, startup['requests']):
        info = file_info(root / 'admission-inputs' / name)
        size = info['size_bytes']; total += size
        require(size <= 2097152 and record['name'] == name and type(record['status']) is int and
                record['status'] == 200 and
                all(type(record[key]) is int and record[key] == size for key in
                    ('received_bytes', 'buffered_bytes', 'retained_bytes', 'fsync_confirmed_bytes')) and
                all(record[key] is True for key in ('eof_confirmed', 'complete', 'close_confirmed', 'semantic_validated')) and
                not any(record.get(key) for key in ('incomplete_read', 'unknown_remainder', 'omission_reason')),
                'startup received/retained/durable byte accounting mismatch')
        persisted = startup['input_persistence'][name]
        require(persisted['sha256'] == info['sha256'] and
                all(type(persisted[key]) is int and persisted[key] == size for key in
                    ('size_bytes', 'buffered_bytes', 'fsync_confirmed_bytes')) and
                all(persisted[key] is True for key in ('write_complete', 'file_fsync_confirmed',
                    'directory_fsync_confirmed', 'readback_confirmed', 'close_confirmed')),
                'startup raw input lacks confirmed publication and readback')
    require(type(startup['response_body_bytes']) is int and startup['response_body_bytes'] == total <= 14680064,
            'startup aggregate response byte accounting mismatch')
    _shared_runtime(runtime, inherited_limits=INHERITED_LIMITS, loader_freeze=admission['loader_pin'])
    return handoff, runtime


def _shared_runtime(runtime, *, inherited_limits, loader_freeze):
    """Revalidate literal observations of the genuine idle shared gate."""
    expected = {'implementation': 'cpython', 'version': RUNTIME['version'],
        'inherited_limits': inherited_limits,
        'memory_cap': {'attempted': True, 'confirmed': True, 'readback': [536870912, 536870912]},
        'flags': {'optimize': 0, 'ignore_environment': 0, 'isolated': 0,
                  'no_site': 0, 'no_user_site': 1, 'dont_write_bytecode': 1},
        'state': {'limits': {**inherited_limits, 'RLIMIT_AS': [536870912, 536870912]},
                  'gc_enabled': True, 'gc_threshold': [700, 10, 10], 'profile_idle': True,
                  'trace_idle': True, 'threads': 1, 'timers': [[0.0, 0.0]] * 3},
        'memory_cap_restoration': 'retained_until_leaf_process_exit'}
    require(type(runtime) is dict and set(runtime) == set(expected) | {'files'} and
            canonical({key: runtime[key] for key in expected}) == canonical(expected),
            'startup shared runtime state differs from frozen policy')
    require(set(runtime['files']) == {'executable', 'library'}, 'startup loader files missing')
    for name, pin in (('executable', RUNTIME['executable_sha256']),
                      ('library', loader_freeze['library_sha256'])):
        record = runtime['files'][name]
        require(record['sha256'] == pin and record['mapped_identity_confirmed'] is True and
                type(record['size_bytes']) is int and record['size_bytes'] > 0 and
                type(record['device']) is int and record['device'] >= 0 and
                type(record['inode']) is int and record['inode'] > 0 and
                record['observed_mapping'] == {'major': os.major(record['device']),
                    'minor': os.minor(record['device']), 'inode': record['inode']},
                'startup stable file/mapped identity mismatch')
    require(runtime['files']['library']['size_bytes'] == loader_freeze['library_size_bytes'],
            'startup library size differs from exact admitted bytes')


def _runtime(runtime, *, child, loader_freeze, attempt_path=None, index=None):
    require({k: runtime[k] for k in RUNTIME} == RUNTIME and
            runtime['gc_enabled'] is True and runtime['gc_threshold'] == [700, 10, 10] and
            runtime['python_environment'] == {'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1'},
            'runtime/GC/environment evidence mismatch')
    require(canonical(runtime['effective_flags']) == canonical({'dont_write_bytecode': 1, 'no_user_site': 1,
            'ignore_environment': 0, 'isolated': 0, 'optimize': 0, 'no_site': 0}),
            'effective interpreter flags mismatch')
    require(type(runtime['executable']) is str and Path(runtime['executable']).is_absolute(),
            'runtime executable path missing')
    identity = runtime['loader']
    require(type(identity) is dict and identity.get('schema') == 'worker38-loader-identity-v1' and
            loader_pin(identity) == loader_freeze and runtime['executable'] == identity['executable_path'],
            'runtime loader identity differs from the authenticated loader freeze')
    inherited = {**INHERITED_LIMITS, 'RLIMIT_AS': [536870912, 536870912],
                 'RLIMIT_CPU': [720, 720]} if child else INHERITED_LIMITS
    require(canonical(runtime['inherited_limits']) == canonical(inherited),
            'fresh process inherited limit baseline mismatch')
    observed = runtime['shared_startup_observation']
    _shared_runtime(observed, inherited_limits=inherited, loader_freeze=loader_freeze)
    library = observed['files']['library']
    require(identity['library_inode'] == library['inode'] and
            identity['library_device'] == {'major': os.major(library['device']),
                                          'minor': os.minor(library['device'])},
            'shared gate and recorded loader mapping disagree')
    flags = runtime['flags']
    require(type(flags) is list and len(flags) >= 4 and all(type(x) is str for x in flags) and
            flags[1:3] == ['-B', '-s'] and Path(flags[3]).is_absolute() and
            flags[3].endswith('/scripts/run_worker38_synthetic.py'), 'exact -B -s invocation required')
    if child:
        require(runtime['address_space'] == [RESOURCES['address_space_bytes']] * 2 and
                flags[4:] == ['_cell', '--attempt', attempt_path, '--cell', str(index)],
                'child argv/address-space evidence mismatch')
    else:
        require(runtime['address_space'] == [RESOURCES['address_space_bytes']] * 2 and
                flags[4:5] == ['measure'], 'coordinator address-space/argv mismatch')
    return flags[3]


def _phase(phase, previous=None):
    require(phase['wall_limit_seconds'] == RESOURCES['measurement_wall_seconds'] and
            phase['cpu_limit_seconds'] == RESOURCES['measurement_cpu_seconds'], 'phase limits mismatch')
    for key in ('wall_seconds', 'cpu_seconds', 'parent_cpu_seconds', 'reaped_child_cpu_seconds', 'live_child_cpu_seconds'):
        _number(phase[key], 1800)
    require(phase['live_child_cpu_seconds'] == 0 and
            phase['cpu_seconds'] + 1e-9 >= phase['parent_cpu_seconds'] + phase['reaped_child_cpu_seconds'],
            'phase CPU reconciliation')
    if previous:
        _phase(previous)
        require(all(phase[k] + 1e-9 >= previous[k] for k in
                    ('wall_seconds', 'cpu_seconds', 'parent_cpu_seconds', 'reaped_child_cpu_seconds')),
                'nonmonotonic measurement-phase totals')


def closing_anchor(root, *, staged=False):
    """Recover a deadline; staged bytes can never prove completed execution."""
    path = Path(root) / ('measurement-phase-close.json.tmp' if staged else 'measurement-phase-close.json')
    raw = path.read_bytes()
    require(len(raw) <= RESOURCES['line_bytes'] and not path.is_symlink(), 'bounded regular closing proof required')
    value = strict_json(raw)
    require(type(value) is dict and value['schema'] == 'worker38-measurement-phase-close-v1' and
            value['includes_computational_receipt_publication'] is True and
            value['closing_proof_included_in_measurement'] is False and value['measurement_work_after_close'] is False and
            value['no_measurement_after_close'] is True,
            'closing measurement boundary proof mismatch')
    start = _number(value['preservation_started_monotonic'], positive=True)
    deadline = _number(value['preservation_deadline_monotonic'], positive=True)
    require(abs(deadline - start - 600) < 1e-8, 'same600-second preservation deadline required')
    return value


def closing_phase(root, receipt):
    """Success also binds original computational receipt and closing accounting."""
    value = closing_anchor(root)
    require(value['computational_receipt'] == {'path': 'receipt.json', **file_info(Path(root) / 'receipt.json')},
            'closing computational receipt binding mismatch')
    _phase(value['phase'], receipt['resource_totals']['phase'])
    return value


def _supervisor(root, identity, admission, receipt, previous):
    name = f"supervisor-cell-{identity['cell']:02d}"
    value = read(root / (name + '.json'))
    log = root / (name + '.log'); log_info = file_info(log)
    require(value['schema'] == 'worker38.supervision.v1' and value['status'] == 'completed' and
            value['reason'] == 'child_exit_zero' and
            value['primary_outcome'] == {'status': 'completed', 'reason': 'child_exit_zero'} and
            value['secondary_failures'] == [] and value['child_accounting_complete'] is True and
            value['phase_accounting_complete'] is True and value['spawned'] is True and
            type(value['pid']) is int and value['pid'] > 0 and value['parent_pid'] == receipt['supervisor_pid'] and
            value['parent_death_signal'] == 9 and value['returncode'] == value['exit_code'] == 0 and
            value['signal'] is None and value['scientific_returns_inferred'] is False and
            value['active_call_at_stop'] is None and value['errors'] == [], 'supervisor completion evidence mismatch')
    require(value.get('spawn_attempted') is True and value.get('spawn_initialization_complete') is True and
            value.get('spawn_ownership_uncertain') is False and value.get('spawn_discovery') == 'not_required' and
            type(value.get('spawn_recovered_pids')) is list and value['spawn_recovered_pids'] == [],
            'successful supervisor requires complete and certain spawn-ownership evidence')
    require('preservation_deadline_monotonic' in value and value['preservation_deadline_monotonic'] is None and
            all(value.get(key) is False for key in ('preservation_transition_attempted',
                'preservation_transition_complete', 'preservation_expired', 'preservation_blocked')) and
            'first_terminal_failure' not in value and 'preservation_boundary_failure' not in value,
            'successful supervisor cannot have missing or contradictory preservation-boundary evidence')
    require(value['cleanup'] == {'complete': True, 'sigkill_used': False, 'remaining_pids': [], 'errors': [], 'failure_details': []},
            'supervisor cleanup not clean')
    require(value['output_log'] == str(Path(receipt['attempt_path']) / (name + '.log')) and
            value['output_capture_mode'] == 'bounded_memory_then_post_cleanup_fsync' and
            value['output_bytes_preserved'] == value['output_bytes_observed'] == log_info['size_bytes'] and
            value['output_durable'] is True and value['output_overflow'] is False and
            value['output_prefix_gap'] is False and value['output_pipe_tail'] == 'eof_observed',
            'supervisor output inventory/durability gap')
    require(value['inherited_limits'] == {**admission['inherited_limits'],
            'RLIMIT_AS': [RESOURCES['address_space_bytes']] * 2}, 'supervisor inherited limit drift')
    expected_limits = {'wall_seconds': 720, 'cpu_seconds': 720, 'address_space_bytes': 512 * 1024 ** 2,
                       'call_wall_seconds': 360, 'call_cpu_seconds': 360,
                       'output_log_limit_bytes': 63 * 1024 ** 2}
    require(value['limits'] == expected_limits, 'supervisor configured protection limits mismatch')
    _number(value['wall_seconds'], 720); _number(value['child_cpu_seconds'], 720)
    _rss(value['child_high_water_rss_kib'])
    _number(value['cpu_tick_seconds'], positive=True)
    require(value['poll_seconds'] == .02, 'supervisor polling evidence drift')
    _phase(value['phase'], previous)
    return value


def verify_attempt(root, *, trusted_admission_path, trusted_admission_sha256,
                   expected_head, expected_tree, trusted_provenance_path,
                   trusted_provenance_sha256, expected_workflow_run, expected_workflow_attempt='1'):
    """Final acceptance boundary: both independently authenticated anchors stay external."""
    return _verify_attempt(root, trusted_admission_path=trusted_admission_path,
        trusted_admission_sha256=trusted_admission_sha256, expected_head=expected_head,
        expected_tree=expected_tree, trusted_provenance_path=trusted_provenance_path,
        trusted_provenance_sha256=trusted_provenance_sha256, expected_workflow_run=expected_workflow_run,
        expected_workflow_attempt=expected_workflow_attempt)


def verify_retained_attempt(root, *, admission_sha256, provenance_sha256,
                            expected_head, expected_tree, expected_workflow_run,
                            expected_workflow_attempt='1'):
    """Preliminary local preservation check; never supplies external acceptance."""
    root = Path(root).absolute()
    return _verify_attempt(root,
        trusted_admission_path=root / 'admission-inputs' / 'admission.json',
        trusted_admission_sha256=admission_sha256, expected_head=expected_head,
        expected_tree=expected_tree,
        trusted_provenance_path=root / 'admission-inputs' / 'provenance.json',
        trusted_provenance_sha256=provenance_sha256, expected_workflow_run=expected_workflow_run,
        expected_workflow_attempt=expected_workflow_attempt, _retained=True)


def _verify_attempt(root, *, trusted_admission_path, trusted_admission_sha256,
                   expected_head, expected_tree, trusted_provenance_path,
                   trusted_provenance_sha256, expected_workflow_run, expected_workflow_attempt='1', _retained=False):
    """Reconcile all preserved bytes against independently authenticated inputs.

    The caller must authenticate the admission/provenance outside this API. A
    filename, hash or asserted remote identity alone cannot perform that step.
    No runtime check or historical module import is performed on the verifier.
    """
    original = Path(root).absolute()
    require(not original.is_symlink(), 'attempt root may not be a symlink')
    root = original.resolve(); receipt = read(root / 'receipt.json')
    admission, binding = _admission(root, trusted_admission_path, trusted_admission_sha256,
                                    expected_head, expected_tree, retained=_retained)
    provenance_path, provenance_raw = _anchor(trusted_provenance_path, trusted_provenance_sha256,
                                               root, RESOURCES['receipt_bytes'], retained=_retained)
    provenance = verify_provenance(provenance_path, trusted_admission_path, trusted_admission_sha256)
    require(provenance['head'] == expected_head and provenance['tree'] == expected_tree and
            provenance['workflow_run'] == expected_workflow_run and type(expected_workflow_run) is str and
            expected_workflow_run.isdecimal() and provenance['workflow_attempt'] == expected_workflow_attempt == '1',
            'externally authenticated workflow/admission provenance mismatch')
    require(provenance['reviews'] == admission['reviews'],
            'authenticated raw prerequisite replay differs from the admitted reviews')
    preserved_auth = root / 'admission-inputs'
    for name in ('event.json', 'request-context.json', *INPUT_NAMES, Path(trusted_admission_path).name, provenance_path.name):
        require((preserved_auth / name).read_bytes() == (provenance_path.parent / name).read_bytes(),
                'preserved admission provenance/input bytes mismatch')
    require(receipt['schema'] == 'worker38-attempt-v1' and receipt['admission_verified'] is True and
            receipt['admission_sha256'] == trusted_admission_sha256 and
            receipt['diagnostic_head'] == expected_head and receipt['diagnostic_tree'] == expected_tree and
            all(receipt[k] == provenance[k] for k in ('attempt_id', 'attempt_path', 'workflow_run', 'workflow_attempt')) and
            Path(receipt['attempt_path']).is_absolute() and
            Path(receipt['attempt_path']).name == f"run-{expected_workflow_run}-attempt-1" and
            Path(receipt['attempt_path']).parent.name == 'worker38-synthetic-profile-01' and
            receipt['attempt_id'] == f'worker38-{expected_workflow_run}-1' and
            receipt['runner'] == admission['runner'] and receipt['preregistration_url'] == PREREGISTRATION and
            receipt['source_manifest_sha256'] == admission['source_manifest_sha256'] and
            receipt['resources'] == RESOURCES and receipt['games'] == 0 and
            receipt['phase'] == 'verification_pending' and receipt['current_cell'] is None and
            receipt['custody'] == 'pending' and receipt['classification'] is None and
            type(receipt['supervisor_pid']) is int and receipt['supervisor_pid'] > 0 and
            receipt['capture_gaps'] == [] and receipt['corrupt_evidence'] == [] and
            receipt['unavailable_evidence'] == [] and receipt['retained_failures'] == [] and not receipt.get('failure') and
            not receipt.get('secondary_errors') and not receipt.get('error') and not receipt.get('error_type'),
            'parent receipt identity/freeze/error gate')
    binding.update(root=str(root), trusted_provenance_path=str(provenance_path),
                   trusted_provenance_sha256=trusted_provenance_sha256,
                   expected_workflow_run=expected_workflow_run, expected_workflow_attempt=expected_workflow_attempt)
    require(receipt['status'] == 'execution_complete' and receipt['completed_prefix'] == list(range(1, 21)),
            'complete ordered allocation required; no partial timing analysis')
    require(receipt['actual_starts'] == receipt['actual_starts_upper_bound'] == receipt['pre_call_markers'] ==
            receipt['actual_returns'] == receipt['confirmed_captures'] == 40,
            'exact 40 starts/returns/captures required')
    require(receipt['schedule'] == list(SCHEDULE) and receipt['maximum_evaluator_calls'] == 40,
            'receipt allocation differs')
    closing = closing_phase(root, receipt)
    manifest = read_manifest(root / 'source-manifest.json'); verify_files(root / 'restored', manifest)
    handoff, startup_runtime = _startup(root, admission, provenance, binding, manifest)
    preflight = read(root / 'source-runtime-preflight.json')
    require(preflight['phase'] == 'source_runtime_preflight' and preflight['evaluator_starts'] == 0 and
            preflight['restored_source_inventory'] == manifest['files'] and
            preflight['diagnostic_files_sha256'] == admission['diagnostic_files_sha256'] and
            preflight['runtime']['inherited_limits'] == admission['inherited_limits'] and
            preflight['coordinator_address_space'] == [RESOURCES['address_space_bytes']] * 2,
            'parent source/runtime preflight differs from authenticated freeze')
    executable_script = _runtime(preflight['runtime'], child=False, loader_freeze=admission['loader_pin'])
    require(preflight['measurement_anchor'] == receipt['measurement_anchor'] == handoff and
            Path(executable_script).parent.parent == Path(handoff['source_path']) and
            receipt['runtime_scope'] == {'idle_gate_passed': True, 'timer_owned': True,
                'original_deadline': handoff['measurement_deadline_monotonic_ns'] / 10 ** 9},
            'coordinator changed its admitted original measurement authority')
    require(abs(closing['preservation_started_monotonic'] -
                (handoff['measurement_monotonic_ns'] / 10 ** 9 + closing['phase']['wall_seconds'])) < 1e-8,
            'preservation anchor is not the original finite computational close')
    initial_library = startup_runtime['files']['library']
    observed_loader = preflight['runtime']['loader']
    require(observed_loader['library_inode'] == initial_library['inode'] and
            observed_loader['library_device'] == {'major': os.major(initial_library['device']),
                                                  'minor': os.minor(initial_library['device'])},
            'admission/coordinator mapped library identity drift')
    timer = preflight['timer_control']
    require(type(timer) is list and len(timer) == 1 and type(timer[0]) is dict,
            'one observed original-deadline coordinator timer arm required')
    timer = timer[0]
    for key in ('deadline', 'before', 'after', 'requested', 'observed_countdown',
                'observed_before', 'observed_after'):
        _number(timer[key], positive=True)
    deadline = handoff['measurement_deadline_monotonic_ns'] / 10 ** 9
    require(timer['deadline'] == deadline and
            handoff['measurement_monotonic_ns'] / 10 ** 9 <= timer['before'] <=
            timer['observed_before'] <= timer['observed_after'] <= timer['after'] < deadline and
            0 < timer['requested'] <= deadline - timer['before'] and
            0 < timer['observed_countdown'] <= timer['requested'] and
            timer['observed_before'] + timer['observed_countdown'] <= deadline and
            type(timer['observed_interval']) in (int, float) and timer['observed_interval'] == 0 and
            type(timer['owner_pid']) is int and timer['owner_pid'] == receipt['supervisor_pid'] and
            all(timer[key] is True for key in
                ('alarm_handler_confirmed', 'usr1_handler_confirmed', 'other_timers_idle')),
            'coordinator timer was not confirmed within original measurement authority')
    restoration = read(root / 'coordinator-restoration.json')
    require(canonical(restoration) == canonical({
            'schema': 'worker38-coordinator-restoration-v1', 'owner_pid': receipt['supervisor_pid'],
            'measurement_deadline_monotonic': deadline,
            'preservation_deadline_monotonic': closing['preservation_deadline_monotonic'],
            'timer_disabled': True, 'alarm_handler_restored': True, 'alarm_restoration_confirmed': True,
            'usr1_handler_restored': True, 'restoration_confirmed': True,
            'measurement_work_after_close': False, 'no_measurement_after_close': True}),
            'coordinator timer and both handlers lack positive restoration confirmation')
    writer = read(root / 'writer-exit-observation.json')
    writer_keys = {'schema', 'workflow_run', 'workflow_attempt', 'admission_exit_receipt',
        'admission_exit_status', 'coordinator_exit_status', 'coordinator_state', 'coordinator_pid',
        'coordinator_start_ticks', 'parent_pid', 'parent_start_ticks', 'no_measurement_after_close',
        'preservation_deadline_monotonic'}
    require(type(writer) is dict and set(writer) == writer_keys and
            writer['schema'] == 'worker38-writer-exit-observation-v1' and
            writer['workflow_run'] == expected_workflow_run and writer['workflow_attempt'] == '1' and
            type(writer['admission_exit_status']) is int and writer['admission_exit_status'] == 0 and
            type(writer['coordinator_exit_status']) is int and writer['coordinator_exit_status'] == 0 and
            writer['coordinator_state'] == 'exited' and
            type(writer['coordinator_pid']) is int and writer['coordinator_pid'] == receipt['supervisor_pid'] and
            type(writer['coordinator_start_ticks']) is int and writer['coordinator_start_ticks'] > 0 and
            writer['coordinator_start_ticks'] == receipt['supervisor_start_ticks'] and
            type(writer['parent_pid']) is int and writer['parent_pid'] > 0 and
            type(writer['parent_start_ticks']) is int and writer['parent_start_ticks'] > 0 and
            writer['no_measurement_after_close'] is True and
            writer['preservation_deadline_monotonic'] == closing['preservation_deadline_monotonic'],
            'complete original writer-exit observation required')
    admission_exit = root / 'admission-process-exit.txt'
    require(admission_exit.read_bytes() == b'schema=worker38-admission-process-exit-v1\nexit_status=0\nadmission_process_returned=true\n' and
            writer['admission_exit_receipt'] == {'path': admission_exit.name, **file_info(admission_exit)},
            'shell observed admission exit bytes differ')
    inventory = Budget(root).inventory()
    require(receipt['file_inventory'] == [x for x in inventory if x['path'] not in ('receipt.json', 'measurement-phase-close.json', 'coordinator-restoration.json', 'writer-exit-observation.json')],
            'parent final evidence inventory mismatch')
    require(file_info(root / 'receipt.json')['size_bytes'] <= RESOURCES['receipt_bytes'], 'receipt cap')
    require(sum(x['size_bytes'] for x in inventory if x['path'] != 'receipt.json') <= 63 * 1024 ** 2,
            'raw evidence invaded terminal receipt reserve')
    require(not any('failure' in x['path'] or x['path'].endswith('.tmp') for x in inventory),
            'failure/unconfirmed evidence forbids successful verification')
    module_names = admission['cell_preflight_modules']
    pins = {entry['module']: entry for entry in manifest['files']}
    require(type(module_names) is list and module_names == sorted(set(module_names)) and
            PRIMARY_MODULES <= set(module_names) <= set(pins), 'authenticated cell module set invalid')
    module_records = {name: {'path': str(Path(receipt['attempt_path']) / 'restored' / pins[name]['path']),
                      'size_bytes': pins[name]['size_bytes'], 'sha256': pins[name]['sha256'],
                      'git_blob': pins[name]['git_blob']} for name in module_names}
    previous_phase = None; supervisors = []
    require(sum(x['size_bytes'] for x in inventory) <= RESOURCES['evidence_bytes'], 'raw cap')
    baselines = {}; journals = {}; cells = []; total = dict.fromkeys(OP_CAPS, 0)
    for identity in SCHEDULE:
        folder = root / 'cells' / f"{identity['cell']:02d}"
        cell = read(folder / 'cell-receipt.json')
        expected_call_modules = set(module_names) | ({'bandido_alcatraz.simulate'} if identity['condition'] == 'P' else set())
        require(expected_call_modules <= set(pins), 'call module not in authenticated source closure')
        call_module_records = {name: {'path': str(Path(receipt['attempt_path']) / 'restored' / pins[name]['path']),
                               'size_bytes': pins[name]['size_bytes'], 'sha256': pins[name]['sha256'],
                               'git_blob': pins[name]['git_blob']} for name in expected_call_modules}
        require(all(type(cell[k]) is type(v) and cell[k] == v for k, v in identity.items()) and cell['status'] == 'complete'
                and cell['hook_restored'] is True and cell['timer_restored'] is True and
                cell['actual_starts'] == cell['actual_starts_upper_bound'] == cell['pre_call_markers'] ==
                cell['invocation_attempts'] == cell['actual_returns'] == cell['confirmed_captures'] == 2,
                'incomplete cell/restoration gate')
        require(cell['schema'] == 'worker38-cell-receipt-v1' and cell['error_type'] is None and
                cell['error'] is None and cell['classification'] is None and cell['failure'] is None and
                cell['secondary_errors'] == [] and cell['phase'] == 'cell_complete' and
                set(cell['calls']) == {'candidate', 'reference'}, 'cell error/evidence gate')
        pre = read(folder / 'source-runtime-preflight.json')
        require(pre['phase'] == 'source_runtime_preflight' and pre['evaluator_starts'] == 0 and
                pre['modules'] == module_records, 'cell module path/hash inventory mismatch')
        require(_runtime(pre['runtime'], child=True, loader_freeze=admission['loader_pin'],
                         attempt_path=receipt['attempt_path'], index=identity['cell']) == executable_script,
                'child diagnostic executable path drift')
        require(pre['runtime']['loader'] == preflight['runtime']['loader'],
                'parent/child loader mapped identity mismatch')
        supervisor = _supervisor(root, identity, admission, receipt, previous_phase)
        previous_phase = supervisor['phase']; supervisors.append(supervisor)
        require(read(folder / 'active-call.json') == {'active': False}, 'call protection marker incomplete')
        _rss(cell['peak_rss_kib'])
        if identity['condition'] == 'U':
            require(canonical(read(folder / 'unmeasured-accounting.json')) == canonical(U_FLAGS), 'U accounting record missing/drift')
        begin = read(folder / 'cell-start.json'); end = read(folder / 'cell-boundaries.json')
        require(begin['observation_sha256'] == digest(begin['public_before']) and
                canonical(begin['public_before']) == canonical(end['public_after']) and
                begin['engine_before'] == end['engine_after'] and
                canonical(begin['conservation_before']) == canonical(end['conservation_after']) and
                begin['conservation_before']['inventory_count'] == 69 and end['equality'] is True and
                all(type(begin[k]) is type(v) and begin[k] == v for k, v in identity.items()), 'invented-state boundary gate')
        conservation = begin['conservation_before']
        require(set(conservation) == {'inventory_count', 'inventory_sha256', 'zones'} and
                set(conservation['zones']) == {'placed', 'collected', 'hand', 'draw', 'set_aside'},
                'complete invented-state conservation witness required')
        ids = [card for values in conservation['zones'].values() for card in values]
        require(len(ids) == len(set(ids)) == 69 and all(type(card) is str for card in ids) and
                all(values == sorted(values) for values in conservation['zones'].values()) and
                digest(sorted(ids)) == conservation['inventory_sha256'], 'all69 identity conservation mismatch')
        payloads = []
        for scope in ('candidate', 'reference'):
            start = read(folder / (scope + '-start.json'))
            payload = read(folder / (scope + '-return.json'))
            confirmed = read(folder / (scope + '-capture-confirmed.json'))
            path = folder / (scope + '-return.json')
            require(confirmed == {'path': path.relative_to(root).as_posix(), **file_info(path)},
                    'durable full return confirmation mismatch')
            require(cell['calls'][scope]['evidence'] == confirmed and cell['calls'][scope]['durable_capture_confirmed'] is True and
                    cell['calls'][scope]['start_marker_durable'] is True and
                    cell['calls'][scope]['invocation_attempted'] is True and cell['calls'][scope]['method_entered'] is True and
                    cell['calls'][scope]['returned'] is True and
                    not cell['calls'][scope].get('error') and not cell['calls'][scope].get('error_type'),
                    'cell receipt capture reconciliation')
            require(all(type(payload[k]) is type(v) and type(start[k]) is type(v) and payload[k] == v and start[k] == v for k, v in identity.items())
                    and payload['scope'] == start['scope'] == scope and
                    payload['observation_sha256'] == start['observation_sha256'] == begin['observation_sha256'],
                    'call identity mismatch')
            require(start['source_modules'] == payload['source_modules'] == call_module_records,
                    'per-call source module path/hash manifest mismatch')
            science = payload['scientific']
            require(type(science) is dict and set(science) == {'schema', 'input_before', 'input_after',
                    'roots', 'supply', 'tiers', 'guards', 'flags', 'chosen_index', 'chosen', 'rng_before', 'rng_after'} and
                    science['schema'] == 'worker35-scientific-v1' and
                    set(science['tiers']) == {'T0', 'F', 'T', 'C', 'final'} and
                    set(science['flags']) == {'reserve_filter_active', 'reserve_primary_tier_changed',
                    'closure_branch_selected', 'true_original_all_collect_crossover', 'reserve_filter_mediated_change'},
                    'complete canonical scientific object required')
            require(payload['scientific_sha256'] == digest(science) and
                    canonical(science['chosen']) == canonical(payload['chosen']) and
                    science['input_before'] == science['input_after'] == begin['observation_sha256'],
                    'full scientific boundary mismatch')
            require(type(science['roots']) is list and len(science['roots']) <= 16384, 'returned-root ceiling')
            require(science['rng_before'] == digest(payload['rng_initial']) == payload['initial_rng_sha256'] ==
                    start['initial_rng_sha256'] == begin['initial_rng_sha256'] and
                    science['rng_after'] == digest(payload['rng_final']) == payload['final_rng_sha256'] and
                    canonical(payload['rng_initial']) == canonical(begin['rng_initial']), 'full RNG boundary mismatch')
            for value in payload['timing'].values():
                _number(value, 360, positive=True)
            require(set(payload['timing']) == {'wall_seconds', 'cpu_seconds'}, 'exact matched timing fields')
            require(payload['production_admissible'] is False, 'diagnostic cannot be production-admissible')
            if identity['condition'] == 'U':
                require(canonical({k: payload[k] for k in U_FLAGS}) == canonical(U_FLAGS), 'U unmeasured accounting flags')
            payloads.append(payload)
        # Full scientific objects and full actual RNG bytes, not digest-only equality.
        science_keys = ('chosen', 'scientific', 'rng_initial', 'rng_final')
        evidence = canonical({k: payloads[0][k] for k in science_keys})
        require(evidence == canonical({k: payloads[1][k] for k in science_keys}), 'independent science/RNG equality')
        full = (evidence, canonical(begin['public_before']), begin['engine_before'], canonical(begin['conservation_before']))
        if identity['size'] in baselines:
            require(full == baselines[identity['size']], 'four-cell fixture equality')
        else:
            baselines[identity['size']] = full
        if identity['condition'] == 'P':
            metrics = rows(folder / 'resource-metrics.jsonl')
            calls = rows(folder / 'call-results/pass-2/11.jsonl')
            traces = rows(folder / 'decision-traces/pass-2/11.jsonl')
            whole = read(folder / 'whole-wrapper-resources.json')
            require([r['scope'] for r in metrics] == [r['scope'] for r in calls] == ['candidate', 'reference'], 'P scope sequence')
            require([r['event'] for r in traces] == ['decision_started', 'decision_completed'], 'P decision sequence')
            expected_calls = []
            for scope, payload in zip(('candidate', 'reference'), payloads):
                result = {'chosen': payload['chosen'], 'cost': payload['physical_cost']}
                if scope == 'candidate':
                    result['scientific'] = payload['scientific']
                else:
                    # The historical producer adds full reference science only
                    # on disagreement. It cannot occur in successful evidence.
                    result['scientific_sha256'] = payload['scientific_sha256']
                expected_calls.append({'ordinal': 1, 'scope': scope, 'result': result})
            require(canonical(calls) == canonical(expected_calls), 'exact original successful P return journal required')
            metric_rss = []
            for scope, payload, metric, call in zip(('candidate', 'reference'), payloads, metrics, calls):
                metric_rss.append(_decision_metric(metric, scope=scope))
                cost = payload['physical_cost']
                require(payload['physical_operation_caps_enforced'] is True and payload['choice_events_observed'] is True,
                        'P accounting flags')
                require(cost == metric['cost'] == call['result']['cost'] and metric['status'] == 'returned' and
                        type(cost['roots']) is int and cost['roots'] == len(payload['scientific']['roots']) <= 16384 and
                        cost['legal_enumerations'] == 1 + cost['previews'] + cost['exit_geometry_checks'],
                        'P independent meter reconciliation')
                require(all(type(cost[k]) is int and 0 <= cost[k] <= OP_CAPS[k] for k in OP_CAPS), 'P caps')
            summed = {k: sum(p['physical_cost'][k] for p in payloads) for k in OP_CAPS}
            require(canonical(whole['operations']) == canonical(summed), 'P whole-wrapper counts differ from sum')
            _number(whole['wall_seconds'], 720, positive=True)
            _number(whole['cpu_seconds'], 720, positive=True)
            wrapper_rss = _rss(whole['peak_rss_kib'])
            require(metric_rss[0] <= metric_rss[1] <= wrapper_rss <= cell['peak_rss_kib'] <=
                    supervisor['child_high_water_rss_kib'], 'P same-child high-water RSS decreased')
            for k in OP_CAPS:
                total[k] += summed[k]
                require(total[k] <= 1000000, 'summed P operations exceed frozen bound')
            science = payloads[0]['scientific']; boundary = traces[1]['audit']['boundary']
            tier = [science['roots'][i]['move'] for i in science['tiers']['final']]
            require(boundary['choice_calls'] == boundary['reference_choice_calls'] == int(bool(tier)) and
                    canonical(boundary['choice_tier']) == canonical(boundary['reference_choice_tier']) == canonical(tier),
                    'P observed RNG choice evidence')
            pair = tuple(normalized_journal(folder / p, Path(receipt['attempt_path']) / 'cells' / f"{identity['cell']:02d}") for p in
                         ('call-results/pass-2/11.jsonl', 'decision-traces/pass-2/11.jsonl'))
            if identity['size'] in journals:
                require(pair == journals[identity['size']], 'repeated P complete journals differ')
            else:
                journals[identity['size']] = pair
        require(sum(p['timing']['cpu_seconds'] for p in payloads) <= supervisor['child_cpu_seconds'] + 1e-6 and
                sum(p['timing']['wall_seconds'] for p in payloads) <= supervisor['wall_seconds'] + 1e-6,
                'matched method windows exceed independent whole-child resources')
        cells.append({**identity, **{scope: p['timing'] for scope, p in zip(('candidate', 'reference'), payloads)}})
    totals = receipt['resource_totals']
    require(totals['supervision'] == supervisors[-1] and totals['P_operations'] == total,
            'parent resource summary reconciliation')
    _phase(totals['phase'], previous_phase)
    require(totals['phase']['reaped_child_cpu_seconds'] + 1e-6 >=
            sum(s['child_cpu_seconds'] for s in supervisors), 'parent total child CPU reconciliation')
    require(Budget(root).inventory() == inventory, 'evidence changed during verification')
    report = {'schema': ('worker38-local-computational-verification-v1' if _retained else
                         'worker38-offline-verification-v2'), 'complete': True, 'cells': cells,
              'total_P_operations': total, 'resource_phase': closing['phase'],
              'prepublication_resource_phase': totals['phase'], 'raw_inventory': inventory,
              'binding': binding, 'custody': 'pending', 'classification': None}
    if _retained:
        report['authentication'] = 'retained_bytes_only'
        report['external_acceptance'] = False
    return {**report, 'verification_sha256': digest(report)}



def _timestamp(value):
    require(type(value) is str, 'missing custody event timestamp')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed),
            'custody timestamps must be UTC')
    return parsed


def _custody_bytes(custody, verification):
    """Check local bytes and provenance consistency, NOT remote authentication."""
    require(custody['schema'] == 'worker38-authenticated-custody-v2' and custody['status'] == 'verified' and
            custody['authenticated_by'] == 'parent-connected-Drive-readback' and
            custody['folder_id'] == CANONICAL_FOLDER and
            custody['verification_sha256'] == verification['verification_sha256'] and
            custody['raw_inventory'] == verification['raw_inventory'],
            'externally authenticated custody binding mismatch')
    outcome = custody['provider_upload_outcome']
    expected = {'schema': 'worker38-provider-upload-outcome-v1',
        'workflow_run': verification['binding']['expected_workflow_run'], 'workflow_attempt': '1',
        'action': './.github/actions/worker38-upload', 'status': 'completed', 'conclusion': 'success',
        'admission_exit_status': 0, 'coordinator_exit_status': 0, 'preservation_exit_status': 0}
    require(type(outcome) is dict and set(outcome) == set(expected) | {'started_at', 'completed_at'} and
            canonical({key: outcome[key] for key in expected}) == canonical(expected),
            'actual completed same-run preservation/composite outcome required')
    duration = (_timestamp(outcome['completed_at']) - _timestamp(outcome['started_at'])).total_seconds()
    require(0 < duration < 60, 'provider composite interval is unknown, empty or reached60seconds')
    manifest = custody['transport_manifest']
    inventory = verification['raw_inventory']
    transport_files = [{'path': x['path'], 'size': x['size_bytes'], 'sha256': x['sha256']} for x in inventory]
    require(manifest['schema'] == 'worker38.transport.v1' and manifest['files'] == transport_files and
            manifest['raw_size'] == sum(x['size_bytes'] for x in inventory) and
            manifest['limits'] == {'raw_bytes': 64 * 1024 ** 2, 'archive_bytes': 64 * 1024 ** 2,
                                  'part_bytes': 30 * 1024 ** 2, 'provider_zip_strictly_below_bytes': 32 * 1024 ** 2},
            'canonical transport/raw inventory mismatch')
    parts = manifest['parts']; descriptors = custody['files']; archive_record = manifest['archive']
    require(type(parts) is list and parts and type(descriptors) is list and len(descriptors) == len(parts) and
            archive_record['path'] == 'attempt.zip' and archive_record['format'] == 'zip-stored-v1' and
            type(archive_record['size']) is int and 0 < archive_record['size'] <= RESOURCES['archive_bytes'],
            'complete bounded custody transport required')
    # Mandatory outer provider wrappers are a distinct archive layer. This
    # read-only checker receives no newly allocated preservation clock; its
    # caller owns the existing external time supervision. Byte/ZIP caps and
    # exact repository/run/attempt/part coverage are always enforced.
    wrapper_checks = verify_provider_wrappers(custody.get('provider_wrappers'), parts,
        transport_manifest=manifest, repository=REPOSITORY, workflow_run=verification['binding']['expected_workflow_run'],
        workflow_attempt=verification['binding']['expected_workflow_attempt'], deadline_monotonic=None)
    require(all(_timestamp(item['asserted_download_receipt']['completed_at']) >=
                _timestamp(outcome['completed_at']) for item in wrapper_checks),
            'provider download preceded observed composite completion')
    chunks = []; seen_ids = set(); seen_inodes = set(); seen_events = set()
    root = Path(verification['binding']['root']); total_bytes = 0
    for order, (part, descriptor) in enumerate(zip(parts, descriptors), 1):
        require(part['order'] == order and part['path'] == f'part-{order:03d}.bin' and
                type(part['size']) is int and 0 < part['size'] <= RESOURCES['part_bytes'] and
                all(descriptor[k] == part[k] for k in ('order', 'path', 'size', 'sha256')),
                'ordered complete transport part descriptor mismatch')
        _hash(part['sha256']); total_bytes += part['size']
        require(total_bytes <= RESOURCES['archive_bytes'], 'reassembled archive cap')
        file_id = descriptor['drive_file_id']; direct = urlsplit(descriptor['direct_url'])
        require(type(file_id) is str and re.fullmatch('[A-Za-z0-9_-]+', file_id) and file_id not in seen_ids and
                direct.scheme == 'https' and direct.netloc == 'drive.google.com' and
                direct.path == f'/file/d/{file_id}/view' and not direct.query and not direct.fragment,
                'unique canonical Drive file identity/direct URL required')
        seen_ids.add(file_id)
        upload_path, upload = _external(descriptor['upload_input_path'], part['sha256'], root, RESOURCES['part_bytes'])
        download_path, downloaded = _external(descriptor['readback_path'], part['sha256'], root, RESOURCES['part_bytes'])
        up_stat = upload_path.stat(); down_stat = download_path.stat()
        inode = (down_stat.st_dev, down_stat.st_ino)
        require(upload_path != download_path and inode != (up_stat.st_dev, up_stat.st_ino) and
                inode not in seen_inodes and len(upload) == len(downloaded) == part['size'],
                'fresh complete readback cannot alias upload or other downloads')
        seen_inodes.add(inode)
        events = []
        for operation in ('upload', 'download'):
            event = descriptor[operation + '_receipt']
            require(event['provider'] == 'google_drive' and event['operation'] == operation and
                    event['file_id'] == file_id and event['size'] == part['size'] and
                    event['sha256'] == part['sha256'] and type(event['event_id']) is str and
                    event['event_id'] and event['event_id'] not in seen_events and
                    (operation != 'upload' or event['parent_folder_id'] == CANONICAL_FOLDER),
                    'authenticated Drive event/byte identity mismatch')
            seen_events.add(event['event_id']); events.append(_timestamp(event['completed_at']))
        require(events[1] > events[0], 'readback must follow successful distinct upload')
        chunks.append(downloaded)
    archive = b''.join(chunks)
    require(len(archive) == archive_record['size'] and sha(archive) == _hash(archive_record['sha256']),
            'fresh canonical archive byte/hash mismatch')
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        members = bundle.infolist()
        require([x.filename for x in members] == [x['path'] for x in inventory],
                'readback archive raw file inventory mismatch')
        for member, expected in zip(members, inventory):
            require(not member.is_dir() and member.compress_type == zipfile.ZIP_STORED and
                    not member.flag_bits & 1 and stat.S_ISREG(member.external_attr >> 16) and
                    member.file_size == member.compress_size == expected['size_bytes'],
                    'readback archive unsafe member or size mismatch')
            raw = bundle.read(member)
            require(len(raw) == expected['size_bytes'] and sha(raw) == expected['sha256'],
                    'fresh canonical raw bytes differ from complete verified evidence')
    # The compact transport manifest is a fourth, independently stored object.
    # Its readback must be fresh too; part readbacks alone cannot prove it was
    # uploaded or that the canonical copy describes the verified archive.
    manifest_raw = canonical(manifest)
    require(wrapper_checks[0]['manifest'] == {'size': len(manifest_raw), 'sha256': sha(manifest_raw)},
            'canonical manifest must equal exact original first-wrapper bytes')
    require(len(manifest_raw) <= 1024 ** 2, 'compact transport manifest exceeds1MiB')
    descriptor = custody['manifest_file']
    expected = {'path': 'transport-manifest.json', 'size': len(manifest_raw), 'sha256': sha(manifest_raw)}
    require(type(descriptor) is dict and all(descriptor[k] == v for k, v in expected.items()),
            'canonical compact manifest descriptor mismatch')
    file_id = descriptor['drive_file_id']; direct = urlsplit(descriptor['direct_url'])
    require(type(file_id) is str and re.fullmatch('[A-Za-z0-9_-]+', file_id) and file_id not in seen_ids and
            direct.scheme == 'https' and direct.netloc == 'drive.google.com' and
            direct.path == f'/file/d/{file_id}/view' and not direct.query and not direct.fragment,
            'unique canonical manifest Drive identity required')
    upload_path, uploaded = _external(descriptor['upload_input_path'], expected['sha256'], root, 1024 ** 2)
    download_path, downloaded = _external(descriptor['readback_path'], expected['sha256'], root, 1024 ** 2)
    up_stat = upload_path.stat(); down_stat = download_path.stat()
    inode = (down_stat.st_dev, down_stat.st_ino)
    require(uploaded == downloaded == manifest_raw and upload_path != download_path and
            inode != (up_stat.st_dev, up_stat.st_ino) and inode not in seen_inodes,
            'canonical manifest readback is absent, changed or aliases an input')
    events = []
    for operation in ('upload', 'download'):
        event = descriptor[operation + '_receipt']
        require(event['provider'] == 'google_drive' and event['operation'] == operation and
                event['file_id'] == file_id and event['size'] == expected['size'] and
                event['sha256'] == expected['sha256'] and type(event['event_id']) is str and
                event['event_id'] and event['event_id'] not in seen_events and
                (operation != 'upload' or event['parent_folder_id'] == CANONICAL_FOLDER),
                'authenticated manifest Drive operation/byte identity mismatch')
        seen_events.add(event['event_id']); events.append(_timestamp(event['completed_at']))
    require(events[1] > events[0], 'manifest readback must follow its distinct upload')
    return wrapper_checks


def timing_report(verification, *, authenticated_custody_receipt,
                  trusted_custody_path, trusted_custody_sha256):
    """Classify only after complete re-verification and external custody binding.

    The parent must authenticate the referenced Drive operations independently,
    then supply the externally pinned v2 receipt. This function checks actual
    provider wrappers, exact local upload/readback/reassembly bytes and evidence bindings. It cannot establish
    remote authenticity from IDs, filenames, timestamps or asserted strings.
    """
    require(type(verification) is dict and verification.get('schema') == 'worker38-offline-verification-v2',
            'complete bound verification required')
    binding = dict(verification['binding']); root = binding.pop('root')
    refreshed = verify_attempt(root, **binding)
    require(canonical(verification) == canonical(refreshed), 'complete verification evidence binding changed')
    _, custody_raw = _external(trusted_custody_path, trusted_custody_sha256, Path(root), RESOURCES['line_bytes'])
    custody = strict_json(custody_raw)
    require(canonical(custody) == canonical(authenticated_custody_receipt),
            'custody receipt differs from independently authenticated exact bytes')
    wrapper_checks = _custody_bytes(custody, refreshed)
    cells = refreshed['cells']; primary = {}; matched = {}
    def cpu(cell):
        return cell['candidate']['cpu_seconds'] + cell['reference']['cpu_seconds']
    for size in (40, 48):
        p = [c for c in cells if c['size'] == size and c['condition'] == 'P']
        u = [c for c in cells if c['size'] == size and c['condition'] == 'U']
        require(len(p) == len(u) == 2, 'primary complete pairs')
        primary[str(size)] = sum(map(cpu, u)) / sum(map(cpu, p))
        for repetition in (1, 2):
            matched[f'{size}/repetition-{repetition}'] = cpu(next(c for c in u if c['repetition'] == repetition)) / cpu(next(c for c in p if c['repetition'] == repetition))
    material = all(v <= .80 for v in primary.values()) and all(v <= .90 for v in matched.values())
    return {'schema': 'worker38-timing-report-v2', 'cells': cells, 'primary_U_over_P_CPU': primary,
            'repetition_matched_U_over_P_CPU': matched, 'custody': 'verified',
            'verification_sha256': refreshed['verification_sha256'], 'custody_sha256': trusted_custody_sha256,
            'provider_wrappers': wrapper_checks,
            'remote_authentication': 'External parent responsibility; not established by local strings or byte checks',
            'classification': 'profile_overhead_material' if material else 'profile_overhead_not_material',
            'interpretation': 'Finite invented inputs only; no production optimization, error-equivalence, efficacy or future run allocation.'}
