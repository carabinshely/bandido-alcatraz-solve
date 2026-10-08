#!/usr/bin/python3
# Frozen source-only finite native05 lineage supplement. A separate durable
# materialization GO, authenticated grant and managed command are mandatory.
# No project module, candidate helper, historical deriver or test is imported.
import ast
import base64
import copy
import hashlib
import json
import os
import resource
import stat
import sys
import time
from pathlib import PurePosixPath

ERROR_CODES = ('0', '1', '123', '456', '9001', '999', 'ALL397', 'ALLOCATION', 'ARGUMENTS', 'A_ALLOCATION', 'A_BASE_HEAD', 'A_BASE_TREE', 'A_BRANCH', 'A_CI_RUN', 'A_EXPERIMENT', 'A_HANDOFF_LINES', 'A_INPUT_NAMES', 'A_LIBRARY_SHA256', 'A_LIBRARY_SIZE', 'A_MARKER', 'A_OWNER', 'A_REPOSITORY', 'A_REQUIRED_PRODUCTION_PATHS', 'A_RUNNER', 'BASE_HEAD', 'BASE_TREE', 'BRANCH', 'CANONICAL_FOLDER', 'CI_RUN', 'CLOSED_FAILURE', 'COMPLETE', 'CONTRACT_SHA256', 'CUSTODY_ALIAS_OLD_IDENTITY', 'CUSTODY_ALIAS_OPERATION', 'CUSTODY_COMMITMENT_ROW_ROSTER', 'CUSTODY_COMMITMENT_WRITE_ROSTER', 'CUSTODY_DELTA_EXACT_ROSTER', 'CUSTODY_DELTA_RECORD_BOUND', 'CUSTODY_EVENT_PREFIX_BOUND', 'CUSTODY_EVENT_PRODUCED_ROLE', 'CUSTODY_EVENT_ROSTER', 'CUSTODY_FINITE_RECIPE_IDENTITY', 'CUSTODY_FIXED_IDENTITY_MISSING', 'CUSTODY_GENERATION_ALIAS', 'CUSTODY_GENERATION_DIRECTORY', 'CUSTODY_GENERATION_ROSTER', 'CUSTODY_HISTORY_EXPORT_PHASE', 'CUSTODY_HISTORY_ORDER_GAP', 'CUSTODY_INVARIANT_ASSET_IDENTITY', 'CUSTODY_INVARIANT_ASSET_LINEAGE', 'CUSTODY_INVARIANT_ASSET_ROSTER', 'CUSTODY_INVARIANT_INVENTORY', 'CUSTODY_NAMESPACE', 'CUSTODY_OBLIGATION_FAMILY_ROSTER', 'CUSTODY_OBLIGATION_IDENTITY', 'CUSTODY_OBLIGATION_REQUIRED', 'CUSTODY_OBLIGATION_ROSTER', 'CUSTODY_OLD_EVENT_HISTORY_MISMATCH', 'CUSTODY_OLD_OBLIGATION_COMMITMENT_MISMATCH', 'CUSTODY_OLD_RESULT_COMMITMENT_MISMATCH', 'CUSTODY_OLD_STATE_COMMITMENT_MISMATCH', 'CUSTODY_PARENT_NAMESPACE', 'CUSTODY_ROW_ROSTER', 'CUSTODY_TOTAL_WRITES', 'CUSTODY_UNEXPECTED_UNCHANGED_DELTA', 'CUSTODY_VERIFIED_PAIR_DOMAIN', 'CUSTODY_VERIFIED_PAIR_IDENTITY', 'CUSTODY_VERIFIED_PAIR_MISSING', 'CUSTODY_WRITE_COUNT', 'CUSTODY_WRITE_IDENTITY', 'CUSTODY_WRITE_ROSTER', 'CUSTODY_WRITE_SIZE', 'C_CONTRACT_SHA256', 'C_FINITE_PLAN_SHA256', 'C_HISTORICAL', 'C_OPS', 'C_PREREGISTRATION', 'C_PROTOCOL_SHA256', 'C_REPOSITORY', 'C_RUNTIME', 'C_SOURCE_MANIFEST_SHA256', 'C_STARTUP_RESOURCES', 'C_UPLOAD_ADOPTION', 'C_UPLOAD_AMENDMENT_SHA256', 'C_UPLOAD_CONTRACT_SHA256', 'C_UPLOAD_FINITE_PLAN_SHA256', 'DEADLINE', 'DELTA', 'DELTA_EXACT_ROSTER', 'DELTA_FRAMING', 'DIRECTORY_PATH', 'DOMAIN_RECORDS', 'DONE', 'EMISSION_CAP', 'EMIT_DUPLICATE_KEY', 'EMIT_KEY', 'EMIT_SHAPE', 'END_', 'END_WORKER38_NATIVE_REVIEW_JSON', 'ENTER', 'EXCEPTION', 'F07_AFFECTED_COUNT', 'F07_AFFECTED_ROSTER', 'F07_BASELINE_COUNT', 'F07_DEPENDENCY_ORDER', 'F07_INVARIANT_ADMISSION', 'F07_INVENTORY_COUNT', 'F07_NAMESPACE', 'F07_ORIGINAL_COUNT', 'F07_ORIGINAL_KIND', 'F07_OUTPUT_ROSTER', 'F07_OUTPUT_SIZE', 'F07_OUTPUT_TYPE', 'F07_ROW', 'F07_SOURCE_LITERAL_PIN', 'FAIL', 'FINITE_PLAN_SHA256', 'F_HEAD', 'F_INHERITED_LIMITS', 'F_INITIAL_MODULES', 'F_OWNER', 'F_TREE', 'GET', 'GRANT_PIN', 'GRANT_SCOPE', 'HEAD', 'INHERITED_LIMITS', 'INITIAL_MODULES', 'INPUT_DOMAIN', 'INPUT_NAMES', 'INP_ER_MANIFEST', 'INP_ER_NAMES', 'INP_INVARIANT', 'INP_NAMESPACE', 'INP_PIN', 'INP_PIN_SHAPE', 'INP_ROW', 'LD_LIBRARY_PATH', 'LITERAL_ASSIGNMENT', 'LITERAL_AST', 'LITERAL_BOOT_ID', 'LITERAL_LOADER_PIN', 'LITERAL_SCOPE', 'LOG_RECORD', 'LOG_VOCABULARY', 'MARKER', 'METADATA_ALL397_FAMILY_JOIN', 'METADATA_ALL397_OBLIGATION_IDENTITY', 'METADATA_ALL397_SELECTOR_JOIN', 'METADATA_COMPLETE397_JOIN', 'METADATA_CUSTODY_DIRECTORY_ALIAS', 'METADATA_CUSTODY_ENCLOSING_COMMITMENT', 'METADATA_CUSTODY_GROUP_DOMAIN', 'METADATA_CUSTODY_GROUP_IDENTITY', 'METADATA_CUSTODY_LEAF_BOUND', 'METADATA_CUSTODY_NAMESPACE_COLLISION', 'METADATA_CUSTODY_NEW_VALUE', 'METADATA_CUSTODY_OLD_VALUE', 'METADATA_EXACT_CUSTODY_LEAF_DOMAIN', 'METADATA_EXACT_NAMESPACE', 'METADATA_EXACT_OWN_LEAF_DOMAIN', 'METADATA_EXACT_PACKING_BOUND', 'METADATA_EXACT_PACKING_DOMAIN', 'METADATA_FAMILY_GROUP_DOMAIN', 'METADATA_FAMILY_ORDINAL_DUPLICATE', 'METADATA_FIXED_INPUT_ROSTERS', 'METADATA_HISTORICAL_P15_CLAIM', 'METADATA_HISTORICAL_PRODUCTS', 'METADATA_INPUT_IDENTITY_DOMAIN', 'METADATA_INPUT_OCCURRENCE_IDENTITY', 'METADATA_INPUT_OLD_IDENTITY', 'METADATA_INPUT_PAIR_IDENTITY', 'METADATA_INPUT_PAIR_MISSING', 'METADATA_INVARIANT_LOADER_CHANGED', 'METADATA_LEAF_BOUND', 'METADATA_LEAF_SHAPE', 'METADATA_LOADER_COMPLETE_DOMAIN', 'METADATA_LOADER_INPUT_LINEAGE', 'METADATA_LOADER_ROSTER_IDENTITY', 'METADATA_LOADER_SCALAR_DOMAIN', 'METADATA_LOADER_SCALAR_ROSTER', 'METADATA_LOADER_SELECTED_CONTEXTS', 'METADATA_NAMESPACE_COMPLETE_DOMAIN', 'METADATA_NAMESPACE_OLD_VALUE', 'METADATA_OLD_LOADER_DESCRIPTOR', 'METADATA_OLD_OBLIGATION_COMMITMENT', 'METADATA_OLD_VERIFIER_RESULT', 'METADATA_P15_JOIN_MISSING', 'METADATA_PACKING_DIGEST', 'METADATA_PACKING_NAMESPACE', 'METADATA_PACKING_SINGLE_LEAF', 'METADATA_POINTER_INDEX', 'METADATA_POINTER_SHAPE', 'METADATA_POINTER_TARGET', 'METADATA_RAW_INPUT_LINEAGE', 'METADATA_ROW_LEAF_TARGET', 'METADATA_ROW_OLD_VALUE', 'METADATA_ROW_POINTER_SCOPE', 'METADATA_VERIFIER_JOIN', 'METADATA_VERIFIER_ORDINAL_DUPLICATE', 'NEW', 'NEW_ALIAS_BYTES', 'NEW_COMPLETE', 'NEW_TRACE_IDENTITY', 'NEW_TRACE_LENGTH', 'NEW_UNCHANGED_OBJECT', 'OBLIGATIONS', 'OLD', 'OLD_ALIAS_BYTES', 'OLD_COMPLETE', 'OLD_PREIMAGE_MISMATCH', 'OWNED_ACTION', 'OWNED_ACTION_ALREADY_FAILED', 'OWNER', 'P', 'P0', 'P04', 'P05', 'P07', 'P08', 'P09', 'P1', 'P10', 'P11', 'P12', 'P15', 'P2', 'P3', 'PAIR_BASE64_READBACK', 'PAIR_FRAMING', 'PAIR_PAYLOAD_COUNT', 'PAIR_PHASE', 'PAIR_RECORD_FRAMING', 'PARENT_MUTATED', 'PARTIAL_SCOPE', 'PATH', 'PREREGISTRATION', 'PROTOCOL_SHA256', 'PYTHONDONTWRITEBYTECODE', 'PYTHONHASHSEED', 'READBACK_ALREADY_ATTEMPTED', 'READBACK_CAP', 'READBACK_PIN', 'READBACK_TYPE_SIZE', 'READ_CHANGED', 'READ_DUPLICATE', 'READ_PIN', 'READ_SCOPE', 'READ_SIZE', 'READ_TOTAL', 'READ_UNREGISTERED', 'REPOSITORY', 'REQUIRED_PRODUCTION_PATHS', 'RLIMIT_AS', 'RLIMIT_CPU', 'RUNNER', 'RUNTIME', 'SCOPE_DOMAIN', 'SCOPE_PIN', 'SOURCE_MANIFEST_SHA256', 'SOURCE_PIN', 'START', 'STARTUP_RESOURCES', 'TOTAL_DOMAIN', 'TREE', 'TYPE', 'U', 'UPLOAD_ADOPTION', 'UPLOAD_AMENDMENT_SHA256', 'UPLOAD_CONTRACT_SHA256', 'UPLOAD_FINITE_PLAN_SHA256', 'VERIFIED', 'V_HEAD', 'V_INHERITED', 'V_INITIAL_MODULES', 'V_PUBLIC', 'V_RNG', 'V_SCIENCE', 'V_SOURCE_BYTES', 'V_SOURCE_MODULES', 'V_TESTED_EXTRA_PATHS', 'V_TREE', 'WORKER38_NATIVE_REVIEW_JSON', 'WRITE_ALLOCATION_ALREADY_ATTEMPTED', 'WRITE_ALREADY_FINALIZING', 'WRITE_FILE_CAP', 'WRITE_FINISH', 'WRITE_SCOPE', 'WRITE_SHORT', 'WRITE_TOTAL_CAP', 'WRITE_TYPE', '_JSON', '_SHA256')

# F07: finite source-transcribed namespace dependency DAG; definitions only.
# This fragment is concatenated into the single standalone lineage program.
# No import, constructor, fixture-byte construction, or I/O occurs on definition.
# Required enclosing stdlib names: copy, hashlib, json, PurePosixPath.


def f07_canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')


def f07_sha(raw):
    return hashlib.sha256(raw).hexdigest()


def f07_digest(value):
    return f07_sha(f07_canonical(value))


def build_f07(ctx, namespace, emit):
    """Build only ordinal47's affected ORIGINAL files after a separate run GO.

    Caller must finish and verify ALL old passes before beginning ANY new pass.
    Identical sorted logical paths give stable old/new pair ordering. Invariant
    files are identity-only dependencies; no ZIP or physical moved copy exists
    here. ctx.accepted is the already verified original accepted06 JSON object.
    """
    if namespace not in ('/workspace/shared/worker38-native-batch-04',
                          '/workspace/shared/worker38-native-batch-05'):
        raise ValueError('F07_NAMESPACE')
    source_rel = 'evidence-design/derive-worker38-all-literal-pins.py'
    C_MIB = 1024 ** 2
    C_REPOSITORY = ctx.literal(source_rel, 'C_REPOSITORY')
    C_HISTORICAL = ctx.literal(source_rel, 'C_HISTORICAL')
    C_PREREGISTRATION = ctx.literal(source_rel, 'C_PREREGISTRATION')
    C_PROTOCOL_SHA256 = ctx.literal(source_rel, 'C_PROTOCOL_SHA256')
    C_RUNTIME = ctx.literal(source_rel, 'C_RUNTIME')
    C_CONTRACT_SHA256 = ctx.literal(source_rel, 'C_CONTRACT_SHA256')
    C_FINITE_PLAN_SHA256 = ctx.literal(source_rel, 'C_FINITE_PLAN_SHA256')
    C_UPLOAD_AMENDMENT_SHA256 = ctx.literal(source_rel, 'C_UPLOAD_AMENDMENT_SHA256')
    C_UPLOAD_CONTRACT_SHA256 = ctx.literal(source_rel, 'C_UPLOAD_CONTRACT_SHA256')
    C_UPLOAD_FINITE_PLAN_SHA256 = ctx.literal(source_rel, 'C_UPLOAD_FINITE_PLAN_SHA256')
    C_UPLOAD_ADOPTION = ctx.literal(source_rel, 'C_UPLOAD_ADOPTION')
    C_SOURCE_MANIFEST_SHA256 = ctx.literal(source_rel, 'C_SOURCE_MANIFEST_SHA256')
    C_STARTUP_RESOURCES = ctx.literal(source_rel, 'C_STARTUP_RESOURCES')
    C_OPS = ctx.literal(source_rel, 'C_OPS')
    C_OP_CAPS = dict(zip(C_OPS, (32768, 32768, 16384)))
    C_CALL_CAPS = {**C_OP_CAPS, 'roots': 16384, 'wall_seconds': 360, 'cpu_seconds': 360}
    C_RESOURCES = {'per_call': {k: dict(C_CALL_CAPS) for k in ('control', 'candidate', 'reference')}, 'whole_cell_wall_seconds': 720, 'whole_cell_cpu_seconds': 720, 'whole_wrapper_operations': {k: 2 * v for k, v in C_OP_CAPS.items()}, 'total_operations': dict.fromkeys(C_OPS, 1000000), 'measurement_wall_seconds': 1800, 'measurement_cpu_seconds': 1800, 'address_space_bytes': 512 * C_MIB, 'evidence_bytes': 64 * C_MIB, 'receipt_bytes': C_MIB, 'trace_bytes': 16 * C_MIB, 'line_bytes': 8 * C_MIB, 'archive_bytes': 64 * C_MIB, 'part_bytes': 30 * C_MIB, 'verification_wall_seconds': 600, 'workflow_minutes': 45, 'free_storage_bytes': 1024 * C_MIB}
    C_SCHEDULE = tuple(({'cell': i + 1, 'repetition': rep, 'size': n, 'condition': condition} for i, (rep, n, condition) in enumerate([(1, n, c) for n in (0, 4, 8, 40, 48) for c in ('P', 'U')] + [(2, n, c) for n in (48, 40, 8, 4, 0) for c in ('U', 'P')])))
    A_UPLOAD_AMENDMENT_SHA256=C_UPLOAD_AMENDMENT_SHA256
    A_UPLOAD_CONTRACT_SHA256=C_UPLOAD_CONTRACT_SHA256
    A_UPLOAD_FINITE_PLAN_SHA256=C_UPLOAD_FINITE_PLAN_SHA256
    A_REPOSITORY = ctx.literal(source_rel, 'A_REPOSITORY')
    A_OWNER = ctx.literal(source_rel, 'A_OWNER')
    A_BRANCH = ctx.literal(source_rel, 'A_BRANCH')
    A_ALLOCATION = ctx.literal(source_rel, 'A_ALLOCATION')
    A_RUNNER = ctx.literal(source_rel, 'A_RUNNER')
    A_BASE_HEAD = ctx.literal(source_rel, 'A_BASE_HEAD')
    A_BASE_TREE = ctx.literal(source_rel, 'A_BASE_TREE')
    A_CI_RUN = ctx.literal(source_rel, 'A_CI_RUN')
    A_WEB = 'https://github.com/' + A_REPOSITORY
    A_MARKER = ctx.literal(source_rel, 'A_MARKER')
    A_START, A_END, A_DIGEST = (A_MARKER + '_JSON', 'END_' + A_MARKER + '_JSON', A_MARKER + '_SHA256')
    A_REVIEW_START, A_REVIEW_END = ('WORKER38_NATIVE_REVIEW_JSON', 'END_WORKER38_NATIVE_REVIEW_JSON')
    A_INPUT_NAMES = ctx.literal(source_rel, 'A_INPUT_NAMES')
    A_LIBRARY_SHA256 = ctx.literal(source_rel, 'A_LIBRARY_SHA256')
    A_LIBRARY_SIZE = ctx.literal(source_rel, 'A_LIBRARY_SIZE')
    A_EXPERIMENT = ctx.literal(source_rel, 'A_EXPERIMENT')
    A_FOCUSED_SOURCE_RECEIPT = A_EXPERIMENT + 'focused-preparation-receipt.json'
    A_METADATA_PATHS = (A_EXPERIMENT + 'PROTOCOL.md', A_EXPERIMENT + 'INTEGRATION-CONTRACT.json', A_EXPERIMENT + 'FINITE-PREPARATION-PLAN.json', A_EXPERIMENT + 'SOURCE-GROUNDING.json', A_EXPERIMENT + 'comparator-source-manifest.json')
    A_REQUIRED_PRODUCTION_PATHS = ctx.literal(source_rel, 'A_REQUIRED_PRODUCTION_PATHS')
    A_UPLOAD_RECORD_PINS = {A_EXPERIMENT + 'upload-amendment/AMENDMENT.md': A_UPLOAD_AMENDMENT_SHA256, A_EXPERIMENT + 'upload-amendment/AMENDMENT-CONTRACT.json': A_UPLOAD_CONTRACT_SHA256, A_EXPERIMENT + 'upload-amendment/FINITE-COVERAGE-AMENDMENT.json': A_UPLOAD_FINITE_PLAN_SHA256, A_EXPERIMENT + 'upload-amendment/SOURCE-OBSERVATION.json': 'c0b2efd71fc498b6beb8dd8f5fc7b90c047a803c1e2003467978191911f5e9d8', A_EXPERIMENT + 'upload-amendment/REPAIR-DISPOSITION.json': 'f291ecfd3b5d10f96bb594f4e6945e0beef1625a2ecfa994368243897c2329a8', A_EXPERIMENT + 'upload-amendment/HANDOFF.json': '54e30bca1fb6c754c211f319789a018255113c35ade1dc0404c197d8c2b0adbe'}
    A_METADATA_PATHS += tuple(A_UPLOAD_RECORD_PINS)
    A_HANDOFF_LINES = ctx.literal(source_rel, 'A_HANDOFF_LINES')
    F_HEAD = ctx.literal(source_rel, 'F_HEAD')
    F_TREE = ctx.literal(source_rel, 'F_TREE')
    F_OWNER = ctx.literal(source_rel, 'F_OWNER')
    F_LIBRARY_PIN = {'schema': 'worker38-loader-pin-v1', 'executable_sha256': C_RUNTIME['executable_sha256'], 'library_relative_path': 'Python/3.11.16/x64/lib/libpython3.11.so.1.0', 'library_sha256': A_LIBRARY_SHA256, 'library_size_bytes': A_LIBRARY_SIZE}
    F_INITIAL_MODULES = ctx.literal(source_rel, 'F_INITIAL_MODULES')
    F_INHERITED_LIMITS = ctx.literal(source_rel, 'F_INHERITED_LIMITS')
    V_HEAD = ctx.literal(source_rel, 'V_HEAD')
    V_TREE = ctx.literal(source_rel, 'V_TREE')
    V_PUBLIC = ctx.literal(source_rel, 'V_PUBLIC')
    V_RNG = ctx.literal(source_rel, 'V_RNG')
    V_SCIENCE = ctx.literal(source_rel, 'V_SCIENCE')
    V_INHERITED = ctx.literal(source_rel, 'V_INHERITED')
    V_SOURCE_BYTES = ctx.literal(source_rel, 'V_SOURCE_BYTES')
    V_TESTED_EXTRA_PATHS = ctx.literal(source_rel, 'V_TESTED_EXTRA_PATHS')
    V_LOADER_PIN = {'schema': 'worker38-loader-pin-v1', 'executable_sha256': C_RUNTIME['executable_sha256'], 'library_relative_path': 'Python/3.11.16/x64/lib/libpython3.11.so.1.0', 'library_sha256': 'ba4450817186fbe1e3c477f6aefeee7c353cba3593cc9950382ad9d1f5e62896', 'library_size_bytes': 23041360}
    V_LOADER_IDENTITY = {'schema': 'worker38-loader-identity-v1', 'tool_cache': '/invented-cache', 'executable_path': '/invented-cache/Python/3.11.16/x64/bin/python3.11', 'executable_sha256': C_RUNTIME['executable_sha256'], 'library_relative_path': 'Python/3.11.16/x64/lib/libpython3.11.so.1.0', 'library_path': '/invented-cache/Python/3.11.16/x64/lib/libpython3.11.so.1.0', 'library_directory': '/invented-cache/Python/3.11.16/x64/lib', 'library_sha256': 'ba4450817186fbe1e3c477f6aefeee7c353cba3593cc9950382ad9d1f5e62896', 'library_size_bytes': 23041360, 'library_device': {'major': 8, 'minor': 1}, 'library_inode': 1234, 'mapped_library': {'path': '/invented-cache/Python/3.11.16/x64/lib/libpython3.11.so.1.0', 'device': {'major': 8, 'minor': 1}, 'inode': 1234}, 'loader_environment': {'LD_LIBRARY_PATH': '/invented-cache/Python/3.11.16/x64/lib'}}
    V_SOURCE_MODULES = ctx.literal(source_rel, 'V_SOURCE_MODULES')
    V_INITIAL_MODULES = ctx.literal(source_rel, 'V_INITIAL_MODULES')

    case = PurePosixPath(namespace) / 'c0047'
    root_rel = 't01/complete-cache/worker38-synthetic-profile/allocations/worker38-synthetic-profile-01/run-123-attempt-1'
    auth_rel = 't01/complete-external/external-auth'
    root = case / root_rel
    cache = str(case / 't01/complete-cache')
    source_path = str(case / 't01/complete-checkout')
    original = str(root)
    script = source_path + '/scripts/run_worker38_synthetic.py'
    row = ctx.accepted['families']['P04']['selector_results'][46]
    if row['ordinal'] != 47 or row['selector'] != ('tests/test_worker38_bootstrap_integration.py:'
            'Worker38BootstrapIntegration.test_F07_complete_literal_20_cell_orchestration'):
        raise ValueError('F07_ROW')
    original_entries = [item for item in row['inputs'] if item.get('recipe') ==
                        'P08 independently derived original F07 cohort before any move']
    if len(original_entries) != 369:
        raise ValueError('F07_ORIGINAL_COUNT')
    accepted_pins = {}
    for item in original_entries:
        path = item['relative_path']
        if item['kind'] != 'file' or path in accepted_pins:
            raise ValueError('F07_ORIGINAL_KIND')
        accepted_pins[path] = dict(item['raw'])
    if len({path for path in accepted_pins if path.startswith(root_rel + '/')}) != 357:
        raise ValueError('F07_BASELINE_COUNT')
    affected_paths = {
        prefix + '/' + name
        for prefix in (auth_rel, root_rel + '/admission-inputs')
        for name in ('request-context.json', 'provenance.json')}
    affected_paths.update(root_rel + '/' + name for name in (
        'startup-handoff.json', 'measurement-handoff.txt',
        'source-runtime-preflight.json', 'receipt.json', 'measurement-phase-close.json'))
    for index in range(1, 21):
        affected_paths.add(root_rel + '/supervisor-cell-%02d.json' % index)
        affected_paths.update(root_rel + '/cells/%02d/' % index + name for name in (
            'source-runtime-preflight.json', 'cell-receipt.json',
            'candidate-start.json', 'candidate-return.json', 'candidate-capture-confirmed.json',
            'reference-start.json', 'reference-return.json', 'reference-capture-confirmed.json'))
    if len(affected_paths) != 189 or not affected_paths.issubset(accepted_pins):
        raise ValueError('F07_AFFECTED_ROSTER')
    raw_objects = {}
    object_values = {}

    def f07_pin(path):
        key = str(path.relative_to(case)) if isinstance(path, PurePosixPath) else path
        if key in raw_objects:
            value = raw_objects[key]
            return {'size_bytes': len(value), 'sha256': f07_sha(value)}
        if key in affected_paths:
            raise ValueError('F07_DEPENDENCY_ORDER')
        return dict(accepted_pins[key])

    def f07_put(path, value, raw=False):
        key = str(path.relative_to(case)) if isinstance(path, PurePosixPath) else path
        if key not in affected_paths or key in raw_objects:
            raise ValueError('F07_OUTPUT_ROSTER')
        content = value if raw else f07_canonical(value)
        if type(content) is not bytes:
            raise ValueError('F07_OUTPUT_TYPE')
        if len(content) > 99413 or len(content) != accepted_pins[key]['size_bytes']:
            raise ValueError('F07_OUTPUT_SIZE')
        raw_objects[key] = content
        if not raw:
            object_values[key] = value

    loader_identity = copy.deepcopy(V_LOADER_IDENTITY)
    loader_identity.update(tool_cache=cache,
        executable_path=cache + '/Python/3.11.16/x64/bin/python3.11',
        library_path=cache + '/Python/3.11.16/x64/lib/libpython3.11.so.1.0',
        library_directory=cache + '/Python/3.11.16/x64/lib')
    loader_identity['mapped_library']['path'] = loader_identity['library_path']
    loader_identity['loader_environment'] = {'LD_LIBRARY_PATH': loader_identity['library_directory']}
    files = []
    for path, module in V_SOURCE_MODULES:
        info = f07_pin(root / 'restored' / path)
        if info['size_bytes'] != len(V_SOURCE_BYTES) or info['sha256'] != f07_sha(V_SOURCE_BYTES):
            raise ValueError('F07_SOURCE_LITERAL_PIN')
        files.append({'path': path, 'module': module, **info,
                      'git_blob': hashlib.sha1(b'blob ' + str(len(V_SOURCE_BYTES)).encode() +
                                              b'\x00' + V_SOURCE_BYTES).hexdigest()})
    manifest = {'schema': 'worker38-comparator-closure-v1', 'repository': C_REPOSITORY,
                'historical_commit': C_HISTORICAL, 'files': files}
    diagnostic = {name: 'a' * 64 for name in A_REQUIRED_PRODUCTION_PATHS + A_METADATA_PATHS}
    diagnostic['experiments/worker38-synthetic-profile/PROTOCOL.md'] = C_PROTOCOL_SHA256
    diagnostic['experiments/worker38-synthetic-profile/INTEGRATION-CONTRACT.json'] = C_CONTRACT_SHA256
    diagnostic['experiments/worker38-synthetic-profile/FINITE-PREPARATION-PLAN.json'] = C_FINITE_PLAN_SHA256
    diagnostic['experiments/worker38-synthetic-profile/comparator-source-manifest.json'] = f07_pin(root / 'source-manifest.json')['sha256']
    diagnostic.update({'experiments/worker38-synthetic-profile/inputs/comparator-7ac2f62c/' + entry['path'] + '.blob': entry['sha256'] for entry in files})
    diagnostic['experiments/worker38-synthetic-profile/upload-amendment/AMENDMENT.md'] = C_UPLOAD_AMENDMENT_SHA256
    diagnostic['experiments/worker38-synthetic-profile/upload-amendment/AMENDMENT-CONTRACT.json'] = C_UPLOAD_CONTRACT_SHA256
    diagnostic['experiments/worker38-synthetic-profile/upload-amendment/FINITE-COVERAGE-AMENDMENT.json'] = C_UPLOAD_FINITE_PLAN_SHA256
    diagnostic.update(A_UPLOAD_RECORD_PINS)
    tested_sources = {**diagnostic, **{path: 'c' * 64 for path in V_TESTED_EXTRA_PATHS}}
    go = {'schema': 'worker38-one-shot-admission-v1', 'admitted': True, 'repository': C_REPOSITORY, 'branch': A_BRANCH, 'preregistration_url': C_PREREGISTRATION, 'protocol_sha256': C_PROTOCOL_SHA256, 'admission_url': A_WEB + '/pull/40', 'head': V_HEAD, 'tree': V_TREE, 'runner': 'bandido-alcatraz-ci', 'runtime': C_RUNTIME, 'loader_pin': copy.deepcopy(V_LOADER_PIN), 'resources': C_RESOURCES, 'schedule': list(C_SCHEDULE), 'maximum_evaluator_calls': 40, 'games': 0, 'source_manifest_sha256': diagnostic['experiments/worker38-synthetic-profile/comparator-source-manifest.json'], 'diagnostic_files_sha256': diagnostic, 'cell_preflight_modules': sorted(V_INITIAL_MODULES), 'inherited_limits': V_INHERITED, 'stub_test_receipt_sha256': f07_pin(root / 'stub-test-receipt.json')['sha256'], 'postmerge_ci': {'run_id': A_CI_RUN, 'head': A_BASE_HEAD, 'status': 'completed', 'conclusion': 'success'}, 'reviews': [{'head': V_HEAD, 'tree': V_TREE, 'verdict': 'clean', 'reviewer': 'literal-reviewer-one', 'url': A_WEB + '/pull/40#issuecomment-100'}, {'head': V_HEAD, 'tree': V_TREE, 'verdict': 'clean', 'reviewer': 'literal-reviewer-two', 'url': A_WEB + '/pull/40#issuecomment-200'}]}

    def f07_request_map(go):
        return tuple(zip(A_INPUT_NAMES, ('/pulls/' + str(go['pr_number']), '/actions/runs/' + str(A_CI_RUN), '/actions/runs/' + str(go['current_source_ci']['run_id']), '/issues/comments/' + str(go['reviews'][0]['comment_id']), '/issues/comments/' + str(go['reviews'][1]['comment_id']), '/issues/comments/' + str(go['preregistration']['comment_id']), '/git/commits/' + go['head'])))

    def f07_independent_review_body(review, number):
        value = {'schema': 'worker38-owner-attested-native-review-v1', 'repository': A_REPOSITORY, 'pr_number': number, 'role': review['role'], 'native_reviewer_id': review['native_reviewer_id'], 'head': review['head'], 'tree': review['tree'], 'verdict': 'clean', 'complete_review': True, 'independent_review_attested': True, 'actionable_findings': {'P0': 0, 'P1': 0, 'P2': 0, 'P3': 0}, 'handoff_sha256': review['handoff_sha256'], 'report_sha256': review['report_sha256']}
        return A_REVIEW_START + '\n' + f07_canonical(value).decode() + A_REVIEW_END + '\n'

    # Authentication is the positive F07 branch only. The canonical admission
    # is a necessary internal preimage of provenance.body_sha256, and its
    # identity is checked against its invariant accepted pin in BOTH passes.
    value = copy.deepcopy(go)
    number = 40
    checked_file_sha256 = dict(tested_sources)
    checked_file_sha256.pop(A_FOCUSED_SOURCE_RECEIPT, None)
    receipt_pin = {'path': A_FOCUSED_SOURCE_RECEIPT, **f07_pin(root / 'stub-test-receipt.json')}
    source_map = diagnostic
    defaults = {'schema': 'worker38-one-shot-admission-v1', 'admitted': True, 'repository': A_REPOSITORY, 'owner': A_OWNER, 'branch': A_BRANCH, 'base_head': A_BASE_HEAD, 'base_tree': A_BASE_TREE, 'allocation_id': A_ALLOCATION, 'pr_number': number, 'protocol_sha256': C_PROTOCOL_SHA256, 'contract_sha256': C_CONTRACT_SHA256, 'finite_plan_sha256': C_FINITE_PLAN_SHA256, 'upload_amendment_sha256': C_UPLOAD_AMENDMENT_SHA256, 'upload_contract_sha256': C_UPLOAD_CONTRACT_SHA256, 'upload_finite_plan_sha256': C_UPLOAD_FINITE_PLAN_SHA256, 'upload_adoption_comment_id': C_UPLOAD_ADOPTION, 'preregistration_url': A_WEB + '/issues/2#issuecomment-603', 'admission_url': A_WEB + '/pull/' + str(number), 'head': F_HEAD, 'tree': F_TREE, 'runner': A_RUNNER, 'runtime': C_RUNTIME, 'loader_pin': F_LIBRARY_PIN, 'resources': C_RESOURCES, 'startup_resources': C_STARTUP_RESOURCES, 'schedule': list(C_SCHEDULE), 'maximum_evaluator_calls': 40, 'games': 0, 'source_manifest_sha256': C_SOURCE_MANIFEST_SHA256, 'diagnostic_files_sha256': source_map, 'checked_file_sha256': checked_file_sha256, 'cell_preflight_modules': F_INITIAL_MODULES, 'inherited_limits': F_INHERITED_LIMITS, 'stub_test_receipt_sha256': receipt_pin['sha256'], 'focused_source_receipt': receipt_pin, 'postmerge_ci': {'run_id': A_CI_RUN, 'head': A_BASE_HEAD, 'status': 'completed', 'conclusion': 'success'}, 'current_source_ci': {'run_id': 401, 'head': value.get('head', F_HEAD), 'status': 'completed', 'conclusion': 'success', 'completed_at': '2026-10-05T00:00:00Z'}}
    for key, default in defaults.items():
        value.setdefault(key, copy.deepcopy(default))
    existing_reviews = value.get('reviews')
    if existing_reviews is None or not all((type(review) is dict and 'comment_id' in review for review in existing_reviews)):
        value['reviews'] = []
        for role, reviewer, comment_id, report_hash in (('exhaustive', 'literal-reviewer-one', 601, 'a' * 64), ('adversarial', 'literal-reviewer-two', 602, 'b' * 64)):
            review = {'role': role, 'native_reviewer_id': reviewer, 'head': value['head'], 'tree': value['tree'], 'verdict': 'clean', 'url': value['admission_url'] + '#issuecomment-' + str(comment_id), 'comment_id': comment_id, 'handoff_sha256': 'c' * 64, 'report_sha256': report_hash}
            review['body_sha256'] = f07_sha(f07_independent_review_body(review, number).encode())
            value['reviews'].append(review)
    prereg_body = 'Invented preregistration of ' + value['protocol_sha256'] + '\nContract ' + value['contract_sha256'] + '\nFinite plan ' + value['finite_plan_sha256'] + '\n'
    if 'preregistration' not in value:
        match = value['preregistration_url'].rsplit('-', 1)[-1]
        prereg_id = int(match)
        value['preregistration'] = {'comment_id': prereg_id, 'url': value['preregistration_url'], 'body_sha256': f07_sha(prereg_body.encode()), 'protocol_sha256': value['protocol_sha256'], 'contract_sha256': value['contract_sha256'], 'finite_plan_sha256': value['finite_plan_sha256']}
    go = value
    admission_raw = f07_canonical(go)
    if {'size_bytes': len(admission_raw), 'sha256': f07_sha(admission_raw)} != f07_pin(root / 'admission-inputs/admission.json'):
        raise ValueError('F07_INVARIANT_ADMISSION')
    admission_body = A_START + '\n' + admission_raw.decode() + A_END + '\n' + A_DIGEST + ': ' + f07_sha(admission_raw) + '\n'
    workflow_run = '123'
    context = {'schema': 'worker38-github-request-context-v1', 'repository': A_REPOSITORY, 'actor': A_OWNER, 'triggering_actor': A_OWNER, 'event_name': 'pull_request', 'workflow_run': workflow_run, 'workflow_attempt': '1', 'runner_name': A_RUNNER, 'runner_tool_cache': cache, 'checkout_path': '/invented-checkout', 'runner_temp': '/invented-temp', 'durable_root': cache + '/worker38-synthetic-profile', 'attempt_path': cache + '/worker38-synthetic-profile/allocations/' + A_ALLOCATION + '/run-' + str(workflow_run) + '-attempt-1', 'attempt_id': 'worker38-' + str(workflow_run) + '-1', 'authentication': 'github-repository-read-token', 'requests': [{'name': name, 'method': 'GET', 'path': path} for name, path in f07_request_map(value)]}
    context['checkout_path'] = source_path
    context_raw = f07_canonical(context)
    f07_put(auth_rel + '/request-context.json', context_raw, raw=True)
    f07_put(root / 'admission-inputs/request-context.json', context_raw, raw=True)
    owner = {**F_OWNER, 'id': 456}
    proof = {'schema': 'worker38-authenticated-pr-admission-v1', 'repository': A_REPOSITORY,
        'event_name': 'pull_request', 'action': 'edited', 'first_admission': True,
        'pull_request_number': go['pr_number'], 'admission_url': go['admission_url'],
        'admission_sha256': f07_pin(root / 'admission-inputs/admission.json')['sha256'],
        'body_sha256': f07_sha(admission_body.encode()),
        'previous_body_sha256': f07_sha(b'Invented previous body\n'),
        'head': go['head'], 'tree': go['tree'], 'branch': A_BRANCH, 'base_head': A_BASE_HEAD,
        'sender': owner, 'author': owner, 'postmerge_ci': go['postmerge_ci'],
        'current_source_ci': go['current_source_ci'], 'reviews': go['reviews'],
        'preregistration': go['preregistration'], 'workflow_run': '123', 'workflow_attempt': '1',
        'attempt_path': context['attempt_path'], 'attempt_id': context['attempt_id'],
        'durable_root': context['durable_root'],
        'event_sha256': f07_pin(root / 'admission-inputs/event.json')['sha256'],
        'request_context_sha256': f07_sha(context_raw),
        'admission_input_hashes': {name: f07_pin(root / 'admission-inputs' / name)['sha256'] for name in A_INPUT_NAMES}}
    proof_raw = f07_canonical(proof)
    f07_put(auth_rel + '/provenance.json', proof_raw, raw=True)
    f07_put(root / 'admission-inputs/provenance.json', proof_raw, raw=True)
    runtime = {'implementation': 'cpython', 'version': '3.11.16', 'inherited_limits': copy.deepcopy(V_INHERITED), 'memory_cap': {'attempted': True, 'confirmed': True, 'readback': [536870912, 536870912]}, 'flags': {'optimize': 0, 'ignore_environment': 0, 'isolated': 0, 'no_site': 0, 'no_user_site': 1, 'dont_write_bytecode': 1}, 'state': {'limits': {**V_INHERITED, 'RLIMIT_AS': [536870912, 536870912]}, 'gc_enabled': True, 'gc_threshold': [700, 10, 10], 'profile_idle': True, 'trace_idle': True, 'threads': 1, 'timers': [[0.0, 0.0]] * 3}, 'memory_cap_restoration': 'retained_until_leaf_process_exit', 'files': {name: {'sha256': pin, 'size_bytes': size, 'device': 2049, 'inode': inode, 'mtime_ns': 1, 'mapped_identity_confirmed': True, 'observed_mapping': {'major': 8, 'minor': 1, 'inode': inode}} for name, pin, size, inode in (('executable', C_RUNTIME['executable_sha256'], 1234, 1233), ('library', V_LOADER_PIN['library_sha256'], V_LOADER_PIN['library_size_bytes'], 1234))}}
    handoff = {'schema': 'worker38-startup-handoff-v1', 'consumer': 'worker38-synthetic-profile-v1', 'boot_id': '11111111-2222-3333-4444-555555555555', 'measurement_monotonic_ns': 9340000000000, 'measurement_boottime_ns': 9340000000000, 'measurement_deadline_monotonic_ns': 11140000000000, 'measurement_deadline_boottime_ns': 11140000000000, 'attempt_path': original, 'source_path': source_path, 'head': V_HEAD, 'tree': V_TREE, 'workflow_run': '123', 'workflow_attempt': '1', 'admission_sha256': f07_pin(root / 'admission-inputs/admission.json')['sha256'], 'provenance_sha256': f07_pin(root / 'admission-inputs/provenance.json')['sha256'], 'runtime_sha256': f07_pin(root / 'runtime.json')['sha256'], 'source_map_sha256': f07_digest(go['checked_file_sha256']), 'restored_inventory_sha256': f07_digest(manifest['files']), 'startup_receipt_sha256': f07_pin(root / 'startup-receipt.json')['sha256']}
    f07_put(root / 'startup-handoff.json', handoff)
    handoff_text = 'version=worker38-handoff-v1\nhandoff_sha256=' + f07_digest(handoff) + '\n'
    handoff_text += ''.join(name + '=' + str(handoff[name]) + '\n' for name in A_HANDOFF_LINES)
    f07_put(root / 'measurement-handoff.txt', handoff_text.encode('ascii'), raw=True)

    def f07_runtime(index=None):
        inherited = {**V_INHERITED, 'RLIMIT_AS': [536870912, 536870912], 'RLIMIT_CPU': [720, 720]} if index is not None else V_INHERITED
        observed = copy.deepcopy(runtime)
        observed['inherited_limits'] = copy.deepcopy(inherited)
        observed['state']['limits'] = {**copy.deepcopy(inherited), 'RLIMIT_AS': [536870912, 536870912]}
        return {**C_RUNTIME, 'inherited_limits': copy.deepcopy(inherited), 'shared_startup_observation': observed, 'executable': loader_identity['executable_path'], 'loader': copy.deepcopy(loader_identity), 'flags': [loader_identity['executable_path'], '-B', '-s', script, '_cell', '--attempt', original, '--cell', str(index)], 'python_environment': {'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1'}, 'gc_enabled': True, 'gc_threshold': [700, 10, 10], 'effective_flags': {'dont_write_bytecode': 1, 'no_user_site': 1, 'ignore_environment': 0, 'isolated': 0, 'optimize': 0, 'no_site': 0}, 'address_space': [512 * 1024 ** 2] * 2}

    def f07_phase(index):
        return {'wall_seconds': 30 * index, 'parent_cpu_seconds': index, 'reaped_child_cpu_seconds': 30 * index, 'live_child_cpu_seconds': 0, 'cpu_seconds': 31 * index, 'wall_limit_seconds': 1800, 'cpu_limit_seconds': 1800}

    parent_runtime = f07_runtime()
    parent_runtime['flags'] = [loader_identity['executable_path'], '-B', '-s', script, 'measure']
    parent_runtime['address_space'] = [512 * 1024 ** 2] * 2
    parent_runtime['inherited_limits'] = V_INHERITED
    f07_put(root / 'source-runtime-preflight.json', {'phase': 'source_runtime_preflight', 'evaluator_starts': 0, 'runtime': parent_runtime, 'coordinator_address_space': [512 * 1024 ** 2] * 2, 'restored_source_inventory': files, 'diagnostic_files_sha256': diagnostic, 'measurement_anchor': handoff, 'timer_control': [{'deadline': 11140, 'before': 9340, 'after': 9340.001, 'requested': 1799.999, 'observed_before': 9340, 'observed_after': 9340.001, 'observed_countdown': 1799.998, 'observed_interval': 0.0, 'alarm_handler_confirmed': True, 'usr1_handler_confirmed': True, 'other_timers_idle': True, 'owner_pid': 1000}]})

    for identity in C_SCHEDULE:
        index = identity['cell']
        folder = root / 'cells' / ('%02d' % index)
        modules = {entry['module']: {'path': original + '/restored/' + entry['path'], **{key: entry[key] for key in ('size_bytes', 'sha256', 'git_blob')}} for entry in manifest['files']}
        f07_put(folder / 'source-runtime-preflight.json', {'phase': 'source_runtime_preflight', 'evaluator_starts': 0, 'runtime': f07_runtime(index), 'modules': {key: value for key, value in modules.items() if key in V_INITIAL_MODULES}})
        science = copy.deepcopy(V_SCIENCE)
        science.update(input_before=f07_digest(V_PUBLIC), input_after=f07_digest(V_PUBLIC),
                       rng_before=f07_digest(V_RNG), rng_after=f07_digest(V_RNG))
        cost = {'legal_enumerations': 1, 'previews': 0, 'exit_geometry_checks': 0, 'roots': 0}
        calls = {}
        for scope in ('candidate', 'reference'):
            start = {**identity, 'scope': scope, 'observation_sha256': f07_digest(V_PUBLIC), 'initial_rng_sha256': f07_digest(V_RNG), 'source_modules': {key: value for key, value in modules.items() if key in V_INITIAL_MODULES or (identity['condition'] == 'P' and key == 'bandido_alcatraz.simulate')}}
            f07_put(folder / (scope + '-start.json'), start)
            payload = {**start, 'chosen': None, 'scientific': science, 'scientific_sha256': f07_digest(science), 'rng_initial': V_RNG, 'rng_final': V_RNG, 'final_rng_sha256': f07_digest(V_RNG), 'timing': {'wall_seconds': 12, 'cpu_seconds': 10 if identity['condition'] == 'P' else 8}, 'physical_cost': cost if identity['condition'] == 'P' else None, 'physical_operation_caps_enforced': identity['condition'] == 'P', 'choice_events_observed': identity['condition'] == 'P', 'production_admissible': False}
            path = folder / (scope + '-return.json')
            f07_put(path, payload)
            evidence = {'path': path.relative_to(root).as_posix(), **f07_pin(path)}
            f07_put(folder / (scope + '-capture-confirmed.json'), evidence)
            calls[scope] = {'start_marker_durable': True, 'invocation_attempted': True, 'method_entered': True, 'returned': True, 'durable_capture_confirmed': True, 'evidence': evidence}
        f07_put(folder / 'cell-receipt.json', {**identity, 'schema': 'worker38-cell-receipt-v1', 'status': 'complete', 'actual_starts': 2, 'actual_starts_upper_bound': 2, 'pre_call_markers': 2, 'invocation_attempts': 2, 'actual_returns': 2, 'confirmed_captures': 2, 'calls': calls, 'hook_restored': True, 'timer_restored': True, 'peak_rss_kib': 1000, 'classification': None, 'error_type': None, 'error': None, 'failure': None, 'secondary_errors': [], 'phase': 'cell_complete'})
        log_name = 'supervisor-cell-%02d.log' % index
        supervisor = {'schema': 'worker38.supervision.v1', 'status': 'completed', 'reason': 'child_exit_zero', 'primary_outcome': {'status': 'completed', 'reason': 'child_exit_zero'}, 'secondary_failures': [], 'child_accounting_complete': True, 'phase_accounting_complete': True, 'spawn_attempted': True, 'spawn_initialization_complete': True, 'spawn_ownership_uncertain': False, 'spawn_discovery': 'not_required', 'spawn_recovered_pids': [], 'preservation_deadline_monotonic': None, 'preservation_transition_attempted': False, 'preservation_transition_complete': False, 'preservation_expired': False, 'preservation_blocked': False, 'spawned': True, 'pid': 2000 + index, 'parent_pid': 1000, 'parent_death_signal': 9, 'returncode': 0, 'exit_code': 0, 'signal': None, 'scientific_returns_inferred': False, 'active_call_at_stop': None, 'errors': [], 'cleanup': {'complete': True, 'sigkill_used': False, 'remaining_pids': [], 'errors': [], 'failure_details': []}, 'output_log': original + '/' + log_name, 'output_capture_mode': 'bounded_memory_then_post_cleanup_fsync', 'output_bytes_preserved': 0, 'output_bytes_observed': 0, 'output_durable': True, 'output_overflow': False, 'output_prefix_gap': False, 'output_pipe_tail': 'eof_observed', 'inherited_limits': {**V_INHERITED, 'RLIMIT_AS': [512 * 1024 ** 2] * 2}, 'limits': {'wall_seconds': 720, 'cpu_seconds': 720, 'address_space_bytes': 512 * 1024 ** 2, 'call_wall_seconds': 360, 'call_cpu_seconds': 360, 'output_log_limit_bytes': 63 * 1024 ** 2}, 'wall_seconds': 30, 'child_cpu_seconds': 30, 'child_high_water_rss_kib': 1000, 'cpu_tick_seconds': 0.01, 'poll_seconds': 0.02, 'phase': f07_phase(index)}
        f07_put(root / ('supervisor-cell-%02d.json' % index), supervisor)

    receipt = {'schema': 'worker38-attempt-v1', 'status': 'execution_complete', 'phase': 'verification_pending', 'admission_verified': True, 'admission_sha256': f07_pin(root / 'admission-inputs/admission.json')['sha256'], 'diagnostic_head': V_HEAD, 'diagnostic_tree': V_TREE, 'attempt_id': 'worker38-123-1', 'attempt_path': original, 'runner': 'bandido-alcatraz-ci', 'workflow_run': '123', 'workflow_attempt': '1', 'preregistration_url': C_PREREGISTRATION, 'source_manifest_sha256': go['source_manifest_sha256'], 'resources': C_RESOURCES, 'games': 0, 'schedule': list(C_SCHEDULE), 'maximum_evaluator_calls': 40, 'actual_starts': 40, 'actual_starts_upper_bound': 40, 'pre_call_markers': 40, 'actual_returns': 40, 'confirmed_captures': 40, 'current_cell': None, 'completed_prefix': list(range(1, 21)), 'capture_gaps': [], 'corrupt_evidence': [], 'unavailable_evidence': [], 'retained_failures': [], 'custody': 'pending', 'classification': None, 'supervisor_pid': 1000, 'supervisor_start_ticks': 934000, 'measurement_anchor': handoff, 'runtime_scope': {'idle_gate_passed': True, 'timer_owned': True, 'original_deadline': 11140.0}, 'resource_totals': {'supervision': object_values[root_rel + '/supervisor-cell-20.json'], 'P_operations': {'legal_enumerations': 20, 'previews': 0, 'exit_geometry_checks': 0}, 'phase': f07_phase(21)}}
    receipt['file_inventory'] = [
        {'path': path[len(root_rel) + 1:], **f07_pin(path)}
        for path in sorted(accepted_pins)
        if path.startswith(root_rel + '/') and path[len(root_rel) + 1:] not in
           ('receipt.json', 'measurement-phase-close.json', 'coordinator-restoration.json',
            'writer-exit-observation.json')]
    if len(receipt['file_inventory']) != 353:
        raise ValueError('F07_INVENTORY_COUNT')
    f07_put(root / 'receipt.json', receipt)
    f07_put(root / 'measurement-phase-close.json', {'schema': 'worker38-measurement-phase-close-v1', 'phase': f07_phase(22), 'computational_receipt': {'path': 'receipt.json', **f07_pin(root / 'receipt.json')}, 'includes_computational_receipt_publication': True, 'closing_proof_included_in_measurement': False, 'measurement_work_after_close': False, 'no_measurement_after_close': True, 'preservation_started_monotonic': 10000, 'preservation_deadline_monotonic': 10600})

    # Fixed original objects only. Moves and return aliases are the coordinator's
    # existing pointer-roster closure, not further bytes/physical copies here.
    if set(raw_objects) != affected_paths:
        raise ValueError('F07_AFFECTED_COUNT')
    for path in sorted(raw_objects):
        emit('input', 47, path, raw_objects[path], 'f07-original:' + path)


# Source construction only. These definitions are not an execution grant.
# Integration names: hashlib, json, PurePosixPath, verified ctx, and emit.

def inp_canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')


def inp_sha(raw):
    return hashlib.sha256(raw).hexdigest()


def inp_row(ctx, family, ordinal):
    matches = [row for row in ctx.accepted['families'][family]['selector_results']
               if row['ordinal'] == ordinal]
    if len(matches) != 1:
        raise ValueError('INP_ROW')
    return matches[0]


def inp_pin(ctx, family, ordinal, path):
    # Only source-owned finite path arguments are passed here. This never reads
    # a metadata-supplied filesystem path and never obtains observed output.
    values = [item['raw'] for item in inp_row(ctx, family, ordinal)['inputs']
              if item['relative_path'] == path and item['kind'] == 'file'
              and item['lineage'] == 'independent_literal_input'
              and isinstance(item.get('raw'), dict)]
    unique = {(value['size_bytes'], value['sha256']) for value in values}
    if len(unique) != 1:
        raise ValueError('INP_PIN')
    size, digest = next(iter(unique))
    if type(size) is not int or size < 0 or type(digest) is not str or len(digest) != 64:
        raise ValueError('INP_PIN_SHAPE')
    return {'size_bytes': size, 'sha256': digest}


def inp_check_invariant(raw, pin):
    if len(raw) != pin['size_bytes'] or inp_sha(raw) != pin['sha256']:
        raise ValueError('INP_INVARIANT')


def inp_case(namespace, ordinal):
    if namespace not in ('/workspace/shared/worker38-native-batch-04',
                          '/workspace/shared/worker38-native-batch-05'):
        raise ValueError('INP_NAMESPACE')
    return PurePosixPath(namespace) / ('c%04d' % ordinal)


def inp_handoff(ctx, namespace, ordinal, family, prefix, attempt, now,
                head, tree, workflow_run, provenance_sha256=None,
                source_path=None, checked=None):
    # p07_startup_files is transcribed as just its affected handoff object.
    # All unchanged physical inputs remain accepted opaque identities.
    base = inp_case(namespace, ordinal) / prefix
    auth = prefix + '/auth/'
    relative_attempt = prefix + '/' + attempt
    admission = inp_pin(ctx, family, ordinal, auth + 'admission.json')['sha256']
    provenance = (provenance_sha256 if provenance_sha256 is not None else
                  inp_pin(ctx, family, ordinal, auth + 'provenance.json')['sha256'])
    runtime = inp_pin(ctx, family, ordinal, relative_attempt + '/runtime.json')['sha256']
    startup = inp_pin(ctx, family, ordinal, relative_attempt + '/startup-receipt.json')['sha256']
    anchor = int(now * 10 ** 9)
    return inp_canonical({
        'schema': 'worker38-startup-handoff-v1',
        'consumer': 'worker38-synthetic-profile-v1',
        'boot_id': ctx.literal('tests/test_worker38_driver_integration.py', 'LITERAL_BOOT_ID'),
        'measurement_monotonic_ns': anchor, 'measurement_boottime_ns': anchor,
        'measurement_deadline_monotonic_ns': anchor + 1800 * 10 ** 9,
        'measurement_deadline_boottime_ns': anchor + 1800 * 10 ** 9,
        'attempt_path': str(base / attempt),
        'source_path': str(base) if source_path is None else str(source_path),
        'head': head, 'tree': tree, 'workflow_run': workflow_run, 'workflow_attempt': '1',
        'admission_sha256': admission, 'provenance_sha256': provenance,
        'runtime_sha256': runtime,
        'source_map_sha256': inp_sha(inp_canonical({} if checked is None else checked)),
        'restored_inventory_sha256': inp_sha(inp_canonical([])),
        'startup_receipt_sha256': startup})


def inp_ordinary_startups(ctx, namespace, emit):
    # Exact source call order within each of the 29 ordinary P07 rows.
    simple = (205, 206, 208, 216, 217, 223, 224, 228, 229, 231,
              237, 238, 239, 240, 242, 243, 247, 264, 265)
    roster = [(ordinal, (('attempt', 1000.0),)) for ordinal in simple]
    roster.extend((
        (204, (('attempt-prerequisite-runtime', 1000.0),
               ('attempt-prerequisite-source', 1000.0))),
        (241, tuple(('event-attempt-' + str(i), 1000.0) for i in range(4))),
        (258, (('attempt-loader-False', 1000.0), ('attempt-loader-True', 1000.0))),
        (263, (('attempt', 1000.0), ('attempt-arm-delay', 100.0))),
        (266, tuple(('attempt-discovered-' + kind, 1000.0) for kind in
                    ('write_expiry', 'read_expiry', 'write_integrity_at_expiry'))),
        (267, (('attempt-arm-before', 1900.0), ('attempt-arm-after', 1900.0))),
        (268, (('attempt-callback-metadata', 1000.0),
               ('attempt-callback-missing_timestamp', 1000.0))),
        (269, tuple(('attempt-coordinator-' + kind, 1000.0) for kind in
                    ('disable_before', 'handler_before', 'disable_after_memory',
                     'handler_after_memory', 'disable_mismatch', 'handler_mismatch',
                     'disable_getter', 'handler_getter'))),
        (271, (('attempt-handler-coordinator', 1000.0),)),
        (273, (('attempt-partial-True', 1000.0), ('attempt-partial-False', 1000.0))),
    ))
    for ordinal, variants in sorted(roster):
        for index, (attempt, now) in enumerate(variants):
            path = 't01/' + attempt + '/startup-handoff.json'
            raw = inp_handoff(ctx, namespace, ordinal, 'P07', 't01', attempt,
                              now, 'a' * 40, 'b' * 40, '123')
            emit('input', ordinal, path, raw, 'inp-startup-%03d-%02d' % (ordinal, index))
    raw = inp_handoff(ctx, namespace, 48, 'P04', 't02', 'attempt', 1000.0,
                      'a' * 40, 'b' * 40, '123')
    emit('input', 48, 't02/attempt/startup-handoff.json', raw, 'inp-f08-startup')


def inp_symlinks_and_journal(ctx, namespace, emit):
    # Nine exact link objects; T008's two accepted occurrences share one state.
    links = (
        (9, 't01/attempt', 't01/actual'),
        (72, 't01/cache', 't01/cache-target'),
        (173, 't05/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0',
         't05/toolcache/Python/3.11.16/x64/lib/target'),
        (173, 't06/toolcache/Python/3.11.16/x64/lib',
         't06/toolcache/Python/3.11.16/x64/other-lib'),
        (260, 't01/github-output-link', 't01/github-output-2'),
        (336, 't01/wrapper-link-6', 't01/literal-github-download.zip-5'),
        (342, 't01/unsafe-source-1/link', 't01/unsafe-source-1/keep'),
        (342, 't01/literal-cache-11/worker38-synthetic-profile/allocations/'
              'worker38-synthetic-profile-01/transport-123-attempt-1/part-001.bin',
              't01/invented-sibling-12'),
        (342, 't01/literal-cache-15/worker38-synthetic-profile/allocations/'
              'worker38-synthetic-profile-01/transport-123-attempt-1',
              't01/invented-sibling-16'),
    )
    for index, (ordinal, path, target) in enumerate(links):
        raw = str(inp_case(namespace, ordinal) / target).encode('ascii')
        emit('input', ordinal, path, raw, 'inp-link-%02d' % index)
    raw = (str(inp_case(namespace, 168) / 't01') +
           ' {"timing":7,"untouched":"a"}\n').encode('utf-8')
    emit('input', 168, 't01/journal', raw, 'inp-core20-journal')


def inp_er_checked(ctx, ordinal):
    experiment = 'experiments/worker38-synthetic-profile/'
    metadata = tuple(experiment + name for name in (
        'PROTOCOL.md', 'INTEGRATION-CONTRACT.json', 'FINITE-PREPARATION-PLAN.json',
        'SOURCE-GROUNDING.json', 'comparator-source-manifest.json',
        'upload-amendment/AMENDMENT.md', 'upload-amendment/AMENDMENT-CONTRACT.json',
        'upload-amendment/FINITE-COVERAGE-AMENDMENT.json',
        'upload-amendment/SOURCE-OBSERVATION.json',
        'upload-amendment/REPAIR-DISPOSITION.json', 'upload-amendment/HANDOFF.json'))
    tests = (
        'tests/test_worker37_bootstrap.py', 'tests/worker38_literal_fixtures.py',
        'tests/worker38_constructor_source.txt', 'tests/test_worker38_bootstrap_integration.py',
        'tests/test_worker38_core.py', 'tests/test_worker38_driver_integration.py',
        'tests/test_worker38_cell_integration.py', 'tests/test_worker38_supervision.py',
        'tests/test_worker38_transport.py', 'tests/test_worker38_verify_integration.py',
        'evidence-design/run-worker38-fixed-preparation.py',
        'evidence-design/worker38-fixed-fixtures.json')
    production = ctx.literal('scripts/worker38/admission.py', 'REQUIRED_PRODUCTION_PATHS')
    manifest = ctx.json(experiment + 'comparator-source-manifest.json')
    if len(manifest['files']) != 21:
        raise ValueError('INP_ER_MANIFEST')
    blobs = tuple(experiment + 'inputs/comparator-7ac2f62c/' + entry['path'] + '.blob'
                  for entry in manifest['files'])
    diagnostics = set(production) | set(metadata) | set(blobs)
    names = diagnostics | set(tests)
    checked = {name: inp_pin(ctx, 'P07', ordinal,
                            't01/metadata-shared-checkout/' + name)['sha256']
               for name in sorted(names)}
    receipt_name = experiment + 'focused-preparation-receipt.json'
    receipt = {'path': receipt_name, **inp_pin(ctx, 'P07', ordinal,
                    't01/metadata-shared-checkout/' + receipt_name)}
    return checked, diagnostics, receipt


def inp_er_resources():
    # Fixed arithmetic transcription of common.py:42-60, not an evaluator.
    operations = {'legal_enumerations': 32768, 'previews': 32768,
                  'exit_geometry_checks': 16384}
    call_caps = {**operations, 'roots': 16384, 'wall_seconds': 360, 'cpu_seconds': 360}
    mib = 1024 ** 2
    resources = {
        'per_call': {name: dict(call_caps) for name in ('control', 'candidate', 'reference')},
        'whole_cell_wall_seconds': 720, 'whole_cell_cpu_seconds': 720,
        'whole_wrapper_operations': {key: 2 * value for key, value in operations.items()},
        'total_operations': dict.fromkeys(operations, 1000000),
        'measurement_wall_seconds': 1800, 'measurement_cpu_seconds': 1800,
        'address_space_bytes': 512 * mib, 'evidence_bytes': 64 * mib,
        'receipt_bytes': mib, 'trace_bytes': 16 * mib, 'line_bytes': 8 * mib,
        'archive_bytes': 64 * mib, 'part_bytes': 30 * mib,
        'verification_wall_seconds': 600, 'workflow_minutes': 45,
        'free_storage_bytes': 1024 * mib}
    order = ([(1, n, condition) for n in (0, 4, 8, 40, 48) for condition in ('P', 'U')] +
             [(2, n, condition) for n in (48, 40, 8, 4, 0) for condition in ('U', 'P')])
    schedule = [{'cell': index + 1, 'repetition': repetition, 'size': size,
                 'condition': condition}
                for index, (repetition, size, condition) in enumerate(order)]
    return resources, schedule


def inp_er_go(ctx, checked, diagnostics, receipt):
    # Necessary invariant scalar/hash dependencies of the selected provenance.
    # This does not construct the seven auth files, event file or any archive.
    common = 'scripts/worker38/common.py'
    admission = 'scripts/worker38/admission.py'
    fixture = 'tests/worker38_literal_fixtures.py'
    repository = ctx.literal(admission, 'REPOSITORY')
    web = 'https://github.com/' + repository
    head = ctx.literal(fixture, 'HEAD')
    tree = ctx.literal(fixture, 'TREE')
    resources, schedule = inp_er_resources()
    value = {
        'schema': 'worker38-one-shot-admission-v1', 'admitted': True,
        'repository': repository, 'owner': ctx.literal(admission, 'OWNER'),
        'branch': ctx.literal(admission, 'BRANCH'),
        'base_head': ctx.literal(admission, 'BASE_HEAD'),
        'base_tree': ctx.literal(admission, 'BASE_TREE'),
        'allocation_id': ctx.literal(admission, 'ALLOCATION'), 'pr_number': 101,
        'protocol_sha256': ctx.literal(common, 'PROTOCOL_SHA256'),
        'contract_sha256': ctx.literal(common, 'CONTRACT_SHA256'),
        'finite_plan_sha256': ctx.literal(common, 'FINITE_PLAN_SHA256'),
        'upload_amendment_sha256': ctx.literal(common, 'UPLOAD_AMENDMENT_SHA256'),
        'upload_contract_sha256': ctx.literal(common, 'UPLOAD_CONTRACT_SHA256'),
        'upload_finite_plan_sha256': ctx.literal(common, 'UPLOAD_FINITE_PLAN_SHA256'),
        'upload_adoption_comment_id': ctx.literal(common, 'UPLOAD_ADOPTION'),
        'preregistration_url': ctx.literal(common, 'PREREGISTRATION'),
        'admission_url': web + '/pull/101', 'head': head, 'tree': tree,
        'runner': ctx.literal(admission, 'RUNNER'),
        'runtime': ctx.literal(common, 'RUNTIME'),
        'loader_pin': ctx.literal('tests/test_worker38_driver_integration.py', 'LITERAL_LOADER_PIN'),
        'resources': resources, 'startup_resources': ctx.literal(common, 'STARTUP_RESOURCES'),
        'schedule': schedule, 'maximum_evaluator_calls': 40, 'games': 0,
        'source_manifest_sha256': ctx.literal(common, 'SOURCE_MANIFEST_SHA256'),
        'diagnostic_files_sha256': {name: checked[name] for name in sorted(diagnostics)},
        'checked_file_sha256': dict(checked),
        'cell_preflight_modules': ctx.literal(fixture, 'INITIAL_MODULES'),
        'inherited_limits': ctx.literal(fixture, 'INHERITED_LIMITS'),
        'stub_test_receipt_sha256': receipt['sha256'], 'focused_source_receipt': dict(receipt),
        'postmerge_ci': {'run_id': ctx.literal(admission, 'CI_RUN'),
                        'head': ctx.literal(admission, 'BASE_HEAD'),
                        'status': 'completed', 'conclusion': 'success'},
        'current_source_ci': {'run_id': 401, 'head': head, 'status': 'completed',
                             'conclusion': 'success', 'completed_at': '2026-10-05T00:00:00Z'}}
    reviews = []
    for role, reviewer, comment_id, report_hash in (
            ('exhaustive', 'literal-reviewer-one', 601, 'a' * 64),
            ('adversarial', 'literal-reviewer-two', 602, 'b' * 64)):
        review = {'role': role, 'native_reviewer_id': reviewer, 'head': head, 'tree': tree,
                  'verdict': 'clean', 'url': value['admission_url'] + '#issuecomment-' + str(comment_id),
                  'comment_id': comment_id, 'handoff_sha256': 'c' * 64, 'report_sha256': report_hash}
        body_value = {
            'schema': 'worker38-owner-attested-native-review-v1', 'repository': repository,
            'pr_number': 101, 'role': role, 'native_reviewer_id': reviewer,
            'head': head, 'tree': tree, 'verdict': 'clean', 'complete_review': True,
            'independent_review_attested': True,
            'actionable_findings': {'P0': 0, 'P1': 0, 'P2': 0, 'P3': 0},
            'handoff_sha256': review['handoff_sha256'], 'report_sha256': report_hash}
        body = ('WORKER38_NATIVE_REVIEW_JSON\n' + inp_canonical(body_value).decode('utf-8') +
                'END_WORKER38_NATIVE_REVIEW_JSON\n').encode('utf-8')
        review['body_sha256'] = inp_sha(body)
        reviews.append(review)
    value['reviews'] = reviews
    prereg_body = ('Invented preregistration of ' + value['protocol_sha256'] +
                  '\nContract ' + value['contract_sha256'] +
                  '\nFinite plan ' + value['finite_plan_sha256'] + '\n').encode('utf-8')
    value['preregistration'] = {
        'comment_id': int(value['preregistration_url'].rsplit('-', 1)[-1]),
        'url': value['preregistration_url'], 'body_sha256': inp_sha(prereg_body),
        'protocol_sha256': value['protocol_sha256'],
        'contract_sha256': value['contract_sha256'],
        'finite_plan_sha256': value['finite_plan_sha256']}
    return value


def inp_er_variant(ctx, namespace, ordinal, label, checked, diagnostics, receipt, emit):
    # Only source_map and receipt_size are deliberately stale. They are never
    # repaired or rewritten by broad digest replacement.
    checked = dict(checked)
    receipt = dict(receipt)
    if label == 'source_map':
        checked['tests/fixed-obsolete-source.py'] = 'f' * 64
    if label == 'receipt_size':
        receipt['size_bytes'] += 1
    go = inp_er_go(ctx, checked, diagnostics, receipt)
    base_path = 't01/metadata-' + label
    attempt = ('tool-cache/worker38-synthetic-profile/allocations/'
               'worker38-synthetic-profile-01/run-9001-attempt-1')
    retained = base_path + '/' + attempt + '/admission-inputs/'
    base = inp_case(namespace, ordinal) / base_path
    cache = base / 'tool-cache'
    repo = inp_case(namespace, ordinal) / 't01/metadata-shared-checkout'
    names = ctx.literal('scripts/worker38/admission.py', 'INPUT_NAMES')
    request_paths = (
        '/pulls/101', '/actions/runs/' + str(go['postmerge_ci']['run_id']),
        '/actions/runs/401', '/issues/comments/601', '/issues/comments/602',
        '/issues/comments/' + str(go['preregistration']['comment_id']), '/git/commits/' + go['head'])
    context = {
        'schema': 'worker38-github-request-context-v1', 'repository': go['repository'],
        'actor': go['owner'], 'triggering_actor': go['owner'], 'event_name': 'pull_request',
        'workflow_run': '9001', 'workflow_attempt': '1', 'runner_name': go['runner'],
        'runner_tool_cache': str(cache), 'checkout_path': str(repo),
        'runner_temp': str(base / 'runner-temp'),
        'durable_root': str(cache / 'worker38-synthetic-profile'),
        'attempt_path': str(base / attempt), 'attempt_id': 'worker38-9001-1',
        'authentication': 'github-repository-read-token',
        'requests': [{'name': name, 'method': 'GET', 'path': path}
                     for name, path in zip(names, request_paths)]}
    context_raw = inp_canonical(context)
    admission_pin = inp_pin(ctx, 'P07', ordinal, retained + 'admission.json')
    # This sole invariant top-level serialization is a prerequisite for the
    # otherwise unavailable nested PR-body hash. Its bytes never become an
    # emitted object or a new top-level identity and must equal the accepted pin.
    admission_raw = inp_canonical(go)
    inp_check_invariant(admission_raw, admission_pin)
    marker = ctx.literal('scripts/worker38/admission.py', 'MARKER')
    body = (marker + '_JSON\n' + admission_raw.decode('utf-8') +
            'END_' + marker + '_JSON\n' + marker + '_SHA256: ' +
            admission_pin['sha256'] + '\n').encode('utf-8')
    owner = ctx.literal('tests/worker38_literal_fixtures.py', 'OWNER')
    provenance = {
        'schema': 'worker38-authenticated-pr-admission-v1', 'repository': go['repository'],
        'event_name': 'pull_request', 'action': 'edited', 'first_admission': True,
        'pull_request_number': 101, 'admission_url': go['admission_url'],
        'admission_sha256': admission_pin['sha256'], 'body_sha256': inp_sha(body),
        'previous_body_sha256': inp_sha(b'Invented previous body\n'),
        'head': go['head'], 'tree': go['tree'], 'branch': go['branch'],
        'base_head': go['base_head'], 'sender': owner, 'author': dict(owner),
        'postmerge_ci': go['postmerge_ci'], 'current_source_ci': go['current_source_ci'],
        'reviews': go['reviews'], 'preregistration': go['preregistration'],
        'workflow_run': '9001', 'workflow_attempt': '1',
        'attempt_path': context['attempt_path'], 'attempt_id': context['attempt_id'],
        'durable_root': context['durable_root'],
        'event_sha256': inp_pin(ctx, 'P07', ordinal, retained + 'event.json')['sha256'],
        'request_context_sha256': inp_sha(context_raw),
        'admission_input_hashes': {name: inp_pin(ctx, 'P07', ordinal, retained + name)['sha256']
                                 for name in names}}
    provenance_raw = inp_canonical(provenance)
    handoff_raw = inp_handoff(ctx, namespace, ordinal, 'P07', base_path, attempt,
                              1000.0, go['head'], go['tree'], '9001',
                              inp_sha(provenance_raw), repo, checked)
    # Emission sequence mirrors the original source: original auth context,
    # original auth provenance, startup handoff, retained provenance, retained
    # context. Original missing/newline-tamper auth states remain invariant.
    states = (
        (base_path + '/auth/request-context.json', context_raw, 'auth-context'),
        (base_path + '/auth/provenance.json', provenance_raw, 'auth-provenance'),
        (base_path + '/' + attempt + '/startup-handoff.json', handoff_raw, 'handoff'),
        (retained + 'provenance.json', provenance_raw, 'retained-provenance'),
        (retained + 'request-context.json', context_raw, 'retained-context'))
    for path, raw, role in states:
        emit('input', ordinal, path, raw, 'inp-er-%03d-%s-%s' % (ordinal, label, role))


def inp_authenticated_metadata(ctx, namespace, emit):
    names = ctx.literal('scripts/worker38/admission.py', 'INPUT_NAMES')
    if names != ('pull-request.json', 'postmerge-ci.json', 'current-source-ci.json',
                 'review-exhaustive.json', 'review-adversarial.json',
                 'preregistration.json', 'diagnostic-commit.json'):
        raise ValueError('INP_ER_NAMES')
    for ordinal in (274, 275):
        checked, diagnostics, receipt = inp_er_checked(ctx, ordinal)
        labels = (('valid',) + names + ('source_map', 'receipt_size') if ordinal == 274
                  else tuple('tamper-' + name for name in names))
        for label in labels:
            inp_er_variant(ctx, namespace, ordinal, label, checked, diagnostics, receipt, emit)


def build_other_inputs(ctx, namespace, emit):
    # Exactly 143 source-owned path/type/size/hash states across 39 rows, with
    # 109 raw identities. Coordinator joins all 144 accepted occurrences,
    # validates the complete old pass first, then admits any new pass.
    inp_case(namespace, 9)
    for source in (
            'tests/test_worker38_bootstrap_integration.py',
            'tests/test_worker37_bootstrap.py', 'tests/test_worker38_core.py',
            'tests/test_worker38_driver_integration.py',
            'tests/test_worker38_transport.py', 'tests/worker38_literal_fixtures.py',
            'scripts/worker38/common.py', 'scripts/worker38/admission.py'):
        ctx.text(source)
    inp_symlinks_and_journal(ctx, namespace, emit)
    inp_ordinary_startups(ctx, namespace, emit)
    inp_authenticated_metadata(ctx, namespace, emit)


def custody_canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')


def custody_digest(value):
    return hashlib.sha256(custody_canonical(value)).hexdigest()


def custody_fail(code):
    # Static codes only. No metadata, path, raw object, or exception text leaks.
    raise ValueError(code)


def custody_rows():
    # (accepted verifier index, original397 ordinal, ordered operation ordinals)
    return ((10, 365, (403,)), (11, 366, (403, 437)), (12, 367, (375,)),
            (13, 368, tuple(range(375, 383))), (14, 369, tuple(range(375, 386))),
            (36, 391, (375,)), (37, 392, (375,)), (38, 393, (375, 376, 377, 378)),
            (39, 394, (375,)), (40, 395, (375, 376)), (41, 396, (375, 376)))


def custody_phase(index):
    return {'wall_seconds': 30 * index, 'parent_cpu_seconds': index,
            'reaped_child_cpu_seconds': 30 * index, 'live_child_cpu_seconds': 0,
            'cpu_seconds': 31 * index, 'wall_limit_seconds': 1800,
            'cpu_limit_seconds': 1800}


def custody_schedule():
    # Closed transcription of common.py:57-60, not expression evaluation.
    order = ([(1, size, condition) for size in (0, 4, 8, 40, 48)
              for condition in ('P', 'U')]
             + [(2, size, condition) for size in (48, 40, 8, 4, 0)
                for condition in ('U', 'P')])
    return [{'cell': index + 1, 'repetition': rep, 'size': size,
             'condition': condition}
            for index, (rep, size, condition) in enumerate(order)]


def custody_identity(state):
    return {key: state[key] for key in ('type', 'size_bytes', 'sha256')}


def custody_unique_state(states, relative_path):
    found = [state for state in states if state['relative_path'] == relative_path]
    if len(found) != 1 or found[0]['type'] != 'file':
        custody_fail('CUSTODY_FIXED_IDENTITY_MISSING')
    return found[0]


def custody_generation(row, generation_number, old_namespace):
    generations = row['custody_input_generations']
    expected_count = 2 if row['ordinal'] == 366 else 1
    if len(generations) != expected_count or not 1 <= generation_number <= expected_count:
        custody_fail('CUSTODY_GENERATION_ROSTER')
    generation = generations[generation_number - 1]
    relative = 't01/custody-inputs-%d' % generation_number
    if generation['directory'] != old_namespace + '/c%04d/' % row['ordinal'] + relative:
        custody_fail('CUSTODY_GENERATION_DIRECTORY')
    inventory = generation['inventory']
    if (len(inventory) != 357 or [entry['path'] for entry in inventory] != row['untouched_baseline_paths']
            or any(set(entry) != {'path', 'size_bytes', 'sha256'} for entry in inventory)):
        custody_fail('CUSTODY_INVARIANT_INVENTORY')
    assets = generation['asset_states']
    expected_names = ('fresh-download-part.bin', 'fresh-transport-manifest.json',
                      'github-provider-wrapper-001.zip', 'upload-part.bin',
                      'upload-transport-manifest.json')
    if [entry['relative_path'] for entry in assets] != [relative + '/' + name for name in expected_names]:
        custody_fail('CUSTODY_INVARIANT_ASSET_ROSTER')
    if any(entry['type'] != 'file' or entry['lineage'] != 'independent_input'
           or entry['asset_role'] != 'fixed_custody_input_asset' for entry in assets):
        custody_fail('CUSTODY_INVARIANT_ASSET_LINEAGE')
    if (custody_identity(assets[0]) != custody_identity(assets[3])
            or custody_identity(assets[1]) != custody_identity(assets[4])
            or assets[0]['size_bytes'] != generation['archive_size']
            or assets[0]['sha256'] != generation['archive_sha256']):
        custody_fail('CUSTODY_INVARIANT_ASSET_IDENTITY')
    # Reference accepted identities only: no auth/raw tree/archive reconstruction.
    return generation, relative, assets


def custody_planned_report(ctx, row, namespace, generation_number, inventory):
    cells = []
    for identity in custody_schedule():
        cpu = 10 if identity['condition'] == 'P' else 8
        if identity['condition'] == 'U' and identity['size'] in (40, 48):
            if row['ordinal'] == 365:
                cpu = 9 if identity['repetition'] == 1 else 7
            elif row['ordinal'] == 366:
                first, second = ((8.01, 8.01) if generation_number == 1 else (9.01, 6))
                cpu = first if identity['repetition'] == 1 else second
        cells.append({**identity, 'candidate': {'wall_seconds': 12, 'cpu_seconds': cpu},
                      'reference': {'wall_seconds': 12, 'cpu_seconds': cpu}})
    admission = custody_unique_state(row['inputs'], 't01/external-auth/admission.json')
    provenance = custody_unique_state(row['inputs'], 't01/external-auth/provenance.json')
    base = namespace + '/c%04d/t01' % row['ordinal']
    binding = {'trusted_admission_path': base + '/external-auth/admission.json',
               'trusted_admission_sha256': admission['sha256'],
               'expected_head': ctx.literal('tests/test_worker38_verify_integration.py', 'HEAD'),
               'expected_tree': ctx.literal('tests/test_worker38_verify_integration.py', 'TREE'),
               'root': base + '/raw-attempt',
               'trusted_provenance_path': base + '/external-auth/provenance.json',
               'trusted_provenance_sha256': provenance['sha256'],
               'expected_workflow_run': '123', 'expected_workflow_attempt': '1'}
    return {'schema': 'worker38-offline-verification-v2', 'complete': True,
            'cells': cells, 'total_P_operations': {'legal_enumerations': 20, 'previews': 0,
                                                 'exit_geometry_checks': 0},
            'resource_phase': custody_phase(22), 'prepublication_resource_phase': custody_phase(21),
            'raw_inventory': inventory, 'binding': binding, 'custody': 'pending',
            'classification': None}


def custody_receipt(ctx, row, namespace, generation_number):
    old_namespace = '/workspace/shared/worker38-native-batch-04'
    generation, relative, assets = custody_generation(row, generation_number, old_namespace)
    directory = namespace + '/c%04d/' % row['ordinal'] + relative
    inventory = copy.deepcopy(generation['inventory'])
    archive_size, archive_sha = generation['archive_size'], generation['archive_sha256']
    manifest_pin, wrapper_pin = assets[1], assets[2]
    folder = ctx.literal('scripts/worker38/verify.py', 'CANONICAL_FOLDER')
    repository = ctx.literal('scripts/worker38/common.py', 'REPOSITORY')
    part = {'order': 1, 'path': 'part-001.bin', 'size': archive_size, 'sha256': archive_sha}
    event = {'provider': 'google_drive', 'file_id': 'literal-Drive-file-one',
             'size': archive_size, 'sha256': archive_sha}
    descriptor = {**part, 'drive_file_id': 'literal-Drive-file-one',
                  'direct_url': 'https://drive.google.com/file/d/literal-Drive-file-one/view',
                  'upload_input_path': directory + '/upload-part.bin',
                  'readback_path': directory + '/fresh-download-part.bin',
                  'upload_receipt': {**event, 'operation': 'upload', 'event_id': 'literal-upload-event',
                                     'completed_at': '2026-10-03T00:00:00Z', 'parent_folder_id': folder},
                  'download_receipt': {**event, 'operation': 'download', 'event_id': 'literal-download-event',
                                       'completed_at': '2026-10-03T00:01:00Z'}}
    manifest = {'schema': 'worker38.transport.v1',
                'files': [{'path': entry['path'], 'size': entry['size_bytes'], 'sha256': entry['sha256']}
                          for entry in inventory],
                'raw_size': sum(entry['size_bytes'] for entry in inventory), 'parts': [part],
                'archive': {'path': 'attempt.zip', 'format': 'zip-stored-v1',
                            'size': archive_size, 'sha256': archive_sha},
                'limits': {'raw_bytes': 67108864, 'archive_bytes': 67108864,
                           'part_bytes': 31457280, 'provider_zip_strictly_below_bytes': 33554432}}
    # The embedded manifest object is source-built; its file identity is an accepted
    # invariant reference. This function never serializes an invariant manifest/ZIP.
    wrapper_info = {'size': wrapper_pin['size_bytes'], 'sha256': wrapper_pin['sha256']}
    wrapper = {'order': 1, 'part_path': 'part-001.bin', 'member_name': 'part-001.bin',
               'path': directory + '/github-provider-wrapper-001.zip', **wrapper_info,
               'download_receipt': {'provider': 'github_actions', 'operation': 'download',
                   'repository': repository, 'run_id': '123', 'run_attempt': '1', 'artifact_id': '456',
                   'artifact_name': 'worker38-123-1-part-001', 'event_id': 'literal-provider-download',
                   'completed_at': '2026-10-03T00:00:00Z', **wrapper_info}}
    manifest_event = {'provider': 'google_drive', 'file_id': 'literal-Drive-manifest',
                      'size': manifest_pin['size_bytes'], 'sha256': manifest_pin['sha256']}
    report = custody_planned_report(ctx, row, namespace, generation_number, inventory)
    return {'schema': 'worker38-authenticated-custody-v2', 'status': 'verified',
            'provider_wrappers': [wrapper],
            'provider_upload_outcome': {'schema': 'worker38-provider-upload-outcome-v1',
                'workflow_run': '123', 'workflow_attempt': '1', 'action': './.github/actions/worker38-upload',
                'status': 'completed', 'conclusion': 'success', 'admission_exit_status': 0,
                'coordinator_exit_status': 0, 'preservation_exit_status': 0,
                'started_at': '2026-10-02T23:59:58Z', 'completed_at': '2026-10-02T23:59:59Z'},
            'authenticated_by': 'parent-connected-Drive-readback', 'folder_id': folder,
            'verification_sha256': custody_digest(report), 'raw_inventory': inventory,
            'files': [descriptor], 'transport_manifest': manifest,
            'manifest_file': {'path': 'transport-manifest.json',
                'size': manifest_pin['size_bytes'], 'sha256': manifest_pin['sha256'],
                'drive_file_id': 'literal-Drive-manifest',
                'direct_url': 'https://drive.google.com/file/d/literal-Drive-manifest/view',
                'upload_input_path': directory + '/upload-transport-manifest.json',
                'readback_path': directory + '/fresh-transport-manifest.json',
                'upload_receipt': {**manifest_event, 'operation': 'upload', 'event_id': 'literal-manifest-upload',
                                  'completed_at': '2026-10-03T00:00:00Z', 'parent_folder_id': folder},
                'download_receipt': {**manifest_event, 'operation': 'download',
                                    'event_id': 'literal-manifest-readback',
                                    'completed_at': '2026-10-03T00:01:00Z'}}}


def custody_variants(ordinal, original):
    # Closed negative-test transcriptions; no metadata-provided edit recipe.
    yield original
    if ordinal == 368:
        for key, value in (('status', 'pending'), ('status', 'blocked'),
                           ('folder_id', 'other-folder'), ('verification_sha256', 'f' * 64),
                           ('raw_inventory', []), ('files', [])):
            altered = copy.deepcopy(original)
            altered[key] = value
            yield altered
        yield original
    elif ordinal == 369:
        for key, value in (('size', 1), ('sha256', 'f' * 64), ('drive_file_id', ''),
                           ('direct_url', 'https://example.com/file')):
            altered = copy.deepcopy(original)
            altered['files'][0][key] = value
            yield altered
        for key, value in (('event_id', 'literal-upload-event'), ('completed_at', '2026-10-02T00:00:00Z')):
            altered = copy.deepcopy(original)
            altered['files'][0]['download_receipt'][key] = value
            yield altered
        altered = copy.deepcopy(original)
        altered['files'][0]['upload_receipt']['parent_folder_id'] = 'wrong-folder'
        yield altered
        altered = copy.deepcopy(original)
        altered['files'][0]['readback_path'] = original['files'][0]['upload_input_path']
        yield altered
        altered = copy.deepcopy(original)
        altered['transport_manifest']['files'] = []
        yield altered
        yield original
    elif ordinal == 393:
        altered = copy.deepcopy(original)
        del altered['provider_wrappers']
        yield altered
        for value in (None, []):
            altered = copy.deepcopy(original)
            altered['provider_wrappers'] = value
            yield altered
    elif ordinal == 395:
        altered = copy.deepcopy(original)
        altered['provider_wrappers'][0]['download_receipt']['run_id'] = '999'
        yield altered
    elif ordinal == 396:
        altered = copy.deepcopy(original)
        altered['schema'] = 'worker38-authenticated-custody-v1'
        yield altered


def build_custody(ctx, namespace, emit):
    if namespace not in ('/workspace/shared/worker38-native-batch-04',
                         '/workspace/shared/worker38-native-batch-05'):
        custody_fail('CUSTODY_NAMESPACE')
    if ctx.accepted['native_output_root'] != '/workspace/shared/worker38-native-batch-04':
        custody_fail('CUSTODY_PARENT_NAMESPACE')
    count = 0
    for index, ordinal, operations in custody_rows():
        row = ctx.accepted['verifier_derivations'][index]
        if row['ordinal'] != ordinal:
            custody_fail('CUSTODY_ROW_ROSTER')
        states = row['ordered_produced_custody_states']
        if tuple(state['source_recipe_binding']['operation_ordinal'] for state in states) != operations:
            custody_fail('CUSTODY_WRITE_ROSTER')
        values = []
        for generation_number in range(1, 3 if ordinal == 366 else 2):
            original = custody_receipt(ctx, row, namespace, generation_number)
            values.extend((generation_number, value) for value in custody_variants(ordinal, original))
        if len(values) != len(operations):
            custody_fail('CUSTODY_WRITE_COUNT')
        for write_index, (generation_number, value) in enumerate(values):
            state = states[write_index]
            logical_path = 't01/custody-inputs-%d/externally-authenticated-custody.json' % generation_number
            if (state['relative_path'] != logical_path or state['path'] != logical_path
                    or state['type'] != 'file' or state['operation'] != 'write'
                    or state['lineage'] != 'produced_output'
                    or state['asset_role'] != 'produced_custody_receipt'):
                custody_fail('CUSTODY_WRITE_IDENTITY')
            raw = custody_canonical(value)
            if len(raw) != state['size_bytes'] or len(raw) > 99413:
                custody_fail('CUSTODY_WRITE_SIZE')
            emit('produced_output', ordinal, logical_path, raw,
                 ('custody-write', ordinal, operations[write_index]))
            count += 1
    if count != 34:
        custody_fail('CUSTODY_TOTAL_WRITES')


def custody_event_calls(ordinal):
    return {365: (2,), 366: (2, 3, 4), 367: (2, 3, 4), 368: tuple(range(2, 10)),
            369: tuple(range(2, 13)), 391: (2,), 392: (2,), 393: (2, 3, 4),
            394: (2,), 395: (2, 3), 396: (2,)}[ordinal]


def custody_operation_history(row):
    # derive_verifier_states adds recipe_phase only after events were committed.
    # Removing this exact export-only field recovers the original metadata domain.
    states = row['ordered_literal_asset_states'] + row['ordered_produced_custody_states']
    ordered = sorted(states, key=lambda state: state['source_recipe_binding']['operation_ordinal'])
    if ([state['source_recipe_binding']['operation_ordinal'] for state in ordered]
            != list(range(1, row['final_operation_count'] + 1))):
        custody_fail('CUSTODY_HISTORY_ORDER_GAP')
    result = []
    for state in ordered:
        operation = copy.deepcopy(state)
        expected_phase = ('baseline_construction' if operation['source_recipe_binding']['operation_ordinal']
                          <= row['baseline_operation_count'] else 'method_operations')
        if operation.pop('recipe_phase') != expected_phase:
            custody_fail('CUSTODY_HISTORY_EXPORT_PHASE')
        result.append(operation)
    return result


def custody_old_state_recipe(state):
    value = {key: state[key] for key in ('relative_path', 'type', 'size_bytes', 'sha256',
                                        'lineage', 'asset_role')}
    return custody_digest({'state': value, 'source_recipe_binding': state['source_recipe_binding']})


def custody_old_event_recipe(accepted, row, event, operations):
    count = event['operation_count']
    if type(count) is not int or not 1 <= count <= len(operations):
        custody_fail('CUSTODY_EVENT_PREFIX_BOUND')
    return custody_digest({'source_sha256': accepted['recipe_source_sha256'],
                           'selector': row['selector'], 'call_ordinal': event['call_ordinal'],
                           'boundary': event['boundary'], 'operations': operations[:count]})


def custody_verified_new_identity(verified_pairs, state):
    key = ('produced_output', state['type'], state['size_bytes'], state['sha256'])
    if key not in verified_pairs:
        custody_fail('CUSTODY_VERIFIED_PAIR_MISSING')
    value = verified_pairs[key]
    if (set(value) != {'type', 'size_bytes', 'sha256'} or value['type'] != 'file'
            or value['size_bytes'] != state['size_bytes']
            or type(value['sha256']) is not str or len(value['sha256']) != 64
            or any(ch not in '0123456789abcdef' for ch in value['sha256'])
            or value['sha256'] == state['sha256']):
        custody_fail('CUSTODY_VERIFIED_PAIR_IDENTITY')
    return value


def custody_new_state_recipe(finite_recipe_identity, row, state, new_identity):
    # Additive provenance: the original recipe is explicitly a historical parent.
    # This does not claim a second execution of the historical full deriver.
    return custody_digest({'schema': 'worker38-native05-finite-custody-state-lineage-v1',
                           'finite_recipe_sha256': finite_recipe_identity,
                           'parent_recipe_sha256': state['independent_recipe_sha256'],
                           'ordinal': row['ordinal'], 'selector': row['selector'],
                           'operation_ordinal': state['source_recipe_binding']['operation_ordinal'],
                           'relative_path': state['relative_path'], 'lineage': 'produced_output',
                           'old_identity': custody_identity(state), 'new_identity': new_identity})


def custody_leaf_delta(kind, target, pointer, old, new):
    if old == new:
        custody_fail('CUSTODY_UNEXPECTED_UNCHANGED_DELTA')
    record = {'kind': kind, 'target': target, 'pointer': pointer, 'old': old, 'new': new}
    if len(custody_canonical(record)) > 1024:
        custody_fail('CUSTODY_DELTA_RECORD_BOUND')
    return record


def custody_rebind_commitments(accepted, verified_pairs, finite_recipe_identity, obligations):
    """Future pure metadata phase, after the coordinator's complete old/new gates.

    Returns only typed leaf deltas, never changes accepted parents. The caller
    must prove all328 old objects before running any new constructor, then prove
    trace/alias equality and all328 new identities before calling this function.
    verified_pairs is the complete verified produced-output identity mapping;
    it contains no raw bytes and supplies no mutation recipes.
    """
    if (type(finite_recipe_identity) is not str or len(finite_recipe_identity) != 64
            or any(ch not in '0123456789abcdef' for ch in finite_recipe_identity)
            or finite_recipe_identity == accepted['recipe_source_sha256']
            or accepted['native_output_root'] != '/workspace/shared/worker38-native-batch-04'):
        custody_fail('CUSTODY_FINITE_RECIPE_IDENTITY')
    old_root = '/workspace/shared/worker38-native-batch-04'
    new_root = '/workspace/shared/worker38-native-batch-05'
    historical = {}
    state_domain = set()
    # Verify every enclosing old commitment before calculating any new one.
    for index, ordinal, operation_ordinals in custody_rows():
        row = accepted['verifier_derivations'][index]
        if row['ordinal'] != ordinal:
            custody_fail('CUSTODY_COMMITMENT_ROW_ROSTER')
        operations = custody_operation_history(row)
        if tuple(state['source_recipe_binding']['operation_ordinal']
                 for state in row['ordered_produced_custody_states']) != operation_ordinals:
            custody_fail('CUSTODY_COMMITMENT_WRITE_ROSTER')
        for state in row['ordered_produced_custody_states']:
            if custody_old_state_recipe(state) != state['independent_recipe_sha256']:
                custody_fail('CUSTODY_OLD_STATE_COMMITMENT_MISMATCH')
            state_domain.add(('produced_output', state['type'], state['size_bytes'], state['sha256']))
            custody_verified_new_identity(verified_pairs, state)
        calls = custody_event_calls(ordinal)
        tainted = tuple(event['call_ordinal'] for event in row['events']
                        if event['operation_count'] >= operation_ordinals[0])
        if tainted != calls:
            custody_fail('CUSTODY_EVENT_ROSTER')
        for call in calls:
            event = row['events'][call - 1]
            if (event['call_ordinal'] != call or event['selector'] != row['selector']
                    or custody_old_event_recipe(accepted, row, event, operations)
                    != event['source_bound_mutation_sequence_sha256']
                    or any(rule['allowed_state']['independent_recipe_sha256']
                           != event['source_bound_mutation_sequence_sha256'] for rule in event['path_rules'])):
                custody_fail('CUSTODY_OLD_EVENT_HISTORY_MISMATCH')
        result_sha = custody_digest(row)
        for family in ('P08', 'P09', 'P10', 'P11', 'P12'):
            ref = accepted['families'][family]['selector_results'][index]
            if (ref['ordinal'] != ordinal or ref['selector'] != row['selector']
                    or ref['verifier_derivation_ordinal'] != ordinal or ref['result_sha256'] != result_sha):
                custody_fail('CUSTODY_OLD_RESULT_COMMITMENT_MISMATCH')
        historical[ordinal] = (operations, result_sha)
    if len(state_domain) != 32 or set(verified_pairs) != state_domain:
        custody_fail('CUSTODY_VERIFIED_PAIR_DOMAIN')
    if obligations is None:
        custody_fail('CUSTODY_OBLIGATION_REQUIRED')
    obligation_locations = {}
    if obligations is not None:
        if (type(obligations) is not dict or set(obligations) != {'rows', 'schema'}
                or type(obligations['rows']) is not list or len(obligations['rows']) != 397):
            custody_fail('CUSTODY_OBLIGATION_ROSTER')
        for index, ordinal, _ in custody_rows():
            obligation = obligations['rows'][ordinal - 1]
            row = accepted['verifier_derivations'][index]
            if obligation['ordinal'] != ordinal or obligation['selector'] != row['selector']:
                custody_fail('CUSTODY_OBLIGATION_IDENTITY')
            found = {}
            for family_index, family in enumerate(obligation['families']):
                if family['family_id'] in ('P08', 'P09', 'P10', 'P11', 'P12'):
                    if family['family_id'] in found or family['result_sha256'] != historical[ordinal][1]:
                        custody_fail('CUSTODY_OLD_OBLIGATION_COMMITMENT_MISMATCH')
                    found[family['family_id']] = family_index
            if set(found) != {'P08', 'P09', 'P10', 'P11', 'P12'}:
                custody_fail('CUSTODY_OBLIGATION_FAMILY_ROSTER')
            obligation_locations[ordinal] = found
    deltas = []
    result_pairs = []
    for index, ordinal, _ in custody_rows():
        row = accepted['verifier_derivations'][index]
        changed = copy.deepcopy(row)
        new_operations = copy.deepcopy(historical[ordinal][0])
        prefix = '/verifier_derivations/%d' % index
        state_changes = {}
        for state_index, state in enumerate(row['ordered_produced_custody_states']):
            identity = custody_verified_new_identity(verified_pairs, state)
            recipe = custody_new_state_recipe(finite_recipe_identity, row, state, identity)
            operation_ordinal = state['source_recipe_binding']['operation_ordinal']
            state_changes[operation_ordinal] = (identity, recipe)
            for key, value in (('sha256', identity['sha256']), ('independent_recipe_sha256', recipe)):
                changed['ordered_produced_custody_states'][state_index][key] = value
                new_operations[operation_ordinal - 1][key] = value
                deltas.append(custody_leaf_delta('custody_ordered_state', 'ALL397',
                    prefix + '/ordered_produced_custody_states/%d/%s' % (state_index, key), state[key], value))
        for collection in ('versions', 'produced'):
            for state_index, state in enumerate(row[collection]):
                op = state['source_recipe_binding']['operation_ordinal']
                if op not in state_changes:
                    custody_fail('CUSTODY_ALIAS_OPERATION')
                identity, recipe = state_changes[op]
                if custody_identity(state) != custody_identity(row['ordered_produced_custody_states'][
                        next(i for i, value in enumerate(row['ordered_produced_custody_states'])
                             if value['source_recipe_binding']['operation_ordinal'] == op)]):
                    custody_fail('CUSTODY_ALIAS_OLD_IDENTITY')
                for key, value in (('sha256', identity['sha256']), ('independent_recipe_sha256', recipe)):
                    changed[collection][state_index][key] = value
                    deltas.append(custody_leaf_delta('custody_' + collection + '_alias', 'ALL397',
                        prefix + '/%s/%d/%s' % (collection, state_index, key), state[key], value))
        for generation_index, generation in enumerate(row['custody_input_generations']):
            old_directory = old_root + '/c%04d/t01/custody-inputs-%d' % (ordinal, generation_index + 1)
            if generation['directory'] != old_directory:
                custody_fail('CUSTODY_GENERATION_ALIAS')
            new_directory = new_root + '/c%04d/t01/custody-inputs-%d' % (ordinal, generation_index + 1)
            changed['custody_input_generations'][generation_index]['directory'] = new_directory
            deltas.append(custody_leaf_delta('custody_generation_directory', 'ALL397',
                prefix + '/custody_input_generations/%d/directory' % generation_index, old_directory, new_directory))
        for call in custody_event_calls(ordinal):
            event = row['events'][call - 1]
            event_prefix = prefix + '/events/%d' % (call - 1)
            recipe = custody_digest({'schema': 'worker38-native05-finite-custody-event-lineage-v1',
                'finite_recipe_sha256': finite_recipe_identity,
                'parent_recipe_sha256': event['source_bound_mutation_sequence_sha256'],
                'selector': row['selector'], 'call_ordinal': call, 'boundary': event['boundary'],
                'operations': new_operations[:event['operation_count']]})
            changed['events'][call - 1]['source_bound_mutation_sequence_sha256'] = recipe
            deltas.append(custody_leaf_delta('custody_event_history', 'ALL397',
                event_prefix + '/source_bound_mutation_sequence_sha256',
                event['source_bound_mutation_sequence_sha256'], recipe))
            for rule_index, rule in enumerate(event['path_rules']):
                state = rule['allowed_state']
                rule_prefix = event_prefix + '/path_rules/%d/allowed_state/' % rule_index
                changed['events'][call - 1]['path_rules'][rule_index]['allowed_state']['independent_recipe_sha256'] = recipe
                deltas.append(custody_leaf_delta('custody_event_recipe_alias', 'ALL397',
                    rule_prefix + 'independent_recipe_sha256', state['independent_recipe_sha256'], recipe))
                if state['lineage'] == 'produced_output':
                    if not rule['relative_path'].endswith('/externally-authenticated-custody.json'):
                        custody_fail('CUSTODY_EVENT_PRODUCED_ROLE')
                    identity = custody_verified_new_identity(verified_pairs, state)
                    changed['events'][call - 1]['path_rules'][rule_index]['allowed_state']['sha256'] = identity['sha256']
                    deltas.append(custody_leaf_delta('custody_event_content', 'ALL397',
                        rule_prefix + 'sha256', state['sha256'], identity['sha256']))
        new_result = custody_digest(changed)
        result_pairs.append({'ordinal': ordinal, 'old': historical[ordinal][1], 'new': new_result})
        for family in ('P08', 'P09', 'P10', 'P11', 'P12'):
            deltas.append(custody_leaf_delta('custody_family_result', 'ALL397',
                '/families/%s/selector_results/%d/result_sha256' % (family, index),
                historical[ordinal][1], new_result))
            if obligations is not None:
                family_index = obligation_locations[ordinal][family]
                deltas.append(custody_leaf_delta('custody_obligation_result', 'OBLIGATIONS',
                    '/rows/%d/families/%d/result_sha256' % (ordinal - 1, family_index),
                    historical[ordinal][1], new_result))
    expected = {'custody_ordered_state': 68, 'custody_versions_alias': 44,
                'custody_produced_alias': 24, 'custody_generation_directory': 12,
                'custody_event_history': 35, 'custody_event_recipe_alias': 1198,
                'custody_event_content': 34, 'custody_family_result': 55}
    if obligations is not None:
        expected['custody_obligation_result'] = 55
    actual = {}
    for delta in deltas:
        actual[delta['kind']] = actual.get(delta['kind'], 0) + 1
    if (actual != expected or len({(delta['target'], delta['pointer']) for delta in deltas}) != len(deltas)
            or len(result_pairs) != 11):
        custody_fail('CUSTODY_DELTA_EXACT_ROSTER')
    return {'deltas': deltas, 'result_pairs': result_pairs,
            'old_commitments_verified': True, 'parent_products_unchanged': True}


def metadata_canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')


def metadata_digest(value):
    return hashlib.sha256(metadata_canonical(value)).hexdigest()


def metadata_fail(code):
    # Call sites supply only fixed diagnostic codes, never data or exceptions.
    raise ValueError(code)


def metadata_sha256(value):
    return (type(value) is str and len(value) == 64
            and all(ch in '0123456789abcdef' for ch in value))


def metadata_pointer_get(document, pointer):
    if type(pointer) is not str or not pointer.startswith('/'):
        metadata_fail('METADATA_POINTER_SHAPE')
    value = document
    for encoded in pointer.split('/')[1:]:
        token = encoded.replace('~1', '/').replace('~0', '~')
        if type(value) is list:
            if (not token.isdigit() or str(int(token)) != token
                    or int(token) >= len(value)):
                metadata_fail('METADATA_POINTER_INDEX')
            value = value[int(token)]
        elif type(value) is dict and token in value:
            value = value[token]
        else:
            metadata_fail('METADATA_POINTER_TARGET')
    return value


def metadata_namespace_value(value):
    old_root = '/workspace/shared/worker38-native-batch-04'
    new_root = '/workspace/shared/worker38-native-batch-05'
    if type(value) is not str or not (value == old_root or value.startswith(old_root + '/')):
        metadata_fail('METADATA_EXACT_NAMESPACE')
    # Only called for a leaf selected by a pinned exact pointer roster.
    return new_root + value[len(old_root):]


def metadata_leaf_delta(kind, target, pointer, old, new):
    if (type(old) not in (str, int, bool, type(None)) or type(new) is not type(old)
            or old == new or target not in ('ALL397', 'OBLIGATIONS')):
        metadata_fail('METADATA_LEAF_SHAPE')
    record = {'kind': kind, 'target': target, 'pointer': pointer, 'old': old, 'new': new}
    if len(metadata_canonical(record)) > 1024:
        metadata_fail('METADATA_LEAF_BOUND')
    return record


def metadata_domain_digest(leaves):
    return metadata_digest([{key: leaf[key] for key in ('kind', 'target', 'pointer', 'old')}
        for leaf in sorted(leaves, key=lambda item: (item['target'], item['pointer']))])


def metadata_checked_row_copy(parent, prefix, leaves):
    # One bounded historical selector/verifier object at a time; never copy ALL397.
    result = copy.deepcopy(parent)
    for leaf in leaves:
        if not leaf['pointer'].startswith(prefix + '/'):
            metadata_fail('METADATA_ROW_POINTER_SCOPE')
        relative = leaf['pointer'][len(prefix):]
        if metadata_pointer_get(result, relative) != leaf['old']:
            metadata_fail('METADATA_ROW_OLD_VALUE')
        container_pointer, _, encoded = relative.rpartition('/')
        container = metadata_pointer_get(result, container_pointer) if container_pointer else result
        token = encoded.replace('~1', '/').replace('~0', '~')
        if type(container) is list:
            container[int(token)] = leaf['new']
        elif type(container) is dict and token in container:
            container[token] = leaf['new']
        else:
            metadata_fail('METADATA_ROW_LEAF_TARGET')
    return result


def metadata_verify_historical_products(accepted, obligations):
    if (accepted.get('schema') != 'worker38-all397-literal-pins-v1'
            or accepted.get('recipe_source_sha256') != '4a5f7136d99e7754d1673f5b22dd7fced6a4b2aed0a19560419d7dca2d647eb5'
            or accepted.get('native_output_root') != '/workspace/shared/worker38-native-batch-04'
            or accepted.get('execution_authorized') is not False
            or accepted.get('all397_reservation_or_fit_certified') is not False
            or obligations.get('schema') != 'worker38-all397-recipe-obligations-v1'
            or len(obligations.get('rows', [])) != 397
            or set(accepted['families']) != {'P%02d' % index for index in range(1, 16)}):
        metadata_fail('METADATA_HISTORICAL_PRODUCTS')
    locations = {}
    selectors = {}
    verifier_hashes = {}
    for index, row in enumerate(accepted['verifier_derivations']):
        if row['ordinal'] in verifier_hashes:
            metadata_fail('METADATA_VERIFIER_ORDINAL_DUPLICATE')
        verifier_hashes[row['ordinal']] = (metadata_digest(row), row['selector'], index)
    family_rows = {}
    for family, product in accepted['families'].items():
        lookup = {}
        for index, row in enumerate(product['selector_results']):
            if row['ordinal'] in lookup:
                metadata_fail('METADATA_FAMILY_ORDINAL_DUPLICATE')
            lookup[row['ordinal']] = (index, row)
        family_rows[family] = lookup
    joined = set()
    for index, obligation in enumerate(obligations['rows']):
        ordinal = index + 1
        if (obligation['ordinal'] != ordinal or obligation['execution_authorized'] is not False
                or obligation['reservation_certified'] is not False or obligation['unresolved'] != []
                or obligation['selector'] in selectors):
            metadata_fail('METADATA_ALL397_OBLIGATION_IDENTITY')
        selectors[obligation['selector']] = ordinal
        seen_families = set()
        for family_index, reference in enumerate(obligation['families']):
            family = reference['family_id']
            if family in seen_families or family not in family_rows or ordinal not in family_rows[family]:
                metadata_fail('METADATA_ALL397_FAMILY_JOIN')
            seen_families.add(family)
            row_index, row = family_rows[family][ordinal]
            if row['selector'] != obligation['selector'] or row['unresolved'] != []:
                metadata_fail('METADATA_ALL397_SELECTOR_JOIN')
            if family in ('P08', 'P09', 'P10', 'P11', 'P12'):
                if ordinal not in verifier_hashes:
                    metadata_fail('METADATA_VERIFIER_JOIN')
                digest, selector, _ = verifier_hashes[ordinal]
                if (row['verifier_derivation_ordinal'] != ordinal or selector != row['selector']
                        or row['result_sha256'] != digest):
                    metadata_fail('METADATA_OLD_VERIFIER_RESULT')
            else:
                digest = metadata_digest(row)
            if reference['result_sha256'] != digest:
                metadata_fail('METADATA_OLD_OBLIGATION_COMMITMENT')
            if family == 'P15' and (row['native_execution_authorized'] is not False
                    or row['namespace'] != '/workspace/shared/worker38-native-batch-04'
                    or row['environment_manifest_sha256'] != 'eaf1cc4d9796e88a07e75d96424fafdab69bec12ddedd9b0f0b48293191fa952'):
                metadata_fail('METADATA_HISTORICAL_P15_CLAIM')
            locations[(family, row_index)] = ('/rows/%d/families/%d/result_sha256' % (index, family_index), digest)
            joined.add((family, row_index))
        if 'P15' not in seen_families:
            metadata_fail('METADATA_P15_JOIN_MISSING')
    expected = {(family, index) for family, product in accepted['families'].items()
                for index in range(len(product['selector_results']))}
    if joined != expected or len(selectors) != 397:
        metadata_fail('METADATA_COMPLETE397_JOIN')
    return locations, verifier_hashes


def metadata_verified_input(verified_pairs, record):
    key = ('input', record['type'], record['old_size_bytes'], record['old_sha256'])
    if key not in verified_pairs:
        metadata_fail('METADATA_INPUT_PAIR_MISSING')
    value = verified_pairs[key]
    if (type(value) is not dict or set(value) != {'type', 'size_bytes', 'sha256'}
            or value['type'] != record['type'] or type(value['size_bytes']) is not int
            or value['size_bytes'] != record['old_size_bytes']
            or not metadata_sha256(value['sha256']) or value['sha256'] == record['old_sha256']):
        metadata_fail('METADATA_INPUT_PAIR_IDENTITY')
    return value


def metadata_validate_custody_leaves(accepted, obligations, custody_edits):
    if (type(custody_edits) is not list or len(custody_edits) != 1525
            or any(type(leaf) is not dict or set(leaf) != {'kind', 'target', 'pointer', 'old', 'new'}
                   for leaf in custody_edits)
            or metadata_domain_digest(custody_edits) != '984d7f0cdc6c9f79c1753853537a4d51559eb839854ece2fafe1861ffff783a8'):
        metadata_fail('METADATA_EXACT_CUSTODY_LEAF_DOMAIN')
    locations = {}
    for leaf in custody_edits:
        target = leaf['target']
        pointer = leaf['pointer']
        if ((target, pointer) in locations
                or metadata_pointer_get(accepted if target == 'ALL397' else obligations, pointer) != leaf['old']):
            metadata_fail('METADATA_CUSTODY_OLD_VALUE')
        if leaf['kind'] == 'custody_generation_directory':
            if leaf['new'] != metadata_namespace_value(leaf['old']):
                metadata_fail('METADATA_CUSTODY_DIRECTORY_ALIAS')
        elif not metadata_sha256(leaf['new']) or leaf['new'] == leaf['old']:
            metadata_fail('METADATA_CUSTODY_NEW_VALUE')
        if len(metadata_canonical(leaf)) > 1024:
            metadata_fail('METADATA_CUSTODY_LEAF_BOUND')
        locations[(target, pointer)] = leaf
    return locations


def metadata_loader_descriptors(accepted, path_roster, finite_recipe_identity, direct_edits):
    historical_source = '4a5f7136d99e7754d1673f5b22dd7fced6a4b2aed0a19560419d7dca2d647eb5'
    selected = {item['pointer']: item for item in path_roster['path_dependent_loader_contexts']}
    if len(selected) != 31:
        metadata_fail('METADATA_LOADER_SELECTED_CONTEXTS')
    result = []
    changed_scalars = set()
    context_count = 0
    invariant_count = 0
    seen = set()
    for row_index, row in enumerate(accepted['families']['P05']['selector_results']):
        for context_index, context in enumerate(row['loader_contexts']):
            context_count += 1
            pointer = '/families/P05/selector_results/%d/loader_contexts/%d' % (row_index, context_index)
            schema = [[field, tag] for field, tag, _ in context['expected_context']]
            old_descriptor = {'slot': context['slot'], 'expected_context': context['expected_context'],
                'context_dynamic_fields': context['context_dynamic_fields'], 'source_sha256': historical_source,
                'field_schema_sha256': metadata_digest(schema)}
            old_recipe = metadata_digest(old_descriptor)
            if (context['context_recipe_sha256'] != old_recipe
                    or any(rule['allowed_state']['independent_recipe_sha256'] != old_recipe
                           for rule in context['path_rules'])):
                metadata_fail('METADATA_OLD_LOADER_DESCRIPTOR')
            scalar_leaves = [leaf for leaf in direct_edits if leaf['pointer'].startswith(pointer + '/expected_context/')]
            if pointer not in selected:
                invariant_count += 1
                if scalar_leaves:
                    metadata_fail('METADATA_INVARIANT_LOADER_CHANGED')
                continue
            seen.add(pointer)
            entry = selected[pointer]
            if (entry['ordinal'] != row['ordinal'] or entry['selector'] != row['selector']
                    or entry['slot'] != context['slot'] or entry['old_recipe_sha256'] != old_recipe
                    or entry['path_rule_count'] != len(context['path_rules'])):
                metadata_fail('METADATA_LOADER_ROSTER_IDENTITY')
            exact = set()
            for scalar in entry['changed_scalars']:
                index = scalar['index']
                value = context['expected_context'][index]
                scalar_pointer = pointer + '/expected_context/%d/2' % index
                if (value[0] != scalar['field'] or value[1] != 'str' or value[2] != scalar['old_value']
                        or scalar_pointer in exact):
                    metadata_fail('METADATA_LOADER_SCALAR_ROSTER')
                exact.add(scalar_pointer)
            if exact != {leaf['pointer'] for leaf in scalar_leaves} or not exact:
                metadata_fail('METADATA_LOADER_SCALAR_DOMAIN')
            changed_scalars.update(exact)
            changed_context = metadata_checked_row_copy(context, pointer, scalar_leaves)
            # This is a new finite, historical-parented METADATA recipe identity.
            # It does not impersonate another run of the original15-family deriver.
            descriptor = {'schema': 'worker38-native05-finite-loader-context-lineage-v1',
                'finite_recipe_sha256': finite_recipe_identity, 'parent_recipe_sha256': old_recipe,
                'parent_deriver_sha256': historical_source, 'slot': context['slot'],
                'expected_context': changed_context['expected_context'],
                'context_dynamic_fields': context['context_dynamic_fields'],
                'field_schema_sha256': old_descriptor['field_schema_sha256']}
            new_recipe = metadata_digest(descriptor)
            result.append(metadata_leaf_delta('loader_context_recipe', 'ALL397',
                pointer + '/context_recipe_sha256', old_recipe, new_recipe))
            for rule_index, rule in enumerate(context['path_rules']):
                result.append(metadata_leaf_delta('loader_path_recipe_alias', 'ALL397',
                    pointer + '/path_rules/%d/allowed_state/independent_recipe_sha256' % rule_index,
                    rule['allowed_state']['independent_recipe_sha256'], new_recipe))
    if (context_count != 60 or invariant_count != 29 or seen != set(selected)
            or len(changed_scalars) != 132 or len(result) != 97):
        metadata_fail('METADATA_LOADER_COMPLETE_DOMAIN')
    return result


def metadata_rebind_commitments(accepted, obligations, input_roster, path_roster,
                                verified_pairs, finite_recipe_identity, custody_edits):
    """Future metadata-only phase; constructing this source does not authorize it.

    Arguments accepted/obligations/rosters must come from the coordinator's pinned
    no-follow reads, parsed from those same verified bytes. verified_pairs must
    contain only identities already admitted after complete old/new preimage
    verification; no byte generation, candidate call, I/O or recipe evaluation is
    performed here. The input map may include the separately verified32 custody
    identities, but the296 input keys must match exactly. Returns only1964 own
    typed leaf edits; custody's1525 leaves remain separately owned and unchanged.
    """
    if (not metadata_sha256(finite_recipe_identity)
            or finite_recipe_identity == '4a5f7136d99e7754d1673f5b22dd7fced6a4b2aed0a19560419d7dca2d647eb5'
            or metadata_digest(input_roster) != 'ef2c715bd9f3311d2458cc973d20760567fe3da029ec0a308f6382b390f528d7'
            or metadata_digest(path_roster) != 'fbd872c0145375316eace63ca7f12ff7cb86f40ea842b04c300b05ecc8e7d933'):
        metadata_fail('METADATA_FIXED_INPUT_ROSTERS')
    locations, verifier_hashes = metadata_verify_historical_products(accepted, obligations)
    custody_locations = metadata_validate_custody_leaves(accepted, obligations, custody_edits)
    input_keys = {('input', item['type'], item['old_size_bytes'], item['old_sha256'])
                  for item in input_roster['records']}
    if (type(verified_pairs) is not dict
            or any(type(key) is not tuple or len(key) != 4 or key[0] not in ('input', 'produced_output')
                   for key in verified_pairs)
            or len(input_roster['records']) != 676 or len(input_keys) != 296
            or len({(item['ordinal'], item['relative_path'], item['type'],
                     item['old_size_bytes'], item['old_sha256']) for item in input_roster['records']}) != 515
            or {key for key in verified_pairs if key[0] == 'input'} != input_keys):
        metadata_fail('METADATA_INPUT_IDENTITY_DOMAIN')
    deltas = []
    for item in input_roster['records']:
        pointer = item['metadata_pointer']
        pin = metadata_pointer_get(accepted, pointer)
        prefix = '/'.join(pointer.split('/')[:5])
        row = metadata_pointer_get(accepted, prefix)
        if (row['ordinal'] != item['ordinal'] or row['selector'] != item['selector']
                or prefix.split('/')[2] != item['family'] or pin['relative_path'] != item['relative_path']):
            metadata_fail('METADATA_INPUT_OCCURRENCE_IDENTITY')
        if '/loader_contexts/' in pointer:
            state = pin['allowed_state']
            old_type, old_size, old_sha = state['type'], state['size_bytes'], state['sha256']
            leaf_pointer = pointer + '/allowed_state/sha256'
            if state['lineage'] != 'independent_input':
                metadata_fail('METADATA_LOADER_INPUT_LINEAGE')
        else:
            old_type, old_size, old_sha = pin['kind'], pin['raw']['size_bytes'], pin['raw']['sha256']
            leaf_pointer = pointer + '/raw/sha256'
            if pin['lineage'] != 'independent_literal_input':
                metadata_fail('METADATA_RAW_INPUT_LINEAGE')
        if (old_type, old_size, old_sha) != (item['type'], item['old_size_bytes'], item['old_sha256']):
            metadata_fail('METADATA_INPUT_OLD_IDENTITY')
        new_identity = metadata_verified_input(verified_pairs, item)
        deltas.append(metadata_leaf_delta('input_content', 'ALL397', leaf_pointer, old_sha, new_identity['sha256']))
    direct_edits = []
    delegated_direct = 0
    for item in path_roster['accepted06_json']:
        pointer, old = item['pointer'], item['old_value']
        if metadata_pointer_get(accepted, pointer) != old:
            metadata_fail('METADATA_NAMESPACE_OLD_VALUE')
        new = metadata_namespace_value(old)
        if ('ALL397', pointer) in custody_locations:
            delegated_direct += 1
            leaf = custody_locations[('ALL397', pointer)]
            if leaf['kind'] != 'custody_generation_directory' or leaf['new'] != new:
                metadata_fail('METADATA_CUSTODY_NAMESPACE_COLLISION')
        else:
            direct_edits.append(metadata_leaf_delta('namespace_scalar', 'ALL397', pointer, old, new))
    if len(direct_edits) != 738 or delegated_direct != 12:
        metadata_fail('METADATA_NAMESPACE_COMPLETE_DOMAIN')
    deltas.extend(direct_edits)
    deltas.extend(metadata_loader_descriptors(accepted, path_roster, finite_recipe_identity, direct_edits))
    # The only generic enclosing commitments are453 historical obligation leaves.
    # P08-P12 enclosing references belong to custody and are checked separately.
    changed_groups = {}
    for leaf in deltas:
        if leaf['pointer'].startswith('/families/'):
            prefix = '/'.join(leaf['pointer'].split('/')[:5])
            changed_groups.setdefault(prefix, []).append(leaf)
    if len(changed_groups) != 453:
        metadata_fail('METADATA_FAMILY_GROUP_DOMAIN')
    for prefix, group in sorted(changed_groups.items()):
        family, index = prefix.split('/')[2], int(prefix.split('/')[4])
        row = metadata_pointer_get(accepted, prefix)
        obligation_pointer, old_digest = locations[(family, index)]
        changed = metadata_checked_row_copy(row, prefix, group)
        new_digest = metadata_digest(changed)
        deltas.append(metadata_leaf_delta('family_obligation_result', 'OBLIGATIONS',
            obligation_pointer, old_digest, new_digest))
        del changed
    # Recompute custody enclosing results after all of their explicit row edits.
    # Do not overwrite/deduplicate them by a last-writer-wins merge.
    custody_groups = {}
    for leaf in custody_edits:
        if leaf['target'] == 'ALL397' and leaf['pointer'].startswith('/verifier_derivations/'):
            prefix = '/'.join(leaf['pointer'].split('/')[:3])
            custody_groups.setdefault(prefix, []).append(leaf)
    if len(custody_groups) != 11:
        metadata_fail('METADATA_CUSTODY_GROUP_DOMAIN')
    for prefix, group in sorted(custody_groups.items()):
        row = metadata_pointer_get(accepted, prefix)
        old_digest, selector, index = verifier_hashes[row['ordinal']]
        if selector != row['selector'] or prefix != '/verifier_derivations/%d' % index:
            metadata_fail('METADATA_CUSTODY_GROUP_IDENTITY')
        changed = metadata_checked_row_copy(row, prefix, group)
        new_digest = metadata_digest(changed)
        del changed
        for family in ('P08', 'P09', 'P10', 'P11', 'P12'):
            result_pointer = '/families/%s/selector_results/%d/result_sha256' % (family, index)
            obligation_pointer, old_obligation = locations[(family, index)]
            for target, pointer in (('ALL397', result_pointer), ('OBLIGATIONS', obligation_pointer)):
                leaf = custody_locations[(target, pointer)]
                if (leaf['old'] != old_digest or old_obligation != old_digest or leaf['new'] != new_digest):
                    metadata_fail('METADATA_CUSTODY_ENCLOSING_COMMITMENT')
    deltas.sort(key=lambda leaf: (leaf['target'], leaf['pointer']))
    if (len(deltas) != 1964
            or metadata_domain_digest(deltas) != '73f38a1dc9508b74ff629d57cfbb7144a58b7280fe74bd83c357a03289d8e25f'
            or len({(leaf['target'], leaf['pointer']) for leaf in deltas}) != 1964
            or any((leaf['target'], leaf['pointer']) in custody_locations for leaf in deltas)):
        metadata_fail('METADATA_EXACT_OWN_LEAF_DOMAIN')
    return deltas


def metadata_pack_delta(leaves):
    """Exact fixed3489-leaf serialization, not a new transformation domain.

    Each of1114 records explicitly includes every leaf's target, pointer, old and
    new scalar. No wildcard, implicit fanout, shared substitution or parent-object
    rewrite exists. Coordinator still enforces4MiB sink/64KiB container framing.
    """
    if (type(leaves) is not list or len(leaves) != 3489
            or any(type(leaf) is not dict or set(leaf) != {'kind', 'target', 'pointer', 'old', 'new'}
                   for leaf in leaves)
            or metadata_domain_digest(leaves) != '6c803f6ebc23ab30ced02e89289893186597c4c94c163e3a75037bbb08b84a19'
            or len({(leaf['target'], leaf['pointer']) for leaf in leaves}) != 3489):
        metadata_fail('METADATA_EXACT_PACKING_DOMAIN')
    packed = []
    current = []
    for leaf in sorted(leaves, key=lambda item: (item['target'], item['pointer'])):
        if leaf['kind'] in ('namespace_scalar', 'custody_generation_directory'):
            if leaf['new'] != metadata_namespace_value(leaf['old']):
                metadata_fail('METADATA_PACKING_NAMESPACE')
        elif not metadata_sha256(leaf['new']) or leaf['new'] == leaf['old']:
            metadata_fail('METADATA_PACKING_DIGEST')
        candidate = current + [leaf]
        if len(metadata_canonical({'edits': candidate})) > 1024:
            if not current:
                metadata_fail('METADATA_PACKING_SINGLE_LEAF')
            packed.append({'edits': current})
            current = [leaf]
        else:
            current = candidate
    if current:
        packed.append({'edits': current})
    sizes = [len(metadata_canonical(record)) for record in packed]
    if (len(packed) != 1114 or len(packed) > 3000 or max(sizes) > 1024
            or sum(sizes) != 981284 or sum(sizes) + len(packed) + 65536 > 4194304):
        metadata_fail('METADATA_EXACT_PACKING_BOUND')
    return packed


# Closed administrative launcher. This source is inert until a separate GO.
OLD_ROOT = '/workspace/shared/worker38-native-batch-04'
NEW_ROOT = '/workspace/shared/worker38-native-batch-05'
SOURCE_DIR = '/workspace/shared/worker38-native05-lineage-implementation-revision03/lineage-source'
OUTPUT_DIR = '/workspace/shared/worker38-native05-input-lineage-materialization'
BASELINE = '/workspace/shared/worker38-native05-C07-repair-revision02/baseline-native04-candidate/'
CAPS = {'PREIMAGE-PAIRS.json': 16777216, 'NATIVE05-LINEAGE-DELTA.json': 4194304,
        'ATTEMPT-STARTED.json': 65536, 'TRANSFORM-RECEIPT.json': 65536, 'phase.log': 65536}
READ_CAP = 134217728
TOTAL_CAP = 25165824
MAX_RAW = 99413


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class ClosedFailure(Exception):
    pass


def require(condition, code):
    if not condition:
        raise ClosedFailure(code)


def hex64(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def stable_stat(value):
    return tuple(getattr(value, key) for key in ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


def close_preserving_primary(fd, primary_failure):
    # One cleanup close of an already owned descriptor. A local earlier failure
    # remains in flight; otherwise this close failure becomes the primary cause.
    # This helper never retries, reads, writes, opens or renews a deadline.
    try:
        os.close(fd)
    except BaseException:
        if not primary_failure:
            raise


def regular_open(path, flags):
    # Transfer ownership before closing a replaced parent, so a failed close is
    # not retried and a newly acquired descriptor can still be disposed of.
    require(path.startswith('/') and '..' not in path.split('/'), 'PATH')
    parts = path.split('/')[1:]
    parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    fd = None
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            previous, parent = parent, child
            close_preserving_primary(previous, False)
        fd = os.open(parts[-1], flags | os.O_NOFOLLOW, dir_fd=parent, mode=0o600)
        require(stat.S_ISREG(os.fstat(fd).st_mode), 'TYPE')
        previous, parent = parent, None
        close_preserving_primary(previous, False)
        result, fd = fd, None
        return result
    except BaseException:
        if fd is not None:
            close_preserving_primary(fd, True)
        if parent is not None:
            close_preserving_primary(parent, True)
        raise


class Reader:
    def __init__(self):
        self.bytes = 0
        self.readback_bytes = 0
        self.seen = set()
        self.pins = []
        self.deadline = time.monotonic() + 600

    def check(self):
        require(time.monotonic() < self.deadline, 'DEADLINE')

    def read(self, path, cap, expected=None):
        self.check()
        require(path not in self.seen and type(cap) is int and 0 <= cap <= 50331648, 'READ_SCOPE')
        self.seen.add(path)
        fd = regular_open(path, os.O_RDONLY)
        primary_failure = False
        try:
            before = os.fstat(fd)
            require(before.st_size <= cap, 'READ_SIZE')
            chunks = []
            remaining = cap + 1
            while remaining:
                self.check()
                raw = os.read(fd, min(65536, remaining))
                if not raw:
                    break
                self.bytes += len(raw)
                require(self.bytes + self.readback_bytes <= READ_CAP, 'READ_TOTAL')
                chunks.append(raw)
                remaining -= len(raw)
            value = b''.join(chunks)
            after = os.fstat(fd)
            require(len(value) <= cap and stable_stat(before) == stable_stat(after) and len(value) == after.st_size, 'READ_CHANGED')
            pin = {'path': path, 'size_bytes': len(value), 'sha256': sha(value)}
            if expected is not None:
                require(pin['size_bytes'] == expected['size_bytes'] and pin['sha256'] == expected['sha256'], 'READ_PIN')
            self.pins.append(pin)
            return value
        except BaseException:
            primary_failure = True
            raise
        finally:
            close_preserving_primary(fd, primary_failure)


class Context:
    def __init__(self, reader, scope):
        self.reader = reader
        self.scope = scope
        self.registry = {row['path']: row for row in scope['reads']}
        require(len(self.registry) == len(scope['reads']), 'READ_DUPLICATE')
        self.cache = {}
        self.objects = {}
        self.literals = {}
        self.accepted = self.named_json('accepted')

    def bytes(self, path):
        require(path in self.registry, 'READ_UNREGISTERED')
        if path not in self.cache:
            row = self.registry[path]
            self.cache[path] = self.reader.read(path, row['size_bytes'], row)
        return self.cache[path]

    def named_json(self, name):
        path = self.scope['named_inputs'][name]
        if path not in self.objects:
            self.objects[path] = json.loads(self.bytes(path))
            # The large accepted JSON is retained as one parsed parent only.
            del self.cache[path]
        return self.objects[path]

    def text(self, relative):
        return self.bytes(BASELINE + relative).decode('utf-8')

    def json(self, relative):
        path = BASELINE + relative
        if path not in self.objects:
            self.objects[path] = json.loads(self.bytes(path))
        return self.objects[path]

    def literal(self, relative, name):
        require([relative, name] in self.scope['literal_requests'], 'LITERAL_SCOPE')
        key = (relative, name)
        if key not in self.literals:
            tree = ast.parse(self.text(relative))
            matches = [node.value for node in tree.body if isinstance(node, ast.Assign)
                       and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                       and node.targets[0].id == name]
            require(len(matches) == 1, 'LITERAL_ASSIGNMENT')
            allowed = (ast.Constant, ast.List, ast.Tuple, ast.Dict, ast.Set,
                       ast.Load, ast.UnaryOp, ast.USub, ast.UAdd)
            require(all(isinstance(node, allowed) for node in ast.walk(matches[0])), 'LITERAL_AST')
            self.literals[key] = ast.literal_eval(matches[0])
        return copy.deepcopy(self.literals[key])


def directory_open(path):
    require(path.startswith('/') and '..' not in path.split('/'), 'DIRECTORY_PATH')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.split('/')[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            previous, fd = fd, child
            close_preserving_primary(previous, False)
        return fd
    except BaseException:
        close_preserving_primary(fd, True)
        raise


class Writer:
    def __init__(self, reader):
        self.reader = reader
        self.total = 0
        self.fd = {}
        self.count = {}
        self.digests = {}
        self.finished = {}
        # Allocation, closure and readback are distinct states. A closed or
        # failed name is never mistaken for an unused exclusive sink.
        self.allocation_attempted = set()
        self.allocated = set()
        self.failed_writes = set()
        self.lifecycle = {}
        self.preservation_attempted = set()
        self.parent_close = 'not_attempted'
        parent_path, name = OUTPUT_DIR.rsplit('/', 1)
        parent = directory_open(parent_path)
        directory_fd = None
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent)
            os.fsync(parent)
            directory_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            previous, parent = parent, None
            close_preserving_primary(previous, False)
            self.dirfd = directory_fd
        except BaseException:
            if directory_fd is not None:
                close_preserving_primary(directory_fd, True)
            if parent is not None:
                close_preserving_primary(parent, True)
            raise

    def once(self, name, action):
        # At most one syscall attempt for each owned sink/action, across both
        # normal finalization and exceptional preservation. No retry of a
        # failed/uncertain fsync or close; close uncertainty stays explicit.
        require(name in self.allocated and action in ('file_sync', 'close', 'parent_sync'), 'OWNED_ACTION')
        state = self.lifecycle[name]
        if state[action] != 'not_attempted':
            require(state[action] == 'succeeded', 'OWNED_ACTION_ALREADY_FAILED')
            return
        try:
            self.reader.check()
        except BaseException:
            state[action] = 'deadline_unavailable'
            raise
        state[action] = 'attempted'
        try:
            if action == 'file_sync':
                os.fsync(self.fd[name])
            elif action == 'close':
                # Never retry close after an error: the descriptor may already
                # have been released. The lifecycle records that uncertainty.
                fd = self.fd.pop(name)
                os.close(fd)
            else:
                os.fsync(self.dirfd)
        except BaseException:
            state[action] = 'failed'
            raise
        state[action] = 'succeeded'

    def append(self, name, raw):
        self.reader.check()
        require(name in CAPS and type(raw) is bytes and name not in self.finished
                and name not in self.failed_writes, 'WRITE_SCOPE')
        try:
            if name not in self.allocated:
                require(name not in self.allocation_attempted, 'WRITE_ALLOCATION_ALREADY_ATTEMPTED')
                self.allocation_attempted.add(name)
                fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=self.dirfd)
                # Register ownership before any fstat or directory fsync can
                # raise, so an acquired descriptor always reaches preservation.
                self.allocated.add(name)
                self.fd[name] = fd
                self.count[name] = 0
                self.digests[name] = hashlib.sha256()
                self.lifecycle[name] = {'file_sync': 'not_attempted', 'close': 'not_attempted',
                                        'parent_sync': 'not_attempted', 'readback': 'not_attempted',
                                        'creation_parent_sync': 'attempted'}
                require(stat.S_ISREG(os.fstat(fd).st_mode), 'WRITE_TYPE')
                try:
                    os.fsync(self.dirfd)
                except BaseException:
                    self.lifecycle[name]['creation_parent_sync'] = 'failed'
                    raise
                self.lifecycle[name]['creation_parent_sync'] = 'succeeded'
            require(name in self.fd and self.lifecycle[name]['file_sync'] == 'not_attempted'
                    and self.lifecycle[name]['close'] == 'not_attempted'
                    and name not in self.preservation_attempted, 'WRITE_ALREADY_FINALIZING')
            require(self.count[name] + len(raw) <= CAPS[name], 'WRITE_FILE_CAP')
            require(self.total + len(raw) <= TOTAL_CAP, 'WRITE_TOTAL_CAP')
            position = 0
            while position < len(raw):
                self.reader.check()
                wrote = os.write(self.fd[name], raw[position:])
                require(wrote > 0, 'WRITE_SHORT')
                self.count[name] += wrote
                self.total += wrote
                self.digests[name].update(raw[position:position + wrote])
                position += wrote
        except BaseException:
            self.failed_writes.add(name)
            raise

    def finish(self, name):
        require(name in self.allocated and name in self.fd and name not in self.finished
                and name not in self.failed_writes and name not in self.preservation_attempted, 'WRITE_FINISH')
        self.once(name, 'file_sync')
        self.once(name, 'close')
        self.once(name, 'parent_sync')
        state = self.lifecycle[name]
        require(state['readback'] == 'not_attempted', 'READBACK_ALREADY_ATTEMPTED')
        state['readback'] = 'attempted'
        fd = None
        primary_failure = False
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=self.dirfd)
            before = os.fstat(fd)
            require(stat.S_ISREG(before.st_mode) and before.st_size == self.count[name], 'READBACK_TYPE_SIZE')
            digest = hashlib.sha256()
            total = 0
            while True:
                self.reader.check()
                raw = os.read(fd, 65536)
                if not raw:
                    break
                total += len(raw)
                self.reader.readback_bytes += len(raw)
                require(self.reader.bytes + self.reader.readback_bytes <= READ_CAP, 'READ_TOTAL')
                require(total <= CAPS[name], 'READBACK_CAP')
                digest.update(raw)
            require(stable_stat(os.fstat(fd)) == stable_stat(before) and total == self.count[name]
                    and digest.hexdigest() == self.digests[name].hexdigest(), 'READBACK_PIN')
        except BaseException:
            primary_failure = True
            state['readback'] = 'failed'
            raise
        finally:
            if fd is not None:
                close_preserving_primary(fd, primary_failure)
        state['readback'] = 'succeeded'
        self.finished[name] = {'size_bytes': total, 'sha256': digest.hexdigest()}
        return self.finished[name]

    def json(self, name, value):
        self.append(name, canonical(value))
        return self.finish(name)

    def diagnostic(self, stage, code, count=0):
        require(stage in ('START', 'OLD', 'NEW', 'DELTA', 'DONE', 'FAIL')
                and code in ('ENTER', 'VERIFIED', 'COMPLETE', 'CLOSED_FAILURE', 'EXCEPTION')
                and type(count) is int and 0 <= count <= 10000, 'LOG_VOCABULARY')
        raw = canonical({'stage': stage, 'code': code, 'count': count})
        require(len(raw) <= 256, 'LOG_RECORD')
        self.append('phase.log', raw)

    def failure_log_once(self, code):
        name = 'phase.log'
        if name in self.finished or name in self.failed_writes:
            return
        if name in self.allocation_attempted and name not in self.allocated:
            return
        if name in self.allocated and (name not in self.fd
                or self.lifecycle[name]['file_sync'] != 'not_attempted'
                or self.lifecycle[name]['close'] != 'not_attempted'):
            return
        self.diagnostic('FAIL', code)
        self.finish(name)

    def preserve_partials_once(self, names):
        # Only source-owned existing descriptors; no reopen, data write,
        # readback, JSON completion, deletion or substitute output. The first
        # pass handles existing sinks; a second call may handle only a newly
        # allocated failure receipt. Each sink/action still runs at most once.
        require(type(names) is tuple and len(names) <= 5 and all(name in CAPS for name in names), 'PARTIAL_SCOPE')
        for name in names:
            if name not in self.allocated or name in self.finished or name in self.preservation_attempted:
                continue
            self.preservation_attempted.add(name)
            for action in ('file_sync', 'close', 'parent_sync'):
                if self.lifecycle[name][action] != 'not_attempted':
                    continue
                if action in ('file_sync', 'close') and name not in self.fd:
                    self.lifecycle[name][action] = 'descriptor_unavailable'
                    continue
                try:
                    self.once(name, action)
                except BaseException:
                    # Per-action state records this secondary failure. It may
                    # not suppress another action/sink or the independent receipt.
                    pass

    def partial_status(self):
        return [{'name': name, 'confirmed_written_bytes': self.count[name],
                 'confirmed_prefix_sha256': self.digests[name].hexdigest(),
                 'complete_verified': name in self.finished,
                 'preservation_attempted': name in self.preservation_attempted,
                 'lifecycle': self.lifecycle[name].copy()}
                for name in sorted(self.allocated)]

    def close_parent_once(self):
        if self.parent_close != 'not_attempted':
            return
        try:
            self.reader.check()
        except BaseException:
            self.parent_close = 'deadline_unavailable'
            raise
        self.parent_close = 'attempted'
        try:
            os.close(self.dirfd)
        except BaseException:
            self.parent_close = 'failed'
            raise
        self.parent_close = 'succeeded'

def expected_domain(ctx):
    inputs = ctx.named_json('input_roster')['records']
    custody = ctx.named_json('custody_roster')['ordered_produced_custody_states']
    require(len(inputs) == 676 and len(custody) == 34, 'DOMAIN_RECORDS')
    result = set()
    paths = {}
    for row in inputs:
        key = ('input', row['type'], row['old_size_bytes'], row['old_sha256'])
        result.add(key)
        paths.setdefault(('input', row['ordinal'], row['relative_path']), set()).add(key)
    require(len(result) == 296, 'INPUT_DOMAIN')
    for row in custody:
        state = row['old_state']
        key = ('produced_output', state['type'], state['size_bytes'], state['sha256'])
        result.add(key)
        paths.setdefault(('produced_output', row['ordinal'], state['relative_path']), set()).add(key)
    require(len(result) == 328 and sum(key[2] for key in result) == 4198534, 'TOTAL_DOMAIN')
    return result, paths


class Pairing:
    def __init__(self, ctx):
        self.ctx = ctx
        self.domain, self.paths = expected_domain(ctx)
        self.old = {}
        self.new = {}
        self.trace = []
        self.stable = set()
        self.index = 0
        self.phase = 'old'

    def emit(self, role, ordinal, path, raw, stable_key):
        self.ctx.reader.check()
        require(role in ('input', 'produced_output') and type(ordinal) is int
                and type(path) is str and type(raw) is bytes and len(raw) <= MAX_RAW, 'EMIT_SHAPE')
        stable = canonical([role, ordinal, path, stable_key])
        require(len(stable) <= 1024, 'EMIT_KEY')
        if self.phase == 'old':
            require(stable not in self.stable, 'EMIT_DUPLICATE_KEY')
            self.stable.add(stable)
            digest = sha(raw)
            matches = [key for key in self.paths.get((role, ordinal, path), ())
                       if key[2] == len(raw) and key[3] == digest]
            require(len(matches) == 1, 'OLD_PREIMAGE_MISMATCH')
            key = matches[0]
            if key in self.old:
                require(self.old[key] == raw, 'OLD_ALIAS_BYTES')
            else:
                self.old[key] = raw
            self.trace.append((stable, key))
            require(len(self.trace) <= 366, 'EMISSION_CAP')
        else:
            require(self.phase == 'new' and self.index < len(self.trace), 'NEW_TRACE_LENGTH')
            expected, key = self.trace[self.index]
            self.index += 1
            require(stable == expected and len(raw) == key[2], 'NEW_TRACE_IDENTITY')
            if key in self.new:
                require(self.new[key] == raw, 'NEW_ALIAS_BYTES')
            else:
                self.new[key] = raw
            require(sha(raw) != key[3], 'NEW_UNCHANGED_OBJECT')

    def old_complete(self):
        require(set(self.old) == self.domain and len(self.trace) == 366, 'OLD_COMPLETE')
        # Every accepted occurrence is covered by the exact proven raw identity.
        # No physical accounting discount is made for identity reuse.
        self.phase = 'new'

    def new_complete(self):
        require(set(self.new) == self.domain and self.index == 366, 'NEW_COMPLETE')
        self.phase = 'closed'
        return {key: {'type': key[1], 'size_bytes': key[2], 'sha256': sha(self.new[key])}
                for key in sorted(self.domain)}

    def write_pairs(self, writer, identity):
        require(self.phase == 'closed', 'PAIR_PHASE')
        name = 'PREIMAGE-PAIRS.json'
        header = {'schema': 'worker38-native05-preimage-pairs-v1', 'finite_recipe_sha256': identity,
                  'old_root': OLD_ROOT, 'new_root': NEW_ROOT, 'records': 328}
        start = canonical(header).rstrip(b'\n')[:-1] + b',"pairs":['
        require(len(start) + 3 <= 65536, 'PAIR_FRAMING')
        writer.append(name, start)
        encoded_count = 0
        for index, key in enumerate(sorted(self.domain)):
            old, new = self.old[key], self.new[key]
            old64, new64 = base64.b64encode(old).decode('ascii'), base64.b64encode(new).decode('ascii')
            require(base64.b64decode(old64, validate=True) == old
                    and base64.b64decode(new64, validate=True) == new, 'PAIR_BASE64_READBACK')
            record = {'id': index + 1, 'lineage': 'independent_literal_input' if key[0] == 'input' else 'produced_output',
                      'type': key[1], 'size_bytes': key[2], 'old_sha256': key[3],
                      'new_sha256': sha(new), 'old_base64': old64, 'new_base64': new64}
            raw = canonical(record).rstrip(b'\n')
            encoded_count += len(old64) + len(new64)
            require(len(raw) - len(old64) - len(new64) + 1 <= 1024, 'PAIR_RECORD_FRAMING')
            writer.append(name, (b',' if index else b'') + raw)
        require(encoded_count == 11197144, 'PAIR_PAYLOAD_COUNT')
        writer.append(name, b']}\n')
        return writer.finish(name)


def run_builders(ctx, namespace, emit):
    build_f07(ctx, namespace, emit)
    build_other_inputs(ctx, namespace, emit)
    build_custody(ctx, namespace, emit)


def write_delta(writer, edits, identity):
    # One source-owned finite serializer; every exact leaf remains explicit.
    groups = metadata_pack_delta(edits)
    value = {'schema': 'worker38-native05-finite-pointer-delta-v1',
             'finite_recipe_sha256': identity, 'old_root': OLD_ROOT, 'new_root': NEW_ROOT,
             'historical_environment_parent_only': True, 'historical_P15_reexecuted': False,
             'native05_environment_certified': False,
             'leaf_records': len(edits), 'packed_records': len(groups), 'records': groups}
    require(len(canonical({k: v for k, v in value.items() if k != 'records'})) + 32 <= 65536, 'DELTA_FRAMING')
    return writer.json('NATIVE05-LINEAGE-DELTA.json', value)


def main():
    # This program cannot establish authentic root approval itself. Its command,
    # exact grant hash, source/scope hashes and absence guard require external
    # durable GO and managed preflight. No grant is shipped in source phase.
    resource.setrlimit(resource.RLIMIT_AS, (536870912, 536870912))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16777216, 16777216))
    reader = Reader()
    writer = None
    stage = 'START'
    first_failure = None
    try:
        require(len(sys.argv) == 3 and sys.argv[1] == '--grant-sha256' and hex64(sys.argv[2]), 'ARGUMENTS')
        grant_raw = reader.read(SOURCE_DIR + '/MATERIALIZATION-GRANT.json', 65536)
        require(sha(grant_raw) == sys.argv[2], 'GRANT_PIN')
        grant = json.loads(grant_raw)
        require(set(grant) == {'schema', 'authority_url', 'source_sha256', 'scope_sha256', 'execute_authorized', 'output_root'}
                and grant['schema'] == 'worker38-native05-lineage-materialization-grant-v1'
                and grant['execute_authorized'] is True and grant['output_root'] == OUTPUT_DIR
                and type(grant['authority_url']) is str
                and grant['authority_url'].startswith('https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-')
                and grant['authority_url'].rsplit('-', 1)[-1].isdigit(), 'GRANT_SCOPE')
        source_raw = reader.read(SOURCE_DIR + '/transform-native05-lineage.py', 1048576)
        require(sha(source_raw) == grant['source_sha256'], 'SOURCE_PIN')
        identity = sha(source_raw)
        scope_raw = reader.read(SOURCE_DIR + '/SCOPE.json', 262144)
        require(sha(scope_raw) == grant['scope_sha256'], 'SCOPE_PIN')
        scope = json.loads(scope_raw)
        require(scope['schema'] == 'worker38-native05-closed-lineage-scope-v1'
                and scope['old_root'] == OLD_ROOT and scope['new_root'] == NEW_ROOT
                and scope['expected_emit_count'] == 366 and scope['expected_pair_count'] == 328, 'SCOPE_DOMAIN')
        del source_raw, scope_raw
        writer = Writer(reader)
        writer.json('ATTEMPT-STARTED.json', {'schema': 'worker38-native05-lineage-attempt-v1',
                    'authority_sha256': sys.argv[2], 'authority_url': grant['authority_url'],
                    'source_sha256': identity, 'scope_sha256': grant['scope_sha256'],
                    'output_root': OUTPUT_DIR, 'attempts': 1, 'retry_allowed': False})
        writer.diagnostic('START', 'ENTER')
        ctx = Context(reader, scope)
        accepted_parent_digest = metadata_digest(ctx.accepted)
        pairing = Pairing(ctx)
        stage = 'OLD'
        run_builders(ctx, OLD_ROOT, pairing.emit)
        pairing.old_complete()
        writer.diagnostic('OLD', 'VERIFIED', 328)
        stage = 'NEW'
        run_builders(ctx, NEW_ROOT, pairing.emit)
        verified = pairing.new_complete()
        writer.diagnostic('NEW', 'VERIFIED', 328)
        pairing.write_pairs(writer, identity)
        stage = 'DELTA'
        obligations = ctx.named_json('obligations')
        custody_pairs = {key: value for key, value in verified.items() if key[0] == 'produced_output'}
        custody_result = custody_rebind_commitments(ctx.accepted, custody_pairs, identity, obligations)
        custody_edits = custody_result['deltas']
        edits = metadata_rebind_commitments(ctx.accepted, obligations, ctx.named_json('input_roster'),
                                            ctx.named_json('path_roster'), verified, identity, custody_edits)
        edits = custody_edits + edits
        roster = sorted([r['target'], r['pointer']] for r in edits)
        require(len(roster) == scope['delta_leaf_count'] and sha(canonical(roster)) == scope['delta_leaf_roster_sha256'], 'DELTA_EXACT_ROSTER')
        require(metadata_digest(ctx.accepted) == accepted_parent_digest, 'PARENT_MUTATED')
        write_delta(writer, edits, identity)
        writer.diagnostic('DONE', 'COMPLETE', len(edits))
        writer.finish('phase.log')
        writer.json('TRANSFORM-RECEIPT.json', {'schema': 'worker38-native05-lineage-receipt-v1',
                    'complete': True, 'source_sha256': identity, 'scope_sha256': grant['scope_sha256'],
                    'authority_sha256': sys.argv[2], 'old_pairs_verified': 328, 'new_pairs_verified': 328,
                    'emissions_per_pass': 366, 'delta_leaf_count': len(edits), 'named_input_bytes': reader.bytes,
                    'read_pins': reader.pins, 'generated_sink_readback_bytes_before_receipt': reader.readback_bytes,
                    'outputs': writer.finished.copy(),
                    'first_failure': None, 'outer_exit_independently_required': True,
                    'native_certification': False, 'native_execution_authorized': False})
        writer.close_parent_once()
        return 0
    except BaseException as exc:
        # Fixed class codes only; never stringify exception/metadata/raw values.
        code = 'CLOSED_FAILURE' if isinstance(exc, ClosedFailure) else 'EXCEPTION'
        detail = exc.args[0] if len(exc.args) == 1 and type(exc.args[0]) is str and exc.args[0] in ERROR_CODES else code
        first_failure = {'stage': stage, 'code': code, 'detail': detail}
        if writer is not None:
            # Freeze first_failure above once. These three independent blocks
            # cannot substitute a secondary logging/durability cause for it.
            try:
                writer.failure_log_once(code)
            except BaseException:
                pass
            try:
                writer.preserve_partials_once(tuple(CAPS))
            except BaseException:
                pass
            try:
                # Allocation attempts are terminal even if exclusive open or
                # success-receipt finalization failed; never recreate/overwrite.
                if 'TRANSFORM-RECEIPT.json' not in writer.allocation_attempted:
                    writer.json('TRANSFORM-RECEIPT.json', {'schema': 'worker38-native05-lineage-receipt-v1',
                                'complete': False, 'first_failure': first_failure,
                                'named_input_bytes': reader.bytes, 'retained_outputs': writer.finished.copy(),
                                'owned_sink_status_before_failure_receipt': writer.partial_status(),
                                'retry_allowed': False, 'native_certification': False})
            except BaseException:
                pass
            finally:
                # Only a newly allocated unsuccessful receipt is eligible here;
                # per-sink state suppresses every repeated preservation action.
                try:
                    writer.preserve_partials_once(('TRANSFORM-RECEIPT.json',))
                except BaseException:
                    pass
                try:
                    writer.close_parent_once()
                except BaseException:
                    pass
        return 1


if __name__ == '__main__':
    sys.exit(main())
