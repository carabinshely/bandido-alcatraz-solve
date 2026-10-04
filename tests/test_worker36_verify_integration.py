"""Finite baseline and recovery-R1 offline integration cases; no evaluator/import execution.

Science, RNG, source and observation objects below are literal invented stubs.
Only metadata/hashes/copies are constructed. Neither an evaluator nor a fixture
constructor is called. Trust anchors stand in for the parent's authenticated
inputs and are not claims about actual GitHub or Drive operations.
"""
import copy
import hashlib
import io
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from worker36 import admission as a
from worker36 import common as c
from worker36 import verify as v
from worker36 import transport as t

HEAD = '1111111111111111111111111111111111111111'
TREE = '2222222222222222222222222222222222222222'
PUBLIC = {'literal': 'invented detached public object, not a game observation'}
RNG = [3, [101, 202, 303], None]
SCIENCE = {'schema': 'worker35-scientific-v1', 'input_before': None, 'input_after': None,
           'roots': [], 'supply': {'literal': 'invented'},
           'tiers': {'T0': [], 'F': [], 'T': [], 'C': [], 'final': []}, 'guards': [],
           'flags': {'reserve_filter_active': False, 'reserve_primary_tier_changed': False,
                     'closure_branch_selected': False, 'true_original_all_collect_crossover': False,
                     'reserve_filter_mediated_change': False},
           'chosen_index': None, 'chosen': None, 'rng_before': None, 'rng_after': None}
INHERITED = {'RLIMIT_AS': [-1, -1], 'RLIMIT_CPU': [-1, -1]}
ORIGINAL = '/invented-cache/worker36-evidence/run-123-attempt-1/worker36-123-1'
SCRIPT = '/invented-checkout/scripts/run_worker36_synthetic.py'
SOURCE_BYTES = b'# Fixed invented inert source; never imported.\n'
TESTED_EXTRA_PATHS = ('evidence-design/admission-integration-test-plan.json', 'evidence-design/ast-fifth-repair-test-plan.json', 'evidence-design/cell-fourth-repair-test-plan.json', 'evidence-design/cell-integration-test-plan.json', 'evidence-design/cell-third-repair-test-plan.json', 'evidence-design/driver-fifth-repair-test-plan.json', 'evidence-design/driver-fourth-repair-test-plan.json', 'evidence-design/driver-integration-test-plan.json', 'evidence-design/driver-sixth-repair-test-plan.json', 'evidence-design/driver-third-repair-test-plan.json', 'evidence-design/external-review-5406951565-test-plan.json', 'evidence-design/failure-state-test-plan.json', 'evidence-design/recovery-r1-driver-test-plan.json', 'evidence-design/recovery-r1-loader-integration-test-plan.json', 'evidence-design/recovery-r1-loader-test-plan.json', 'evidence-design/recovery-r1-preflight-shell-test-plan.json', 'evidence-design/recovery-r1-runner-repair-test-plan.json', 'evidence-design/recovery-r1-supervisor-test-plan.json', 'evidence-design/recovery-r1-test-isolation-test-plan.json', 'evidence-design/recovery-r1-verifier-test-plan.json', 'evidence-design/runner-preflight-test-plan.json', 'evidence-design/supervisor-fifth-repair-test-plan.json', 'evidence-design/supervisor-fourth-repair-test-plan.json', 'evidence-design/supervisor-sixth-repair-test-plan.json', 'evidence-design/supervisor-test-plan.json', 'evidence-design/supervisor-third-repair-test-plan.json', 'evidence-design/transport-test-plan.json', 'evidence-design/verifier-integration-test-plan.json', 'tests/test_worker36_admission_integration.py', 'tests/test_worker36_cell_integration.py', 'tests/test_worker36_core.py', 'tests/test_worker36_driver_integration.py', 'tests/test_worker36_runner_preflight.py', 'tests/test_worker36_supervision.py', 'tests/test_worker36_transport.py', 'tests/test_worker36_verify_integration.py', 'tests/worker36_constructor_source.txt')
LOADER_PIN = {'schema': 'worker36-loader-pin-v1', 'executable_sha256': c.RUNTIME['executable_sha256'],
              'library_relative_path': 'Python/3.11.16/x64/lib/libpython3.11.so.1.0',
              'library_sha256': 'b' * 64, 'library_size_bytes': 12345}
LOADER_IDENTITY = {
    'schema': 'worker36-loader-identity-v1', 'tool_cache': '/invented-cache',
    'executable_path': '/invented-cache/Python/3.11.16/x64/bin/python3.11',
    'executable_sha256': c.RUNTIME['executable_sha256'],
    'library_relative_path': 'Python/3.11.16/x64/lib/libpython3.11.so.1.0',
    'library_path': '/invented-cache/Python/3.11.16/x64/lib/libpython3.11.so.1.0',
    'library_directory': '/invented-cache/Python/3.11.16/x64/lib',
    'library_sha256': 'b' * 64, 'library_size_bytes': 12345,
    'library_device': {'major': 8, 'minor': 1}, 'library_inode': 1234,
    'mapped_library': {'path': '/invented-cache/Python/3.11.16/x64/lib/libpython3.11.so.1.0',
                       'device': {'major': 8, 'minor': 1}, 'inode': 1234},
    'loader_environment': {'LD_LIBRARY_PATH': '/invented-cache/Python/3.11.16/x64/lib'}}
IDENTITIES = ['literal01', 'literal02', 'literal03', 'literal04', 'literal05', 'literal06', 'literal07',
              'literal08', 'literal09', 'literal10', 'literal11', 'literal12', 'literal13', 'literal14',
              'literal15', 'literal16', 'literal17', 'literal18', 'literal19', 'literal20', 'literal21',
              'literal22', 'literal23', 'literal24', 'literal25', 'literal26', 'literal27', 'literal28',
              'literal29', 'literal30', 'literal31', 'literal32', 'literal33', 'literal34', 'literal35',
              'literal36', 'literal37', 'literal38', 'literal39', 'literal40', 'literal41', 'literal42',
              'literal43', 'literal44', 'literal45', 'literal46', 'literal47', 'literal48', 'literal49',
              'literal50', 'literal51', 'literal52', 'literal53', 'literal54', 'literal55', 'literal56',
              'literal57', 'literal58', 'literal59', 'literal60', 'literal61', 'literal62', 'literal63',
              'literal64', 'literal65', 'literal66', 'literal67', 'literal68', 'literal69']
SOURCE_MODULES = (
    ('src/bandido_alcatraz/simulate.py', 'bandido_alcatraz.simulate'),
    ('scripts/benchmark_worker35_synthetic.py', 'benchmark_worker35_synthetic'),
    ('scripts/run_quota_reserve_closure_development.py', 'run_quota_reserve_closure_development'),
    ('scripts/worker35_resources.py', 'worker35_resources'),
    ('src/bandido_alcatraz/quota_reserve_closure.py', 'bandido_alcatraz.quota_reserve_closure'),
    ('src/bandido_alcatraz/quota_reserve_closure_reference.py', 'bandido_alcatraz.quota_reserve_closure_reference'),
    ('src/bandido_alcatraz/worker32/evidence.py', 'bandido_alcatraz.worker32.evidence'))


def write(path, value, raw=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if raw else c.canonical(value))


def read(path):
    return c.strict_json(path.read_bytes())


def set_nested(value, keys, replacement):
    for key in keys[:-1]:
        value = value[key]
    value[keys[-1]] = replacement


class LiteralBundle:
    def __init__(self, base):
        self.base = Path(base); self.root = self.base / 'raw-attempt'; self.root.mkdir()
        self.auth = self.base / 'external-auth'; self.auth.mkdir()
        self.admission = self.auth / 'admission.json'; self.provenance = self.auth / 'provenance.json'
        files = []
        for path, module in SOURCE_MODULES:
            write(self.root / 'restored' / path, SOURCE_BYTES, raw=True)
            files.append({'path': path, 'module': module, 'size_bytes': len(SOURCE_BYTES),
                          'sha256': c.sha(SOURCE_BYTES),
                          'git_blob': hashlib.sha1(b'blob ' + str(len(SOURCE_BYTES)).encode() + b'\0' + SOURCE_BYTES).hexdigest()})
        self.manifest = {'schema': 'worker36-source-manifest-v1', 'repository': c.REPOSITORY,
                         'historical_commit': c.HISTORICAL, 'files': files}
        write(self.root / 'source-manifest.json', self.manifest)
        diagnostic = {'scripts/worker36/' + name: 'a' * 64 for name in
                      ('__init__.py', 'admission.py', 'cell.py', 'common.py', 'driver.py', 'runner_preflight.py', 'sources.py', 'supervision.py', 'transport.py', 'verify.py')}
        diagnostic.update({name: 'a' * 64 for name in ('scripts/run_worker36_synthetic.py', 'scripts/worker36-loader.sh',
                          '.github/workflows/worker36-synthetic-profile.yml', '.github/workflows/worker36-runner-preflight.yml',
                          'experiments/synthetic-profile-overhead/fault-test-manifest.json')})
        diagnostic['experiments/synthetic-profile-overhead/PROTOCOL.md'] = c.PROTOCOL_SHA256
        diagnostic['experiments/synthetic-profile-overhead/source-manifest.json'] = c.file_info(self.root / 'source-manifest.json')['sha256']
        tested_sources = {**diagnostic, **{path: 'c' * 64 for path in TESTED_EXTRA_PATHS}}
        stub = {'success': True, 'checked_file_sha256': tested_sources, 'candidate_evaluator_calls': 0,
                'reference_evaluator_calls': 0, 'measurement_fixture_constructions': 0,
                'historical_source_imports': 0, 'games': 0, 'failures': 0, 'errors': 0}
        write(self.root / 'stub-test-receipt.json', stub)
        self.go = {'schema': 'worker36-one-shot-admission-v1', 'admitted': True,
                   'repository': c.REPOSITORY, 'branch': a.BRANCH, 'preregistration_url': c.PREREGISTRATION,
                   'protocol_sha256': c.PROTOCOL_SHA256, 'admission_url': a.WEB + '/pull/40',
                   'head': HEAD, 'tree': TREE, 'runner': 'bandido-alcatraz-ci',
                   'runtime': c.RUNTIME, 'loader_pin': copy.deepcopy(LOADER_PIN), 'resources': c.RESOURCES, 'schedule': list(c.SCHEDULE),
                   'maximum_evaluator_calls': 40, 'games': 0,
                   'source_manifest_sha256': diagnostic['experiments/synthetic-profile-overhead/source-manifest.json'],
                   'diagnostic_files_sha256': diagnostic,
                   'cell_preflight_modules': sorted(module for _, module in SOURCE_MODULES if module != 'bandido_alcatraz.simulate'),
                   'inherited_limits': INHERITED,
                   'stub_test_receipt_sha256': c.file_info(self.root / 'stub-test-receipt.json')['sha256'],
                   'postmerge_ci': {'run_id': a.CI_RUN, 'head': a.BASE_HEAD, 'status': 'completed', 'conclusion': 'success'},
                   'reviews': [{'head': HEAD, 'tree': TREE, 'verdict': 'clean', 'reviewer': 'literal-reviewer-one',
                                'url': a.WEB + '/pull/40#issuecomment-100'},
                               {'head': HEAD, 'tree': TREE, 'verdict': 'clean', 'reviewer': 'literal-reviewer-two',
                                'url': a.WEB + '/pull/40#issuecomment-200'}]}
        self.write_auth()
        parent_runtime = self.runtime()
        parent_runtime['flags'] = [LOADER_IDENTITY['executable_path'], '-B', '-s', SCRIPT, 'measure']
        parent_runtime['address_space'] = [-1, -1]; parent_runtime['inherited_limits'] = INHERITED
        write(self.root / 'source-runtime-preflight.json', {'phase': 'source_runtime_preflight', 'evaluator_starts': 0,
              'runtime': parent_runtime, 'coordinator_address_space': [512 * 1024 ** 2] * 2,
              'restored_source_inventory': files, 'diagnostic_files_sha256': diagnostic})
        for identity in c.SCHEDULE:
            self.cell(identity)
        self.receipt = {'schema': 'worker36-attempt-v1', 'status': 'execution_complete',
                        'phase': 'verification_pending', 'admission_verified': True,
                        'admission_sha256': c.sha(self.admission.read_bytes()), 'diagnostic_head': HEAD,
                        'diagnostic_tree': TREE, 'attempt_id': 'worker36-123-1', 'attempt_path': ORIGINAL,
                        'runner': 'bandido-alcatraz-ci', 'workflow_run': '123', 'workflow_attempt': '1',
                        'preregistration_url': c.PREREGISTRATION,
                        'source_manifest_sha256': self.go['source_manifest_sha256'], 'resources': c.RESOURCES,
                        'games': 0, 'schedule': list(c.SCHEDULE), 'maximum_evaluator_calls': 40,
                        'actual_starts': 40, 'actual_starts_upper_bound': 40, 'pre_call_markers': 40, 'actual_returns': 40, 'confirmed_captures': 40,
                        'current_cell': None, 'completed_prefix': list(range(1, 21)), 'capture_gaps': [], 'corrupt_evidence': [], 'unavailable_evidence': [], 'retained_failures': [],
                        'custody': 'pending', 'classification': None, 'supervisor_pid': 1000,
                        'resource_totals': {'supervision': read(self.root / 'supervisor-cell-20.json'),
                            'P_operations': {'legal_enumerations': 20, 'previews': 0, 'exit_geometry_checks': 0},
                            'phase': self.phase(21)}}
        write(self.root / 'receipt.json', self.receipt); self.refresh()

    def write_auth(self):
        from test_worker36_admission_integration import literal_prerequisite_bundle
        # Invalid structural pins are rejected by the authoritative gate before
        # any literal prerequisite provenance is constructed.
        a.admitted_loader_pin(self.go.get('loader_pin'))
        stub_path = self.root / 'stub-test-receipt.json'
        source = {'path': v.FOCUSED_SOURCE_RECEIPT, **c.file_info(stub_path)}
        checked = {**read(stub_path)['checked_file_sha256'], v.FOCUSED_SOURCE_RECEIPT: source['sha256']}
        self.go, proof_bytes = literal_prerequisite_bundle(self.go, pr_number=40, owner_id=456,
            cache='/invented-cache', focused_source_receipt=source, checked_file_sha256=checked)
        raw = c.canonical(self.go)
        body = a.START + '\n' + raw.decode() + a.END + '\n' + a.DIGEST + ': ' + c.sha(raw) + '\n'
        owner = {'login': a.OWNER, 'id': 456, 'type': 'User'}
        repo = {'full_name': c.REPOSITORY, 'html_url': a.WEB, 'url': a.API, 'owner': owner}
        pr = {'number': 40, 'html_url': a.WEB + '/pull/40', 'url': a.API + '/pulls/40',
              'issue_url': a.API + '/issues/40', 'state': 'open', 'merged': False, 'merged_at': None,
              'user': owner, 'head': {'ref': a.BRANCH, 'sha': HEAD, 'repo': repo},
              'base': {'ref': 'main', 'sha': a.BASE_HEAD, 'repo': repo}, 'body': body}
        event = {'action': 'edited', 'repository': repo, 'sender': owner, 'number': 40,
                 'pull_request': pr, 'changes': {'body': {'from': 'Fixed invented previous PR body'}}}
        ci = {'repository': repo, 'id': a.CI_RUN, 'url': a.API + '/actions/runs/' + str(a.CI_RUN),
              'html_url': a.WEB + '/actions/runs/' + str(a.CI_RUN), 'head_sha': a.BASE_HEAD,
              'head_branch': 'main', 'event': 'push', 'path': '.github/workflows/test.yml',
              'status': 'completed', 'conclusion': 'success'}
        context = {'schema': 'worker36-github-request-context-v1', 'repository': c.REPOSITORY,
                   'event_name': 'pull_request', 'workflow_run': '123', 'workflow_attempt': '1',
                   'server_url': 'https://github.com', 'api_url': 'https://api.github.com',
                   'authentication': 'github-repository-read-token',
                   'pull_request_request': {'method': 'GET', 'url': a.API + '/pulls/40'},
                   'postmerge_ci_request': {'method': 'GET', 'url': a.API + '/actions/runs/' + str(a.CI_RUN)},
                   'runner_name': 'bandido-alcatraz-ci', 'actor': a.OWNER,
                   'run_url': a.WEB + '/actions/runs/123', 'attempt_id': 'worker36-123-1',
                   'runner_tool_cache': '/invented-cache', 'checkout_path': '/invented-checkout',
                   'runner_temp': '/invented-temp',
                   'durable_root': '/invented-cache/worker36-evidence/run-123-attempt-1', 'attempt_path': ORIGINAL}
        inputs = dict(zip(a.INPUT_NAMES[:4], (event, pr, ci, context)))
        for name, value in inputs.items():
            write(self.auth / name, value)
        extracted, provenance = a.extract_pr_admission(event, pr, ci)
        provenance.update(a.verified_context(context, provenance, '123', '1'))
        provenance.update(a.validate_prerequisites(self.go, provenance, proof_bytes))
        for name, raw_proof in proof_bytes.items():
            write(self.auth / name, raw_proof, raw=True)
        provenance['admission_input_hashes'] = {name: c.file_info(self.auth / name)['sha256'] for name in a.INPUT_NAMES}
        write(self.admission, extracted, raw=True); write(self.provenance, provenance)
        write(self.root / 'external-admission.json', extracted, raw=True)
        for name in (*a.INPUT_NAMES, self.admission.name, self.provenance.name):
            write(self.root / 'admission-inputs' / name, (self.auth / name).read_bytes(), raw=True)

    def runtime(self, index=None):
        return {**c.RUNTIME, 'executable': LOADER_IDENTITY['executable_path'],
                'loader': copy.deepcopy(LOADER_IDENTITY),
                'flags': [LOADER_IDENTITY['executable_path'], '-B', '-s', SCRIPT, '_cell', '--attempt', ORIGINAL, '--cell', str(index)],
                'python_environment': {'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1'},
                'gc_enabled': True, 'gc_threshold': [700, 10, 10],
                'effective_flags': {'dont_write_bytecode': 1, 'no_user_site': 1, 'ignore_environment': 0,
                                    'isolated': 0, 'optimize': 0, 'no_site': 0}, 'address_space': [512 * 1024 ** 2] * 2}

    def phase(self, index):
        return {'wall_seconds': 30 * index, 'parent_cpu_seconds': index, 'reaped_child_cpu_seconds': 30 * index,
                'live_child_cpu_seconds': 0, 'cpu_seconds': 31 * index,
                'wall_limit_seconds': 1800, 'cpu_limit_seconds': 1800}

    def cell(self, identity):
        index = identity['cell']; folder = self.root / 'cells' / f'{index:02d}'; folder.mkdir(parents=True)
        modules = {entry['module']: {'path': ORIGINAL + '/restored/' + entry['path'],
                   **{key: entry[key] for key in ('size_bytes', 'sha256', 'git_blob')}} for entry in self.manifest['files']}
        write(folder / 'source-runtime-preflight.json', {'phase': 'source_runtime_preflight', 'evaluator_starts': 0,
                                                       'runtime': self.runtime(index), 'modules': {key: value for key, value in modules.items()
                                                        if key != 'bandido_alcatraz.simulate'}})
        begin = {**identity, 'observation_sha256': c.digest(PUBLIC), 'initial_rng_sha256': c.digest(RNG),
                 'rng_initial': RNG, 'public_before': PUBLIC, 'engine_before': 'literal invented witness',
                 'conservation_before': {'inventory_count': 69, 'inventory_sha256': c.digest(IDENTITIES),
                 'zones': {'placed': [], 'collected': [], 'hand': [], 'draw': IDENTITIES, 'set_aside': []}}}
        write(folder / 'cell-start.json', begin)
        write(folder / 'cell-boundaries.json', {'public_after': PUBLIC, 'engine_after': begin['engine_before'],
              'conservation_after': begin['conservation_before'], 'equality': True})
        write(folder / 'active-call.json', {'active': False})
        science = copy.deepcopy(SCIENCE)
        science.update(input_before=c.digest(PUBLIC), input_after=c.digest(PUBLIC),
                       rng_before=c.digest(RNG), rng_after=c.digest(RNG))
        cost = {'legal_enumerations': 1, 'previews': 0, 'exit_geometry_checks': 0, 'roots': 0}
        calls = {}; payloads = []
        for scope in ('candidate', 'reference'):
            start = {**identity, 'scope': scope, 'observation_sha256': c.digest(PUBLIC), 'initial_rng_sha256': c.digest(RNG),
                     'source_modules': {key: value for key, value in modules.items()
                                        if identity['condition'] == 'P' or key != 'bandido_alcatraz.simulate'}}
            write(folder / (scope + '-start.json'), start)
            payload = {**start, 'chosen': None, 'scientific': science, 'scientific_sha256': c.digest(science),
                       'rng_initial': RNG, 'rng_final': RNG, 'final_rng_sha256': c.digest(RNG),
                       'timing': {'wall_seconds': 12, 'cpu_seconds': 10 if identity['condition'] == 'P' else 8},
                       'physical_cost': cost if identity['condition'] == 'P' else None,
                       'physical_operation_caps_enforced': identity['condition'] == 'P',
                       'choice_events_observed': identity['condition'] == 'P', 'production_admissible': False}
            path = folder / (scope + '-return.json'); write(path, payload)
            evidence = {'path': path.relative_to(self.root).as_posix(), **c.file_info(path)}
            write(folder / (scope + '-capture-confirmed.json'), evidence)
            calls[scope] = {'start_marker_durable': True, 'invocation_attempted': True, 'method_entered': True, 'returned': True, 'durable_capture_confirmed': True, 'evidence': evidence}
            payloads.append(payload)
        if identity['condition'] == 'P':
            metrics = [{'kind': 'decision', 'pass': 2, 'seed': 11, 'ordinal': 1, 'scope': scope,
                        'wall_seconds': 13, 'cpu_seconds': 11, 'peak_rss_kib': 1000,
                        'cost': cost, 'status': 'returned'} for scope in ('candidate', 'reference')]
            journals = [
                {'ordinal': 1, 'scope': 'candidate', 'result': {'chosen': None, 'scientific': science, 'cost': cost}},
                {'ordinal': 1, 'scope': 'reference', 'result': {'chosen': None, 'scientific_sha256': c.digest(science), 'cost': cost}}]
            traces = [{'event': 'decision_started'}, {'event': 'decision_completed', 'audit': {'boundary':
                      {'choice_calls': 0, 'reference_choice_calls': 0, 'choice_tier': [], 'reference_choice_tier': []}}}]
            for name, values in (('resource-metrics.jsonl', metrics), ('call-results/pass-2/11.jsonl', journals),
                                 ('decision-traces/pass-2/11.jsonl', traces)):
                write(folder / name, b''.join(c.canonical(row) for row in values), raw=True)
            write(folder / 'whole-wrapper-resources.json', {'operations': {'legal_enumerations': 2, 'previews': 0, 'exit_geometry_checks': 0},
                  'wall_seconds': 25, 'cpu_seconds': 21, 'peak_rss_kib': 1000})
        else:
            write(folder / 'unmeasured-accounting.json', c.U_FLAGS)
        write(folder / 'cell-receipt.json', {**identity, 'schema': 'worker36-cell-receipt-v1', 'status': 'complete',
              'actual_starts': 2, 'actual_starts_upper_bound': 2, 'pre_call_markers': 2, 'invocation_attempts': 2, 'actual_returns': 2, 'confirmed_captures': 2, 'calls': calls,
              'hook_restored': True, 'timer_restored': True, 'peak_rss_kib': 1000,
              'classification': None, 'error_type': None, 'error': None,
              'failure': None, 'secondary_errors': [], 'phase': 'cell_complete'})
        log_name = f'supervisor-cell-{index:02d}.log'; write(self.root / log_name, b'', raw=True)
        supervisor = {'schema': 'worker36.supervision.v1', 'status': 'completed', 'reason': 'child_exit_zero',
                 'primary_outcome': {'status': 'completed', 'reason': 'child_exit_zero'}, 'secondary_failures': [], 'child_accounting_complete': True, 'phase_accounting_complete': True,
                      'spawn_attempted': True, 'spawn_initialization_complete': True,
                      'spawn_ownership_uncertain': False, 'spawn_discovery': 'not_required', 'spawn_recovered_pids': [],
                      'preservation_deadline_monotonic': None, 'preservation_transition_attempted': False,
                      'preservation_transition_complete': False, 'preservation_expired': False,
                      'preservation_blocked': False,
                      'spawned': True, 'pid': 2000 + index, 'parent_pid': 1000, 'parent_death_signal': 9,
                      'returncode': 0, 'exit_code': 0, 'signal': None, 'scientific_returns_inferred': False,
                      'active_call_at_stop': None, 'errors': [],
                      'cleanup': {'complete': True, 'sigkill_used': False, 'remaining_pids': [], 'errors': [], 'failure_details': []},
                      'output_log': ORIGINAL + '/' + log_name, 'output_capture_mode': 'bounded_memory_then_post_cleanup_fsync',
                      'output_bytes_preserved': 0, 'output_bytes_observed': 0, 'output_durable': True,
                      'output_overflow': False, 'output_prefix_gap': False, 'output_pipe_tail': 'eof_observed',
                      'inherited_limits': {**INHERITED, 'RLIMIT_AS': [512 * 1024 ** 2] * 2},
                      'limits': {'wall_seconds': 720, 'cpu_seconds': 720, 'address_space_bytes': 512 * 1024 ** 2,
                                 'call_wall_seconds': 360, 'call_cpu_seconds': 360, 'output_log_limit_bytes': 63 * 1024 ** 2},
                      'wall_seconds': 30, 'child_cpu_seconds': 30, 'child_high_water_rss_kib': 1000,
                      'cpu_tick_seconds': .01, 'poll_seconds': .02, 'phase': self.phase(index)}
        write(self.root / f'supervisor-cell-{index:02d}.json', supervisor)

    def refresh(self):
        receipt = read(self.root / 'receipt.json')
        receipt['file_inventory'] = [x for x in c.Budget(self.root).inventory() if x['path'] not in ('receipt.json','measurement-phase-close.json')]
        write(self.root / 'receipt.json', receipt)
        write(self.root/'measurement-phase-close.json',{
            'schema':'worker36-measurement-phase-close-v1','phase':self.phase(22),
            'computational_receipt':{'path':'receipt.json',**c.file_info(self.root/'receipt.json')},
            'includes_computational_receipt_publication':True,'closing_proof_included_in_measurement':False,
            'measurement_work_after_close':False,'preservation_started_monotonic':10000,'preservation_deadline_monotonic':10600})

    def mutate(self, name, keys, value, refresh=True):
        path = self.root / name; data = read(path); set_nested(data, keys, value); write(path, data)
        if refresh:
            self.refresh()

    def verify(self, **overrides):
        args = {'trusted_admission_path': self.admission, 'trusted_admission_sha256': c.sha(self.admission.read_bytes()),
                'expected_head': HEAD, 'expected_tree': TREE, 'trusted_provenance_path': self.provenance,
                'trusted_provenance_sha256': c.sha(self.provenance.read_bytes()), 'expected_workflow_run': '123'}
        args.update(overrides)
        return v.verify_attempt(self.root, **args)

    def custody(self, verification):
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, 'w', compression=zipfile.ZIP_STORED) as archive:
            for entry in verification['raw_inventory']:
                info = zipfile.ZipInfo(entry['path'], (1980, 1, 1, 0, 0, 0)); info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o600) << 16
                archive.writestr(info, (self.root / entry['path']).read_bytes())
        raw = memory.getvalue(); upload = self.base / 'upload-part.bin'; downloaded = self.base / 'fresh-download-part.bin'
        write(upload, raw, raw=True); write(downloaded, raw, raw=True)
        part = {'order': 1, 'path': 'part-001.bin', 'size': len(raw), 'sha256': c.sha(raw)}
        file_id = 'literal-Drive-file-one'
        event = {'provider': 'google_drive', 'file_id': file_id, 'size': len(raw), 'sha256': c.sha(raw)}
        descriptor = {**part, 'drive_file_id': file_id, 'direct_url': 'https://drive.google.com/file/d/' + file_id + '/view',
                      'upload_input_path': str(upload), 'readback_path': str(downloaded),
                      'upload_receipt': {**event, 'operation': 'upload', 'event_id': 'literal-upload-event',
                                         'completed_at': '2026-10-03T00:00:00Z', 'parent_folder_id': v.CANONICAL_FOLDER},
                      'download_receipt': {**event, 'operation': 'download', 'event_id': 'literal-download-event',
                                           'completed_at': '2026-10-03T00:01:00Z'}}
        wrapper_path = self.base / 'github-provider-wrapper-001.zip'
        with zipfile.ZipFile(wrapper_path, 'w', compression=zipfile.ZIP_STORED) as wrapper:
            wrapper.writestr(part['path'], raw)
        wrapper_info = {'size': wrapper_path.stat().st_size, 'sha256': c.sha(wrapper_path.read_bytes())}
        provider_wrapper = {'order': 1, 'part_path': part['path'], 'member_name': part['path'],
                            'path': str(wrapper_path), **wrapper_info,
                            'download_receipt': {'provider': 'github_actions', 'operation': 'download',
                                'repository': c.REPOSITORY, 'run_id': '123', 'run_attempt': '1',
                                'artifact_id': '456', 'artifact_name': 'worker36-transport-001-123',
                                'event_id': 'literal-provider-download', 'completed_at': '2026-10-03T00:00:00Z',
                                **wrapper_info}}
        result = {'schema': 'worker36-authenticated-custody-v2', 'status': 'verified',
                  'provider_wrappers': [provider_wrapper],
                  'authenticated_by': 'parent-connected-Drive-readback', 'folder_id': v.CANONICAL_FOLDER,
                  'verification_sha256': verification['verification_sha256'], 'raw_inventory': verification['raw_inventory'],
                  'files': [descriptor], 'transport_manifest': {'schema': 'worker36.transport.v1',
                      'files': [{'path': x['path'], 'size': x['size_bytes'], 'sha256': x['sha256']} for x in verification['raw_inventory']],
                      'raw_size': sum(x['size_bytes'] for x in verification['raw_inventory']), 'parts': [part],
                      'archive': {'path': 'attempt.zip', 'format': 'zip-stored-v1', 'size': len(raw), 'sha256': c.sha(raw)},
                      'limits': {'raw_bytes': 64 * 1024 ** 2, 'archive_bytes': 64 * 1024 ** 2,
                                 'part_bytes': 30 * 1024 ** 2, 'provider_zip_strictly_below_bytes': 32 * 1024 ** 2}}}
        self.custody_path = self.base / 'externally-authenticated-custody.json'; write(self.custody_path, result)
        return result

    def timing(self, verification, custody, **overrides):
        args = {'authenticated_custody_receipt': custody, 'trusted_custody_path': self.custody_path,
                'trusted_custody_sha256': c.sha(self.custody_path.read_bytes())}
        args.update(overrides)
        return v.timing_report(verification, **args)


class VerifyIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.bundle = LiteralBundle(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def rejected_mutation(self, path, keys, value):
        full = self.bundle.root / path; before = full.read_bytes()
        try:
            self.bundle.mutate(path, keys, value)
            with self.assertRaises((ValueError, KeyError, TypeError, OSError, c.ResourceExceeded)):
                self.bundle.verify()
        finally:
            full.write_bytes(before); self.bundle.refresh()

    def test_V01_complete_literal_bundle(self):
        result = self.bundle.verify()
        self.assertTrue(result['complete']); self.assertEqual(len(result['cells']), 20)
        self.assertEqual(result['custody'], 'pending'); self.assertIsNone(result['classification'])
        self.assertEqual(result['total_P_operations']['legal_enumerations'], 20)
        self.assertEqual(result['raw_inventory'], c.Budget(self.bundle.root).inventory())
        self.assertEqual([x['cell'] for x in result['cells']], list(range(1, 21)))

    def test_V02_external_admission_binding(self):
        for overrides in ({'trusted_admission_path': self.bundle.root / 'external-admission.json'},
                          {'trusted_admission_sha256': 'f' * 64}, {'expected_head': 'f' * 40},
                          {'expected_tree': 'f' * 40}, {'trusted_provenance_sha256': 'f' * 64},
                          {'expected_workflow_run': '999'}, {'expected_workflow_attempt': '2'}):
            with self.subTest(overrides=overrides), self.assertRaises((ValueError, OSError)):
                self.bundle.verify(**overrides)
        for keys, value in ((['attempt_id'], 'different'), (['attempt_path'], '/elsewhere/worker36-123-1'),
                            (['admission_sha256'], 'f' * 64), (['diagnostic_tree'], 'f' * 40)):
            with self.subTest(keys=keys):
                self.rejected_mutation('receipt.json', keys, value)
        self.rejected_mutation('admission-inputs/event.json', ['sender', 'login'], 'other-person')

    def test_V03_authenticated_freeze_pins(self):
        mutations = ((['resources'], {}), (['runtime'], {}), (['protocol_sha256'], 'f' * 64),
                     (['source_manifest_sha256'], 'f' * 64), (['maximum_evaluator_calls'], 42),
                     (['schedule'], []), (['diagnostic_files_sha256'], {}),
                     (['cell_preflight_modules'], []), (['stub_test_receipt_sha256'], 'f' * 64))
        original = copy.deepcopy(self.bundle.go)
        for keys, value in mutations:
            with self.subTest(keys=keys):
                self.bundle.go = copy.deepcopy(original); set_nested(self.bundle.go, keys, value)
                # Stronger admission may reject an invalid freeze before an
                # authenticated offline bundle can exist. Do not fake that step.
                with self.assertRaises((ValueError, KeyError, c.ResourceExceeded)):
                    self.bundle.write_auth()
                    self.bundle.mutate('receipt.json', ['admission_sha256'], c.sha(self.bundle.admission.read_bytes()))
                    self.bundle.verify()
        self.bundle.go = original; self.bundle.write_auth()

    def test_V04_parent_source_preflight(self):
        for keys, value in ((['evaluator_starts'], 1), (['restored_source_inventory'], []),
                            (['diagnostic_files_sha256'], {}), (['runtime', 'inherited_limits'], {}),
                            (['coordinator_address_space'], [-1, -1])):
            with self.subTest(keys=keys):
                self.rejected_mutation('source-runtime-preflight.json', keys, value)
        path = self.bundle.root / 'restored' / SOURCE_MODULES[0][0]
        original = path.read_bytes(); path.write_bytes(b'# altered inert source\n'); self.bundle.refresh()
        with self.assertRaises((ValueError, c.ResourceExceeded)):
            self.bundle.verify()
        path.write_bytes(original); self.bundle.refresh()
        self.rejected_mutation('stub-test-receipt.json', ['checked_file_sha256'], {})

    def test_V05_cell_module_manifest(self):
        path = 'cells/01/source-runtime-preflight.json'; module = 'worker35_resources'
        for keys, value in ((['modules'], {}), (['modules', module, 'path'], '/ambient/module.py'),
                            (['modules', module, 'sha256'], 'f' * 64),
                            (['modules', module, 'git_blob'], 'f' * 40),
                            (['modules', module, 'size_bytes'], 0)):
            with self.subTest(keys=keys):
                self.rejected_mutation(path, keys, value)

    def test_V06_exact_runtime_policy(self):
        path = 'cells/02/source-runtime-preflight.json'
        runtime = self.bundle.runtime(2)
        variants = ((['runtime', 'flags'], ['/invented/python', '-I', '-s', SCRIPT]),
                    (['runtime', 'flags'], ['/invented/python', '-B', '-s', '-O', SCRIPT]),
                    (['runtime', 'address_space'], [-1, -1]),
                    (['runtime', 'gc_enabled'], False), (['runtime', 'gc_threshold'], [100, 10, 10]),
                    (['runtime', 'python_environment'], {'PYTHONPATH': '/ambient'}),
                    (['runtime', 'executable_sha256'], 'f' * 64), (['runtime', 'version'], '3.12.14'), (['runtime', 'effective_flags', 'optimize'], 1))
        for keys, value in variants:
            with self.subTest(keys=keys):
                self.rejected_mutation(path, keys, value)

    def test_V07_supervision_and_logs_required_for_every_cell(self):
        self.rejected_mutation('supervisor-cell-01.json', ['child_accounting_complete'], False)
        self.rejected_mutation('supervisor-cell-01.json', ['phase_accounting_complete'], False)
        self.rejected_mutation('supervisor-cell-01.json', ['cleanup','failure_details'], [{'status':'resource_incomplete'}])
        self.rejected_mutation('supervisor-cell-01.json', ['primary_outcome'], {'status':'resource_incomplete','reason':'call_wall_limit'})
        self.rejected_mutation('supervisor-cell-01.json', ['secondary_failures'], [{'status':'execution_incomplete','reason':'cleanup','phase':'cleanup'}])
        for index in range(1, 21):
            for suffix in ('.json', '.log'):
                path = self.bundle.root / f'supervisor-cell-{index:02d}{suffix}'; raw = path.read_bytes()
                with self.subTest(cell=index, suffix=suffix):
                    path.unlink(); self.bundle.refresh()
                    with self.assertRaises((ValueError, OSError)):
                        self.bundle.verify()
                    path.write_bytes(raw); self.bundle.refresh()
        for keys, value in ((['returncode'], 1), (['cleanup', 'complete'], False),
                            (['cleanup', 'remaining_pids'], [123]), (['output_prefix_gap'], True),
                            (['output_durable'], False), (['output_bytes_preserved'], 1),
                            (['output_pipe_tail'], 'unobserved'), (['errors'], ['literal failure']),
                            (['limits', 'call_wall_seconds'], 999), (['inherited_limits'], {}),
                            (['wall_seconds'], 720), (['child_cpu_seconds'], 720)):
            with self.subTest(keys=keys):
                self.rejected_mutation('supervisor-cell-01.json', keys, value)

    def test_V08_parent_totals_errors_inventory(self):
        for keys, value in ((['completed_prefix'], list(range(1, 20))), (['actual_returns'], 39),
                            (['capture_gaps'], [{'cell': 1}]), (['corrupt_evidence'], [{'literal': 'corrupt'}]),
                            (['unavailable_evidence'], [{'literal': 'unavailable'}]), (['retained_failures'], [{'status':'integrity_invalid'}]), (['error'], 'literal error'),
                            (['resource_totals', 'P_operations', 'legal_enumerations'], 19),
                            (['resource_totals', 'phase', 'cpu_seconds'], 1800),
                            (['resource_totals', 'phase', 'wall_seconds'], 1800)):
            with self.subTest(keys=keys):
                self.rejected_mutation('receipt.json', keys, value)
        self.rejected_mutation('supervisor-cell-02.json', ['phase', 'wall_seconds'], 0)
        self.bundle.mutate('receipt.json', ['file_inventory'], [], refresh=False)
        with self.assertRaises((ValueError, c.ResourceExceeded)):
            self.bundle.verify()

    def test_V09_science_rng_capture_boundary(self):
        cases = (('cells/01/candidate-capture-confirmed.json', ['sha256'], 'f' * 64),
                 ('cells/01/candidate-start.json', ['scope'], 'reference'),
                 ('cells/01/candidate-start.json', ['initial_rng_sha256'], 'f' * 64),
                 ('cells/01/candidate-start.json', ['source_modules'], {}),
                 ('cells/01/cell-boundaries.json', ['public_after'], {'literal': 'changed'}),
                 ('cells/01/cell-boundaries.json', ['equality'], False),
                 ('cells/01/cell-start.json', ['conservation_before', 'inventory_count'], 68),
                 ('cells/01/cell-receipt.json', ['hook_restored'], False),
                 ('cells/01/cell-receipt.json', ['timer_restored'], False),
                 ('cells/01/cell-receipt.json', ['calls', 'candidate', 'returned'], False))
        for path, keys, value in cases:
            with self.subTest(path=path, keys=keys):
                self.rejected_mutation(path, keys, value)
        folder = self.bundle.root / 'cells/02'; path = folder / 'reference-return.json'; payload = read(path)
        payload['scientific']['guards'] = [{'literal': 'different reference scientific object'}]
        payload['scientific_sha256'] = c.digest(payload['scientific']); write(path, payload)
        self.reconfirm(2, 'reference'); self.bundle.refresh()
        with self.assertRaisesRegex(ValueError, 'independent science/RNG equality'):
            self.bundle.verify()

    def reconfirm(self, index, scope):
        folder = self.bundle.root / 'cells' / f'{index:02d}'; path = folder / (scope + '-return.json')
        evidence = {'path': path.relative_to(self.bundle.root).as_posix(), **c.file_info(path)}
        write(folder / (scope + '-capture-confirmed.json'), evidence)
        receipt = read(folder / 'cell-receipt.json'); receipt['calls'][scope]['evidence'] = evidence
        write(folder / 'cell-receipt.json', receipt)

    def test_V10_required_accounting_and_timing(self):
        cases = (('cells/02/active-call.json', ['active'], True),
                 ('cells/02/unmeasured-accounting.json', ['physical_cost'], {}),
                 ('cells/01/whole-wrapper-resources.json', ['operations', 'previews'], 1))
        for path, keys, value in cases:
            with self.subTest(path=path):
                self.rejected_mutation(path, keys, value)
        for value in (0, -1, 360, True):
            with self.subTest(timing=value):
                path = self.bundle.root / 'cells/02/candidate-return.json'; original = path.read_bytes()
                payload = read(path); payload['timing']['cpu_seconds'] = value; write(path, payload)
                self.reconfirm(2, 'candidate'); self.bundle.refresh()
                with self.assertRaises((ValueError, c.ResourceExceeded)):
                    self.bundle.verify()
                path.write_bytes(original); self.reconfirm(2, 'candidate'); self.bundle.refresh()
        path = self.bundle.root / 'cells/01/decision-traces/pass-2/11.jsonl'
        lines = v.rows(path); lines[1]['audit']['boundary']['choice_calls'] = 1
        write(path, b''.join(c.canonical(row) for row in lines), raw=True); self.bundle.refresh()
        with self.assertRaises((ValueError, c.ResourceExceeded)):
            self.bundle.verify()

    def set_u_cpu(self, first, second):
        for identity in c.SCHEDULE:
            if identity['condition'] == 'U' and identity['size'] in (40, 48):
                for scope in ('candidate', 'reference'):
                    path = self.bundle.root / 'cells' / f"{identity['cell']:02d}" / (scope + '-return.json')
                    payload = read(path); payload['timing']['cpu_seconds'] = first if identity['repetition'] == 1 else second
                    write(path, payload); self.reconfirm(identity['cell'], scope)
        self.bundle.refresh()

    def test_V11_joint_threshold_inclusive(self):
        self.set_u_cpu(9, 7)
        verified = self.bundle.verify(); custody = self.bundle.custody(verified)
        report = self.bundle.timing(verified, custody)
        self.assertEqual(report['classification'], 'profile_overhead_material')
        self.assertEqual(report['primary_U_over_P_CPU'], {'40': .8, '48': .8})
        self.assertEqual(report['repetition_matched_U_over_P_CPU']['40/repetition-1'], .9)
        self.assertEqual(len(report['cells']), 20)

    def test_V12_each_joint_threshold_failure(self):
        for first, second in ((8.01, 8.01), (9.01, 6)):
            with self.subTest(first=first, second=second):
                self.set_u_cpu(first, second)
                verified = self.bundle.verify(); custody = self.bundle.custody(verified)
                self.assertEqual(self.bundle.timing(verified, custody)['classification'], 'profile_overhead_not_material')

    def test_V13_revalidate_complete_evidence_binding(self):
        verified = self.bundle.verify(); custody = self.bundle.custody(verified)
        fabricated = {'complete': True, 'cells': verified['cells'], 'raw_inventory': verified['raw_inventory']}
        with self.assertRaises((ValueError, c.ResourceExceeded)):
            self.bundle.timing(fabricated, custody)
        forged = copy.deepcopy(verified); forged['cells'][0]['candidate']['cpu_seconds'] = .1
        with self.assertRaises((ValueError, c.ResourceExceeded)):
            self.bundle.timing(forged, custody)
        self.bundle.mutate('supervisor-cell-01.json', ['output_prefix_gap'], True)
        with self.assertRaises((ValueError, c.ResourceExceeded)):
            self.bundle.timing(verified, custody)

    def test_V14_external_custody_gate(self):
        verified = self.bundle.verify(); custody = self.bundle.custody(verified)
        with self.assertRaises(TypeError):
            v.timing_report(verified, authenticated_custody_receipt=custody)
        with self.assertRaises((ValueError, c.ResourceExceeded)):
            self.bundle.timing(verified, custody, trusted_custody_sha256='f' * 64)
        for keys, value in ((['status'], 'pending'), (['status'], 'blocked'), (['folder_id'], 'other-folder'),
                            (['verification_sha256'], 'f' * 64), (['raw_inventory'], []), (['files'], [])):
            with self.subTest(keys=keys, value=value):
                altered = copy.deepcopy(custody); set_nested(altered, keys, value)
                write(self.bundle.custody_path, altered)
                with self.assertRaises((ValueError, c.ResourceExceeded)):
                    self.bundle.timing(verified, altered)
        write(self.bundle.custody_path, custody)
        altered = copy.deepcopy(custody); altered['authenticated_by'] = 'self-described-untrusted'
        with self.assertRaises((ValueError, c.ResourceExceeded)):
            self.bundle.timing(verified, altered)

    def test_V15_exact_readback_provenance_and_files(self):
        verified = self.bundle.verify(); custody = self.bundle.custody(verified)
        variants = ((['files', 0, 'size'], 1), (['files', 0, 'sha256'], 'f' * 64),
                    (['files', 0, 'drive_file_id'], ''), (['files', 0, 'direct_url'], 'https://example.com/file'),
                    (['files', 0, 'download_receipt', 'event_id'], 'literal-upload-event'),
                    (['files', 0, 'download_receipt', 'completed_at'], '2026-10-02T00:00:00Z'),
                    (['files', 0, 'upload_receipt', 'parent_folder_id'], 'wrong-folder'),
                    (['files', 0, 'readback_path'], custody['files'][0]['upload_input_path']),
                    (['transport_manifest', 'files'], []))
        for keys, value in variants:
            with self.subTest(keys=keys):
                altered = copy.deepcopy(custody); set_nested(altered, keys, value)
                write(self.bundle.custody_path, altered)
                with self.assertRaises((ValueError, c.ResourceExceeded)):
                    self.bundle.timing(verified, altered)
        write(self.bundle.custody_path, custody)
        path = Path(custody['files'][0]['readback_path']); original = path.read_bytes()
        path.write_bytes(b'corrupt literal downloaded bytes')
        with self.assertRaises((ValueError, c.ResourceExceeded)):
            self.bundle.timing(verified, custody)
        path.write_bytes(original); path.unlink()
        with self.assertRaises((ValueError, OSError)):
            self.bundle.timing(verified, custody)


    def test_V16_closing_phase_proof(self):
        path=self.bundle.root/'measurement-phase-close.json';original=path.read_bytes()
        path.unlink()
        with self.assertRaises(FileNotFoundError):self.bundle.verify()
        path.write_bytes(original)
        for key,value in (('computational_receipt',{'path':'receipt.json','size_bytes':1,'sha256':'0'*64}),
                          ('preservation_deadline_monotonic',10601),('includes_computational_receipt_publication',False)):
            with self.subTest(key=key):
                data=c.strict_json(original);data[key]=value;write(path,data)
                with self.assertRaises(ValueError):self.bundle.verify()
        data=c.strict_json(original);data['phase']['cpu_seconds']=1800;write(path,data)
        with self.assertRaises(c.ResourceExceeded):self.bundle.verify()
        path.write_bytes(original);self.assertTrue(self.bundle.verify()['complete'])


    def test_V17_closing_totals_are_reported(self):
        result=self.bundle.verify();closing=read(self.bundle.root/'measurement-phase-close.json')
        self.assertEqual(result['resource_phase'],closing['phase'])
        self.assertEqual(result['prepublication_resource_phase'],read(self.bundle.root/'receipt.json')['resource_totals']['phase'])
        self.assertGreater(result['resource_phase']['cpu_seconds'],result['prepublication_resource_phase']['cpu_seconds'])
        self.assertGreater(result['resource_phase']['wall_seconds'],result['prepublication_resource_phase']['wall_seconds'])
    def test_V18_matched_clock_error_types(self):
        path=self.bundle.root/'cells/02/candidate-return.json';original=path.read_bytes()
        for value,kind in ((360,c.ResourceExceeded),(361,c.ResourceExceeded),('360',c.IntegrityError),
                           (True,c.IntegrityError),(0,c.IntegrityError),(-1,c.IntegrityError),(10**400,c.IntegrityError)):
            with self.subTest(value=str(value)[:20]):
                payload=c.strict_json(original);payload['timing']['cpu_seconds']=value;write(path,payload)
                self.reconfirm(2,'candidate');self.bundle.refresh()
                with self.assertRaises(kind):self.bundle.verify()
        path.write_bytes(original);self.reconfirm(2,'candidate');self.bundle.refresh()
        self.assertTrue(self.bundle.verify()['complete'])


    def test_V19_recovery_loader_runtime_binding(self):
        self.assertTrue(self.bundle.verify()['complete'])
        cases = (
            ('null_loader', 'update', ['runtime', 'loader'], None),
            ('portable_substitute', 'update', ['runtime', 'loader'], LOADER_PIN),
            ('wrong_schema', 'update', ['runtime', 'loader', 'schema'], 'untrusted-loader'),
            ('missing_mapping', 'delete', ['runtime', 'loader', 'mapped_library'], None),
            ('wrong_library_hash', 'update', ['runtime', 'loader', 'library_sha256'], 'e' * 64),
            ('boolean_library_size', 'update', ['runtime', 'loader', 'library_size_bytes'], True),
            ('wrong_executable_path', 'update', ['runtime', 'loader', 'executable_path'], '/ambient/python'),
            ('wrong_mapped_inode', 'update', ['runtime', 'loader', 'mapped_library', 'inode'], 5678),
            ('wrong_mapped_device', 'update', ['runtime', 'loader', 'mapped_library', 'device'], {'major': 8, 'minor': 2}),
            ('wrong_loader_environment', 'update', ['runtime', 'loader', 'loader_environment'], {'LD_LIBRARY_PATH': '/ambient/lib'}),
            ('extra_identity_field', 'update', ['runtime', 'loader', 'extra'], False),
            ('different_runtime_executable', 'update', ['runtime', 'executable'], '/ambient/python'))
        self.assertEqual(len(cases), 12)
        for name in ('source-runtime-preflight.json', 'cells/02/source-runtime-preflight.json'):
            path = self.bundle.root / name; original = path.read_bytes()
            try:
                for label, action, keys, replacement in cases:
                    with self.subTest(record=name, case=label):
                        value = c.strict_json(original)
                        if action == 'delete':
                            parent = value
                            for key in keys[:-1]:
                                parent = parent[key]
                            del parent[keys[-1]]
                        else:
                            set_nested(value, keys, copy.deepcopy(replacement))
                        write(path, value); self.bundle.refresh()
                        with self.assertRaises(c.IntegrityError):
                            self.bundle.verify()
            finally:
                path.write_bytes(original); self.bundle.refresh()
        path = self.bundle.root / 'cells/02/source-runtime-preflight.json'; original = path.read_bytes()
        try:
            value = c.strict_json(original)
            value['runtime']['loader']['library_inode'] = 5678
            value['runtime']['loader']['mapped_library']['inode'] = 5678
            write(path, value); self.bundle.refresh()
            with self.assertRaisesRegex(c.IntegrityError, 'parent/child loader mapped identity'):
                self.bundle.verify()
        finally:
            path.write_bytes(original); self.bundle.refresh()
        self.assertTrue(self.bundle.verify()['complete'])

    def test_V20_supervisor_preservation_boundary_consistency(self):
        path = self.bundle.root / 'supervisor-cell-01.json'
        original = path.read_bytes()
        self.assertTrue(self.bundle.verify()['complete'])
        flags = ('preservation_transition_attempted', 'preservation_transition_complete',
                 'preservation_expired', 'preservation_blocked')
        failure = {'status': 'resource_incomplete', 'reason': 'literal_preservation_failure'}
        cases = [('missing_' + key, 'delete', {key: None})
                 for key in ('preservation_deadline_monotonic', *flags)]
        cases += [('nonnull_deadline_' + repr(value), 'update', {'preservation_deadline_monotonic': value})
                  for value in (0, 10000, '10000', False)]
        cases += [('wrong_' + key + '_' + repr(value), 'update', {key: value})
                  for key in flags for value in (True, None, 0, 'false')]
        cases += [('forbidden_' + key + '_' + repr(value), 'update', {key: value})
                  for key in ('first_terminal_failure', 'preservation_boundary_failure')
                  for value in (None, failure)]
        cases.append(('contradictory_completed_record', 'update', {
            'preservation_deadline_monotonic': 10000,
            'preservation_transition_attempted': True, 'preservation_transition_complete': True,
            'first_terminal_failure': failure}))
        self.assertEqual(len(cases), 30)
        try:
            for name, action, changes in cases:
                with self.subTest(case=name):
                    value = c.strict_json(original)
                    if action == 'delete':
                        for key in changes:
                            del value[key]
                    else:
                        value.update(changes)
                    write(path, value)
                    self.bundle.refresh()
                    with self.assertRaisesRegex(c.IntegrityError, 'preservation-boundary evidence'):
                        self.bundle.verify()
        finally:
            path.write_bytes(original)
            self.bundle.refresh()
        self.assertTrue(self.bundle.verify()['complete'])

    def test_V21_supervisor_partial_spawn_consistency(self):
        path = self.bundle.root / 'supervisor-cell-01.json'
        original = path.read_bytes()
        self.assertTrue(self.bundle.verify()['complete'])
        true_flags = ('spawn_attempted', 'spawn_initialization_complete')
        cases = [('missing_' + key, 'delete', {key: None})
                 for key in (*true_flags, 'spawn_ownership_uncertain')]
        cases += [('wrong_' + key + '_' + repr(value), 'update', {key: value})
                  for key in true_flags for value in (False, None, 1, 'true')]
        cases += [('wrong_uncertainty_' + repr(value), 'update', {'spawn_ownership_uncertain': value})
                  for value in (True, None, 0, 'false')]
        cases += [
            ('partial_constructor_contradiction', 'update', {
                'spawn_attempted': True, 'spawn_initialization_complete': False,
                'spawn_ownership_uncertain': True}),
            ('unattempted_constructor_contradiction', 'update', {
                'spawn_attempted': False, 'spawn_initialization_complete': False,
                'spawn_ownership_uncertain': False})]
        cases += [('missing_' + key, 'delete', {key: None})
                  for key in ('spawn_discovery', 'spawn_recovered_pids')]
        cases += [('wrong_discovery_' + repr(value), 'update', {'spawn_discovery': value})
                  for value in (None, False, 'initialized', 'recovered')]
        cases += [('wrong_recovered_pids_' + repr(value), 'update', {'spawn_recovered_pids': value})
                  for value in (None, False, 0, {}, '[]', [123])]
        cases.append(('recovery_diagnostics_contradiction', 'update', {
            'spawn_discovery': 'recovered', 'spawn_recovered_pids': [123]}))
        self.assertEqual(len(cases), 30)
        try:
            for name, action, changes in cases:
                with self.subTest(case=name):
                    value = c.strict_json(original)
                    if action == 'delete':
                        for key in changes:
                            del value[key]
                    else:
                        value.update(changes)
                    write(path, value)
                    self.bundle.refresh()
                    with self.assertRaisesRegex(c.IntegrityError, 'spawn-ownership evidence'):
                        self.bundle.verify()
        finally:
            path.write_bytes(original)
            self.bundle.refresh()
        self.assertTrue(self.bundle.verify()['complete'])

    def test_V22_recovery_loader_admission_and_helper_pin(self):
        self.assertTrue(self.bundle.verify()['complete'])
        original_go = copy.deepcopy(self.bundle.go)
        stub_path = self.bundle.root / 'stub-test-receipt.json'; original_stub = stub_path.read_bytes()
        cases = ('missing_loader_pin', 'full_identity_in_go', 'extra_portable_field',
                 'changed_library_hash', 'changed_library_size', 'missing_loader_shell_pin',
                 'missing_loader_shell_test_pin')
        self.assertEqual(len(cases), 7)
        try:
            for label in cases:
                with self.subTest(case=label):
                    self.bundle.go = copy.deepcopy(original_go); stub_path.write_bytes(original_stub)
                    if label == 'missing_loader_pin':
                        del self.bundle.go['loader_pin']
                    elif label == 'full_identity_in_go':
                        self.bundle.go['loader_pin'] = copy.deepcopy(LOADER_IDENTITY)
                    elif label == 'extra_portable_field':
                        self.bundle.go['loader_pin']['extra'] = False
                    elif label == 'changed_library_hash':
                        self.bundle.go['loader_pin']['library_sha256'] = 'e' * 64
                    elif label == 'changed_library_size':
                        self.bundle.go['loader_pin']['library_size_bytes'] = 12346
                    elif label == 'missing_loader_shell_pin':
                        del self.bundle.go['diagnostic_files_sha256']['scripts/worker36-loader.sh']
                    else:
                        stub = c.strict_json(original_stub)
                        del stub['checked_file_sha256']['scripts/worker36-loader.sh']
                        write(stub_path, stub)
                        self.bundle.go['stub_test_receipt_sha256'] = c.file_info(stub_path)['sha256']
                    if label in ('missing_loader_pin', 'full_identity_in_go', 'extra_portable_field'):
                        # Invalid GO cannot produce authenticated evidence. Its
                        # authoritative admission rejection is the expected gate.
                        with self.assertRaises(a.AdmissionError):
                            self.bundle.write_auth()
                        continue
                    with self.assertRaises((c.IntegrityError, a.AdmissionError, KeyError)):
                        self.bundle.write_auth()
                        self.bundle.mutate('receipt.json', ['admission_sha256'], c.sha(self.bundle.admission.read_bytes()))
                        self.bundle.verify()
        finally:
            self.bundle.go = original_go; stub_path.write_bytes(original_stub); self.bundle.write_auth()
            self.bundle.mutate('receipt.json', ['admission_sha256'], c.sha(self.bundle.admission.read_bytes()))
        self.assertTrue(self.bundle.verify()['complete'])


    def rewrite_rows(self, relative, edit):
        path = self.bundle.root / relative
        values = v.rows(path); edit(values)
        write(path, b''.join(c.canonical(row) for row in values), raw=True)
        self.bundle.refresh()

    def reject_row_mutation(self, relative, edit, error=c.IntegrityError):
        path = self.bundle.root / relative; original = path.read_bytes()
        try:
            self.rewrite_rows(relative, edit)
            with self.assertRaises(error):
                self.bundle.verify()
        finally:
            path.write_bytes(original); self.bundle.refresh()

    def test_JR01_exact_successful_journal_schema(self):
        verified = self.bundle.verify()
        calls = v.rows(self.bundle.root / 'cells/01/call-results/pass-2/11.jsonl')
        self.assertEqual(set(calls[0]), {'ordinal', 'scope', 'result'})
        self.assertEqual(set(calls[0]['result']), {'chosen', 'cost', 'scientific'})
        self.assertEqual(set(calls[1]['result']), {'chosen', 'cost', 'scientific_sha256'})
        self.assertEqual(len(verified['cells']), 20)
        self.assertIn('scientific', read(self.bundle.root / 'cells/01/reference-return.json'))

    def test_JR02_identical_reference_science_contradiction(self):
        for index in (1, 20):
            def edit(rows):
                science = copy.deepcopy(rows[0]['result']['scientific'])
                science['guards'] = [{'literal': 'contradictory reference object'}]
                rows[1]['result']['scientific'] = science
            self.rewrite_rows(f'cells/{index:02d}/call-results/pass-2/11.jsonl', edit)
        with self.assertRaises(c.IntegrityError):
            self.bundle.verify()

    def test_JR03_matching_extra_reference_science_rejected(self):
        def edit(rows):
            rows[1]['result']['scientific'] = copy.deepcopy(rows[0]['result']['scientific'])
        self.reject_row_mutation('cells/01/call-results/pass-2/11.jsonl', edit)

    def test_JR04_reference_digest_required_and_bound(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                def edit(rows):
                    if missing:
                        del rows[1]['result']['scientific_sha256']
                    else:
                        rows[1]['result']['scientific_sha256'] = 'e' * 64
                self.reject_row_mutation('cells/01/call-results/pass-2/11.jsonl', edit)

    def test_JR05_chosen_bound_to_each_full_sidecar(self):
        for index in (0, 1):
            with self.subTest(scope=index):
                def edit(rows):
                    rows[index]['result']['chosen'] = {'literal': 'different chosen value'}
                self.reject_row_mutation('cells/01/call-results/pass-2/11.jsonl', edit)

    def test_JR06_ordinal_scope_and_exact_result_keys(self):
        for index in (0, 1):
            for kind in ('changed_ordinal', 'missing_ordinal', 'wrong_scope', 'extra_result_key'):
                with self.subTest(scope=index, kind=kind):
                    def edit(rows):
                        if kind == 'changed_ordinal':
                            rows[index]['ordinal'] = 2
                        elif kind == 'missing_ordinal':
                            del rows[index]['ordinal']
                        elif kind == 'wrong_scope':
                            rows[index]['scope'] = 'control'
                        else:
                            rows[index]['result']['extra'] = False
                    self.reject_row_mutation('cells/01/call-results/pass-2/11.jsonl', edit)

    def test_JR07_full_reference_sidecar_still_required(self):
        path = self.bundle.root / 'cells/01/reference-return.json'; original = path.read_bytes()
        for kind in ('missing', 'corrupt'):
            with self.subTest(kind=kind):
                if kind == 'missing':
                    path.unlink()
                else:
                    path.write_bytes(b'{')
                self.bundle.refresh()
                with self.assertRaises((ValueError, OSError)):
                    self.bundle.verify()
                path.write_bytes(original); self.bundle.refresh()
        self.assertTrue(self.bundle.verify()['complete'])

    def test_MR01_complete_original_metric_fields(self):
        result = self.bundle.verify()
        metrics = v.rows(self.bundle.root / 'cells/01/resource-metrics.jsonl')
        for scope, metric in zip(('candidate', 'reference'), metrics):
            self.assertEqual(v._decision_metric(metric, scope=scope), 1000)
        self.assertEqual(len(result['cells']), 20)

    def test_MR02_inclusive_clock_and_uncapped_rss_fields(self):
        metrics = v.rows(self.bundle.root / 'cells/01/resource-metrics.jsonl')
        for scope, original in zip(('candidate', 'reference'), metrics):
            for key in ('wall_seconds', 'cpu_seconds'):
                for value in (0, 360):
                    with self.subTest(scope=scope, key=key, value=value):
                        metric = copy.deepcopy(original); metric[key] = value
                        self.assertEqual(v._decision_metric(metric, scope=scope), 1000)
            for value in (0, 1000, 600000):
                with self.subTest(scope=scope, rss=value):
                    metric = copy.deepcopy(original); metric['peak_rss_kib'] = value
                    self.assertEqual(v._decision_metric(metric, scope=scope), value)
        # Coherent high-water samples above AS/1024 must not create a new RSS cap.
        self.rewrite_rows('cells/01/resource-metrics.jsonl',
                          lambda rows: [row.update(peak_rss_kib=600000) for row in rows])
        self.bundle.mutate('cells/01/whole-wrapper-resources.json', ['peak_rss_kib'], 600001)
        self.bundle.mutate('cells/01/cell-receipt.json', ['peak_rss_kib'], 600002)
        self.bundle.mutate('supervisor-cell-01.json', ['child_high_water_rss_kib'], 600003)
        self.assertTrue(self.bundle.verify()['complete'])

    def test_MR03_missing_malformed_and_over_cap_metrics(self):
        for index in (0, 1):
            for key in ('wall_seconds', 'cpu_seconds', 'peak_rss_kib'):
                cases = ('missing', -1, True, None, '0', 1.5) if key == 'peak_rss_kib' else ('missing', -1, True, None, '0', 360.000001)
                for replacement in cases:
                    with self.subTest(scope=index, key=key, value=replacement):
                        def edit(rows):
                            if replacement == 'missing':
                                del rows[index][key]
                            else:
                                rows[index][key] = replacement
                        expected = c.ResourceExceeded if key != 'peak_rss_kib' and replacement == 360.000001 else c.IntegrityError
                        self.reject_row_mutation('cells/01/resource-metrics.jsonl', edit, expected)

    def test_MR04_metric_identity_fields(self):
        for index in (0, 1):
            for key, replacement in (('kind', 'policy'), ('pass', 3), ('seed', 12),
                                     ('ordinal', 2), ('scope', 'control'), ('status', 'failed')):
                with self.subTest(scope=index, key=key):
                    self.reject_row_mutation('cells/01/resource-metrics.jsonl',
                                              lambda rows: rows[index].update({key: replacement}))

    def test_MR05_identical_invalid_repeated_metrics(self):
        for index in (1, 20):
            self.rewrite_rows(f'cells/{index:02d}/resource-metrics.jsonl',
                              lambda rows: [row.update(wall_seconds=-1) for row in rows])
        with self.assertRaises(c.IntegrityError):
            self.bundle.verify()

    def test_MR06_nonfinite_and_huge_integer_metrics(self):
        path = self.bundle.root / 'cells/01/resource-metrics.jsonl'; original = path.read_bytes()
        for token in (b'NaN', b'Infinity', b'-Infinity'):
            with self.subTest(token=token):
                path.write_bytes(original.replace(b'"wall_seconds":13', b'"wall_seconds":' + token, 1))
                self.bundle.refresh()
                with self.assertRaises(c.IntegrityError):
                    self.bundle.verify()
                path.write_bytes(original); self.bundle.refresh()
        self.reject_row_mutation('cells/01/resource-metrics.jsonl',
                                  lambda rows: rows[0].update(cpu_seconds=10 ** 400))

    def test_MR07_true_integer_monotonic_high_water(self):
        participants = (('candidate', 'cells/01/resource-metrics.jsonl', 0, 'peak_rss_kib'),
                        ('reference', 'cells/01/resource-metrics.jsonl', 1, 'peak_rss_kib'),
                        ('wrapper', 'cells/01/whole-wrapper-resources.json', None, 'peak_rss_kib'),
                        ('cell', 'cells/01/cell-receipt.json', None, 'peak_rss_kib'),
                        ('supervisor', 'supervisor-cell-01.json', None, 'child_high_water_rss_kib'))
        for name, relative, row, key in participants:
            for value in (-1, True, None, 1.5, '1000'):
                with self.subTest(participant=name, value=value):
                    if row is not None:
                        self.reject_row_mutation(relative, lambda rows: rows[row].update({key: value}))
                    else:
                        self.rejected_mutation(relative, [key], value)
        for name, relative, row, key in participants[:-1]:
            with self.subTest(decreasing_after=name):
                if row is not None:
                    self.reject_row_mutation(relative, lambda rows: rows[row].update({key: 1001}))
                else:
                    self.rejected_mutation(relative, [key], 1001)

    def test_MR08_method_rows_and_unmeasured_flags_unchanged(self):
        verified = self.bundle.verify(); custody = self.bundle.custody(verified)
        report = self.bundle.timing(verified, custody)
        self.assertEqual(report['cells'], verified['cells'])
        self.assertEqual(len(report['cells']), 20)
        self.assertEqual(read(self.bundle.root / 'cells/02/unmeasured-accounting.json'), c.U_FLAGS)
        self.assertEqual(report['classification'], 'profile_overhead_material')

    def test_PW01_complete_wrapper_final_classification(self):
        verified = self.bundle.verify(); custody = self.bundle.custody(verified)
        report = self.bundle.timing(verified, custody)
        self.assertEqual(report['classification'], 'profile_overhead_material')
        self.assertEqual(len(report['provider_wrappers']), 1)
        self.assertIs(report['provider_wrappers'][0]['external_origin_authenticated'], False)

    def test_PW02_wrapper_coverage_is_mandatory(self):
        verified = self.bundle.verify(); custody = self.bundle.custody(verified)
        for kind in ('missing', 'null', 'empty'):
            with self.subTest(kind=kind):
                changed = copy.deepcopy(custody)
                if kind == 'missing':
                    del changed['provider_wrappers']
                else:
                    changed['provider_wrappers'] = None if kind == 'null' else []
                write(self.bundle.custody_path, changed)
                with self.assertRaises((c.IntegrityError, t.TransportError)):
                    self.bundle.timing(verified, changed)

    def test_PW13_outer_wrapper_is_not_canonical_part(self):
        verified = self.bundle.verify(); custody = self.bundle.custody(verified)
        outer = Path(custody['provider_wrappers'][0]['path']).read_bytes()
        for key in ('upload_input_path', 'readback_path'):
            Path(custody['files'][0][key]).write_bytes(outer)
        with self.assertRaises(c.IntegrityError):
            self.bundle.timing(verified, custody)

    def test_PW14_exact_and_semantic_wrapper_binding(self):
        verified = self.bundle.verify(); custody = self.bundle.custody(verified)
        changed = copy.deepcopy(custody)
        changed['provider_wrappers'][0]['download_receipt']['run_id'] = '999'
        with self.assertRaises(c.IntegrityError):
            self.bundle.timing(verified, changed)
        write(self.bundle.custody_path, changed)
        with self.assertRaises(t.TransportError):
            self.bundle.timing(verified, changed)

    def test_PW15_legacy_custody_is_not_accepted(self):
        verified = self.bundle.verify(); custody = self.bundle.custody(verified)
        custody['schema'] = 'worker36-authenticated-custody-v1'
        write(self.bundle.custody_path, custody)
        with self.assertRaises(c.IntegrityError):
            self.bundle.timing(verified, custody)


    def test_ER_I02_retained_prerequisites_replayed_offline(self):
        for name in a.PREREQUISITE_NAMES:
            with self.subTest(input=name):
                external = self.bundle.auth / name
                retained = self.bundle.root / 'admission-inputs' / name
                original = external.read_bytes(); provenance_bytes = self.bundle.provenance.read_bytes()
                try:
                    if name == 'preflight.zip':
                        changed = b'fixed literal corrupt prerequisite ZIP'
                    else:
                        value = c.strict_json(original)
                        if name.startswith('review-'):
                            value['body'] = 'fixed literal unstructured review statement'
                        elif name == 'preflight-run.json':
                            value['status'] = 'in_progress'
                        else:
                            value['expired'] = True
                        changed = c.canonical(value)
                    external.write_bytes(changed); retained.write_bytes(changed)
                    provenance = c.strict_json(provenance_bytes)
                    provenance['admission_input_hashes'][name] = c.sha(changed)
                    write(self.bundle.provenance, provenance)
                    write(self.bundle.root / 'admission-inputs' / self.bundle.provenance.name, provenance)
                    self.bundle.refresh()
                    # Even updated local hash metadata and earlier validated
                    # descriptor flags cannot replace replay of the raw proofs.
                    with self.assertRaises((a.AdmissionError, c.IntegrityError)):
                        self.bundle.verify()
                finally:
                    external.write_bytes(original); retained.write_bytes(original)
                    self.bundle.provenance.write_bytes(provenance_bytes)
                    (self.bundle.root / 'admission-inputs' / self.bundle.provenance.name).write_bytes(provenance_bytes)
                    self.bundle.refresh()
        self.assertTrue(self.bundle.verify()['complete'])

if __name__ == '__main__':
    unittest.main()
