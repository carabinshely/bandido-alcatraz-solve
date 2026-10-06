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
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from worker38 import admission as a
from worker38 import common as c
from worker38 import verify as v
from worker38 import transport as t
from worker38 import sources as sources

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
INHERITED = {'RLIMIT_AS': [-1, -1], 'RLIMIT_CORE': [0, -1], 'RLIMIT_CPU': [-1, -1], 'RLIMIT_DATA': [-1, -1], 'RLIMIT_FSIZE': [-1, -1], 'RLIMIT_MEMLOCK': [67108864, 67108864], 'RLIMIT_MSGQUEUE': [819200, 819200], 'RLIMIT_NICE': [0, 0], 'RLIMIT_NOFILE': [1048576, 1048576], 'RLIMIT_NPROC': [127622, 127622], 'RLIMIT_OFILE': [1048576, 1048576], 'RLIMIT_RSS': [-1, -1], 'RLIMIT_RTPRIO': [0, 0], 'RLIMIT_RTTIME': [-1, -1], 'RLIMIT_SIGPENDING': [127622, 127622], 'RLIMIT_STACK': [8388608, -1]}
ORIGINAL = '/invented-cache/worker38-synthetic-profile/allocations/worker38-synthetic-profile-01/run-123-attempt-1'
SCRIPT = '/invented-checkout/scripts/run_worker38_synthetic.py'
SOURCE_BYTES = b'# Fixed invented inert source; never imported.\n'
TESTED_EXTRA_PATHS = ('tests/test_worker37_bootstrap.py', 'tests/test_worker38_bootstrap_integration.py', 'tests/test_worker38_cell_integration.py', 'tests/test_worker38_core.py', 'tests/test_worker38_driver_integration.py', 'tests/test_worker38_supervision.py', 'tests/test_worker38_transport.py', 'tests/test_worker38_verify_integration.py', 'tests/worker38_constructor_source.txt', 'tests/worker38_literal_fixtures.py', 'evidence-design/run-worker38-fixed-preparation.py', 'evidence-design/worker38-fixed-fixtures.json')
LOADER_PIN = {'schema': 'worker38-loader-pin-v1', 'executable_sha256': c.RUNTIME['executable_sha256'],
              'library_relative_path': 'Python/3.11.16/x64/lib/libpython3.11.so.1.0',
              'library_sha256': 'ba4450817186fbe1e3c477f6aefeee7c353cba3593cc9950382ad9d1f5e62896', 'library_size_bytes': 23041360}
LOADER_IDENTITY = {
    'schema': 'worker38-loader-identity-v1', 'tool_cache': '/invented-cache',
    'executable_path': '/invented-cache/Python/3.11.16/x64/bin/python3.11',
    'executable_sha256': c.RUNTIME['executable_sha256'],
    'library_relative_path': 'Python/3.11.16/x64/lib/libpython3.11.so.1.0',
    'library_path': '/invented-cache/Python/3.11.16/x64/lib/libpython3.11.so.1.0',
    'library_directory': '/invented-cache/Python/3.11.16/x64/lib',
    'library_sha256': 'ba4450817186fbe1e3c477f6aefeee7c353cba3593cc9950382ad9d1f5e62896', 'library_size_bytes': 23041360,
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
SOURCE_MODULES = (('src/bandido_alcatraz/__init__.py', 'bandido_alcatraz'), ('src/bandido_alcatraz/board.py', 'bandido_alcatraz.board'), ('src/bandido_alcatraz/deck_data.py', 'bandido_alcatraz.deck_data'), ('src/bandido_alcatraz/game.py', 'bandido_alcatraz.game'), ('src/bandido_alcatraz/model.py', 'bandido_alcatraz.model'), ('src/bandido_alcatraz/moves.py', 'bandido_alcatraz.moves'), ('src/bandido_alcatraz/photo_geometry.py', 'bandido_alcatraz.photo_geometry'), ('src/bandido_alcatraz/physical_deck.py', 'bandido_alcatraz.physical_deck'), ('src/bandido_alcatraz/policies.py', 'bandido_alcatraz.policies'), ('src/bandido_alcatraz/quota_reserve_closure.py', 'bandido_alcatraz.quota_reserve_closure'), ('src/bandido_alcatraz/quota_reserve_closure_reference.py', 'bandido_alcatraz.quota_reserve_closure_reference'), ('src/bandido_alcatraz/rules.py', 'bandido_alcatraz.rules'), ('src/bandido_alcatraz/setup.py', 'bandido_alcatraz.setup'), ('src/bandido_alcatraz/simulate.py', 'bandido_alcatraz.simulate'), ('src/bandido_alcatraz/strategy.py', 'bandido_alcatraz.strategy'), ('src/bandido_alcatraz/worker32/__init__.py', 'bandido_alcatraz.worker32'), ('src/bandido_alcatraz/worker32/evidence.py', 'bandido_alcatraz.worker32.evidence'), ('scripts/benchmark_worker35_synthetic.py', 'benchmark_worker35_synthetic'), ('scripts/run_quota_reserve_closure_development.py', 'run_quota_reserve_closure_development'), ('scripts/worker31_geometry.py', 'worker31_geometry'), ('scripts/worker35_resources.py', 'worker35_resources'))
INITIAL_MODULES = ('bandido_alcatraz', 'bandido_alcatraz.board', 'bandido_alcatraz.game', 'bandido_alcatraz.model', 'bandido_alcatraz.moves', 'bandido_alcatraz.policies', 'bandido_alcatraz.quota_reserve_closure', 'bandido_alcatraz.quota_reserve_closure_reference', 'bandido_alcatraz.rules', 'bandido_alcatraz.setup', 'bandido_alcatraz.strategy', 'bandido_alcatraz.worker32', 'bandido_alcatraz.worker32.evidence', 'benchmark_worker35_synthetic', 'run_quota_reserve_closure_development', 'worker35_resources')


# Only the separately approved native runner installs this fixed evidence hook.
# Ordinary CI never copies an overwritten receipt through this boundary.
PRODUCTION_OUTPUT_HOOK = None
CURRENT_PRODUCTION_SELECTOR = None
# Only these adopted native selectors may construct an input witness.
# Shared helpers used by F07 and ordinary CI emit no input-identity event.
INPUT_WITNESS_SELECTORS = frozenset((
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V01_complete_literal_bundle',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V02_external_admission_binding',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V03_authenticated_freeze_pins',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V04_parent_source_preflight',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V05_cell_module_manifest',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V06_exact_runtime_policy',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V07_supervision_and_logs_required_for_every_cell',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V08_parent_totals_errors_inventory',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V09_science_rng_capture_boundary',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V10_required_accounting_and_timing',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V11_joint_threshold_inclusive',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V12_each_joint_threshold_failure',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V13_revalidate_complete_evidence_binding',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V14_external_custody_gate',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V15_exact_readback_provenance_and_files',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V16_closing_phase_proof',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V17_closing_totals_are_reported',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V18_matched_clock_error_types',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V19_recovery_loader_runtime_binding',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V20_supervisor_preservation_boundary_consistency',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V21_supervisor_partial_spawn_consistency',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_V22_recovery_loader_admission_and_helper_pin',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_JR01_exact_successful_journal_schema',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_JR02_identical_reference_science_contradiction',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_JR03_matching_extra_reference_science_rejected',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_JR04_reference_digest_required_and_bound',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_JR05_chosen_bound_to_each_full_sidecar',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_JR06_ordinal_scope_and_exact_result_keys',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_JR07_full_reference_sidecar_still_required',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_MR01_complete_original_metric_fields',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_MR02_inclusive_clock_and_uncapped_rss_fields',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_MR03_missing_malformed_and_over_cap_metrics',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_MR04_metric_identity_fields',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_MR05_identical_invalid_repeated_metrics',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_MR06_nonfinite_and_huge_integer_metrics',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_MR07_true_integer_monotonic_high_water',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_MR08_method_rows_and_unmeasured_flags_unchanged',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_PW01_complete_wrapper_final_classification',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_PW02_wrapper_coverage_is_mandatory',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_PW13_outer_wrapper_is_not_canonical_part',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_PW14_exact_and_semantic_wrapper_binding',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_PW15_legacy_custody_is_not_accepted',
    'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.test_ER_I02_retained_prerequisites_replayed_offline',
))
CUSTODY_VERSION_LABELS = {
    'test_V14_external_custody_gate': (
        'V14-custody-before-02', 'V14-custody-before-03', 'V14-custody-before-04',
        'V14-custody-before-05', 'V14-custody-before-06', 'V14-custody-before-07',
        'V14-custody-before-08'),
    'test_V15_exact_readback_provenance_and_files': (
        'V15-custody-before-02', 'V15-custody-before-03', 'V15-custody-before-04',
        'V15-custody-before-05', 'V15-custody-before-06', 'V15-custody-before-07',
        'V15-custody-before-08', 'V15-custody-before-09', 'V15-custody-before-10',
        'V15-custody-before-11'),
    'test_PW02_wrapper_coverage_is_mandatory': (
        'PW02-custody-before-02', 'PW02-custody-before-03', 'PW02-custody-before-04'),
    'test_PW14_exact_and_semantic_wrapper_binding': ('PW14-custody-before-02',),
    'test_PW15_legacy_custody_is_not_accepted': ('PW15-custody-before-02',),
}
_CUSTODY_VERSION_COUNTS = {}


def preserve_existing_observed_custody(path):
    """Retain one actual observed version before this fixed helper overwrites it."""
    if PRODUCTION_OUTPUT_HOOK is None:
        return
    if path.name != 'externally-authenticated-custody.json' or path.is_symlink():
        raise AssertionError('unsafe native observed-custody path')
    if not path.exists():
        return
    prefix = 'tests/test_worker38_verify_integration.py:VerifyIntegrationTests.'
    selector = CURRENT_PRODUCTION_SELECTOR
    if not isinstance(selector, str) or not selector.startswith(prefix):
        raise AssertionError('native custody overwrite requires its exact registered selector')
    method = selector[len(prefix):]
    labels = CUSTODY_VERSION_LABELS.get(method, ())
    ordinal = _CUSTODY_VERSION_COUNTS.get(selector, 0)
    if path.parent.name != 'custody-inputs-1' or ordinal >= len(labels):
        raise AssertionError('unregistered native observed-custody overwrite')
    PRODUCTION_OUTPUT_HOOK(selector, [{
        'event': 'preserve_observed_version', 'path': str(path),
        'label': labels[ordinal], 'maximum_bytes': 131072}])
    # A failed synchronous capture must leave the original receipt untouched.
    _CUSTODY_VERSION_COUNTS[selector] = ordinal + 1


def write(path, value, raw=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.name == 'externally-authenticated-custody.json':
        preserve_existing_observed_custody(path)
    path.write_bytes(value if raw else c.canonical(value))


def read(path):
    return c.strict_json(path.read_bytes())


def set_nested(value, keys, replacement):
    for key in keys[:-1]:
        value = value[key]
    value[keys[-1]] = replacement


CUSTODY_INPUT_CASES = frozenset((
    'test_V11_joint_threshold_inclusive', 'test_V12_each_joint_threshold_failure',
    'test_V13_revalidate_complete_evidence_binding', 'test_V14_external_custody_gate',
    'test_V15_exact_readback_provenance_and_files', 'test_MR08_method_rows_and_unmeasured_flags_unchanged',
    'test_PW01_complete_wrapper_final_classification', 'test_PW02_wrapper_coverage_is_mandatory',
    'test_PW13_outer_wrapper_is_not_canonical_part', 'test_PW14_exact_and_semantic_wrapper_binding',
    'test_PW15_legacy_custody_is_not_accepted'))


class LiteralBundle:
    def __init__(self, base, *, driver_target=None, custody_case=None):
        self.base = Path(base)
        self.driver_target = driver_target is not None
        if custody_case is not None and (custody_case not in CUSTODY_INPUT_CASES or self.driver_target):
            raise ValueError('only the closed offline literal cases may freeze independent custody inputs')
        base_text = str(self.base.absolute())
        if custody_case is not None and (len(base_text) > 60 or any(character not in
                '/.-_0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz' for character in base_text)):
            raise ValueError('fixed independent custody fixture base must be<=60literalASCIIpathbytes')
        self.custody_case = custody_case
        self.custody_input_versions = []
        self._frozen_custody = None
        self._custody_lineage = None
        self.cache = '/invented-cache'
        self.source_path = str(Path(SCRIPT).parent.parent)
        if self.driver_target:
            # F07 alone reuses this same fixed20-cell literal cohort at the
            # actual driver target. All paths remain temporary test inputs.
            self.root = Path(driver_target).absolute()
            self.cache = str(self.root.parents[3])
            expected = (Path(self.cache) / 'worker38-synthetic-profile' / 'allocations' /
                        'worker38-synthetic-profile-01' / 'run-123-attempt-1')
            if self.root != expected or self.root.resolve() != self.root or str(self.root) != ORIGINAL:
                raise ValueError('fixed canonical F07 target and matching ORIGINAL literal required')
            if LOADER_IDENTITY['tool_cache'] != self.cache:
                raise ValueError('F07 loader literal must use the same canonical cache')
            for directory in (Path(self.cache), *reversed(self.root.parents[:3])):
                directory.mkdir(mode=0o700, parents=True, exist_ok=True)
                directory.chmod(0o700)
            self.root.mkdir(mode=0o700)
        else:
            self.root = self.base / 'raw-attempt'
            self.root.mkdir()
        self.auth = self.base / 'external-auth'; self.auth.mkdir()
        self.admission = self.auth / 'admission.json'; self.provenance = self.auth / 'provenance.json'
        files = []
        for path, module in SOURCE_MODULES:
            write(self.root / 'restored' / path, SOURCE_BYTES, raw=True)
            files.append({'path': path, 'module': module, 'size_bytes': len(SOURCE_BYTES),
                          'sha256': c.sha(SOURCE_BYTES),
                          'git_blob': hashlib.sha1(b'blob ' + str(len(SOURCE_BYTES)).encode() + b'\0' + SOURCE_BYTES).hexdigest()})
        self.manifest = {'schema': 'worker38-comparator-closure-v1', 'repository': c.REPOSITORY,
                         'historical_commit': c.HISTORICAL, 'files': files}
        write(self.root / 'source-manifest.json', self.manifest)
        diagnostic = {name: 'a' * 64 for name in a.REQUIRED_PRODUCTION_PATHS + a.METADATA_PATHS}
        diagnostic['experiments/worker38-synthetic-profile/PROTOCOL.md'] = c.PROTOCOL_SHA256
        diagnostic['experiments/worker38-synthetic-profile/INTEGRATION-CONTRACT.json'] = c.CONTRACT_SHA256
        diagnostic['experiments/worker38-synthetic-profile/FINITE-PREPARATION-PLAN.json'] = c.FINITE_PLAN_SHA256
        diagnostic['experiments/worker38-synthetic-profile/comparator-source-manifest.json'] = c.file_info(self.root / 'source-manifest.json')['sha256']
        diagnostic.update({'experiments/worker38-synthetic-profile/inputs/comparator-7ac2f62c/' +
                           entry['path'] + '.blob': entry['sha256'] for entry in files})
        diagnostic['experiments/worker38-synthetic-profile/upload-amendment/AMENDMENT.md'] = c.UPLOAD_AMENDMENT_SHA256
        diagnostic['experiments/worker38-synthetic-profile/upload-amendment/AMENDMENT-CONTRACT.json'] = c.UPLOAD_CONTRACT_SHA256
        diagnostic['experiments/worker38-synthetic-profile/upload-amendment/FINITE-COVERAGE-AMENDMENT.json'] = c.UPLOAD_FINITE_PLAN_SHA256
        diagnostic.update(a.UPLOAD_RECORD_PINS)
        tested_sources = {**diagnostic, **{path: 'c' * 64 for path in TESTED_EXTRA_PATHS}}
        stub = {'success': True, 'checked_file_sha256': tested_sources, 'candidate_evaluator_calls': 0,
                'reference_evaluator_calls': 0, 'measurement_fixture_constructions': 0,
                'historical_source_imports': 0, 'games': 0, 'failures': 0, 'errors': 0}
        write(self.root / 'stub-test-receipt.json', stub)
        self.go = {'schema': 'worker38-one-shot-admission-v1', 'admitted': True,
                   'repository': c.REPOSITORY, 'branch': a.BRANCH, 'preregistration_url': c.PREREGISTRATION,
                   'protocol_sha256': c.PROTOCOL_SHA256, 'admission_url': a.WEB + '/pull/40',
                   'head': HEAD, 'tree': TREE, 'runner': 'bandido-alcatraz-ci',
                   'runtime': c.RUNTIME, 'loader_pin': copy.deepcopy(LOADER_PIN), 'resources': c.RESOURCES, 'schedule': list(c.SCHEDULE),
                   'maximum_evaluator_calls': 40, 'games': 0,
                   'source_manifest_sha256': diagnostic['experiments/worker38-synthetic-profile/comparator-source-manifest.json'],
                   'diagnostic_files_sha256': diagnostic,
                   'cell_preflight_modules': sorted(INITIAL_MODULES),
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
        parent_runtime['address_space'] = [512 * 1024 ** 2] * 2; parent_runtime['inherited_limits'] = INHERITED
        write(self.root / 'source-runtime-preflight.json', {'phase': 'source_runtime_preflight', 'evaluator_starts': 0,
              'runtime': parent_runtime, 'coordinator_address_space': [512 * 1024 ** 2] * 2,
              'restored_source_inventory': files, 'diagnostic_files_sha256': diagnostic,
              'measurement_anchor': self.measurement_anchor,
              'timer_control': [{'deadline': 11140, 'before': 9340, 'after': 9340.001, 'requested': 1799.999,
                  'observed_before': 9340, 'observed_after': 9340.001, 'observed_countdown': 1799.998,
                  'observed_interval': 0.0, 'alarm_handler_confirmed': True, 'usr1_handler_confirmed': True,
                  'other_timers_idle': True, 'owner_pid': 1000}]})
        for identity in c.SCHEDULE:
            self.cell(identity)
        self.receipt = {'schema': 'worker38-attempt-v1', 'status': 'execution_complete',
                        'phase': 'verification_pending', 'admission_verified': True,
                        'admission_sha256': c.sha(self.admission.read_bytes()), 'diagnostic_head': HEAD,
                        'diagnostic_tree': TREE, 'attempt_id': 'worker38-123-1', 'attempt_path': ORIGINAL,
                        'runner': 'bandido-alcatraz-ci', 'workflow_run': '123', 'workflow_attempt': '1',
                        'preregistration_url': c.PREREGISTRATION,
                        'source_manifest_sha256': self.go['source_manifest_sha256'], 'resources': c.RESOURCES,
                        'games': 0, 'schedule': list(c.SCHEDULE), 'maximum_evaluator_calls': 40,
                        'actual_starts': 40, 'actual_starts_upper_bound': 40, 'pre_call_markers': 40, 'actual_returns': 40, 'confirmed_captures': 40,
                        'current_cell': None, 'completed_prefix': list(range(1, 21)), 'capture_gaps': [], 'corrupt_evidence': [], 'unavailable_evidence': [], 'retained_failures': [],
                        'custody': 'pending', 'classification': None, 'supervisor_pid': 1000, 'supervisor_start_ticks': 934000,
                        'measurement_anchor': self.measurement_anchor,
                        'runtime_scope': {'idle_gate_passed': True, 'timer_owned': True, 'original_deadline': 11140.0},
                        'resource_totals': {'supervision': read(self.root / 'supervisor-cell-20.json'),
                            'P_operations': {'legal_enumerations': 20, 'previews': 0, 'exit_geometry_checks': 0},
                            'phase': self.phase(21)}}
        write(self.root / 'receipt.json', self.receipt); self.refresh()

    def write_auth(self):
        from worker38_literal_fixtures import literal_bundle, write_literal_bundle
        # Invalid supplied fields remain invalid. The helper never replaces an
        # explicit pin with its own default or imports a historical test helper.
        a.admitted_loader_pin(self.go.get('loader_pin'))
        stub_path = self.root / 'stub-test-receipt.json'
        source = {'path': v.FOCUSED_SOURCE_RECEIPT, **c.file_info(stub_path)}
        checked = read(stub_path)['checked_file_sha256']
        bundle = literal_bundle(self.go, pr_number=40, owner_id=456,
            cache=self.cache, focused_source_receipt=source,
            checked_file_sha256=checked, workflow_run='123')
        bundle['context']['checkout_path'] = self.source_path
        self.go = bundle['go']
        write_literal_bundle(self.auth, bundle)
        write(self.root / 'external-admission.json', bundle['admission_raw'], raw=True)
        for name in ('event.json', 'request-context.json', *a.INPUT_NAMES,
                     self.admission.name, self.provenance.name):
            write(self.root / 'admission-inputs' / name, (self.auth / name).read_bytes(), raw=True)
        self.write_startup()

    def write_startup(self):
        # Administrative records below are invented observations only. No clock,
        # loader, process, network or scientific producer is invoked.
        runtime = {'implementation': 'cpython', 'version': '3.11.16',
            'inherited_limits': copy.deepcopy(INHERITED),
            'memory_cap': {'attempted': True, 'confirmed': True, 'readback': [536870912, 536870912]},
            'flags': {'optimize': 0, 'ignore_environment': 0, 'isolated': 0,
                      'no_site': 0, 'no_user_site': 1, 'dont_write_bytecode': 1},
            'state': {'limits': {**INHERITED, 'RLIMIT_AS': [536870912, 536870912]},
                      'gc_enabled': True, 'gc_threshold': [700, 10, 10], 'profile_idle': True,
                      'trace_idle': True, 'threads': 1, 'timers': [[0.0, 0.0]] * 3},
            'memory_cap_restoration': 'retained_until_leaf_process_exit',
            'files': {name: {'sha256': pin, 'size_bytes': size, 'device': 2049, 'inode': inode,
                'mtime_ns': 1, 'mapped_identity_confirmed': True,
                'observed_mapping': {'major': 8, 'minor': 1, 'inode': inode}}
                for name, pin, size, inode in (
                    ('executable', c.RUNTIME['executable_sha256'], 1234, 1233),
                    ('library', LOADER_PIN['library_sha256'], LOADER_PIN['library_size_bytes'], 1234))}}
        startup = {'schema': 'worker38-startup-receipt-v1', 'allocation_id': 'worker38-synthetic-profile-01',
            'admission_verified': True, 'classification': None, 'scientific_classification': None,
            'evaluator_starts': 0, 'actual_starts_upper_bound': 0, 'historical_source_imports': 0,
            'measurement_fixture_constructions': 0, 'games': 0, 'phase': 'admission_complete',
            'primary_failure': None, 'secondary_failures': [], 'transition_attempted': False,
            'first_failure_monotonic': None, 'preservation_deadline_monotonic': None,
            'requested_prefix': list(a.INPUT_NAMES), 'completed_prefix': list(a.INPUT_NAMES),
            'requests': [], 'response_body_bytes': 0, 'runtime': runtime, 'input_persistence': {},
            'admission_CPU_seconds': 1, 'admission_CPU_limit': [90, 90],
            'administrative_deadlines': {'startup_boottime_ns': 9300000000000,
                'startup_deadline_boottime_ns': 9420000000000,
                'admission_deadline_boottime_ns': 9400000000000,
                'observed_leaf_entry_boottime_ns': 9310000000000},
            'free_bytes_before_source': 1073741824,
            'restored_source_inventory': self.manifest['files']}
        for name in a.INPUT_NAMES:
            info = c.file_info(self.auth / name); size = info['size_bytes']
            startup['response_body_bytes'] += size
            startup['requests'].append({'name': name, 'status': 200, 'received_bytes': size,
                'buffered_bytes': size, 'retained_bytes': size, 'fsync_confirmed_bytes': size,
                'eof_confirmed': True, 'complete': True, 'close_confirmed': True, 'semantic_validated': True})
            startup['input_persistence'][name] = {**info, 'buffered_bytes': size,
                'fsync_confirmed_bytes': size, 'write_complete': True, 'file_fsync_confirmed': True,
                'directory_fsync_confirmed': True, 'readback_confirmed': True, 'close_confirmed': True}
        reservation = ('schema=worker38-observed-reservation-v1\nallocation_id=worker38-synthetic-profile-01\nrun_id=123\n'
            'run_attempt=1\nobserved_head=' + HEAD +
            '\ndescriptor_binding=not_yet_validated\nevaluator_starts=0\nscientific_classification=null\n').encode()
        write(self.root / 'reservation.txt', reservation, raw=True)
        write(self.root / 'admission-process-exit.txt', b'schema=worker38-admission-process-exit-v1\nexit_status=0\nadmission_process_returned=true\n', raw=True)
        if self.driver_target:
            write(self.root.parent / 'reservation.txt', reservation, raw=True)
        write(self.root / 'runtime.json', runtime)
        write(self.root / 'startup-receipt.json', startup)
        write(self.root / 'restored-inventory.json', self.manifest['files'])
        go = read(self.admission)
        handoff = {'schema': 'worker38-startup-handoff-v1', 'consumer': 'worker38-synthetic-profile-v1',
            'boot_id': '11111111-2222-3333-4444-555555555555',
            'measurement_monotonic_ns': 9340000000000, 'measurement_boottime_ns': 9340000000000,
            'measurement_deadline_monotonic_ns': 11140000000000, 'measurement_deadline_boottime_ns': 11140000000000,
            'attempt_path': ORIGINAL, 'source_path': self.source_path,
            'head': HEAD, 'tree': TREE, 'workflow_run': '123', 'workflow_attempt': '1',
            'admission_sha256': c.sha(self.admission.read_bytes()),
            'provenance_sha256': c.sha(self.provenance.read_bytes()),
            'runtime_sha256': c.file_info(self.root / 'runtime.json')['sha256'],
            'source_map_sha256': c.digest(go['checked_file_sha256']),
            'restored_inventory_sha256': c.digest(self.manifest['files']),
            'startup_receipt_sha256': c.file_info(self.root / 'startup-receipt.json')['sha256']}
        self.measurement_anchor = handoff
        write(self.root / 'startup-handoff.json', handoff)
        text = 'version=worker38-handoff-v1\nhandoff_sha256=' + c.digest(handoff) + '\n'
        text += ''.join(name + '=' + str(handoff[name]) + '\n' for name in a.HANDOFF_LINES)
        write(self.root / 'measurement-handoff.txt', text.encode('ascii'), raw=True)
        for name in ('receipt.json', 'source-runtime-preflight.json'):
            path = self.root / name
            if path.exists():
                record = read(path); record['measurement_anchor'] = handoff; write(path, record)

    def runtime(self, index=None):
        inherited = {**INHERITED, 'RLIMIT_AS': [536870912, 536870912], 'RLIMIT_CPU': [720, 720]} if index is not None else INHERITED
        observed = read(self.root / 'runtime.json')
        observed['inherited_limits'] = copy.deepcopy(inherited)
        observed['state']['limits'] = {**copy.deepcopy(inherited), 'RLIMIT_AS': [536870912, 536870912]}
        return {**c.RUNTIME, 'inherited_limits': copy.deepcopy(inherited),
                'shared_startup_observation': observed, 'executable': LOADER_IDENTITY['executable_path'],
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
                                                        if key in INITIAL_MODULES}})
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
                                        if key in INITIAL_MODULES or (identity['condition'] == 'P' and key == 'bandido_alcatraz.simulate')}}
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
        write(folder / 'cell-receipt.json', {**identity, 'schema': 'worker38-cell-receipt-v1', 'status': 'complete',
              'actual_starts': 2, 'actual_starts_upper_bound': 2, 'pre_call_markers': 2, 'invocation_attempts': 2, 'actual_returns': 2, 'confirmed_captures': 2, 'calls': calls,
              'hook_restored': True, 'timer_restored': True, 'peak_rss_kib': 1000,
              'classification': None, 'error_type': None, 'error': None,
              'failure': None, 'secondary_errors': [], 'phase': 'cell_complete'})
        log_name = f'supervisor-cell-{index:02d}.log'; write(self.root / log_name, b'', raw=True)
        supervisor = {'schema': 'worker38.supervision.v1', 'status': 'completed', 'reason': 'child_exit_zero',
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
        receipt['file_inventory'] = [x for x in self.literal_inventory() if x['path'] not in ('receipt.json','measurement-phase-close.json','coordinator-restoration.json','writer-exit-observation.json')]
        write(self.root / 'receipt.json', receipt)
        write(self.root/'measurement-phase-close.json',{
            'schema':'worker38-measurement-phase-close-v1','phase':self.phase(22),
            'computational_receipt':{'path':'receipt.json',**c.file_info(self.root/'receipt.json')},
            'includes_computational_receipt_publication':True,'closing_proof_included_in_measurement':False,
            'measurement_work_after_close':False,'no_measurement_after_close':True,'preservation_started_monotonic':10000,'preservation_deadline_monotonic':10600})
        write(self.root / 'coordinator-restoration.json', {
            'schema': 'worker38-coordinator-restoration-v1', 'owner_pid': 1000,
            'measurement_deadline_monotonic': 11140.0, 'preservation_deadline_monotonic': 10600,
            'timer_disabled': True, 'alarm_handler_restored': True, 'alarm_restoration_confirmed': True,
            'usr1_handler_restored': True, 'restoration_confirmed': True,
            'measurement_work_after_close': False, 'no_measurement_after_close': True})
        write(self.root / 'writer-exit-observation.json', {
            'schema': 'worker38-writer-exit-observation-v1', 'workflow_run': '123', 'workflow_attempt': '1',
            'admission_exit_receipt': {'path': 'admission-process-exit.txt',
                                     **c.file_info(self.root / 'admission-process-exit.txt')},
            'admission_exit_status': 0, 'coordinator_exit_status': 0, 'coordinator_state': 'exited',
            'coordinator_pid': 1000, 'coordinator_start_ticks': 934000,
            'parent_pid': 900, 'parent_start_ticks': 900000, 'no_measurement_after_close': True,
            'preservation_deadline_monotonic': 10600})

    def mutate(self, name, keys, value, refresh=True):
        path = self.root / name; data = read(path); set_nested(data, keys, value); write(path, data)
        if refresh:
            self.refresh()

    def verify(self, **overrides):
        if self.custody_case is not None:
            self.prepare_custody_inputs()
        args = {'trusted_admission_path': self.admission, 'trusted_admission_sha256': c.sha(self.admission.read_bytes()),
                'expected_head': HEAD, 'expected_tree': TREE, 'trusted_provenance_path': self.provenance,
                'trusted_provenance_sha256': c.sha(self.provenance.read_bytes()), 'expected_workflow_run': '123'}
        args.update(overrides)
        with mock.patch.object(sources, 'SOURCE_MANIFEST_SHA256', c.sha(c.canonical(self.manifest))):
            if PRODUCTION_OUTPUT_HOOK is not None and CURRENT_PRODUCTION_SELECTOR in INPUT_WITNESS_SELECTORS:
                PRODUCTION_OUTPUT_HOOK(CURRENT_PRODUCTION_SELECTOR, [{
                    'event': 'input_identity', 'boundary': 'LiteralBundle.verify',
                    'paths': {'attempt': str(self.root),
                        'trusted_admission': str(args['trusted_admission_path']) if args['trusted_admission_path'] is not None else None,
                        'trusted_provenance': str(args['trusted_provenance_path']) if args['trusted_provenance_path'] is not None else None}}])
            result = v.verify_attempt(self.root, **args)
        if self.custody_case is not None and result['raw_inventory'] != self._frozen_inventory:
            raise AssertionError('real verifier inventory differs from independently frozen literal inputs')
        return result

    def literal_inventory(self):
        # Test-input authority is the explicitly generated literal byte tree,
        # never a verifier result or production inventory function.
        records = []
        for path in sorted(self.root.rglob('*')):
            if path.is_symlink():
                raise AssertionError('literal input inventory cannot follow links')
            if path.is_file():
                raw = path.read_bytes()
                records.append({'path': path.relative_to(self.root).as_posix(),
                                'size_bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
        if sum(item['size_bytes'] for item in records) > 2 * 1024 ** 2:
            raise AssertionError('fixed offline literal input tree exceeded its prospective2MiB bound')
        return records

    def prepare_custody_inputs(self):
        if self.custody_case not in CUSTODY_INPUT_CASES or self.driver_target:
            raise AssertionError('independent custody fixture is not an observed-driver output route')
        inventory = self.literal_inventory()
        expected_paths = {'source-manifest.json', 'stub-test-receipt.json', 'external-admission.json',
            'source-runtime-preflight.json', 'receipt.json', 'measurement-phase-close.json',
            'coordinator-restoration.json', 'writer-exit-observation.json', 'reservation.txt',
            'admission-process-exit.txt', 'runtime.json', 'startup-receipt.json', 'restored-inventory.json',
            'startup-handoff.json', 'measurement-handoff.txt'}
        expected_paths.update('restored/' + path for path, _ in SOURCE_MODULES)
        expected_paths.update('admission-inputs/' + name for name in
                             ('event.json', 'request-context.json', *a.INPUT_NAMES, 'admission.json', 'provenance.json'))
        for identity in c.SCHEDULE:
            prefix = f"cells/{identity['cell']:02d}/"
            names = ['source-runtime-preflight.json', 'cell-start.json', 'cell-boundaries.json',
                     'active-call.json', 'cell-receipt.json']
            names += [scope + suffix for scope in ('candidate', 'reference') for suffix in
                      ('-start.json', '-return.json', '-capture-confirmed.json')]
            names += (['resource-metrics.jsonl', 'call-results/pass-2/11.jsonl',
                       'decision-traces/pass-2/11.jsonl', 'whole-wrapper-resources.json']
                      if identity['condition'] == 'P' else ['unmeasured-accounting.json'])
            expected_paths.update(prefix + name for name in names)
            expected_paths.update(f"supervisor-cell-{identity['cell']:02d}" + suffix for suffix in ('.json', '.log'))
        if len(expected_paths) != 357 or {entry['path'] for entry in inventory} != expected_paths:
            raise AssertionError('independent custody input must use the exact fixed357path roster')
        if self._frozen_custody is not None and inventory == self._frozen_inventory:
            return
        maximum = 2 if self.custody_case == 'test_V12_each_joint_threshold_failure' else 1
        if len(self.custody_input_versions) >= maximum:
            raise AssertionError('no additional custody input scenario is authorized')
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, 'w', compression=zipfile.ZIP_STORED) as archive:
            for entry in inventory:
                info = zipfile.ZipInfo(entry['path'], (1980, 1, 1, 0, 0, 0)); info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o600) << 16
                payload = (self.root / entry['path']).read_bytes()
                if len(payload) != entry['size_bytes'] or hashlib.sha256(payload).hexdigest() != entry['sha256']:
                    raise AssertionError('literal bytes changed during independent input freeze')
                archive.writestr(info, payload)
        raw = memory.getvalue()
        if len(raw) > 2 * 1024 ** 2:
            raise AssertionError('fixed custody input archive exceeds prospective2MiB fixture bound')
        self._custody_lineage = 'independent_literal_input'
        directory = self.base / ('custody-inputs-' + str(len(self.custody_input_versions) + 1))
        frozen = self._custody_artifacts(inventory, raw, directory)
        self._frozen_inventory = copy.deepcopy(inventory)
        self._frozen_custody = frozen
        expected_names = {'upload-part.bin', 'fresh-download-part.bin', 'github-provider-wrapper-001.zip',
                          'upload-transport-manifest.json', 'fresh-transport-manifest.json'}
        if {path.name for path in directory.iterdir()} != expected_names:
            raise AssertionError('independent custody input file roster drift')
        asset_pins = [{'path': path.name, 'size_bytes': len(path.read_bytes()),
                       'sha256': hashlib.sha256(path.read_bytes()).hexdigest()} for path in sorted(directory.iterdir())]
        self.custody_input_versions.append({'directory': str(directory),
            'inventory': copy.deepcopy(inventory), 'archive_size': len(raw), 'archive_sha256': c.sha(raw),
            'assets_frozen_before_verifier': asset_pins})

    def custody(self, verification):
        # Bulk bytes already existed before the actual verifier ran. Only this
        # small receipt now depends on its observed verification digest.
        if self._frozen_custody is None or verification['raw_inventory'] != self._frozen_inventory:
            raise AssertionError('actual verifier did not match the frozen input inventory')
        result = copy.deepcopy(self._frozen_custody)
        result['verification_sha256'] = verification['verification_sha256']
        if len(c.canonical(result)) > 128 * 1024:
            raise AssertionError('fixed observed custody receipt exceeds prospective128KiB output bound')
        write(self.custody_path, result)
        return result

    def custody_from_production(self, verification, transport_directory):
        # F07 exclusively uses real package outputs. Every archive/part/provider
        # and Drive copy derived here remains produced output in the byte map.
        if not self.driver_target or self.custody_case is not None:
            raise AssertionError('production custody route is fixed to actual F07 driver output')
        transport_directory = Path(transport_directory)
        manifest_raw = (transport_directory / 'transport-manifest.json').read_bytes()
        manifest = c.strict_json(manifest_raw)
        archive = (transport_directory / 'attempt.zip').read_bytes()
        if len(manifest['parts']) != 1 or (transport_directory / 'part-001.bin').read_bytes() != archive:
            raise AssertionError('fixed F07 literal cohort must retain its single real transport part')
        inventory = verification['raw_inventory']
        self._custody_lineage = 'production_output'
        result = self._custody_artifacts(inventory, archive, self.base / 'production-custody',
            produced_manifest=manifest, produced_manifest_raw=manifest_raw,
            produced_transport=transport_directory)
        if c.canonical(result['transport_manifest']) != manifest_raw:
            raise AssertionError('custody differs from actual original produced transport manifest')
        result['verification_sha256'] = verification['verification_sha256']
        write(self.custody_path, result)
        return result

    def _custody_artifacts(self, inventory, raw, directory, *, produced_manifest=None,
                          produced_manifest_raw=None, produced_transport=None):
        directory.mkdir(mode=0o700)
        downloaded = directory / 'fresh-download-part.bin'
        if self._custody_lineage == 'production_output':
            if produced_transport is None:
                raise AssertionError('F07 must use actual sealed transport upload inputs')
            upload = produced_transport / 'part-001.bin'
            if upload.read_bytes() != raw:
                raise AssertionError('actual sealed upload part changed before custody construction')
        else:
            if produced_transport is not None:
                raise AssertionError('independent literal inputs cannot use produced upload paths')
            upload = directory / 'upload-part.bin'
            write(upload, raw, raw=True)
        write(downloaded, raw, raw=True)
        part = {'order': 1, 'path': 'part-001.bin', 'size': len(raw), 'sha256': c.sha(raw)}
        file_id = 'literal-Drive-file-one'
        event = {'provider': 'google_drive', 'file_id': file_id, 'size': len(raw), 'sha256': c.sha(raw)}
        descriptor = {**part, 'drive_file_id': file_id, 'direct_url': 'https://drive.google.com/file/d/' + file_id + '/view',
                      'upload_input_path': str(upload), 'readback_path': str(downloaded),
                      'upload_receipt': {**event, 'operation': 'upload', 'event_id': 'literal-upload-event',
                                         'completed_at': '2026-10-03T00:00:00Z', 'parent_folder_id': v.CANONICAL_FOLDER},
                      'download_receipt': {**event, 'operation': 'download', 'event_id': 'literal-download-event',
                                           'completed_at': '2026-10-03T00:01:00Z'}}
        wrapper_path = directory / 'github-provider-wrapper-001.zip'
        provider_wrapper = {'order': 1, 'part_path': part['path'], 'member_name': part['path'],
            'path': str(wrapper_path), 'download_receipt': {'provider': 'github_actions', 'operation': 'download',
                'repository': c.REPOSITORY, 'run_id': '123', 'run_attempt': '1', 'artifact_id': '456',
                'artifact_name': 'worker38-123-1-part-001', 'event_id': 'literal-provider-download',
                'completed_at': '2026-10-03T00:00:00Z'}}
        result = {'schema': 'worker38-authenticated-custody-v2', 'status': 'verified',
                  'provider_wrappers': [provider_wrapper],
                  'provider_upload_outcome': {'schema': 'worker38-provider-upload-outcome-v1',
                      'workflow_run': '123', 'workflow_attempt': '1', 'action': './.github/actions/worker38-upload',
                      'status': 'completed', 'conclusion': 'success', 'admission_exit_status': 0,
                      'coordinator_exit_status': 0, 'preservation_exit_status': 0,
                      'started_at': '2026-10-02T23:59:58Z', 'completed_at': '2026-10-02T23:59:59Z'},
                  'authenticated_by': 'parent-connected-Drive-readback', 'folder_id': v.CANONICAL_FOLDER,
                  'verification_sha256': None, 'raw_inventory': inventory,
                  'files': [descriptor]}
        if self._custody_lineage == 'production_output':
            if produced_manifest is None or produced_manifest_raw is None:
                raise AssertionError('F07 must supply actual original manifest bytes')
            result['transport_manifest'] = copy.deepcopy(produced_manifest)
            manifest_raw = produced_manifest_raw
            expected_files = [{'path': x['path'], 'size': x['size_bytes'], 'sha256': x['sha256']} for x in inventory]
            if produced_manifest['files'] != expected_files or produced_manifest['parts'] != [part]:
                raise AssertionError('actual produced manifest does not bind the real verified raw inventory and part')
        else:
            if produced_manifest is not None or produced_manifest_raw is not None:
                raise AssertionError('independent literal input route cannot accept produced manifest bytes')
            result['transport_manifest'] = {'schema': 'worker38.transport.v1',
                'files': [{'path': x['path'], 'size': x['size_bytes'], 'sha256': x['sha256']} for x in inventory],
                'raw_size': sum(x['size_bytes'] for x in inventory), 'parts': [part],
                'archive': {'path': 'attempt.zip', 'format': 'zip-stored-v1', 'size': len(raw), 'sha256': c.sha(raw)},
                'limits': {'raw_bytes': 64 * 1024 ** 2, 'archive_bytes': 64 * 1024 ** 2,
                           'part_bytes': 30 * 1024 ** 2, 'provider_zip_strictly_below_bytes': 32 * 1024 ** 2}}
            manifest_raw = c.canonical(result['transport_manifest'])
        if self._custody_lineage == 'independent_literal_input' and len(manifest_raw) > 64 * 1024:
            raise AssertionError('fixed original custody manifest exceeds prospective64KiB input bound')
        with zipfile.ZipFile(wrapper_path, 'w', compression=zipfile.ZIP_STORED) as wrapper:
            for name, data in ((part['path'], raw), ('transport-manifest.json', manifest_raw)):
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)); info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o600) << 16
                wrapper.writestr(info, data)
        wrapper_info = {'size': wrapper_path.stat().st_size, 'sha256': c.sha(wrapper_path.read_bytes())}
        provider_wrapper.update(wrapper_info)
        provider_wrapper['download_receipt'].update(wrapper_info)
        manifest_readback = directory / 'fresh-transport-manifest.json'
        if self._custody_lineage == 'production_output':
            manifest_upload = produced_transport / 'transport-manifest.json'
            if manifest_upload.read_bytes() != manifest_raw:
                raise AssertionError('actual sealed upload manifest changed before custody construction')
        else:
            manifest_upload = directory / 'upload-transport-manifest.json'
            write(manifest_upload, manifest_raw, raw=True)
        write(manifest_readback, manifest_raw, raw=True)
        manifest_event = {'provider': 'google_drive', 'file_id': 'literal-Drive-manifest',
                          'size': len(manifest_raw), 'sha256': c.sha(manifest_raw)}
        result['manifest_file'] = {'path': 'transport-manifest.json', 'size': len(manifest_raw),
            'sha256': c.sha(manifest_raw), 'drive_file_id': 'literal-Drive-manifest',
            'direct_url': 'https://drive.google.com/file/d/literal-Drive-manifest/view',
            'upload_input_path': str(manifest_upload), 'readback_path': str(manifest_readback),
            'upload_receipt': {**manifest_event, 'operation': 'upload', 'event_id': 'literal-manifest-upload',
                'completed_at': '2026-10-03T00:00:00Z', 'parent_folder_id': v.CANONICAL_FOLDER},
            'download_receipt': {**manifest_event, 'operation': 'download', 'event_id': 'literal-manifest-readback',
                'completed_at': '2026-10-03T00:01:00Z'}}
        self.custody_path = directory / 'externally-authenticated-custody.json'
        if self._custody_lineage == 'independent_literal_input' and len(c.canonical(result)) + 64 > 128 * 1024:
            raise AssertionError('fixed custody receipt template exceeds prospective128KiB output bound')
        return result

    def timing(self, verification, custody, **overrides):
        args = {'authenticated_custody_receipt': custody, 'trusted_custody_path': self.custody_path,
                'trusted_custody_sha256': c.sha(self.custody_path.read_bytes())}
        args.update(overrides)
        with mock.patch.object(sources, 'SOURCE_MANIFEST_SHA256', c.sha(c.canonical(self.manifest))):
            if PRODUCTION_OUTPUT_HOOK is not None and CURRENT_PRODUCTION_SELECTOR in INPUT_WITNESS_SELECTORS:
                binding = verification.get('binding') if type(verification) is dict else None
                if type(binding) is not dict:
                    binding = {}
                PRODUCTION_OUTPUT_HOOK(CURRENT_PRODUCTION_SELECTOR, [{
                    'event': 'input_identity', 'boundary': 'LiteralBundle.timing',
                    'paths': {'attempt': str(binding['root']) if binding.get('root') is not None else None,
                        'trusted_admission': str(binding['trusted_admission_path']) if binding.get('trusted_admission_path') is not None else None,
                        'trusted_provenance': str(binding['trusted_provenance_path']) if binding.get('trusted_provenance_path') is not None else None,
                        'trusted_custody': str(args['trusted_custody_path']) if args['trusted_custody_path'] is not None else None}}])
            return v.timing_report(verification, **args)


class VerifyIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        custody_case = self._testMethodName if self._testMethodName in CUSTODY_INPUT_CASES else None
        self.bundle = LiteralBundle(self.temporary.name, custody_case=custody_case)

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
        # Same-attempt local validation is explicitly preliminary. It cannot
        # stand in for the separately authenticated off-runner acceptance gate.
        with mock.patch.object(sources, 'SOURCE_MANIFEST_SHA256', c.sha(c.canonical(self.bundle.manifest))):
            if PRODUCTION_OUTPUT_HOOK is not None and CURRENT_PRODUCTION_SELECTOR in INPUT_WITNESS_SELECTORS:
                PRODUCTION_OUTPUT_HOOK(CURRENT_PRODUCTION_SELECTOR, [{
                    'event': 'input_identity',
                    'boundary': 'VerifyIntegrationTests.test_V02_external_admission_binding',
                    'paths': {'attempt': str(self.bundle.root),
                        'trusted_admission': str(self.bundle.root / 'admission-inputs' / 'admission.json'),
                        'trusted_provenance': str(self.bundle.root / 'admission-inputs' / 'provenance.json')}}])
            local = v.verify_retained_attempt(self.bundle.root,
                admission_sha256=c.sha(self.bundle.admission.read_bytes()),
                provenance_sha256=c.sha(self.bundle.provenance.read_bytes()),
                expected_head=HEAD, expected_tree=TREE, expected_workflow_run='123')
        self.assertEqual(local['schema'], 'worker38-local-computational-verification-v1')
        self.assertEqual(local['authentication'], 'retained_bytes_only')
        self.assertIs(local['external_acceptance'], False)
        self.assertEqual(local['custody'], 'pending'); self.assertIsNone(local['classification'])
        self.assertNotIn('primary_U_over_P_CPU', local)
        with self.assertRaises(c.IntegrityError):
            v.timing_report(local, authenticated_custody_receipt={},
                trusted_custody_path=self.bundle.base / 'unused-custody.json', trusted_custody_sha256='0' * 64)
        for overrides in ({'trusted_admission_path': self.bundle.root / 'external-admission.json'},
                          {'trusted_admission_sha256': 'f' * 64}, {'expected_head': 'f' * 40},
                          {'expected_tree': 'f' * 40}, {'trusted_provenance_sha256': 'f' * 64},
                          {'expected_workflow_run': '999'}, {'expected_workflow_attempt': '2'}):
            with self.subTest(overrides=overrides), self.assertRaises((ValueError, OSError)):
                self.bundle.verify(**overrides)
        for keys, value in ((['attempt_id'], 'different'), (['attempt_path'], '/elsewhere/worker38-123-1'),
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
            value['runtime']['shared_startup_observation']['files']['library']['inode'] = 5678
            value['runtime']['shared_startup_observation']['files']['library']['observed_mapping']['inode'] = 5678
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
                        self.bundle.go['loader_pin']['library_size_bytes'] = 23041361
                    elif label == 'missing_loader_shell_pin':
                        del self.bundle.go['diagnostic_files_sha256']['scripts/worker_bootstrap_shared.sh']
                    else:
                        stub = c.strict_json(original_stub)
                        del stub['checked_file_sha256']['scripts/worker_bootstrap_shared.sh']
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
        custody['schema'] = 'worker38-authenticated-custody-v1'
        write(self.bundle.custody_path, custody)
        with self.assertRaises(c.IntegrityError):
            self.bundle.timing(verified, custody)


    def test_ER_I02_retained_prerequisites_replayed_offline(self):
        # Seven fixed semantic changes. All local byte-only bindings are updated
        # so only actual prerequisite reauthentication can reject these proofs.
        mutations = (
            ('pull-request.json', ('head', 'sha'), '3333333333333333333333333333333333333333', 'pr_head'),
            ('postmerge-ci.json', ('conclusion',), 'failure', 'ci_run_scope'),
            ('current-source-ci.json', ('head_sha',), '3333333333333333333333333333333333333333', 'ci_run_scope'),
            ('review-exhaustive.json', ('verdict',), 'not_clean', 'review_clean_exact_scope'),
            ('review-adversarial.json', ('native_reviewer_id',),
             self.bundle.go['reviews'][0]['native_reviewer_id'], 'review_clean_exact_scope'),
            ('preregistration.json', ('issue_url',), a.API + '/issues/101', 'comment_identity'),
            ('diagnostic-commit.json', ('tree', 'sha'), '4444444444444444444444444444444444444444', 'diagnostic_commit_tree'))
        self.assertEqual(tuple(row[0] for row in mutations), a.INPUT_NAMES)
        names = ('event.json', 'request-context.json', *a.INPUT_NAMES, 'admission.json', 'provenance.json')
        original = {name: (self.bundle.auth / name).read_bytes() for name in names}
        original_go = c.strict_json(original['admission.json'])
        for name, keys, replacement, expected_code in mutations:
            with self.subTest(input=name):
                self.assertTrue(self.bundle.verify()['complete'])
                corpus = dict(original)
                go = copy.deepcopy(original_go)
                value = c.strict_json(corpus[name])
                try:
                    if name in ('review-exhaustive.json', 'review-adversarial.json'):
                        prefix, suffix = a.REVIEW_START + '\n', a.REVIEW_END + '\n'
                        attestation = c.strict_json(value['body'][len(prefix):-len(suffix)])
                        set_nested(attestation, keys, replacement)
                        value['body'] = prefix + c.canonical(attestation).decode() + suffix
                        review_index = 0 if name == 'review-exhaustive.json' else 1
                        # Refresh only the raw body binding. Clean verdict,
                        # reviewer independence and head/tree remain fixed.
                        go['reviews'][review_index]['body_sha256'] = c.sha(value['body'].encode())
                        corpus['admission.json'] = c.canonical(go)
                        body = (a.START + '\n' + corpus['admission.json'].decode() + a.END + '\n' +
                                a.DIGEST + ': ' + c.sha(corpus['admission.json']) + '\n')
                        event = c.strict_json(corpus['event.json'])
                        pr = c.strict_json(corpus['pull-request.json'])
                        event['pull_request']['body'] = pr['body'] = body
                        corpus['event.json'] = c.canonical(event)
                        corpus['pull-request.json'] = c.canonical(pr)
                    else:
                        set_nested(value, keys, replacement)
                    corpus[name] = c.canonical(value)
                    provenance = c.strict_json(original['provenance.json'])
                    provenance['admission_sha256'] = c.sha(corpus['admission.json'])
                    provenance['body_sha256'] = c.sha(c.strict_json(corpus['event.json'])['pull_request']['body'].encode())
                    provenance['event_sha256'] = c.sha(corpus['event.json'])
                    provenance['request_context_sha256'] = c.sha(corpus['request-context.json'])
                    provenance['admission_input_hashes'] = {key: c.sha(corpus[key]) for key in a.INPUT_NAMES}
                    provenance['reviews'] = copy.deepcopy(go['reviews'])
                    corpus['provenance.json'] = c.canonical(provenance)
                    for key, raw in corpus.items():
                        write(self.bundle.auth / key, raw, raw=True)
                        write(self.bundle.root / 'admission-inputs' / key, raw, raw=True)
                    write(self.bundle.root / 'external-admission.json', corpus['admission.json'], raw=True)
                    self.bundle.write_startup()
                    self.bundle.mutate('receipt.json', ['admission_sha256'], c.sha(corpus['admission.json']))
                    self.assertIs(read(self.bundle.root / 'receipt.json')['admission_verified'], True)
                    # This is the actual offline verifier. The exact semantic
                    # error rules out a stale-hash or missing-file false positive.
                    with self.assertRaisesRegex(a.AdmissionError, '^' + expected_code + '$'):
                        self.bundle.verify()
                finally:
                    for key, raw in original.items():
                        write(self.bundle.auth / key, raw, raw=True)
                        write(self.bundle.root / 'admission-inputs' / key, raw, raw=True)
                    write(self.bundle.root / 'external-admission.json', original['admission.json'], raw=True)
                    self.bundle.write_startup()
                    self.bundle.mutate('receipt.json', ['admission_sha256'], c.sha(original['admission.json']))
                self.assertTrue(self.bundle.verify()['complete'])

if __name__ == '__main__':
    unittest.main()
