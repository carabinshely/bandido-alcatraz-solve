"""Offline byte/equality/accounting verification. Never imports scientific code."""
from __future__ import annotations
import math
import io
import re
import stat
import zipfile
from datetime import datetime, timezone
from urllib.parse import urlsplit
from pathlib import Path
from .common import (Budget, OP_CAPS, RESOURCES, RUNTIME, SCHEDULE, U_FLAGS, canonical, digest,
                     file_info, require, strict_json, sha, loader_pin, ResourceExceeded, HISTORICAL, REPOSITORY, PREREGISTRATION, PROTOCOL_SHA256)
from .sources import read_manifest, verify_files
from .admission import verify_provenance, INPUT_NAMES


def read(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= RESOURCES['line_bytes'],
            'bounded regular offline evidence file required')
    raw = path.read_bytes()
    require(len(raw) <= 8 * 1024 ** 2, 'offline JSON record exceeds frozen line bound')
    return strict_json(raw)


def rows(path):
    lines = Path(path).read_bytes().splitlines()
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
CANONICAL_FOLDER = '1sQhQY3aKuHvQfyOTUIQjJGANCKOwKgEd'


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


def _admission(root, trusted_path, trusted_hash, head, tree):
    path, raw = _external(trusted_path, trusted_hash, root, RESOURCES['receipt_bytes'])
    require((root / 'external-admission.json').read_bytes() == raw,
            'attempt admission differs from externally authenticated bytes')
    go = strict_json(raw)
    require(type(head) is str and re.fullmatch('[0-9a-f]{40}', head) and
            type(tree) is str and re.fullmatch('[0-9a-f]{40}', tree) and
            go['head'] == head and go['tree'] == tree, 'authenticated exact head/tree mismatch')
    require(go['schema'] == 'worker36-one-shot-admission-v1' and go['admitted'] is True and
            go['repository'] == REPOSITORY and go['preregistration_url'] == PREREGISTRATION and
            go['protocol_sha256'] == PROTOCOL_SHA256 and go['runtime'] == RUNTIME and
            go['resources'] == RESOURCES and go['schedule'] == list(SCHEDULE) and
            go['maximum_evaluator_calls'] == 40 and go['games'] == 0 and
            go['runner'] == 'bandido-alcatraz-ci' and
            go['branch'] == 'research/worker36-synthetic-profile-overhead', 'authenticated freeze mismatch')
    require(loader_pin(go['loader_pin']) == go['loader_pin'],
            'admission requires the exact portable loader pin')
    require(go['postmerge_ci'] == {'run_id': 37108669492, 'head': '9c1eeeb8a26868d41f8d8d89b17fc897a60cb38b',
            'status': 'completed', 'conclusion': 'success'}, 'postmerge CI prerequisite')
    reviews = go['reviews']
    require(type(reviews) is list and len(reviews) >= 2 and
            all(r['head'] == head and r['tree'] == tree and r['verdict'] == 'clean' and
                r['url'].startswith('https://github.com/' + REPOSITORY + '/') for r in reviews) and
            len({r['reviewer'] for r in reviews}) >= 2, 'independent exact-head reviews missing')
    require(file_info(root / 'stub-test-receipt.json')['sha256'] == _hash(go['stub_test_receipt_sha256']),
            'frozen literal-stub test receipt bytes mismatch')
    require(file_info(root / 'source-manifest.json')['sha256'] == go['source_manifest_sha256'],
            'authenticated source-manifest pin mismatch')
    pins = go['diagnostic_files_sha256']
    required = {'scripts/worker36/' + name for name in
                ('__init__.py', 'admission.py', 'cell.py', 'common.py', 'driver.py', 'runner_preflight.py', 'sources.py', 'supervision.py', 'transport.py', 'verify.py')}
    required |= {'scripts/run_worker36_synthetic.py', 'scripts/worker36-loader.sh', '.github/workflows/worker36-synthetic-profile.yml', '.github/workflows/worker36-runner-preflight.yml',
                 'experiments/synthetic-profile-overhead/PROTOCOL.md',
                 'experiments/synthetic-profile-overhead/source-manifest.json',
                 'experiments/synthetic-profile-overhead/fault-test-manifest.json'}
    require(set(pins) == required and all(_hash(pin) for pin in pins.values()) and
            pins['experiments/synthetic-profile-overhead/PROTOCOL.md'] == PROTOCOL_SHA256 and
            pins['experiments/synthetic-profile-overhead/source-manifest.json'] == go['source_manifest_sha256'],
            'authenticated diagnostic input pins mismatch')
    stub = read(root / 'stub-test-receipt.json')
    require(all(stub['checked_file_sha256'].get(name) == value for name, value in pins.items()) and
            stub['candidate_evaluator_calls'] == stub['reference_evaluator_calls'] == stub['games'] == 0 and
            stub['failures'] == stub['errors'] == 0, 'test receipt does not cover authenticated diagnostic sources')
    return go, {'trusted_admission_path': str(path), 'trusted_admission_sha256': trusted_hash,
                'expected_head': head, 'expected_tree': tree}


def _runtime(runtime, *, child, loader_freeze, attempt_path=None, index=None):
    require({k: runtime[k] for k in RUNTIME} == RUNTIME and
            runtime['gc_enabled'] is True and runtime['gc_threshold'] == [700, 10, 10] and
            runtime['python_environment'] == {'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1'},
            'runtime/GC/environment evidence mismatch')
    require(runtime['effective_flags'] == {'dont_write_bytecode': 1, 'no_user_site': 1,
            'ignore_environment': 0, 'isolated': 0, 'optimize': 0, 'no_site': 0},
            'effective interpreter flags mismatch')
    require(type(runtime['executable']) is str and Path(runtime['executable']).is_absolute(),
            'runtime executable path missing')
    identity = runtime['loader']
    require(type(identity) is dict and identity.get('schema') == 'worker36-loader-identity-v1' and
            loader_pin(identity) == loader_freeze and runtime['executable'] == identity['executable_path'],
            'runtime loader identity differs from the authenticated loader freeze')
    flags = runtime['flags']
    require(type(flags) is list and len(flags) >= 4 and all(type(x) is str for x in flags) and
            flags[1:3] == ['-B', '-s'] and Path(flags[3]).is_absolute() and
            flags[3].endswith('/scripts/run_worker36_synthetic.py'), 'exact -B -s invocation required')
    if child:
        require(runtime['address_space'] == [RESOURCES['address_space_bytes']] * 2 and
                flags[4:] == ['_cell', '--attempt', attempt_path, '--cell', str(index)],
                'child argv/address-space evidence mismatch')
    else:
        require(runtime['address_space'] == [-1, -1] and flags[4:5] == ['measure'],
                'coordinator initial address-space/argv mismatch')
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
    require(type(value) is dict and value['schema'] == 'worker36-measurement-phase-close-v1' and
            value['includes_computational_receipt_publication'] is True and
            value['closing_proof_included_in_measurement'] is False and value['measurement_work_after_close'] is False,
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
    require(value['schema'] == 'worker36.supervision.v1' and value['status'] == 'completed' and
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
    _number(value['child_high_water_rss_kib'], positive=True)
    _number(value['cpu_tick_seconds'], positive=True)
    require(value['poll_seconds'] == .02, 'supervisor polling evidence drift')
    _phase(value['phase'], previous)
    return value


def verify_attempt(root, *, trusted_admission_path, trusted_admission_sha256,
                   expected_head, expected_tree, trusted_provenance_path,
                   trusted_provenance_sha256, expected_workflow_run, expected_workflow_attempt='1'):
    """Reconcile all preserved bytes against independently authenticated inputs.

    The caller must authenticate the admission/provenance outside this API. A
    filename, hash or asserted remote identity alone cannot perform that step.
    No runtime check or historical module import is performed on the verifier.
    """
    original = Path(root).absolute()
    require(not original.is_symlink(), 'attempt root may not be a symlink')
    root = original.resolve(); receipt = read(root / 'receipt.json')
    admission, binding = _admission(root, trusted_admission_path, trusted_admission_sha256,
                                    expected_head, expected_tree)
    provenance_path, provenance_raw = _external(trusted_provenance_path, trusted_provenance_sha256,
                                               root, RESOURCES['receipt_bytes'])
    provenance = verify_provenance(provenance_path, trusted_admission_path, trusted_admission_sha256)
    require(provenance['head'] == expected_head and provenance['tree'] == expected_tree and
            provenance['workflow_run'] == expected_workflow_run and type(expected_workflow_run) is str and
            expected_workflow_run.isdecimal() and provenance['workflow_attempt'] == expected_workflow_attempt == '1',
            'externally authenticated workflow/admission provenance mismatch')
    preserved_auth = root / 'admission-inputs'
    for name in (*INPUT_NAMES, Path(trusted_admission_path).name, provenance_path.name):
        require((preserved_auth / name).read_bytes() == (provenance_path.parent / name).read_bytes(),
                'preserved admission provenance/input bytes mismatch')
    require(receipt['schema'] == 'worker36-attempt-v1' and receipt['admission_verified'] is True and
            receipt['admission_sha256'] == trusted_admission_sha256 and
            receipt['diagnostic_head'] == expected_head and receipt['diagnostic_tree'] == expected_tree and
            all(receipt[k] == provenance[k] for k in ('attempt_id', 'attempt_path', 'workflow_run', 'workflow_attempt')) and
            Path(receipt['attempt_path']).is_absolute() and Path(receipt['attempt_path']).name == receipt['attempt_id'] and
            receipt['runner'] == admission['runner'] and receipt['preregistration_url'] == PREREGISTRATION and
            receipt['source_manifest_sha256'] == admission['source_manifest_sha256'] and
            receipt['resources'] == RESOURCES and receipt['games'] == 0 and
            receipt['phase'] == 'verification_pending' and receipt['current_cell'] is None and
            receipt['custody'] == 'pending' and receipt['classification'] is None and
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
    preflight = read(root / 'source-runtime-preflight.json')
    require(preflight['phase'] == 'source_runtime_preflight' and preflight['evaluator_starts'] == 0 and
            preflight['restored_source_inventory'] == manifest['files'] and
            preflight['diagnostic_files_sha256'] == admission['diagnostic_files_sha256'] and
            preflight['runtime']['inherited_limits'] == admission['inherited_limits'] and
            preflight['coordinator_address_space'] == [RESOURCES['address_space_bytes']] * 2,
            'parent source/runtime preflight differs from authenticated freeze')
    executable_script = _runtime(preflight['runtime'], child=False, loader_freeze=admission['loader_pin'])
    inventory = Budget(root).inventory()
    require(receipt['file_inventory'] == [x for x in inventory if x['path'] not in ('receipt.json', 'measurement-phase-close.json')],
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
        require(all(cell[k] == v for k, v in identity.items()) and cell['status'] == 'complete'
                and cell['hook_restored'] and cell['timer_restored'] and
                cell['actual_starts'] == cell['actual_starts_upper_bound'] == cell['pre_call_markers'] ==
                cell['invocation_attempts'] == cell['actual_returns'] == cell['confirmed_captures'] == 2,
                'incomplete cell/restoration gate')
        require(cell['schema'] == 'worker36-cell-receipt-v1' and cell['error_type'] is None and
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
        _number(cell['peak_rss_kib'], positive=True)
        if identity['condition'] == 'U':
            require(read(folder / 'unmeasured-accounting.json') == U_FLAGS, 'U accounting record missing/drift')
        begin = read(folder / 'cell-start.json'); end = read(folder / 'cell-boundaries.json')
        require(begin['observation_sha256'] == digest(begin['public_before']) and
                canonical(begin['public_before']) == canonical(end['public_after']) and
                begin['engine_before'] == end['engine_after'] and
                canonical(begin['conservation_before']) == canonical(end['conservation_after']) and
                begin['conservation_before']['inventory_count'] == 69 and end['equality'] is True and
                all(begin[k] == v for k, v in identity.items()), 'invented-state boundary gate')
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
            require(all(payload[k] == v and start[k] == v for k, v in identity.items())
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
                require(all(payload[k] == v for k, v in U_FLAGS.items()), 'U unmeasured accounting flags')
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
            require(canonical(calls[0]['result']['scientific']) == canonical(payloads[0]['scientific']) and
                    calls[1]['result']['scientific_sha256'] == payloads[1]['scientific_sha256'], 'P original return journal')
            for payload, metric, call in zip(payloads, metrics, calls):
                cost = payload['physical_cost']
                require(payload['physical_operation_caps_enforced'] is True and payload['choice_events_observed'] is True,
                        'P accounting flags')
                require(cost == metric['cost'] == call['result']['cost'] and metric['status'] == 'returned' and
                        type(cost['roots']) is int and cost['roots'] == len(payload['scientific']['roots']) <= 16384 and
                        cost['legal_enumerations'] == 1 + cost['previews'] + cost['exit_geometry_checks'],
                        'P independent meter reconciliation')
                require(all(type(cost[k]) is int and 0 <= cost[k] <= OP_CAPS[k] for k in OP_CAPS), 'P caps')
            summed = {k: sum(p['physical_cost'][k] for p in payloads) for k in OP_CAPS}
            require(whole['operations'] == summed, 'P whole-wrapper counts differ from sum')
            _number(whole['wall_seconds'], 720, positive=True)
            _number(whole['cpu_seconds'], 720, positive=True)
            _number(whole['peak_rss_kib'], positive=True)
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
    report = {'schema': 'worker36-offline-verification-v2', 'complete': True, 'cells': cells,
              'total_P_operations': total, 'resource_phase': closing['phase'],
              'prepublication_resource_phase': totals['phase'], 'raw_inventory': inventory,
              'binding': binding, 'custody': 'pending', 'classification': None}
    return {**report, 'verification_sha256': digest(report)}



def _timestamp(value):
    require(type(value) is str, 'missing custody event timestamp')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed),
            'custody timestamps must be UTC')
    return parsed


def _custody_bytes(custody, verification):
    """Check local bytes and provenance consistency, NOT remote authentication."""
    require(custody['schema'] == 'worker36-authenticated-custody-v1' and custody['status'] == 'verified' and
            custody['authenticated_by'] == 'parent-connected-Drive-readback' and
            custody['folder_id'] == CANONICAL_FOLDER and
            custody['verification_sha256'] == verification['verification_sha256'] and
            custody['raw_inventory'] == verification['raw_inventory'],
            'externally authenticated custody binding mismatch')
    manifest = custody['transport_manifest']
    inventory = verification['raw_inventory']
    transport_files = [{'path': x['path'], 'size': x['size_bytes'], 'sha256': x['sha256']} for x in inventory]
    require(manifest['schema'] == 'worker36.transport.v1' and manifest['files'] == transport_files and
            manifest['raw_size'] == sum(x['size_bytes'] for x in inventory) and
            manifest['limits'] == {'raw_bytes': 64 * 1024 ** 2, 'archive_bytes': 64 * 1024 ** 2,
                                  'part_bytes': 30 * 1024 ** 2, 'provider_zip_strictly_below_bytes': 32 * 1024 ** 2},
            'canonical transport/raw inventory mismatch')
    parts = manifest['parts']; descriptors = custody['files']; archive_record = manifest['archive']
    require(type(parts) is list and parts and type(descriptors) is list and len(descriptors) == len(parts) and
            archive_record['path'] == 'attempt.zip' and archive_record['format'] == 'zip-stored-v1' and
            type(archive_record['size']) is int and 0 < archive_record['size'] <= RESOURCES['archive_bytes'],
            'complete bounded custody transport required')
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


def timing_report(verification, *, authenticated_custody_receipt,
                  trusted_custody_path, trusted_custody_sha256):
    """Classify only after complete re-verification and external custody binding.

    The parent must authenticate the referenced Drive operations independently,
    then supply the externally pinned receipt. This function checks exact local
    upload/readback/reassembly bytes and evidence bindings. It cannot establish
    remote authenticity from IDs, filenames, timestamps or asserted strings.
    """
    require(type(verification) is dict and verification.get('schema') == 'worker36-offline-verification-v2',
            'complete bound verification required')
    binding = dict(verification['binding']); root = binding.pop('root')
    refreshed = verify_attempt(root, **binding)
    require(canonical(verification) == canonical(refreshed), 'complete verification evidence binding changed')
    _, custody_raw = _external(trusted_custody_path, trusted_custody_sha256, Path(root), RESOURCES['line_bytes'])
    custody = strict_json(custody_raw)
    require(canonical(custody) == canonical(authenticated_custody_receipt),
            'custody receipt differs from independently authenticated exact bytes')
    _custody_bytes(custody, refreshed)
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
    return {'schema': 'worker36-timing-report-v2', 'cells': cells, 'primary_U_over_P_CPU': primary,
            'repetition_matched_U_over_P_CPU': matched, 'custody': 'verified',
            'verification_sha256': refreshed['verification_sha256'], 'custody_sha256': trusted_custody_sha256,
            'remote_authentication': 'External parent responsibility; not established by local strings or byte checks',
            'classification': 'profile_overhead_material' if material else 'profile_overhead_not_material',
            'interpretation': 'Finite invented inputs only; no production optimization, error-equivalence, efficacy or future run allocation.'}
