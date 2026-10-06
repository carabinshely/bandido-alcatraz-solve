"""Closed independent Worker38 literal source, never a test/preparation runner.

Authority 6003711624 and the bounded P14 amendment 6005833787 admit
source authoring and AST/hash/schema work only.
This source has NOT been run or imported. Independent materialization needs a
distinct reviewed grant bound to this source, final inputs, namespace and command.

The fixed transcriptions below build owned dictionaries. They do not import
candidate code, call its helpers or validators, interpret source ASTs, intercept
a filesystem, run tests/processes, or read observed outputs as expectations.
Every event must have one exact state. Any missing prerequisite fails closed.
"""
from __future__ import annotations
import argparse
import ast
import base64
import copy
import hashlib
import json
import re
import struct
import zlib
from pathlib import Path, PurePosixPath

SCHEMA = 'worker38-all-literal-recipes-v1'
ADOPTION_ID = 6003711624
REPAIRED_HANDOFF_SHA256 = '0673afc331cc2394a51864d1d7541c40f0036b7adf6b936552c390be6ce23210'
MAP_LIMIT = 8388608
CAPS = {'methods':397,'bash_cases':25,'generic_roots':45,'existing_descendants':2,
        'seconds':600,'address_space_bytes':536870912,'prefix_bytes':25165824,
        'log_bytes':8388608,'prefix_reserve_bytes':65536}

class ClosurePrerequisite(ValueError):
    pass

def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('utf-8')

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def digest(value):
    return sha(canonical(value))

def case_root(ctx, ordinal):
    if type(ordinal) is not int or not 1 <= ordinal <= 397:
        raise ClosurePrerequisite('ordinal outside original397 roster')
    return PurePosixPath(ctx['namespace']) / ('c%04d' % ordinal)

def source_literal(ctx, path, assignment_name):
    # Direct literal extraction only, never names/calls/expressions/bodies.
    tree=ast.parse(ctx['source_bytes'][path],filename=path)
    matches=[n.value for n in tree.body if isinstance(n,ast.Assign) and
        any(isinstance(t,ast.Name) and t.id==assignment_name for t in n.targets)]
    if len(matches)!=1:
        raise ClosurePrerequisite('ambiguous literal '+path+':'+assignment_name)
    if any(not isinstance(n,(ast.Constant,ast.List,ast.Tuple,ast.Dict,ast.Set,ast.Load,ast.UnaryOp,ast.USub)) for n in ast.walk(matches[0])):
        raise ClosurePrerequisite('not direct literal '+path+':'+assignment_name)
    return ast.literal_eval(matches[0])

def set_nested(value, keys, replacement):
    for key in keys[:-1]:
        value=value[key]
    value[keys[-1]]=replacement

# Fixed constant and auth transcriptions. SOURCE_SPANS binds the original text.

C_MIB = 1024 ** 2

C_REPOSITORY = 'carabinshely/bandido-alcatraz-solve'

C_HISTORICAL = '7ac2f62c9c5c9dcac9ec9b8770382960f985acc2'

C_PREREGISTRATION = 'https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5987629515'

C_PROTOCOL_SHA256 = '17abf2d644106bb7c10fbec5481deb7da33e17867ee2f08ea065ca591e8499a7'

C_RUNTIME = {'implementation': 'CPython', 'version': '3.11.16', 'executable_sha256': 'a15ccdaf07655a8667a3687b13171486c9a265d92273ba3ad820fbb64d2cfecc'}

C_CONTRACT_SHA256 = '5830bcf1a85f00987e01621f5557f401bcd875bbede2cb34b5d9fd4080c50251'

C_FINITE_PLAN_SHA256 = '31ed253dafcfa502bbfa4d7dca9292e93de6e7b48e39a0e33336b6df894b35c9'

C_UPLOAD_AMENDMENT_SHA256 = 'a7a4041d39e77a9265b9a185015f15e56efab7fe66a7b336dcf619ebec410913'

C_UPLOAD_CONTRACT_SHA256 = 'b66fc26eba0141b61c21762e97432485bc3f7e896801550ba7b65c31118c86bb'

C_UPLOAD_FINITE_PLAN_SHA256 = '192f12b30c83237766f808f83eef21c07a295eefece4e6964535d14bf6b5d75b'

C_UPLOAD_ADOPTION = 5988411319

C_SOURCE_MANIFEST_SHA256 = '99afc71070445a1246216f8ed8ff68a2125d95bc2bce95debf77604d4505709b'

C_STARTUP_RESOURCES = {'P_decision_trace_bytes': 16777216, 'P_per_evaluator_operations': {'exit_geometry_checks': 16384, 'legal_enumerations': 32768, 'previews': 32768}, 'P_whole_wrapper_operations': {'exit_geometry_checks': 32768, 'legal_enumerations': 65536, 'previews': 65536}, 'TERM_grace_seconds': 0.1, 'active_call_record_bytes': 16384, 'admission_leaf_CPU_seconds': 90, 'admission_leaf_wall_seconds': 90, 'all_P_operation_sum_each_category': 1000000, 'call_CPU_seconds': 360, 'call_wall_seconds': 360, 'cap_exhaustion_time_comparison': 'New diagnostic evaluator/cell/measurement intervals: greater than or equal fails. Original P meter journal timing retains finite0..360 inclusive historical schema.', 'cell_CPU_seconds': 720, 'cell_kernel_RLIMIT_CPU': [720, 720], 'cell_wall_seconds': 720, 'checkout_wall_seconds': 60, 'complete_archive_bytes': 67108864, 'mandatory_cleanup_seconds': 5.0, 'maximum_transport_parts': 3, 'measurement_external_backstop_does_not_renew_preservation': True, 'measurement_external_kill_after_seconds': 600, 'measurement_external_timeout_duration_rule': 'Conservatively rounded remaining time to the immutable paired measurement deadline;1800 is a maximum, never a new interval from command launch. Unknown/expired handoff blocks launch.', 'measurement_external_timeout_foreground': True, 'measurement_external_timeout_signal': 'SIGUSR1', 'measurement_external_timeout_uses_original_remaining_deadline': True, 'measurement_external_timeout_wall_seconds': 1800, 'measurement_summed_parent_child_CPU_seconds': 1800, 'measurement_wall_seconds': 1800, 'new_preservation_budget_on_recovery': False, 'ordinary_output_truncation_allowed': False, 'original_P_RSS_rule': 'Nonnegative integer and same-child monotonic high-water consistency; no new physical RSS cap', 'original_P_journal_timing_inclusive_range_seconds': [0, 360], 'physical_RSS_limit_inferred_from_RLIMIT_AS': False, 'preservation_original_wall_seconds': 600, 'process_RLIMIT_AS': [536870912, 536870912], 'provider_upload_wall_seconds': 60, 'provider_wrapper_strictly_less_than_bytes': 33554432, 'raw_ordinary_bytes': 66060288, 'raw_total_bytes': 67108864, 'required_free_bytes': 1073741824, 'returned_roots': 16384, 'shared_shell_startup_wall_seconds': 30, 'single_JSONL_line_bytes': 8388608, 'startup_CPU_semantics': 'No independent aggregate shell/helper CPU promise. Helpers are finite and serialized under30wall; record observed CPU. This administrative envelope never changes scientific1800CPU.', 'startup_admission_outer_wall_seconds': 120, 'startup_timeout_still_running_during_measurement': False, 'sum_phase_caps_seconds': 2640, 'supervisor_poll_seconds': 0.02, 'terminal_total_bytes': 1048576, 'transport_part_bytes': 31457280, 'unallocated_workflow_margin_seconds': 60, 'workflow_wall_seconds': 2700}

C_OPS = ('legal_enumerations', 'previews', 'exit_geometry_checks')

C_OP_CAPS = dict(zip(C_OPS, (32768, 32768, 16384)))

C_CALL_CAPS = {**C_OP_CAPS, 'roots': 16384, 'wall_seconds': 360, 'cpu_seconds': 360}

C_RESOURCES = {'per_call': {k: dict(C_CALL_CAPS) for k in ('control', 'candidate', 'reference')}, 'whole_cell_wall_seconds': 720, 'whole_cell_cpu_seconds': 720, 'whole_wrapper_operations': {k: 2 * v for k, v in C_OP_CAPS.items()}, 'total_operations': dict.fromkeys(C_OPS, 1000000), 'measurement_wall_seconds': 1800, 'measurement_cpu_seconds': 1800, 'address_space_bytes': 512 * C_MIB, 'evidence_bytes': 64 * C_MIB, 'receipt_bytes': C_MIB, 'trace_bytes': 16 * C_MIB, 'line_bytes': 8 * C_MIB, 'archive_bytes': 64 * C_MIB, 'part_bytes': 30 * C_MIB, 'verification_wall_seconds': 600, 'workflow_minutes': 45, 'free_storage_bytes': 1024 * C_MIB}

C_U_FLAGS = {'physical_cost': None, 'physical_operation_caps_enforced': False, 'choice_events_observed': False, 'production_admissible': False}

C_SCHEDULE = tuple(({'cell': i + 1, 'repetition': rep, 'size': n, 'condition': condition} for i, (rep, n, condition) in enumerate([(1, n, c) for n in (0, 4, 8, 40, 48) for c in ('P', 'U')] + [(2, n, c) for n in (48, 40, 8, 4, 0) for c in ('U', 'P')])))

A_UPLOAD_AMENDMENT_SHA256=C_UPLOAD_AMENDMENT_SHA256

A_UPLOAD_CONTRACT_SHA256=C_UPLOAD_CONTRACT_SHA256

A_UPLOAD_FINITE_PLAN_SHA256=C_UPLOAD_FINITE_PLAN_SHA256

A_REPOSITORY = 'carabinshely/bandido-alcatraz-solve'

A_OWNER = 'carabinshely'

A_BRANCH = 'research/worker38-synthetic-profile'

A_CONSUMER = 'worker38-synthetic-profile-v1'

A_ALLOCATION = 'worker38-synthetic-profile-01'

A_RUNNER = 'bandido-alcatraz-ci'

A_BASE_HEAD = '6ff861bba828e78d8f5b75d8355f2f4a56018898'

A_BASE_TREE = '7a97c827c75c135d2fbbb5cd97873d1418e069fb'

A_CI_RUN = 37250449266

A_PROTOCOL_SHA256 = '17abf2d644106bb7c10fbec5481deb7da33e17867ee2f08ea065ca591e8499a7'

A_WEB = 'https://github.com/' + A_REPOSITORY

A_API = 'https://api.github.com/repos/' + A_REPOSITORY

A_PREREGISTRATION = A_WEB + '/issues/2#issuecomment-5987629515'

A_MARKER = 'WORKER38_SYNTHETIC_ADMISSION'

A_START, A_END, A_DIGEST = (A_MARKER + '_JSON', 'END_' + A_MARKER + '_JSON', A_MARKER + '_SHA256')

A_REVIEW_START, A_REVIEW_END = ('WORKER38_NATIVE_REVIEW_JSON', 'END_WORKER38_NATIVE_REVIEW_JSON')

A_INPUT_NAMES = ('pull-request.json', 'postmerge-ci.json', 'current-source-ci.json', 'review-exhaustive.json', 'review-adversarial.json', 'preregistration.json', 'diagnostic-commit.json')

A_LIBRARY_SHA256 = 'ba4450817186fbe1e3c477f6aefeee7c353cba3593cc9950382ad9d1f5e62896'

A_LIBRARY_SIZE = 23041360

A_EXPERIMENT = 'experiments/worker38-synthetic-profile/'

A_FOCUSED_SOURCE_RECEIPT = A_EXPERIMENT + 'focused-preparation-receipt.json'

A_METADATA_PATHS = (A_EXPERIMENT + 'PROTOCOL.md', A_EXPERIMENT + 'INTEGRATION-CONTRACT.json', A_EXPERIMENT + 'FINITE-PREPARATION-PLAN.json', A_EXPERIMENT + 'SOURCE-GROUNDING.json', A_EXPERIMENT + 'comparator-source-manifest.json')

A_REQUIRED_PRODUCTION_PATHS = ('.github/workflows/worker38-synthetic-profile.yml', 'scripts/worker_bootstrap_shared.sh', 'scripts/worker_bootstrap_shared.py', 'scripts/worker37-bootstrap.sh', 'scripts/worker37_bootstrap.py', 'scripts/worker38-bootstrap.sh', 'scripts/run_worker38_synthetic.py', 'scripts/worker38/__init__.py', 'scripts/worker38/admission.py', 'scripts/worker38/common.py', 'scripts/worker38/sources.py', 'scripts/worker38/supervision.py', 'scripts/worker38/cell.py', 'scripts/worker38/driver.py', 'scripts/worker38/transport.py', 'scripts/worker38/verify.py', '.github/actions/worker38-upload/action.yml')

A_UPLOAD_RECORD_PINS = {A_EXPERIMENT + 'upload-amendment/AMENDMENT.md': A_UPLOAD_AMENDMENT_SHA256, A_EXPERIMENT + 'upload-amendment/AMENDMENT-CONTRACT.json': A_UPLOAD_CONTRACT_SHA256, A_EXPERIMENT + 'upload-amendment/FINITE-COVERAGE-AMENDMENT.json': A_UPLOAD_FINITE_PLAN_SHA256, A_EXPERIMENT + 'upload-amendment/SOURCE-OBSERVATION.json': 'c0b2efd71fc498b6beb8dd8f5fc7b90c047a803c1e2003467978191911f5e9d8', A_EXPERIMENT + 'upload-amendment/REPAIR-DISPOSITION.json': 'f291ecfd3b5d10f96bb594f4e6945e0beef1625a2ecfa994368243897c2329a8', A_EXPERIMENT + 'upload-amendment/HANDOFF.json': '54e30bca1fb6c754c211f319789a018255113c35ade1dc0404c197d8c2b0adbe'}

A_METADATA_PATHS += tuple(A_UPLOAD_RECORD_PINS)

A_HANDOFF_LINES = ('boot_id', 'measurement_monotonic_ns', 'measurement_boottime_ns', 'measurement_deadline_boottime_ns', 'attempt_path', 'source_path', 'head', 'tree', 'admission_sha256', 'provenance_sha256', 'runtime_sha256', 'source_map_sha256')

F_HEAD = '1111111111111111111111111111111111111111'

F_TREE = '2222222222222222222222222222222222222222'

F_SOURCE_BYTES = b'INVENTED_SOURCE_BYTES_ONLY\n'

F_FIXED_INPUTS = ('pull-request.json', 'postmerge-ci.json', 'current-source-ci.json', 'review-exhaustive.json', 'review-adversarial.json', 'preregistration.json', 'diagnostic-commit.json')

F_OWNER = {'login': 'carabinshely', 'id': 456, 'type': 'User'}

F_LIBRARY_PIN = {'schema': 'worker38-loader-pin-v1', 'executable_sha256': C_RUNTIME['executable_sha256'], 'library_relative_path': 'Python/3.11.16/x64/lib/libpython3.11.so.1.0', 'library_sha256': A_LIBRARY_SHA256, 'library_size_bytes': A_LIBRARY_SIZE}

F_INITIAL_MODULES = ['bandido_alcatraz', 'bandido_alcatraz.board', 'bandido_alcatraz.game', 'bandido_alcatraz.model', 'bandido_alcatraz.moves', 'bandido_alcatraz.policies', 'bandido_alcatraz.quota_reserve_closure', 'bandido_alcatraz.quota_reserve_closure_reference', 'bandido_alcatraz.rules', 'bandido_alcatraz.setup', 'bandido_alcatraz.strategy', 'bandido_alcatraz.worker32', 'bandido_alcatraz.worker32.evidence', 'benchmark_worker35_synthetic', 'run_quota_reserve_closure_development', 'worker35_resources']

F_INHERITED_LIMITS = {'RLIMIT_AS': [-1, -1], 'RLIMIT_CORE': [0, -1], 'RLIMIT_CPU': [-1, -1], 'RLIMIT_DATA': [-1, -1], 'RLIMIT_FSIZE': [-1, -1], 'RLIMIT_MEMLOCK': [67108864, 67108864], 'RLIMIT_MSGQUEUE': [819200, 819200], 'RLIMIT_NICE': [0, 0], 'RLIMIT_NOFILE': [1048576, 1048576], 'RLIMIT_NPROC': [127622, 127622], 'RLIMIT_OFILE': [1048576, 1048576], 'RLIMIT_RSS': [-1, -1], 'RLIMIT_RTPRIO': [0, 0], 'RLIMIT_RTTIME': [-1, -1], 'RLIMIT_SIGPENDING': [127622, 127622], 'RLIMIT_STACK': [8388608, -1]}

V_HEAD = '1111111111111111111111111111111111111111'

V_TREE = '2222222222222222222222222222222222222222'

V_PUBLIC = {'literal': 'invented detached public object, not a game observation'}

V_RNG = [3, [101, 202, 303], None]

V_SCIENCE = {'schema': 'worker35-scientific-v1', 'input_before': None, 'input_after': None, 'roots': [], 'supply': {'literal': 'invented'}, 'tiers': {'T0': [], 'F': [], 'T': [], 'C': [], 'final': []}, 'guards': [], 'flags': {'reserve_filter_active': False, 'reserve_primary_tier_changed': False, 'closure_branch_selected': False, 'true_original_all_collect_crossover': False, 'reserve_filter_mediated_change': False}, 'chosen_index': None, 'chosen': None, 'rng_before': None, 'rng_after': None}

V_INHERITED = {'RLIMIT_AS': [-1, -1], 'RLIMIT_CORE': [0, -1], 'RLIMIT_CPU': [-1, -1], 'RLIMIT_DATA': [-1, -1], 'RLIMIT_FSIZE': [-1, -1], 'RLIMIT_MEMLOCK': [67108864, 67108864], 'RLIMIT_MSGQUEUE': [819200, 819200], 'RLIMIT_NICE': [0, 0], 'RLIMIT_NOFILE': [1048576, 1048576], 'RLIMIT_NPROC': [127622, 127622], 'RLIMIT_OFILE': [1048576, 1048576], 'RLIMIT_RSS': [-1, -1], 'RLIMIT_RTPRIO': [0, 0], 'RLIMIT_RTTIME': [-1, -1], 'RLIMIT_SIGPENDING': [127622, 127622], 'RLIMIT_STACK': [8388608, -1]}

V_ORIGINAL = '/invented-cache/worker38-synthetic-profile/allocations/worker38-synthetic-profile-01/run-123-attempt-1'

V_SCRIPT = '/invented-checkout/scripts/run_worker38_synthetic.py'

V_SOURCE_BYTES = b'# Fixed invented inert source; never imported.\n'

V_TESTED_EXTRA_PATHS = ('tests/test_worker37_bootstrap.py', 'tests/test_worker38_bootstrap_integration.py', 'tests/test_worker38_cell_integration.py', 'tests/test_worker38_core.py', 'tests/test_worker38_driver_integration.py', 'tests/test_worker38_supervision.py', 'tests/test_worker38_transport.py', 'tests/test_worker38_verify_integration.py', 'tests/worker38_constructor_source.txt', 'tests/worker38_literal_fixtures.py', 'evidence-design/run-worker38-fixed-preparation.py', 'evidence-design/worker38-fixed-fixtures.json')

V_LOADER_PIN = {'schema': 'worker38-loader-pin-v1', 'executable_sha256': C_RUNTIME['executable_sha256'], 'library_relative_path': 'Python/3.11.16/x64/lib/libpython3.11.so.1.0', 'library_sha256': 'ba4450817186fbe1e3c477f6aefeee7c353cba3593cc9950382ad9d1f5e62896', 'library_size_bytes': 23041360}

V_LOADER_IDENTITY = {'schema': 'worker38-loader-identity-v1', 'tool_cache': '/invented-cache', 'executable_path': '/invented-cache/Python/3.11.16/x64/bin/python3.11', 'executable_sha256': C_RUNTIME['executable_sha256'], 'library_relative_path': 'Python/3.11.16/x64/lib/libpython3.11.so.1.0', 'library_path': '/invented-cache/Python/3.11.16/x64/lib/libpython3.11.so.1.0', 'library_directory': '/invented-cache/Python/3.11.16/x64/lib', 'library_sha256': 'ba4450817186fbe1e3c477f6aefeee7c353cba3593cc9950382ad9d1f5e62896', 'library_size_bytes': 23041360, 'library_device': {'major': 8, 'minor': 1}, 'library_inode': 1234, 'mapped_library': {'path': '/invented-cache/Python/3.11.16/x64/lib/libpython3.11.so.1.0', 'device': {'major': 8, 'minor': 1}, 'inode': 1234}, 'loader_environment': {'LD_LIBRARY_PATH': '/invented-cache/Python/3.11.16/x64/lib'}}

V_IDENTITIES = ['literal01', 'literal02', 'literal03', 'literal04', 'literal05', 'literal06', 'literal07', 'literal08', 'literal09', 'literal10', 'literal11', 'literal12', 'literal13', 'literal14', 'literal15', 'literal16', 'literal17', 'literal18', 'literal19', 'literal20', 'literal21', 'literal22', 'literal23', 'literal24', 'literal25', 'literal26', 'literal27', 'literal28', 'literal29', 'literal30', 'literal31', 'literal32', 'literal33', 'literal34', 'literal35', 'literal36', 'literal37', 'literal38', 'literal39', 'literal40', 'literal41', 'literal42', 'literal43', 'literal44', 'literal45', 'literal46', 'literal47', 'literal48', 'literal49', 'literal50', 'literal51', 'literal52', 'literal53', 'literal54', 'literal55', 'literal56', 'literal57', 'literal58', 'literal59', 'literal60', 'literal61', 'literal62', 'literal63', 'literal64', 'literal65', 'literal66', 'literal67', 'literal68', 'literal69']

V_SOURCE_MODULES = (('src/bandido_alcatraz/__init__.py', 'bandido_alcatraz'), ('src/bandido_alcatraz/board.py', 'bandido_alcatraz.board'), ('src/bandido_alcatraz/deck_data.py', 'bandido_alcatraz.deck_data'), ('src/bandido_alcatraz/game.py', 'bandido_alcatraz.game'), ('src/bandido_alcatraz/model.py', 'bandido_alcatraz.model'), ('src/bandido_alcatraz/moves.py', 'bandido_alcatraz.moves'), ('src/bandido_alcatraz/photo_geometry.py', 'bandido_alcatraz.photo_geometry'), ('src/bandido_alcatraz/physical_deck.py', 'bandido_alcatraz.physical_deck'), ('src/bandido_alcatraz/policies.py', 'bandido_alcatraz.policies'), ('src/bandido_alcatraz/quota_reserve_closure.py', 'bandido_alcatraz.quota_reserve_closure'), ('src/bandido_alcatraz/quota_reserve_closure_reference.py', 'bandido_alcatraz.quota_reserve_closure_reference'), ('src/bandido_alcatraz/rules.py', 'bandido_alcatraz.rules'), ('src/bandido_alcatraz/setup.py', 'bandido_alcatraz.setup'), ('src/bandido_alcatraz/simulate.py', 'bandido_alcatraz.simulate'), ('src/bandido_alcatraz/strategy.py', 'bandido_alcatraz.strategy'), ('src/bandido_alcatraz/worker32/__init__.py', 'bandido_alcatraz.worker32'), ('src/bandido_alcatraz/worker32/evidence.py', 'bandido_alcatraz.worker32.evidence'), ('scripts/benchmark_worker35_synthetic.py', 'benchmark_worker35_synthetic'), ('scripts/run_quota_reserve_closure_development.py', 'run_quota_reserve_closure_development'), ('scripts/worker31_geometry.py', 'worker31_geometry'), ('scripts/worker35_resources.py', 'worker35_resources'))

V_INITIAL_MODULES = ('bandido_alcatraz', 'bandido_alcatraz.board', 'bandido_alcatraz.game', 'bandido_alcatraz.model', 'bandido_alcatraz.moves', 'bandido_alcatraz.policies', 'bandido_alcatraz.quota_reserve_closure', 'bandido_alcatraz.quota_reserve_closure_reference', 'bandido_alcatraz.rules', 'bandido_alcatraz.setup', 'bandido_alcatraz.strategy', 'bandido_alcatraz.worker32', 'bandido_alcatraz.worker32.evidence', 'benchmark_worker35_synthetic', 'run_quota_reserve_closure_development', 'worker35_resources')

V_CUSTODY_VERSION_LABELS = {'test_V14_external_custody_gate': ('V14-custody-before-02', 'V14-custody-before-03', 'V14-custody-before-04', 'V14-custody-before-05', 'V14-custody-before-06', 'V14-custody-before-07', 'V14-custody-before-08'), 'test_V15_exact_readback_provenance_and_files': ('V15-custody-before-02', 'V15-custody-before-03', 'V15-custody-before-04', 'V15-custody-before-05', 'V15-custody-before-06', 'V15-custody-before-07', 'V15-custody-before-08', 'V15-custody-before-09', 'V15-custody-before-10', 'V15-custody-before-11'), 'test_PW02_wrapper_coverage_is_mandatory': ('PW02-custody-before-02', 'PW02-custody-before-03', 'PW02-custody-before-04'), 'test_PW14_exact_and_semantic_wrapper_binding': ('PW14-custody-before-02',), 'test_PW15_legacy_custody_is_not_accepted': ('PW15-custody-before-02',)}

V_CUSTODY_INPUT_CASES = frozenset(('test_V11_joint_threshold_inclusive', 'test_V12_each_joint_threshold_failure', 'test_V13_revalidate_complete_evidence_binding', 'test_V14_external_custody_gate', 'test_V15_exact_readback_provenance_and_files', 'test_MR08_method_rows_and_unmeasured_flags_unchanged', 'test_PW01_complete_wrapper_final_classification', 'test_PW02_wrapper_coverage_is_mandatory', 'test_PW13_outer_wrapper_is_not_canonical_part', 'test_PW14_exact_and_semantic_wrapper_binding', 'test_PW15_legacy_custody_is_not_accepted'))

V_CANONICAL_FOLDER='1sQhQY3aKuHvQfyOTUIQjJGANCKOwKgEd'

def request_map(go):
    return tuple(zip(A_INPUT_NAMES, ('/pulls/' + str(go['pr_number']), '/actions/runs/' + str(A_CI_RUN), '/actions/runs/' + str(go['current_source_ci']['run_id']), '/issues/comments/' + str(go['reviews'][0]['comment_id']), '/issues/comments/' + str(go['reviews'][1]['comment_id']), '/issues/comments/' + str(go['preregistration']['comment_id']), '/git/commits/' + go['head'])))

def independent_review_body(review, number):
    value = {'schema': 'worker38-owner-attested-native-review-v1', 'repository': A_REPOSITORY, 'pr_number': number, 'role': review['role'], 'native_reviewer_id': review['native_reviewer_id'], 'head': review['head'], 'tree': review['tree'], 'verdict': 'clean', 'complete_review': True, 'independent_review_attested': True, 'actionable_findings': {'P0': 0, 'P1': 0, 'P2': 0, 'P3': 0}, 'handoff_sha256': review['handoff_sha256'], 'report_sha256': review['report_sha256']}
    return A_REVIEW_START + '\n' + canonical(value).decode() + A_REVIEW_END + '\n'

def independent_auth_bundle(go=None, *, pr_number=101, owner_id=456, cache='/invented-cache', focused_source_receipt=None, checked_file_sha256=None, workflow_run='501'):
    """Defaults fill only absent fields; supplied invalid values remain invalid."""
    value = copy.deepcopy(go) if go is not None else {}
    number = value.get('pr_number', pr_number)
    owner = {**F_OWNER, 'id': owner_id}
    repo = {'full_name': A_REPOSITORY, 'html_url': A_WEB, 'url': A_API, 'owner': owner}
    source_map = {path: sha(F_SOURCE_BYTES) for path in A_REQUIRED_PRODUCTION_PATHS + A_METADATA_PATHS}
    source_map.update({A_EXPERIMENT + 'PROTOCOL.md': C_PROTOCOL_SHA256, A_EXPERIMENT + 'INTEGRATION-CONTRACT.json': C_CONTRACT_SHA256, A_EXPERIMENT + 'FINITE-PREPARATION-PLAN.json': C_FINITE_PLAN_SHA256, A_EXPERIMENT + 'comparator-source-manifest.json': C_SOURCE_MANIFEST_SHA256})
    source_map.update(A_UPLOAD_RECORD_PINS)
    if checked_file_sha256 is None:
        checked_file_sha256 = value.get('checked_file_sha256', value.get('diagnostic_files_sha256', source_map))
    checked_file_sha256 = dict(checked_file_sha256)
    checked_file_sha256.pop(A_FOCUSED_SOURCE_RECEIPT, None)
    receipt = {'success': True, 'failures': 0, 'errors': 0, 'checked_file_sha256': checked_file_sha256, 'candidate_evaluator_calls': 0, 'reference_evaluator_calls': 0, 'games': 0, 'measurement_fixture_constructions': 0, 'historical_source_imports': 0}
    receipt_raw = canonical(receipt)
    receipt_pin = focused_source_receipt or {'path': A_FOCUSED_SOURCE_RECEIPT, 'size_bytes': len(receipt_raw), 'sha256': sha(receipt_raw)}
    defaults = {'schema': 'worker38-one-shot-admission-v1', 'admitted': True, 'repository': A_REPOSITORY, 'owner': A_OWNER, 'branch': A_BRANCH, 'base_head': A_BASE_HEAD, 'base_tree': A_BASE_TREE, 'allocation_id': A_ALLOCATION, 'pr_number': number, 'protocol_sha256': C_PROTOCOL_SHA256, 'contract_sha256': C_CONTRACT_SHA256, 'finite_plan_sha256': C_FINITE_PLAN_SHA256, 'upload_amendment_sha256': C_UPLOAD_AMENDMENT_SHA256, 'upload_contract_sha256': C_UPLOAD_CONTRACT_SHA256, 'upload_finite_plan_sha256': C_UPLOAD_FINITE_PLAN_SHA256, 'upload_adoption_comment_id': C_UPLOAD_ADOPTION, 'preregistration_url': A_WEB + '/issues/2#issuecomment-603', 'admission_url': A_WEB + '/pull/' + str(number), 'head': F_HEAD, 'tree': F_TREE, 'runner': A_RUNNER, 'runtime': C_RUNTIME, 'loader_pin': F_LIBRARY_PIN, 'resources': C_RESOURCES, 'startup_resources': C_STARTUP_RESOURCES, 'schedule': list(C_SCHEDULE), 'maximum_evaluator_calls': 40, 'games': 0, 'source_manifest_sha256': C_SOURCE_MANIFEST_SHA256, 'diagnostic_files_sha256': source_map, 'checked_file_sha256': checked_file_sha256, 'cell_preflight_modules': F_INITIAL_MODULES, 'inherited_limits': F_INHERITED_LIMITS, 'stub_test_receipt_sha256': receipt_pin['sha256'], 'focused_source_receipt': receipt_pin, 'postmerge_ci': {'run_id': A_CI_RUN, 'head': A_BASE_HEAD, 'status': 'completed', 'conclusion': 'success'}, 'current_source_ci': {'run_id': 401, 'head': value.get('head', F_HEAD), 'status': 'completed', 'conclusion': 'success', 'completed_at': '2026-10-05T00:00:00Z'}}
    for key, default in defaults.items():
        value.setdefault(key, copy.deepcopy(default))
    existing_reviews = value.get('reviews')
    if existing_reviews is None or not all((type(review) is dict and 'comment_id' in review for review in existing_reviews)):
        value['reviews'] = []
        for role, reviewer, comment_id, report_hash in (('exhaustive', 'literal-reviewer-one', 601, 'a' * 64), ('adversarial', 'literal-reviewer-two', 602, 'b' * 64)):
            review = {'role': role, 'native_reviewer_id': reviewer, 'head': value['head'], 'tree': value['tree'], 'verdict': 'clean', 'url': value['admission_url'] + '#issuecomment-' + str(comment_id), 'comment_id': comment_id, 'handoff_sha256': 'c' * 64, 'report_sha256': report_hash}
            review['body_sha256'] = sha(independent_review_body(review, number).encode())
            value['reviews'].append(review)
    prereg_body = 'Invented preregistration of ' + value['protocol_sha256'] + '\nContract ' + value['contract_sha256'] + '\nFinite plan ' + value['finite_plan_sha256'] + '\n'
    if 'preregistration' not in value:
        match = value['preregistration_url'].rsplit('-', 1)[-1]
        prereg_id = int(match)
        value['preregistration'] = {'comment_id': prereg_id, 'url': value['preregistration_url'], 'body_sha256': sha(prereg_body.encode()), 'protocol_sha256': value['protocol_sha256'], 'contract_sha256': value['contract_sha256'], 'finite_plan_sha256': value['finite_plan_sha256']}
    raw = canonical(value)
    body = A_START + '\n' + raw.decode() + A_END + '\n' + A_DIGEST + ': ' + sha(raw) + '\n'
    pr = {'number': number, 'html_url': value['admission_url'], 'url': A_API + '/pulls/' + str(number), 'issue_url': A_API + '/issues/' + str(number), 'state': 'open', 'merged': False, 'merged_at': None, 'user': owner, 'head': {'ref': A_BRANCH, 'sha': value['head'], 'repo': repo}, 'base': {'ref': 'main', 'sha': A_BASE_HEAD, 'repo': repo}, 'body': body, 'updated_at': '2026-10-05T00:01:00Z'}
    event = {'action': 'edited', 'repository': repo, 'sender': owner, 'number': number, 'pull_request': copy.deepcopy(pr), 'changes': {'body': {'from': 'Invented previous body\n'}}}
    context = {'schema': 'worker38-github-request-context-v1', 'repository': A_REPOSITORY, 'actor': A_OWNER, 'triggering_actor': A_OWNER, 'event_name': 'pull_request', 'workflow_run': workflow_run, 'workflow_attempt': '1', 'runner_name': A_RUNNER, 'runner_tool_cache': cache, 'checkout_path': '/invented-checkout', 'runner_temp': '/invented-temp', 'durable_root': cache + '/worker38-synthetic-profile', 'attempt_path': cache + '/worker38-synthetic-profile/allocations/' + A_ALLOCATION + '/run-' + str(workflow_run) + '-attempt-1', 'attempt_id': 'worker38-' + str(workflow_run) + '-1', 'authentication': 'github-repository-read-token', 'requests': [{'name': name, 'method': 'GET', 'path': path} for name, path in request_map(value)]}
    responses = [pr]
    for base in (True, False):
        binding = value['postmerge_ci' if base else 'current_source_ci']
        run = binding['run_id']
        responses.append({'repository': repo, 'id': run, 'url': A_API + '/actions/runs/' + str(run), 'html_url': A_WEB + '/actions/runs/' + str(run), 'head_sha': binding['head'], 'head_branch': 'main' if base else A_BRANCH, 'event': 'push' if base else 'pull_request', 'path': '.github/workflows/test.yml', 'name': 'tests', 'status': 'completed', 'conclusion': 'success', 'updated_at': '2026-10-04T23:00:00Z' if base else binding['completed_at']})
    for review in value['reviews']:
        responses.append({'id': review['comment_id'], 'url': A_API + '/issues/comments/' + str(review['comment_id']), 'html_url': review['url'], 'issue_url': A_API + '/issues/' + str(number), 'user': owner, 'body': independent_review_body(review, number)})
    prereg = value['preregistration']
    responses.append({'id': prereg['comment_id'], 'url': A_API + '/issues/comments/' + str(prereg['comment_id']), 'html_url': prereg['url'], 'issue_url': A_API + '/issues/2', 'user': owner, 'body': prereg_body})
    responses.append({'sha': value['head'], 'tree': {'sha': value['tree']}})
    inputs = dict(zip(F_FIXED_INPUTS, (canonical(response) for response in responses)))
    event_raw, context_raw = (canonical(event), canonical(context))
    return {'go': value, 'event': event, 'context': context, 'inputs': inputs, 'admission_raw': raw, 'event_raw': event_raw, 'context_raw': context_raw, 'stub_receipt_raw': receipt_raw}


def independent_auth_proof(bundle):
    """P03: admission.py434-454 output dictionary, no reconcile or validator."""
    go, event, context = bundle['go'], bundle['event'], bundle['context']
    event_raw, context_raw = canonical(event), canonical(context)
    body = event['pull_request']['body']
    owner = event['repository']['owner']
    return {'schema':'worker38-authenticated-pr-admission-v1','repository':A_REPOSITORY,
        'event_name':'pull_request','action':'edited','first_admission':True,
        'pull_request_number':go['pr_number'],'admission_url':go['admission_url'],
        'admission_sha256':sha(bundle['admission_raw']),'body_sha256':sha(body.encode()),
        'previous_body_sha256':sha(event['changes']['body']['from'].encode()),
        'head':go['head'],'tree':go['tree'],'branch':A_BRANCH,'base_head':A_BASE_HEAD,
        'sender':owner,'author':owner,'postmerge_ci':go['postmerge_ci'],
        'current_source_ci':go['current_source_ci'],'reviews':go['reviews'],
        'preregistration':go['preregistration'],'workflow_run':context['workflow_run'],
        'workflow_attempt':'1','attempt_path':context['attempt_path'],
        'attempt_id':context['attempt_id'],'durable_root':context['durable_root'],
        'event_sha256':sha(event_raw),'request_context_sha256':sha(context_raw),
        'admission_input_hashes':{name:sha(bundle['inputs'][name]) for name in A_INPUT_NAMES}}


def fixed_stored_zip(entries, *, negative=False, mode=0o100600):
    """P11/P13 explicit ZIP_STORED grammar,1980 DOS date,Unix regular0600.

    No archive library or filesystem is involved. The closed inputs are ASCII
    member names and independently derived bytes, in the supplied fixed order.
    ZIP64, encryption, descriptors, extra/comment data and dynamic clocks fail.
    """
    local, central, offset = [], [], 0
    if len(entries)>65535: raise ClosurePrerequisite('ZIP64 not admitted')
    names=set()
    for name,raw in entries:
        encoded=name.encode('ascii')
        if len(encoded)>65535 or (not negative and (name in names or name.startswith('/') or '..' in PurePosixPath(name).parts)):
            raise ClosurePrerequisite('fixed ZIP member domain drift')
        names.add(name)
        if not isinstance(raw,bytes) or len(raw)>=2**32: raise ClosurePrerequisite('ZIP raw bound')
        crc=zlib.crc32(raw)&0xffffffff
        head=struct.pack('<4s5H3I2H',b'PK\x03\x04',20,0,0,0,33,crc,len(raw),len(raw),len(encoded),0)
        local.append(head+encoded+raw)
        center=struct.pack('<4s6H3I5H2I',b'PK\x01\x02',788,20,0,0,0,33,crc,len(raw),len(raw),len(encoded),0,0,0,0,(mode<<16),offset)
        central.append(center+encoded);offset+=len(head)+len(encoded)+len(raw)
    directory=b''.join(central)
    trailer=struct.pack('<4s4H2IH',b'PK\x05\x06',0,0,len(entries),len(entries),len(directory),offset,0)
    return b''.join(local)+directory+trailer


class VerifierRecipe:
    """P08-12 closed in-memory planned byte DAG, never a filesystem adapter.

    PurePosixPath is lexical only. Every raw read addresses this recipe's own
    previously constructed dictionary. No observed file can populate this DAG.
    """
    def asset_state(self,path,raw,operation):
        """One complete independently planned state, with a closed ownership role."""
        path=PurePosixPath(path)
        if not path.is_relative_to(self.case):raise ClosurePrerequisite('asset outside fixed case')
        if path.is_relative_to(self.root):
            role='raw_attempt_literal';lineage='independent_input'
        elif path.parent==self.auth and path.name in ('event.json','request-context.json',*A_INPUT_NAMES,'admission.json','provenance.json'):
            role='external_auth_literal';lineage='independent_input'
        elif path.parent in (self.base/'custody-inputs-1',self.base/'custody-inputs-2'):
            if path.name=='externally-authenticated-custody.json':
                role='produced_custody_receipt';lineage='produced_output'
            elif path.name in ('upload-part.bin','fresh-download-part.bin','github-provider-wrapper-001.zip',
                    'upload-transport-manifest.json','fresh-transport-manifest.json'):
                role='fixed_custody_input_asset';lineage='independent_input'
            else:raise ClosurePrerequisite('unknown custody asset role')
        elif self.driver_target and path==self.root.parent/'reservation.txt':
            role='F07_parent_reservation_literal';lineage='independent_input'
        else:raise ClosurePrerequisite('unlisted verifier asset ownership role '+str(path))
        if operation not in ('write','remove') or (operation=='write')!=(type(raw) is bytes):
            raise ClosurePrerequisite('asset operation/raw type mismatch')
        value={'relative_path':str(path.relative_to(self.case)),
            'type':'file' if raw is not None else 'missing','size_bytes':len(raw) if raw is not None else 0,
            'sha256':sha(raw) if raw is not None else None,'lineage':lineage,'asset_role':role}
        binding={'recipe_source_sha256':self.ctx['recipe_sha256'],'selector':self.selector,
            'source_path':'tests/test_worker38_verify_integration.py',
            'source_sha256':sha(self.ctx['source_bytes']['tests/test_worker38_verify_integration.py']),
            'operation':operation,'operation_ordinal':len(self.operations)+1}
        if self.driver_target:
            # LiteralBundle.write_startup constructs the parent reservation;
            # F07 complete_orchestration supplies its distinct roots/loader.
            binding.update(caller_source_path='tests/test_worker38_bootstrap_integration.py',
                caller_source_sha256=sha(self.ctx['source_bytes']['tests/test_worker38_bootstrap_integration.py']),
                caller='Worker38BootstrapIntegration.complete_orchestration',
                constructor_variant='F07_explicit_driver_target_and_external_auth')
        return {**value,'source_recipe_binding':binding,
            'independent_recipe_sha256':digest({'state':value,'source_recipe_binding':binding})}

    def export_asset_states(self):
        # Final missing states are retained alongside present files. This reads
        # only this independent recipe's owned maps, never a candidate inventory.
        if {path for path,state in self.asset_states.items() if state['type']=='file'}!=set(self.files):
            raise ClosurePrerequisite('complete planned file/state roster disagreement')
        result=[]
        for path,state in sorted(self.asset_states.items()):
            raw=self.files.get(path)
            if state['type']=='file':
                if type(raw) is not bytes or state['size_bytes']!=len(raw) or state['sha256']!=sha(raw):
                    raise ClosurePrerequisite('planned asset identity changed without an ordered write')
            elif state['type']!='missing' or raw is not None or state['size_bytes']!=0 or state['sha256'] is not None:
                raise ClosurePrerequisite('planned missing asset identity mismatch')
            result.append(copy.deepcopy(state))
        return result

    def put_raw(self,path,raw):
        if type(raw) is not bytes: raise ClosurePrerequisite('raw byte type')
        key=str(path)
        if not PurePosixPath(key).is_relative_to(self.case):
            raise ClosurePrerequisite('planned write outside case base')
        if PurePosixPath(key).name=='externally-authenticated-custody.json' and key in self.files:
            labels=V_CUSTODY_VERSION_LABELS.get(self.method,())
            index=len(self.versions)
            if index>=len(labels): raise ClosurePrerequisite('extra custody version')
            previous=copy.deepcopy(self.asset_states[key])
            if previous['lineage']!='produced_output':raise ClosurePrerequisite('custody version lost produced lineage')
            self.versions.append({'label':labels[index],**previous,
                'preserved_before_operation_ordinal':len(self.operations)+1})
        self.files[key]=raw
        state=self.asset_state(path,raw,'write')
        self.asset_states[key]=state
        self.operations.append({'operation':'write','path':str(PurePosixPath(key).relative_to(self.case)),
            **state})

    def write(self,path,value,raw=False):
        self.put_raw(path,value if raw else canonical(value))

    def raw(self,path):
        return self.files[str(path)]

    def read(self,path):
        return json.loads(self.raw(path))

    def info(self,path):
        raw=self.raw(path)
        return {'size_bytes':len(raw),'sha256':sha(raw)}

    def exists(self,path):
        return str(path) in self.files

    def remove(self,path):
        del self.files[str(path)]
        state=self.asset_state(path,None,'remove')
        self.asset_states[str(path)]=state
        self.operations.append({'operation':'remove','path':str(PurePosixPath(path).relative_to(self.case)),**state})

    def rows(self,path):
        return [json.loads(line) for line in self.raw(path).splitlines()]

    def literal_inventory(self):
        records=[{'path':str(PurePosixPath(path).relative_to(self.root)),
                  'size_bytes':len(raw),'sha256':sha(raw)}
            for path,raw in sorted(self.files.items()) if PurePosixPath(path).is_relative_to(self.root)]
        if sum(x['size_bytes'] for x in records)>2097152:
            raise ClosurePrerequisite('fixed literal tree exceeds 2MiB')
        return records

    def write_auth(self):
        # Only enumerated successful write_auth branches call this constructor.
        # Rejected admission branches are selected explicitly by recipe_V03/V22.
        stub=self.root/'stub-test-receipt.json'
        source={'path':A_FOCUSED_SOURCE_RECEIPT,**self.info(stub)}
        bundle=independent_auth_bundle(self.go,pr_number=40,owner_id=456,cache=self.cache,
            focused_source_receipt=source,checked_file_sha256=self.read(stub)['checked_file_sha256'],workflow_run='123')
        bundle['context']['checkout_path']=self.source_path
        self.go=bundle['go']
        proof=independent_auth_proof(bundle)
        payloads={'event.json':canonical(bundle['event']),'request-context.json':canonical(bundle['context']),
            **bundle['inputs'],'admission.json':bundle['admission_raw'],'provenance.json':canonical(proof)}
        for name,raw in payloads.items():
            self.put_raw(self.auth/name,raw)
            self.put_raw(self.root/'admission-inputs'/name,raw)
        self.put_raw(self.root/'external-admission.json',bundle['admission_raw'])
        self.write_startup()


    def __init__(self, ctx, row, *, f07=False):
        self.ctx = ctx
        self.row = row
        self.selector = row['selector']
        self.method = self.selector.rsplit('.', 1)[-1]
        self.case = case_root(ctx, row['ordinal'])
        self.base = self.case / 't01'
        if not f07 and (len(str(self.base)) > 60 or re.fullmatch('[/._A-Za-z0-9-]+', str(self.base)) is None):
            raise ClosurePrerequisite('custody base domain: <=60 ASCII path bytes')
        self.root = self.base / 'raw-attempt'
        self.auth = self.base / 'external-auth'
        self.admission = self.auth / 'admission.json'
        self.provenance = self.auth / 'provenance.json'
        self.cache = '/invented-cache'
        self.source_path = '/invented-checkout'
        self.original = V_ORIGINAL
        self.script = V_SCRIPT
        self.loader_identity = copy.deepcopy(V_LOADER_IDENTITY)
        self.driver_target = f07
        if f07:
            if self.method != 'test_F07_complete_literal_20_cell_orchestration':
                raise ClosurePrerequisite('only named F07 may bind moved literal cohort')
            cache = self.case/'t01'/'complete-cache'
            self.root = cache/'worker38-synthetic-profile/allocations/worker38-synthetic-profile-01/run-123-attempt-1'
            self.base = self.case/'t01'/'complete-external'
            self.auth = self.base/'external-auth'
            self.admission = self.auth/'admission.json'
            self.provenance = self.auth/'provenance.json'
            self.cache = str(cache)
            self.source_path = str(self.case/'t01'/'complete-checkout')
            self.original = str(self.root)
            self.script = self.source_path+'/scripts/run_worker38_synthetic.py'
            self.loader_identity.update(tool_cache=self.cache,
                executable_path=self.cache+'/Python/3.11.16/x64/bin/python3.11',
                library_path=self.cache+'/Python/3.11.16/x64/lib/libpython3.11.so.1.0',
                library_directory=self.cache+'/Python/3.11.16/x64/lib')
            self.loader_identity['mapped_library']['path']=self.loader_identity['library_path']
            self.loader_identity['loader_environment']={'LD_LIBRARY_PATH':self.loader_identity['library_directory']}
        self.custody_case = self.method if self.method in V_CUSTODY_INPUT_CASES else None
        self._frozen_custody = None
        self.custody_input_versions = []
        self.files = {}
        self.asset_states = {}
        self.operations = []
        self.versions = []
        self.events = []
        self.expected = [copy.deepcopy(e) for e in ctx['events'] if e['selector'] == self.selector]
        files = []
        for path, module in V_SOURCE_MODULES:
            self.write(self.root / 'restored' / path, V_SOURCE_BYTES, raw=True)
            files.append({'path': path, 'module': module, 'size_bytes': len(V_SOURCE_BYTES), 'sha256': sha(V_SOURCE_BYTES), 'git_blob': hashlib.sha1(b'blob ' + str(len(V_SOURCE_BYTES)).encode() + b'\x00' + V_SOURCE_BYTES).hexdigest()})
        self.manifest = {'schema': 'worker38-comparator-closure-v1', 'repository': C_REPOSITORY, 'historical_commit': C_HISTORICAL, 'files': files}
        self.write(self.root / 'source-manifest.json', self.manifest)
        diagnostic = {name: 'a' * 64 for name in A_REQUIRED_PRODUCTION_PATHS + A_METADATA_PATHS}
        diagnostic['experiments/worker38-synthetic-profile/PROTOCOL.md'] = C_PROTOCOL_SHA256
        diagnostic['experiments/worker38-synthetic-profile/INTEGRATION-CONTRACT.json'] = C_CONTRACT_SHA256
        diagnostic['experiments/worker38-synthetic-profile/FINITE-PREPARATION-PLAN.json'] = C_FINITE_PLAN_SHA256
        diagnostic['experiments/worker38-synthetic-profile/comparator-source-manifest.json'] = self.info(self.root / 'source-manifest.json')['sha256']
        diagnostic.update({'experiments/worker38-synthetic-profile/inputs/comparator-7ac2f62c/' + entry['path'] + '.blob': entry['sha256'] for entry in files})
        diagnostic['experiments/worker38-synthetic-profile/upload-amendment/AMENDMENT.md'] = C_UPLOAD_AMENDMENT_SHA256
        diagnostic['experiments/worker38-synthetic-profile/upload-amendment/AMENDMENT-CONTRACT.json'] = C_UPLOAD_CONTRACT_SHA256
        diagnostic['experiments/worker38-synthetic-profile/upload-amendment/FINITE-COVERAGE-AMENDMENT.json'] = C_UPLOAD_FINITE_PLAN_SHA256
        diagnostic.update(A_UPLOAD_RECORD_PINS)
        tested_sources = {**diagnostic, **{path: 'c' * 64 for path in V_TESTED_EXTRA_PATHS}}
        stub = {'success': True, 'checked_file_sha256': tested_sources, 'candidate_evaluator_calls': 0, 'reference_evaluator_calls': 0, 'measurement_fixture_constructions': 0, 'historical_source_imports': 0, 'games': 0, 'failures': 0, 'errors': 0}
        self.write(self.root / 'stub-test-receipt.json', stub)
        self.go = {'schema': 'worker38-one-shot-admission-v1', 'admitted': True, 'repository': C_REPOSITORY, 'branch': A_BRANCH, 'preregistration_url': C_PREREGISTRATION, 'protocol_sha256': C_PROTOCOL_SHA256, 'admission_url': A_WEB + '/pull/40', 'head': V_HEAD, 'tree': V_TREE, 'runner': 'bandido-alcatraz-ci', 'runtime': C_RUNTIME, 'loader_pin': copy.deepcopy(V_LOADER_PIN), 'resources': C_RESOURCES, 'schedule': list(C_SCHEDULE), 'maximum_evaluator_calls': 40, 'games': 0, 'source_manifest_sha256': diagnostic['experiments/worker38-synthetic-profile/comparator-source-manifest.json'], 'diagnostic_files_sha256': diagnostic, 'cell_preflight_modules': sorted(V_INITIAL_MODULES), 'inherited_limits': V_INHERITED, 'stub_test_receipt_sha256': self.info(self.root / 'stub-test-receipt.json')['sha256'], 'postmerge_ci': {'run_id': A_CI_RUN, 'head': A_BASE_HEAD, 'status': 'completed', 'conclusion': 'success'}, 'reviews': [{'head': V_HEAD, 'tree': V_TREE, 'verdict': 'clean', 'reviewer': 'literal-reviewer-one', 'url': A_WEB + '/pull/40#issuecomment-100'}, {'head': V_HEAD, 'tree': V_TREE, 'verdict': 'clean', 'reviewer': 'literal-reviewer-two', 'url': A_WEB + '/pull/40#issuecomment-200'}]}
        self.write_auth()
        parent_runtime = self.runtime()
        parent_runtime['flags'] = [self.loader_identity['executable_path'], '-B', '-s', self.script, 'measure']
        parent_runtime['address_space'] = [512 * 1024 ** 2] * 2
        parent_runtime['inherited_limits'] = V_INHERITED
        self.write(self.root / 'source-runtime-preflight.json', {'phase': 'source_runtime_preflight', 'evaluator_starts': 0, 'runtime': parent_runtime, 'coordinator_address_space': [512 * 1024 ** 2] * 2, 'restored_source_inventory': files, 'diagnostic_files_sha256': diagnostic, 'measurement_anchor': self.measurement_anchor, 'timer_control': [{'deadline': 11140, 'before': 9340, 'after': 9340.001, 'requested': 1799.999, 'observed_before': 9340, 'observed_after': 9340.001, 'observed_countdown': 1799.998, 'observed_interval': 0.0, 'alarm_handler_confirmed': True, 'usr1_handler_confirmed': True, 'other_timers_idle': True, 'owner_pid': 1000}]})
        for identity in C_SCHEDULE:
            self.cell(identity)
        self.receipt = {'schema': 'worker38-attempt-v1', 'status': 'execution_complete', 'phase': 'verification_pending', 'admission_verified': True, 'admission_sha256': sha(self.raw(self.admission)), 'diagnostic_head': V_HEAD, 'diagnostic_tree': V_TREE, 'attempt_id': 'worker38-123-1', 'attempt_path': self.original, 'runner': 'bandido-alcatraz-ci', 'workflow_run': '123', 'workflow_attempt': '1', 'preregistration_url': C_PREREGISTRATION, 'source_manifest_sha256': self.go['source_manifest_sha256'], 'resources': C_RESOURCES, 'games': 0, 'schedule': list(C_SCHEDULE), 'maximum_evaluator_calls': 40, 'actual_starts': 40, 'actual_starts_upper_bound': 40, 'pre_call_markers': 40, 'actual_returns': 40, 'confirmed_captures': 40, 'current_cell': None, 'completed_prefix': list(range(1, 21)), 'capture_gaps': [], 'corrupt_evidence': [], 'unavailable_evidence': [], 'retained_failures': [], 'custody': 'pending', 'classification': None, 'supervisor_pid': 1000, 'supervisor_start_ticks': 934000, 'measurement_anchor': self.measurement_anchor, 'runtime_scope': {'idle_gate_passed': True, 'timer_owned': True, 'original_deadline': 11140.0}, 'resource_totals': {'supervision': self.read(self.root / 'supervisor-cell-20.json'), 'P_operations': {'legal_enumerations': 20, 'previews': 0, 'exit_geometry_checks': 0}, 'phase': self.phase(21)}}
        self.write(self.root / 'receipt.json', self.receipt)
        self.refresh()

    def write_startup(self):
        runtime = {'implementation': 'cpython', 'version': '3.11.16', 'inherited_limits': copy.deepcopy(V_INHERITED), 'memory_cap': {'attempted': True, 'confirmed': True, 'readback': [536870912, 536870912]}, 'flags': {'optimize': 0, 'ignore_environment': 0, 'isolated': 0, 'no_site': 0, 'no_user_site': 1, 'dont_write_bytecode': 1}, 'state': {'limits': {**V_INHERITED, 'RLIMIT_AS': [536870912, 536870912]}, 'gc_enabled': True, 'gc_threshold': [700, 10, 10], 'profile_idle': True, 'trace_idle': True, 'threads': 1, 'timers': [[0.0, 0.0]] * 3}, 'memory_cap_restoration': 'retained_until_leaf_process_exit', 'files': {name: {'sha256': pin, 'size_bytes': size, 'device': 2049, 'inode': inode, 'mtime_ns': 1, 'mapped_identity_confirmed': True, 'observed_mapping': {'major': 8, 'minor': 1, 'inode': inode}} for name, pin, size, inode in (('executable', C_RUNTIME['executable_sha256'], 1234, 1233), ('library', V_LOADER_PIN['library_sha256'], V_LOADER_PIN['library_size_bytes'], 1234))}}
        startup = {'schema': 'worker38-startup-receipt-v1', 'allocation_id': 'worker38-synthetic-profile-01', 'admission_verified': True, 'classification': None, 'scientific_classification': None, 'evaluator_starts': 0, 'actual_starts_upper_bound': 0, 'historical_source_imports': 0, 'measurement_fixture_constructions': 0, 'games': 0, 'phase': 'admission_complete', 'primary_failure': None, 'secondary_failures': [], 'transition_attempted': False, 'first_failure_monotonic': None, 'preservation_deadline_monotonic': None, 'requested_prefix': list(A_INPUT_NAMES), 'completed_prefix': list(A_INPUT_NAMES), 'requests': [], 'response_body_bytes': 0, 'runtime': runtime, 'input_persistence': {}, 'admission_CPU_seconds': 1, 'admission_CPU_limit': [90, 90], 'administrative_deadlines': {'startup_boottime_ns': 9300000000000, 'startup_deadline_boottime_ns': 9420000000000, 'admission_deadline_boottime_ns': 9400000000000, 'observed_leaf_entry_boottime_ns': 9310000000000}, 'free_bytes_before_source': 1073741824, 'restored_source_inventory': self.manifest['files']}
        for name in A_INPUT_NAMES:
            info = self.info(self.auth / name)
            size = info['size_bytes']
            startup['response_body_bytes'] += size
            startup['requests'].append({'name': name, 'status': 200, 'received_bytes': size, 'buffered_bytes': size, 'retained_bytes': size, 'fsync_confirmed_bytes': size, 'eof_confirmed': True, 'complete': True, 'close_confirmed': True, 'semantic_validated': True})
            startup['input_persistence'][name] = {**info, 'buffered_bytes': size, 'fsync_confirmed_bytes': size, 'write_complete': True, 'file_fsync_confirmed': True, 'directory_fsync_confirmed': True, 'readback_confirmed': True, 'close_confirmed': True}
        reservation = ('schema=worker38-observed-reservation-v1\nallocation_id=worker38-synthetic-profile-01\nrun_id=123\nrun_attempt=1\nobserved_head=' + V_HEAD + '\ndescriptor_binding=not_yet_validated\nevaluator_starts=0\nscientific_classification=null\n').encode()
        self.write(self.root / 'reservation.txt', reservation, raw=True)
        self.write(self.root / 'admission-process-exit.txt', b'schema=worker38-admission-process-exit-v1\nexit_status=0\nadmission_process_returned=true\n', raw=True)
        if self.driver_target:
            self.write(self.root.parent / 'reservation.txt', reservation, raw=True)
        self.write(self.root / 'runtime.json', runtime)
        self.write(self.root / 'startup-receipt.json', startup)
        self.write(self.root / 'restored-inventory.json', self.manifest['files'])
        go = self.read(self.admission)
        handoff = {'schema': 'worker38-startup-handoff-v1', 'consumer': 'worker38-synthetic-profile-v1', 'boot_id': '11111111-2222-3333-4444-555555555555', 'measurement_monotonic_ns': 9340000000000, 'measurement_boottime_ns': 9340000000000, 'measurement_deadline_monotonic_ns': 11140000000000, 'measurement_deadline_boottime_ns': 11140000000000, 'attempt_path': self.original, 'source_path': self.source_path, 'head': V_HEAD, 'tree': V_TREE, 'workflow_run': '123', 'workflow_attempt': '1', 'admission_sha256': sha(self.raw(self.admission)), 'provenance_sha256': sha(self.raw(self.provenance)), 'runtime_sha256': self.info(self.root / 'runtime.json')['sha256'], 'source_map_sha256': digest(go['checked_file_sha256']), 'restored_inventory_sha256': digest(self.manifest['files']), 'startup_receipt_sha256': self.info(self.root / 'startup-receipt.json')['sha256']}
        self.measurement_anchor = handoff
        self.write(self.root / 'startup-handoff.json', handoff)
        text = 'version=worker38-handoff-v1\nhandoff_sha256=' + digest(handoff) + '\n'
        text += ''.join((name + '=' + str(handoff[name]) + '\n' for name in A_HANDOFF_LINES))
        self.write(self.root / 'measurement-handoff.txt', text.encode('ascii'), raw=True)
        for name in ('receipt.json', 'source-runtime-preflight.json'):
            path = self.root / name
            if self.exists(path):
                record = self.read(path)
                record['measurement_anchor'] = handoff
                self.write(path, record)

    def runtime(self, index=None):
        inherited = {**V_INHERITED, 'RLIMIT_AS': [536870912, 536870912], 'RLIMIT_CPU': [720, 720]} if index is not None else V_INHERITED
        observed = self.read(self.root / 'runtime.json')
        observed['inherited_limits'] = copy.deepcopy(inherited)
        observed['state']['limits'] = {**copy.deepcopy(inherited), 'RLIMIT_AS': [536870912, 536870912]}
        return {**C_RUNTIME, 'inherited_limits': copy.deepcopy(inherited), 'shared_startup_observation': observed, 'executable': self.loader_identity['executable_path'], 'loader': copy.deepcopy(self.loader_identity), 'flags': [self.loader_identity['executable_path'], '-B', '-s', self.script, '_cell', '--attempt', self.original, '--cell', str(index)], 'python_environment': {'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1'}, 'gc_enabled': True, 'gc_threshold': [700, 10, 10], 'effective_flags': {'dont_write_bytecode': 1, 'no_user_site': 1, 'ignore_environment': 0, 'isolated': 0, 'optimize': 0, 'no_site': 0}, 'address_space': [512 * 1024 ** 2] * 2}

    def phase(self, index):
        return {'wall_seconds': 30 * index, 'parent_cpu_seconds': index, 'reaped_child_cpu_seconds': 30 * index, 'live_child_cpu_seconds': 0, 'cpu_seconds': 31 * index, 'wall_limit_seconds': 1800, 'cpu_limit_seconds': 1800}

    def cell(self, identity):
        index = identity['cell']
        folder = self.root / 'cells' / f'{index:02d}'
        modules = {entry['module']: {'path': self.original + '/restored/' + entry['path'], **{key: entry[key] for key in ('size_bytes', 'sha256', 'git_blob')}} for entry in self.manifest['files']}
        self.write(folder / 'source-runtime-preflight.json', {'phase': 'source_runtime_preflight', 'evaluator_starts': 0, 'runtime': self.runtime(index), 'modules': {key: value for key, value in modules.items() if key in V_INITIAL_MODULES}})
        begin = {**identity, 'observation_sha256': digest(V_PUBLIC), 'initial_rng_sha256': digest(V_RNG), 'rng_initial': V_RNG, 'public_before': V_PUBLIC, 'engine_before': 'literal invented witness', 'conservation_before': {'inventory_count': 69, 'inventory_sha256': digest(V_IDENTITIES), 'zones': {'placed': [], 'collected': [], 'hand': [], 'draw': V_IDENTITIES, 'set_aside': []}}}
        self.write(folder / 'cell-start.json', begin)
        self.write(folder / 'cell-boundaries.json', {'public_after': V_PUBLIC, 'engine_after': begin['engine_before'], 'conservation_after': begin['conservation_before'], 'equality': True})
        self.write(folder / 'active-call.json', {'active': False})
        science = copy.deepcopy(V_SCIENCE)
        science.update(input_before=digest(V_PUBLIC), input_after=digest(V_PUBLIC), rng_before=digest(V_RNG), rng_after=digest(V_RNG))
        cost = {'legal_enumerations': 1, 'previews': 0, 'exit_geometry_checks': 0, 'roots': 0}
        calls = {}
        payloads = []
        for scope in ('candidate', 'reference'):
            start = {**identity, 'scope': scope, 'observation_sha256': digest(V_PUBLIC), 'initial_rng_sha256': digest(V_RNG), 'source_modules': {key: value for key, value in modules.items() if key in V_INITIAL_MODULES or (identity['condition'] == 'P' and key == 'bandido_alcatraz.simulate')}}
            self.write(folder / (scope + '-start.json'), start)
            payload = {**start, 'chosen': None, 'scientific': science, 'scientific_sha256': digest(science), 'rng_initial': V_RNG, 'rng_final': V_RNG, 'final_rng_sha256': digest(V_RNG), 'timing': {'wall_seconds': 12, 'cpu_seconds': 10 if identity['condition'] == 'P' else 8}, 'physical_cost': cost if identity['condition'] == 'P' else None, 'physical_operation_caps_enforced': identity['condition'] == 'P', 'choice_events_observed': identity['condition'] == 'P', 'production_admissible': False}
            path = folder / (scope + '-return.json')
            self.write(path, payload)
            evidence = {'path': path.relative_to(self.root).as_posix(), **self.info(path)}
            self.write(folder / (scope + '-capture-confirmed.json'), evidence)
            calls[scope] = {'start_marker_durable': True, 'invocation_attempted': True, 'method_entered': True, 'returned': True, 'durable_capture_confirmed': True, 'evidence': evidence}
            payloads.append(payload)
        if identity['condition'] == 'P':
            metrics = [{'kind': 'decision', 'pass': 2, 'seed': 11, 'ordinal': 1, 'scope': scope, 'wall_seconds': 13, 'cpu_seconds': 11, 'peak_rss_kib': 1000, 'cost': cost, 'status': 'returned'} for scope in ('candidate', 'reference')]
            journals = [{'ordinal': 1, 'scope': 'candidate', 'result': {'chosen': None, 'scientific': science, 'cost': cost}}, {'ordinal': 1, 'scope': 'reference', 'result': {'chosen': None, 'scientific_sha256': digest(science), 'cost': cost}}]
            traces = [{'event': 'decision_started'}, {'event': 'decision_completed', 'audit': {'boundary': {'choice_calls': 0, 'reference_choice_calls': 0, 'choice_tier': [], 'reference_choice_tier': []}}}]
            for name, values in (('resource-metrics.jsonl', metrics), ('call-results/pass-2/11.jsonl', journals), ('decision-traces/pass-2/11.jsonl', traces)):
                self.write(folder / name, b''.join((canonical(row) for row in values)), raw=True)
            self.write(folder / 'whole-wrapper-resources.json', {'operations': {'legal_enumerations': 2, 'previews': 0, 'exit_geometry_checks': 0}, 'wall_seconds': 25, 'cpu_seconds': 21, 'peak_rss_kib': 1000})
        else:
            self.write(folder / 'unmeasured-accounting.json', C_U_FLAGS)
        self.write(folder / 'cell-receipt.json', {**identity, 'schema': 'worker38-cell-receipt-v1', 'status': 'complete', 'actual_starts': 2, 'actual_starts_upper_bound': 2, 'pre_call_markers': 2, 'invocation_attempts': 2, 'actual_returns': 2, 'confirmed_captures': 2, 'calls': calls, 'hook_restored': True, 'timer_restored': True, 'peak_rss_kib': 1000, 'classification': None, 'error_type': None, 'error': None, 'failure': None, 'secondary_errors': [], 'phase': 'cell_complete'})
        log_name = f'supervisor-cell-{index:02d}.log'
        self.write(self.root / log_name, b'', raw=True)
        supervisor = {'schema': 'worker38.supervision.v1', 'status': 'completed', 'reason': 'child_exit_zero', 'primary_outcome': {'status': 'completed', 'reason': 'child_exit_zero'}, 'secondary_failures': [], 'child_accounting_complete': True, 'phase_accounting_complete': True, 'spawn_attempted': True, 'spawn_initialization_complete': True, 'spawn_ownership_uncertain': False, 'spawn_discovery': 'not_required', 'spawn_recovered_pids': [], 'preservation_deadline_monotonic': None, 'preservation_transition_attempted': False, 'preservation_transition_complete': False, 'preservation_expired': False, 'preservation_blocked': False, 'spawned': True, 'pid': 2000 + index, 'parent_pid': 1000, 'parent_death_signal': 9, 'returncode': 0, 'exit_code': 0, 'signal': None, 'scientific_returns_inferred': False, 'active_call_at_stop': None, 'errors': [], 'cleanup': {'complete': True, 'sigkill_used': False, 'remaining_pids': [], 'errors': [], 'failure_details': []}, 'output_log': self.original + '/' + log_name, 'output_capture_mode': 'bounded_memory_then_post_cleanup_fsync', 'output_bytes_preserved': 0, 'output_bytes_observed': 0, 'output_durable': True, 'output_overflow': False, 'output_prefix_gap': False, 'output_pipe_tail': 'eof_observed', 'inherited_limits': {**V_INHERITED, 'RLIMIT_AS': [512 * 1024 ** 2] * 2}, 'limits': {'wall_seconds': 720, 'cpu_seconds': 720, 'address_space_bytes': 512 * 1024 ** 2, 'call_wall_seconds': 360, 'call_cpu_seconds': 360, 'output_log_limit_bytes': 63 * 1024 ** 2}, 'wall_seconds': 30, 'child_cpu_seconds': 30, 'child_high_water_rss_kib': 1000, 'cpu_tick_seconds': 0.01, 'poll_seconds': 0.02, 'phase': self.phase(index)}
        self.write(self.root / f'supervisor-cell-{index:02d}.json', supervisor)

    def refresh(self):
        receipt = self.read(self.root / 'receipt.json')
        receipt['file_inventory'] = [x for x in self.literal_inventory() if x['path'] not in ('receipt.json', 'measurement-phase-close.json', 'coordinator-restoration.json', 'writer-exit-observation.json')]
        self.write(self.root / 'receipt.json', receipt)
        self.write(self.root / 'measurement-phase-close.json', {'schema': 'worker38-measurement-phase-close-v1', 'phase': self.phase(22), 'computational_receipt': {'path': 'receipt.json', **self.info(self.root / 'receipt.json')}, 'includes_computational_receipt_publication': True, 'closing_proof_included_in_measurement': False, 'measurement_work_after_close': False, 'no_measurement_after_close': True, 'preservation_started_monotonic': 10000, 'preservation_deadline_monotonic': 10600})
        self.write(self.root / 'coordinator-restoration.json', {'schema': 'worker38-coordinator-restoration-v1', 'owner_pid': 1000, 'measurement_deadline_monotonic': 11140.0, 'preservation_deadline_monotonic': 10600, 'timer_disabled': True, 'alarm_handler_restored': True, 'alarm_restoration_confirmed': True, 'usr1_handler_restored': True, 'restoration_confirmed': True, 'measurement_work_after_close': False, 'no_measurement_after_close': True})
        self.write(self.root / 'writer-exit-observation.json', {'schema': 'worker38-writer-exit-observation-v1', 'workflow_run': '123', 'workflow_attempt': '1', 'admission_exit_receipt': {'path': 'admission-process-exit.txt', **self.info(self.root / 'admission-process-exit.txt')}, 'admission_exit_status': 0, 'coordinator_exit_status': 0, 'coordinator_state': 'exited', 'coordinator_pid': 1000, 'coordinator_start_ticks': 934000, 'parent_pid': 900, 'parent_start_ticks': 900000, 'no_measurement_after_close': True, 'preservation_deadline_monotonic': 10600})

    def mutate(self, name, keys, value, refresh=True):
        path = self.root / name
        data = self.read(path)
        set_nested(data, keys, value)
        self.write(path, data)
        if refresh:
            self.refresh()

    def expected_baseline_paths(self):
        expected={'source-manifest.json','stub-test-receipt.json','external-admission.json',
            'source-runtime-preflight.json','receipt.json','measurement-phase-close.json',
            'coordinator-restoration.json','writer-exit-observation.json','reservation.txt',
            'admission-process-exit.txt','runtime.json','startup-receipt.json','restored-inventory.json',
            'startup-handoff.json','measurement-handoff.txt'}
        expected.update('restored/'+path for path,_ in V_SOURCE_MODULES)
        expected.update('admission-inputs/'+name for name in ('event.json','request-context.json',*A_INPUT_NAMES,'admission.json','provenance.json'))
        for identity in C_SCHEDULE:
            prefix='cells/%02d/'%identity['cell']
            names=['source-runtime-preflight.json','cell-start.json','cell-boundaries.json','active-call.json','cell-receipt.json']
            names += [scope+suffix for scope in ('candidate','reference') for suffix in ('-start.json','-return.json','-capture-confirmed.json')]
            names += ['resource-metrics.jsonl','call-results/pass-2/11.jsonl','decision-traces/pass-2/11.jsonl','whole-wrapper-resources.json'] if identity['condition']=='P' else ['unmeasured-accounting.json']
            expected.update(prefix+name for name in names)
            expected.update('supervisor-cell-%02d'%identity['cell']+suffix for suffix in ('.json','.log'))
        if len(expected)!=357:raise ClosurePrerequisite('fixed357 source path grammar changed')
        return expected

    def prepare_custody_inputs(self):
        inventory=self.literal_inventory()
        if set(x['path'] for x in inventory)!=self.expected_baseline_paths():
            raise ClosurePrerequisite('exact untouched357 baseline path roster drift')
        if self._frozen_custody is not None and inventory==self._frozen_inventory:return
        maximum=2 if self.method=='test_V12_each_joint_threshold_failure' else 1
        if len(self.custody_input_versions)>=maximum:raise ClosurePrerequisite('extra custody literal version')
        raw=fixed_stored_zip([(x['path'],self.raw(self.root/x['path'])) for x in inventory])
        if len(raw)>2097152:raise ClosurePrerequisite('literal custody archive exceeds2MiB')
        directory=self.base/('custody-inputs-'+str(len(self.custody_input_versions)+1))
        self._frozen_custody=self.custody_artifacts(inventory,raw,directory)
        self._frozen_inventory=copy.deepcopy(inventory)
        expected_assets={'upload-part.bin','fresh-download-part.bin','github-provider-wrapper-001.zip',
            'upload-transport-manifest.json','fresh-transport-manifest.json'}
        paths={PurePosixPath(path) for path in self.files if PurePosixPath(path).parent==directory}
        if paths!={directory/name for name in expected_assets}:
            raise ClosurePrerequisite('exact five frozen custody input assets missing')
        assets=[copy.deepcopy(self.asset_states[str(path)]) for path in sorted(paths)]
        if any(state['lineage']!='independent_input' or state['asset_role']!='fixed_custody_input_asset' for state in assets):
            raise ClosurePrerequisite('frozen custody asset lineage mismatch')
        self.custody_input_versions.append({'directory':str(directory),'inventory':copy.deepcopy(inventory),
            'archive_size':len(raw),'archive_sha256':sha(raw),'asset_states':assets,
            'frozen_before_operation_ordinal':len(self.operations)+1})

    def custody_artifacts(self,inventory,raw,directory):
        upload=directory/'upload-part.bin';downloaded=directory/'fresh-download-part.bin'
        self.put_raw(upload,raw);self.put_raw(downloaded,raw)
        part={'order':1,'path':'part-001.bin','size':len(raw),'sha256':sha(raw)}
        file_id='literal-Drive-file-one'
        event={'provider':'google_drive','file_id':file_id,'size':len(raw),'sha256':sha(raw)}
        descriptor={**part,'drive_file_id':file_id,'direct_url':'https://drive.google.com/file/d/'+file_id+'/view',
            'upload_input_path':str(upload),'readback_path':str(downloaded),
            'upload_receipt':{**event,'operation':'upload','event_id':'literal-upload-event',
                'completed_at':'2026-10-03T00:00:00Z','parent_folder_id':V_CANONICAL_FOLDER},
            'download_receipt':{**event,'operation':'download','event_id':'literal-download-event','completed_at':'2026-10-03T00:01:00Z'}}
        manifest={'schema':'worker38.transport.v1',
            'files':[{'path':x['path'],'size':x['size_bytes'],'sha256':x['sha256']} for x in inventory],
            'raw_size':sum(x['size_bytes'] for x in inventory),'parts':[part],
            'archive':{'path':'attempt.zip','format':'zip-stored-v1','size':len(raw),'sha256':sha(raw)},
            'limits':{'raw_bytes':67108864,'archive_bytes':67108864,'part_bytes':31457280,'provider_zip_strictly_below_bytes':33554432}}
        manifest_raw=canonical(manifest)
        if len(manifest_raw)>65536:raise ClosurePrerequisite('literal manifest bound')
        wrapper_path=directory/'github-provider-wrapper-001.zip'
        wrapper_raw=fixed_stored_zip([(part['path'],raw),('transport-manifest.json',manifest_raw)])
        self.put_raw(wrapper_path,wrapper_raw)
        wrapper_info={'size':len(wrapper_raw),'sha256':sha(wrapper_raw)}
        provider_wrapper={'order':1,'part_path':part['path'],'member_name':part['path'],'path':str(wrapper_path),
            **wrapper_info,'download_receipt':{'provider':'github_actions','operation':'download',
                'repository':C_REPOSITORY,'run_id':'123','run_attempt':'1','artifact_id':'456',
                'artifact_name':'worker38-123-1-part-001','event_id':'literal-provider-download',
                'completed_at':'2026-10-03T00:00:00Z',**wrapper_info}}
        manifest_upload=directory/'upload-transport-manifest.json';manifest_readback=directory/'fresh-transport-manifest.json'
        self.put_raw(manifest_upload,manifest_raw);self.put_raw(manifest_readback,manifest_raw)
        me={'provider':'google_drive','file_id':'literal-Drive-manifest','size':len(manifest_raw),'sha256':sha(manifest_raw)}
        result={'schema':'worker38-authenticated-custody-v2','status':'verified','provider_wrappers':[provider_wrapper],
            'provider_upload_outcome':{'schema':'worker38-provider-upload-outcome-v1','workflow_run':'123','workflow_attempt':'1',
                'action':'./.github/actions/worker38-upload','status':'completed','conclusion':'success',
                'admission_exit_status':0,'coordinator_exit_status':0,'preservation_exit_status':0,
                'started_at':'2026-10-02T23:59:58Z','completed_at':'2026-10-02T23:59:59Z'},
            'authenticated_by':'parent-connected-Drive-readback','folder_id':V_CANONICAL_FOLDER,
            'verification_sha256':None,'raw_inventory':inventory,'files':[descriptor],'transport_manifest':manifest,
            'manifest_file':{'path':'transport-manifest.json','size':len(manifest_raw),'sha256':sha(manifest_raw),
                'drive_file_id':'literal-Drive-manifest','direct_url':'https://drive.google.com/file/d/literal-Drive-manifest/view',
                'upload_input_path':str(manifest_upload),'readback_path':str(manifest_readback),
                'upload_receipt':{**me,'operation':'upload','event_id':'literal-manifest-upload',
                    'completed_at':'2026-10-03T00:00:00Z','parent_folder_id':V_CANONICAL_FOLDER},
                'download_receipt':{**me,'operation':'download','event_id':'literal-manifest-readback','completed_at':'2026-10-03T00:01:00Z'}}}
        self.custody_path=directory/'externally-authenticated-custody.json'
        if len(canonical(result))+64>131072:raise ClosurePrerequisite('custody receipt bound')
        return result

    def planned_report(self,retained=False):
        cells=[]
        for identity in C_SCHEDULE:
            folder=self.root/'cells'/('%02d'%identity['cell'])
            cells.append({**identity,**{scope:self.read(folder/(scope+'-return.json'))['timing'] for scope in ('candidate','reference')}})
        binding={'trusted_admission_path':str(self.root/'admission-inputs'/'admission.json' if retained else self.admission),
            'trusted_admission_sha256':sha(self.raw(self.admission)),'expected_head':V_HEAD,'expected_tree':V_TREE,
            'root':str(self.root),'trusted_provenance_path':str(self.root/'admission-inputs'/'provenance.json' if retained else self.provenance),
            'trusted_provenance_sha256':sha(self.raw(self.provenance)),'expected_workflow_run':'123','expected_workflow_attempt':'1'}
        report={'schema':'worker38-local-computational-verification-v1' if retained else 'worker38-offline-verification-v2',
            'complete':True,'cells':cells,'total_P_operations':{'legal_enumerations':20,'previews':0,'exit_geometry_checks':0},
            'resource_phase':self.read(self.root/'measurement-phase-close.json')['phase'],
            'prepublication_resource_phase':self.read(self.root/'receipt.json')['resource_totals']['phase'],
            'raw_inventory':self.literal_inventory(),'binding':binding,'custody':'pending','classification':None}
        if retained:report.update(authentication='retained_bytes_only',external_acceptance=False)
        return {**report,'verification_sha256':digest(report)}

    def custody(self,verification):
        if self._frozen_custody is None or verification['raw_inventory']!=self._frozen_inventory:
            raise ClosurePrerequisite('planned report/custody inventory disagreement')
        result=copy.deepcopy(self._frozen_custody)
        result['verification_sha256']=verification['verification_sha256']
        self.write(self.custody_path,result)
        return result

    def emit(self,boundary,arguments):
        index=len(self.events)
        if index>=len(self.expected):raise ClosurePrerequisite('unlisted verifier event '+self.selector)
        event=self.expected[index]
        if event['boundary']!=boundary or event['call_ordinal']!=index+1:
            raise ClosurePrerequisite('ordered verifier boundary drift')
        relative={role:(str(PurePosixPath(path).relative_to(self.case)) if path is not None else None) for role,path in arguments.items()}
        if relative!=event['argument_paths']:raise ClosurePrerequisite('exact effective argument-path drift')
        scope=self.ctx['path_scopes'][event['path_scope_id']]
        recipe=digest({'source_sha256':self.ctx['recipe_sha256'],'selector':self.selector,
            'call_ordinal':index+1,'boundary':boundary,'operations':self.operations})
        states=[]
        for rule in scope['path_rules']:
            relative_path=rule['relative_path'];path=self.case/relative_path
            raw=self.files.get(str(path))
            kind='file' if raw is not None else 'missing'
            if raw is None and any(PurePosixPath(p).is_relative_to(path) for p in self.files):kind='directory'
            lineage='produced_output' if path.name=='externally-authenticated-custody.json' else 'independent_input'
            states.append({'relative_path':relative_path,'rule_id':rule['rule_id'],
                'allowed_state':{'type':kind,'size_bytes':len(raw) if raw is not None else 0,
                    'sha256':sha(raw) if raw is not None else None,'lineage':lineage,
                    'independent_recipe_sha256':recipe}})
        self.events.append({'selector':self.selector,'boundary':boundary,'call_ordinal':index+1,
            'slot':'v%04d'%(index+1),'argument_paths':relative,'path_rules':states,
            'source_bound_mutation_sequence_sha256':recipe,'operation_count':len(self.operations)})

    def capture_verifier(self,report=False,**overrides):
        if self.custody_case is not None:self.prepare_custody_inputs()
        args={'trusted_admission_path':self.admission,'trusted_provenance_path':self.provenance}
        args.update(overrides)
        self.emit('LiteralBundle.verify',{'attempt':self.root,'trusted_admission':args['trusted_admission_path'],
            'trusted_provenance':args['trusted_provenance_path']})
        return self.planned_report() if report else None

    def capture_timing(self,verification,custody,**overrides):
        binding=verification.get('binding',{}) if type(verification) is dict else {}
        if type(binding) is not dict:binding={}
        self.emit('LiteralBundle.timing',{'attempt':binding.get('root'),
            'trusted_admission':binding.get('trusted_admission_path'),'trusted_provenance':binding.get('trusted_provenance_path'),
            'trusted_custody':overrides.get('trusted_custody_path',self.custody_path)})
        return None


    def rejected_mutation(self, path, keys, value):
        full = self.root / path
        before = self.raw(full)
        try:
            self.mutate(path, keys, value)
            self.capture_verifier()
        finally:
            self.put_raw(full, before)
            self.refresh()

    def recipe_V01_complete_literal_bundle(self):
        result = self.capture_verifier(report=True)

    def recipe_V04_parent_source_preflight(self):
        for keys, value in ((['evaluator_starts'], 1), (['restored_source_inventory'], []), (['diagnostic_files_sha256'], {}), (['runtime', 'inherited_limits'], {}), (['coordinator_address_space'], [-1, -1])):
            self.rejected_mutation('source-runtime-preflight.json', keys, value)
        path = self.root / 'restored' / V_SOURCE_MODULES[0][0]
        original = self.raw(path)
        self.put_raw(path, b'# altered inert source\n')
        self.refresh()
        self.capture_verifier()
        self.put_raw(path, original)
        self.refresh()
        self.rejected_mutation('stub-test-receipt.json', ['checked_file_sha256'], {})

    def recipe_V05_cell_module_manifest(self):
        path = 'cells/01/source-runtime-preflight.json'
        module = 'worker35_resources'
        for keys, value in ((['modules'], {}), (['modules', module, 'path'], '/ambient/module.py'), (['modules', module, 'sha256'], 'f' * 64), (['modules', module, 'git_blob'], 'f' * 40), (['modules', module, 'size_bytes'], 0)):
            self.rejected_mutation(path, keys, value)

    def recipe_V06_exact_runtime_policy(self):
        path = 'cells/02/source-runtime-preflight.json'
        runtime = self.runtime(2)
        variants = ((['runtime', 'flags'], ['/invented/python', '-I', '-s', self.script]), (['runtime', 'flags'], ['/invented/python', '-B', '-s', '-O', self.script]), (['runtime', 'address_space'], [-1, -1]), (['runtime', 'gc_enabled'], False), (['runtime', 'gc_threshold'], [100, 10, 10]), (['runtime', 'python_environment'], {'PYTHONPATH': '/ambient'}), (['runtime', 'executable_sha256'], 'f' * 64), (['runtime', 'version'], '3.12.14'), (['runtime', 'effective_flags', 'optimize'], 1))
        for keys, value in variants:
            self.rejected_mutation(path, keys, value)

    def recipe_V07_supervision_and_logs_required_for_every_cell(self):
        self.rejected_mutation('supervisor-cell-01.json', ['child_accounting_complete'], False)
        self.rejected_mutation('supervisor-cell-01.json', ['phase_accounting_complete'], False)
        self.rejected_mutation('supervisor-cell-01.json', ['cleanup', 'failure_details'], [{'status': 'resource_incomplete'}])
        self.rejected_mutation('supervisor-cell-01.json', ['primary_outcome'], {'status': 'resource_incomplete', 'reason': 'call_wall_limit'})
        self.rejected_mutation('supervisor-cell-01.json', ['secondary_failures'], [{'status': 'execution_incomplete', 'reason': 'cleanup', 'phase': 'cleanup'}])
        for index in range(1, 21):
            for suffix in ('.json', '.log'):
                path = self.root / f'supervisor-cell-{index:02d}{suffix}'
                raw = self.raw(path)
                self.remove(path)
                self.refresh()
                self.capture_verifier()
                self.put_raw(path, raw)
                self.refresh()
        for keys, value in ((['returncode'], 1), (['cleanup', 'complete'], False), (['cleanup', 'remaining_pids'], [123]), (['output_prefix_gap'], True), (['output_durable'], False), (['output_bytes_preserved'], 1), (['output_pipe_tail'], 'unobserved'), (['errors'], ['literal failure']), (['limits', 'call_wall_seconds'], 999), (['inherited_limits'], {}), (['wall_seconds'], 720), (['child_cpu_seconds'], 720)):
            self.rejected_mutation('supervisor-cell-01.json', keys, value)

    def recipe_V08_parent_totals_errors_inventory(self):
        for keys, value in ((['completed_prefix'], list(range(1, 20))), (['actual_returns'], 39), (['capture_gaps'], [{'cell': 1}]), (['corrupt_evidence'], [{'literal': 'corrupt'}]), (['unavailable_evidence'], [{'literal': 'unavailable'}]), (['retained_failures'], [{'status': 'integrity_invalid'}]), (['error'], 'literal error'), (['resource_totals', 'P_operations', 'legal_enumerations'], 19), (['resource_totals', 'phase', 'cpu_seconds'], 1800), (['resource_totals', 'phase', 'wall_seconds'], 1800)):
            self.rejected_mutation('receipt.json', keys, value)
        self.rejected_mutation('supervisor-cell-02.json', ['phase', 'wall_seconds'], 0)
        self.mutate('receipt.json', ['file_inventory'], [], refresh=False)
        self.capture_verifier()

    def recipe_V09_science_rng_capture_boundary(self):
        cases = (('cells/01/candidate-capture-confirmed.json', ['sha256'], 'f' * 64), ('cells/01/candidate-start.json', ['scope'], 'reference'), ('cells/01/candidate-start.json', ['initial_rng_sha256'], 'f' * 64), ('cells/01/candidate-start.json', ['source_modules'], {}), ('cells/01/cell-boundaries.json', ['public_after'], {'literal': 'changed'}), ('cells/01/cell-boundaries.json', ['equality'], False), ('cells/01/cell-start.json', ['conservation_before', 'inventory_count'], 68), ('cells/01/cell-receipt.json', ['hook_restored'], False), ('cells/01/cell-receipt.json', ['timer_restored'], False), ('cells/01/cell-receipt.json', ['calls', 'candidate', 'returned'], False))
        for path, keys, value in cases:
            self.rejected_mutation(path, keys, value)
        folder = self.root / 'cells/02'
        path = folder / 'reference-return.json'
        payload = self.read(path)
        payload['scientific']['guards'] = [{'literal': 'different reference scientific object'}]
        payload['scientific_sha256'] = digest(payload['scientific'])
        self.write(path, payload)
        self.reconfirm(2, 'reference')
        self.refresh()
        self.capture_verifier()

    def reconfirm(self, index, scope):
        folder = self.root / 'cells' / f'{index:02d}'
        path = folder / (scope + '-return.json')
        evidence = {'path': path.relative_to(self.root).as_posix(), **self.info(path)}
        self.write(folder / (scope + '-capture-confirmed.json'), evidence)
        receipt = self.read(folder / 'cell-receipt.json')
        receipt['calls'][scope]['evidence'] = evidence
        self.write(folder / 'cell-receipt.json', receipt)

    def recipe_V10_required_accounting_and_timing(self):
        cases = (('cells/02/active-call.json', ['active'], True), ('cells/02/unmeasured-accounting.json', ['physical_cost'], {}), ('cells/01/whole-wrapper-resources.json', ['operations', 'previews'], 1))
        for path, keys, value in cases:
            self.rejected_mutation(path, keys, value)
        for value in (0, -1, 360, True):
            path = self.root / 'cells/02/candidate-return.json'
            original = self.raw(path)
            payload = self.read(path)
            payload['timing']['cpu_seconds'] = value
            self.write(path, payload)
            self.reconfirm(2, 'candidate')
            self.refresh()
            self.capture_verifier()
            self.put_raw(path, original)
            self.reconfirm(2, 'candidate')
            self.refresh()
        path = self.root / 'cells/01/decision-traces/pass-2/11.jsonl'
        lines = self.rows(path)
        lines[1]['audit']['boundary']['choice_calls'] = 1
        self.write(path, b''.join((canonical(row) for row in lines)), raw=True)
        self.refresh()
        self.capture_verifier()

    def set_u_cpu(self, first, second):
        for identity in C_SCHEDULE:
            if identity['condition'] == 'U' and identity['size'] in (40, 48):
                for scope in ('candidate', 'reference'):
                    path = self.root / 'cells' / f"{identity['cell']:02d}" / (scope + '-return.json')
                    payload = self.read(path)
                    payload['timing']['cpu_seconds'] = first if identity['repetition'] == 1 else second
                    self.write(path, payload)
                    self.reconfirm(identity['cell'], scope)
        self.refresh()

    def recipe_V11_joint_threshold_inclusive(self):
        self.set_u_cpu(9, 7)
        verified = self.capture_verifier(report=True)
        custody = self.custody(verified)
        report = self.capture_timing(verified, custody)

    def recipe_V12_each_joint_threshold_failure(self):
        for first, second in ((8.01, 8.01), (9.01, 6)):
            self.set_u_cpu(first, second)
            verified = self.capture_verifier(report=True)
            custody = self.custody(verified)
            self.capture_timing(verified, custody)

    def recipe_V13_revalidate_complete_evidence_binding(self):
        verified = self.capture_verifier(report=True)
        custody = self.custody(verified)
        fabricated = {'complete': True, 'cells': verified['cells'], 'raw_inventory': verified['raw_inventory']}
        self.capture_timing(fabricated, custody)
        forged = copy.deepcopy(verified)
        forged['cells'][0]['candidate']['cpu_seconds'] = 0.1
        self.capture_timing(forged, custody)
        self.mutate('supervisor-cell-01.json', ['output_prefix_gap'], True)
        self.capture_timing(verified, custody)

    def recipe_V14_external_custody_gate(self):
        verified = self.capture_verifier(report=True)
        custody = self.custody(verified)
        self.capture_timing(verified, custody, trusted_custody_sha256='f' * 64)
        for keys, value in ((['status'], 'pending'), (['status'], 'blocked'), (['folder_id'], 'other-folder'), (['verification_sha256'], 'f' * 64), (['raw_inventory'], []), (['files'], [])):
            altered = copy.deepcopy(custody)
            set_nested(altered, keys, value)
            self.write(self.custody_path, altered)
            self.capture_timing(verified, altered)
        self.write(self.custody_path, custody)
        altered = copy.deepcopy(custody)
        altered['authenticated_by'] = 'self-described-untrusted'
        self.capture_timing(verified, altered)

    def recipe_V15_exact_readback_provenance_and_files(self):
        verified = self.capture_verifier(report=True)
        custody = self.custody(verified)
        variants = ((['files', 0, 'size'], 1), (['files', 0, 'sha256'], 'f' * 64), (['files', 0, 'drive_file_id'], ''), (['files', 0, 'direct_url'], 'https://example.com/file'), (['files', 0, 'download_receipt', 'event_id'], 'literal-upload-event'), (['files', 0, 'download_receipt', 'completed_at'], '2026-10-02T00:00:00Z'), (['files', 0, 'upload_receipt', 'parent_folder_id'], 'wrong-folder'), (['files', 0, 'readback_path'], custody['files'][0]['upload_input_path']), (['transport_manifest', 'files'], []))
        for keys, value in variants:
            altered = copy.deepcopy(custody)
            set_nested(altered, keys, value)
            self.write(self.custody_path, altered)
            self.capture_timing(verified, altered)
        self.write(self.custody_path, custody)
        path = PurePosixPath(custody['files'][0]['readback_path'])
        original = self.raw(path)
        self.put_raw(path, b'corrupt literal downloaded bytes')
        self.capture_timing(verified, custody)
        self.put_raw(path, original)
        self.remove(path)
        self.capture_timing(verified, custody)

    def recipe_V16_closing_phase_proof(self):
        path = self.root / 'measurement-phase-close.json'
        original = self.raw(path)
        self.remove(path)
        self.capture_verifier()
        self.put_raw(path, original)
        for key, value in (('computational_receipt', {'path': 'receipt.json', 'size_bytes': 1, 'sha256': '0' * 64}), ('preservation_deadline_monotonic', 10601), ('includes_computational_receipt_publication', False)):
            data = json.loads(original)
            data[key] = value
            self.write(path, data)
            self.capture_verifier()
        data = json.loads(original)
        data['phase']['cpu_seconds'] = 1800
        self.write(path, data)
        self.capture_verifier()
        self.put_raw(path, original)
        self.capture_verifier()

    def recipe_V17_closing_totals_are_reported(self):
        result = self.capture_verifier(report=True)
        closing = self.read(self.root / 'measurement-phase-close.json')

    def recipe_V18_matched_clock_error_types(self):
        path = self.root / 'cells/02/candidate-return.json'
        original = self.raw(path)
        for value, kind in ((360, ValueError), (361, ValueError), ('360', ValueError), (True, ValueError), (0, ValueError), (-1, ValueError), (10 ** 400, ValueError)):
            payload = json.loads(original)
            payload['timing']['cpu_seconds'] = value
            self.write(path, payload)
            self.reconfirm(2, 'candidate')
            self.refresh()
            self.capture_verifier()
        self.put_raw(path, original)
        self.reconfirm(2, 'candidate')
        self.refresh()
        self.capture_verifier()

    def recipe_V19_recovery_loader_runtime_binding(self):
        self.capture_verifier()
        cases = (('null_loader', 'update', ['runtime', 'loader'], None), ('portable_substitute', 'update', ['runtime', 'loader'], V_LOADER_PIN), ('wrong_schema', 'update', ['runtime', 'loader', 'schema'], 'untrusted-loader'), ('missing_mapping', 'delete', ['runtime', 'loader', 'mapped_library'], None), ('wrong_library_hash', 'update', ['runtime', 'loader', 'library_sha256'], 'e' * 64), ('boolean_library_size', 'update', ['runtime', 'loader', 'library_size_bytes'], True), ('wrong_executable_path', 'update', ['runtime', 'loader', 'executable_path'], '/ambient/python'), ('wrong_mapped_inode', 'update', ['runtime', 'loader', 'mapped_library', 'inode'], 5678), ('wrong_mapped_device', 'update', ['runtime', 'loader', 'mapped_library', 'device'], {'major': 8, 'minor': 2}), ('wrong_loader_environment', 'update', ['runtime', 'loader', 'loader_environment'], {'LD_LIBRARY_PATH': '/ambient/lib'}), ('extra_identity_field', 'update', ['runtime', 'loader', 'extra'], False), ('different_runtime_executable', 'update', ['runtime', 'executable'], '/ambient/python'))
        for name in ('source-runtime-preflight.json', 'cells/02/source-runtime-preflight.json'):
            path = self.root / name
            original = self.raw(path)
            try:
                for label, action, keys, replacement in cases:
                    value = json.loads(original)
                    if action == 'delete':
                        parent = value
                        for key in keys[:-1]:
                            parent = parent[key]
                        del parent[keys[-1]]
                    else:
                        set_nested(value, keys, copy.deepcopy(replacement))
                    self.write(path, value)
                    self.refresh()
                    self.capture_verifier()
            finally:
                self.put_raw(path, original)
                self.refresh()
        path = self.root / 'cells/02/source-runtime-preflight.json'
        original = self.raw(path)
        try:
            value = json.loads(original)
            value['runtime']['loader']['library_inode'] = 5678
            value['runtime']['loader']['mapped_library']['inode'] = 5678
            value['runtime']['shared_startup_observation']['files']['library']['inode'] = 5678
            value['runtime']['shared_startup_observation']['files']['library']['observed_mapping']['inode'] = 5678
            self.write(path, value)
            self.refresh()
            self.capture_verifier()
        finally:
            self.put_raw(path, original)
            self.refresh()
        self.capture_verifier()

    def recipe_V20_supervisor_preservation_boundary_consistency(self):
        path = self.root / 'supervisor-cell-01.json'
        original = self.raw(path)
        self.capture_verifier()
        flags = ('preservation_transition_attempted', 'preservation_transition_complete', 'preservation_expired', 'preservation_blocked')
        failure = {'status': 'resource_incomplete', 'reason': 'literal_preservation_failure'}
        cases = [('missing_' + key, 'delete', {key: None}) for key in ('preservation_deadline_monotonic', *flags)]
        cases += [('nonnull_deadline_' + repr(value), 'update', {'preservation_deadline_monotonic': value}) for value in (0, 10000, '10000', False)]
        cases += [('wrong_' + key + '_' + repr(value), 'update', {key: value}) for key in flags for value in (True, None, 0, 'false')]
        cases += [('forbidden_' + key + '_' + repr(value), 'update', {key: value}) for key in ('first_terminal_failure', 'preservation_boundary_failure') for value in (None, failure)]
        cases.append(('contradictory_completed_record', 'update', {'preservation_deadline_monotonic': 10000, 'preservation_transition_attempted': True, 'preservation_transition_complete': True, 'first_terminal_failure': failure}))
        try:
            for name, action, changes in cases:
                value = json.loads(original)
                if action == 'delete':
                    for key in changes:
                        del value[key]
                else:
                    value.update(changes)
                self.write(path, value)
                self.refresh()
                self.capture_verifier()
        finally:
            self.put_raw(path, original)
            self.refresh()
        self.capture_verifier()

    def recipe_V21_supervisor_partial_spawn_consistency(self):
        path = self.root / 'supervisor-cell-01.json'
        original = self.raw(path)
        self.capture_verifier()
        true_flags = ('spawn_attempted', 'spawn_initialization_complete')
        cases = [('missing_' + key, 'delete', {key: None}) for key in (*true_flags, 'spawn_ownership_uncertain')]
        cases += [('wrong_' + key + '_' + repr(value), 'update', {key: value}) for key in true_flags for value in (False, None, 1, 'true')]
        cases += [('wrong_uncertainty_' + repr(value), 'update', {'spawn_ownership_uncertain': value}) for value in (True, None, 0, 'false')]
        cases += [('partial_constructor_contradiction', 'update', {'spawn_attempted': True, 'spawn_initialization_complete': False, 'spawn_ownership_uncertain': True}), ('unattempted_constructor_contradiction', 'update', {'spawn_attempted': False, 'spawn_initialization_complete': False, 'spawn_ownership_uncertain': False})]
        cases += [('missing_' + key, 'delete', {key: None}) for key in ('spawn_discovery', 'spawn_recovered_pids')]
        cases += [('wrong_discovery_' + repr(value), 'update', {'spawn_discovery': value}) for value in (None, False, 'initialized', 'recovered')]
        cases += [('wrong_recovered_pids_' + repr(value), 'update', {'spawn_recovered_pids': value}) for value in (None, False, 0, {}, '[]', [123])]
        cases.append(('recovery_diagnostics_contradiction', 'update', {'spawn_discovery': 'recovered', 'spawn_recovered_pids': [123]}))
        try:
            for name, action, changes in cases:
                value = json.loads(original)
                if action == 'delete':
                    for key in changes:
                        del value[key]
                else:
                    value.update(changes)
                self.write(path, value)
                self.refresh()
                self.capture_verifier()
        finally:
            self.put_raw(path, original)
            self.refresh()
        self.capture_verifier()

    def rewrite_rows(self, relative, edit):
        path = self.root / relative
        values = self.rows(path)
        edit(values)
        self.write(path, b''.join((canonical(row) for row in values)), raw=True)
        self.refresh()

    def reject_row_mutation(self, relative, edit, error=ValueError):
        path = self.root / relative
        original = self.raw(path)
        try:
            self.rewrite_rows(relative, edit)
            self.capture_verifier()
        finally:
            self.put_raw(path, original)
            self.refresh()

    def recipe_JR01_exact_successful_journal_schema(self):
        verified = self.capture_verifier(report=True)
        calls = self.rows(self.root / 'cells/01/call-results/pass-2/11.jsonl')

    def recipe_JR02_identical_reference_science_contradiction(self):
        for index in (1, 20):

            def edit(rows):
                science = copy.deepcopy(rows[0]['result']['scientific'])
                science['guards'] = [{'literal': 'contradictory reference object'}]
                rows[1]['result']['scientific'] = science
            self.rewrite_rows(f'cells/{index:02d}/call-results/pass-2/11.jsonl', edit)
        self.capture_verifier()

    def recipe_JR03_matching_extra_reference_science_rejected(self):

        def edit(rows):
            rows[1]['result']['scientific'] = copy.deepcopy(rows[0]['result']['scientific'])
        self.reject_row_mutation('cells/01/call-results/pass-2/11.jsonl', edit)

    def recipe_JR04_reference_digest_required_and_bound(self):
        for missing in (False, True):

            def edit(rows):
                if missing:
                    del rows[1]['result']['scientific_sha256']
                else:
                    rows[1]['result']['scientific_sha256'] = 'e' * 64
            self.reject_row_mutation('cells/01/call-results/pass-2/11.jsonl', edit)

    def recipe_JR05_chosen_bound_to_each_full_sidecar(self):
        for index in (0, 1):

            def edit(rows):
                rows[index]['result']['chosen'] = {'literal': 'different chosen value'}
            self.reject_row_mutation('cells/01/call-results/pass-2/11.jsonl', edit)

    def recipe_JR06_ordinal_scope_and_exact_result_keys(self):
        for index in (0, 1):
            for kind in ('changed_ordinal', 'missing_ordinal', 'wrong_scope', 'extra_result_key'):

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

    def recipe_JR07_full_reference_sidecar_still_required(self):
        path = self.root / 'cells/01/reference-return.json'
        original = self.raw(path)
        for kind in ('missing', 'corrupt'):
            if kind == 'missing':
                self.remove(path)
            else:
                self.put_raw(path, b'{')
            self.refresh()
            self.capture_verifier()
            self.put_raw(path, original)
            self.refresh()
        self.capture_verifier()

    def recipe_MR01_complete_original_metric_fields(self):
        result = self.capture_verifier(report=True)
        metrics = self.rows(self.root / 'cells/01/resource-metrics.jsonl')

    def recipe_MR02_inclusive_clock_and_uncapped_rss_fields(self):
        metrics = self.rows(self.root / 'cells/01/resource-metrics.jsonl')
        for scope, original in zip(('candidate', 'reference'), metrics):
            for key in ('wall_seconds', 'cpu_seconds'):
                for value in (0, 360):
                    metric = copy.deepcopy(original)
                    metric[key] = value
            for value in (0, 1000, 600000):
                metric = copy.deepcopy(original)
                metric['peak_rss_kib'] = value
        self.rewrite_rows('cells/01/resource-metrics.jsonl', lambda rows: [row.update(peak_rss_kib=600000) for row in rows])
        self.mutate('cells/01/whole-wrapper-resources.json', ['peak_rss_kib'], 600001)
        self.mutate('cells/01/cell-receipt.json', ['peak_rss_kib'], 600002)
        self.mutate('supervisor-cell-01.json', ['child_high_water_rss_kib'], 600003)
        self.capture_verifier()

    def recipe_MR03_missing_malformed_and_over_cap_metrics(self):
        for index in (0, 1):
            for key in ('wall_seconds', 'cpu_seconds', 'peak_rss_kib'):
                cases = ('missing', -1, True, None, '0', 1.5) if key == 'peak_rss_kib' else ('missing', -1, True, None, '0', 360.000001)
                for replacement in cases:

                    def edit(rows):
                        if replacement == 'missing':
                            del rows[index][key]
                        else:
                            rows[index][key] = replacement
                    expected = ValueError if key != 'peak_rss_kib' and replacement == 360.000001 else ValueError
                    self.reject_row_mutation('cells/01/resource-metrics.jsonl', edit, expected)

    def recipe_MR04_metric_identity_fields(self):
        for index in (0, 1):
            for key, replacement in (('kind', 'policy'), ('pass', 3), ('seed', 12), ('ordinal', 2), ('scope', 'control'), ('status', 'failed')):
                self.reject_row_mutation('cells/01/resource-metrics.jsonl', lambda rows: rows[index].update({key: replacement}))

    def recipe_MR05_identical_invalid_repeated_metrics(self):
        for index in (1, 20):
            self.rewrite_rows(f'cells/{index:02d}/resource-metrics.jsonl', lambda rows: [row.update(wall_seconds=-1) for row in rows])
        self.capture_verifier()

    def recipe_MR06_nonfinite_and_huge_integer_metrics(self):
        path = self.root / 'cells/01/resource-metrics.jsonl'
        original = self.raw(path)
        for token in (b'NaN', b'Infinity', b'-Infinity'):
            self.put_raw(path, original.replace(b'"wall_seconds":13', b'"wall_seconds":' + token, 1))
            self.refresh()
            self.capture_verifier()
            self.put_raw(path, original)
            self.refresh()
        self.reject_row_mutation('cells/01/resource-metrics.jsonl', lambda rows: rows[0].update(cpu_seconds=10 ** 400))

    def recipe_MR07_true_integer_monotonic_high_water(self):
        participants = (('candidate', 'cells/01/resource-metrics.jsonl', 0, 'peak_rss_kib'), ('reference', 'cells/01/resource-metrics.jsonl', 1, 'peak_rss_kib'), ('wrapper', 'cells/01/whole-wrapper-resources.json', None, 'peak_rss_kib'), ('cell', 'cells/01/cell-receipt.json', None, 'peak_rss_kib'), ('supervisor', 'supervisor-cell-01.json', None, 'child_high_water_rss_kib'))
        for name, relative, row, key in participants:
            for value in (-1, True, None, 1.5, '1000'):
                if row is not None:
                    self.reject_row_mutation(relative, lambda rows: rows[row].update({key: value}))
                else:
                    self.rejected_mutation(relative, [key], value)
        for name, relative, row, key in participants[:-1]:
            if row is not None:
                self.reject_row_mutation(relative, lambda rows: rows[row].update({key: 1001}))
            else:
                self.rejected_mutation(relative, [key], 1001)

    def recipe_MR08_method_rows_and_unmeasured_flags_unchanged(self):
        verified = self.capture_verifier(report=True)
        custody = self.custody(verified)
        report = self.capture_timing(verified, custody)

    def recipe_PW01_complete_wrapper_final_classification(self):
        verified = self.capture_verifier(report=True)
        custody = self.custody(verified)
        report = self.capture_timing(verified, custody)

    def recipe_PW02_wrapper_coverage_is_mandatory(self):
        verified = self.capture_verifier(report=True)
        custody = self.custody(verified)
        for kind in ('missing', 'null', 'empty'):
            changed = copy.deepcopy(custody)
            if kind == 'missing':
                del changed['provider_wrappers']
            else:
                changed['provider_wrappers'] = None if kind == 'null' else []
            self.write(self.custody_path, changed)
            self.capture_timing(verified, changed)

    def recipe_PW13_outer_wrapper_is_not_canonical_part(self):
        verified = self.capture_verifier(report=True)
        custody = self.custody(verified)
        outer = self.raw(PurePosixPath(custody['provider_wrappers'][0]['path']))
        for key in ('upload_input_path', 'readback_path'):
            self.put_raw(PurePosixPath(custody['files'][0][key]), outer)
        self.capture_timing(verified, custody)

    def recipe_PW14_exact_and_semantic_wrapper_binding(self):
        verified = self.capture_verifier(report=True)
        custody = self.custody(verified)
        changed = copy.deepcopy(custody)
        changed['provider_wrappers'][0]['download_receipt']['run_id'] = '999'
        self.capture_timing(verified, changed)
        self.write(self.custody_path, changed)
        self.capture_timing(verified, changed)

    def recipe_PW15_legacy_custody_is_not_accepted(self):
        verified = self.capture_verifier(report=True)
        custody = self.custody(verified)
        custody['schema'] = 'worker38-authenticated-custody-v1'
        self.write(self.custody_path, custody)
        self.capture_timing(verified, custody)

    def recipe_ER_I02_retained_prerequisites_replayed_offline(self):
        mutations = (('pull-request.json', ('head', 'sha'), '3333333333333333333333333333333333333333', 'pr_head'), ('postmerge-ci.json', ('conclusion',), 'failure', 'ci_run_scope'), ('current-source-ci.json', ('head_sha',), '3333333333333333333333333333333333333333', 'ci_run_scope'), ('review-exhaustive.json', ('verdict',), 'not_clean', 'review_clean_exact_scope'), ('review-adversarial.json', ('native_reviewer_id',), self.go['reviews'][0]['native_reviewer_id'], 'review_clean_exact_scope'), ('preregistration.json', ('issue_url',), A_API + '/issues/101', 'comment_identity'), ('diagnostic-commit.json', ('tree', 'sha'), '4444444444444444444444444444444444444444', 'diagnostic_commit_tree'))
        names = ('event.json', 'request-context.json', *A_INPUT_NAMES, 'admission.json', 'provenance.json')
        original = {name: self.raw(self.auth / name) for name in names}
        original_go = json.loads(original['admission.json'])
        for name, keys, replacement, expected_code in mutations:
            self.capture_verifier()
            corpus = dict(original)
            go = copy.deepcopy(original_go)
            value = json.loads(corpus[name])
            try:
                if name in ('review-exhaustive.json', 'review-adversarial.json'):
                    prefix, suffix = (A_REVIEW_START + '\n', A_REVIEW_END + '\n')
                    attestation = json.loads(value['body'][len(prefix):-len(suffix)])
                    set_nested(attestation, keys, replacement)
                    value['body'] = prefix + canonical(attestation).decode() + suffix
                    review_index = 0 if name == 'review-exhaustive.json' else 1
                    go['reviews'][review_index]['body_sha256'] = sha(value['body'].encode())
                    corpus['admission.json'] = canonical(go)
                    body = A_START + '\n' + corpus['admission.json'].decode() + A_END + '\n' + A_DIGEST + ': ' + sha(corpus['admission.json']) + '\n'
                    event = json.loads(corpus['event.json'])
                    pr = json.loads(corpus['pull-request.json'])
                    event['pull_request']['body'] = pr['body'] = body
                    corpus['event.json'] = canonical(event)
                    corpus['pull-request.json'] = canonical(pr)
                else:
                    set_nested(value, keys, replacement)
                corpus[name] = canonical(value)
                provenance = json.loads(original['provenance.json'])
                provenance['admission_sha256'] = sha(corpus['admission.json'])
                provenance['body_sha256'] = sha(json.loads(corpus['event.json'])['pull_request']['body'].encode())
                provenance['event_sha256'] = sha(corpus['event.json'])
                provenance['request_context_sha256'] = sha(corpus['request-context.json'])
                provenance['admission_input_hashes'] = {key: sha(corpus[key]) for key in A_INPUT_NAMES}
                provenance['reviews'] = copy.deepcopy(go['reviews'])
                corpus['provenance.json'] = canonical(provenance)
                for key, raw in corpus.items():
                    self.write(self.auth / key, raw, raw=True)
                    self.write(self.root / 'admission-inputs' / key, raw, raw=True)
                self.write(self.root / 'external-admission.json', corpus['admission.json'], raw=True)
                self.write_startup()
                self.mutate('receipt.json', ['admission_sha256'], sha(corpus['admission.json']))
                self.capture_verifier()
            finally:
                for key, raw in original.items():
                    self.write(self.auth / key, raw, raw=True)
                    self.write(self.root / 'admission-inputs' / key, raw, raw=True)
                self.write(self.root / 'external-admission.json', original['admission.json'], raw=True)
                self.write_startup()
                self.mutate('receipt.json', ['admission_sha256'], sha(original['admission.json']))
            self.capture_verifier()

    def configure_exact_branches(self):
        original=self.raw(self.root/'stub-test-receipt.json')
        changed=json.loads(original)
        del changed['checked_file_sha256']['scripts/worker_bootstrap_shared.sh']
        changed_raw=canonical(changed)
        original_hash,changed_hash=sha(original),sha(changed_raw)
        self.branches={'V03':{'original_stub_sha256':original_hash,'compared_digest':'f'*64,
                'optional_callback':original_hash=='f'*64},
            'V22':{'original_stub_sha256':original_hash,'deleted_shell_stub_sha256':changed_hash,
                'raw_bytes_equal':original==changed_raw,'optional_callback':original_hash==changed_hash}}
        case=self.method.split('_')[1]
        if case not in ('V03','V22') or not self.branches[case]['optional_callback']:return
        scope='scope-dc2312b64cbdd7fd'
        if scope not in self.ctx['path_scopes']:
            raise ClosurePrerequisite('conditional36path scope missing')
        template=copy.deepcopy(self.expected[0])
        template.update(boundary='LiteralBundle.verify',path_scope_id=scope,
            variant='independent exact byte/hash comparison selected optional '+case,selected_path_count=36)
        self.expected.insert(1,template)
        for index,e in enumerate(self.expected,1):
            e['call_ordinal']=index;e['slot']='v%04d'%index

    def recipe_V02_external_admission_binding(self):
        self.emit('VerifyIntegrationTests.test_V02_external_admission_binding',
            {'attempt':self.root,'trusted_admission':self.root/'admission-inputs'/'admission.json',
                'trusted_provenance':self.root/'admission-inputs'/'provenance.json'})
        for overrides in ({'trusted_admission_path':self.root/'external-admission.json'},
            {'trusted_admission_sha256':'f'*64},{'expected_head':'f'*40},{'expected_tree':'f'*40},
            {'trusted_provenance_sha256':'f'*64},{'expected_workflow_run':'999'},{'expected_workflow_attempt':'2'}):
            self.capture_verifier(**overrides)
        for keys,value in ((['attempt_id'],'different'),(['attempt_path'],'/elsewhere/worker38-123-1'),
            (['admission_sha256'],'f'*64),(['diagnostic_tree'],'f'*40)):
            self.rejected_mutation('receipt.json',keys,value)
        self.rejected_mutation('admission-inputs/event.json',['sender','login'],'other-person')

    def recipe_V03_authenticated_freeze_pins(self):
        # Eight pre-auth rejection branches never reach the observed callback.
        # Source-manifest hash has valid syntax, so this exact variant does.
        original=copy.deepcopy(self.go)
        self.go=copy.deepcopy(original);self.go['source_manifest_sha256']='f'*64
        self.write_auth();self.mutate('receipt.json',['admission_sha256'],sha(self.raw(self.admission)))
        self.capture_verifier()
        if self.branches['V03']['optional_callback']:
            self.go=copy.deepcopy(original);self.go['stub_test_receipt_sha256']='f'*64
            self.write_auth();self.mutate('receipt.json',['admission_sha256'],sha(self.raw(self.admission)))
            self.capture_verifier()
        self.go=original;self.write_auth()

    def recipe_V22_recovery_loader_admission_and_helper_pin(self):
        self.capture_verifier()
        original_go=copy.deepcopy(self.go);path=self.root/'stub-test-receipt.json';original=self.raw(path)
        changed=json.loads(original);del changed['checked_file_sha256']['scripts/worker_bootstrap_shared.sh']
        self.put_raw(path,canonical(changed));self.go=copy.deepcopy(original_go)
        self.go['stub_test_receipt_sha256']=self.info(path)['sha256']
        if self.branches['V22']['optional_callback']:
            self.write_auth();self.mutate('receipt.json',['admission_sha256'],sha(self.raw(self.admission)))
            self.capture_verifier()
        self.go=original_go;self.put_raw(path,original);self.write_auth()
        self.mutate('receipt.json',['admission_sha256'],sha(self.raw(self.admission)))
        self.capture_verifier()

VERIFIER_RECIPES = {
    'test_ER_I02_retained_prerequisites_replayed_offline': VerifierRecipe.recipe_ER_I02_retained_prerequisites_replayed_offline,
    'test_JR01_exact_successful_journal_schema': VerifierRecipe.recipe_JR01_exact_successful_journal_schema,
    'test_JR02_identical_reference_science_contradiction': VerifierRecipe.recipe_JR02_identical_reference_science_contradiction,
    'test_JR03_matching_extra_reference_science_rejected': VerifierRecipe.recipe_JR03_matching_extra_reference_science_rejected,
    'test_JR04_reference_digest_required_and_bound': VerifierRecipe.recipe_JR04_reference_digest_required_and_bound,
    'test_JR05_chosen_bound_to_each_full_sidecar': VerifierRecipe.recipe_JR05_chosen_bound_to_each_full_sidecar,
    'test_JR06_ordinal_scope_and_exact_result_keys': VerifierRecipe.recipe_JR06_ordinal_scope_and_exact_result_keys,
    'test_JR07_full_reference_sidecar_still_required': VerifierRecipe.recipe_JR07_full_reference_sidecar_still_required,
    'test_MR01_complete_original_metric_fields': VerifierRecipe.recipe_MR01_complete_original_metric_fields,
    'test_MR02_inclusive_clock_and_uncapped_rss_fields': VerifierRecipe.recipe_MR02_inclusive_clock_and_uncapped_rss_fields,
    'test_MR03_missing_malformed_and_over_cap_metrics': VerifierRecipe.recipe_MR03_missing_malformed_and_over_cap_metrics,
    'test_MR04_metric_identity_fields': VerifierRecipe.recipe_MR04_metric_identity_fields,
    'test_MR05_identical_invalid_repeated_metrics': VerifierRecipe.recipe_MR05_identical_invalid_repeated_metrics,
    'test_MR06_nonfinite_and_huge_integer_metrics': VerifierRecipe.recipe_MR06_nonfinite_and_huge_integer_metrics,
    'test_MR07_true_integer_monotonic_high_water': VerifierRecipe.recipe_MR07_true_integer_monotonic_high_water,
    'test_MR08_method_rows_and_unmeasured_flags_unchanged': VerifierRecipe.recipe_MR08_method_rows_and_unmeasured_flags_unchanged,
    'test_PW01_complete_wrapper_final_classification': VerifierRecipe.recipe_PW01_complete_wrapper_final_classification,
    'test_PW02_wrapper_coverage_is_mandatory': VerifierRecipe.recipe_PW02_wrapper_coverage_is_mandatory,
    'test_PW13_outer_wrapper_is_not_canonical_part': VerifierRecipe.recipe_PW13_outer_wrapper_is_not_canonical_part,
    'test_PW14_exact_and_semantic_wrapper_binding': VerifierRecipe.recipe_PW14_exact_and_semantic_wrapper_binding,
    'test_PW15_legacy_custody_is_not_accepted': VerifierRecipe.recipe_PW15_legacy_custody_is_not_accepted,
    'test_V01_complete_literal_bundle': VerifierRecipe.recipe_V01_complete_literal_bundle,
    'test_V02_external_admission_binding': VerifierRecipe.recipe_V02_external_admission_binding,
    'test_V03_authenticated_freeze_pins': VerifierRecipe.recipe_V03_authenticated_freeze_pins,
    'test_V04_parent_source_preflight': VerifierRecipe.recipe_V04_parent_source_preflight,
    'test_V05_cell_module_manifest': VerifierRecipe.recipe_V05_cell_module_manifest,
    'test_V06_exact_runtime_policy': VerifierRecipe.recipe_V06_exact_runtime_policy,
    'test_V07_supervision_and_logs_required_for_every_cell': VerifierRecipe.recipe_V07_supervision_and_logs_required_for_every_cell,
    'test_V08_parent_totals_errors_inventory': VerifierRecipe.recipe_V08_parent_totals_errors_inventory,
    'test_V09_science_rng_capture_boundary': VerifierRecipe.recipe_V09_science_rng_capture_boundary,
    'test_V10_required_accounting_and_timing': VerifierRecipe.recipe_V10_required_accounting_and_timing,
    'test_V11_joint_threshold_inclusive': VerifierRecipe.recipe_V11_joint_threshold_inclusive,
    'test_V12_each_joint_threshold_failure': VerifierRecipe.recipe_V12_each_joint_threshold_failure,
    'test_V13_revalidate_complete_evidence_binding': VerifierRecipe.recipe_V13_revalidate_complete_evidence_binding,
    'test_V14_external_custody_gate': VerifierRecipe.recipe_V14_external_custody_gate,
    'test_V15_exact_readback_provenance_and_files': VerifierRecipe.recipe_V15_exact_readback_provenance_and_files,
    'test_V16_closing_phase_proof': VerifierRecipe.recipe_V16_closing_phase_proof,
    'test_V17_closing_totals_are_reported': VerifierRecipe.recipe_V17_closing_totals_are_reported,
    'test_V18_matched_clock_error_types': VerifierRecipe.recipe_V18_matched_clock_error_types,
    'test_V19_recovery_loader_runtime_binding': VerifierRecipe.recipe_V19_recovery_loader_runtime_binding,
    'test_V20_supervisor_preservation_boundary_consistency': VerifierRecipe.recipe_V20_supervisor_preservation_boundary_consistency,
    'test_V21_supervisor_partial_spawn_consistency': VerifierRecipe.recipe_V21_supervisor_partial_spawn_consistency,
    'test_V22_recovery_loader_admission_and_helper_pin': VerifierRecipe.recipe_V22_recovery_loader_admission_and_helper_pin,
}


def loader_identity_values(cache):
    executable=cache/'Python/3.11.16/x64/bin/python3.11'
    library=cache/'Python/3.11.16/x64/lib/libpython3.11.so.1.0'
    return {'schema':'worker38-loader-identity-v1','tool_cache':str(cache),
        'executable_path':str(executable),'executable_sha256':sha(b'literal executable bytes\n'),
        'library_relative_path':'Python/3.11.16/x64/lib/libpython3.11.so.1.0','library_path':str(library),
        'library_directory':str(library.parent),'library_sha256':sha(b'literal library bytes\n'),
        'library_size_bytes':22,'library_device':{'major':None,'minor':None},'library_inode':None,
        'mapped_library':{'path':str(library),'device':{'major':None,'minor':None},'inode':None},
        'loader_environment':{'LD_LIBRARY_PATH':str(library.parent)}}


def loader_portable_values(identity):
    return {'schema':'worker38-loader-pin-v1',**{key:identity[key] for key in
        ('executable_sha256','library_relative_path','library_sha256','library_size_bytes')}}


def loader_identity_fields(value,prefix='argument'):
    # Closed scalar field projection, with named dynamic slots already set None.
    # This is a constructor for independently specified values, never callback data.
    keys=('schema','tool_cache','executable_path','executable_sha256','library_relative_path',
        'library_path','library_directory','library_sha256','library_size_bytes','library_device',
        'library_inode','mapped_library','loader_environment','extra')
    if type(value) is str:return {prefix+'.shape':'str',prefix+'.mask':None,prefix+'.value':value}
    result={prefix+'.shape':'dict',prefix+'.mask':sum(1<<i for i,key in enumerate(keys) if key in value)}
    for key in ('schema','tool_cache','executable_path','executable_sha256','library_relative_path',
        'library_path','library_directory','library_sha256','library_size_bytes','library_inode','extra'):
        result[prefix+'.'+key]=value.get(key)
    for group,group_keys in (('library_device',('major','minor')),('mapped_library',('path','device','inode')),
        ('mapped_library.device',('major','minor')),('loader_environment',('LD_LIBRARY_PATH','LD_PRELOAD'))):
        nested=value.get('mapped_library',{}).get('device') if group=='mapped_library.device' else value.get(group)
        result[prefix+'.'+group+'.shape']='dict' if type(nested) is dict else 'absent'
        result[prefix+'.'+group+'.mask']=sum(1<<i for i,key in enumerate(group_keys) if key in nested) if type(nested) is dict else None
        for key in group_keys:
            if key=='device':continue
            result[prefix+'.'+group+'.'+key]=nested.get(key) if type(nested) is dict else None
    return result


def derive_P05(ctx):
    results=[]
    for row in ctx['rows']:
        if 'P05' not in row['family_ids']:continue
        result={'selector':row['selector'],'ordinal':row['ordinal'],'inputs':[],'produced':[],'unresolved':[],'loader_contexts':[]}
        ordinal=row['ordinal']
        contexts=[entry for entry in ctx['loader_fields']['rows'] if entry['ordinal']==ordinal]
        for entry in contexts:
            slot=entry['slot'];group=int(slot[1:3]);index=int(slot[-2:]);paths=entry['file_paths'];root=case_root(ctx,ordinal)
            if slot=='c31-01':
                if ordinal!=179 or entry['boundary']!='clean-without-loader' or paths!=[]:
                    raise ClosurePrerequisite('c31-01 exact zero-path context changed')
                # The omitted loader has scalar context only. No cache, loader
                # identity or real-file anchor is constructed for this event.
                cache=identity=library=None
            else:
                if not paths:raise ClosurePrerequisite('unexpected empty loader path roster '+slot)
                temp=paths[0].split('/')[0];cache=root/temp/'toolcache'
                identity=loader_identity_values(cache);library=PurePosixPath(identity['library_path'])
            dynamic=ctx['loader_dynamic']['fields'][slot]
            values={}
            if group==25:
                values={'variant':entry['boundary'],'cache':str(cache),'executable':identity['executable_path'],'library_environment':str(library.parent)}
                if index==1:values['cache']='relative/cache'
                elif index==2:values['cache']=str(cache)+'/../toolcache'
                elif index==3:values['executable']=str(PurePosixPath(identity['executable_path']).with_name('other-python'))
            elif group==26:
                if index<=5:
                    values={'content_state':'changed' if index==3 else 'fixed'}
                    if index!=1:values['changed']=index in (3,5)
                    if index in (2,3):
                        for prefix in (('initial','observed','returned') if index==3 else ('initial',)):
                            values[prefix+'.container']='tuple'
                            for key in ('dev','ino','mode','size','mtime_ns','ctime_ns','nlink'):values[prefix+'.'+key]=None
                    elif index in (4,5):values.update({'initial.dev':None,'initial.ino':None})
                else:
                    for prefix,raw,size in (('executable',b'literal executable bytes\n',25),('library',b'literal library bytes\n',22),('changed',b'changed literal bytes',22)):
                        values.update({prefix+'.shape':'dict',prefix+'.sha256':sha(raw),prefix+'.size_bytes':size,
                            prefix+'.device.shape':'dict',prefix+'.device.major':None,prefix+'.device.minor':None,
                            prefix+'.inode':None,prefix+'._stat.container':'tuple'})
                        for key in ('dev','ino','mode','size','mtime_ns','ctime_ns','nlink'):values[prefix+'._stat.'+key]=None
            elif group==27:
                values={'maps.container':'tuple' if index==9 else 'single','maps.0':'1000-2000 rw-p 00000000 00:00 0\n' if index==1 else None,
                    'device.major':None,'device.minor':None,'inode':None}
                if index==9:values['maps.1']=None
            elif group==28:
                key,value=(('LD_PRELOAD','/literal.so'),('LD_AUDIT','/literal.so'),('LD_DEBUG','libs'),('LD_UNKNOWN','literal'),
                    ('LD_LIBRARY_PATH',None),('LD_LIBRARY_PATH','/one:/two'),('LD_LIBRARY_PATH','/wrong/library'))[index-1]
                values={'key':key,'present':value is not None,'value':value,'cache':str(cache),
                    'library_environment':value if key=='LD_LIBRARY_PATH' else str(library.parent)}
            elif group==29:
                value=copy.deepcopy(identity) if index==1 else loader_portable_values(identity)
                if index==3:del value['library_sha256']
                elif index==4:value['extra']=1
                elif index==5:value['schema']='other'
                elif index in (6,7,8):value['library_size_bytes']={6:True,7:0,8:-1}[index]
                elif index==9:value['library_sha256']='f'*63
                elif index==10:value['executable_sha256']='0'*64
                elif index==11:value['library_relative_path']='../libpython3.11.so.1.0'
                values=loader_identity_fields(value)
            elif group==30:
                value=copy.deepcopy(identity)
                if index==1:value['extra']=1
                elif index==2:del value['mapped_library']
                elif index==3:value['tool_cache']+='/..'
                elif index==4:value['executable_path']+='-other'
                elif index==5:value['library_path']+='-other'
                elif index==6:value['library_directory']+='-other'
                elif index==7:value['mapped_library']['path']+='-other'
                elif index in (8,9):pass # exact +1 anchored scalar is applied only by the named collector substitution
                elif index==10:value['loader_environment']['LD_PRELOAD']='/literal.so'
                values=loader_identity_fields(value)
            elif group==31:
                values={'dirty.shape':'dict','dirty.mask':63,'local.mode':'IntegrityError' if index==7 else 'function',
                    'local.error':'literal local verification failure' if index==7 else None}
                values.update({'dirty.'+key:value for key,value in (('KEEP','yes'),('LD_LIBRARY_PATH','/wrong'),('LD_AUDIT','/wrong'),
                    ('LD_UNKNOWN','yes'),('PYTHONPATH','/wrong'),('PYTHONUNKNOWN','yes'))})
                if index==1:values['argument.shape']='omitted'
                else:
                    value=loader_portable_values(identity) if index in (3,5) else copy.deepcopy(identity)
                    if index==5:value['library_sha256']='0'*64
                    elif index==6:value='/arbitrary/library'
                    values.update(loader_identity_fields(value))
            elif group==32:
                values={'implementation':'CPython','version':'3.11.16','platform':'linux','gc.enabled':True,
                    'gc.threshold.container':'tuple','gc.threshold.0':700,'gc.threshold.1':10,'gc.threshold.2':10,
                    'timer.container':'tuple','timer.0':0,'timer.1':0,'limits.container':'tuple','limits.0':536870912,'limits.1':536870912,
                    'registered.sha256':identity['library_sha256'],'registered.size':22,
                    'loader.mode':'IntegrityError' if index==2 else 'return','loader.error':'fixed loader verification failure' if index==2 else None,
                    'environment.GITHUB_ACTIONS':'true','environment.GITHUB_REPOSITORY':C_REPOSITORY,'environment.RUNNER_NAME':'bandido-alcatraz-ci',
                    'environment.PYTHONUNEXPECTED':'literal' if index==3 else None,'child':index==1}
                values.update({'flags.'+key:value for key,value in zip(('dont_write_bytecode','no_user_site','ignore_environment','isolated','optimize','no_site'),(1,1,0,0,0,0))})
                values.update({key+'.side_effect':None for key in ('implementation','version','gc.enabled','gc.threshold','timer','limits')})
                values.update(loader_identity_fields(identity,'loader'))
            else:raise ClosurePrerequisite('unlisted loader group')
            schema=entry['field_schema']
            if set(values)!={name for name,_tag in schema}:raise ClosurePrerequisite('loader expected finite field roster '+slot)
            expected=[]
            for name,tag in schema:
                value=values[name]
                if name in dynamic:
                    if value is not None:raise ClosurePrerequisite('dynamic placeholder must be explicit null '+slot+':'+name)
                elif {'null':type(None),'str':str,'int':int,'bool':bool}[tag] is not type(value):
                    raise ClosurePrerequisite('loader expected exact scalar tag '+slot+':'+name)
                expected.append([name,tag,value])
            if len(canonical(expected))>8192:raise ClosurePrerequisite('loader canonical context exceeds8KiB')
            descriptor={'slot':slot,'expected_context':expected,'context_dynamic_fields':dynamic,
                'source_sha256':ctx['recipe_sha256'],'field_schema_sha256':digest(schema)}
            path_rules=[]
            for relative in paths:
                path=PurePosixPath(relative);kind='file'
                if path.name in ('python3.11','other-python'):raw=b'literal executable bytes\n'
                elif path.name=='literal-library':raw=b'other literal file' if slot=='c26-03' else b'fixed literal file'
                else:raw=b'literal library bytes\n'
                if slot=='c25-04' and path.name=='libpython3.11.so.1.0':kind='symlink';raw=str((root/path).with_name('target')).encode('ascii')
                elif slot=='c25-05':
                    if path.name=='lib':kind='symlink';raw=str((root/path).with_name('other-lib')).encode('ascii')
                    elif path.parent.name=='lib':kind='blocked_ancestor';raw=None
                elif slot=='c25-06' and path.name=='libpython3.11.so.1.0':kind='missing';raw=None
                elif slot=='c25-07' and path.name=='libpython3.11.so.1.0':kind='directory';raw=None
                path_rules.append({'rule_id':'input:'+relative,'relative_path':relative,'allowed_state':{'type':kind,
                    'size_bytes':len(raw) if raw is not None else 0,'sha256':sha(raw) if raw is not None else None,
                    'lineage':'independent_input','independent_recipe_sha256':digest(descriptor),'materialized':True}})
            result['loader_contexts'].append({'boundary':entry['boundary'],'call_ordinal':index,'slot':slot,
                'path_rules':path_rules,'record_byte_cap':16384,'context_recipe_sha256':digest(descriptor),
                'context_materialized':True,'expected_context':expected,'context_dynamic_fields':dynamic})
        if ordinal==168:
            root=case_root(ctx,ordinal)/'t01'
            result['inputs'].append({'relative_path':'t01/journal','kind':'file',
                'raw':(str(root)+' {"timing":7,"untouched":"a"}\n').encode('utf-8'),
                'lineage':'independent_literal_input','recipe':'core20 source149-151: absolute root + fixed text + LF'})
        if ordinal==172:
            for relative,raw in (('t02/toolcache/Python/3.11.16/x64/bin/python3.11',b'literal executable bytes\n'),
                ('t02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0',b'literal library bytes\n')):
                result['inputs'].append({'relative_path':relative,'kind':'file','raw':raw,
                    'lineage':'independent_literal_input','recipe':'core24 second temporary root: exact literal_loader source bytes'})
        results.append(result)
    return {'family_id':'P05','selector_results':results}

T_MANIFEST_SCHEMA='worker38.transport.v1'
T_RAW_CAP=67108864
T_ARCHIVE_CAP=67108864
T_PART_CAP=31457280
T_PROVIDER_WRAPPER_LIMIT=33554432

class TransportLiteralRecipe:
    def __init__(self,ctx,row):
        self.row=row;self.base=case_root(ctx,row['ordinal'])/'t01'
        self.counter=0;self.files={};self.links={};self.versions=[];self.stages=[]

    def fresh(self,stem):
        self.counter+=1
        return self.base/(stem+'-'+str(self.counter))

    def raw_zip(self,members,mode=None):
        return fixed_stored_zip(members,negative=True,mode=0o100600 if mode is None else mode)

    def put_raw(self,path,raw):
        key=str(path);raw=bytes(raw)
        if key in self.files:self.versions.append({'relative_path':str(PurePosixPath(key).relative_to(self.base.parent)),
            'raw':self.files[key],'kind':'file','lineage':'independent_literal_input','recipe':'exact ordered pre-overwrite literal state'})
        self.files[key]=raw

    def raw(self,path):return self.files[str(path)]

    def remove(self,path):del self.files[str(path)]

    def link(self,path,target):self.links[str(path)]=str(target).encode('ascii')

    def classification_wrapper_check(self,parts,descriptors):
        # Named input-stage retention only; no validator or output oracle.
        self.stages.append({'ordinal':len(self.stages)+1,'parts':copy.deepcopy(parts),
            'descriptors':copy.deepcopy(descriptors),'manifest':copy.deepcopy(self.classification_manifest),
            'files':[{ 'relative_path':str(PurePosixPath(p).relative_to(self.base.parent)),
                'raw':raw,'kind':'file','lineage':'independent_literal_input','recipe':'closed literal wrapper stage'} for p,raw in sorted(self.files.items())],
            'links':[{ 'relative_path':str(PurePosixPath(p).relative_to(self.base.parent)),
                'raw':raw,'kind':'symlink','lineage':'independent_literal_input','recipe':'exact absolute link target'} for p,raw in sorted(self.links.items())]})
        return None


    def classification_wrappers(self, payloads=(b'literal first transport payload',)):
        """Literal wrapper-boundary data, not an underfilled production archive."""
        parts = [{'order': order, 'path': f'part-{order:03d}.bin', 'size': len(payload), 'sha256': sha(payload)} for order, payload in enumerate(payloads, 1)]
        self.classification_manifest = {'schema': T_MANIFEST_SCHEMA, 'raw_size': 0, 'files': [], 'archive': {'path': 'attempt.zip', 'format': 'zip-stored-v1', 'size': sum((len(value) for value in payloads)), 'sha256': sha(b''.join(payloads))}, 'parts': parts, 'limits': {'raw_bytes': T_RAW_CAP, 'archive_bytes': T_ARCHIVE_CAP, 'part_bytes': T_PART_CAP, 'provider_zip_strictly_below_bytes': T_PROVIDER_WRAPPER_LIMIT}}
        manifest_raw = canonical(self.classification_manifest)
        descriptors = []
        for order, (payload, part) in enumerate(zip(payloads, parts), 1):
            name = part['path']
            path = self.fresh('literal-github-download.zip')
            members = [(name, payload)] + ([('transport-manifest.json', manifest_raw)] if order == 1 else [])
            self.put_raw(path, self.raw_zip(members))
            wrapper = self.raw(path)
            receipt = {'provider': 'github_actions', 'operation': 'download', 'repository': 'carabinshely/bandido-alcatraz-solve', 'run_id': '123', 'run_attempt': '1', 'artifact_id': str(1000 + order), 'artifact_name': f'worker38-123-1-part-{order:03d}', 'event_id': f'literal-provider-download-{order}', 'completed_at': '2026-10-04T00:00:00Z', 'size': len(wrapper), 'sha256': sha(wrapper)}
            descriptors.append({'order': order, 'part_path': name, 'member_name': name, 'path': str(path), 'size': len(wrapper), 'sha256': sha(wrapper), 'download_receipt': receipt})
        return (parts, descriptors)

    def repin_literal_wrapper(self, descriptor, raw):
        self.put_raw(PurePosixPath(descriptor['path']), raw)
        descriptor.update(size=len(raw), sha256=sha(raw))
        descriptor['download_receipt'].update(size=len(raw), sha256=sha(raw))

    def recipe_PW03_mandatory_exact_ordered_wrapper_coverage(self):
        parts, descriptors = self.classification_wrappers((b'first', b'second'))
        variants = (None, [], descriptors[:1], descriptors + [copy.deepcopy(descriptors[0])], [descriptors[0], copy.deepcopy(descriptors[0])], list(reversed(descriptors)))
        for index, altered in enumerate(variants):
            self.classification_wrapper_check(parts, altered)
        unknown = copy.deepcopy(descriptors)
        unknown[1]['part_path'] = 'part-003.bin'
        self.classification_wrapper_check(parts, unknown)

    def recipe_PW04_one_actual_part_needs_one_actual_wrapper(self):
        parts, descriptors = self.classification_wrappers()
        checked = self.classification_wrapper_check(parts, descriptors)
        manifest_raw = canonical(self.classification_manifest)

    def recipe_PW05_actual_wrapper_bytes_must_match_both_pins(self):
        for fault in ('size', 'sha256', 'changed-bytes'):
            parts, descriptors = self.classification_wrappers()
            if fault == 'size':
                descriptors[0]['size'] += 1
            elif fault == 'sha256':
                descriptors[0]['sha256'] = 'f' * 64
            else:
                path = PurePosixPath(descriptors[0]['path'])
                self.put_raw(path, self.raw(path) + b'changed')
            self.classification_wrapper_check(parts, descriptors)

    def recipe_PW06_strict_provider_zip_limit_uses_actual_size(self):
        parts, descriptors = self.classification_wrappers()
        self.classification_wrapper_check(parts, descriptors)
        for size in (T_PROVIDER_WRAPPER_LIMIT, T_PROVIDER_WRAPPER_LIMIT + 1):
            self.classification_wrapper_check(parts, descriptors)
        raw = bytearray(self.raw(PurePosixPath(descriptors[0]['path'])))
        first = raw.index(b'PK\x01\x02')
        second = raw.index(b'PK\x01\x02', first + 4)
        struct.pack_into('<I', raw, second + 24, 1048577)
        self.repin_literal_wrapper(descriptors[0], raw)
        self.classification_wrapper_check(parts, descriptors)

    def recipe_PW07_exact_member_name_size_and_payload(self):
        payload = b'fixed payload'
        for fault in ('name', 'declared-size', 'payload-size', 'payload-hash'):
            parts, descriptors = self.classification_wrappers((payload,))
            name = 'renamed.bin' if fault == 'name' else parts[0]['path']
            altered = payload + b'x' if fault == 'payload-size' else payload
            if fault == 'payload-hash':
                altered = b'X' + payload[1:]
            raw = bytearray(self.raw_zip([(name, altered), ('transport-manifest.json', canonical(self.classification_manifest))]))
            if fault == 'declared-size':
                central = raw.index(b'PK\x01\x02')
                struct.pack_into('<I', raw, central + 24, len(payload) + 1)
            self.repin_literal_wrapper(descriptors[0], raw)
            if fault == 'name':
                descriptors[0]['member_name'] = name
            self.classification_wrapper_check(parts, descriptors)
        for label in ('manifest_ordered_part_binding', 'manifest_archive_inventory_binding'):
            parts, descriptors = self.classification_wrappers((b'fixed payload',))
            changed = copy.deepcopy(self.classification_manifest)
            if label == 'manifest_ordered_part_binding':
                changed['parts'][0]['sha256'] = 'f' * 64
                expected_error = 'ordered part binding'
            else:
                changed['archive']['sha256'] = 'f' * 64
                changed['files'] = [{'path': 'invented-extra.bin', 'size': 1, 'sha256': sha(b'x')}]
                changed['raw_size'] = 1
                expected_error = 'archive inventory binding'
            raw = self.raw_zip([('part-001.bin', b'fixed payload'), ('transport-manifest.json', canonical(changed))])
            self.repin_literal_wrapper(descriptors[0], raw)
            self.classification_wrapper_check(parts, descriptors)

    def recipe_PW08_extra_or_duplicate_wrapper_members_reject(self):
        for second_name in ('unexpected.bin', 'part-001.bin'):
            parts, descriptors = self.classification_wrappers((b'first',))
            raw = self.raw_zip([('part-001.bin', b'first'), ('transport-manifest.json', canonical(self.classification_manifest)), (second_name, b'second')])
            self.repin_literal_wrapper(descriptors[0], raw)
            self.classification_wrapper_check(parts, descriptors)
        for label in ('first_missing_manifest', 'first_duplicate_manifest', 'later_extra_manifest'):
            parts, descriptors = self.classification_wrappers((b'first', b'second'))
            manifest_raw = canonical(self.classification_manifest)
            if label == 'first_missing_manifest':
                index, members = (0, [('part-001.bin', b'first')])
            elif label == 'first_duplicate_manifest':
                index, members = (0, [('part-001.bin', b'first'), ('transport-manifest.json', manifest_raw), ('transport-manifest.json', manifest_raw)])
            else:
                index, members = (1, [('part-002.bin', b'second'), ('transport-manifest.json', manifest_raw)])
            raw = self.raw_zip(members)
            self.repin_literal_wrapper(descriptors[index], raw)
            self.classification_wrapper_check(parts, descriptors)

    def recipe_PW09_provider_identity_binds_verified_attempt(self):
        cases = (('provider', 'other-provider'), ('operation', 'upload'), ('repository', 'other/repository'), ('run_id', '124'), ('run_attempt', '2'), ('artifact_name', 'worker38-123-1-part-002'), ('artifact_id', ''), ('event_id', ''), ('artifact_id', None), ('event_id', None))
        for key, value in cases:
            parts, descriptors = self.classification_wrappers()
            if value is None:
                del descriptors[0]['download_receipt'][key]
            else:
                descriptors[0]['download_receipt'][key] = value
            self.classification_wrapper_check(parts, descriptors)

    def recipe_PW10_unique_artifact_and_download_event_per_part(self):
        for field in ('artifact_id', 'event_id'):
            parts, descriptors = self.classification_wrappers((b'first', b'second'))
            descriptors[1]['download_receipt'][field] = descriptors[0]['download_receipt'][field]
            self.classification_wrapper_check(parts, descriptors)

    def recipe_PW11_actual_retained_file_required_not_verified_flags(self):
        for fault in ('flag-only', 'missing-path', 'missing-file', 'unreadable-file', 'symlink'):
            parts, descriptors = self.classification_wrappers()
            if fault == 'flag-only':
                descriptors = [{'verified': True}]
            elif fault == 'missing-path':
                descriptors[0].pop('path')
                descriptors[0]['verified'] = True
            elif fault == 'missing-file':
                self.remove(PurePosixPath(descriptors[0]['path']))
            elif fault == 'symlink':
                link = self.fresh('wrapper-link')
                self.link(link, descriptors[0]['path'])
                descriptors[0]['path'] = str(link)
            if fault == 'unreadable-file':
                self.classification_wrapper_check(parts, descriptors)
            else:
                self.classification_wrapper_check(parts, descriptors)

    def recipe_PW12_original_archive_or_raw_part_is_not_outer_wrapper(self):
        for wrong_layer in (self.raw_zip([('receipt.json', b'{}')]), b'a raw split payload'):
            parts, descriptors = self.classification_wrappers()
            self.repin_literal_wrapper(descriptors[0], wrong_layer)
            self.classification_wrapper_check(parts, descriptors)

    def recipe_PW16_local_checks_never_authenticate_provider_origin(self):
        parts, descriptors = self.classification_wrappers()
        checked = self.classification_wrapper_check(parts, descriptors)

TRANSPORT_LITERAL_RECIPES = {
    'test_PW03_mandatory_exact_ordered_wrapper_coverage': TransportLiteralRecipe.recipe_PW03_mandatory_exact_ordered_wrapper_coverage,
    'test_PW04_one_actual_part_needs_one_actual_wrapper': TransportLiteralRecipe.recipe_PW04_one_actual_part_needs_one_actual_wrapper,
    'test_PW05_actual_wrapper_bytes_must_match_both_pins': TransportLiteralRecipe.recipe_PW05_actual_wrapper_bytes_must_match_both_pins,
    'test_PW06_strict_provider_zip_limit_uses_actual_size': TransportLiteralRecipe.recipe_PW06_strict_provider_zip_limit_uses_actual_size,
    'test_PW07_exact_member_name_size_and_payload': TransportLiteralRecipe.recipe_PW07_exact_member_name_size_and_payload,
    'test_PW08_extra_or_duplicate_wrapper_members_reject': TransportLiteralRecipe.recipe_PW08_extra_or_duplicate_wrapper_members_reject,
    'test_PW09_provider_identity_binds_verified_attempt': TransportLiteralRecipe.recipe_PW09_provider_identity_binds_verified_attempt,
    'test_PW10_unique_artifact_and_download_event_per_part': TransportLiteralRecipe.recipe_PW10_unique_artifact_and_download_event_per_part,
    'test_PW11_actual_retained_file_required_not_verified_flags': TransportLiteralRecipe.recipe_PW11_actual_retained_file_required_not_verified_flags,
    'test_PW12_original_archive_or_raw_part_is_not_outer_wrapper': TransportLiteralRecipe.recipe_PW12_original_archive_or_raw_part_is_not_outer_wrapper,
    'test_PW16_local_checks_never_authenticate_provider_origin': TransportLiteralRecipe.recipe_PW16_local_checks_never_authenticate_provider_origin,
}


_P01_P07_SHARED_SELECTORS = {207: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D04_torn_records_terminalize', 209: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D06_marker_entry_bounds', 210: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D07_integrity_survives_later_receipt_failure', 214: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D11_actual_test_receipt_and_checked_bytes', 215: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D12_offline_memory_cap_exact', 220: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D17_read_io_is_gap', 221: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D18_stat_io_is_gap', 222: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D19_later_child_preflight_is_incomplete', 225: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D22_surviving_parent_and_supervisor_integrity', 226: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D23_main_receipt_io_uses_sidecar', 227: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D24_reducer_resource_and_uncertainty', 230: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D27_malformed_retained_matrix', 232: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D29_torn_staging_is_uncertainty', 233: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D30_unavailable_types_preserved', 234: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D31_malformed_failure_fields', 235: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D32_recorded_unavailable_failure_stays_terminal', 236: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D33_malformed_direct_causes_do_not_escape', 244: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D41_offline_resource_types', 245: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D42_gap_without_primary_stops', 246: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_D43_terminal_memory_classification', 259: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_R1D02_paired_handoff_clock_order_and_floor', 261: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_R1D04_invalid_incoming_handoff_stops_bulk_work', 270: 'tests/test_worker38_driver_integration.py:DriverIntegration.test_R1D13_offline_restoration_only_sidecar_preserves_in_memory_integrity'}
_P01_P07_INITIAL_PATHS = (
    't01/experiment/source-manifest.json','t01/stub-test-receipt.json',
    't01/auth/admission.json','t01/auth/provenance.json',
    't01/auth/pull-request.json','t01/auth/postmerge-ci.json','t01/auth/current-source-ci.json',
    't01/auth/review-exhaustive.json','t01/auth/review-adversarial.json',
    't01/auth/preregistration.json','t01/auth/diagnostic-commit.json')


def p01_p07_initial_rule_join(ctx,row,old):
    if row['ordinal'] not in _P01_P07_SHARED_SELECTORS:return None
    if row['selector']!=_P01_P07_SHARED_SELECTORS[row['ordinal']] or 'P07' not in row['family_ids']:
        raise ClosurePrerequisite('named P01/P07 shared setup selector drift')
    rules=old['input_rules']
    if len(rules)!=11 or {rule.get('pattern') for rule in rules}!=set(_P01_P07_INITIAL_PATHS):
        raise ClosurePrerequisite('exact eleven Driver initial rules changed')
    # P07 owns these source-derived setup bytes. The missing relative_path in
    # the old map is accepted only for this exact named23-by11 source join.
    files=p07_initial_files(ctx)
    if {'t01/'+name for name in files}!=set(_P01_P07_INITIAL_PATHS):
        raise ClosurePrerequisite('P07 initial constructor path roster changed')
    result={}
    source_sha256=sha(ctx['source_bytes']['tests/test_worker38_driver_integration.py'])
    for rule in rules:
        if set(rule)!={'pattern','expected_type','maximum_bytes','allowed_sha256'}:
            raise ClosurePrerequisite('named Driver predecessor rule schema changed')
        path=rule['pattern'];raw=files[path.removeprefix('t01/')]
        if (rule['expected_type']!='file' or type(rule['maximum_bytes']) is not int or
                rule['maximum_bytes']!=len(raw) or rule['allowed_sha256']!=[sha(raw)]):
            raise ClosurePrerequisite('independent P07 bytes disagree with exact predecessor rule '+path)
        binding={'owner':'P07.p07_initial_files','recipe_source_sha256':ctx['recipe_sha256'],
            'source_path':'tests/test_worker38_driver_integration.py','source_sha256':source_sha256,
            'selector':row['selector'],'relative_path':path,'operation':'DriverIntegration.setUp original initial file'}
        result[path]={'relative_path':path,'kind':'file','raw':raw,'lineage':'independent_literal_input',
            'recipe':'P01 exact shared obligation resolved by P07 source constructor; final cross-family equality required',
            'shared_recipe_owner':'P07.p07_initial_files','source_provenance':binding,
            'independent_recipe_sha256':digest(binding)}
    return result


def derive_P01(ctx):
    """Direct byte/source-copy lineage from fixed saved rules and source spans.

    A direct literal catalogue is not an AST evaluator. Only Constant strings and
    bytes are eligible; arbitrary expression or helper results never qualify.
    Each prospective input is rederived from source and prior pins are crosschecks.
    """
    catalogue={}
    for path,raw in ctx['source_bytes'].items():
        catalogue.setdefault(sha(raw),[]).append((raw,{'source_path':path,'operation':'complete-source-byte-copy'}))
        if not path.endswith('.py'):continue
        for node in ast.walk(ast.parse(raw,filename=path)):
            if isinstance(node,ast.Constant) and type(node.value) in (bytes,str):
                value=node.value if type(node.value) is bytes else node.value.encode('utf-8')
                catalogue.setdefault(sha(value),[]).append((value,{'source_path':path,'first_line':node.lineno,
                    'last_line':node.end_lineno,'operation':'direct bytes literal' if type(node.value) is bytes else 'direct string literal UTF-8'}))
    results=[]
    for row in ctx['rows']:
        if 'P01' not in row['family_ids']:continue
        old=ctx['fixed_map']['cases'][row['ordinal']-1]
        if old['selector']!=row['selector']:raise ClosurePrerequisite('P01 original row order changed')
        result={'selector':row['selector'],'ordinal':row['ordinal'],'inputs':[],'produced':[],'unresolved':[]}
        shared_initial=p01_p07_initial_rule_join(ctx,row,old)
        for rule in old['input_rules']:
            if shared_initial is not None:
                result['inputs'].append(shared_initial[rule['pattern']])
                continue
            path=rule.get('relative_path');recipe=rule.get('recipe_id','')
            if not path or path!=rule.get('pattern'):result['unresolved'].append('P01 non-exact direct input rule '+repr(rule.get('pattern')));continue
            if recipe.startswith('copy:'):
                source=recipe[5:]
                if source not in ctx['source_bytes']:raise ClosurePrerequisite('missing named source copy '+source)
                raw=ctx['source_bytes'][source];origin={'source_path':source,'operation':'complete final source bytes'}
            elif recipe.rsplit(':',1)[-1]=='S09-symlink-target':
                raw=str(case_root(ctx,9)/'t01'/'actual').encode('ascii');origin={'operation':'exact batch04/c0009/t01/actual link target'}
            elif recipe.rsplit(':',1)[-1]=='consumed-reservation':
                raw=(b'schema=worker38-observed-reservation-v1\nallocation_id=worker38-synthetic-profile-01\nrun_id=501\nrun_attempt=1\nobserved_head='+b'1'*40+b'\ndescriptor_binding=not_yet_validated\nevaluator_starts=0\nscientific_classification=null\n')
                origin={'source_path':'tests/test_worker38_bootstrap_integration.py','operation':'pipeline fixed reservation ASCII recipe'}
            elif row['ordinal']==165 and recipe=='unadmitted-go':
                if (row['selector']!='tests/test_worker38_core.py:CoreTests.test_17_missing_admission_blocked' or
                        path!='t01/go.json' or rule['expected_type']!='file'):
                    raise ClosurePrerequisite('Core17 exact false-admission input rule changed')
                raw=canonical({'admitted':False})
                if rule['maximum_bytes']!=len(raw) or rule['allowed_sha256']!=[sha(raw)]:
                    raise ClosurePrerequisite('Core17 independent canonical bytes disagree with predecessor pin')
                origin={'source_path':'tests/test_worker38_core.py',
                    'source_sha256':sha(ctx['source_bytes']['tests/test_worker38_core.py']),
                    'method':'CoreTests.test_17_missing_admission_blocked',
                    'operation':'canonical serialization of exact source dictionary admitted=False'}
            else:
                pins=rule.get('allowed_sha256',[])
                if len(pins)!=1 or pins[0] not in catalogue:
                    result['unresolved'].append('P01 source-literal/copy expression not yet closed: '+path+' recipe='+recipe);continue
                options=catalogue[pins[0]]
                if any(value!=options[0][0] for value,_ in options):raise ClosurePrerequisite('source literal digest ambiguity')
                raw,origin=options[0]
            result['inputs'].append({'relative_path':path,'kind':rule['expected_type'],'raw':raw,
                'lineage':'independent_literal_input','recipe':recipe,'source_provenance':origin})
        result['scope']='Existing exact direct-literal/source-copy input rules only; constructed family joins are separate obligations'
        results.append(result)
    return {'family_id':'P01','selector_results':results}


def derive_P03(ctx):
    return {'family_id':'P03','constructor':'independent_auth_bundle + independent_auth_proof',
        'operation_order':['default-preserving descriptor merge','focused receipt dictionary','two review body envelopes',
            'preregistration body','descriptor body envelope','event/context/seven ordered responses','independent admission proof dictionary'],
        'input_names':list(A_INPUT_NAMES),'candidate_validator_calls':0,
        'selector_results':[{'selector':r['selector'],'ordinal':r['ordinal'],'inputs':[],'produced':[],
            'unresolved':[],'join':'P08 for verifier, P04/P07 exact per-selector constructors for startup/driver'}
            for r in ctx['rows'] if 'P03' in r['family_ids']]}


def derive_verifier_states(ctx):
    results=[]
    for row in ctx['rows']:
        if row['source_path']!='tests/test_worker38_verify_integration.py':continue
        recipe=VerifierRecipe(ctx,row)
        baseline_inventory=recipe.literal_inventory()
        baseline_paths=recipe.expected_baseline_paths()
        if {x['path'] for x in baseline_inventory}!=baseline_paths:
            raise ClosurePrerequisite('full verifier exact357 untouched baseline missing')
        baseline_assets=recipe.export_asset_states()
        expected_assets={str((recipe.root/path).relative_to(recipe.case)) for path in baseline_paths}
        external_names=('event.json','request-context.json',*A_INPUT_NAMES,'admission.json','provenance.json')
        expected_assets.update(str((recipe.auth/name).relative_to(recipe.case)) for name in external_names)
        if (len(external_names)!=11 or len(baseline_assets)!=368 or
                {state['relative_path'] for state in baseline_assets}!=expected_assets or
                any(state['type']!='file' or state['lineage']!='independent_input' for state in baseline_assets)):
            raise ClosurePrerequisite('complete baseline357 plus external-auth11 export roster mismatch')
        baseline_operation_count=len(recipe.operations)
        recipe.configure_exact_branches()
        method=row['selector'].rsplit('.',1)[-1]
        if method not in VERIFIER_RECIPES:raise ClosurePrerequisite('no fixed verifier mutation program')
        VERIFIER_RECIPES[method](recipe)
        if len(recipe.events)!=len(recipe.expected):raise ClosurePrerequisite('verifier event sequence incomplete '+method)
        labels=V_CUSTODY_VERSION_LABELS.get(method,())
        if tuple(v['label'] for v in recipe.versions)!=labels:raise ClosurePrerequisite('custody22 ordered version roster drift '+method)
        final_assets=recipe.export_asset_states()
        ordered_assets=copy.deepcopy(recipe.operations)
        if [state['source_recipe_binding']['operation_ordinal'] for state in ordered_assets]!=list(range(1,len(recipe.operations)+1)):
            raise ClosurePrerequisite('ordered verifier asset export lost a write/remove step')
        for state in ordered_assets:
            state['recipe_phase']=('baseline_construction' if state['source_recipe_binding']['operation_ordinal']<=baseline_operation_count else 'method_operations')
        results.append({'selector':row['selector'],'ordinal':row['ordinal'],'inputs':baseline_assets,
            'baseline_raw_asset_count':357,'baseline_external_auth_asset_count':11,
            'baseline_operation_count':baseline_operation_count,'final_operation_count':len(recipe.operations),
            'ordered_literal_asset_states':[state for state in ordered_assets if state['lineage']=='independent_input'],
            'final_literal_asset_states':[state for state in final_assets if state['lineage']=='independent_input'],
            'custody_input_generations':copy.deepcopy(recipe.custody_input_versions),
            'events':recipe.events,'versions':copy.deepcopy(recipe.versions),'branches':recipe.branches,
            'untouched_baseline_paths':sorted(baseline_paths),
            'produced':[state for state in final_assets if state['lineage']=='produced_output'],
            'ordered_produced_custody_states':[state for state in ordered_assets if state['lineage']=='produced_output'],
            'asset_states_are_not_selected_witness_alternatives':True,'unresolved':[],
            'mutations_and_refreshes':'Direct fixed method source transcriptions retain cumulative edits and finally restorations'})
    if len(results)!=43:raise ClosurePrerequisite('exact43 verifier selector gate changed')
    return results


def derive_P08(ctx):
    return {'family_id':'P08','selector_results':ctx['verifier_results'],'baseline_file_count':357}

def derive_P09(ctx):
    return {'family_id':'P09','selector_results':ctx['verifier_results'],'branch_policy':'actual independent SHA256 comparisons only'}

def derive_P10(ctx):
    return {'family_id':'P10','selector_results':ctx['verifier_results'],
        'negative_state_policy':'raw malformed bytes never normalized; missing=zero/null; no link traversal; original node granularity'}

def derive_P11(ctx):
    return {'family_id':'P11','selector_results':ctx['verifier_results'],'zip_recipe':'fixed_stored_zip; one version except V12 two'}

def derive_P12(ctx):
    return {'family_id':'P12','selector_results':ctx['verifier_results'],'custody_lineage':'produced_output','ordered_preserved_versions':22}


def derive_P13(ctx):
    results=[]
    for row in ctx['rows']:
        if 'P13' not in row['family_ids']:continue
        method=row['selector'].rsplit('.',1)[-1]
        result={'selector':row['selector'],'ordinal':row['ordinal'],'inputs':[],'produced':[],'unresolved':[]}
        if method in TRANSPORT_LITERAL_RECIPES:
            plan=TransportLiteralRecipe(ctx,row);TRANSPORT_LITERAL_RECIPES[method](plan)
            result['stages']=plan.stages;result['versions']=plan.versions
        else:
            result['produced'].append({'role':'actual package/custody/downloads and timestamped provider wrappers',
                'lineage':'produced_output','input_role':'consumed by transport verification',
                'exact_expected_hash':None,'raw_versions_required':True,'partial_bytes_charged':True,
                'source_lineage':'package/wrappers/custody_mapping; final T11/T12/T15 capture proof',
                'no_expected_hash_fallback':True})
            if method=='test_T09_zip_attacks':
                plan=TransportLiteralRecipe(ctx,row)
                raw=plan.raw_zip([('a',b'x')]);central=raw.index(b'PK\x01\x02')
                encrypted=bytearray(raw);struct.pack_into('<H',encrypted,central+8,1)
                bomb=bytearray(raw);struct.pack_into('<I',bomb,central+24,67108865)
                corrupted=bytearray(raw);corrupted[31]^=1
                variants=(('traversal',plan.raw_zip([('../escape',b'x')])),('absolute',plan.raw_zip([('/escape',b'x')])),
                    ('backslash',plan.raw_zip([('bad\\name',b'x')])),('duplicate',plan.raw_zip([('a',b'x'),('a',b'x')])),
                    ('symlink',plan.raw_zip([('a',b'x')],mode=0o120777)),('special',plan.raw_zip([('a',b'x')],mode=0o010600)),
                    ('encrypted',bytes(encrypted)),('bomb',bytes(bomb)),('corrupt-data',bytes(corrupted)),('inventory',plan.raw_zip([('unexpected',b'x')])))
                for index,(name,raw) in enumerate(variants):
                    result['inputs'].append({'relative_path':'t01/invented-malicious-part-'+str(2*index+1),'kind':'file',
                        'raw':raw,'lineage':'independent_literal_input','recipe':'T09 '+name+' exact member/header mutation in original order'})
            else:
                direct,produced=transport_direct_setup(ctx,row)
                result['inputs'].extend(direct);result['produced'].extend(produced)
        results.append(result)
    return {'family_id':'P13','selector_results':results}


def derive_P15(ctx):
    # The parent-owned environment deriver remains an independently reviewed input;
    # this family cannot promote its prior first33 observation into a397 certificate.
    return {'family_id':'P15','selector_results':[{'selector':r['selector'],'ordinal':r['ordinal'],
        'inputs':[],'produced':[],'unresolved':['P15 final source/native namespace and all397 dependency closure must be independently materialized and rebound; predecessor observations are not final'],
        'namespace':ctx['namespace']} for r in ctx['rows'] if 'P15' in r['family_ids']]}


# Independently authored fixed family fragment, original SHA256 6dc92239e5184800e54d77de3ff8638126155c85292fd8f2f8b661e31c0509ca
# SOURCE TEXT ONLY. Do not execute, import, compile, or dynamically load.
# Intended for explicit human-inspected inlining into the sole authorized deriver.
# Shared names: canonical, sha, source_literal, case_root; stdlib base64/json.

def derive_P02(ctx):
    path = 'tests/test_worker37_bootstrap.py'
    python_cases = (1,17,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,
        39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,
        61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84)
    bash_cases = (2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,18,38)
    results = []
    for row in ctx['rows']:
        if 'P02' not in row['family_ids']:
            continue
        number = int(row['selector'].split('.test_T', 1)[1][:3])
        result = {'selector':row['selector'], 'ordinal':row['ordinal'],
            'inputs':[], 'produced':[], 'unresolved':[]}
        if number in python_cases:
            descriptor = source_literal(ctx, path, 'FROZEN_DESCRIPTOR')
            recipe = ['AST literal FROZEN_DESCRIPTOR; independent mutable copy',
                'LiteralScenario.inputs builds event snapshot before response-only PR overrides']
            if number == 26:
                descriptor['historical_fixture']['artifact_id'] = True
                recipe.append('artifact_id=True; retain JSON boolean type')
            elif number == 27:
                descriptor['fetch_url'] = 'https://other.example.invalid/steal'
                recipe.append('add exact fetch_url')
            elif number in (53,54,55,56):
                zip_bytes = base64.b64decode(source_literal(ctx, path, 'FROZEN_ZIPS')['T%03d' % number], validate=True)
                descriptor['historical_fixture']['zip_sha256'] = sha(zip_bytes)
                descriptor['historical_fixture']['zip_size_bytes'] = len(zip_bytes)
                recipe.append('base64-decode named FROZEN_ZIPS literal and change only zip_sha256/zip_size_bytes')
            elif number == 82:
                descriptor['historical_fixture']['pr_number'] = 41
                recipe.append('historical_fixture.pr_number=41; prior frozen-pin copy is not event content')
            descriptor_raw = canonical(descriptor).rstrip(b'\n')
            body = ('WORKER37_ENGINEERING_ADMISSION_JSON\n' + descriptor_raw.decode('utf-8') +
                '\nEND_WORKER37_ENGINEERING_ADMISSION_JSON\nWORKER37_ENGINEERING_ADMISSION_SHA256 ' + sha(descriptor_raw))
            repository = 'carabinshely/bandido-alcatraz-solve'
            pr = {'number':101,'state':'open','merged':False,'user':{'login':'carabinshely'},
                'head':{'sha':'1'*40,'ref':'research/worker37-bootstrap-readiness','repo':{'full_name':repository}},
                'base':{'sha':'5'*40,'ref':'main','repo':{'full_name':repository}},'body':body}
            event = {'action':'edited','number':101,'repository':{'full_name':repository},
                'sender':{'login':'carabinshely'},'changes':{'body':{'from':'Prior ordinary body'}},'pull_request':pr}
            result['inputs'].append({'relative_path':'t01/output/event.json','kind':'file','raw':canonical(event),
                'lineage':'independent_literal_input','recipe':'; '.join(recipe)})
        elif number in bash_cases:
            result['inputs'].append({'relative_path':'t01/event.json','kind':'file','raw':b'{}\n',
                'lineage':'independent_literal_input','recipe':'run_bash exact event literal'})
            if number == 8:
                target = str(case_root(ctx,row['ordinal']) / 't01' / 'cache-target')
                result['inputs'].append({'relative_path':'t01/cache','kind':'symlink','raw':target.encode('utf-8'),
                    'lineage':'independent_literal_input','recipe':'run_bash T008: absolute cache-target under frozen cNNNN/t01; do not follow link'})
        elif number == 60:
            result['family_scope'] = 'Source-only AST/text assertions; no case-created event input'
        else:
            raise ValueError('P02 selector outside closed 84-case roster')
        result['other_families'] = ['P01: exact shared source copies and direct literal setup','P15: native/source namespace bindings']
        results.append(result)
    if len(results) != 84:
        raise ValueError('P02 exact roster count changed')
    return {'family_id':'P02','selector_results':results}


def derive_P06(ctx):
    # These finite tables encode the actual prepare invocations, not observed files.
    prepared = {
        1:[('attempt',2)],2:[('attempt',1)],3:[('attempt',2)],7:[('attempt',2)],
        9:[('runtime',2),('imports',2)],10:[('attempt',2)],11:[('attempt',2)],
        12:[('attempt',2)],13:[('attempt',2)],14:[('attempt',2)],
        15:[('ITIMER_REAL',2),('ITIMER_PROF',2)],19:[('attempt',2)],
        20:[('resource_then_io',2),('io_then_resource',2),('integrity_then_resource',2)],
        21:[('attempt',2)],
        22:[('missing_pin',2),('bad_pin',2),('missing_observation',2),('library_hash',2),('library_size',2)]}
    no_prepare = (4,5,6,8,16,17,18)
    runtime = source_literal(ctx,'scripts/worker38/common.py','RUNTIME')
    results = []
    for row in ctx['rows']:
        if 'P06' not in row['family_ids']:
            continue
        number = int(row['selector'].split('.test_C',1)[1][:2])
        result = {'selector':row['selector'],'ordinal':row['ordinal'],'inputs':[], 'produced':[], 'unresolved':[]}
        if number not in prepared and number not in no_prepare:
            raise ValueError('P06 selector outside exact 22-case roster')
        for name,index in prepared.get(number,()):
            pin = {'schema':'worker38-loader-pin-v1','executable_sha256':runtime['executable_sha256'],
                'library_relative_path':'Python/3.11.16/x64/lib/libpython3.11.so.1.0',
                'library_sha256':'4'*64,'library_size_bytes':4096}
            value = {'cell_preflight_modules':['literal_stub'],'loader_pin':pin}
            recipe = 'prepare: canonical fixed module list and setUp loader pin'
            if number == 22 and name == 'missing_pin':
                del value['loader_pin']
                recipe += '; delete loader_pin before consumption'
            elif number == 22 and name == 'bad_pin':
                value['loader_pin']['extra'] = 'forbidden'
                recipe += '; add loader_pin.extra=forbidden before consumption'
            elif number == 22:
                recipe += '; runtime-only mutation leaves external-admission bytes unchanged'
            result['inputs'].append({'relative_path':'t01/'+name+'/external-admission.json','kind':'file',
                'raw':canonical(value),'lineage':'independent_literal_input','recipe':recipe})
            result['produced'].append({'relative_path':'t01/'+name+'/receipt.json','kind':'file',
                'lineage':'runtime_generated_consumed_setup','raw_expected':None,
                'source_recipe':'canonical(admission_verified=True,status=measuring,current_cell='+str(index)+
                    ',supervisor_pid=live os.getppid(),supervisor_start_ticks=1001)',
                'input_role':'cell.run_cell reads receipt to verify (pid,1001) identity before work',
                'reservation_reference':'existing diagnostic setup_prefix_allowance_bytes and exact row path union; all raw bytes and partials must remain charged',
                'no_overwrite_proof':'prepare called once per distinct name; cell.py reads parent receipt at51 and never writes it; writes only cells/NN/cell-receipt.json at270 or distinct failure-receipt-cell-NN.json at277; C22 mutates external-admission only',
                'retention':'original produced parent receipt survives under same path; no fabricated PID/hash and no new mock'})
        if number == 5:
            result['inputs'].append({'relative_path':'t01/no_clobber/active-call.json','kind':'file','raw':b'original',
                'lineage':'independent_literal_input','recipe':'C05 no_clobber branch writes exact original bytes; attempted Budget.write cannot replace'})
        elif number == 16:
            for name in ('read_memory','parse_memory','parse_resource','parse_recursion','read_permission'):
                result['inputs'].append({'relative_path':'t01/'+name+'/receipt.json','kind':'file',
                    'raw':canonical({'status':'measuring','literal':'preserved'}),'lineage':'independent_literal_input',
                    'recipe':'C16 exact preexisting receipt; mocked read/parse error prevents modification'})
        elif number == 17:
            for name,raw in (('syntax',b'{'),('duplicate',b'{"status":1,"status":2}'),('encoding',b'\xff'),
                    ('nonobject',b'[]'),('sidecar_memory',b'{'),('sidecar_io',b'{')):
                result['inputs'].append({'relative_path':'t01/'+name+'/receipt.json','kind':'file','raw':raw,
                    'lineage':'independent_literal_input','recipe':'C17 exact malformed bytes; never parse/normalize/repair'})
        result['rng_domain'] = {'seed':11,'native':'CPython3.11.16 random.Random integer-seed/getstate',
            'lineage':'produced delegate/preflight evidence only; no literal setup file contains RNG state',
            'source_correction':'reviewed prose Random(7) is stale; actual cell.py146,186 and test module146 use Random(11)',
            'clone':'Random() is immediately setstate to seed11 state before use; ambient seed is not consumed',
            'execution_in_this_stage':False}
        results.append(result)
    if len(results) != 22:
        raise ValueError('P06 exact roster count changed')
    return {'family_id':'P06','selector_results':results}


# Issue2comment6005833787 adopts only these seven runtime-produced setup slots.
# Exact final source and method spans were checked statically after implementation.
P14_ADOPTION = {'id':6005833787,
    'body_sha256':'db817e61315bef55c57450b261e4531ce88fa2b44dbce537f43e67a98d534180',
    'proposal_sha256':'7b1fb70ad70630cd67953942f0dc1b9394e81ae6663a516bcce92d80fa2a5ab2'}
P14_SOURCE_BINDING = {'path': 'tests/test_worker38_supervision.py', 'sha256': 'efae3f68684d1c1456c1e2fec90e84ebdede16e47feae60dd07e0a277c8545a1', 'size_bytes': 106808}
P14_METHOD_BINDINGS = {300: {'selector': 'tests/test_worker38_supervision.py:SupervisionStubTests.test_F4_04_committed_marker_integrity_matrix', 'first_line': 1055, 'last_line': 1110, 'span_sha256': '5000d8a537888cd41870554557af310409538ae2090db000d70dd35bd8be4209', 'span_size_bytes': 3219}, 303: {'selector': 'tests/test_worker38_supervision.py:SupervisionStubTests.test_F5_01_oversized_integer_clocks_are_integrity_failures', 'first_line': 1155, 'last_line': 1195, 'span_sha256': '02b1778a1372d3f3a1a0969f2f068429c968c37b382cbae8b0c269de557adeab', 'span_size_bytes': 2614}}


def p14_produced_consumed_markers(ctx,row):
    """Name the finite live inputs; never construct their bytes or expected hash."""
    if P14_SOURCE_BINDING is None or set(P14_METHOD_BINDINGS)!={300,303}:
        raise ClosurePrerequisite('P14 final two-method source proof is missing')
    source=ctx['source_bytes']['tests/test_worker38_supervision.py']
    if len(source)!=P14_SOURCE_BINDING['size_bytes'] or sha(source)!=P14_SOURCE_BINDING['sha256']:
        raise ClosurePrerequisite('P14 final supervision source binding drift')
    bound=P14_METHOD_BINDINGS[row['ordinal']]
    if row['selector']!=bound['selector']:
        raise ClosurePrerequisite('P14 exact original selector/ordinal drift')
    span=b''.join(source.splitlines(keepends=True)[bound['first_line']-1:bound['last_line']])
    if len(span)!=bound['span_size_bytes'] or sha(span)!=bound['span_sha256']:
        raise ClosurePrerequisite('P14 completed method source span drift')
    if row['ordinal']==300:
        variants=(
            ('committed-marker-4.json',86,4,
             ['active','wall_started','cpu_started'],
             ['bool True','binary64 T','binary64 0.1'],
             'active call_state has missing or unexpected schema fields'),
            ('committed-marker-6.json',108,6,
             ['active','scope','wall_started','cpu_started'],
             ['bool True','str candidate','binary64 result T-10','binary64 0.1'],
             'call_state wall clock outside child lifetime'),
            ('committed-marker-7.json',108,7,
             ['active','scope','wall_started','cpu_started'],
             ['bool True','str candidate','binary64 result T+100','binary64 0.1'],
             'call_state wall clock outside child lifetime'),
            ('committed-marker-8.json',107,8,
             ['active','scope','wall_started','cpu_started'],
             ['bool True','str candidate','binary64 T','int -1'],
             'call_state CPU clock outside observed child lifetime'),
            ('committed-marker-9.json',128,9,
             ['active','scope','wall_started','cpu_started','unexpected'],
             ['bool True','str candidate','binary64 T','binary64 0.1','bool True'],
             'active call_state has missing or unexpected schema fields'))
    else:
        variants=(
            ('oversized-clock-cpu_started-1.json',506,1,
             ['active','scope','wall_started','cpu_started'],
             ['bool True','str candidate','binary64 T','int 10**400'],
             'invalid active call_state cpu_started'),
            ('oversized-clock-cpu_started--1.json',507,-1,
             ['active','scope','wall_started','cpu_started'],
             ['bool True','str candidate','binary64 T','int -(10**400)'],
             'invalid active call_state cpu_started'))
    completion={
        'write_result':'type(result) is int and result == len(raw); original single write only',
        'readback':'Before and after consumer, O_RDONLY|O_NOFOLLOW|O_NONBLOCK regular single-link file; exact size; one read of len(raw)+1 <=508 bytes equals original raw; close in finally',
        'stable_identity_fields':['st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns'],
        'identity_scope':'descriptor before/after read and named no-follow stat, across both reads and consumer',
        'assertion_scope':'completion/readback and exact reason checks outside expected-exception block',
        'failure':'No repair, retry, deletion or settlement; retain and charge complete or partial bytes',
        'consumer':'one original supervision._call_state(path,T,1.0,T-1,100) call per variant',
        'clock':'T is the original single live time.monotonic() value per method; no new read or mock',
        'future_variant':'T+100 must still fail the original consumer lifetime predicate; delay cannot be repaired or waived',
        'fresh_consumer_clock_numeric_record':False}
    produced=[]
    for name,maximum,index,keys,values,reason in variants:
        produced.append({'relative_path':'t01/'+name,'kind':'file','lineage':'produced_output',
            'classification':'runtime_produced_consumed_setup_data','raw_expected':None,
            'independently_expected_sha256':None,'version_count':1,'maximum_bytes':maximum,
            'input_role':'Original handwritten marker consumed by supervision._call_state; retained at the same unique path',
            'source_variant':{'index_or_sign':index,'ordered_keys':keys,'typed_values':values,
                'serializer':'json.dumps insertion order/default spaces, UTF-8, no newline'},
            'exception_class':'CallStateIntegrityError','exact_reason':reason,
            'required_cause':'OverflowError' if row['ordinal']==303 else None,
            'required_classification':'integrity_invalid' if row['ordinal']==303 else None,
            'completion_conditions':completion,'source_binding':P14_SOURCE_BINDING,
            'source_method_binding':bound,'adoption':P14_ADOPTION,
            'independent_source_recipe_sha256':digest({'recipe_source':ctx['recipe_sha256'],
                'method':bound,'path':name,'variant':index,'reason':reason,'adoption':P14_ADOPTION}),
            'observed_hash_role':'Observed retained identity only; never an independent allowed-state pin',
            'reservation_reference':'Existing setup slot; charge all full/partial bytes once; seven live slots <=1550 bytes and all fourteen slots <=2620 bytes',
            'execution_authorized':False,'reservation_certified':False})
    if len(produced)!=(5 if row['ordinal']==300 else 2) or sum(x['maximum_bytes'] for x in produced)!=(537 if row['ordinal']==300 else 1013):
        raise ClosurePrerequisite('P14 exact live marker count/payload bound drift')
    return produced


def derive_P14(ctx):
    results = []
    for row in ctx['rows']:
        if 'P14' not in row['family_ids']:
            continue
        method = row['selector'].split('.',1)[1]
        result = {'selector':row['selector'],'ordinal':row['ordinal'],'inputs':[], 'produced':[], 'unresolved':[]}
        def add(path,raw,recipe):
            result['inputs'].append({'relative_path':'t01/'+path,'kind':'file','raw':raw,
                'lineage':'independent_literal_input','recipe':recipe})
        if method.endswith('test_S15_valid_transition_and_admission_rejections'):
            add('stub-2/call-state.json',b'preserve','before(state): exact text without newline')
            add('stub-3/child.log',b'preserve','before(log): exact text without newline')
        elif method.endswith('test_F4_04_committed_marker_integrity_matrix'):
            for index,raw in ((0,b'{'),(1,b'{"active":false,"active":true}'),(2,b'[]'),(3,b'{"active":1}'),
                    (5,b'{"active":true,"scope":"candidate","wall_started":NaN,"cpu_started":0}')):
                add('committed-marker-'+str(index)+'.json',raw,'exact handwritten malformed marker literal; no normalization')
            result['produced'].extend(p14_produced_consumed_markers(ctx,row))
            result['source_method_binding']=P14_METHOD_BINDINGS[300]
        elif method.endswith('test_F5_01_oversized_integer_clocks_are_integrity_failures'):
            for sign in (1,-1):
                value = {'active':True,'scope':'candidate','wall_started':sign*(10**400),'cpu_started':0.1}
                add('oversized-clock-wall_started-'+str(sign)+'.json',json.dumps(value).encode('utf-8'),
                    'literal arithmetic 10**400; insertion-order json.dumps default separators, no newline; wall clock field overwritten')
            result['produced'].extend(p14_produced_consumed_markers(ctx,row))
            result['source_method_binding']=P14_METHOD_BINDINGS[303]
        elif method.endswith('test_S47_reused_root_group_and_baseline_do_not_confer_ownership'):
            add('S47-call.json',json.dumps({'active':True,'scope':'candidate','wall_started':110.0,'cpu_started':0.0}).encode('utf-8'),
                'fixed handwritten marker; json.dumps insertion order/default spaces; UTF-8 no newline')
        result['produced'].append({'role':'actual child/STUB_PRELUDE markers, pending markers, child logs, supervisor reports and harness log',
            'lineage':'produced_output','raw_expected':None,
            'reservation_reference':'existing per-selector diagnostic path union; no new file or allowance',
            'native_clocks':'actual spawned-child clock/PID records remain output, not independent literal expected hash',
            'fixed_harness_domain':{'initial_now':1000.0,'failure_now':1900.0,'expired_now':2601.0,
                'cutoff':2500.0,'base_child_pid':987654321,'partial_root_pid':987654310,
                'partial_adopted_pid':987654311,'partial_descendant_pid':987654309,
                'old_producer_pid':987654320,'unrelated_pid':987654321,'pipe_prefix':'literal diagnostic prefix\n'},
            'predecessor_captures':'S14 seventh and S15 first child preserve actual raw predecessor before replace; required completion checks owned by authorized seam patch'})
        result['other_families'] = ['P01: generated stub.py bytes = exact STUB_PRELUDE + newline + finite original code argument; final modified S14/S15 snippets must be rebound','P15: native scalar and source bindings']
        results.append(result)
    if len(results) != 52:
        raise ValueError('P14 exact roster count changed')
    return {'family_id':'P14','selector_results':results}


# Independently authored fixed family fragment, original SHA256 3a4e40697f9d87eda7e6a77c072017c14ada20a65b65a5fbbd5d060b11c034c2
# SOURCE TEXT ONLY; never executed in this authorization stage.
# Exact common constructors. Callers must bind each finite original method's
# ordered root/clock/mutation variants; these helpers alone do not close a row.

def p07_initial_files(ctx):
    files = {'experiment/source-manifest.json':canonical({'files':[]}),
        'stub-test-receipt.json':canonical({'literal':'stub'}),
        'auth/admission.json':canonical({'literal':'GO stub'}),
        'auth/provenance.json':canonical({'literal':'provenance stub'})}
    for name in ('pull-request.json','postmerge-ci.json','current-source-ci.json','review-exhaustive.json',
            'review-adversarial.json','preregistration.json','diagnostic-commit.json'):
        files['auth/'+name] = canonical({'literal':'authenticated-input stub'})
    return files


def p07_loader_identity(ctx):
    pin = source_literal(ctx,'tests/test_worker38_driver_integration.py','LITERAL_LOADER_PIN')
    cache = '/literal-runner/tool-cache'
    library = cache + '/' + pin['library_relative_path']
    directory = library.rsplit('/',1)[0]
    return {**pin,'schema':'worker38-loader-identity-v1','tool_cache':cache,
        'executable_path':cache+'/Python/3.11.16/x64/bin/python3.11','library_path':library,
        'library_directory':directory,'library_device':{'major':8,'minor':1},'library_inode':101,
        'mapped_library':{'path':library,'device':{'major':8,'minor':1},'inode':101},
        'loader_environment':{'LD_LIBRARY_PATH':directory}}


def p07_stub_go(ctx):
    limits = source_literal(ctx,'tests/worker38_literal_fixtures.py','INHERITED_LIMITS')
    limits['RLIMIT_AS'] = [-1,-1]
    return {'head':'a'*40,'tree':'b'*40,'inherited_limits':limits,
        'diagnostic_files_sha256':{},'checked_file_sha256':{},
        'loader_pin':source_literal(ctx,'tests/test_worker38_driver_integration.py','LITERAL_LOADER_PIN')}


def p07_startup_files(ctx, *, absolute_root, attempt_name, claim_name, now,
        auth_files, go, workflow_run='123', source_path=None, runtime_value=None):
    # auth_files maps the seven names plus admission/provenance and optional
    # event/request-context to independently derived bytes, never observed files.
    attempt_path = str(absolute_root / attempt_name)
    if runtime_value is None:
        runtime_value = {'literal':'runtime observations only','loader':p07_loader_identity(ctx),
            'inherited_limits':go['inherited_limits']}
    runtime_raw = canonical(runtime_value)
    startup_raw = canonical({'schema':'worker38-literal-startup-v1','evaluator_starts':0,
        'classification':None,'reservation_consumed':True})
    anchor = int(now * 10**9)
    handoff = {'schema':'worker38-startup-handoff-v1','consumer':'worker38-synthetic-profile-v1',
        'boot_id':'11111111-2222-3333-4444-555555555555',
        'measurement_monotonic_ns':anchor,'measurement_boottime_ns':anchor,
        'measurement_deadline_monotonic_ns':anchor+1800*10**9,
        'measurement_deadline_boottime_ns':anchor+1800*10**9,
        'attempt_path':attempt_path,'source_path':str(absolute_root) if source_path is None else str(source_path),
        'head':go['head'],'tree':go['tree'],'workflow_run':workflow_run,'workflow_attempt':'1',
        'admission_sha256':sha(auth_files['admission.json']),
        'provenance_sha256':sha(auth_files['provenance.json']),
        'runtime_sha256':sha(runtime_raw),'source_map_sha256':sha(canonical(go['checked_file_sha256'])),
        'restored_inventory_sha256':sha(canonical([])),'startup_receipt_sha256':sha(startup_raw)}
    files = {claim_name+'/reservation.txt':
        b'worker38-observed-reservation-v1\ndescriptor_binding=not_yet_validated\nevaluator_starts=0\nclassification=null\n',
        attempt_name+'/source-manifest.json':canonical({'files':[]}),
        attempt_name+'/runtime.json':runtime_raw,attempt_name+'/startup-receipt.json':startup_raw,
        attempt_name+'/startup-handoff.json':canonical(handoff)}
    for name in ('pull-request.json','postmerge-ci.json','current-source-ci.json','review-exhaustive.json',
            'review-adversarial.json','preregistration.json','diagnostic-commit.json','admission.json','provenance.json'):
        files[attempt_name+'/admission-inputs/'+name] = auth_files[name]
    for name in ('event.json','request-context.json'):
        if name in auth_files:
            files[attempt_name+'/admission-inputs/'+name] = auth_files[name]
    return files


def p07_receipt_raw(status='execution_complete'):
    return canonical({'schema':'worker38-attempt-v1','status':status,'failure':None,'actual_starts':0,
        'phase':'verification_pending' if status=='execution_complete' else 'measurement',
        'completed_prefix':[],'resource_totals':{'phase':{'wall_seconds':1,'cpu_seconds':1,
            'wall_limit_seconds':1800,'cpu_limit_seconds':1800,'parent_cpu_seconds':1,
            'reaped_child_cpu_seconds':0,'live_child_cpu_seconds':0}}})


def p07_closing_raw(receipt_raw, now, updates=None):
    # receipt_raw is the independently derived version at this exact call.
    value = {'schema':'worker38-measurement-phase-close-v1',
        'phase':{'wall_seconds':2,'cpu_seconds':2,'wall_limit_seconds':1800,'cpu_limit_seconds':1800,
            'parent_cpu_seconds':2,'reaped_child_cpu_seconds':0,'live_child_cpu_seconds':0},
        'computational_receipt':{'path':'receipt.json','size_bytes':len(receipt_raw),'sha256':sha(receipt_raw)},
        'includes_computational_receipt_publication':True,'closing_proof_included_in_measurement':False,
        'measurement_work_after_close':False,'no_measurement_after_close':True,
        'preservation_started_monotonic':now,'preservation_deadline_monotonic':now+600}
    if updates is not None:
        value.update(updates)
    return canonical(value)


def p04_tampered_handoff_raw():
    value = {'schema':'worker38-startup-handoff-v1','consumer':'worker38-synthetic-profile-v1',
        'boot_id':'11111111-2222-3333-4444-555555555555','measurement_monotonic_ns':100000000000,
        'measurement_boottime_ns':100000000000,'measurement_deadline_monotonic_ns':1900000000000,
        'measurement_deadline_boottime_ns':1900000000000,
        'attempt_path':'/invented-cache/worker38-synthetic-profile/allocations/worker38-synthetic-profile-01/run-501-attempt-1',
        'source_path':'/invented-checkout','head':'1'*40,'tree':'2'*40,'workflow_run':'501','workflow_attempt':'1',
        'admission_sha256':'a'*64,'provenance_sha256':'b'*64,'runtime_sha256':'c'*64,
        'source_map_sha256':'d'*64,'restored_inventory_sha256':'e'*64,'startup_receipt_sha256':'f'*64}
    return canonical(value) + b' '


def p04_failure_setup_files():
    # runtime_observations has Linux makedev(8,1)=2049, fixed inode10/11,
    # executable size1/library23041360 and mtime1. These are mock observations,
    # not stat-derived values from setup files E and L.
    base = 'runtime-0/worker38-synthetic-profile/allocations/worker38-synthetic-profile-01'
    attempt = base+'/run-501-attempt-1'
    shell = ('version=worker38-shell-runtime-v1\nexecutable_stat=2049:10:1:1\n'
        'library_stat=2049:11:23041360:1\nhead='+'1'*40+'\ntree='+'2'*40+
        '\nevent_sha256='+'a'*64+'\nevent_stat=1:20:3:1\n').encode('ascii')
    reservation = ('schema=worker38-observed-reservation-v1\nallocation_id=worker38-synthetic-profile-01\n'
        'run_id=501\nrun_attempt=1\nobserved_head='+'1'*40+
        '\ndescriptor_binding=not_yet_validated\nevaluator_starts=0\nscientific_classification=null\n').encode('ascii')
    return {'failure-checkout/.git/HEAD':('1'*40+'\n').encode('ascii'),
        'runtime-0/Python/3.11.16/x64/bin/python3.11':b'E',
        'runtime-0/Python/3.11.16/x64/lib/libpython3.11.so.1.0':b'L',
        attempt+'/shell-runtime.txt':shell,attempt+'/reservation.txt':reservation,
        base+'/reservation.txt':reservation}


def derive_P04(ctx):
    results = []
    for row in ctx['rows']:
        if 'P04' not in row['family_ids']:
            continue
        case = row['selector'].split('.test_',1)[1].split('_',1)[0]
        result = {'selector':row['selector'],'ordinal':row['ordinal'],'inputs':[], 'produced':[], 'unresolved':[]}
        files = {}
        if case == 'C05':
            files['t01/startup-handoff.json.tmp'] = b'{torn'
        elif case == 'C06':
            files['t01/startup-handoff.json'] = p04_tampered_handoff_raw()
        elif case == 'C08':
            for index in range(20):
                files['t01/experiments/worker38-synthetic-profile/inputs/comparator-7ac2f62c/src/literal_'+str(index)+'.py.blob'] = b'x'
        elif case in ('C04','F01','F02'):
            files.update({'t01/'+path:raw for path,raw in p04_failure_setup_files().items()})
            if case != 'F02':
                files['t01/runtime-0/worker38-synthetic-profile/allocations/worker38-synthetic-profile-01/run-501-attempt-1/admission-process-exit.txt'] = b'schema=worker38-admission-process-exit-v1\nexit_status=79\nadmission_process_returned=true\n'
            result['produced'].append({'role':'failure-preservation report/runtime/failure-handoff/package/custody and any moved pipeline admission-inputs',
                'lineage':'produced_output','raw_expected':None,'reservation_reference':'existing C04/F01/F02 exact path union',
                'source_clock_sequence':'120.0; then121.0 when handoff published; F01 fsync changes now to721.0; preservation cutoff720.0',
                'version_rule':'C04 existing pipeline output rename into failure attempt preserves bytes and origin; do not reclassify as literal input'})
        elif case in ('C09','F03','F05'):
            count = 4 if case == 'F03' else 1
            for index in range(count):
                files['t01/runtime-'+str(index)+'/Python/3.11.16/x64/bin/python3.11'] = b'E'
                files['t01/runtime-'+str(index)+'/Python/3.11.16/x64/lib/libpython3.11.so.1.0'] = b'L'
        elif case == 'H16':
            production = source_literal(ctx,'scripts/worker38/admission.py','REQUIRED_PRODUCTION_PATHS')
            metadata = tuple('experiments/worker38-synthetic-profile/'+name for name in (
                'PROTOCOL.md','INTEGRATION-CONTRACT.json','FINITE-PREPARATION-PLAN.json',
                'SOURCE-GROUNDING.json','comparator-source-manifest.json',
                'upload-amendment/AMENDMENT.md','upload-amendment/AMENDMENT-CONTRACT.json',
                'upload-amendment/FINITE-COVERAGE-AMENDMENT.json','upload-amendment/SOURCE-OBSERVATION.json',
                'upload-amendment/REPAIR-DISPOSITION.json','upload-amendment/HANDOFF.json'))
            originals = {name:b'INVENTED_SOURCE_BYTES_ONLY\n' for name in production}
            originals.update({name:ctx['source_bytes'][name] for name in metadata})
            mapping = {name:sha(raw) for name,raw in originals.items()}
            receipt = canonical({'success':True,'errors':0,'failures':0,'checked_file_sha256':mapping,
                'candidate_evaluator_calls':0,'reference_evaluator_calls':0,'games':0,
                'measurement_fixture_constructions':0,'historical_source_imports':0})
            for variant in ('loader','missing_shared','focused_receipt'):
                prefix = 't01/source-'+variant+'/'
                files.update({prefix+path:raw for path,raw in originals.items()})
                files[prefix+'experiments/worker38-synthetic-profile/focused-preparation-receipt.json'] = (
                    b'changed focused receipt\n' if variant=='focused_receipt' else receipt)
            result['produced'].append({'role':'H16 retained frozen-descriptor/report records','lineage':'produced_output',
                'raw_expected':None,'reservation_reference':'existing H16 output/capture path union',
                'source_mutations':'loader runtime library digest d*64; missing_shared deletes checked mapping only; focused_receipt overwrites literal receipt before source verification'})
        elif case in ('F07','F08'):
            initial = p07_initial_files(ctx)
            files.update({'t02/'+path:raw for path,raw in initial.items()})
            if case == 'F08':
                auth = {path.removeprefix('auth/'):raw for path,raw in initial.items() if path.startswith('auth/')}
                startup = p07_startup_files(ctx,absolute_root=case_root(ctx,row['ordinal'])/'t02',
                    attempt_name='attempt',claim_name='claims',now=1000.0,auth_files=auth,go=p07_stub_go(ctx))
                files.update({'t02/'+path:raw for path,raw in startup.items()})
                result['produced'].append({'role':'one candidate capture prefix plus actual driver failure/rescan receipts',
                    'lineage':'produced_output','raw_expected':None,'reservation_reference':'existing F08 original path union',
                    'source':'literal_orchestration failing=True; reference branch breaks before second scope'})
            else:
                files['t01/complete-checkout/.git/HEAD'] = ('1'*40+'\n').encode('ascii')
                result['unresolved'].append('P04-F07-CROSS-FAMILY-INTEGRATION: instantiate independently derived P08 full357 baseline at t01/complete-external with driver_target=t01/complete-cache/.../run-123-attempt-1 and SCRIPT=t01/complete-checkout/scripts/run_worker38_synthetic.py; apply exact moved cohort and refreshed startup before certification')
                result['produced'].append({'role':'F07 actual driver/package/custody outputs','lineage':'produced_output','raw_expected':None,
                    'reservation_reference':'existing F07 complete orchestration path union',
                    'clock_sequence':'case.now9340.0; child index1..20 sets9340.0+30.0*index; preservation now9941.0; original cutoff10540.0',
                    'fixed_pids':'measure1000; preserve1001; parent1002; former coordinator1000 is FileNotFoundError',
                    'move_sequence':'cells,receipt,source-runtime-preflight,measurement-phase-close,coordinator-restoration,external-admission,stub-test-receipt,writer-exit-observation then40 supervisor json/log paths move target->complete-pending; each cell record and matching log move back once in original order; no byte copy changes lineage'})
        for path,raw in files.items():
            result['inputs'].append({'relative_path':path,'kind':'file','raw':raw,
                'lineage':'independent_literal_input','recipe':'P04 exact finite source constructor for '+case+'; preserve literal newline/malformed bytes and final root where present'})
        result['other_families'] = ['P01 direct shell/source/stub/literal setup','P03 baseline and mutated authentication bundle','P07 Driver common constructors','P08 F07 full357 literal cohort']
        results.append(result)
    if len(results) != 64:
        raise ValueError('P04 exact roster count changed')
    return {'family_id':'P04','selector_results':results}


def derive_P07(ctx):
    # Row-specific startup calls are explicitly enumerated below. No test body
    # or helper is executed or interpreted. A review must still join the
    # ordered source mutation specification before full row certification.
    simple_startup = ('D02','D03','D05','D13','D14','D20','D21','D25','D26','D28',
        'D34','D35','D36','D37','D39','D40','D44','R1D07','R1D08')
    simple_measuring = ('D04','D06','D07','D15','D16','D17','D18','D19','D22','D23',
        'D27','D29','D30','D32','D43')
    simple_complete = ('D08','D09','D10','D45','D46','D47','D48')
    plain_no_other_file_setup = ('D12','D24','D31','D33','D41','D42')
    results = []
    for row in ctx['rows']:
        if 'P07' not in row['family_ids']:
            continue
        label = row['selector'].split('.test_',1)[1]
        case = label.split('_',1)[0]
        if label.startswith('ER_I01_'):
            case = 'ER_I01'
        elif label.startswith('ER_I02_'):
            case = 'ER_I02'
        result = {'selector':row['selector'],'ordinal':row['ordinal'],'inputs':[], 'produced':[], 'unresolved':[]}
        initial = p07_initial_files(ctx)
        def add(path,raw,recipe):
            result['inputs'].append({'relative_path':'t01/'+path,'kind':'file','raw':raw,
                'lineage':'independent_literal_input','recipe':recipe})
        for path,raw in initial.items():
            add(path,raw,'DriverIntegration.setUp exact initial fixture; exists for all72 methods')
        auth = {path.removeprefix('auth/'):raw for path,raw in initial.items() if path.startswith('auth/')}
        startup = []
        if case in simple_startup:
            startup = [('attempt','claims',1000.0)]
        elif case == 'D01':
            startup = [('attempt-prerequisite-runtime','claims-prerequisite-runtime',1000.0),
                ('attempt-prerequisite-source','claims-prerequisite-source',1000.0)]
        elif case == 'D38':
            startup = [('event-attempt-'+str(i),'event-claims-'+str(i),1000.0) for i in range(4)]
        elif case == 'R1D01':
            startup = [('attempt-loader-False','claims-loader-False',1000.0),('attempt-loader-True','claims-loader-True',1000.0)]
        elif case == 'R1D06':
            startup = [('attempt','claims',1000.0),('attempt-arm-delay','claims-arm-delay',100.0)]
        elif case == 'R1D09':
            startup = [('attempt-discovered-'+kind,'claims-discovered-'+kind,1000.0)
                for kind in ('write_expiry','read_expiry','write_integrity_at_expiry')]
        elif case == 'R1D10':
            startup = [('attempt-arm-before','claims-arm-before',1900.0),('attempt-arm-after','claims-arm-after',1900.0)]
        elif case == 'R1D11':
            startup = [('attempt-callback-'+kind,'claims-callback-'+kind,1000.0) for kind in ('metadata','missing_timestamp')]
        elif case == 'R1D12':
            startup = [('attempt-coordinator-'+kind,'claims-coordinator-'+kind,1000.0)
                for kind in ('disable_before','handler_before','disable_after_memory','handler_after_memory',
                    'disable_mismatch','handler_mismatch','disable_getter','handler_getter')]
        elif case == 'R1D14':
            startup = [('attempt-handler-coordinator','claims-handler-coordinator',1000.0)]
        elif case == 'R1D16':
            startup = [('attempt-partial-True','claims-partial-True',1000.0),('attempt-partial-False','claims-partial-False',1000.0)]
        for attempt,claim,now in startup:
            for path,raw in p07_startup_files(ctx,absolute_root=case_root(ctx,row['ordinal'])/'t01',
                    attempt_name=attempt,claim_name=claim,now=now,auth_files=auth,go=p07_stub_go(ctx)).items():
                add(path,raw,'Exact prepare_startup call at mocked now='+repr(now)+'; original root/claim variant '+attempt)
        if case in simple_measuring or case in simple_complete:
            status = 'measuring' if case in simple_measuring else 'execution_complete'
            raw = p07_receipt_raw(status)
            add('attempt/receipt.json',raw,'make_receipt initial exact setup; later production mutation retains produced lineage')
            if status == 'execution_complete':
                add('attempt/measurement-phase-close.json',p07_closing_raw(raw,1000.0),
                    'first make_receipt closing proof from independent receipt bytes and existing mocked1000.0 clock')
            if case in ('D45','D47','D48'):
                add('attempt/measurement-phase-close.json',p07_closing_raw(raw,1000.0,
                    {'preservation_started_monotonic':299.0,'preservation_deadline_monotonic':899.0}),
                    'second closing-proof version; exact explicit299.0/899.0 update before consumption')
        if case in ('ER_I01','ER_I02'):
            result['unresolved'].append('P07-'+case+'-AUTHENTICATED-METADATA-JOIN: independently bind shared checked-source roster/source receipts and P03 auth values for all10 prerequisite or7 tamper variants, then p07_startup_files; retain copied-original versus missing/newline-mutated auth states')
        elif case not in plain_no_other_file_setup:
            result['unresolved'].append('P07-'+case+'-ORDERED-STATE-JOIN: common initial/startup/receipt recipes are supplied, but final per-invocation setup/mutation/missing/staged/version bindings in P04-P07-ORDERED-SOURCE-SPEC.json must be explicitly joined before this row can be certified')
        result['produced'].append({'role':'actual driver receipt/runtime/reconciliation/preservation/timer/child/staging outputs',
            'lineage':'produced_output','raw_expected':None,'reservation_reference':'existing original-order Driver72 path union and11 fixed pre-mutation versions',
            'no_oracle':'never source expected input from observed setup_inventory, c.file_info or returned helper results'})
        results.append(result)
    if len(results) != 72:
        raise ValueError('P07 exact roster count changed')
    return {'family_id':'P07','selector_results':results}


PROSPECTIVE_NATIVE_NAMESPACE = '/workspace/shared/worker38-native-batch-04'
NAMED_SOURCE_INPUTS = ('evidence-design/derive-first33-input-pins.py', 'evidence-design/derive-native-environment-closure.py', 'evidence-design/run-worker38-fixed-preparation.py', 'experiments/worker38-synthetic-profile/FINITE-PREPARATION-PLAN.json', 'experiments/worker38-synthetic-profile/INTEGRATION-CONTRACT.json', 'experiments/worker38-synthetic-profile/PROTOCOL.md', 'experiments/worker38-synthetic-profile/SOURCE-GROUNDING.json', 'experiments/worker38-synthetic-profile/comparator-source-manifest.json', 'experiments/worker38-synthetic-profile/upload-amendment/AMENDMENT-CONTRACT.json', 'experiments/worker38-synthetic-profile/upload-amendment/AMENDMENT.md', 'experiments/worker38-synthetic-profile/upload-amendment/FINITE-COVERAGE-AMENDMENT.json', 'experiments/worker38-synthetic-profile/upload-amendment/HANDOFF.json', 'experiments/worker38-synthetic-profile/upload-amendment/REPAIR-DISPOSITION.json', 'experiments/worker38-synthetic-profile/upload-amendment/SOURCE-OBSERVATION.json', 'scripts/worker37-bootstrap.sh', 'scripts/worker37_bootstrap.py', 'scripts/worker38-bootstrap.sh', 'scripts/worker38/admission.py', 'scripts/worker38/common.py', 'scripts/worker38/driver.py', 'scripts/worker38/supervision.py', 'scripts/worker38/transport.py', 'scripts/worker38/verify.py', 'scripts/worker_bootstrap_shared.py', 'scripts/worker_bootstrap_shared.sh', 'tests/test_worker37_bootstrap.py', 'tests/test_worker38_bootstrap_integration.py', 'tests/test_worker38_cell_integration.py', 'tests/test_worker38_core.py', 'tests/test_worker38_driver_integration.py', 'tests/test_worker38_supervision.py', 'tests/test_worker38_transport.py', 'tests/test_worker38_verify_integration.py', 'tests/worker38_constructor_source.txt', 'tests/worker38_literal_fixtures.py')
PREDECESSOR_SOURCE_BINDINGS = {'evidence-design/derive-first33-input-pins.py': {'path': '/workspace/shared/worker38-implementation/evidence-design/derive-first33-input-pins.py', 'sha256': '910c22f761f871ddd2d408a7a3d5f58df45ced37b46659ea1b9e7d09c2c3b644', 'size_bytes': 24909}, 'evidence-design/derive-native-environment-closure.py': {'path': '/workspace/shared/worker38-implementation/evidence-design/derive-native-environment-closure.py', 'sha256': 'd02fc1d78a7cd20b71e67a24629af9c88d0994c508d688700aaaea4d7a00ffd7', 'size_bytes': 33372}, 'evidence-design/run-worker38-fixed-preparation.py': {'path': '/workspace/shared/worker38-implementation/evidence-design/run-worker38-fixed-preparation.py', 'sha256': 'c9407bd56aee2b0cce35b3787145feaaed40fafa2fc8f2de2fdd0b9f963ee494', 'size_bytes': 81406}, 'scripts/worker38/admission.py': {'path': '/workspace/shared/worker38-implementation/scripts/worker38/admission.py', 'sha256': '260309ba2ba0e2c720c805dd7c9821f6efb689ce76ef6d9a4513d9a26473b7ce', 'size_bytes': 74181}, 'scripts/worker38/common.py': {'path': '/workspace/shared/worker38-implementation/scripts/worker38/common.py', 'sha256': 'fe0732a0e08d5852c87ed9c18c23469ced28d93d097c3d434ce6171e4acdd927', 'size_bytes': 37905}, 'scripts/worker38/driver.py': {'path': '/workspace/shared/worker38-implementation/scripts/worker38/driver.py', 'sha256': '22dc18c2141e6aa82de84e052cde8d87fa2871b0f1ddda5e791d0db538f3d0e6', 'size_bytes': 104303}, 'scripts/worker38/supervision.py': {'path': '/workspace/shared/worker38-implementation/scripts/worker38/supervision.py', 'sha256': '1f6a4434c250b9adf0efb02e25bfb458f0cb378282eaa2d1c6ea6e5e92420f88', 'size_bytes': 83208}, 'scripts/worker38/transport.py': {'path': '/workspace/shared/worker38-implementation/scripts/worker38/transport.py', 'sha256': 'fa285ccf140f646acea0fbcc7ba7bd63103966357040b22f83eccd174b47fb82', 'size_bytes': 66602}, 'scripts/worker38/verify.py': {'path': '/workspace/shared/worker38-implementation/scripts/worker38/verify.py', 'sha256': 'd8040979eb7ba7ca4081075efaa2176c8d74628fad086cb71a6c795ad0f29204', 'size_bytes': 70923}, 'tests/test_worker37_bootstrap.py': {'path': '/workspace/shared/worker38-implementation/tests/test_worker37_bootstrap.py', 'sha256': '81824787ff3b8cae5ce82d29ccf5ab9c7139ed4db47e82bbdb8ad40722d3db83', 'size_bytes': 123546}, 'tests/test_worker38_bootstrap_integration.py': {'path': '/workspace/shared/worker38-implementation/tests/test_worker38_bootstrap_integration.py', 'sha256': '125b0ee9bfbb0c8c371babacb87164547a90b1c202660cd2c5ef715c40fd0042', 'size_bytes': 107174}, 'tests/test_worker38_cell_integration.py': {'path': '/workspace/shared/worker38-implementation/tests/test_worker38_cell_integration.py', 'sha256': '0fc276cef0ee61c17e797a4928dddc7dda90d83a8f1f11ceea6796ec70f4e5ca', 'size_bytes': 39173}, 'tests/test_worker38_core.py': {'path': '/workspace/shared/worker38-implementation/tests/test_worker38_core.py', 'sha256': 'bf8e7feb7ac25102766e0b5b28a202fb8ccc0e705c160022d2ad1413fdece7f8', 'size_bytes': 30668}, 'tests/test_worker38_driver_integration.py': {'path': '/workspace/shared/worker38-implementation/tests/test_worker38_driver_integration.py', 'sha256': '4570bfc2b34aaf2d743ac6c6b5fb8761abdd27c4642174b0cb0aa62f3f1f6b7b', 'size_bytes': 117000}, 'tests/test_worker38_supervision.py': {'path': '/workspace/shared/worker38-implementation/tests/test_worker38_supervision.py', 'sha256': '4b30a0e579354f96e19e8fb1a0f7e45c2642f141c1d35c3268433e4c8b7ef71c', 'size_bytes': 96410}, 'tests/test_worker38_transport.py': {'path': '/workspace/shared/worker38-implementation/tests/test_worker38_transport.py', 'sha256': 'd89ba63aca51c72972e4ba5a1c67d697fed08bf1c26fee84f6e8531513561dc1', 'size_bytes': 44185}, 'tests/test_worker38_verify_integration.py': {'path': '/workspace/shared/worker38-implementation/tests/test_worker38_verify_integration.py', 'sha256': '5fb0c8d1b6b13eba69041ef1e1b16ec7268433f9862153d580a18e100ccc2a11', 'size_bytes': 110561}, 'tests/worker38_literal_fixtures.py': {'path': '/workspace/shared/worker38-implementation/tests/worker38_literal_fixtures.py', 'sha256': '635eaaf457800c5f508f11033f6f28003c1e0393dc0444fa155a1e907984dde2', 'size_bytes': 12036}}
FIXED_METADATA_INPUTS = {'DERIVATION-FAMILIES.json': {'path': '/workspace/shared/worker38-full-closure-proposal-repair01/pins/DERIVATION-FAMILIES.json', 'size_bytes': 40763, 'sha256': 'd5a942708e2b0123c6af88b69c8a61327f8b43c0287fe25060d7ba351d6e28d4'}, 'FULL397-PIN-OBLIGATION-MATRIX.json': {'path': '/workspace/shared/worker38-full-closure-proposal-repair01/pins/FULL397-PIN-OBLIGATION-MATRIX.json', 'size_bytes': 882337, 'sha256': '7ee70b8bc1cec31bdce0f6579473a3792de3f2688617ca82631ce3a9f4cf2f32'}, 'VERIFIER-EVENT-MATRIX.json': {'path': '/workspace/shared/worker38-full-closure-proposal-repair01/pins/VERIFIER-EVENT-MATRIX.json', 'size_bytes': 880574, 'sha256': 'b02354f88eff7c991de64e0895ea2afc954c48acca70d4b6bd25d1f673177b1d'}, 'FINAL-LITERAL-RUNTIME-DISPOSITIONS.json': {'path': '/workspace/shared/worker38-full-closure-proposal-repair01/pins/FINAL-LITERAL-RUNTIME-DISPOSITIONS.json', 'size_bytes': 3150, 'sha256': 'f1ff43d1c963c506e2d909bec4bb009a0548a9c8f230ac93cb4adc7bb9d81e37'}, 'fixed_map': {'path': '/workspace/shared/worker38-implementation/evidence-design/worker38-fixed-fixtures.json', 'size_bytes': 1762030, 'sha256': 'b5f5561ea24049f0d4107ff7679ac0d7af23f8cb35ee6969ba235daefa18d1a6'}, 'loader_fields': {'path': '/workspace/shared/worker38-full-closure-implementation/core-proof/CONTEXT-FIELD-ROSTER.json', 'size_bytes': 122419, 'sha256': 'a39b8c523fc020a05b4eea3fa20b308177cd15c9342716d009ccfa6d5bc18145'}, 'loader_dynamic': {'path': '/workspace/shared/worker38-full-closure-implementation/collector-proof/DYNAMIC-FIELD-ROSTER.json', 'size_bytes': 7647, 'sha256': '4d9f4f03f4b2c9228f653d5d7094b3d256d3553018347f9602ae10e8a57a967d'}}

# The deterministic recipes are authored, not executed or runtime-certified.
# Issue2comment6005833787 dispositions only the seven live P14 input slots.
# Source closure never grants materialization, reserves all397, or admits a run.
DETERMINISTIC_SOURCE_STATUS = 'AUTHORED_STATIC_ONLY_PENDING_COMPLETE_INDEPENDENT_REVIEWS'
SOURCE_CLOSURE_COMPLETE = True
OPEN_RECIPE_PREREQUISITES = ()
FAMILY_DISPATCH = {'P01':derive_P01,'P02':derive_P02,'P03':derive_P03,'P04':derive_P04,
    'P05':derive_P05,'P06':derive_P06,'P07':derive_P07,'P08':derive_P08,'P09':derive_P09,
    'P10':derive_P10,'P11':derive_P11,'P12':derive_P12,'P13':derive_P13,'P14':derive_P14,'P15':derive_P15}


def read_bound_json(pin):
    if set(pin)!={'path','size_bytes','sha256'}:raise ClosurePrerequisite('exact metadata binding shape')
    path=Path(pin['path'])
    if path.is_symlink() or not path.is_file():raise ClosurePrerequisite('metadata must be a regular nonlink file')
    raw=path.read_bytes()
    if len(raw)!=pin['size_bytes'] or sha(raw)!=pin['sha256']:raise ClosurePrerequisite('metadata bytes drift '+str(path))
    return json.loads(raw)


def load_materialization_context(bindings):
    expected={'schema','candidate_root','namespace','recipe_source_sha256','source_pins','caps','environment_closure'}
    if set(bindings)!=expected or bindings['schema']!='worker38-literal-final-input-bindings-v1':
        raise ClosurePrerequisite('final input binding schema')
    if bindings['namespace']!=PROSPECTIVE_NATIVE_NAMESPACE or bindings['caps']!=CAPS:
        raise ClosurePrerequisite('native namespace/count/order/caps may not change')
    if bindings['candidate_root']!='/workspace/shared/worker38-implementation':
        raise ClosurePrerequisite('candidate source root changed')
    if set(bindings['source_pins'])!=set(NAMED_SOURCE_INPUTS):
        raise ClosurePrerequisite('finite named source input set changed')
    source_bytes={}
    for name in NAMED_SOURCE_INPUTS:
        pin=bindings['source_pins'][name]
        if set(pin)!={'size_bytes','sha256'}:raise ClosurePrerequisite('exact source binding schema')
        path=Path(bindings['candidate_root'])/name
        if path.is_symlink() or not path.is_file():raise ClosurePrerequisite('source not regular nonlink '+name)
        raw=path.read_bytes()
        if name in IMMUTABLE_SOURCE_PINS and pin!=IMMUTABLE_SOURCE_PINS[name]:
            raise ClosurePrerequisite('unadopted immutable source change '+name)
        if len(raw)!=pin['size_bytes'] or sha(raw)!=pin['sha256']:raise ClosurePrerequisite('final source drift '+name)
        source_bytes[name]=raw
    meta={key:read_bound_json(pin) for key,pin in FIXED_METADATA_INPUTS.items()}
    rows=meta['FULL397-PIN-OBLIGATION-MATRIX.json']['rows']
    if len(rows)!=397 or [r['ordinal'] for r in rows]!=list(range(1,398)):
        raise ClosurePrerequisite('original397 method order drift')
    ev=meta['VERIFIER-EVENT-MATRIX.json']
    if len(ev['events'])!=401 or ev['intended_path_occurrences']!=11559 or len(ev['path_scopes'])!=72:
        raise ClosurePrerequisite('frozen verifier event/path scope changed')
    return {'namespace':bindings['namespace'],'source_bytes':source_bytes,'rows':rows,
        'events':ev['events'],'path_scopes':ev['path_scopes'],'recipe_sha256':bindings['recipe_source_sha256'],
        'fixed_map':meta['fixed_map'],'loader_fields':meta['loader_fields'],'loader_dynamic':meta['loader_dynamic'],
        'environment_closure':bindings['environment_closure'],'startup_auth_audit':meta['startup_auth_audit']}


def pin_wire(value):
    # Convert only independently constructed bytes, never external expected files.
    if type(value) is bytes:return {'size_bytes':len(value),'sha256':sha(value)}
    if type(value) in (tuple,list):return [pin_wire(x) for x in value]
    if type(value) is dict:return {key:pin_wire(item) for key,item in value.items()}
    return value


def reconcile_p01_p07_initial_inputs(ctx,family_results):
    """Discharge only the exact253 shared setup obligations, never other errors."""
    p01={item['ordinal']:item for item in family_results['P01']['selector_results']}
    p07={item['ordinal']:item for item in family_results['P07']['selector_results']}
    joined=[]
    for ordinal,selector in _P01_P07_SHARED_SELECTORS.items():
        left=p01[ordinal];right=p07[ordinal]
        if left['selector']!=selector or right['selector']!=selector:
            raise ClosurePrerequisite('P01/P07 initial selector equality failed')
        left_inputs=[value for value in left['inputs'] if value.get('shared_recipe_owner')=='P07.p07_initial_files']
        right_inputs=[value for value in right['inputs']
            if value['recipe']=='DriverIntegration.setUp exact initial fixture; exists for all72 methods']
        if (len(left_inputs)!=11 or len(right_inputs)!=11 or
                {value['relative_path'] for value in left_inputs}!=set(_P01_P07_INITIAL_PATHS) or
                {value['relative_path'] for value in right_inputs}!=set(_P01_P07_INITIAL_PATHS)):
            raise ClosurePrerequisite('P01/P07 exact eleven initial paths failed')
        right_by_path={value['relative_path']:value for value in right_inputs}
        for left_value in left_inputs:
            right_value=right_by_path[left_value['relative_path']]
            if (left_value['kind']!='file' or right_value['kind']!='file' or
                    left_value['lineage']!='independent_literal_input' or
                    right_value['lineage']!='independent_literal_input' or
                    type(left_value['raw']) is not bytes or type(right_value['raw']) is not bytes or
                    left_value['raw']!=right_value['raw']):
                raise ClosurePrerequisite('P01/P07 complete raw/type/lineage equality failed')
            joined.append({'ordinal':ordinal,'selector':selector,'relative_path':left_value['relative_path'],
                'type':'file','size_bytes':len(left_value['raw']),'sha256':sha(left_value['raw']),
                'lineage':'independent_input','owner':'P07.p07_initial_files',
                'independent_recipe_sha256':left_value['independent_recipe_sha256'],
                'same_physical_asset_not_additional_copy':True})
    if len(joined)!=253:raise ClosurePrerequisite('exact253 shared Driver rule join changed')
    return joined


def derive_complete_literals(ctx):
    if not SOURCE_CLOSURE_COMPLETE:
        raise ClosurePrerequisite('source recipe closure incomplete: '+'; '.join(OPEN_RECIPE_PREREQUISITES))
    environment_result=FAMILY_DISPATCH['P15'](ctx)
    ctx['verifier_results']=derive_verifier_states(ctx)
    family_results={name:(environment_result if name=='P15' else FAMILY_DISPATCH[name](ctx)) for name in FAMILY_DISPATCH}
    shared_initial_inputs=reconcile_p01_p07_initial_inputs(ctx,family_results)
    obligations=[]
    for row in ctx['rows']:
        resolutions=[];unresolved=[]
        for family in row['family_ids']:
            matches=[x for x in family_results[family]['selector_results'] if x['selector']==row['selector']]
            if len(matches)!=1:raise ClosurePrerequisite('missing singular family/selector obligation '+family+' '+row['selector'])
            item=matches[0];unresolved.extend(item.get('unresolved',[]))
            resolutions.append({'family_id':family,'recipe_function':FAMILY_DISPATCH[family].__name__,
                'result_sha256':digest(pin_wire(item))})
        obligations.append({'ordinal':row['ordinal'],'selector':row['selector'],'families':resolutions,
            'unresolved':unresolved,'reservation_certified':False,'execution_authorized':False})
    failures=[item for item in obligations if item['unresolved']]
    if failures:raise ClosurePrerequisite('unclosed exact obligations: '+json.dumps(failures,sort_keys=True))
    # P08-P12 share one derivation per selector. Export the full state product
    # once; a family reference cannot replace or supply missing asset identities.
    verifier_derivations=pin_wire(ctx['verifier_results'])
    verifier_by_ordinal={item['ordinal']:item for item in verifier_derivations}
    exported_families={}
    for family,result in family_results.items():
        if family in ('P08','P09','P10','P11','P12'):
            references=[]
            for item in result['selector_results']:
                exported=verifier_by_ordinal[item['ordinal']]
                if exported['selector']!=item['selector'] or exported!=pin_wire(item):
                    raise ClosurePrerequisite('shared verifier asset export/family mismatch')
                references.append({'selector':item['selector'],'ordinal':item['ordinal'],
                    'verifier_derivation_ordinal':item['ordinal'],'result_sha256':digest(exported),
                    'unresolved':list(item['unresolved'])})
            exported_families[family]={**{key:pin_wire(value) for key,value in result.items() if key!='selector_results'},
                'selector_results':references}
        else:exported_families[family]=pin_wire(result)
    return {'schema':'worker38-all397-literal-pins-v1','recipe_source_sha256':ctx['recipe_sha256'],
        'native_output_root':ctx['namespace'],'families':exported_families,'caps':CAPS,
        'verifier_derivations':verifier_derivations,
        'verifier_asset_export_schema':'worker38-complete-independent-verifier-assets-v1',
        'selected_witnesses_do_not_replace_complete_asset_pins':True,
        'p01_p07_shared_initial_inputs':shared_initial_inputs,
        'execution_authorized':False,'all397_reservation_or_fit_certified':False},obligations


def serialize_final_map(final_map):
    # The parent owns map construction. Call only after every enclosing field,
    # comma, row/reference/list framing and source/environment binding is present.
    raw=canonical(final_map)
    if len(final_map.get('cases',[]))!=397:raise ClosurePrerequisite('final map roster incomplete')
    if len(raw)>MAP_LIMIT:raise ClosurePrerequisite('complete compact UTF8 map including LF exceeds8388608')
    return raw,{'size_bytes':len(raw),'sha256':sha(raw),'newline_included':True}


def main():
    parser=argparse.ArgumentParser(description='Independently materialize reviewed closed Worker38 literal recipes; never run tests')
    parser.add_argument('--bindings',required=True)
    parser.add_argument('--materialization-authority',required=True)
    parser.add_argument('--output-directory',required=True)
    args=parser.parse_args()
    # This static work stage supplies NO materialization grant. Source incompleteness
    # fails before constructing any fixture, loading candidate source or writing.
    if not SOURCE_CLOSURE_COMPLETE:
        raise SystemExit('BLOCKED: '+ '; '.join(OPEN_RECIPE_PREREQUISITES))
    source_raw=Path(__file__).read_bytes()
    binding_raw=Path(args.bindings).read_bytes();bindings=json.loads(binding_raw)
    grant=json.loads(Path(args.materialization_authority).read_bytes())
    command=['/usr/bin/python3','-B','-P',str(Path(__file__).absolute()),'--bindings',str(Path(args.bindings).absolute()),
        '--materialization-authority',str(Path(args.materialization_authority).absolute()),
        '--output-directory',str(Path(args.output_directory).absolute())]
    required={'schema','action','recipe_source_sha256','bindings_sha256','command_sha256','output_directory'}
    if set(grant)!=required or grant['schema']!='worker38-independent-literal-materialization-authority-v1' or grant['action']!='independent_literal_materialization_only':
        raise ClosurePrerequisite('missing separate bounded materialization authority')
    if grant['recipe_source_sha256']!=sha(source_raw) or bindings['recipe_source_sha256']!=sha(source_raw) or grant['bindings_sha256']!=sha(binding_raw) or grant['command_sha256']!=digest(command):
        raise ClosurePrerequisite('exact command/source/dependency grant binding mismatch')
    destination=Path(args.output_directory).absolute()
    if str(destination)!=grant['output_directory'] or destination.exists():raise ClosurePrerequisite('exclusive granted output directory required')
    for forbidden in (Path(bindings['candidate_root']),Path(PROSPECTIVE_NATIVE_NAMESPACE)):
        if destination.is_relative_to(forbidden):raise ClosurePrerequisite('literal output must remain outside candidate and native-attempt namespace')
    ctx=load_materialization_context(bindings)
    pins,obligations=derive_complete_literals(ctx)
    documents={'ALL397-INDEPENDENT-LITERAL-PINS.json':pins,
        'ALL397-PIN-OBLIGATIONS.json':{'schema':'worker38-all397-recipe-obligations-v1','rows':obligations},
        'LITERAL-DERIVATION-RECEIPT.json':{'schema':'worker38-literal-materialization-receipt-v1',
            'recipe_source_sha256':sha(source_raw),'bindings_sha256':sha(binding_raw),'command':command,
            'fixture_helper_calls':0,'candidate_imports':0,'tests':0,'runner_invocations':0,'science':0,
            'map_size_gate_pending':True,'reservation_certification_pending':True,'execution_authorized':False}}
    encoded={name:canonical(value) for name,value in documents.items()}
    output_limits={'ALL397-INDEPENDENT-LITERAL-PINS.json':50331648,
        'ALL397-PIN-OBLIGATIONS.json':4194304,'LITERAL-DERIVATION-RECEIPT.json':65536}
    if tuple(encoded)!=tuple(output_limits):
        raise ClosurePrerequisite('exact three literal output names/order required')
    # Exit 73 means only an established exact encoded-byte cap, never a guessed
    # cause from stderr. Every byte, including LF, is checked before mkdir/open.
    if (any(len(encoded[name])>limit for name,limit in output_limits.items()) or
            sum(len(raw) for raw in encoded.values())>54591488):
        raise SystemExit(73)
    import os
    output_failure=None
    parent_fd=None
    directory_fd=None
    try:
        parent_fd=os.open(destination.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
        os.mkdir(destination.name,mode=0o700,dir_fd=parent_fd)
        directory_fd=os.open(destination.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,
            dir_fd=parent_fd)
        for name,raw in encoded.items():
            file_failure=None
            file_fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,
                0o600,dir_fd=directory_fd)
            try:
                # One unbuffered write; no buffered flush/close can retry it.
                written=os.write(file_fd,raw)
                if type(written) is not int or written!=len(raw):
                    raise OSError('incomplete exclusive literal output write')
            except BaseException as failure:
                file_failure=failure
            finally:
                try:
                    os.fsync(file_fd)
                except BaseException as failure:
                    if file_failure is None:
                        file_failure=failure
                    else:
                        failure.__context__=file_failure.__cause__
                        file_failure.__cause__=failure
                try:
                    os.close(file_fd)
                except BaseException as failure:
                    if file_failure is None:
                        file_failure=failure
                    else:
                        failure.__context__=file_failure.__cause__
                        file_failure.__cause__=failure
            if file_failure is not None:
                raise file_failure
    except BaseException as failure:
        output_failure=failure
    finally:
        # Persist the file names and new directory name, including partials.
        # Each owned directory is synced and closed once, within the one phase.
        for owned_fd in (directory_fd,parent_fd):
            if owned_fd is None:
                continue
            try:
                os.fsync(owned_fd)
            except BaseException as failure:
                if output_failure is None:
                    output_failure=failure
                else:
                    failure.__context__=output_failure.__cause__
                    output_failure.__cause__=failure
            try:
                os.close(owned_fd)
            except BaseException as failure:
                if output_failure is None:
                    output_failure=failure
                else:
                    failure.__context__=output_failure.__cause__
                    output_failure.__cause__=failure
    if output_failure is not None:
        raise output_failure




def transport_direct_setup(ctx,row):
    """P13 original T01-16 exact finite raw-source and seal fixture paths.

    Package/download/wrapper mutation results retain production lineage. These
    operations describe actual-output versions but never calculate their bytes
    from observed output or invent a live timestamp/PID expected hash.
    """
    method=row['selector'].rsplit('.',1)[-1];case=method.split('_')[1]
    prefix=case_root(ctx,row['ordinal'])/'t01'
    inputs=[];produced=[]
    def add(path,raw,kind='file',phase='setup'):
        inputs.append({'relative_path':'t01/'+path,'kind':kind,'raw':raw,
            'lineage':'independent_literal_input','recipe':case+' '+phase+' exact direct source operation'})
    def package(index):
        add('raw-'+str(index)+'/receipt.json',b'invented transport bytes\n')
        add('raw-'+str(index)+'/nested/stub.bin',b'\x00\x01stub\xff')
        produced.append({'relative_root':'t01/package-'+str(index+1),'lineage':'produced_output',
            'role':'actual deterministic archive, part, manifest, partials and failure sidecars',
            'source':'OfflineTransportPlan.package69-78; transport.package_attempt',
            'raw_expected':None,'complete_and_partial_charged':True})
    def writers(index):
        root='literal-cache-'+str(index)+'/worker38-synthetic-profile/allocations/worker38-synthetic-profile-01/'
        for name in ('writer-exit-observation.json','startup-failure.json'):
            add(root+'run-123-attempt-1/'+name,b'{"literal":"fixed completed writer evidence"}\n')
        produced.append({'relative_root':'t01/'+root+'transport-123-attempt-1','lineage':'produced_output',
            'operation':'rename original package directory without changing content or lineage; seal adds production plan/receipt',
            'in_memory_handoff':'preservation_pid is actual os.getpid; no serialized literal expected PID/hash claimed',
            'complete_and_partial_charged':True})
    if case in ('T01','T02','T03','T08','T10','T11','T12','T13','T14','T16'):
        package(1)
    if case=='T01':
        writers(5)
        produced += [{'relative_path':'t01/invented-provider-wrapper.zip-3','lineage':'produced_output','operation':'native timestamped wrapper; raw retained unchanged'},
            {'relative_root':'t01/readback-4','lineage':'produced_output','operation':'actual transport extraction and rehash; all copies and partials charged'}]
    elif case=='T02':package(3)
    elif case=='T03':
        produced.append({'relative_root':'t01/package-2','lineage':'produced_output','operation':'both rejected destination reuses preserve the first package bytes; no extra copy'})
    elif case=='T04':
        for index,kind in ((1,'symlink'),(3,'fifo'),(5,'unsafe-name'),(7,'nested-destination')):
            root='unsafe-source-'+str(index)
            add(root+'/keep',b'preserve')
            if kind=='symlink':add(root+'/link',str(prefix/root/'keep').encode('ascii'),'symlink')
            elif kind=='fifo':add(root+'/pipe',None,'special')
            elif kind=='unsafe-name':add(root+'/bad\\name',b'bad')
            produced.append({'relative_root':'t01/unsafe-output-'+str(index+1),'lineage':'produced_output',
                'operation':'rejected unsafe source; nested-destination uses '+root+'/transport for index7; retain any actual partial'})
        for index in (9,13):package(index)
        writers(11);writers(15)
        for cache_index,sibling_index,node in ((11,12,'part-001.bin'),(15,16,None)):
            destination='literal-cache-'+str(cache_index)+'/worker38-synthetic-profile/allocations/worker38-synthetic-profile-01/transport-123-attempt-1'
            link=destination+'/'+node if node else destination
            add(link,str(prefix/('invented-sibling-'+str(sibling_index))).encode('ascii'),'symlink','after-production-rename')
            produced.append({'relative_path':'t01/invented-sibling-'+str(sibling_index),'lineage':'produced_output',
                'operation':'actual original '+('part moved' if node else 'whole package moved')+' before exact symlink replacement; bytes preserved at sibling'})
    elif case in ('T05','T06'):
        produced.append({'role':'no filesystem fixture payload','lineage':'produced_output',
            'source':'T05 fixed fstatvfs metadata boundaries; T06 _StubSeekableSink numeric positions and in-memory descriptors only',
            'literal_file_inputs':0,'no_large_buffer_materialization':True})
    elif case=='T07':
        for index in (1,3):
            add('prefix-source-'+str(index)+'/a',b'original')
            produced.append({'relative_path':'t01/prefix-output-'+str(index+1)+'/attempt.zip.partial','lineage':'produced_output',
                'source_fixed_prefix':'surviving partial archive','operation':'mocked archive writer emits prefix then raises original resource/IO error; retain output and failure receipt'})
    elif case=='T08':
        produced.append({'relative_roots':['t01/corrupt-readback-'+str(index) for index in range(3,11)],'lineage':'produced_output',
            'ordered_in_memory_manifest_variants':['missing','extra','duplicate','order','size','hash','limits','raw-order'],
            'operation':'consumes actual package with original finite descriptor changes; no source bytes changed'})
    elif case=='T10':
        produced.append({'relative_path':'t01/invented-provider-wrapper.zip-3','lineage':'produced_output',
            'operation':'actual native timestamped wrapper reused; caller removes receipt only after initial readback4; failure readback5'})
    elif case=='T11':
        produced.append({'relative_paths':['t01/invented-provider-wrapper.zip-'+str(i) for i in (3,5,7,9,11,13)],
            'lineage':'produced_output','ordered_wrapper_parameters':[{'member_name':'renamed.bin'},{'payload':'wrong'},{'extra':True},{'duplicate':True},{'empty':True},{}],
            'last_version_operation':'at wrapper13 retain actual bytes, mutate central header offset+24 to31457281, update actual receipt size/hash, consume in oversized-wrapper-payload14',
            'predecessor_boundary':'before-central-directory-size-mutation','predecessor_raw_required':True,
            'expected_hash_from_observation_forbidden':True,'all_versions_and_partials_charged':True})
    elif case=='T12':
        produced.append({'relative_path':'t01/invented-drive-download-3','lineage':'produced_output',
            'operation':'copy actual part once; first verify consumes it; retain raw predecessor before replacing with literal tampered bytes; second verify consumes replacement',
            'predecessor_boundary':'before-tampered-drive-download','predecessor_raw_required':True,'all_versions_and_partials_charged':True})
    elif case=='T13':
        produced.append({'relative_paths':['t01/invented-drive-download-'+str(i) for i in (3,4,5,6,8,9,10,11,12,13,14)]+['t01/download-hardlink-7'],
            'lineage':'produced_output','ordered_descriptor_variants':['missing-id','wrong-url','same-path','same-inode','old-download','missing-receipt','same-event','wrong-folder','incomplete','virtual_part1','virtual_part2'],
            'operation':'all downloads copy actual part; hardlink7 aliases original production upload part; metadata-only two virtual parts do not create30MiB fixtures'})
    elif case=='T14':
        produced.append({'relative_path':'t01/invented-drive-download-3','lineage':'produced_output','operation':'one unchanged actual part copy and custody verification'})
    elif case=='T15':
        add('mutable-source-1/a',b'before',phase='after-original-inventory-before-mutation')
        add('mutable-source-1/a',b'after!',phase='original_inventory returned then fixed callback mutation before archive read')
        produced.append({'relative_root':'t01/mutated-output-2','lineage':'produced_output','operation':'archive mutation rejection retains actual partial; pre-mutation input state captured in original bounded slot'})
    elif case=='T16':
        produced += [{'relative_root':'t01/io-failed-readback-3','lineage':'produced_output','operation':'raw first member nested/stub.bin receives retained-prefix then extraction raises'},
            {'relative_root':'t01/expired-4','lineage':'produced_output','operation':'expired deadline rejects before extraction'},
            {'relative_path':'t01/invented-drive-download-5','lineage':'produced_output','operation':'actual part copy before fixed readback-hash error'},
            {'relative_path':'t01/archive-body-memory.partial-6','lineage':'produced_output','operation':'actual archive stage may retain partial before body MemoryError plus final fsync error; charge prefix'}]
    elif case!='T09':raise ClosurePrerequisite('transport selector outside closedT01-16')
    return inputs,produced


# Independently source-inspected supplement SHA256 1d264c4c831bf308a69bfbe06c9cfe86630181acbc9850ffea807c48a88118a3
# SOURCE TEXT ONLY. Requires p07_receipt_raw/p07_closing_raw from revision01.
# Return explicit ordered literal states; do not execute this artifact here.
# All paths below are relative to the selector's t01. Production mutations are
# separate records; no observed output contributes an expected literal byte.

def p07_ordered_extra_states(ctx, row):
    label = row['selector'].split('.test_',1)[1]
    case = label.split('_',1)[0]
    states = []
    operations = []
    def add(path,raw,reason,kind='file'):
        states.append({'relative_path':'t01/'+path,'kind':kind,'raw':raw,
            'lineage':'independent_literal_input','recipe':reason,'ordered_literal_state':len(states)+1})
    def receipt(prefix,status='execution_complete',now=1000.0):
        raw = p07_receipt_raw(status)
        add(prefix+'/receipt.json',raw,'original make_receipt('+status+')')
        if status=='execution_complete':
            add(prefix+'/measurement-phase-close.json',p07_closing_raw(raw,now),
                'original make_receipt calls closing proof at mocked'+repr(now))
        return raw
    def close(prefix,raw,now,started,deadline):
        add(prefix+'/measurement-phase-close.json',p07_closing_raw(raw,now,
            {'preservation_started_monotonic':started,'preservation_deadline_monotonic':deadline}),
            'ordered explicit closing-proof overwrite with independently derived receipt pin')
    def missing(path,reason):
        add(path,None,reason,kind='missing')
    if case=='D04':
        add('attempt/cells/01/cell-receipt.json',b'{torn','first exact torn record')
        add('attempt/cells/01/candidate-capture-confirmed.json',b'{torn','second exact torn record')
    elif case=='D06':
        add('attempt/cells/01/candidate-start.json',canonical({'literal':'pre-call marker'}),'first reconcile sees exact marker')
        add('attempt/cells/01/cell-receipt.json',canonical({'calls':{'candidate':{
            'invocation_attempted':False,'method_entered':False,'returned':False}}}),'second reconcile negative call flags')
        add('attempt/cells/01/candidate-start.json',b'{partial','overwrite marker before second reconcile')
    elif case=='D08':
        add('attempt/receipt.json',b'bad original','overwrite original literal receipt; closing proof retains original receipt digest')
    elif case=='D11':
        original = b'# fixed source stub\n'
        add('repo/literal.py',original,'original fixed source bytes')
        value = {'success':True,'failures':0,'errors':0,'candidate_evaluator_calls':0,'reference_evaluator_calls':0,
            'games':0,'measurement_fixture_constructions':0,'historical_source_imports':0,
            'checked_file_sha256':{'literal.py':sha(original)}}
        add('repo/experiments/worker38-synthetic-profile/focused-preparation-receipt.json',canonical(value),
            'independent checked receipt binds original literal.py; wrong supplied pin0*64 changes argument only')
        add('repo/literal.py',b'# changed\n','third verification sees modified source with same retained receipt')
    elif case=='D15':
        add('attempt/receipt.json',p07_receipt_raw('measuring'),'phase=measurement and completed_prefix=[] update repeats identical bytes')
    elif case=='D16':
        value = {'status':'integrity_invalid','failure':{'status':'integrity_invalid','category':'integrity',
            'error_type':'IntegrityError','error':'surviving child mismatch','phase':'cell_measurement'},'calls':{}}
        add('attempt/failure-receipt-cell-01.json',canonical(value),'literal preserved child sidecar before preserve')
    elif case=='D17':
        add('attempt/cells/01/candidate-start.json',canonical({'literal':'marker'}),'exact marker; both Path.open faults leave bytes unchanged')
    elif case=='D18':
        missing('attempt/cells/01/candidate-start.json','first lstat fault has no actual start-marker file')
        raw = canonical({'literal':'return'})
        add('attempt/cells/01/candidate-return.json',raw,'second phase literal return')
        add('attempt/cells/01/candidate-capture-confirmed.json',canonical({'path':'cells/01/candidate-return.json',
            'size_bytes':len(raw),'sha256':sha(raw)}),
            'independent Budget.write return includes path/size/hash; later mocked stat fault leaves bytes unchanged')
    elif case=='D19':
        add('attempt/cells/01/cell-receipt.json',canonical({'calls':{'candidate':{'returned':True,'method_entered':True}}}),
            'first cell partial literal evidence')
        value = {'status':'execution_blocked','failure':{'status':'execution_blocked','category':'preflight',
            'error_type':'PermissionError','error':'later prerequisite unavailable','phase':'cell_source_runtime_preflight'},'calls':{}}
        add('attempt/cells/02/cell-receipt.json',canonical(value),'second cell literal preflight failure')
    elif case=='D27':
        valid = {'status':'integrity_invalid','category':'integrity','error_type':'IntegrityError',
            'error':'literal mismatch','phase':'measurement'}
        values = [{'status':value} for value in ([],{},True,1,'unknown')]
        values.extend(({'status':'execution_incomplete','failure':[]},
            {'status':'execution_incomplete','failure':{'status':[]}},
            {'status':'resource_incomplete','failure':valid}))
        for index,value in enumerate(values):
            add('attempt/supervisor-cell-01.json',canonical(value),'ordered malformed supervisor variant'+str(index))
            operations.append({'after_literal_state':len(states),'operation':'actual terminalize receipt mutation remains produced_output'})
    elif case=='D22':
        add('attempt/supervisor-cell-01.json',canonical({'status':'execution_incomplete','exit_code':65,'reason':'typed exit'}),
            'literal supervisor typed-exit record')
        add('attempt/failure-receipt-parent-1.json',canonical({'status':'integrity_invalid','failure':{
            'status':'integrity_invalid','category':'integrity','error_type':'IntegrityError',
            'error':'earlier parent mismatch','phase':'measurement'}}),'literal retained parent sidecar')
    elif case=='D29':
        add('attempt/cells/01/candidate-start.json.tmp',b'{partial','same retained uncommitted bytes across both reducer cases')
    elif case=='D30':
        raw = canonical({'literal':'return'})
        add('attempt/cells/01/candidate-return.json',raw,'literal return survives three read failures')
        add('attempt/cells/01/candidate-capture-confirmed.json',canonical({'path':'cells/01/candidate-return.json',
            'size_bytes':len(raw),'sha256':sha(raw)}),'last phase explicitly includes path with independently calculated file size/hash')
    elif case=='D46':
        missing('attempt/measurement-phase-close.json','remove proof after first closing_phase call; source order preserves first use')
    elif case=='D48':
        add('attempt/receipt.json',b'{committed malformed receipt','proof keeps original independent receipt hash after receipt mutation')
    elif case=='D49':
        root = ''
        for index,fault in enumerate(('denied','malformed')):
            root += ('/' if root else '')+'anchor-'+str(index)
            receipt(root+'/attempt')
            if fault=='malformed':
                add(root+'/attempt/measurement-phase-close.json',b'{bad closing proof','second cumulative-root variant malformed anchor')
            operations.append({'root':root,'read_fault':fault,'clock':1000.0})
    elif case=='D50':
        root = ''
        for index,(prior,starts) in enumerate(((None,0),(None,2),('integrity_invalid',2),('resource_incomplete',2))):
            root += ('/' if root else '')+'storage-'+str(index)
            prefix = root+'/attempt'
            initial = receipt(prefix)
            value = json.loads(initial)
            value['actual_starts'] = starts
            if prior is not None:
                value['status'] = prior
                value['failure'] = {'status':prior,'category':'literal_prior','phase':'measurement',
                    'error_type':'LiteralPriorFailure','error':'fixed earlier cause'}
            raw = canonical(value)
            add(prefix+'/receipt.json',raw,'ordered literal prior/start mutation'+str(index))
            add(prefix+'/measurement-phase-close.json',p07_closing_raw(raw,1000.0),
                'refresh closing proof after literal receipt mutation, before actual preservation')
    elif case=='D51':
        root = ''
        for index,age in enumerate((701,10)):
            root += ('/' if root else '')+'staged-'+str(index)
            prefix = root+'/attempt';raw = receipt(prefix)
            started = 1000.0-age
            close(prefix,raw,1000.0,started,started+600)
            staged = p07_closing_raw(raw,1000.0,{'preservation_started_monotonic':started,
                'preservation_deadline_monotonic':started+600})
            add(prefix+'/measurement-phase-close.json.tmp',staged,'rename exact latest complete anchor to staging')
            missing(prefix+'/measurement-phase-close.json','original final path absent after rename')
    elif case=='D52':
        root = ''
        for index,kind in enumerate(('complete','terminalized','missing-receipt')):
            root += ('/' if root else '')+'missing-'+str(index)
            prefix = root+'/attempt';receipt(prefix)
            missing(prefix+'/measurement-phase-close.json','explicit deletion in every variant')
            if kind=='missing-receipt':
                missing(prefix+'/receipt.json','third branch explicitly removes receipt')
            elif kind=='terminalized':
                operations.append({'path':prefix+'/receipt.json','operation':'actual terminalize with OSError(later restoration failure), phase coordinator_timer_restoration; produced_output'})
            add(prefix+'/fixed-prefix.bin',b'literal surviving evidence','retained prefix exact literal')
    elif case=='D53':
        root = ''
        for index,kind in enumerate(('torn','future')):
            root += ('/' if root else '')+'uncertain-'+str(index)
            prefix = root+'/attempt';raw = receipt(prefix)
            staged = p07_closing_raw(raw,1000.0)
            if kind=='future':
                close(prefix,raw,1000.0,1100.0,1700.0)
                staged = p07_closing_raw(raw,1000.0,{'preservation_started_monotonic':1100.0,'preservation_deadline_monotonic':1700.0})
            add(prefix+'/measurement-phase-close.json.tmp',staged,'rename latest anchor to staging before optional torn overwrite')
            missing(prefix+'/measurement-phase-close.json','final path absent after rename')
            if kind=='torn':
                add(prefix+'/measurement-phase-close.json.tmp',b'{uncommitted partial anchor','exact torn staged overwrite')
    elif case=='D54':
        root = ''
        for index,(status,phase,staging) in enumerate((('execution_blocked','admission',False),
                ('measuring','measurement',False),('measuring','measurement',True))):
            root += ('/' if root else '')+'preclosing-'+str(index)
            prefix=root+'/attempt';initial=receipt(prefix,status)
            value=json.loads(initial);value.update(phase=phase,completed_prefix=[])
            add(prefix+'/receipt.json',canonical(value),'ordered exact preclosing phase mutation')
            if status=='measuring':
                operations.append({'path':prefix+'/receipt.json','operation':'actual terminalize with OSError(partial cell unavailable), phase measurement; produced_output'})
            if staging:
                add(prefix+'/receipt.json.tmp',b'{possible computational publication','fixed possible-completion staging prefix')
    elif case=='R1D02':
        add('github-output',b'','initial exact empty handoff destination; later appends remain produced_output')
    elif case=='R1D03':
        for index,kind in enumerate(('absent','relative','symlink','partial','write_error','fsync_error')):
            add('github-output-'+str(index),b'','initial empty handoff destination '+kind)
            if kind=='symlink':
                target=str(case_root(ctx,row['ordinal'])/'t01'/'github-output-2').encode('utf-8')
                add('github-output-link',target,'exact absolute-root negative symlink target; no traversal','symlink')
            operations.append({'path':'github-output-'+str(index),'operation':'actual publish_preservation_handoff1500.0; '+kind+' fault; any complete/partial append is produced_output'})
    elif case=='R1D04':
        for index in range(7):
            receipt('attempt-incoming-'+str(index),'measuring')
    elif case=='R1D05':
        root=''
        for index,(staged,deadline,terminal) in enumerate(((False,1500.0,False),(True,1500.0,True),
                (False,1700.0,True),(True,1700.0,False))):
            root+=('/' if root else '')+'clamp-'+str(index)
            prefix=root+'/attempt';raw=receipt(prefix,now=1100.0)
            close(prefix,raw,1100.0,deadline-600,deadline)
            if staged:
                add(prefix+'/measurement-phase-close.json.tmp',p07_closing_raw(raw,1100.0,
                    {'preservation_started_monotonic':deadline-600,'preservation_deadline_monotonic':deadline}),
                    'exact complete staged anchor after rename')
                missing(prefix+'/measurement-phase-close.json','final absent after rename')
            if terminal:
                operations.append({'path':prefix+'/receipt.json','operation':'actual terminalize IntegrityError(prior fixed mismatch), phase measurement; produced_output'})
    elif case=='R1D10':
        receipt('attempt-arm-shorter_anchor',now=400.0)
    elif case=='R1D13':
        for name in ('disable_before','handler_before','disable_after_memory','handler_after_memory',
                'disable_mismatch','handler_mismatch','disable_getter','handler_getter'):
            receipt('attempt-offline-'+name,'measuring')
    elif case=='R1D14':
        receipt('attempt-handler-offline','measuring')
    elif case=='R1D15':
        root=''
        for name in ('incoming_expired','verification_expired','second-retain'):
            root+=('/' if root else '')+name
            receipt(root+'/attempt',now=1000.0)
    return {'selector':row['selector'],'ordered_literal_states':states,'produced_operations':operations,
        'scope':'Supplement revision01; this does not by itself certify complete invocation/state/path joins',
        'unresolved':['ER_I01/ER_I02 authenticated metadata join remains owned with P03' ] if label.startswith('ER_') else []}


def derive_P07_revision02(ctx):
    # This explicit family join supplies source recipes only. No statement
    # below is authority to materialize, certify reservations, or execute tests.
    result = derive_P07(ctx)
    by_selector = {row['selector']:row for row in ctx['rows'] if 'P07' in row['family_ids']}
    covered = tuple('D%02d' % number for number in range(1,55)) + tuple('R1D%02d' % number for number in range(1,17))
    for item in result['selector_results']:
        row = by_selector[item['selector']]
        label = row['selector'].split('.test_',1)[1]
        case = label.split('_',1)[0]
        extra = p07_ordered_extra_states(ctx,row)
        item['inputs'].extend(extra['ordered_literal_states'])
        item['produced'].extend(extra['produced_operations'])
        if case in covered:
            item['unresolved'] = []
            item['recipe_status'] = 'FAMILY_LOCAL_SOURCE_OPERATIONS_SPECIFIED_NOT_EXECUTED_OR_CERTIFIED'
        item['source_join_requirements'] = [
            'Preserve all source-written input versions in listed original order; materialization remains separately gated',
            'Bind final family operations to collector exact observed path/type/version roles; no broad allowed-state replacement',
            'All actual terminalize/reconcile/child/report/package outputs retain produced_output lineage',
            'Keep existing11 Driver pre-overwrite captures; no new slot or version capture is authorized',
            'R1D07 uses original literal supervisor harness pipe prefix and1000.0->1900.0->2601.0 clock domains; parent and output PID fields remain produced observations',
            'P01/P15 source/native/namespace and complete finite original-order reservation proofs remain required']
    return result


# Independently source-inspected supplement SHA256 5bc780f486e87a4c1885a255fad230bcbfe0321fbf8acf77c18a0176b6cd7aad
# SOURCE TEXT ONLY. Explicit source recipe joins to the independent P03/P08
# constructors in the sole authorized program. Never execute this artifact here.

def p07_authenticated_metadata_states(ctx, row):
    method = row['selector'].rsplit('.',1)[-1]
    if method not in ('test_ER_I01_consumed_reservation_survives_prerequisite_failure',
            'test_ER_I02_consumed_reservation_survives_seven_input_tamper'):
        raise ValueError('closed ER metadata selector required')
    root = case_root(ctx,row['ordinal'])/'t01'
    repo = root/'metadata-shared-checkout'
    experiment = 'experiments/worker38-synthetic-profile/'
    receipt_name = experiment+'focused-preparation-receipt.json'
    metadata = tuple(experiment+name for name in ('PROTOCOL.md','INTEGRATION-CONTRACT.json',
        'FINITE-PREPARATION-PLAN.json','SOURCE-GROUNDING.json','comparator-source-manifest.json',
        'upload-amendment/AMENDMENT.md','upload-amendment/AMENDMENT-CONTRACT.json',
        'upload-amendment/FINITE-COVERAGE-AMENDMENT.json','upload-amendment/SOURCE-OBSERVATION.json',
        'upload-amendment/REPAIR-DISPOSITION.json','upload-amendment/HANDOFF.json'))
    production = source_literal(ctx,'scripts/worker38/admission.py','REQUIRED_PRODUCTION_PATHS')
    tests = ('tests/test_worker37_bootstrap.py','tests/worker38_literal_fixtures.py',
        'tests/worker38_constructor_source.txt','tests/test_worker38_bootstrap_integration.py',
        'tests/test_worker38_core.py','tests/test_worker38_driver_integration.py',
        'tests/test_worker38_cell_integration.py','tests/test_worker38_supervision.py',
        'tests/test_worker38_transport.py','tests/test_worker38_verify_integration.py',
        'evidence-design/run-worker38-fixed-preparation.py','evidence-design/worker38-fixed-fixtures.json')
    manifest = json.loads(ctx['source_bytes'][experiment+'comparator-source-manifest.json'])
    if len(manifest['files']) != 21:
        raise ValueError('ER checked-source21-member manifest changed')
    blobs = tuple(experiment+'inputs/comparator-7ac2f62c/'+entry['path']+'.blob' for entry in manifest['files'])
    diagnostics = set(production) | set(metadata) | set(blobs)
    checked_names = diagnostics | set(tests)
    shared = {name:b'# fixed invented checked-source metadata only\n' for name in sorted(checked_names)}
    shared.update({name:ctx['source_bytes'][name] for name in metadata})
    checked = {name:sha(shared[name]) for name in sorted(checked_names)}
    test_record = {'success':True,'failures':0,'errors':0,'candidate_evaluator_calls':0,
        'reference_evaluator_calls':0,'games':0,'measurement_fixture_constructions':0,
        'historical_source_imports':0,'checked_file_sha256':checked,
        'literal_fixture':'invented metadata receipt; no measurement authority'}
    receipt_raw = canonical(test_record)
    shared[receipt_name] = receipt_raw
    shared['.git/HEAD'] = ('1'*40+'\n').encode('ascii')
    result = {'selector':row['selector'],'ordinal':row['ordinal'],'inputs':[],'produced':[],
        'unresolved':[],'source_case_order':[]}
    def add(path,raw,reason,kind='file',mode=None):
        value={'relative_path':str(path.relative_to(case_root(ctx,row['ordinal']))),'kind':kind,'raw':raw,
            'lineage':'independent_literal_input','recipe':reason,'ordered_literal_state':len(result['inputs'])+1}
        if mode is not None:value['mode']=mode
        result['inputs'].append(value)
    for name,raw in shared.items():
        add(repo/name,raw,'fixed_authenticated_metadata creates shared checkout once, then chmods each file0400',mode=0o400)
    input_names = ('pull-request.json','postmerge-ci.json','current-source-ci.json','review-exhaustive.json',
        'review-adversarial.json','preregistration.json','diagnostic-commit.json')
    if method.startswith('test_ER_I01_'):
        cases = [('valid',None)] + [(name,'missing') for name in input_names] + [('source_map','stale'),('receipt_size','stale')]
    else:
        cases = [('tamper-'+name,'tamper') for name in input_names]
    for label,kind in cases:
        result['source_case_order'].append(label)
        base = root/('metadata-'+label)
        cache = base/'tool-cache'
        temporary = base/'runner-temp'
        auth_path = base/'auth'
        admitted = dict(checked)
        receipt_pin = {'path':receipt_name,'size_bytes':len(receipt_raw),'sha256':sha(receipt_raw)}
        if label=='source_map':admitted['tests/fixed-obsolete-source.py']='f'*64
        if label=='receipt_size':receipt_pin['size_bytes']+=1
        go = {'preregistration_url':source_literal(ctx,'scripts/worker38/common.py','PREREGISTRATION'),
            'upload_amendment_sha256':source_literal(ctx,'scripts/worker38/common.py','UPLOAD_AMENDMENT_SHA256'),
            'upload_contract_sha256':source_literal(ctx,'scripts/worker38/common.py','UPLOAD_CONTRACT_SHA256'),
            'upload_finite_plan_sha256':source_literal(ctx,'scripts/worker38/common.py','UPLOAD_FINITE_PLAN_SHA256'),
            'upload_adoption_comment_id':source_literal(ctx,'scripts/worker38/common.py','UPLOAD_ADOPTION'),
            'diagnostic_files_sha256':{name:checked[name] for name in sorted(diagnostics)},
            'checked_file_sha256':admitted,'focused_source_receipt':receipt_pin,'stub_test_receipt_sha256':sha(receipt_raw)}
        bundle = independent_auth_bundle(go,cache=str(cache),focused_source_receipt=receipt_pin,
            checked_file_sha256=admitted,workflow_run='9001')
        bundle['context'].update(checkout_path=str(repo),runner_temp=str(temporary))
        proof = independent_auth_proof(bundle)
        payloads = {'event.json':canonical(bundle['event']),'request-context.json':canonical(bundle['context']),
            **bundle['inputs'],'admission.json':bundle['admission_raw'],'provenance.json':canonical(proof)}
        for name,raw in payloads.items():
            add(auth_path/name,raw,'P03 independent authenticated original for exact ER variant '+label)
        attempt = cache/'worker38-synthetic-profile/allocations/worker38-synthetic-profile-01/run-9001-attempt-1'
        startup = p07_startup_files(ctx,absolute_root=root,attempt_name=str(attempt.relative_to(root)),
            claim_name=str(attempt.parent.relative_to(root)),now=1000.0,auth_files=payloads,
            go=bundle['go'],workflow_run='9001',source_path=repo)
        for name,raw in startup.items():
            add(root/name,raw,'ER original consumed startup copy precedes '+str(kind)+' mutation')
        if kind=='missing':
            add(auth_path/label,None,'ER_I01 unlink exact selected auth input; retained admission-inputs copy stays original',kind='missing')
        elif kind=='tamper':
            name=label.removeprefix('tamper-')
            add(auth_path/name,payloads[name]+b'\n','ER_I02 append one newline after startup copy; provenance and retained original are unchanged')
        result['produced'].append({'case':label,'role':'actual metadata-only measure receipt/failure sidecars',
            'lineage':'produced_output','source':'runtime passes then fixed disk_usage OSError, or exact missing/stale/tampered authenticated prerequisite rejects',
            'no_overwrite':'shared checkout0400 files remain unchanged; each auth/attempt/cache variant has unique path; original consumed reservation retained',
            'reservation_reference':'existing ER_I01ten/ER_I02seven case path unions; no new cap or source path'})
    return result


def p04_f07_moved_cohort_states(ctx, row):
    if row['selector'].rsplit('.',1)[-1] != 'test_F07_complete_literal_20_cell_orchestration':
        raise ValueError('closed F07 selector required')
    plan = VerifierRecipe(ctx,row,f07=True)
    case = case_root(ctx,row['ordinal'])
    pending = case/'t01'/'complete-pending'
    target = plan.root
    original_files = dict(plan.files)
    inputs = []
    moves = []
    def add(absolute,raw,reason,kind='file'):
        inputs.append({'relative_path':str(absolute.relative_to(case)),'kind':kind,'raw':raw,
            'lineage':'independent_literal_input','recipe':reason,'ordered_literal_state':len(inputs)+1})
    for path,raw in sorted(original_files.items()):
        add(type(case)(path),raw,'P08 independently derived original F07 cohort before any move')
    names = ['cells','receipt.json','source-runtime-preflight.json','measurement-phase-close.json',
        'coordinator-restoration.json','external-admission.json','stub-test-receipt.json','writer-exit-observation.json']
    names += ['supervisor-cell-%02d.%s' % (index,suffix) for index in range(1,21) for suffix in ('json','log')]
    moved = {}
    for name in names:
        prefix = str(target/name)
        selected = [(path,raw) for path,raw in original_files.items() if path==prefix or path.startswith(prefix+'/')]
        for path,raw in sorted(selected):
            relative = type(case)(path).relative_to(target)
            destination = pending/relative
            moved[str(destination)] = raw
            add(destination,raw,'original cohort rename target->complete-pending; byte identity retained')
            add(type(case)(path),None,'original source filename absent immediately after move',kind='missing')
        moves.append({'order':len(moves)+1,'operation':'rename_original_cohort','source':prefix,'destination':str(pending/name),
            'independent_file_count':len(selected),'no_copy':True})
    # prepare_startup sees existing target/startup-handoff.json and returns.
    # It does NOT rewrite baseline runtime/handoff/source/admission copies.
    for index in range(1,21):
        folder = pending/'cells'/('%02d' % index)
        for path,raw in sorted(moved.items()):
            if path.startswith(str(folder)+'/'):
                destination = target/type(case)(path).relative_to(pending)
                add(destination,raw,'cell'+str(index)+' source record renamed back once before supervisor result consumption')
                add(type(case)(path),None,'pending cell source absent after original move',kind='missing')
        name='supervisor-cell-%02d.log' % index
        add(target/name,moved[str(pending/name)],'original per-cell supervisor log renamed back once')
        add(pending/name,None,'pending log absent after rename',kind='missing')
        moves.append({'order':len(moves)+1,'operation':'consume_cell_and_log','cell':index,
            'source_folder':str(folder),'target_folder':str(target/'cells'/('%02d'%index)),
            'supervisor_result_read':str(pending/('supervisor-cell-%02d.json'%index)),
            'now_after_return':9340.0+30.0*index,'fixed_guard_pid':1000,'fixed_start_ticks':934000})
    return {'selector':row['selector'],'ordinal':row['ordinal'],'inputs':inputs,'ordered_moves':moves,'unresolved':[],
        'produced':[{'role':'actual Driver measurement/terminal/preservation/package/provider-copy/custody output',
            'lineage':'produced_output','raw_expected':None,
            'reservation_reference':'existing complete F07 v4 union; no new slot/capture/cap',
            'startup_short_circuit':'target handoff already exists; prepare_startup returns before any baseline overwrite',
            'source_clock_sequence':'9340.0; then9340.0+30.0*index for1..20; actual preservation observation9941.0 and cutoff10540.0',
            'remaining_pending_inputs':'receipt/source-runtime/close/restoration/external-admission/stub-receipt/writer-exit and20 supervisor json originals remain under pending; only cell contents and20logs are moved back',
            'output_anchors':'actual computational receipt/close raw retained and compared unchanged after verify/custody/timing; never used to create their own expected input hash'}]}


def derive_P07_revision03(ctx):
    result = derive_P07_revision02(ctx)
    rows = {row['selector']:row for row in ctx['rows'] if 'P07' in row['family_ids']}
    for item in result['selector_results']:
        if '.test_ER_I01_' in item['selector'] or '.test_ER_I02_' in item['selector']:
            extra = p07_authenticated_metadata_states(ctx,rows[item['selector']])
            item['inputs'].extend(extra['inputs'])
            item['produced'].extend(extra['produced'])
            item['source_case_order'] = extra['source_case_order']
            item['unresolved'] = []
            item['recipe_status'] = 'FAMILY_LOCAL_SOURCE_OPERATIONS_SPECIFIED_NOT_EXECUTED_OR_CERTIFIED'
    return result


def derive_P04_revision03(ctx):
    result = derive_P04(ctx)
    rows = {row['selector']:row for row in ctx['rows'] if 'P04' in row['family_ids']}
    for item in result['selector_results']:
        if item['selector'].endswith('.test_F07_complete_literal_20_cell_orchestration'):
            extra = p04_f07_moved_cohort_states(ctx,rows[item['selector']])
            item['inputs'].extend(extra['inputs'])
            item['produced'].extend(extra['produced'])
            item['ordered_moves'] = extra['ordered_moves']
            item['unresolved'] = []
            item['recipe_status'] = 'FAMILY_LOCAL_SOURCE_OPERATIONS_SPECIFIED_NOT_EXECUTED_OR_CERTIFIED'
    return result

FAMILY_DISPATCH['P04']=derive_P04_revision03
FAMILY_DISPATCH['P07']=derive_P07_revision03


# Fixed source-pairing fragment SHA256 3c599c5334191791452675da222c581dc6ce2ae46d58cd80c7c013a7a5ae2bcb
# P01 fixed source pairing supplement. Source-only authoring; not run or imported.
# Inline into the one authorized recipe source; never load this fragment dynamically.
_P01_SUPERVISION_SOURCE = 'tests/test_worker38_supervision.py'
_P01_SUPERVISION_SHA256 = 'efae3f68684d1c1456c1e2fec90e84ebdede16e47feae60dd07e0a277c8545a1'
_P01_STUB_PROGRAMS = ((276, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_S01_zero_exit_records_process_only', ("print('invented stdout', flush=True)\nprint('invented stderr', file=sys.stderr, flush=True)",)), (277, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_S02_nonzero_and_signal_are_explicit', ("print('prefix', flush=True)\nsys.exit(7)", "print('prefix', flush=True)\nos.kill(os.getpid(), signal.SIGKILL)")), (278, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_S03_whole_cell_wall_works_without_state', ('bounded_sleep(30)',)), (279, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_S04_active_hang_with_profiles_suppressed', ('activate()\nsys.setprofile = lambda hook: None\nbounded_sleep(30)',)), (280, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_S05_live_cpu_not_just_reaped_children', ('activate()\nsys.setprofile = lambda hook: None\nwhile within_lifetime(): pass',)), (281, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_S06_whole_cell_cpu_without_state', ('while within_lifetime(): pass',)), (282, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_S07_phase_wall_blocks_or_terminates', ("raise AssertionError('must not spawn')", 'bounded_sleep(30)')), (283, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_S08_phase_parent_reaped_live_terms', ('pass', 'stop = time.process_time() + 0.08\nwhile time.process_time() < stop and within_lifetime(): pass', 'while within_lifetime(): pass')), (284, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_S09_term_ignoring_escaped_descendant_is_killed', ('\npid = os.fork()\nif pid == 0:\n    arm_same_lifetime()\n    os.setsid()\n    signal.signal(signal.SIGTERM, signal.SIG_IGN)\n    Path("descendant.pid").write_text(str(os.getpid()))\n    while within_lifetime(): bounded_sleep(1)\nelse:\n    while within_lifetime(): bounded_sleep(1)\n',)), (285, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_S10_child_exit_leaving_descendant_is_incomplete', ('\npid = os.fork()\nif pid == 0:\n    arm_same_lifetime()\n    Path("descendant.pid").write_text(str(os.getpid()))\n    while within_lifetime(): bounded_sleep(1)\nelse:\n    while not Path("descendant.pid").exists(): bounded_sleep(0.005)\n    os._exit(0)\n',)), (286, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_S11_exact_address_space_and_inherited_limits', ("print(json.dumps({'as': resource.getrlimit(resource.RLIMIT_AS), 'pid': os.getpid(), 'pgid': os.getpgrp(), 'sid': os.getsid(0)}))", 'pass', 'pass')), (287, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_S12_proc_or_subreaper_unavailable_blocks_spawn', ('pass', 'pass')), (288, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_S13_output_overflow_preserves_bounded_prefix', ("os.write(1, b'x' * 8192)\nbounded_sleep(30)", "print('bytes', flush=True)\nbounded_sleep(30)", "print('guarded prefix', flush=True)")), (289, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_S14_malformed_state_variants_fail_closed', ("state_path.write_text('{')\nbounded_sleep(30)", "state_path.write_text('x' * 17000)\nbounded_sleep(30)", 'state_path.write_text(\'{"active": true, "scope": "candidate", "wall_started": NaN, "cpu_started": 0}\')\nbounded_sleep(30)', "mark({'active': True, 'scope': 'candidate', 'wall_started': time.monotonic() + 100, 'cpu_started': 0})\nbounded_sleep(30)", "mark({'active': True, 'scope': 'candidate', 'wall_started': time.monotonic(), 'cpu_started': 1000000})\nbounded_sleep(30)", "Path('target').write_text('{}'); state_path.symlink_to('target')\nbounded_sleep(30)", "activate(); time.sleep(0.1);\n_capture_directory = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)\ntry:\n    _capture_source = os.open('call-state.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,\n                              dir_fd=_capture_directory)\n    try:\n        _capture_before = os.fstat(_capture_source)\n        if (_capture_before.st_mode & 0o170000 != 0o100000 or _capture_before.st_nlink != 1 or\n                not 0 < _capture_before.st_size <= 137):\n            raise RuntimeError('predecessor source is outside its fixed domain')\n        _capture_raw = os.read(_capture_source, 138)\n        if len(_capture_raw) != _capture_before.st_size or os.read(_capture_source, 1):\n            raise RuntimeError('predecessor source read is incomplete')\n        _capture_after = os.fstat(_capture_source)\n        _capture_named = os.stat('call-state.json', dir_fd=_capture_directory, follow_symlinks=False)\n        if any(getattr(_capture_before, key) != getattr(observed, key)\n               for observed in (_capture_after, _capture_named)\n               for key in ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_nlink')):\n            raise RuntimeError('predecessor source changed while read')\n    finally:\n        os.close(_capture_source)\n    _capture_copy = os.open('call-state.predecessor', os.O_WRONLY | os.O_CREAT | os.O_EXCL |\n                            os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=_capture_directory)\n    try:\n        if os.write(_capture_copy, _capture_raw) != len(_capture_raw):\n            raise RuntimeError('predecessor write is incomplete')\n        os.fsync(_capture_copy)\n    finally:\n        os.close(_capture_copy)\n    os.fsync(_capture_directory)\nfinally:\n    os.close(_capture_directory)\nactivate()\nbounded_sleep(30)")), (290, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_S15_valid_transition_and_admission_rejections', ("activate()\ntime.sleep(0.06)\n_capture_directory = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)\ntry:\n    _capture_source = os.open('call-state.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,\n                              dir_fd=_capture_directory)\n    try:\n        _capture_before = os.fstat(_capture_source)\n        if (_capture_before.st_mode & 0o170000 != 0o100000 or _capture_before.st_nlink != 1 or\n                not 0 < _capture_before.st_size <= 137):\n            raise RuntimeError('predecessor source is outside its fixed domain')\n        _capture_raw = os.read(_capture_source, 138)\n        if len(_capture_raw) != _capture_before.st_size or os.read(_capture_source, 1):\n            raise RuntimeError('predecessor source read is incomplete')\n        _capture_after = os.fstat(_capture_source)\n        _capture_named = os.stat('call-state.json', dir_fd=_capture_directory, follow_symlinks=False)\n        if any(getattr(_capture_before, key) != getattr(observed, key)\n               for observed in (_capture_after, _capture_named)\n               for key in ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_nlink')):\n            raise RuntimeError('predecessor source changed while read')\n    finally:\n        os.close(_capture_source)\n    _capture_copy = os.open('call-state.predecessor', os.O_WRONLY | os.O_CREAT | os.O_EXCL |\n                            os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=_capture_directory)\n    try:\n        if os.write(_capture_copy, _capture_raw) != len(_capture_raw):\n            raise RuntimeError('predecessor write is incomplete')\n        os.fsync(_capture_copy)\n    finally:\n        os.close(_capture_copy)\n    os.fsync(_capture_directory)\nfinally:\n    os.close(_capture_directory)\nmark({'active': False})\ntime.sleep(0.06)", 'pass', 'pass', 'pass', 'pass', 'pass', 'pass', 'pass')), (291, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_S16_injected_io_spawn_observation_and_cleanup_failures', ('pass', 'bounded_sleep(30)', "print('prefix', flush=True)", 'bounded_sleep(30)', 'bounded_sleep(30)')), (292, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_P2_02_resource_survives_subreaper_restoration_failure', ('bounded_sleep(30)',)), (293, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_P2_03_resource_survives_deferred_log_failure', ("print('retained in memory', flush=True)\nbounded_sleep(30)",)), (294, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_P2_04_zero_exit_with_restoration_failure_is_not_completed', ('pass',)), (295, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_P2_05_final_output_budget_keeps_primary_zero_exit', ("print('invented raw prefix', flush=True)",)), (297, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_F4_01_postspawn_memory_is_resource', ('bounded_sleep(30)',)), (298, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_F4_02_secondary_memory_phases_preserve_exit', ("print('invented prefix', flush=True)", "print('invented prefix', flush=True)", "print('invented prefix', flush=True)", "print('invented prefix', flush=True)")), (299, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_F4_03_exit65_survives_resource_accounting_faults', ('sys.exit(65)', 'sys.exit(65)', 'sys.exit(65)')), (301, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_F4_05_unavailable_observations_are_not_corruption', ('bounded_sleep(30)', 'bounded_sleep(30)')), (302, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_F4_06_marker_corruption_dominates_cleanup_memory', ("mark({'active': 'invalid'})\nbounded_sleep(30)",)), (305, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_S30_timeout_handler_diagnostic_is_preserved', ("\ndef on_term(signum, frame):\n    os.write(1, b'SIGTERM diagnostic\\n')\n    os._exit(0)\nsignal.signal(signal.SIGTERM, on_term)\nos.write(1, b'start\\n')\nwhile within_lifetime():\n    bounded_sleep(1)\n",)), (306, 'tests/test_worker38_supervision.py:SupervisionStubTests.test_S31_timeout_handler_respects_original_output_cap', ("\ndef on_term(signum, frame):\n    os.write(1, b'terminated:' + b'x' * 128 + b'\\n')\n    os._exit(0)\nsignal.signal(signal.SIGTERM, on_term)\nos.write(1, b'start\\n')\nwhile within_lifetime():\n    bounded_sleep(1)\n",)))

_P01_COMMAND_NAMES = ('realpath','readlink','stat','id','mkdir','cat','sync','sha256sum','git','timeout')
_P01_LEGACY_COPY_NAMES = ('worker37-bootstrap.sh','worker37_bootstrap.py','worker_bootstrap_shared.sh','worker_bootstrap_shared.py')

def derive_P01_pairing(ctx):
    """Supplement exact setup paths; no observed-output oracle or helper evaluation."""
    if sha(ctx['source_bytes'][_P01_SUPERVISION_SOURCE]) != _P01_SUPERVISION_SHA256:
        raise ClosurePrerequisite('P01 final supervision source changed; re-review exact literal programs')
    registered = {row['ordinal']:row for row in ctx['rows']}
    results = {}
    def result_for(ordinal):
        row = registered[ordinal]
        if 'P01' not in row['family_ids']:
            raise ClosurePrerequisite('P01 family pairing changed')
        return results.setdefault(ordinal,{'selector':row['selector'],'ordinal':ordinal,
            'inputs':[],'produced':[],'unresolved':[],
            'scope':'Fixed source-copy/direct setup and59 generated-stub path pairings only; other families retain their own obligations'})
    def add(ordinal,path,raw,recipe,kind='file',source=None):
        result = result_for(ordinal)
        if any(item['relative_path']==path for item in result['inputs']):
            raise ClosurePrerequisite('duplicate P01 source pairing')
        value={'relative_path':path,'kind':kind,'raw':raw,'lineage':'independent_literal_input',
            'recipe':recipe,'setup_write_multiplicity':1,
            'interrupted_setup_payload_upper_bytes':len(raw),
            'partial_or_divergent_bytes_are_output':True}
        if source is not None:value['source_provenance']=source
        result['inputs'].append(value)
    prelude = source_literal(ctx,_P01_SUPERVISION_SOURCE,'STUB_PRELUDE')
    for ordinal,selector,codes in _P01_STUB_PROGRAMS:
        if registered[ordinal]['selector']!=selector:
            raise ClosurePrerequisite('P01 generated-stub selector/order mismatch')
        for index,code in enumerate(codes,1):
            raw=(prelude+'\n'+code).encode('utf-8')
            add(ordinal,'t01/stub-'+str(index)+'/stub.py',raw,
                'exact final STUB_PRELUDE + one LF + fixed code argument'+str(index)+'; UTF-8, no added final newline',
                source={'source_path':_P01_SUPERVISION_SOURCE,'source_sha256':_P01_SUPERVISION_SHA256,
                    'helper':'SupervisionStubTests.run_stub','code_selection':'fixed source-ordered literal program'})
        result_for(ordinal)['generated_stub_input_count']=len(codes)
        result_for(ordinal)['produced'].append({'role':'Any interrupted or divergent stub.py setup writes',
            'lineage':'produced_output','paths':['t01/stub-'+str(i)+'/stub.py' for i in range(1,len(codes)+1)],
            'maximum_payload_bytes':sum(len((prelude+'\n'+code).encode('utf-8')) for code in codes),
            'raw_expected':None,'version_rule':'Complete exact input is excluded only on singular type/size/hash match; partial or divergent bytes remain retained output'})
    boot='tests/test_worker38_bootstrap_integration.py'
    legacy='tests/test_worker37_bootstrap.py'
    bash_stub=source_literal(ctx,boot,'BASH_STUB').encode('utf-8')
    frozen_stub=source_literal(ctx,legacy,'FROZEN_STUB').encode('utf-8')
    source_stub=source_literal(ctx,legacy,'SOURCE_BYTES')
    legacy_shell_ids=('T002','T003','T004','T005','T006','T007','T008','T009','T010','T011','T012','T013','T014','T015','T016','T018','T038')
    legacy_python_ids=('T001','T017','T019','T020','T021','T022','T023','T024','T025','T026','T027','T028','T029','T030','T031','T032','T033','T034','T035','T036','T037','T039','T040','T041','T042','T043','T044','T045','T046','T047','T048','T049','T050','T051','T052','T053','T054','T055','T056','T057','T058','T059','T061','T062','T063','T064','T065','T066','T067','T068','T069','T070','T071','T072','T073','T074','T075','T076','T077','T078','T079','T080','T081','T082','T083','T084')
    boot_shell_ids=('S02','S03','S05','S06','S08','C01','C02')
    shell_count=python_count=0
    for row in ctx['rows']:
        source_path=row['selector'].split(':',1)[0]
        case=row['selector'].split('.test_',1)[1].split('_',1)[0]
        ordinal=row['ordinal']
        if (source_path==legacy and case in legacy_shell_ids) or (source_path==boot and case=='S01'):
            shell_count+=1
            base='t02/' if source_path==boot else 't01/'
            for name in _P01_LEGACY_COPY_NAMES:
                source='scripts/'+name
                add(ordinal,base+'workspace/scripts/'+name,ctx['source_bytes'][source],
                    'run_bash exact full source-byte copy; no decode or interpolation',source={'source_path':source})
            for name in _P01_COMMAND_NAMES:
                if case=='T007' and name=='timeout':continue
                add(ordinal,base+'commands/'+name,frozen_stub,'FROZEN_STUB direct AST string UTF-8; exact command copy')
            cache='cache-target/' if case=='T008' else 'cache/'
            add(ordinal,base+cache+'Python/3.11.16/x64/bin/python3.11',frozen_stub,'FROZEN_STUB exact inert executable copy')
            add(ordinal,base+cache+'Python/3.11.16/x64/lib/libpython3.11.so.1.0',b'INVENTED_LIBRARY_BYTES_NOT_LOADABLE\n','run_bash direct bytes literal')
            add(ordinal,base+'event.json',b'{}\n','run_bash direct bytes literal')
            if case=='T013':
                add(ordinal,base+'cache/worker37-bootstrap-readiness/allocations/worker37-bootstrap-readiness-01/reservation.txt',
                    b'INVENTED_PREVIOUS_RUN_108_RESERVATION\n','T013 exact preexisting reservation literal')
            if case=='T008':
                add(ordinal,base+'cache',str(case_root(ctx,ordinal)/'t01'/'cache-target').encode('ascii'),
                    'exact absolute T008 cache symlink target; physical child files paired only below cache-target; never follow link','symlink')
            result_for(ordinal)['bash_root_count']=1
        elif source_path==legacy and case in legacy_python_ids:
            python_count+=1
            add(ordinal,'t01/source/scripts/worker37_bootstrap.py',source_stub,'run_python SOURCE_BYTES direct AST bytes literal')
            add(ordinal,'t01/literal.netrc',b'machine api.github.com login invented password INVENTED_NETRC\n','run_python direct invented string UTF-8; LF retained')
            add(ordinal,'t01/literal.cookies',b'INVENTED_COOKIE_JAR\n','run_python direct invented string UTF-8; LF retained')
        elif source_path==boot and case in boot_shell_ids:
            shell_count+=1
            base='t01/'+case+'/'
            for name in ('worker_bootstrap_shared.sh','worker38-bootstrap.sh'):
                source='scripts/'+name
                add(ordinal,base+'source/scripts/'+name,ctx['source_bytes'][source],
                    'bash_case exact full source-byte copy; no decode or interpolation',source={'source_path':source})
            add(ordinal,base+'source/scripts/worker38/admission.py',b'# invented nonexecuted metadata path\n','bash_case direct bytes literal')
            add(ordinal,base+'source/scripts/run_worker38_synthetic.py',b'# invented nonexecuted science path\n','bash_case direct bytes literal')
            for name in _P01_COMMAND_NAMES:
                add(ordinal,base+'commands/'+name,bash_stub,'BASH_STUB direct AST string UTF-8; exact command copy')
            add(ordinal,base+'cache/Python/3.11.16/x64/bin/python3.11',bash_stub,'BASH_STUB exact inert executable copy')
            add(ordinal,base+'cache/Python/3.11.16/x64/lib/libpython3.11.so.1.0',b'INERT_LIBRARY\n','bash_case direct bytes literal')
            add(ordinal,base+'event.json',b'{}\n','bash_case direct bytes literal')
            if case in ('S06','S08'):
                add(ordinal,base+'cache/worker38-synthetic-profile/allocations/worker38-synthetic-profile-01/reservation.txt',
                    b'INVENTED_PREVIOUS_RESERVATION\n','occupied=True direct preexisting reservation literal')
            if case=='C02':
                credential=source_literal(ctx,'tests/worker38_literal_fixtures.py','CREDENTIAL').encode('utf-8')
                add(ordinal,base+'credential-fd.txt',credential,'CREDENTIAL direct invented string UTF-8; no newline')
            result_for(ordinal)['bash_root_count']=1
    if shell_count!=25 or python_count!=66:
        raise ClosurePrerequisite('P01 exact shell/Python setup selector count changed')
    for result in results.values():
        result['paired_setup_path_count']=len(result['inputs'])
        result['paired_interrupted_setup_payload_upper_bytes']=sum(len(value['raw']) for value in result['inputs'])
        result['reservation_certified']=False
    return {'family_id':'P01','selector_results':[results[k] for k in sorted(results)],
        'counts':{'generated_stub_helper_calls':59,'generic_roots':45,'existing_descendants':2,'Bash_cases':25,'legacy_Python_setup_cases':66},
        'scope':'Supplemental fixed pairs only; retaining other family blockers is mandatory'}


def derive_P01_complete_pairing(ctx):
    result=derive_P01(ctx)
    additions=derive_P01_pairing(ctx)
    by_selector={item['selector']:item for item in result['selector_results']}
    for added in additions['selector_results']:
        item=by_selector[added['selector']]
        if added.get('bash_root_count')==1 or added['selector'].startswith('tests/test_worker37_bootstrap.py:'):
            # The complete fixed setup pairing supersedes the previous incomplete
            # source-only map, including T008's no-follow physical child paths.
            item['inputs']=[]
            item['unresolved']=[]
        paths={value['relative_path'] for value in added['inputs']}
        item['inputs']=[value for value in item['inputs'] if value['relative_path'] not in paths]
        item['inputs'].extend(added['inputs']);item['produced'].extend(added['produced'])
        item['unresolved'].extend(added['unresolved'])
        item['paired_interrupted_setup_payload_upper_bytes']=added['paired_interrupted_setup_payload_upper_bytes']
    result['counts']=additions['counts']
    return result

FAMILY_DISPATCH['P01']=derive_P01_complete_pairing


def derive_P13_with_boundaries(ctx):
    result=derive_P13(ctx)
    for row in result['selector_results']:
        method=row['selector'].rsplit('.',1)[-1]
        if method=='test_PW06_strict_provider_zip_limit_uses_actual_size':
            first=row['stages'][0]
            if first['ordinal']!=1 or len(first['files'])!=1:raise ClosurePrerequisite('PW06 exact first literal state')
            item=first['files'][0]
            relative,raw=item['relative_path'],item['raw']
            if relative!='t01/literal-github-download.zip-1':raise ClosurePrerequisite('PW06 original path drift')
            boundary,slot,cap='accepted-wrapper-before-positive-check','pw06-01',735
        elif method=='test_T15_source_mutation_is_rejected_and_preserved':
            relative,raw='t01/mutable-source-1/a',b'before'
            boundary,slot,cap='after-original-inventory-before-mutation','t15-01',668
        else:continue
        recipe=digest({'family':'P13','source_sha256':ctx['recipe_sha256'],'selector':row['selector'],
            'boundary':boundary,'operation':'exact independently constructed predecessor literal state'})
        row['transport_inputs']=[{'boundary':boundary,'call_ordinal':1,'slot':slot,'record_byte_cap':cap,
            'path_rules':[{'rule_id':'input:'+relative,'relative_path':relative,'allowed_state':{'type':'file',
                'size_bytes':len(raw),'sha256':sha(raw),'lineage':'independent_input',
                'independent_recipe_sha256':recipe,'materialized':True}}]}]
    return result

FAMILY_DISPATCH['P13']=derive_P13_with_boundaries


IMMUTABLE_SOURCE_PINS = {'evidence-design/derive-first33-input-pins.py': {'size_bytes': 24909, 'sha256': '910c22f761f871ddd2d408a7a3d5f58df45ced37b46659ea1b9e7d09c2c3b644'}, 'experiments/worker38-synthetic-profile/FINITE-PREPARATION-PLAN.json': {'size_bytes': 219508, 'sha256': '31ed253dafcfa502bbfa4d7dca9292e93de6e7b48e39a0e33336b6df894b35c9'}, 'experiments/worker38-synthetic-profile/INTEGRATION-CONTRACT.json': {'size_bytes': 32415, 'sha256': '5830bcf1a85f00987e01621f5557f401bcd875bbede2cb34b5d9fd4080c50251'}, 'experiments/worker38-synthetic-profile/PROTOCOL.md': {'size_bytes': 64134, 'sha256': '17abf2d644106bb7c10fbec5481deb7da33e17867ee2f08ea065ca591e8499a7'}, 'experiments/worker38-synthetic-profile/SOURCE-GROUNDING.json': {'size_bytes': 52061, 'sha256': 'cad19fa4ddc826ff6cc4b6d165dbd70325b731dd8b1e5f996077af6196f96717'}, 'experiments/worker38-synthetic-profile/comparator-source-manifest.json': {'size_bytes': 15708, 'sha256': '99afc71070445a1246216f8ed8ff68a2125d95bc2bce95debf77604d4505709b'}, 'experiments/worker38-synthetic-profile/upload-amendment/AMENDMENT-CONTRACT.json': {'size_bytes': 11094, 'sha256': 'b66fc26eba0141b61c21762e97432485bc3f7e896801550ba7b65c31118c86bb'}, 'experiments/worker38-synthetic-profile/upload-amendment/AMENDMENT.md': {'size_bytes': 8827, 'sha256': 'a7a4041d39e77a9265b9a185015f15e56efab7fe66a7b336dcf619ebec410913'}, 'experiments/worker38-synthetic-profile/upload-amendment/FINITE-COVERAGE-AMENDMENT.json': {'size_bytes': 7518, 'sha256': '192f12b30c83237766f808f83eef21c07a295eefece4e6964535d14bf6b5d75b'}, 'experiments/worker38-synthetic-profile/upload-amendment/HANDOFF.json': {'size_bytes': 4478, 'sha256': '54e30bca1fb6c754c211f319789a018255113c35ade1dc0404c197d8c2b0adbe'}, 'experiments/worker38-synthetic-profile/upload-amendment/REPAIR-DISPOSITION.json': {'size_bytes': 749, 'sha256': 'f291ecfd3b5d10f96bb594f4e6945e0beef1625a2ecfa994368243897c2329a8'}, 'experiments/worker38-synthetic-profile/upload-amendment/SOURCE-OBSERVATION.json': {'size_bytes': 471, 'sha256': 'c0b2efd71fc498b6beb8dd8f5fc7b90c047a803c1e2003467978191911f5e9d8'}, 'scripts/worker37-bootstrap.sh': {'size_bytes': 9501, 'sha256': '65d714ea51a0063aedfc1acf38a9a6730de6a572be471514ab395761d7ecc5de'}, 'scripts/worker37_bootstrap.py': {'size_bytes': 51135, 'sha256': '4219f940c1e4365d739e6190c118b7a4dba163960f285dd550d226b524183a09'}, 'scripts/worker38-bootstrap.sh': {'size_bytes': 28516, 'sha256': '934588288efe6dd267cf810758be25338d35056b2aaaffcc0deeb0f16fe758f2'}, 'scripts/worker38/admission.py': {'size_bytes': 74181, 'sha256': '260309ba2ba0e2c720c805dd7c9821f6efb689ce76ef6d9a4513d9a26473b7ce'}, 'scripts/worker38/common.py': {'size_bytes': 37905, 'sha256': 'fe0732a0e08d5852c87ed9c18c23469ced28d93d097c3d434ce6171e4acdd927'}, 'scripts/worker38/driver.py': {'size_bytes': 104303, 'sha256': '22dc18c2141e6aa82de84e052cde8d87fa2871b0f1ddda5e791d0db538f3d0e6'}, 'scripts/worker38/supervision.py': {'size_bytes': 83208, 'sha256': '1f6a4434c250b9adf0efb02e25bfb458f0cb378282eaa2d1c6ea6e5e92420f88'}, 'scripts/worker38/transport.py': {'size_bytes': 66602, 'sha256': 'fa285ccf140f646acea0fbcc7ba7bd63103966357040b22f83eccd174b47fb82'}, 'scripts/worker38/verify.py': {'size_bytes': 70923, 'sha256': 'd8040979eb7ba7ca4081075efaa2176c8d74628fad086cb71a6c795ad0f29204'}, 'scripts/worker_bootstrap_shared.py': {'size_bytes': 10519, 'sha256': 'd3b60dda4cd4796cda088d2bdf9f87c39920f2f7fe98bd5d3ba8e1f09b4fb367'}, 'scripts/worker_bootstrap_shared.sh': {'size_bytes': 19191, 'sha256': '031b30c3f7593299b3dd57daaefbf3cef4dec5b23744f9cc96092b1a612fe475'}, 'tests/test_worker37_bootstrap.py': {'size_bytes': 123546, 'sha256': '81824787ff3b8cae5ce82d29ccf5ab9c7139ed4db47e82bbdb8ad40722d3db83'}, 'tests/test_worker38_bootstrap_integration.py': {'size_bytes': 107174, 'sha256': '125b0ee9bfbb0c8c371babacb87164547a90b1c202660cd2c5ef715c40fd0042'}, 'tests/test_worker38_cell_integration.py': {'size_bytes': 39173, 'sha256': '0fc276cef0ee61c17e797a4928dddc7dda90d83a8f1f11ceea6796ec70f4e5ca'}, 'tests/test_worker38_driver_integration.py': {'size_bytes': 117000, 'sha256': '4570bfc2b34aaf2d743ac6c6b5fb8761abdd27c4642174b0cb0aa62f3f1f6b7b'}, 'tests/test_worker38_verify_integration.py': {'size_bytes': 110561, 'sha256': '5fb0c8d1b6b13eba69041ef1e1b16ec7268433f9862153d580a18e100ccc2a11'}, 'tests/worker38_constructor_source.txt': {'size_bytes': 8645, 'sha256': 'eae10578a56b0a94857b9d9b6132ce6d0772706e57c1f11df1573cd0112fa6cf'}, 'tests/worker38_literal_fixtures.py': {'size_bytes': 12036, 'sha256': '635eaaf457800c5f508f11033f6f28003c1e0393dc0444fa155a1e907984dde2'}}
FIXED_METADATA_INPUTS['fixed_map']['path']='/workspace/shared/worker38-full-closure-implementation/recipe-proof/PREDECESSOR-FIXED-MAP.json'


def verify_environment_file_pin(pin):
    path=Path(pin['path'])
    exists=path.exists() or path.is_symlink()
    if exists!=pin['exists']:raise ClosurePrerequisite('environment presence drift '+str(path))
    if not exists:return
    status=path.lstat()
    if status.st_mode&0o7777!=pin['mode']:raise ClosurePrerequisite('environment mode drift '+str(path))
    kind='symlink' if path.is_symlink() else 'directory' if path.is_dir() else 'file' if status.st_mode&0o170000==0o100000 else 'special'
    if kind!=pin['type']:raise ClosurePrerequisite('environment node drift '+str(path))
    if kind=='symlink':
        target=str(path.readlink())
        if not target.isascii() or target!=pin['target'] or sha(target.encode('ascii'))!=pin['target_bytes_sha256'] or str(path.resolve())!=pin['resolved']:
            raise ClosurePrerequisite('environment link drift '+str(path))
    if 'sha256' in pin:
        before=path.stat();raw=path.read_bytes();after=path.stat()
        fields=('st_dev','st_ino','st_size','st_mtime_ns')
        if any(getattr(before,key)!=getattr(after,key) for key in fields) or len(raw)!=pin['size_bytes'] or sha(raw)!=pin['sha256'] or after.st_mtime_ns!=pin['mtime_ns']:
            raise ClosurePrerequisite('environment byte/freshness drift '+str(path))


def verify_environment_inventory(inventory):
    if inventory['columns']!=['relative_path','type','size_bytes','sha256','mtime_ns','symlink_target','resolved_symlink_target']:
        raise ClosurePrerequisite('environment tree row schema drift')
    rows=inventory['entries']
    if inventory['entry_count']!=len(rows) or inventory['manifest_sha256']!=digest(rows):
        raise ClosurePrerequisite('environment inventory digest/count drift')
    root=Path(inventory['root'])
    names=sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() or p.is_symlink())
    if names!=[r[0] for r in rows]:raise ClosurePrerequisite('environment tree membership drift')
    for relative,kind,size,pin,mtime,target,resolved in rows:
        path=root/relative
        if kind=='symlink':
            if not path.is_symlink() or str(path.readlink())!=target or str(path.resolve())!=resolved:
                raise ClosurePrerequisite('environment tree symlink drift')
        elif kind!='file' or path.is_symlink():raise ClosurePrerequisite('environment tree file kind drift')
        if pin is not None:
            before=path.stat();raw=path.read_bytes();after=path.stat()
            if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns) or len(raw)!=size or sha(raw)!=pin or after.st_mtime_ns!=mtime:
                raise ClosurePrerequisite('environment tree bytes/freshness drift')


def verify_environment_namespace(namespace):
    root=Path(namespace['root'])
    if root.is_dir()!=namespace['exists']:raise ClosurePrerequisite('namespace presence drift')
    if not namespace['exists']:return
    recursive=namespace.get('schema')=='worker38-project-import-namespace-v2'
    rows=[]
    def visit(directory,prefix=''):
        for child in sorted(directory.iterdir()):
            name=child.name;is_directory=child.is_dir();is_link=child.is_symlink()
            if recursive:
                status=child.lstat();is_directory=status.st_mode&0o170000==0o040000
                if not name.isascii():raise ClosurePrerequisite('nonASCII project namespace')
                if not (name.endswith(('.py','.pyc','.so')) or name.isidentifier() and (is_directory or is_link)):continue
            kind='symlink' if is_link else 'directory' if is_directory else 'file'
            if recursive and (is_link or child.lstat().st_mode&0o170000 not in (0o040000,0o100000)):
                raise ClosurePrerequisite('project namespace link/special node')
            rows.append([prefix+name,kind,str(child.readlink()) if is_link else None])
            if recursive and is_directory and name.isidentifier():visit(child,prefix+name+'/')
    if recursive:
        for path,kind,target in namespace['ancestor_entries']:
            if Path(path).is_symlink() or not Path(path).is_dir() or kind!='directory' or target is not None:
                raise ClosurePrerequisite('project namespace ancestor drift')
    visit(root)
    if rows!=namespace['entries'] or digest(rows)!=namespace['entries_sha256']:
        raise ClosurePrerequisite('exact environment namespace membership drift')


def derive_P15_bound_environment(ctx):
    pin=ctx['environment_closure']
    expected_path='/workspace/shared/worker38-implementation/evidence-design/NATIVE-ENVIRONMENT-CLOSURE-06.json'
    if pin.get('path')!=expected_path:raise ClosurePrerequisite('only exact final06 environment manifest is accepted')
    env=read_bound_json(pin)
    if env.get('schema')!='worker38-static-native-environment-closure-v1':raise ClosurePrerequisite('environment schema drift')
    if env['deriver']!={'path':'evidence-design/derive-native-environment-closure.py',
            'sha256':sha(ctx['source_bytes']['evidence-design/derive-native-environment-closure.py'])}:
        raise ClosurePrerequisite('environment final deriver source binding drift')
    binding=env['source_input_binding']
    fields={'schema','native_output_root','recipe_source','recipe_source_identity','literal_input_materialization','current_literal_input_admission'}
    if set(binding)!=fields or binding['schema']!='worker38-preparation-source-input-binding-v1' or binding['native_output_root']!=ctx['namespace'] or binding['recipe_source']!='evidence-design/derive-worker38-all-literal-pins.py' or binding['literal_input_materialization']!='SEPARATE_FULL397_MATERIALIZATION_REQUIRED' or binding['current_literal_input_admission'] is not False:
        raise ClosurePrerequisite('environment source-input binding drift')
    source=Path(__file__).read_bytes()
    identity=binding['recipe_source_identity']
    imports=sorted({name for node in ast.walk(ast.parse(source)) for name in
        ([alias.name for alias in node.names] if isinstance(node,ast.Import) else [node.module or ''] if isinstance(node,ast.ImportFrom) else [])})
    expected_identity={'size_bytes':len(source),'sha256':sha(source),'syntactic_import_names':imports,
        'no_execution_claim':'AST statement inventory includes conditional/unreachable imports; not an observed loaded-module list'}
    if identity!=expected_identity or identity!=env['project_syntactic_import_inventory'][binding['recipe_source']] or sha(source)!=ctx['recipe_sha256']:
        raise ClosurePrerequisite('environment recipe identity/import inventory stale')
    for name,raw in ctx['source_bytes'].items():
        if not name.endswith('.py'):continue
        if name in ('evidence-design/derive-first33-input-pins.py','evidence-design/derive-native-environment-closure.py'):
            # First33 source is inert historical data; current environment
            # deriver is independently bound by env['deriver'] above.
            continue
        item=env['project_syntactic_import_inventory'].get(name)
        if item is None or item['sha256']!=sha(raw) or item['size_bytes']!=len(raw):raise ClosurePrerequisite('environment source input stale '+name)
    historical=env['historical_first33_input_recipe_record']
    if historical['current_literal_input_admission'] is not False or historical['native_output_root']!='/workspace/shared/worker38-native-batch-03':
        raise ClosurePrerequisite('historical33 is not current397 literal evidence')
    if any(env['activity'].get(key)!=0 for key in ('project_imports','test_imports','fixture_calls','target_interpreter_invocations','target_Bash_invocations','target_timeout_invocations','runtime_probes','process_probes','network_probes','bytecode_execution')):
        raise ClosurePrerequisite('environment manifest violates static scope')
    closure=env['elf_closure']
    if any(closure[key] for key in ('missing_DT_NEEDED_candidates','multiple_distinct_cache_candidates','RPATH_RUNPATH_FILTER_AUXILIARY_objects')):
        raise ClosurePrerequisite('environment ELF closure has unresolved branches')
    launch=env['launch_contract']
    if launch['interpreter']!='/usr/bin/python3' or launch['python_flags']!=['-B','-P'] or launch['safe_path'] is not True:
        raise ClosurePrerequisite('environment materialization interpreter/flags mismatch')
    for filepin in launch['executables']+env['path_aliases']+env['configuration_files']+env['absent_or_present_startup_candidates']:
        verify_environment_file_pin(filepin)
    verify_environment_file_pin(env['loader_cache']['file'])
    for item in closure['objects'].values():verify_environment_file_pin(item['file'])
    for item in closure['symlink_requests'].values():verify_environment_file_pin(item)
    verify_environment_inventory(env['stdlib_complete_tree'])
    verify_environment_inventory(env['SSL_default_certificate_tree'])
    if env['cached_bytecode']['headers_sha256']!=digest(env['cached_bytecode']['headers']):raise ClosurePrerequisite('cache header binding drift')
    site=env['site'];verify_environment_file_pin(site['source'])
    for filepin in site['pth_files']:verify_environment_file_pin(filepin)
    for files in site['customizer_candidates'].values():
        for filepin in files:verify_environment_file_pin(filepin)
    for namespace in env['project_import_roots']+site['global_site_directory_namespaces']:
        verify_environment_namespace(namespace)
    return {'family_id':'P15','environment_manifest':pin,'remaining_nonexecution_limits':env['remaining_uncertainties'],
        'literal_input_materialization_separate':True,'selector_results':[{'selector':r['selector'],'ordinal':r['ordinal'],
            'inputs':[],'produced':[],'unresolved':[],'environment_manifest_sha256':pin['sha256'],
            'namespace':ctx['namespace'],'native_execution_authorized':False} for r in ctx['rows'] if 'P15' in r['family_ids']]}

FAMILY_DISPATCH['P15']=derive_P15_bound_environment


# P03 startup lineage source fragment SHAcba5591a45f2aaeb4eb548d4ea54d0bc6fe57576f0ac8e0050194cfc8392d7f2
# SOURCE TEXT ONLY. Additional exact P03 startup lineage join.
# This does not run Client, Response, validators, tests or the candidate.
# In-memory source mutations are bound by P03-STARTUP-CALLER-AUDIT.json and
# the original source methods, not converted into invented input-file paths.

def derive_P03_startup_lineage(ctx):
    counts = {'A01':1,'A02':1,'A03':1,'A04':1,'A05':1,'A06':1,'A07':1,'A08':1,
        'A09':1,'A10':1,'A11':1,'A12':1,'A13':1,'A14':1,'A15':1,'A16':1,'A17':1,'A18':1,
        'C04':1,'F06':1,'H01':1,'H02':2,'H03':5,'H04':2,'H05':1,'H06':1,'H07':1,
        'H08':1,'H09':1,'H10':2,'H11':4,'H13':8,'H14':6,'H15':6}
    no_pipeline = ('S01','S02','S03','S04','S05','S06','S07','S08','S09','S10','S11','S12',
        'C01','C02','C03','C05','C06','C07','C08','C09','C10',
        'F01','F02','F03','F04','F05','F07','F08','H12','H16')
    input_names = ('pull-request.json','postmerge-ci.json','current-source-ci.json','review-exhaustive.json',
        'review-adversarial.json','preregistration.json','diagnostic-commit.json')
    reservation = (b'schema=worker38-observed-reservation-v1\nallocation_id=worker38-synthetic-profile-01\n'
        b'run_id=501\nrun_attempt=1\nobserved_head='+b'1'*40+
        b'\ndescriptor_binding=not_yet_validated\nevaluator_starts=0\nscientific_classification=null\n')
    results = []
    for row in ctx['rows']:
        if row['source_path'] != 'tests/test_worker38_bootstrap_integration.py':
            continue
        case = row['selector'].split('.test_',1)[1].split('_',1)[0]
        if case not in counts and case not in no_pipeline:
            raise ValueError('P03 startup64 caller domain changed')
        result = {'selector':row['selector'],'ordinal':row['ordinal'],'inputs':[],'produced':[],'unresolved':[],
            'in_memory_mutation_proof':'Exact original method and helper spans in P03-STARTUP-CALLER-AUDIT.json; default independent_auth_bundle is mutated in original source order. No fixture/helper execution is used as an oracle.',
            'auth_file_lineage':'pipeline never pre-materializes event/context/admission/provenance or seven auth input files; its Response bytes are in-memory fixtures. Client writes are produced outputs.'}
        for index in range(counts.get(case,0)):
            base='t01/consumed-'+str(index)
            result['inputs'].append({'relative_path':base+'/reservation.txt','kind':'file','raw':reservation,
                'lineage':'independent_literal_input','recipe':'pipeline fixed ASCII reservation before watch_production; original per-selector subcase index'+str(index)})
            result['produced'].append({'lineage':'produced_output','source':'startup.pipeline Client.inputs/Evidence persistence after watch_production',
                'subtree':base+'/admission-inputs','possible_original_names':list(input_names),
                'actual_input_role':'these produced response files are reread by Client validation; raw complete/partial/absent outcomes remain charged',
                'expected_hash_source':'none; observed Client return/file content cannot seed independent expected input identity',
                'reservation_reference':'existing startup selector exact source/output/partial ledger; no new capture or allowance'})
        if case=='C04':
            result['produced'].append({'lineage':'produced_output','operation':'rename_only',
                'source':'t01/consumed-0/admission-inputs',
                'destination':'t01/runtime-0/worker38-synthetic-profile/allocations/worker38-synthetic-profile-01/run-501-attempt-1/admission-inputs',
                'literal_reservation_survives':'t01/consumed-0/reservation.txt',
                'proof':'failure_preservation(existing=result) moves only existing.evidence.output; no copy or reservation rename'})
        if counts.get(case,0):
            result['produced'].append({'lineage':'produced_output','role':'retain observed files/copies and observed-report.json',
                'source':'retain increments subcase before destination check; existing output references must be byte-identical and are removed from duplicate payloads',
                'no_reclassification':'a retained copy of an independently constructed in-memory response remains an observed Client output'})
        if case=='S07':
            result['memory_only']='context.attempt_path changed to closed worker37 namespace; validate_context only'
        elif case=='C03':
            result['memory_only']='handoff dictionary plus GH_TOKEN; validate_handoff only; no serialized input'
        elif case=='H16':
            result['existing_join']='P04 exact local_sources files and focused-receipt mutations; three frozen-descriptor/report retentions are produced'
        elif case in ('F07','F08'):
            result['existing_join']='P04_revision03/P07_revision03/P08 explicitly bind physical auth/startup/cohort paths; this startup lineage join adds none'
        results.append(result)
    if len(results)!=64 or sum(counts.values())!=61:
        raise ValueError('P03 exact64 caller/61 invocation domain changed')
    return {'family_id':'P03','selector_results':results,
        'coverage':'Complete startup physical-input/produced-lineage disposition; exact source mutation audit remains bound separately',
        'newly_closed_static_input':'ordinal34 t01/consumed-0/reservation.txt; other60 paths independently crosscheck existing P01 recipes',
        'reservation_certified':False,'execution_authorized':False}


def derive_P03_with_startup_lineage(ctx):
    result = derive_P03(ctx)
    by_selector = {item['selector']:item for item in result['selector_results']}
    for item in derive_P03_startup_lineage(ctx)['selector_results']:
        previous=by_selector[item['selector']]
        previous['inputs'].extend(item['inputs'])
        previous['produced'].extend(item['produced'])
        previous['startup_lineage']={key:value for key,value in item.items()
            if key not in ('selector','ordinal','inputs','produced','unresolved')}
        previous['unresolved'].extend(item['unresolved'])
    return result

FIXED_METADATA_INPUTS['startup_auth_audit']={'path': '/workspace/shared/worker38-full-closure-implementation/recipe-family-proof/P03-STARTUP-CALLER-AUDIT.json', 'size_bytes': 105208, 'sha256': '3c469edf69139aab3ac3eddd06657fea8dca91942b16deeea4f72e82f4bd2532'}


def derive_P03_bound_startup_lineage(ctx):
    result=derive_P03_with_startup_lineage(ctx)
    audit=ctx['startup_auth_audit']
    source=ctx['source_bytes']['tests/test_worker38_bootstrap_integration.py']
    if audit['source_binding']['sha256']!=sha(source):raise ClosurePrerequisite('P03 startup source/audit binding drift')
    rows={row['selector']:row for row in audit['rows']}
    if len(rows)!=64 or audit['counts']['pipeline_invocations']!=61:
        raise ClosurePrerequisite('P03 startup audit roster drift')
    for item in result['selector_results']:
        if item['selector'] not in rows:continue
        bound=rows[item['selector']]
        if item['ordinal']!=bound['ordinal']:raise ClosurePrerequisite('P03 startup audit order drift')
        item['in_memory_source_recipe']=bound['in_memory_source_recipe']
        item['original_source_operations']=bound['original_source_operations']
        item['source_method_binding']=bound['method_binding']
        for value in item['inputs']:
            value['physical_file_identity']=item['selector']+'|'+value['relative_path']
            value['cross_family_coalescence']='One physical file; merge P01/P03 only after independently derived type/raw bytes match exactly; never charge a fictional duplicate'
    return result

FAMILY_DISPATCH['P03']=derive_P03_bound_startup_lineage

if __name__=='__main__':
    main()
