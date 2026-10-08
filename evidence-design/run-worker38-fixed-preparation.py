"""Closed397-method native preparation entrypoint; never a research launcher.

This file is inert until the separately reviewed exact map hash is supplied.
The map pins all source, fixture, command, retention and output definitions.
"""
from __future__ import annotations

import base64
import builtins
import fnmatch
import gc
import hashlib
import importlib.abc
import importlib.util
import io
import json
import os
from pathlib import Path
import resource
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / 'evidence-design/worker38-fixed-fixtures.json'
OUTPUT = Path('/workspace/shared/worker38-native-batch-05')
LOG_CAP = 8 * 1024 ** 2
PREFIX_CAP = 24 * 1024 ** 2
MEMORY_CAP = 512 * 1024 ** 2
GLOBAL_RESERVE = 65536
GLOBAL_RECORD_LIMITS = {'start.json': 4096, 'receipt.json': 16384, 'index.json': 45056}
# Tests deliberately mock these modules. Capture real observations beforehand.
NOW = time.monotonic
BOOT_NS = time.clock_gettime_ns
OPEN = builtins.open
LSTAT = os.lstat
LISTDIR = os.listdir
READLINK = os.readlink
GETPID = os.getpid
GETRLIMIT = resource.getrlimit
FSYNC = os.fsync
OS_WRITE = os.write
OS_OPEN = os.open
OS_CLOSE = os.close
OS_READ = os.read
STAT = os.stat
FSTAT = os.fstat
GET_PROFILE = sys.getprofile
GET_TRACE = sys.gettrace
GET_TIMER = signal.getitimer
GET_HANDLER = signal.getsignal
GC_ENABLED = gc.isenabled
GC_THRESHOLDS = gc.get_threshold
THREAD_COUNT = threading.active_count
MAJOR = os.major
MINOR = os.minor
ORIGINAL_TEMPORARY_DIRECTORY = tempfile.TemporaryDirectory

# Exact adopted verifier set; F07 and other selectors never emit these witnesses.
INPUT_WITNESS_SELECTORS = (
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
)

# Adopted finite source seams, independent of runtime map contents.
LOADER_CONTEXT_EVENTS = {
    'tests/test_worker38_core.py:CoreTests.test_25_loader_rejects_noncanonical_paths': (
        ('relative_cache', 'c25-01', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('cache_matches_variant', 'executable_matches_variant', 'selected_environment_matches_variant', 'node_layout_matches_variant')),
        ('dotdot_cache', 'c25-02', ('t03/toolcache/Python/3.11.16/x64/bin/python3.11', 't03/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('cache_matches_variant', 'executable_matches_variant', 'selected_environment_matches_variant', 'node_layout_matches_variant')),
        ('wrong_executable', 'c25-03', ('t04/toolcache/Python/3.11.16/x64/bin/python3.11', 't04/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0', 't04/toolcache/Python/3.11.16/x64/bin/other-python'), ('cache_matches_variant', 'executable_matches_variant', 'selected_environment_matches_variant', 'node_layout_matches_variant')),
        ('symlink_library', 'c25-04', ('t05/toolcache/Python/3.11.16/x64/bin/python3.11', 't05/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0', 't05/toolcache/Python/3.11.16/x64/lib/target'), ('cache_matches_variant', 'executable_matches_variant', 'selected_environment_matches_variant', 'node_layout_matches_variant')),
        ('symlink_directory', 'c25-05', ('t06/toolcache/Python/3.11.16/x64/bin/python3.11', 't06/toolcache/Python/3.11.16/x64/lib', 't06/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0', 't06/toolcache/Python/3.11.16/x64/other-lib/libpython3.11.so.1.0'), ('cache_matches_variant', 'executable_matches_variant', 'selected_environment_matches_variant', 'node_layout_matches_variant')),
        ('missing_library', 'c25-06', ('t07/toolcache/Python/3.11.16/x64/bin/python3.11', 't07/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('cache_matches_variant', 'executable_matches_variant', 'selected_environment_matches_variant', 'node_layout_matches_variant')),
        ('directory_library', 'c25-07', ('t08/toolcache/Python/3.11.16/x64/bin/python3.11', 't08/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('cache_matches_variant', 'executable_matches_variant', 'selected_environment_matches_variant', 'node_layout_matches_variant')),
    ),
    'tests/test_worker38_core.py:CoreTests.test_26_loader_file_identity_stays_stable': (
        ('P01-before-stable-read', 'c26-01', ('t01/literal-library',), ('file_bytes_match_fixed',)),
        ('P02-before-mutating-read', 'c26-02', ('t01/literal-library',), ('file_bytes_match_fixed',)),
        ('P02-after-mocks-before-reset', 'c26-03', ('t01/literal-library',), ('mutation_ran', 'file_bytes_match_changed', 'injected_mtime_delta_is_one')),
        ('P03-before-mutating-read', 'c26-04', ('t01/literal-library',), ('file_bytes_match_fixed',)),
        ('P03-after-mocks-before-next-context', 'c26-05', ('t01/literal-library',), ('mutation_ran', 'file_bytes_match_fixed', 'path_inode_differs_from_pre_read')),
        ('P04-before-loader-identity', 'c26-06', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('fixed_executable_hash', 'fixed_library_hash', 'mocked_second_hash_differs', 'mocked_nonhash_metadata_equal')),
    ),
    'tests/test_worker38_core.py:CoreTests.test_27_loader_rejects_mapping_variants': (
        ('absent', 'c27-01', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'mapping_variant_matches_recipe')),
        ('alias_path', 'c27-02', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'mapping_variant_matches_recipe')),
        ('deleted', 'c27-03', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'mapping_variant_matches_recipe')),
        ('wrong_device', 'c27-04', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'mapping_variant_matches_recipe')),
        ('wrong_inode', 'c27-05', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'mapping_variant_matches_recipe')),
        ('other_version', 'c27-06', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'mapping_variant_matches_recipe')),
        ('malformed', 'c27-07', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'mapping_variant_matches_recipe')),
        ('same_inode_alias', 'c27-08', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'mapping_variant_matches_recipe')),
        ('changed_mapping', 'c27-09', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'mapping_variant_matches_recipe')),
    ),
    'tests/test_worker38_core.py:CoreTests.test_28_loader_rejects_ambient_loader_settings': (
        ('LD_PRELOAD', 'c28-01', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'selected_environment_matches_variant')),
        ('LD_AUDIT', 'c28-02', ('t03/toolcache/Python/3.11.16/x64/bin/python3.11', 't03/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'selected_environment_matches_variant')),
        ('LD_DEBUG', 'c28-03', ('t04/toolcache/Python/3.11.16/x64/bin/python3.11', 't04/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'selected_environment_matches_variant')),
        ('LD_UNKNOWN', 'c28-04', ('t05/toolcache/Python/3.11.16/x64/bin/python3.11', 't05/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'selected_environment_matches_variant')),
        ('LD_LIBRARY_PATH-absent', 'c28-05', ('t06/toolcache/Python/3.11.16/x64/bin/python3.11', 't06/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'selected_environment_matches_variant')),
        ('LD_LIBRARY_PATH-colon', 'c28-06', ('t07/toolcache/Python/3.11.16/x64/bin/python3.11', 't07/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'selected_environment_matches_variant')),
        ('LD_LIBRARY_PATH-wrong', 'c28-07', ('t08/toolcache/Python/3.11.16/x64/bin/python3.11', 't08/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'selected_environment_matches_variant')),
    ),
    'tests/test_worker38_core.py:CoreTests.test_29_loader_portable_pin_exact_fields': (
        ('positive-full-identity', 'c29-01', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'argument_shape_matches_recipe')),
        ('positive-portable-pin', 'c29-02', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'argument_shape_matches_recipe')),
        ('negative-0', 'c29-03', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'argument_shape_matches_recipe')),
        ('negative-1', 'c29-04', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'argument_shape_matches_recipe')),
        ('negative-2', 'c29-05', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'argument_shape_matches_recipe')),
        ('negative-3', 'c29-06', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'argument_shape_matches_recipe')),
        ('negative-4', 'c29-07', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'argument_shape_matches_recipe')),
        ('negative-5', 'c29-08', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'argument_shape_matches_recipe')),
        ('negative-6', 'c29-09', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'argument_shape_matches_recipe')),
        ('negative-7', 'c29-10', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'argument_shape_matches_recipe')),
        ('negative-8', 'c29-11', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'argument_shape_matches_recipe')),
    ),
    'tests/test_worker38_core.py:CoreTests.test_30_loader_full_identity_consistency': (
        ('extra', 'c30-01', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'identity_mutation_matches_recipe')),
        ('missing', 'c30-02', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'identity_mutation_matches_recipe')),
        ('cache', 'c30-03', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'identity_mutation_matches_recipe')),
        ('executable', 'c30-04', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'identity_mutation_matches_recipe')),
        ('library', 'c30-05', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'identity_mutation_matches_recipe')),
        ('directory', 'c30-06', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'identity_mutation_matches_recipe')),
        ('mapped_path', 'c30-07', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'identity_mutation_matches_recipe')),
        ('device', 'c30-08', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'identity_mutation_matches_recipe')),
        ('inode', 'c30-09', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'identity_mutation_matches_recipe')),
        ('environment', 'c30-10', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('literal_files_match', 'identity_mutation_matches_recipe')),
    ),
    'tests/test_worker38_core.py:CoreTests.test_31_clean_environment_requires_verified_loader': (
        ('clean-without-loader', 'c31-01', (), ('dirty_mapping_unchanged', 'loader_argument_matches_recipe', 'local_verification_mode_matches_recipe')),
        ('clean-with-full-identity', 'c31-02', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('dirty_mapping_unchanged', 'loader_argument_matches_recipe', 'local_verification_mode_matches_recipe')),
        ('clean-with-portable-pin', 'c31-03', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('dirty_mapping_unchanged', 'loader_argument_matches_recipe', 'local_verification_mode_matches_recipe')),
        ('reject-different-inode', 'c31-04', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('dirty_mapping_unchanged', 'loader_argument_matches_recipe', 'local_verification_mode_matches_recipe')),
        ('reject-different-pin', 'c31-05', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('dirty_mapping_unchanged', 'loader_argument_matches_recipe', 'local_verification_mode_matches_recipe')),
        ('reject-string-loader', 'c31-06', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('dirty_mapping_unchanged', 'loader_argument_matches_recipe', 'local_verification_mode_matches_recipe')),
        ('reject-local-verification-failure', 'c31-07', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('dirty_mapping_unchanged', 'loader_argument_matches_recipe', 'local_verification_mode_matches_recipe')),
    ),
    'tests/test_worker38_core.py:CoreTests.test_32_runtime_binds_loader_identity': (
        ('runtime-positive-child', 'c32-01', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('runtime_mock_state_matches_recipe', 'loader_mode_matches_recipe', 'selected_environment_matches_recipe')),
        ('runtime-loader-failure', 'c32-02', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('runtime_mock_state_matches_recipe', 'loader_mode_matches_recipe', 'selected_environment_matches_recipe')),
        ('runtime-unexpected-environment', 'c32-03', ('t02/toolcache/Python/3.11.16/x64/bin/python3.11', 't02/toolcache/Python/3.11.16/x64/lib/libpython3.11.so.1.0'), ('runtime_mock_state_matches_recipe', 'loader_mode_matches_recipe', 'selected_environment_matches_recipe')),
    ),
}
TRANSPORT_INPUT_EVENTS = {
    'tests/test_worker38_transport.py:OfflineTransportPlan.test_PW06_strict_provider_zip_limit_uses_actual_size': (
        ('accepted-wrapper-before-positive-check', 'pw06-01', ('t01/literal-github-download.zip-1',), ()),
    ),
    'tests/test_worker38_transport.py:OfflineTransportPlan.test_T15_source_mutation_is_rejected_and_preserved': (
        ('after-original-inventory-before-mutation', 't15-01', ('t01/mutable-source-1/a',), ()),
    ),
}
LOADER_CONTEXT_CAP = 8192
LOADER_RECORD_CAP = 16384
TRANSPORT_INPUT_CAPS = {'pw06-01': 735, 't15-01': 668}

# Fixed source-derived names and exact scalar tags, never discovered at runtime.
_LOADER_FIELDS_C25_01 = (
    ('variant', 'str'),
    ('cache', 'str'),
    ('executable', 'str'),
    ('library_environment', 'str'),
)
_LOADER_FIELDS_C26_01 = (
    ('content_state', 'str'),
)
_LOADER_FIELDS_C26_02 = (
    ('content_state', 'str'),
    ('changed', 'bool'),
    ('initial.container', 'str'),
    ('initial.dev', 'int'),
    ('initial.ino', 'int'),
    ('initial.mode', 'int'),
    ('initial.size', 'int'),
    ('initial.mtime_ns', 'int'),
    ('initial.ctime_ns', 'int'),
    ('initial.nlink', 'int'),
)
_LOADER_FIELDS_C26_03 = (
    ('content_state', 'str'),
    ('changed', 'bool'),
    ('initial.container', 'str'),
    ('initial.dev', 'int'),
    ('initial.ino', 'int'),
    ('initial.mode', 'int'),
    ('initial.size', 'int'),
    ('initial.mtime_ns', 'int'),
    ('initial.ctime_ns', 'int'),
    ('initial.nlink', 'int'),
    ('observed.container', 'str'),
    ('observed.dev', 'int'),
    ('observed.ino', 'int'),
    ('observed.mode', 'int'),
    ('observed.size', 'int'),
    ('observed.mtime_ns', 'int'),
    ('observed.ctime_ns', 'int'),
    ('observed.nlink', 'int'),
    ('returned.container', 'str'),
    ('returned.dev', 'int'),
    ('returned.ino', 'int'),
    ('returned.mode', 'int'),
    ('returned.size', 'int'),
    ('returned.mtime_ns', 'int'),
    ('returned.ctime_ns', 'int'),
    ('returned.nlink', 'int'),
)
_LOADER_FIELDS_C26_04 = (
    ('content_state', 'str'),
    ('changed', 'bool'),
    ('initial.dev', 'int'),
    ('initial.ino', 'int'),
)
_LOADER_FIELDS_C26_06 = (
    ('executable.shape', 'str'),
    ('executable.sha256', 'str'),
    ('executable.size_bytes', 'int'),
    ('executable.device.shape', 'str'),
    ('executable.device.major', 'int'),
    ('executable.device.minor', 'int'),
    ('executable.inode', 'int'),
    ('executable._stat.container', 'str'),
    ('executable._stat.dev', 'int'),
    ('executable._stat.ino', 'int'),
    ('executable._stat.mode', 'int'),
    ('executable._stat.size', 'int'),
    ('executable._stat.mtime_ns', 'int'),
    ('executable._stat.ctime_ns', 'int'),
    ('executable._stat.nlink', 'int'),
    ('library.shape', 'str'),
    ('library.sha256', 'str'),
    ('library.size_bytes', 'int'),
    ('library.device.shape', 'str'),
    ('library.device.major', 'int'),
    ('library.device.minor', 'int'),
    ('library.inode', 'int'),
    ('library._stat.container', 'str'),
    ('library._stat.dev', 'int'),
    ('library._stat.ino', 'int'),
    ('library._stat.mode', 'int'),
    ('library._stat.size', 'int'),
    ('library._stat.mtime_ns', 'int'),
    ('library._stat.ctime_ns', 'int'),
    ('library._stat.nlink', 'int'),
    ('changed.shape', 'str'),
    ('changed.sha256', 'str'),
    ('changed.size_bytes', 'int'),
    ('changed.device.shape', 'str'),
    ('changed.device.major', 'int'),
    ('changed.device.minor', 'int'),
    ('changed.inode', 'int'),
    ('changed._stat.container', 'str'),
    ('changed._stat.dev', 'int'),
    ('changed._stat.ino', 'int'),
    ('changed._stat.mode', 'int'),
    ('changed._stat.size', 'int'),
    ('changed._stat.mtime_ns', 'int'),
    ('changed._stat.ctime_ns', 'int'),
    ('changed._stat.nlink', 'int'),
)
_LOADER_FIELDS_C27_01 = (
    ('maps.container', 'str'),
    ('maps.0', 'str'),
    ('device.major', 'int'),
    ('device.minor', 'int'),
    ('inode', 'int'),
)
_LOADER_FIELDS_C27_09 = (
    ('maps.container', 'str'),
    ('maps.0', 'str'),
    ('maps.1', 'str'),
    ('device.major', 'int'),
    ('device.minor', 'int'),
    ('inode', 'int'),
)
_LOADER_FIELDS_C28_01 = (
    ('key', 'str'),
    ('present', 'bool'),
    ('value', 'str'),
    ('cache', 'str'),
    ('library_environment', 'str'),
)
_LOADER_FIELDS_C28_05 = (
    ('key', 'str'),
    ('present', 'bool'),
    ('value', 'null'),
    ('cache', 'str'),
    ('library_environment', 'null'),
)
_LOADER_FIELDS_C29_01 = (
    ('argument.shape', 'str'),
    ('argument.mask', 'int'),
    ('argument.schema', 'str'),
    ('argument.tool_cache', 'str'),
    ('argument.executable_path', 'str'),
    ('argument.executable_sha256', 'str'),
    ('argument.library_relative_path', 'str'),
    ('argument.library_path', 'str'),
    ('argument.library_directory', 'str'),
    ('argument.library_sha256', 'str'),
    ('argument.library_size_bytes', 'int'),
    ('argument.library_inode', 'int'),
    ('argument.extra', 'null'),
    ('argument.library_device.shape', 'str'),
    ('argument.library_device.mask', 'int'),
    ('argument.library_device.major', 'int'),
    ('argument.library_device.minor', 'int'),
    ('argument.mapped_library.shape', 'str'),
    ('argument.mapped_library.mask', 'int'),
    ('argument.mapped_library.path', 'str'),
    ('argument.mapped_library.inode', 'int'),
    ('argument.mapped_library.device.shape', 'str'),
    ('argument.mapped_library.device.mask', 'int'),
    ('argument.mapped_library.device.major', 'int'),
    ('argument.mapped_library.device.minor', 'int'),
    ('argument.loader_environment.shape', 'str'),
    ('argument.loader_environment.mask', 'int'),
    ('argument.loader_environment.LD_LIBRARY_PATH', 'str'),
    ('argument.loader_environment.LD_PRELOAD', 'null'),
)
_LOADER_FIELDS_C29_02 = (
    ('argument.shape', 'str'),
    ('argument.mask', 'int'),
    ('argument.schema', 'str'),
    ('argument.tool_cache', 'null'),
    ('argument.executable_path', 'null'),
    ('argument.executable_sha256', 'str'),
    ('argument.library_relative_path', 'str'),
    ('argument.library_path', 'null'),
    ('argument.library_directory', 'null'),
    ('argument.library_sha256', 'str'),
    ('argument.library_size_bytes', 'int'),
    ('argument.library_inode', 'null'),
    ('argument.extra', 'null'),
    ('argument.library_device.shape', 'str'),
    ('argument.library_device.mask', 'null'),
    ('argument.library_device.major', 'null'),
    ('argument.library_device.minor', 'null'),
    ('argument.mapped_library.shape', 'str'),
    ('argument.mapped_library.mask', 'null'),
    ('argument.mapped_library.path', 'null'),
    ('argument.mapped_library.inode', 'null'),
    ('argument.mapped_library.device.shape', 'str'),
    ('argument.mapped_library.device.mask', 'null'),
    ('argument.mapped_library.device.major', 'null'),
    ('argument.mapped_library.device.minor', 'null'),
    ('argument.loader_environment.shape', 'str'),
    ('argument.loader_environment.mask', 'null'),
    ('argument.loader_environment.LD_LIBRARY_PATH', 'null'),
    ('argument.loader_environment.LD_PRELOAD', 'null'),
)
_LOADER_FIELDS_C29_03 = (
    ('argument.shape', 'str'),
    ('argument.mask', 'int'),
    ('argument.schema', 'str'),
    ('argument.tool_cache', 'null'),
    ('argument.executable_path', 'null'),
    ('argument.executable_sha256', 'str'),
    ('argument.library_relative_path', 'str'),
    ('argument.library_path', 'null'),
    ('argument.library_directory', 'null'),
    ('argument.library_sha256', 'null'),
    ('argument.library_size_bytes', 'int'),
    ('argument.library_inode', 'null'),
    ('argument.extra', 'null'),
    ('argument.library_device.shape', 'str'),
    ('argument.library_device.mask', 'null'),
    ('argument.library_device.major', 'null'),
    ('argument.library_device.minor', 'null'),
    ('argument.mapped_library.shape', 'str'),
    ('argument.mapped_library.mask', 'null'),
    ('argument.mapped_library.path', 'null'),
    ('argument.mapped_library.inode', 'null'),
    ('argument.mapped_library.device.shape', 'str'),
    ('argument.mapped_library.device.mask', 'null'),
    ('argument.mapped_library.device.major', 'null'),
    ('argument.mapped_library.device.minor', 'null'),
    ('argument.loader_environment.shape', 'str'),
    ('argument.loader_environment.mask', 'null'),
    ('argument.loader_environment.LD_LIBRARY_PATH', 'null'),
    ('argument.loader_environment.LD_PRELOAD', 'null'),
)
_LOADER_FIELDS_C29_04 = (
    ('argument.shape', 'str'),
    ('argument.mask', 'int'),
    ('argument.schema', 'str'),
    ('argument.tool_cache', 'null'),
    ('argument.executable_path', 'null'),
    ('argument.executable_sha256', 'str'),
    ('argument.library_relative_path', 'str'),
    ('argument.library_path', 'null'),
    ('argument.library_directory', 'null'),
    ('argument.library_sha256', 'str'),
    ('argument.library_size_bytes', 'int'),
    ('argument.library_inode', 'null'),
    ('argument.extra', 'int'),
    ('argument.library_device.shape', 'str'),
    ('argument.library_device.mask', 'null'),
    ('argument.library_device.major', 'null'),
    ('argument.library_device.minor', 'null'),
    ('argument.mapped_library.shape', 'str'),
    ('argument.mapped_library.mask', 'null'),
    ('argument.mapped_library.path', 'null'),
    ('argument.mapped_library.inode', 'null'),
    ('argument.mapped_library.device.shape', 'str'),
    ('argument.mapped_library.device.mask', 'null'),
    ('argument.mapped_library.device.major', 'null'),
    ('argument.mapped_library.device.minor', 'null'),
    ('argument.loader_environment.shape', 'str'),
    ('argument.loader_environment.mask', 'null'),
    ('argument.loader_environment.LD_LIBRARY_PATH', 'null'),
    ('argument.loader_environment.LD_PRELOAD', 'null'),
)
_LOADER_FIELDS_C29_06 = (
    ('argument.shape', 'str'),
    ('argument.mask', 'int'),
    ('argument.schema', 'str'),
    ('argument.tool_cache', 'null'),
    ('argument.executable_path', 'null'),
    ('argument.executable_sha256', 'str'),
    ('argument.library_relative_path', 'str'),
    ('argument.library_path', 'null'),
    ('argument.library_directory', 'null'),
    ('argument.library_sha256', 'str'),
    ('argument.library_size_bytes', 'bool'),
    ('argument.library_inode', 'null'),
    ('argument.extra', 'null'),
    ('argument.library_device.shape', 'str'),
    ('argument.library_device.mask', 'null'),
    ('argument.library_device.major', 'null'),
    ('argument.library_device.minor', 'null'),
    ('argument.mapped_library.shape', 'str'),
    ('argument.mapped_library.mask', 'null'),
    ('argument.mapped_library.path', 'null'),
    ('argument.mapped_library.inode', 'null'),
    ('argument.mapped_library.device.shape', 'str'),
    ('argument.mapped_library.device.mask', 'null'),
    ('argument.mapped_library.device.major', 'null'),
    ('argument.mapped_library.device.minor', 'null'),
    ('argument.loader_environment.shape', 'str'),
    ('argument.loader_environment.mask', 'null'),
    ('argument.loader_environment.LD_LIBRARY_PATH', 'null'),
    ('argument.loader_environment.LD_PRELOAD', 'null'),
)
_LOADER_FIELDS_C30_01 = (
    ('argument.shape', 'str'),
    ('argument.mask', 'int'),
    ('argument.schema', 'str'),
    ('argument.tool_cache', 'str'),
    ('argument.executable_path', 'str'),
    ('argument.executable_sha256', 'str'),
    ('argument.library_relative_path', 'str'),
    ('argument.library_path', 'str'),
    ('argument.library_directory', 'str'),
    ('argument.library_sha256', 'str'),
    ('argument.library_size_bytes', 'int'),
    ('argument.library_inode', 'int'),
    ('argument.extra', 'int'),
    ('argument.library_device.shape', 'str'),
    ('argument.library_device.mask', 'int'),
    ('argument.library_device.major', 'int'),
    ('argument.library_device.minor', 'int'),
    ('argument.mapped_library.shape', 'str'),
    ('argument.mapped_library.mask', 'int'),
    ('argument.mapped_library.path', 'str'),
    ('argument.mapped_library.inode', 'int'),
    ('argument.mapped_library.device.shape', 'str'),
    ('argument.mapped_library.device.mask', 'int'),
    ('argument.mapped_library.device.major', 'int'),
    ('argument.mapped_library.device.minor', 'int'),
    ('argument.loader_environment.shape', 'str'),
    ('argument.loader_environment.mask', 'int'),
    ('argument.loader_environment.LD_LIBRARY_PATH', 'str'),
    ('argument.loader_environment.LD_PRELOAD', 'null'),
)
_LOADER_FIELDS_C30_02 = (
    ('argument.shape', 'str'),
    ('argument.mask', 'int'),
    ('argument.schema', 'str'),
    ('argument.tool_cache', 'str'),
    ('argument.executable_path', 'str'),
    ('argument.executable_sha256', 'str'),
    ('argument.library_relative_path', 'str'),
    ('argument.library_path', 'str'),
    ('argument.library_directory', 'str'),
    ('argument.library_sha256', 'str'),
    ('argument.library_size_bytes', 'int'),
    ('argument.library_inode', 'int'),
    ('argument.extra', 'null'),
    ('argument.library_device.shape', 'str'),
    ('argument.library_device.mask', 'int'),
    ('argument.library_device.major', 'int'),
    ('argument.library_device.minor', 'int'),
    ('argument.mapped_library.shape', 'str'),
    ('argument.mapped_library.mask', 'null'),
    ('argument.mapped_library.path', 'null'),
    ('argument.mapped_library.inode', 'null'),
    ('argument.mapped_library.device.shape', 'str'),
    ('argument.mapped_library.device.mask', 'null'),
    ('argument.mapped_library.device.major', 'null'),
    ('argument.mapped_library.device.minor', 'null'),
    ('argument.loader_environment.shape', 'str'),
    ('argument.loader_environment.mask', 'int'),
    ('argument.loader_environment.LD_LIBRARY_PATH', 'str'),
    ('argument.loader_environment.LD_PRELOAD', 'null'),
)
_LOADER_FIELDS_C30_10 = (
    ('argument.shape', 'str'),
    ('argument.mask', 'int'),
    ('argument.schema', 'str'),
    ('argument.tool_cache', 'str'),
    ('argument.executable_path', 'str'),
    ('argument.executable_sha256', 'str'),
    ('argument.library_relative_path', 'str'),
    ('argument.library_path', 'str'),
    ('argument.library_directory', 'str'),
    ('argument.library_sha256', 'str'),
    ('argument.library_size_bytes', 'int'),
    ('argument.library_inode', 'int'),
    ('argument.extra', 'null'),
    ('argument.library_device.shape', 'str'),
    ('argument.library_device.mask', 'int'),
    ('argument.library_device.major', 'int'),
    ('argument.library_device.minor', 'int'),
    ('argument.mapped_library.shape', 'str'),
    ('argument.mapped_library.mask', 'int'),
    ('argument.mapped_library.path', 'str'),
    ('argument.mapped_library.inode', 'int'),
    ('argument.mapped_library.device.shape', 'str'),
    ('argument.mapped_library.device.mask', 'int'),
    ('argument.mapped_library.device.major', 'int'),
    ('argument.mapped_library.device.minor', 'int'),
    ('argument.loader_environment.shape', 'str'),
    ('argument.loader_environment.mask', 'int'),
    ('argument.loader_environment.LD_LIBRARY_PATH', 'str'),
    ('argument.loader_environment.LD_PRELOAD', 'str'),
)
_LOADER_FIELDS_C31_01 = (
    ('dirty.shape', 'str'),
    ('dirty.mask', 'int'),
    ('dirty.KEEP', 'str'),
    ('dirty.LD_LIBRARY_PATH', 'str'),
    ('dirty.LD_AUDIT', 'str'),
    ('dirty.LD_UNKNOWN', 'str'),
    ('dirty.PYTHONPATH', 'str'),
    ('dirty.PYTHONUNKNOWN', 'str'),
    ('local.mode', 'str'),
    ('local.error', 'null'),
    ('argument.shape', 'str'),
)
_LOADER_FIELDS_C31_02 = (
    ('dirty.shape', 'str'),
    ('dirty.mask', 'int'),
    ('dirty.KEEP', 'str'),
    ('dirty.LD_LIBRARY_PATH', 'str'),
    ('dirty.LD_AUDIT', 'str'),
    ('dirty.LD_UNKNOWN', 'str'),
    ('dirty.PYTHONPATH', 'str'),
    ('dirty.PYTHONUNKNOWN', 'str'),
    ('local.mode', 'str'),
    ('local.error', 'null'),
    ('argument.shape', 'str'),
    ('argument.mask', 'int'),
    ('argument.schema', 'str'),
    ('argument.tool_cache', 'str'),
    ('argument.executable_path', 'str'),
    ('argument.executable_sha256', 'str'),
    ('argument.library_relative_path', 'str'),
    ('argument.library_path', 'str'),
    ('argument.library_directory', 'str'),
    ('argument.library_sha256', 'str'),
    ('argument.library_size_bytes', 'int'),
    ('argument.library_inode', 'int'),
    ('argument.extra', 'null'),
    ('argument.library_device.shape', 'str'),
    ('argument.library_device.mask', 'int'),
    ('argument.library_device.major', 'int'),
    ('argument.library_device.minor', 'int'),
    ('argument.mapped_library.shape', 'str'),
    ('argument.mapped_library.mask', 'int'),
    ('argument.mapped_library.path', 'str'),
    ('argument.mapped_library.inode', 'int'),
    ('argument.mapped_library.device.shape', 'str'),
    ('argument.mapped_library.device.mask', 'int'),
    ('argument.mapped_library.device.major', 'int'),
    ('argument.mapped_library.device.minor', 'int'),
    ('argument.loader_environment.shape', 'str'),
    ('argument.loader_environment.mask', 'int'),
    ('argument.loader_environment.LD_LIBRARY_PATH', 'str'),
    ('argument.loader_environment.LD_PRELOAD', 'null'),
)
_LOADER_FIELDS_C31_03 = (
    ('dirty.shape', 'str'),
    ('dirty.mask', 'int'),
    ('dirty.KEEP', 'str'),
    ('dirty.LD_LIBRARY_PATH', 'str'),
    ('dirty.LD_AUDIT', 'str'),
    ('dirty.LD_UNKNOWN', 'str'),
    ('dirty.PYTHONPATH', 'str'),
    ('dirty.PYTHONUNKNOWN', 'str'),
    ('local.mode', 'str'),
    ('local.error', 'null'),
    ('argument.shape', 'str'),
    ('argument.mask', 'int'),
    ('argument.schema', 'str'),
    ('argument.tool_cache', 'null'),
    ('argument.executable_path', 'null'),
    ('argument.executable_sha256', 'str'),
    ('argument.library_relative_path', 'str'),
    ('argument.library_path', 'null'),
    ('argument.library_directory', 'null'),
    ('argument.library_sha256', 'str'),
    ('argument.library_size_bytes', 'int'),
    ('argument.library_inode', 'null'),
    ('argument.extra', 'null'),
    ('argument.library_device.shape', 'str'),
    ('argument.library_device.mask', 'null'),
    ('argument.library_device.major', 'null'),
    ('argument.library_device.minor', 'null'),
    ('argument.mapped_library.shape', 'str'),
    ('argument.mapped_library.mask', 'null'),
    ('argument.mapped_library.path', 'null'),
    ('argument.mapped_library.inode', 'null'),
    ('argument.mapped_library.device.shape', 'str'),
    ('argument.mapped_library.device.mask', 'null'),
    ('argument.mapped_library.device.major', 'null'),
    ('argument.mapped_library.device.minor', 'null'),
    ('argument.loader_environment.shape', 'str'),
    ('argument.loader_environment.mask', 'null'),
    ('argument.loader_environment.LD_LIBRARY_PATH', 'null'),
    ('argument.loader_environment.LD_PRELOAD', 'null'),
)
_LOADER_FIELDS_C31_06 = (
    ('dirty.shape', 'str'),
    ('dirty.mask', 'int'),
    ('dirty.KEEP', 'str'),
    ('dirty.LD_LIBRARY_PATH', 'str'),
    ('dirty.LD_AUDIT', 'str'),
    ('dirty.LD_UNKNOWN', 'str'),
    ('dirty.PYTHONPATH', 'str'),
    ('dirty.PYTHONUNKNOWN', 'str'),
    ('local.mode', 'str'),
    ('local.error', 'null'),
    ('argument.shape', 'str'),
    ('argument.mask', 'null'),
    ('argument.value', 'str'),
)
_LOADER_FIELDS_C31_07 = (
    ('dirty.shape', 'str'),
    ('dirty.mask', 'int'),
    ('dirty.KEEP', 'str'),
    ('dirty.LD_LIBRARY_PATH', 'str'),
    ('dirty.LD_AUDIT', 'str'),
    ('dirty.LD_UNKNOWN', 'str'),
    ('dirty.PYTHONPATH', 'str'),
    ('dirty.PYTHONUNKNOWN', 'str'),
    ('local.mode', 'str'),
    ('local.error', 'str'),
    ('argument.shape', 'str'),
    ('argument.mask', 'int'),
    ('argument.schema', 'str'),
    ('argument.tool_cache', 'str'),
    ('argument.executable_path', 'str'),
    ('argument.executable_sha256', 'str'),
    ('argument.library_relative_path', 'str'),
    ('argument.library_path', 'str'),
    ('argument.library_directory', 'str'),
    ('argument.library_sha256', 'str'),
    ('argument.library_size_bytes', 'int'),
    ('argument.library_inode', 'int'),
    ('argument.extra', 'null'),
    ('argument.library_device.shape', 'str'),
    ('argument.library_device.mask', 'int'),
    ('argument.library_device.major', 'int'),
    ('argument.library_device.minor', 'int'),
    ('argument.mapped_library.shape', 'str'),
    ('argument.mapped_library.mask', 'int'),
    ('argument.mapped_library.path', 'str'),
    ('argument.mapped_library.inode', 'int'),
    ('argument.mapped_library.device.shape', 'str'),
    ('argument.mapped_library.device.mask', 'int'),
    ('argument.mapped_library.device.major', 'int'),
    ('argument.mapped_library.device.minor', 'int'),
    ('argument.loader_environment.shape', 'str'),
    ('argument.loader_environment.mask', 'int'),
    ('argument.loader_environment.LD_LIBRARY_PATH', 'str'),
    ('argument.loader_environment.LD_PRELOAD', 'null'),
)
_LOADER_FIELDS_C32_01 = (
    ('implementation', 'str'),
    ('version', 'str'),
    ('platform', 'str'),
    ('flags.dont_write_bytecode', 'int'),
    ('flags.no_user_site', 'int'),
    ('flags.ignore_environment', 'int'),
    ('flags.isolated', 'int'),
    ('flags.optimize', 'int'),
    ('flags.no_site', 'int'),
    ('gc.enabled', 'bool'),
    ('gc.threshold.container', 'str'),
    ('gc.threshold.0', 'int'),
    ('gc.threshold.1', 'int'),
    ('gc.threshold.2', 'int'),
    ('timer.container', 'str'),
    ('timer.0', 'int'),
    ('timer.1', 'int'),
    ('limits.container', 'str'),
    ('limits.0', 'int'),
    ('limits.1', 'int'),
    ('registered.sha256', 'str'),
    ('registered.size', 'int'),
    ('loader.mode', 'str'),
    ('loader.error', 'null'),
    ('environment.GITHUB_ACTIONS', 'str'),
    ('environment.GITHUB_REPOSITORY', 'str'),
    ('environment.RUNNER_NAME', 'str'),
    ('environment.PYTHONUNEXPECTED', 'null'),
    ('child', 'bool'),
    ('implementation.side_effect', 'null'),
    ('version.side_effect', 'null'),
    ('gc.enabled.side_effect', 'null'),
    ('gc.threshold.side_effect', 'null'),
    ('timer.side_effect', 'null'),
    ('limits.side_effect', 'null'),
    ('loader.shape', 'str'),
    ('loader.mask', 'int'),
    ('loader.schema', 'str'),
    ('loader.tool_cache', 'str'),
    ('loader.executable_path', 'str'),
    ('loader.executable_sha256', 'str'),
    ('loader.library_relative_path', 'str'),
    ('loader.library_path', 'str'),
    ('loader.library_directory', 'str'),
    ('loader.library_sha256', 'str'),
    ('loader.library_size_bytes', 'int'),
    ('loader.library_inode', 'int'),
    ('loader.extra', 'null'),
    ('loader.library_device.shape', 'str'),
    ('loader.library_device.mask', 'int'),
    ('loader.library_device.major', 'int'),
    ('loader.library_device.minor', 'int'),
    ('loader.mapped_library.shape', 'str'),
    ('loader.mapped_library.mask', 'int'),
    ('loader.mapped_library.path', 'str'),
    ('loader.mapped_library.inode', 'int'),
    ('loader.mapped_library.device.shape', 'str'),
    ('loader.mapped_library.device.mask', 'int'),
    ('loader.mapped_library.device.major', 'int'),
    ('loader.mapped_library.device.minor', 'int'),
    ('loader.loader_environment.shape', 'str'),
    ('loader.loader_environment.mask', 'int'),
    ('loader.loader_environment.LD_LIBRARY_PATH', 'str'),
    ('loader.loader_environment.LD_PRELOAD', 'null'),
)
_LOADER_FIELDS_C32_02 = (
    ('implementation', 'str'),
    ('version', 'str'),
    ('platform', 'str'),
    ('flags.dont_write_bytecode', 'int'),
    ('flags.no_user_site', 'int'),
    ('flags.ignore_environment', 'int'),
    ('flags.isolated', 'int'),
    ('flags.optimize', 'int'),
    ('flags.no_site', 'int'),
    ('gc.enabled', 'bool'),
    ('gc.threshold.container', 'str'),
    ('gc.threshold.0', 'int'),
    ('gc.threshold.1', 'int'),
    ('gc.threshold.2', 'int'),
    ('timer.container', 'str'),
    ('timer.0', 'int'),
    ('timer.1', 'int'),
    ('limits.container', 'str'),
    ('limits.0', 'int'),
    ('limits.1', 'int'),
    ('registered.sha256', 'str'),
    ('registered.size', 'int'),
    ('loader.mode', 'str'),
    ('loader.error', 'str'),
    ('environment.GITHUB_ACTIONS', 'str'),
    ('environment.GITHUB_REPOSITORY', 'str'),
    ('environment.RUNNER_NAME', 'str'),
    ('environment.PYTHONUNEXPECTED', 'null'),
    ('child', 'bool'),
    ('implementation.side_effect', 'null'),
    ('version.side_effect', 'null'),
    ('gc.enabled.side_effect', 'null'),
    ('gc.threshold.side_effect', 'null'),
    ('timer.side_effect', 'null'),
    ('limits.side_effect', 'null'),
    ('loader.shape', 'str'),
    ('loader.mask', 'int'),
    ('loader.schema', 'str'),
    ('loader.tool_cache', 'str'),
    ('loader.executable_path', 'str'),
    ('loader.executable_sha256', 'str'),
    ('loader.library_relative_path', 'str'),
    ('loader.library_path', 'str'),
    ('loader.library_directory', 'str'),
    ('loader.library_sha256', 'str'),
    ('loader.library_size_bytes', 'int'),
    ('loader.library_inode', 'int'),
    ('loader.extra', 'null'),
    ('loader.library_device.shape', 'str'),
    ('loader.library_device.mask', 'int'),
    ('loader.library_device.major', 'int'),
    ('loader.library_device.minor', 'int'),
    ('loader.mapped_library.shape', 'str'),
    ('loader.mapped_library.mask', 'int'),
    ('loader.mapped_library.path', 'str'),
    ('loader.mapped_library.inode', 'int'),
    ('loader.mapped_library.device.shape', 'str'),
    ('loader.mapped_library.device.mask', 'int'),
    ('loader.mapped_library.device.major', 'int'),
    ('loader.mapped_library.device.minor', 'int'),
    ('loader.loader_environment.shape', 'str'),
    ('loader.loader_environment.mask', 'int'),
    ('loader.loader_environment.LD_LIBRARY_PATH', 'str'),
    ('loader.loader_environment.LD_PRELOAD', 'null'),
)
_LOADER_FIELDS_C32_03 = (
    ('implementation', 'str'),
    ('version', 'str'),
    ('platform', 'str'),
    ('flags.dont_write_bytecode', 'int'),
    ('flags.no_user_site', 'int'),
    ('flags.ignore_environment', 'int'),
    ('flags.isolated', 'int'),
    ('flags.optimize', 'int'),
    ('flags.no_site', 'int'),
    ('gc.enabled', 'bool'),
    ('gc.threshold.container', 'str'),
    ('gc.threshold.0', 'int'),
    ('gc.threshold.1', 'int'),
    ('gc.threshold.2', 'int'),
    ('timer.container', 'str'),
    ('timer.0', 'int'),
    ('timer.1', 'int'),
    ('limits.container', 'str'),
    ('limits.0', 'int'),
    ('limits.1', 'int'),
    ('registered.sha256', 'str'),
    ('registered.size', 'int'),
    ('loader.mode', 'str'),
    ('loader.error', 'null'),
    ('environment.GITHUB_ACTIONS', 'str'),
    ('environment.GITHUB_REPOSITORY', 'str'),
    ('environment.RUNNER_NAME', 'str'),
    ('environment.PYTHONUNEXPECTED', 'str'),
    ('child', 'bool'),
    ('implementation.side_effect', 'null'),
    ('version.side_effect', 'null'),
    ('gc.enabled.side_effect', 'null'),
    ('gc.threshold.side_effect', 'null'),
    ('timer.side_effect', 'null'),
    ('limits.side_effect', 'null'),
    ('loader.shape', 'str'),
    ('loader.mask', 'int'),
    ('loader.schema', 'str'),
    ('loader.tool_cache', 'str'),
    ('loader.executable_path', 'str'),
    ('loader.executable_sha256', 'str'),
    ('loader.library_relative_path', 'str'),
    ('loader.library_path', 'str'),
    ('loader.library_directory', 'str'),
    ('loader.library_sha256', 'str'),
    ('loader.library_size_bytes', 'int'),
    ('loader.library_inode', 'int'),
    ('loader.extra', 'null'),
    ('loader.library_device.shape', 'str'),
    ('loader.library_device.mask', 'int'),
    ('loader.library_device.major', 'int'),
    ('loader.library_device.minor', 'int'),
    ('loader.mapped_library.shape', 'str'),
    ('loader.mapped_library.mask', 'int'),
    ('loader.mapped_library.path', 'str'),
    ('loader.mapped_library.inode', 'int'),
    ('loader.mapped_library.device.shape', 'str'),
    ('loader.mapped_library.device.mask', 'int'),
    ('loader.mapped_library.device.major', 'int'),
    ('loader.mapped_library.device.minor', 'int'),
    ('loader.loader_environment.shape', 'str'),
    ('loader.loader_environment.mask', 'int'),
    ('loader.loader_environment.LD_LIBRARY_PATH', 'str'),
    ('loader.loader_environment.LD_PRELOAD', 'null'),
)

LOADER_CONTEXT_SCHEMAS = {
    'c25-01': _LOADER_FIELDS_C25_01,
    'c25-02': _LOADER_FIELDS_C25_01,
    'c25-03': _LOADER_FIELDS_C25_01,
    'c25-04': _LOADER_FIELDS_C25_01,
    'c25-05': _LOADER_FIELDS_C25_01,
    'c25-06': _LOADER_FIELDS_C25_01,
    'c25-07': _LOADER_FIELDS_C25_01,
    'c26-01': _LOADER_FIELDS_C26_01,
    'c26-02': _LOADER_FIELDS_C26_02,
    'c26-03': _LOADER_FIELDS_C26_03,
    'c26-04': _LOADER_FIELDS_C26_04,
    'c26-05': _LOADER_FIELDS_C26_04,
    'c26-06': _LOADER_FIELDS_C26_06,
    'c27-01': _LOADER_FIELDS_C27_01,
    'c27-02': _LOADER_FIELDS_C27_01,
    'c27-03': _LOADER_FIELDS_C27_01,
    'c27-04': _LOADER_FIELDS_C27_01,
    'c27-05': _LOADER_FIELDS_C27_01,
    'c27-06': _LOADER_FIELDS_C27_01,
    'c27-07': _LOADER_FIELDS_C27_01,
    'c27-08': _LOADER_FIELDS_C27_01,
    'c27-09': _LOADER_FIELDS_C27_09,
    'c28-01': _LOADER_FIELDS_C28_01,
    'c28-02': _LOADER_FIELDS_C28_01,
    'c28-03': _LOADER_FIELDS_C28_01,
    'c28-04': _LOADER_FIELDS_C28_01,
    'c28-05': _LOADER_FIELDS_C28_05,
    'c28-06': _LOADER_FIELDS_C28_01,
    'c28-07': _LOADER_FIELDS_C28_01,
    'c29-01': _LOADER_FIELDS_C29_01,
    'c29-02': _LOADER_FIELDS_C29_02,
    'c29-03': _LOADER_FIELDS_C29_03,
    'c29-04': _LOADER_FIELDS_C29_04,
    'c29-05': _LOADER_FIELDS_C29_02,
    'c29-06': _LOADER_FIELDS_C29_06,
    'c29-07': _LOADER_FIELDS_C29_02,
    'c29-08': _LOADER_FIELDS_C29_02,
    'c29-09': _LOADER_FIELDS_C29_02,
    'c29-10': _LOADER_FIELDS_C29_02,
    'c29-11': _LOADER_FIELDS_C29_02,
    'c30-01': _LOADER_FIELDS_C30_01,
    'c30-02': _LOADER_FIELDS_C30_02,
    'c30-03': _LOADER_FIELDS_C29_01,
    'c30-04': _LOADER_FIELDS_C29_01,
    'c30-05': _LOADER_FIELDS_C29_01,
    'c30-06': _LOADER_FIELDS_C29_01,
    'c30-07': _LOADER_FIELDS_C29_01,
    'c30-08': _LOADER_FIELDS_C29_01,
    'c30-09': _LOADER_FIELDS_C29_01,
    'c30-10': _LOADER_FIELDS_C30_10,
    'c31-01': _LOADER_FIELDS_C31_01,
    'c31-02': _LOADER_FIELDS_C31_02,
    'c31-03': _LOADER_FIELDS_C31_03,
    'c31-04': _LOADER_FIELDS_C31_02,
    'c31-05': _LOADER_FIELDS_C31_03,
    'c31-06': _LOADER_FIELDS_C31_06,
    'c31-07': _LOADER_FIELDS_C31_07,
    'c32-01': _LOADER_FIELDS_C32_01,
    'c32-02': _LOADER_FIELDS_C32_02,
    'c32-03': _LOADER_FIELDS_C32_03,
}
_LOADER_DYNAMIC_C25_01 = ()
_LOADER_DYNAMIC_C26_02 = (
    'initial.dev',
    'initial.ino',
    'initial.mode',
    'initial.size',
    'initial.mtime_ns',
    'initial.ctime_ns',
    'initial.nlink',
)
_LOADER_DYNAMIC_C26_03 = (
    'initial.dev',
    'initial.ino',
    'initial.mode',
    'initial.size',
    'initial.mtime_ns',
    'initial.ctime_ns',
    'initial.nlink',
    'observed.dev',
    'observed.ino',
    'observed.mode',
    'observed.size',
    'observed.mtime_ns',
    'observed.ctime_ns',
    'observed.nlink',
    'returned.dev',
    'returned.ino',
    'returned.mode',
    'returned.size',
    'returned.mtime_ns',
    'returned.ctime_ns',
    'returned.nlink',
)
_LOADER_DYNAMIC_C26_04 = (
    'initial.dev',
    'initial.ino',
)
_LOADER_DYNAMIC_C26_06 = (
    'executable.device.major',
    'executable.device.minor',
    'executable.inode',
    'executable._stat.dev',
    'executable._stat.ino',
    'executable._stat.mode',
    'executable._stat.size',
    'executable._stat.mtime_ns',
    'executable._stat.ctime_ns',
    'executable._stat.nlink',
    'library.device.major',
    'library.device.minor',
    'library.inode',
    'library._stat.dev',
    'library._stat.ino',
    'library._stat.mode',
    'library._stat.size',
    'library._stat.mtime_ns',
    'library._stat.ctime_ns',
    'library._stat.nlink',
    'changed.device.major',
    'changed.device.minor',
    'changed.inode',
    'changed._stat.dev',
    'changed._stat.ino',
    'changed._stat.mode',
    'changed._stat.size',
    'changed._stat.mtime_ns',
    'changed._stat.ctime_ns',
    'changed._stat.nlink',
)
_LOADER_DYNAMIC_C27_01 = (
    'device.major',
    'device.minor',
    'inode',
)
_LOADER_DYNAMIC_C27_02 = (
    'maps.0',
    'device.major',
    'device.minor',
    'inode',
)
_LOADER_DYNAMIC_C27_09 = (
    'maps.0',
    'maps.1',
    'device.major',
    'device.minor',
    'inode',
)
_LOADER_DYNAMIC_C29_01 = (
    'argument.library_inode',
    'argument.library_device.major',
    'argument.library_device.minor',
    'argument.mapped_library.inode',
    'argument.mapped_library.device.major',
    'argument.mapped_library.device.minor',
)
_LOADER_DYNAMIC_C30_02 = (
    'argument.library_inode',
    'argument.library_device.major',
    'argument.library_device.minor',
)
_LOADER_DYNAMIC_C32_01 = (
    'loader.library_inode',
    'loader.library_device.major',
    'loader.library_device.minor',
    'loader.mapped_library.inode',
    'loader.mapped_library.device.major',
    'loader.mapped_library.device.minor',
)

LOADER_DYNAMIC_FIELDS = {
    'c25-01': _LOADER_DYNAMIC_C25_01,
    'c25-02': _LOADER_DYNAMIC_C25_01,
    'c25-03': _LOADER_DYNAMIC_C25_01,
    'c25-04': _LOADER_DYNAMIC_C25_01,
    'c25-05': _LOADER_DYNAMIC_C25_01,
    'c25-06': _LOADER_DYNAMIC_C25_01,
    'c25-07': _LOADER_DYNAMIC_C25_01,
    'c26-01': _LOADER_DYNAMIC_C25_01,
    'c26-02': _LOADER_DYNAMIC_C26_02,
    'c26-03': _LOADER_DYNAMIC_C26_03,
    'c26-04': _LOADER_DYNAMIC_C26_04,
    'c26-05': _LOADER_DYNAMIC_C26_04,
    'c26-06': _LOADER_DYNAMIC_C26_06,
    'c27-01': _LOADER_DYNAMIC_C27_01,
    'c27-02': _LOADER_DYNAMIC_C27_02,
    'c27-03': _LOADER_DYNAMIC_C27_02,
    'c27-04': _LOADER_DYNAMIC_C27_02,
    'c27-05': _LOADER_DYNAMIC_C27_02,
    'c27-06': _LOADER_DYNAMIC_C27_02,
    'c27-07': _LOADER_DYNAMIC_C27_02,
    'c27-08': _LOADER_DYNAMIC_C27_02,
    'c27-09': _LOADER_DYNAMIC_C27_09,
    'c28-01': _LOADER_DYNAMIC_C25_01,
    'c28-02': _LOADER_DYNAMIC_C25_01,
    'c28-03': _LOADER_DYNAMIC_C25_01,
    'c28-04': _LOADER_DYNAMIC_C25_01,
    'c28-05': _LOADER_DYNAMIC_C25_01,
    'c28-06': _LOADER_DYNAMIC_C25_01,
    'c28-07': _LOADER_DYNAMIC_C25_01,
    'c29-01': _LOADER_DYNAMIC_C29_01,
    'c29-02': _LOADER_DYNAMIC_C25_01,
    'c29-03': _LOADER_DYNAMIC_C25_01,
    'c29-04': _LOADER_DYNAMIC_C25_01,
    'c29-05': _LOADER_DYNAMIC_C25_01,
    'c29-06': _LOADER_DYNAMIC_C25_01,
    'c29-07': _LOADER_DYNAMIC_C25_01,
    'c29-08': _LOADER_DYNAMIC_C25_01,
    'c29-09': _LOADER_DYNAMIC_C25_01,
    'c29-10': _LOADER_DYNAMIC_C25_01,
    'c29-11': _LOADER_DYNAMIC_C25_01,
    'c30-01': _LOADER_DYNAMIC_C29_01,
    'c30-02': _LOADER_DYNAMIC_C30_02,
    'c30-03': _LOADER_DYNAMIC_C29_01,
    'c30-04': _LOADER_DYNAMIC_C29_01,
    'c30-05': _LOADER_DYNAMIC_C29_01,
    'c30-06': _LOADER_DYNAMIC_C29_01,
    'c30-07': _LOADER_DYNAMIC_C29_01,
    'c30-08': _LOADER_DYNAMIC_C29_01,
    'c30-09': _LOADER_DYNAMIC_C29_01,
    'c30-10': _LOADER_DYNAMIC_C29_01,
    'c31-01': _LOADER_DYNAMIC_C25_01,
    'c31-02': _LOADER_DYNAMIC_C29_01,
    'c31-03': _LOADER_DYNAMIC_C25_01,
    'c31-04': _LOADER_DYNAMIC_C29_01,
    'c31-05': _LOADER_DYNAMIC_C25_01,
    'c31-06': _LOADER_DYNAMIC_C25_01,
    'c31-07': _LOADER_DYNAMIC_C29_01,
    'c32-01': _LOADER_DYNAMIC_C32_01,
    'c32-02': _LOADER_DYNAMIC_C32_01,
    'c32-03': _LOADER_DYNAMIC_C32_01,
}


class BatchStopped(BaseException):
    def __init__(self, reason, status='execution_incomplete'):
        super().__init__(reason)
        self.reason = reason
        self.status = status


FAILURE_PRIORITY = {'execution_blocked': 0, 'execution_incomplete': 1,
                    'resource_incomplete': 2, 'integrity_invalid': 3}
FAILURE_SEQUENCE = 0


def typed_failure_status(error):
    if isinstance(error, BatchStopped):
        return error.status
    if isinstance(error, (MemoryError, RecursionError, subprocess.TimeoutExpired)):
        return 'resource_incomplete'
    # Only exact classes from the already pinned, lazily loaded modules count.
    # Arbitrary similarly named exceptions or free-form text do not classify.
    admission = sys.modules.get('worker38.admission')
    admission_error = getattr(admission, 'AdmissionError', None)
    if isinstance(admission_error, type) and isinstance(error, admission_error):
        status = error.classification
        return 'execution_incomplete' if status == 'evidence_incomplete' else (
            status if type(status) is str and status in FAILURE_PRIORITY else 'integrity_invalid')
    common = sys.modules.get('worker38.common')
    if common is not None:
        resource_error = getattr(common, 'ResourceExceeded', None)
        integrity_error = getattr(common, 'IntegrityError', None)
        if isinstance(resource_error, type) and isinstance(error, resource_error):
            return 'resource_incomplete'
        if isinstance(integrity_error, type) and isinstance(error, integrity_error):
            return 'integrity_invalid'
    return 'execution_incomplete'


def retain_failure(state, error, phase, code=None):
    """Fixed bounded typed evidence, strongest cause wins; equal keeps first."""
    global FAILURE_SEQUENCE
    FAILURE_SEQUENCE += 1
    status = typed_failure_status(error)
    record = {'error_type': type(error).__name__[:64], 'status': status,
              'code': (code or (error.reason if isinstance(error, BatchStopped) else
                       'native_unexpected_exception'))[:160], 'phase': phase,
              'observed_order': FAILURE_SEQUENCE}
    return retain_failure_record(state, record)


def retain_failure_record(state, record):
    status = record['status']
    if state is None:
        return {**record, 'primary_failure': record, 'secondary_failures': [],
                'additional_failure_records_omitted': 0}
    old = state['primary_failure']
    if (FAILURE_PRIORITY[status] > FAILURE_PRIORITY[old['status']] or
            FAILURE_PRIORITY[status] == FAILURE_PRIORITY[old['status']] and
            record['observed_order'] < old['observed_order']):
        state.update(record)
        state['primary_failure'] = record
        record = old
    if len(state['secondary_failures']) < 12:
        state['secondary_failures'].append(record)
        state['secondary_failures'].sort(key=lambda item: item['observed_order'])
    else:
        state['additional_failure_records_omitted'] += 1
    return state


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def sync_directory(path):
    fd = OS_OPEN(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        FSYNC(fd)
    finally:
        OS_CLOSE(fd)


def runtime_isolation_snapshot():
    return (GET_PROFILE(), GET_TRACE(), GC_ENABLED(), GC_THRESHOLDS(), THREAD_COUNT(),
            tuple(GET_TIMER(item) for item in (signal.ITIMER_REAL, signal.ITIMER_VIRTUAL, signal.ITIMER_PROF)),
            GET_HANDLER(signal.SIGALRM), GET_HANDLER(signal.SIGUSR1), GETRLIMIT(resource.RLIMIT_AS))


def verify_project_namespace(tree, deadline):
    policy = {'recursive': True, 'follow_symlinks': False, 'symlinks_allowed': False,
              'special_nodes_allowed': False, 'non_ascii_names_allowed': False,
              'candidate_file_suffixes': ['.py', '.pyc', '.so'],
              'directory_rule': 'name.isidentifier() (includes __pycache__)'}
    root = Path(tree['root'])
    if (tree['schema'] != 'worker38-project-import-namespace-v2' or
            tree['exists'] is not True or tree['root_type'] != 'directory' or
            tree['policy'] != policy or not root.is_absolute()):
        raise BatchStopped('native project namespace schema differs', 'execution_blocked')
    ancestors = []
    for path in [*reversed(root.parents), root]:
        if not stat.S_ISDIR(LSTAT(path).st_mode):
            raise BatchStopped('native project root ancestry differs', 'execution_blocked')
        ancestors.append([str(path), 'directory', None])
    entries = []
    def visit(path, prefix=''):
        if NOW() >= deadline:
            raise BatchStopped('native cooperative cutoff expired during namespace check', 'resource_incomplete')
        for name in sorted(LISTDIR(path)):
            if not name.isascii():
                raise BatchStopped('native project entry domain differs', 'execution_blocked')
            child = path / name
            info = LSTAT(child)
            is_dir, is_link = stat.S_ISDIR(info.st_mode), stat.S_ISLNK(info.st_mode)
            if not (name.endswith(('.py', '.pyc', '.so')) or
                    name.isidentifier() and (is_dir or is_link)):
                continue
            kind = ('symlink' if is_link else 'directory' if is_dir else
                    'file' if stat.S_ISREG(info.st_mode) else 'special')
            relative = prefix + name
            entries.append([relative, kind, READLINK(child) if is_link else None])
            if kind in ('symlink', 'special'):
                raise BatchStopped('native project candidate alias or special node', 'execution_blocked')
            if is_dir and name.isidentifier():
                visit(child, relative + '/')
    visit(root)
    entries.sort(key=lambda row: row[0])
    if (ancestors != tree['ancestor_entries'] or entries != tree['entries'] or
            sha(canonical(entries)) != tree['entries_sha256']):
        raise BatchStopped('native project namespace changed', 'execution_blocked')


def verify_native_environment(binding, expected_environment, deadline):
    """Recheck the one frozen native metadata manifest; never launch a probe."""
    path = ROOT / binding['path']
    size, digest = hash_file(path)
    if size != binding['size_bytes'] or digest != binding['sha256']:
        raise BatchStopped('native environment manifest changed', 'execution_blocked')
    actual = dict(os.environ)
    for name in ('WORKER38_FIXED_MAP_SHA256', 'WORKER38_NATIVE_DEADLINE_CS'):
        actual.pop(name, None)
    if (actual != expected_environment or not sys.dont_write_bytecode or
            not sys.flags.safe_path or sys.pycache_prefix is not None):
        raise BatchStopped('native positive environment differs', 'execution_blocked')
    with OPEN(path, 'rb') as stream:
        metadata = json.load(stream)
    checked = set()
    def check_file(record):
        name = record['path']
        if name in checked:
            return
        if NOW() >= deadline:
            raise BatchStopped('original native deadline expired during metadata checks', 'resource_incomplete')
        try:
            info = LSTAT(name)
        except FileNotFoundError:
            if record.get('exists') is False:
                checked.add(name); return
            raise
        if record.get('exists') is False:
            raise BatchStopped('native absent-path binding changed', 'execution_blocked')
        if record.get('type') == 'symlink':
            if not stat.S_ISLNK(info.st_mode) or READLINK(name) != record['target']:
                raise BatchStopped('native symlink binding changed', 'execution_blocked')
            if 'resolved' in record and str(Path(name).resolve()) != record['resolved']:
                raise BatchStopped('native resolved target changed', 'execution_blocked')
        elif record.get('type') == 'file' and not stat.S_ISREG(info.st_mode):
            raise BatchStopped('native regular-file binding changed', 'execution_blocked')
        if 'mode' in record and stat.S_IMODE(info.st_mode) != record['mode']:
            raise BatchStopped('native mode binding changed', 'execution_blocked')
        if 'mtime_ns' in record and Path(name).stat().st_mtime_ns != record['mtime_ns']:
            raise BatchStopped('native cache/source timestamp binding changed', 'execution_blocked')
        if 'sha256' in record:
            got_size, got_hash = hash_file(name)
            if got_size != record['size_bytes'] or got_hash != record['sha256']:
                raise BatchStopped('native file bytes changed', 'execution_blocked')
        checked.add(name)
    def walk(value):
        if isinstance(value, dict):
            if 'path' in value and 'exists' in value:
                check_file(value)
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
    walk(metadata)
    for key in ('stdlib_complete_tree', 'SSL_default_certificate_tree'):
        tree = metadata[key]
        actual_names = []
        def names_below(directory, prefix=''):
            for leaf in sorted(LISTDIR(directory)):
                relative = prefix + leaf
                child = str(Path(directory) / leaf)
                if stat.S_ISDIR(LSTAT(child).st_mode):
                    names_below(child, relative + '/')
                else:
                    actual_names.append(relative)
        names_below(tree['root'])
        if sorted(actual_names) != sorted(row[0] for row in tree['entries']):
            raise BatchStopped('native library namespace changed', 'execution_blocked')
        for relative, kind, length, pin, mtime, target, resolved in tree['entries']:
            name = str(Path(tree['root']) / relative)
            check_file({'path': name, 'exists': True, 'type': kind, 'size_bytes': length,
                        'sha256': pin, 'mtime_ns': mtime,
                        **({'target': target, 'resolved': resolved} if kind == 'symlink' else {})})
    for tree in metadata['site']['global_site_directory_namespaces']:
        if tree['exists'] is False:
            try:
                LSTAT(tree['root'])
            except FileNotFoundError:
                continue
            raise BatchStopped('native absent site directory appeared', 'execution_blocked')
        if tree['exists'] is not True or not stat.S_ISDIR(LSTAT(tree['root']).st_mode):
            raise BatchStopped('native site directory binding differs', 'execution_blocked')
        names = sorted(LISTDIR(tree['root']))
        if names != [row[0] for row in tree['entries']]:
            raise BatchStopped('native site namespace changed', 'execution_blocked')
    namespaces = metadata['project_import_roots']
    if [tree['root'] for tree in namespaces] != [str(ROOT / name) for name in ('evidence-design', 'tests', 'scripts')]:
        raise BatchStopped('native project namespace roots differ', 'execution_blocked')
    for tree in namespaces:
        verify_project_namespace(tree, deadline)
    return len(checked)


def hash_file(path, durable=False):
    total = 0
    digest = hashlib.sha256()
    with OPEN(path, 'rb') as stream:
        while block := stream.read(65536):
            total += len(block)
            digest.update(block)
        if durable:
            FSYNC(stream.fileno())
    return total, digest.hexdigest()


def inventory(root, durable=False):
    """No-follow observations of the retained finite scratch tree."""
    root = os.fspath(root)
    rows = []
    def visit(directory, prefix=''):
        for name in sorted(LISTDIR(directory)):
            path = directory + '/' + name
            relative = prefix + name
            if len(path.encode('ascii')) > 512:
                raise BatchStopped('native path outside frozen scalar domain')
            info = LSTAT(path)
            if stat.S_ISDIR(info.st_mode):
                visit(path, relative + '/')
            elif stat.S_ISREG(info.st_mode):
                size, digest = hash_file(path, durable=durable)
                rows.append({'path': relative, 'type': 'file', 'size_bytes': size,
                             'sha256': digest, 'mode': stat.S_IMODE(info.st_mode),
                             'device': info.st_dev, 'inode': info.st_ino, 'nlink': info.st_nlink})
            elif stat.S_ISLNK(info.st_mode):
                target = os.fsencode(READLINK(path))
                rows.append({'path': relative, 'type': 'symlink', 'size_bytes': len(target),
                             'sha256': sha(target), 'mode': stat.S_IMODE(info.st_mode),
                             'device': info.st_dev, 'inode': info.st_ino, 'nlink': info.st_nlink})
            else:
                rows.append({'path': relative, 'type': 'special', 'size_bytes': 0,
                             'mode': stat.S_IMODE(info.st_mode),
                             'device': info.st_dev, 'inode': info.st_ino, 'nlink': info.st_nlink})
        if durable:
            sync_directory(directory)
    visit(root)
    return rows


class DenyScientificImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('bandido_alcatraz', 'worker36', 'scripts.worker36')) or fullname in (
                'benchmark_worker35_synthetic', 'worker35_resources',
                'run_quota_reserve_closure_development', 'worker31_geometry'):
            raise BatchStopped('historical scientific import outside fixed literal preparation: ' + fullname)
        return None


def deny_network(*args, **kwargs):
    raise BatchStopped('live network outside fixed literal preparation')


class LogStream(io.TextIOBase):
    def __init__(self, path):
        self.stream = OPEN(path, 'xb', buffering=0)
        self.size = 0
        self.case_started = 0
        self.case_limit = 0
        self.overflow = False
        self.write_failure = False
        self.size_complete = True
        self.failure = None
    def writable(self):
        return True
    @property
    def buffer(self):
        return self
    def write(self, value):
        if self.write_failure:
            raise BatchStopped('native log capture already failed')
        raw = value if isinstance(value, bytes) else value.encode('utf-8', errors='backslashreplace')
        remaining = min(LOG_CAP - self.size, self.case_limit - (self.size - self.case_started))
        if len(raw) > remaining:
            self.overflow = True
            self.failure = retain_failure(self.failure,
                BatchStopped('native stdout/stderr allowance exhausted', 'resource_incomplete'), 'log_write')
            if remaining:
                self._write_once(raw[:remaining])
            raise BatchStopped('native stdout/stderr allowance exhausted; prefix retained', 'resource_incomplete')
        self._write_once(raw)
        return len(value)
    def _write_once(self, raw):
        try:
            count = self.stream.write(raw)
        except BaseException as error:
            self.write_failure = True
            self.size_complete = False
            self.failure = retain_failure(self.failure, error, 'log_write')
            # A failed unbuffered write may leave a prefix. This one bounded
            # size observation never authorizes another write or loses cause.
            try:
                observed = FSTAT(self.stream.fileno()).st_size
                if self.size <= observed <= self.size + len(raw):
                    self.size = observed
                    self.size_complete = True
            except BaseException as observation_error:
                self.failure = retain_failure(self.failure, observation_error, 'log_size_observation')
            raise
        if type(count) is not int or not 0 <= count <= len(raw):
            self.write_failure = True
            self.size_complete = False
            raise BatchStopped('native log write count is unconfirmed')
        self.size += count
        if count != len(raw):
            self.write_failure = True
            raise BatchStopped('native log short write; actual prefix retained')
    def flush(self):
        self.stream.flush()
    def durable(self):
        self.flush(); FSYNC(self.stream.fileno())


class Capture:
    def __init__(self, plan, started, deadline, boottime_deadline_ns):
        self.plan = plan
        self.started = started
        self.deadline = deadline
        self.boottime_deadline_ns = boottime_deadline_ns
        self.current = None
        self.current_row = None
        self.case_root = None
        self.temp_count = 0
        self.roots = []
        self.hooks = []
        self.output_files = {}
        self.input_files = {}
        self.records_bytes = 0
        self.method_results = []
        self.observations = []
        self.stopped = None
        self.settled_prefix_bytes = 0
        self.active_prefix_reservation = 0
        self.active_log_reservation = 0
        self.case_record_bytes = 0
        self.global_record_bytes = 0
        self.global_record_attempts = set()
        self.collect_attempted = False
        self.inventory_index = []
        self.started_selectors = []
        self.log = None
        self.failure = None
        self.capture_failed = False
        self.version_identities = []
        self.version_attempted_slots = set()
        self.input_witnesses = []
        self.input_attempted_slots = set()
        self.loader_contexts = []
        self.loader_attempted_slots = set()
        self.loader_anchor_history = {}
        self.transport_inputs = []
        self.transport_attempted_slots = set()

    def fail(self, error, phase, code=None):
        # Finite known helper handoffs and real exception context only. No
        # traceback-text classification or arbitrary callback discovery.
        global FAILURE_SEQUENCE
        seen = set()
        is_admission = bool(type(self.current) is str and type(self.current_row) is dict and
            self.current_row.get('selector') == self.current and
            type(self.current_row.get('literal_case_id')) is str and
            self.current_row['literal_case_id'].startswith('A'))
        admission_type = getattr(sys.modules.get('worker38.admission'), 'AdmissionError', None)
        test_module = sys.modules.get('test_worker38_bootstrap_integration')
        table = getattr(test_module, 'A_ACCEPTANCE', {})
        expected = table.get(self.current.rsplit('.', 1)[-1]) if is_admission else None

        def invalid_handoff():
            self.failure = retain_failure(self.failure,
                BatchStopped('native typed failure handoff differs', 'integrity_invalid'), 'failure_handoff')

        def visit(caught, location, local_code=None):
            global FAILURE_SEQUENCE
            if caught is None or id(caught) in seen:
                return
            if not isinstance(caught, BaseException):
                invalid_handoff(); return
            if len(seen) >= 32:
                self.failure = retain_failure(self.failure,
                    BatchStopped('native exception graph bound exhausted', 'resource_incomplete'), 'failure_handoff')
                self.failure['exception_graph_incomplete'] = True
                return
            seen.add(id(caught))
            marked = getattr(caught, 'worker38_expected_admission_rejection', False)
            intended = (is_admission and marked is True and isinstance(admission_type, type) and
                        type(caught) is admission_type and expected is not None and expected[0] is not None and
                        (caught.code, caught.classification) == expected[:2])
            if marked and not intended:
                invalid_handoff()
            cleanup = getattr(caught, 'worker38_native_cleanup_exceptions', ())
            if type(cleanup) is not tuple or len(cleanup) > 3:
                invalid_handoff(); cleanup = ()
            retention_error = (getattr(caught, 'worker38_prefix_retention_exception', None)
                               if is_admission else None)
            # Re-raising the saved primary while handling cleanup can form a
            # context cycle. Explicit later causes remain after that primary.
            later = {id(item) for item in cleanup}
            if retention_error is not None:
                later.add(id(retention_error))
            # A positively identified deliberate rejection and its internal
            # parser context are expected test behavior. Unexpected attached
            # report/cleanup causes remain eligible below.
            if not intended:
                if id(caught.__context__) not in later:
                    visit(caught.__context__, 'exception_context')
                if id(caught.__cause__) not in later:
                    visit(caught.__cause__, 'exception_cause')
            if is_admission:
                records = getattr(caught, 'worker38_admission_failure_records', ())
                if type(records) is not tuple or len(records) > 13:
                    invalid_handoff()
                else:
                    for record in records:
                        required = {'classification', 'code', 'phase', 'error_type'}
                        if (type(record) is not dict or not required <= set(record) <= required | {'operation'} or
                                type(record['classification']) is not str or record['classification'] not in FAILURE_PRIORITY or
                                ('operation' in record and (type(record['operation']) is not str or
                                                            not 1 <= len(record['operation']) <= 64)) or
                                any(type(record[key]) is not str or not 1 <= len(record[key]) <= limit
                                    for key, limit in (('code', 160), ('phase', 64), ('error_type', 64)))):
                            invalid_handoff(); continue
                        FAILURE_SEQUENCE += 1
                        self.failure = retain_failure_record(self.failure, {
                            'status': record['classification'], 'code': record['code'],
                            'phase': record['phase'], 'error_type': record['error_type'],
                            'observed_order': FAILURE_SEQUENCE})
            if not intended:
                self.failure = retain_failure(self.failure, caught, location, local_code)
            for secondary in cleanup:
                visit(secondary, 'native_cleanup')
            if is_admission:
                visit(retention_error, 'admission_prefix_retention')

        visit(error, phase, code)

    def merge_failure(self, state):
        if state is not None:
            for record in [state['primary_failure'], *state['secondary_failures']]:
                self.failure = retain_failure_record(self.failure, record)
            self.failure['additional_failure_records_omitted'] += state['additional_failure_records_omitted']

    def check_time(self):
        if NOW() >= self.deadline or BOOT_NS(time.CLOCK_BOOTTIME) >= self.boottime_deadline_ns:
            raise BatchStopped('conservative native cooperative cutoff exhausted', 'resource_incomplete')

    def write_record(self, path, value, maximum):
        self.check_time()
        raw = canonical(value)
        if self.current is None or len(raw) > maximum:
            raise BatchStopped('native case record outside its fixed writer boundary')
        if self.case_record_bytes + len(raw) > self.current_row['capture_record_bytes_upper']:
            raise BatchStopped('native case capture reservation exhausted')
        # Charge before the exclusive open. A partial/unknown write never
        # releases this allowance or authorizes a second publication.
        self.case_record_bytes += len(raw)
        self.records_bytes += len(raw)
        with OPEN(path, 'xb') as stream:
            stream.write(raw); stream.flush(); FSYNC(stream.fileno())
        sync_directory(path.parent)

    def write_global(self, name, value):
        self.check_time()
        if name not in GLOBAL_RECORD_LIMITS or name in self.global_record_attempts:
            raise BatchStopped('global evidence publication is not an exclusive fixed slot')
        self.global_record_attempts.add(name)
        raw = canonical(value)
        if len(raw) > GLOBAL_RECORD_LIMITS[name] or self.global_record_bytes + len(raw) > GLOBAL_RESERVE:
            raise BatchStopped('native global diagnostic reserve exhausted')
        self.global_record_bytes += len(raw)
        with OPEN(OUTPUT / name, 'xb') as stream:
            stream.write(raw); stream.flush(); FSYNC(stream.fileno())
        sync_directory(OUTPUT)

    def prefix_bytes(self):
        return self.records_bytes + sum(row['size_bytes'] for row in self.output_files.values())

    def begin(self, index, row):
        self.check_time()
        if self.current is not None or row.get('reservation_certified') is not True:
            raise BatchStopped('next fixed selector reservation is unproved',
                               'execution_incomplete' if self.started_selectors else 'execution_blocked')
        prefix = row['reservation_upper_bytes']
        logs = row['log_reservation_upper_bytes']
        controls = row['capture_record_bytes_upper']
        if any(type(value) is not int or value < 0 for value in (prefix, logs, controls)) or controls > prefix:
            raise BatchStopped('fixed selector reservation schema differs')
        if self.settled_prefix_bytes + prefix + GLOBAL_RESERVE > PREFIX_CAP:
            raise BatchStopped('next fixed selector lacks its frozen output headroom', 'resource_incomplete')
        if self.log is None or self.log.size + logs > LOG_CAP:
            raise BatchStopped('next fixed selector lacks its frozen log headroom', 'resource_incomplete')
        self.current = row['selector']; self.current_row = row
        self.active_prefix_reservation = prefix
        self.active_log_reservation = logs
        self.case_log_started = self.log.size
        self.log.case_started = self.log.size
        self.log.case_limit = logs
        self.case_record_bytes = 0
        self.collect_attempted = False
        self.capture_failed = False
        self.version_identities = []
        self.version_attempted_slots = set()
        self.input_witnesses = []
        self.input_attempted_slots = set()
        self.loader_contexts = []
        self.loader_attempted_slots = set()
        self.loader_anchor_history = {}
        self.transport_inputs = []
        self.transport_attempted_slots = set()
        self.case_root = OUTPUT / f'c{index:04d}'
        self.case_root.mkdir(mode=0o700)
        sync_directory(OUTPUT)
        self.temp_count = 0; self.roots = []; self.hooks = []; self.observations = []
        self.case_started = NOW()
        self.case_runtime_before = runtime_isolation_snapshot()
        self.write_record(self.case_root / 'start.json',
            {'schema': 'worker38-native-case-start-v1', 'ordinal': index,
             'selector': self.current, 'reservation_upper_bytes': prefix,
             'log_reservation_upper_bytes': logs}, 512)
        self.started_selectors.append(self.current)

    def temporary(self, suffix=None, prefix=None, dir=None, ignore_cleanup_errors=False, *, delete=True):
        if self.current is None:
            raise BatchStopped('temporary fixture outside fixed selector')
        if suffix not in (None, '') or prefix not in self.plan['allowed_temporary_prefixes']:
            raise BatchStopped('unregistered temporary fixture shape')
        if dir is not None and not Path(dir).absolute().is_relative_to(self.case_root):
            raise BatchStopped('temporary fixture escaped the current fixed case')
        self.temp_count += 1
        if self.temp_count > self.current_row['maximum_temporary_roots'] or self.temp_count > 99:
            raise BatchStopped('temporary fixture count exceeds frozen selector')
        path = self.case_root / f't{self.temp_count:02d}'
        path.mkdir(mode=0o700)
        sync_directory(self.case_root)
        self.roots.append({'root': str(path), 'requested_prefix': prefix, 'ordinal': self.temp_count})
        class RetainedTemporaryDirectory:
            name = str(path)
            def __enter__(self):
                return self.name
            def __exit__(self, *args):
                self.cleanup()
            def cleanup(self):
                # No finalizer is created. Owner kill cannot erase a prefix.
                return None
        return RetainedTemporaryDirectory()

    def hook(self, selector, records):
        # Some tests still have mocked low-level I/O at this callback. Only
        # retain these plain records in memory; inspect after all cleanups.
        try:
            if selector != self.current or self.current is None or type(records) is not list:
                raise BatchStopped('native capture selector mismatch', 'integrity_invalid')
            for record in records:
                if type(record) is not dict:
                    raise BatchStopped('native capture record type differs', 'integrity_invalid')
                if record.get('event') == 'preserve_observed_version':
                    self.preserve_version(record)
                elif record.get('event') == 'input_identity':
                    self.preserve_input_identity(record)
                elif record.get('event') == 'loader_context':
                    self.preserve_loader_context(record)
                elif record.get('event') == 'transport_input_identity':
                    self.preserve_transport_input(record)
                else:
                    self.hooks.append(record)
        except BaseException as error:
            self.capture_error(error, 'native_capture_hook')
            raise

    def capture_error(self, error, phase):
        # A tested expected-exception handler cannot erase a failed witness.
        self.capture_failed = True
        self.fail(error, phase)

    @staticmethod
    def capture_slot(value):
        return (type(value) is str and 1 <= len(value) <= 48 and
                all(ch in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for ch in value))

    def capture_relative(self, value):
        if type(value) is not str or not value.isascii() or len(value) > 512:
            raise BatchStopped('witness path domain differs', 'integrity_invalid')
        path = Path(value)
        if (not path.is_absolute() or '..' in path.parts or
                not path.is_relative_to(self.case_root) or path == self.case_root):
            raise BatchStopped('witness path is outside retained case', 'integrity_invalid')
        return path.relative_to(self.case_root).as_posix()

    def capture_file(self, relative, maximum, *, retain_bytes=False):
        """Read one named regular file through stable no-follow descriptors."""
        descriptors = []
        directory_identities = []
        primary = None
        result = None
        identity = lambda info: (info.st_dev, info.st_ino, info.st_mode,
                                 info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)
        try:
            self.check_time()
            if (type(maximum) is not int or not 0 <= maximum <= PREFIX_CAP or
                    type(relative) is not str or not relative or not relative.isascii() or
                    Path(relative).is_absolute() or any(part in ('', '.', '..') for part in relative.split('/'))):
                raise BatchStopped('witness regular-file rule differs', 'integrity_invalid')
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            current_path = self.case_root
            before = LSTAT(current_path)
            parent = OS_OPEN(current_path, flags)
            descriptors.append(parent)
            opened = FSTAT(parent)
            if not stat.S_ISDIR(before.st_mode) or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                raise BatchStopped('witness case directory changed', 'integrity_invalid')
            directory_identities.append((current_path, opened.st_dev, opened.st_ino))
            parts = relative.split('/')
            for part in parts[:-1]:
                self.check_time()
                before = STAT(part, dir_fd=parent, follow_symlinks=False)
                child = OS_OPEN(part, flags, dir_fd=parent)
                descriptors.append(child)
                opened = FSTAT(child)
                if not stat.S_ISDIR(before.st_mode) or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                    raise BatchStopped('witness ancestor changed', 'integrity_invalid')
                parent = child
                current_path = current_path / part
                directory_identities.append((current_path, opened.st_dev, opened.st_ino))
            before = STAT(parts[-1], dir_fd=parent, follow_symlinks=False)
            fd = OS_OPEN(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=parent)
            descriptors.append(fd)
            opened = FSTAT(fd)
            if not stat.S_ISREG(opened.st_mode) or identity(before) != identity(opened) or opened.st_size > maximum:
                raise BatchStopped('witness file type, identity or size differs', 'integrity_invalid')
            total = 0
            digest = hashlib.sha256()
            blocks = [] if retain_bytes else None
            while True:
                self.check_time()
                block = OS_READ(fd, min(65536, maximum - total + 1))
                if not block:
                    break
                total += len(block)
                if total > maximum or total > opened.st_size:
                    raise BatchStopped('witness file grew during read', 'integrity_invalid')
                digest.update(block)
                if blocks is not None:
                    blocks.append(block)
            after = FSTAT(fd)
            path_after = STAT(parts[-1], dir_fd=parent, follow_symlinks=False)
            if total != opened.st_size or identity(after) != identity(opened) or identity(path_after) != identity(opened):
                raise BatchStopped('witness file changed during read', 'integrity_invalid')
            for path, device, inode in directory_identities:
                info = LSTAT(path)
                if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != (device, inode):
                    raise BatchStopped('witness ancestry changed during read', 'integrity_invalid')
            result = (total, digest.hexdigest(), opened, b''.join(blocks) if blocks is not None else None)
        except BaseException as error:
            primary = error
            self.capture_error(error, 'witness_read')
        finally:
            for fd in reversed(descriptors):
                try:
                    OS_CLOSE(fd)
                except BaseException as error:
                    self.capture_error(error, 'witness_read_close')
                    if primary is None:
                        primary = error
        if primary is not None:
            raise primary
        return result

    def write_capture(self, path, raw):
        """One exclusive, bounded witness publication; a failed slot survives."""
        fd = None
        primary = None
        try:
            self.check_time()
            fd = OS_OPEN(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
            position = 0
            while position < len(raw):
                self.check_time()
                written = OS_WRITE(fd, memoryview(raw)[position:])
                if type(written) is not int or not 0 < written <= len(raw) - position:
                    raise BatchStopped('witness write progress is unconfirmed')
                position += written
            FSYNC(fd)
            if FSTAT(fd).st_size != len(raw):
                raise BatchStopped('witness publication size differs', 'integrity_invalid')
            sync_directory(path.parent)
        except BaseException as error:
            primary = error
            self.capture_error(error, 'witness_write')
        finally:
            if fd is not None:
                try:
                    OS_CLOSE(fd)
                except BaseException as error:
                    self.capture_error(error, 'witness_write_close')
                    if primary is None:
                        primary = error
        if primary is not None:
            raise primary

    def preserve_version(self, record):
        """Only explicitly registered before-overwrite fixture boundaries."""
        try:
            self.check_time()
            if self.capture_failed:
                raise BatchStopped('native evidence capture already failed', self.failure['status'])
            if type(self.current_row) is not dict or self.current_row.get('selector') != self.current:
                raise BatchStopped('version event has no active selector', 'integrity_invalid')
            allowed = self.current_row['version_witnesses']
            index = len(self.version_identities)
            if (type(allowed) is not list or index >= len(allowed) or
                    type(record) is not dict or set(record) != {'event', 'path', 'label', 'maximum_bytes'}):
                raise BatchStopped('unexpected or failed observed version sequence', 'integrity_invalid')
            rule = allowed[index]
            relative = self.capture_relative(record['path'])
            if (type(rule) is not dict or set(rule) != {'label', 'source_pattern', 'slot', 'maximum_bytes'} or
                    not self.capture_slot(rule['slot']) or rule['slot'] in self.version_attempted_slots or
                    type(rule['source_pattern']) is not str or rule['label'] != record['label'] or
                    type(record['maximum_bytes']) is not int or record['maximum_bytes'] != rule['maximum_bytes'] or
                    not fnmatch.fnmatchcase(relative, rule['source_pattern'])):
                raise BatchStopped('unregistered observed version boundary', 'integrity_invalid')
            self.version_attempted_slots.add(rule['slot'])
            size, digest, info, raw = self.capture_file(relative, rule['maximum_bytes'], retain_bytes=True)
            target = self.case_root / ('version-' + rule['slot'] + '.bin')
            observed = {'label': record['label'], 'source_path': relative, 'slot': rule['slot'],
                        'size_bytes': size, 'sha256': digest, 'source_device': info.st_dev,
                        'source_inode': info.st_ino}
            if len(canonical(observed)) > 1024:
                raise BatchStopped('version identity record exceeds fixed domain', 'integrity_invalid')
            self.write_capture(target, raw)
            self.version_identities.append(observed)
        except BaseException as error:
            self.capture_error(error, 'observed_version')
            raise

    def input_path_identity(self, relative, maximum):
        """Observe one map-listed path; expected negative nodes are not followed."""
        descriptors = []
        ancestors = []
        primary = None
        result = None
        try:
            self.check_time()
            if (type(maximum) is not int or not 0 <= maximum <= PREFIX_CAP or
                    type(relative) is not str or not relative or not relative.isascii() or
                    Path(relative).is_absolute() or any(part in ('', '.', '..') for part in relative.split('/'))):
                raise BatchStopped('input witness path rule differs', 'integrity_invalid')
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            parent = OS_OPEN(self.case_root, flags)
            descriptors.append(parent)
            info = FSTAT(parent)
            ancestors.append((self.case_root, info.st_dev, info.st_ino))
            parts = relative.split('/')
            walked = self.case_root
            blocked = False
            for part in parts[:-1]:
                self.check_time()
                try:
                    info = STAT(part, dir_fd=parent, follow_symlinks=False)
                except FileNotFoundError:
                    result = [relative, 'missing', 0, None, 0, 0, 0, 0]
                    blocked = True
                    break
                if not stat.S_ISDIR(info.st_mode):
                    result = [relative, 'blocked_ancestor', 0, None, stat.S_IMODE(info.st_mode),
                              info.st_dev, info.st_ino, info.st_nlink]
                    blocked = True
                    break
                child = OS_OPEN(part, flags, dir_fd=parent)
                descriptors.append(child)
                opened = FSTAT(child)
                if (info.st_dev, info.st_ino) != (opened.st_dev, opened.st_ino):
                    raise BatchStopped('input witness ancestor changed', 'integrity_invalid')
                parent = child
                walked = walked / part
                ancestors.append((walked, opened.st_dev, opened.st_ino))
            if not blocked:
                try:
                    info = STAT(parts[-1], dir_fd=parent, follow_symlinks=False)
                except FileNotFoundError:
                    result = [relative, 'missing', 0, None, 0, 0, 0, 0]
                else:
                    size, digest = 0, None
                    if stat.S_ISREG(info.st_mode):
                        kind = 'file'
                        size, digest, opened, _ = self.capture_file(relative, maximum)
                        if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (
                                opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns):
                            raise BatchStopped('input witness regular-file identity changed', 'integrity_invalid')
                    elif stat.S_ISLNK(info.st_mode):
                        kind = 'symlink'
                        target = os.fsencode(READLINK(parts[-1], dir_fd=parent))
                        size, digest = len(target), sha(target)
                        if size > maximum:
                            raise BatchStopped('input witness symlink exceeds fixed domain', 'integrity_invalid')
                    elif stat.S_ISDIR(info.st_mode):
                        kind = 'directory'
                    else:
                        kind = 'special'
                    after = STAT(parts[-1], dir_fd=parent, follow_symlinks=False)
                    fields = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_size,
                                             value.st_mtime_ns, value.st_ctime_ns, value.st_nlink)
                    if fields(after) != fields(info):
                        raise BatchStopped('input witness node changed', 'integrity_invalid')
                    result = [relative, kind, size, digest, stat.S_IMODE(info.st_mode),
                              info.st_dev, info.st_ino, info.st_nlink]
            for path, device, inode in ancestors:
                after = LSTAT(path)
                if not stat.S_ISDIR(after.st_mode) or (after.st_dev, after.st_ino) != (device, inode):
                    raise BatchStopped('input witness ancestry changed', 'integrity_invalid')
        except BaseException as error:
            primary = error
            self.capture_error(error, 'input_witness_read')
        finally:
            for fd in reversed(descriptors):
                try:
                    OS_CLOSE(fd)
                except BaseException as error:
                    self.capture_error(error, 'input_witness_close')
                    if primary is None:
                        primary = error
        if primary is not None:
            raise primary
        return result

    def preserve_input_identity(self, record):
        """Only the exact registered verifier boundaries, with literal path rules."""
        try:
            self.check_time()
            if self.capture_failed:
                raise BatchStopped('native evidence capture already failed', self.failure['status'])
            allowed_selectors = self.plan.get('input_witness_selectors', [])
            if (allowed_selectors != list(INPUT_WITNESS_SELECTORS) or self.current not in INPUT_WITNESS_SELECTORS or
                    type(self.current_row) is not dict or self.current_row.get('selector') != self.current or
                    type(record) is not dict or set(record) != {'event', 'boundary', 'paths'}):
                raise BatchStopped('input witness selector or event differs', 'integrity_invalid')
            allowed = self.current_row.get('input_witnesses', [])
            index = len(self.input_witnesses)
            if type(allowed) is not list or index >= len(allowed):
                raise BatchStopped('input witness event is unregistered', 'integrity_invalid')
            rule = allowed[index]
            required = {'boundary', 'call_ordinal', 'slot', 'argument_paths', 'path_rules',
                        'maximum_rows', 'maximum_relative_path_bytes', 'record_byte_cap', 'independent_recipe_sha256'}
            if (type(rule) is not dict or set(rule) != required or rule['boundary'] != record['boundary'] or
                    not self.finite_digest(rule['independent_recipe_sha256']) or
                    type(rule['call_ordinal']) is not int or rule['call_ordinal'] != index + 1 or
                    not self.capture_slot(rule['slot']) or rule['slot'] in self.input_attempted_slots or
                    type(record['paths']) is not dict or type(rule['argument_paths']) is not dict or
                    set(record['paths']) != set(rule['argument_paths'])):
                raise BatchStopped('input witness order or arguments differ', 'integrity_invalid')
            arguments = {name: None if value is None else self.capture_relative(value)
                         for name, value in record['paths'].items()}
            if arguments != rule['argument_paths']:
                raise BatchStopped('input witness effective paths differ', 'integrity_invalid')
            paths = rule['path_rules']
            if (type(paths) is not list or type(rule['maximum_rows']) is not int or
                    not 0 <= len(paths) <= rule['maximum_rows'] <= 9999 or
                    type(rule['maximum_relative_path_bytes']) is not int or
                    not 1 <= rule['maximum_relative_path_bytes'] <= 512 or
                    type(rule['record_byte_cap']) is not int or
                    not 0 < rule['record_byte_cap'] <= self.current_row['capture_record_bytes_upper']):
                raise BatchStopped('input witness row or byte bound differs', 'integrity_invalid')
            lookup = {}
            for category in ('input', 'output'):
                for item in self.current_row[category + '_rules']:
                    key = category + ':' + item['pattern']
                    if key in lookup:
                        raise BatchStopped('input witness rule identity is ambiguous', 'integrity_invalid')
                    lookup[key] = item
            rows, seen, validated_paths = [], set(), []
            for item in paths:
                if type(item) is not dict or set(item) != {'rule_id', 'relative_path', 'allowed_state'}:
                    raise BatchStopped('input witness path selection differs', 'integrity_invalid')
                relative = item['relative_path']
                source_rule = lookup.get(item['rule_id'])
                if (source_rule is None or type(relative) is not str or not relative.isascii() or
                        len(relative) > rule['maximum_relative_path_bytes'] or relative in seen or
                        not fnmatch.fnmatchcase(relative, source_rule['pattern'])):
                    raise BatchStopped('input witness path lacks its fixed rule', 'integrity_invalid')
                expected = item['allowed_state']
                state_keys = {'type', 'size_bytes', 'sha256', 'lineage'}
                node_types = {'file', 'symlink', 'missing', 'directory', 'special', 'blocked_ancestor'}
                maximum = source_rule['maximum_bytes']
                digest_pin = lambda value: (type(value) is str and len(value) == 64 and
                                             all(ch in '0123456789abcdef' for ch in value))
                lineage = 'independent_input' if item['rule_id'].startswith('input:') else 'produced_output'
                if (type(expected) is not dict or set(expected) != state_keys or
                        type(expected['type']) is not str or expected['type'] not in node_types or
                        type(maximum) is not int or not 0 <= maximum <= PREFIX_CAP or
                        type(expected['size_bytes']) is not int or not 0 <= expected['size_bytes'] <= maximum or
                        expected['lineage'] != lineage):
                    raise BatchStopped('input witness independent state pin differs', 'integrity_invalid')
                if expected['type'] in ('file', 'symlink'):
                    valid_identity = digest_pin(expected['sha256'])
                else:
                    valid_identity = expected['size_bytes'] == 0 and expected['sha256'] is None
                if not valid_identity:
                    raise BatchStopped('input witness state identity schema differs', 'integrity_invalid')
                seen.add(relative)
                validated_paths.append((relative, maximum,
                    (expected['type'], expected['size_bytes'], expected['sha256'])))
            # Validate the complete frozen state contract before reading any
            # selected input, including a malformed pin in a later path rule.
            state_mismatch = None
            self.input_attempted_slots.add(rule['slot'])
            for relative, maximum, expected_identity in validated_paths:
                observed_row = self.input_path_identity(relative, maximum)
                rows.append(observed_row)
                # The fixed map supplies one independently anchored state for
                # this exact invocation, never a union of all test variants.
                # Raw malformed-file and symlink hashes are valid negative
                # fixtures when pinned; no JSON parsing or link following occurs.
                if tuple(observed_row[1:4]) != expected_identity:
                    state_mismatch = BatchStopped('input witness consumed state differs', 'integrity_invalid')
                    # Establish the primary cause before any fallible evidence
                    # publication. Keep the observed prefix in this same slot.
                    self.capture_error(state_mismatch, 'input_identity_state')
                    break
            observed = {'schema': 'worker38-native-input-witness-v1', 'selector': self.current,
                        'boundary': record['boundary'], 'call_ordinal': index + 1, 'slot': rule['slot'],
                        'arguments': arguments, 'rows': rows, 'rows_sha256': sha(canonical(rows))}
            raw = canonical(observed)
            if len(raw) > rule['record_byte_cap'] or self.case_record_bytes + len(raw) > self.current_row['capture_record_bytes_upper']:
                raise BatchStopped('input witness exceeds reserved control bytes', 'resource_incomplete')
            self.case_record_bytes += len(raw)
            self.records_bytes += len(raw)
            self.write_capture(self.case_root / ('input-witness-' + rule['slot'] + '.json'), raw)
            if state_mismatch is not None:
                # A durable mismatch witness is retained evidence, not an
                # accepted event. It cannot advance the count or settle.
                raise state_mismatch
            identity = {'slot': rule['slot'], 'boundary': record['boundary'],
                        'call_ordinal': index + 1, 'size_bytes': len(raw), 'sha256': sha(raw)}
            if len(canonical(identity)) > 1024:
                raise BatchStopped('input witness identity exceeds fixed domain', 'integrity_invalid')
            self.input_witnesses.append(identity)
        except BaseException as error:
            self.capture_error(error, 'input_identity')
            raise

    @staticmethod
    def finite_digest(value):
        return (type(value) is str and len(value) == 64 and
                all(ch in '0123456789abcdef' for ch in value))

    def finite_path_contract(self, rule, exact_paths):
        """Only the named loader/transport seams; never discover path rules."""
        paths = rule['path_rules']
        if type(paths) is not list or len(paths) != len(exact_paths):
            raise BatchStopped('finite boundary path roster differs', 'integrity_invalid')
        lookup = {}
        for category in ('input', 'output'):
            for item in self.current_row[category + '_rules']:
                name = category + ':' + item['pattern']
                if name in lookup:
                    raise BatchStopped('finite boundary lineage is ambiguous', 'integrity_invalid')
                lookup[name] = item
        validated = []
        for item, relative in zip(paths, exact_paths):
            if (type(item) is not dict or set(item) != {'rule_id', 'relative_path', 'allowed_state'} or
                    item['relative_path'] != relative or type(item['rule_id']) is not str):
                raise BatchStopped('finite boundary path selection differs', 'integrity_invalid')
            source = lookup.get(item['rule_id'])
            if source is None or not fnmatch.fnmatchcase(relative, source['pattern']):
                raise BatchStopped('finite boundary path lacks source lineage', 'integrity_invalid')
            expected = item['allowed_state']
            keys = {'type', 'size_bytes', 'sha256', 'lineage', 'independent_recipe_sha256', 'materialized'}
            maximum = source['maximum_bytes']
            lineage = 'independent_input' if item['rule_id'].startswith('input:') else 'produced_output'
            if (type(expected) is not dict or set(expected) != keys or
                    expected['materialized'] is not True or
                    type(expected['type']) is not str or expected['type'] not in
                        ('file', 'symlink', 'missing', 'directory', 'special', 'blocked_ancestor') or
                    type(maximum) is not int or not 0 <= maximum <= PREFIX_CAP or
                    type(expected['size_bytes']) is not int or not 0 <= expected['size_bytes'] <= maximum or
                    expected['lineage'] != lineage or
                    not self.finite_digest(expected['independent_recipe_sha256'])):
                raise BatchStopped('finite boundary independent state is unadmitted', 'integrity_invalid')
            if expected['type'] in ('file', 'symlink'):
                valid = self.finite_digest(expected['sha256'])
            else:
                valid = expected['size_bytes'] == 0 and expected['sha256'] is None
            if not valid:
                raise BatchStopped('finite boundary state identity differs', 'integrity_invalid')
            validated.append((relative, maximum,
                (expected['type'], expected['size_bytes'], expected['sha256'])))
        return validated

    def finite_rows(self, validated, *, with_stats=False):
        """Keep an observed prefix even when the next no-follow read fails."""
        rows, anchors, failure = [], {}, None
        for relative, maximum, expected in validated:
            try:
                row = self.input_path_identity(relative, maximum)
                if (any(type(value) is not int or len(str(abs(value))) > 20 for value in row[4:]) or
                        len(canonical(row)) > 192 + 6 * len(relative.encode('ascii'))):
                    raise BatchStopped('finite boundary real scalar domain differs', 'integrity_invalid')
                rows.append(row)
                if tuple(row[1:4]) != expected:
                    raise BatchStopped('finite boundary consumed state differs', 'integrity_invalid')
                if with_stats and row[1] == 'file':
                    size, digest, info, _ = self.capture_file(relative, maximum)
                    signature = (info.st_dev, info.st_ino, info.st_mode, info.st_size,
                                 info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)
                    if (any(type(value) is not int or len(str(abs(value))) > 20 for value in signature) or
                            (size, digest, stat.S_IMODE(info.st_mode), info.st_dev, info.st_ino, info.st_nlink) !=
                            (row[2], row[3], *row[4:])):
                        raise BatchStopped('finite boundary real anchor changed', 'integrity_invalid')
                    anchors[relative] = signature
            except BaseException as error:
                failure = error
                self.capture_error(error, 'finite_boundary_state')
                break
        return rows, anchors, failure

    def publish_finite_capture(self, rule, prefix, observed, accepted, failure):
        raw = canonical(observed)
        if len(raw) > rule['record_byte_cap'] or self.case_record_bytes + len(raw) > self.current_row['capture_record_bytes_upper']:
            raise BatchStopped('finite boundary exceeds reserved control bytes', 'resource_incomplete')
        # Same charge and same exclusive slot for success, mismatch and partial.
        self.case_record_bytes += len(raw)
        self.records_bytes += len(raw)
        self.write_capture(self.case_root / (prefix + rule['slot'] + '.json'), raw)
        if failure is not None:
            raise failure
        identity = {'slot': rule['slot'], 'boundary': rule['boundary'],
                    'call_ordinal': rule['call_ordinal'], 'size_bytes': len(raw), 'sha256': sha(raw)}
        if len(canonical(identity)) > 1024:
            raise BatchStopped('finite reference scalar domain differs', 'integrity_invalid')
        accepted.append(identity)

    def finite_settlement_contract(self):
        """Exact new-event counts and separately charged enclosing JSON framing."""
        framing = 0
        for name, events, accepted in (
                ('loader_contexts', LOADER_CONTEXT_EVENTS, self.loader_contexts),
                ('transport_inputs', TRANSPORT_INPUT_EVENTS, self.transport_inputs)):
            required = len(events.get(self.current, ()))
            listed = self.current_row.get(name, [])
            if type(listed) is not list or len(listed) != required or len(accepted) != required:
                raise BatchStopped('finite boundary sequence is incomplete', 'integrity_invalid')
            if required:
                # Nonempty inventory object: comma + quoted key + colon + []
                # + (n-1) inter-reference commas. Reference bodies themselves
                # are separately reserved, with their terminal newline removed.
                framing += len(name) + required + 5
        if (type(self.current_row.get('finite_reference_framing_bytes_upper', 0)) is not int or
                self.current_row.get('finite_reference_framing_bytes_upper', 0) != framing):
            raise BatchStopped('finite reference framing reservation differs', 'integrity_invalid')

    def preserve_transport_input(self, record):
        """Two fixed consumed-input seams, outside the unchanged verifier gate."""
        try:
            self.check_time()
            if self.capture_failed:
                raise BatchStopped('native evidence capture already failed', self.failure['status'])
            events = TRANSPORT_INPUT_EVENTS.get(self.current)
            if (events is None or type(self.current_row) is not dict or
                    self.current_row.get('selector') != self.current or
                    type(record) is not dict or set(record) != {'event', 'boundary', 'paths'}):
                raise BatchStopped('transport boundary selector or envelope differs', 'integrity_invalid')
            allowed = self.current_row.get('transport_inputs')
            index = len(self.transport_inputs)
            if type(allowed) is not list or len(allowed) != len(events) or index >= len(events):
                raise BatchStopped('transport boundary count differs', 'integrity_invalid')
            boundary, slot, paths, _ = events[index]
            rule = allowed[index]
            if (type(rule) is not dict or set(rule) !=
                    {'boundary', 'call_ordinal', 'slot', 'path_rules', 'record_byte_cap'} or
                    rule['boundary'] != boundary or record['boundary'] != boundary or rule['slot'] != slot or
                    slot in self.transport_attempted_slots or type(rule['call_ordinal']) is not int or
                    rule['call_ordinal'] != index + 1 or type(rule['record_byte_cap']) is not int or
                    rule['record_byte_cap'] != TRANSPORT_INPUT_CAPS[slot] or
                    type(record['paths']) is not list or len(record['paths']) != len(paths) or
                    tuple(self.capture_relative(value) for value in record['paths']) != paths):
                raise BatchStopped('transport boundary fixed contract differs', 'integrity_invalid')
            validated = self.finite_path_contract(rule, paths)
            self.transport_attempted_slots.add(slot)
            rows, _, failure = self.finite_rows(validated)
            observed = {'schema': 'worker38-native-transport-input-v1', 'selector': self.current,
                        'boundary': boundary, 'call_ordinal': index + 1, 'slot': slot,
                        'rows': rows, 'rows_sha256': sha(canonical(rows))}
            self.publish_finite_capture(rule, 'transport-input-', observed, self.transport_inputs, failure)
        except BaseException as error:
            self.capture_error(error, 'transport_input_identity')
            raise

    @staticmethod
    def loader_scalar_valid(name, tag, value, slot):
        if tag == 'null':
            return value is None
        if tag == 'bool':
            return type(value) is bool
        if tag == 'int':
            return type(value) is int and -(10 ** 20) < value < 10 ** 20
        if tag != 'str' or type(value) is not str:
            return False
        if name.endswith('sha256'):
            width = 63 if slot == 'c29-09' and name == 'argument.library_sha256' else 64
            return len(value) == width and all(char in '0123456789abcdef' for char in value)
        mapping = name in ('maps.0', 'maps.1')
        ceiling = 2048 if mapping else (64 if name.endswith(('.shape', '.container', '.mode', '.error'))
                                          or name in ('variant', 'content_state', 'key', 'implementation',
                                                      'version', 'platform') else 512)
        return (len(value) <= ceiling and value.isascii() and
                all(' ' <= char <= '~' or mapping and char == '\n' for char in value))

    def loader_context_prefix(self, context, schema, slot):
        """Encode only the finite selected scalar roster, retaining a safe prefix."""
        safe, complete = [], True
        if type(context) is not list:
            return canonical(safe), False
        for index, item in enumerate(context[:65]):
            if (index >= len(schema) or index >= 64 or type(item) is not list or len(item) != 3 or
                    item[0] != schema[index][0] or type(item[1]) is not str or
                    not self.loader_scalar_valid(item[0], item[1], item[2], slot)):
                complete = False
                break
            safe.append(item)
            raw = canonical(safe)
            if len(raw) > LOADER_CONTEXT_CAP:
                return raw[:LOADER_CONTEXT_CAP], False
            if item[1] != schema[index][1]:
                complete = False
                break
        raw = canonical(safe)
        return raw, complete and len(safe) == len(schema) == len(context)

    def loader_dynamic_values(self, slot, rows, anchors):
        """Handwritten named substitutions; no map expressions or callback values."""
        values = {}
        stat_names = ('dev', 'ino', 'mode', 'size', 'mtime_ns', 'ctime_ns', 'nlink')
        def stat_fields(prefix, signature):
            for name, value in zip(stat_names, signature):
                values[prefix + '.' + name] = value

        if slot in ('c26-02', 'c26-03'):
            current = anchors['t01/literal-library']
            initial = current if slot == 'c26-02' else self.loader_anchor_history['c26-02']['t01/literal-library']
            stat_fields('initial', initial)
            if slot == 'c26-03':
                stat_fields('observed', current)
                stat_fields('returned', current)
                values['returned.mtime_ns'] = initial[4] + 1
        elif slot in ('c26-04', 'c26-05'):
            current = anchors['t01/literal-library']
            initial = current if slot == 'c26-04' else self.loader_anchor_history['c26-04']['t01/literal-library']
            values['initial.dev'], values['initial.ino'] = initial[:2]
            if slot == 'c26-05' and current[:2] == initial[:2]:
                raise BatchStopped('P03 replacement real inode pair did not change', 'integrity_invalid')
        elif slot == 'c26-06':
            for prefix, row in (('executable', rows[0]), ('library', rows[1]), ('changed', rows[1])):
                signature = anchors[row[0]]
                values[prefix + '.device.major'] = MAJOR(signature[0])
                values[prefix + '.device.minor'] = MINOR(signature[0])
                values[prefix + '.inode'] = signature[1]
                stat_fields(prefix + '._stat', signature)
        elif slot.startswith('c27-'):
            library = rows[1]
            major, minor, inode = MAJOR(library[5]), MINOR(library[5]), library[6]
            values.update({'device.major': major, 'device.minor': minor, 'inode': inode})
            path = str(self.case_root / library[0])
            devtext = '%x:%x' % (major, minor)
            maps = ('1000-2000 r--p 00000000 %s %s %s\n'
                    '2000-3000 r-xp 00001000 %s %s %s\n') % (devtext, inode, path, devtext, inode, path)
            if slot == 'c27-02':
                values['maps.0'] = maps.replace(path, str(Path(path).parent / 'alias-libpython.so'))
            elif slot == 'c27-03':
                values['maps.0'] = maps.replace(path, path + ' (deleted)')
            elif slot == 'c27-04':
                values['maps.0'] = maps.replace(' ' + devtext + ' ', ' ff:ff ')
            elif slot == 'c27-05':
                values['maps.0'] = maps.replace(' %s ' % inode, ' %s ' % (inode + 1))
            elif slot == 'c27-06':
                values['maps.0'] = maps + '3000-4000 r-xp 00000000 00:01 987 /other/libpython3.12.so.1.0\n'
            elif slot == 'c27-07':
                values['maps.0'] = maps + 'not a proc map\n'
            elif slot == 'c27-08':
                values['maps.0'] = maps + '3000-4000 r-xp 00000000 %s %s /other/alias.so\n' % (devtext, inode)
            elif slot == 'c27-09':
                values['maps.0'] = maps
                values['maps.1'] = maps.replace('2000-3000', '2000-4000')
        elif (slot == 'c29-01' or slot.startswith('c30-') or
                slot in ('c31-02', 'c31-04', 'c31-07') or slot.startswith('c32-')):
            library = rows[1]
            prefix = 'loader' if slot.startswith('c32-') else 'argument'
            major, minor, inode = MAJOR(library[5]), MINOR(library[5]), library[6]
            values[prefix + '.library_device.major'] = major
            values[prefix + '.library_device.minor'] = minor
            values[prefix + '.library_inode'] = inode + (1 if slot == 'c31-04' else 0)
            if slot != 'c30-02':
                values[prefix + '.mapped_library.device.major'] = major
                values[prefix + '.mapped_library.device.minor'] = minor + (1 if slot == 'c30-08' else 0)
                values[prefix + '.mapped_library.inode'] = inode + (1 if slot in ('c30-09', 'c31-04') else 0)
        return values

    def preserve_loader_context(self, record):
        """Sixty exact loader seams with actual context and independent contracts."""
        try:
            self.check_time()
            if self.capture_failed:
                raise BatchStopped('native evidence capture already failed', self.failure['status'])
            events = LOADER_CONTEXT_EVENTS.get(self.current)
            if (events is None or type(self.current_row) is not dict or
                    self.current_row.get('selector') != self.current or type(record) is not dict):
                raise BatchStopped('loader boundary selector differs', 'integrity_invalid')
            allowed = self.current_row.get('loader_contexts')
            index = len(self.loader_contexts)
            if type(allowed) is not list or len(allowed) != len(events) or index >= len(events):
                raise BatchStopped('loader boundary count differs', 'integrity_invalid')
            boundary, slot, paths, relation_names = events[index]
            rule = allowed[index]
            keys = {'boundary', 'call_ordinal', 'slot', 'path_rules', 'record_byte_cap',
                    'context_recipe_sha256', 'context_materialized', 'expected_context', 'context_dynamic_fields'}
            if (type(rule) is not dict or set(rule) != keys or rule['boundary'] != boundary or
                    rule['slot'] != slot or slot in self.loader_attempted_slots or
                    type(rule['call_ordinal']) is not int or rule['call_ordinal'] != index + 1 or
                    type(rule['record_byte_cap']) is not int or rule['record_byte_cap'] != LOADER_RECORD_CAP or
                    rule['context_materialized'] is not True or not self.finite_digest(rule['context_recipe_sha256'])):
                raise BatchStopped('loader independent contract is unadmitted', 'integrity_invalid')
            schema, dynamic_fields = LOADER_CONTEXT_SCHEMAS[slot], LOADER_DYNAMIC_FIELDS[slot]
            expected = rule['expected_context']
            if (type(expected) is not list or len(expected) != len(schema) or
                    rule['context_dynamic_fields'] != list(dynamic_fields)):
                raise BatchStopped('loader independent context roster differs', 'integrity_invalid')
            for item, (name, tag) in zip(expected, schema):
                if (type(item) is not list or len(item) != 3 or item[:2] != [name, tag] or
                        (item[2] is not None if name in dynamic_fields else
                         not self.loader_scalar_valid(name, tag, item[2], slot))):
                    raise BatchStopped('loader independent context value differs', 'integrity_invalid')
            # Validate the whole independent contract before observing any file
            # or accepting any dynamic substitution. A literal null is separate
            # from the exact source-fixed dynamic-field roster above.
            validated = self.finite_path_contract(rule, paths)
            self.loader_attempted_slots.add(slot)
            failure, rows, anchors = None, [], {}
            try:
                if (set(record) != {'event', 'boundary', 'context', 'paths'} or
                        record.get('boundary') != boundary or type(record.get('paths')) is not list or
                        len(record['paths']) != len(paths) or
                        tuple(self.capture_relative(value) for value in record['paths']) != paths):
                    raise BatchStopped('loader actual envelope or paths differ', 'integrity_invalid')
                rows, anchors, failure = self.finite_rows(validated, with_stats=slot.startswith('c26-'))
            except BaseException as error:
                failure = error
                self.capture_error(error, 'loader_context_envelope')
            raw_context, complete = self.loader_context_prefix(record.get('context'), schema, slot)
            actual_matches = False
            if failure is None:
                try:
                    values = self.loader_dynamic_values(slot, rows, anchors)
                    if set(values) != set(dynamic_fields):
                        raise BatchStopped('loader real dynamic anchor roster differs', 'integrity_invalid')
                    resolved = [[name, tag, values[name] if name in dynamic_fields else value]
                                for name, tag, value in expected]
                    if any(not self.loader_scalar_valid(name, tag, value, slot) for name, tag, value in resolved):
                        raise BatchStopped('loader real dynamic anchor domain differs', 'integrity_invalid')
                    actual_matches = complete and canonical(resolved) == raw_context
                    if not actual_matches:
                        raise BatchStopped('loader actual context differs from independent recipe', 'integrity_invalid')
                except BaseException as error:
                    failure = error
                    self.capture_error(error, 'loader_context_state')
            # Relations are verified only by complete independently checked
            # context plus observed node state. Null means unverified on a
            # failure path; it never claims an individual relation was false.
            observed = {'schema': 'worker38-native-loader-context-v1', 'selector': self.current,
                        'boundary': boundary, 'call_ordinal': index + 1, 'slot': slot,
                        'rows': rows, 'rows_sha256': sha(canonical(rows)),
                        'relations': [True if failure is None and actual_matches else None] * len(relation_names),
                        'actual_context_b64': base64.b64encode(raw_context).decode('ascii'),
                        'context_complete': complete, 'context_recipe_sha256': rule['context_recipe_sha256'],
                        'context_size_bytes': len(raw_context)}
            self.publish_finite_capture(rule, 'loader-context-', observed, self.loader_contexts, failure)
            if slot in ('c26-02', 'c26-04'):
                self.loader_anchor_history[slot] = anchors
        except BaseException as error:
            self.capture_error(error, 'loader_context')
            raise

    def observe(self, status, label):
        self.check_time()
        encoded = label.encode('utf-8')
        record = {'ordinal': len(self.observations) + 1, 'status': status,
                  'label_sha256': sha(encoded), 'label_bytes': len(encoded)}
        if len(self.observations) >= self.current_row['maximum_observation_records']:
            raise BatchStopped('native observation count exceeds frozen selector')
        self.write_record(self.case_root / f'observation-{len(self.observations)+1:04d}.json', record, 256)
        self.observations.append(record)

    def collect(self):
        self.check_time()
        if self.collect_attempted:
            raise BatchStopped('native case reconciliation is not retried')
        self.collect_attempted = True
        explicit = set()
        observed_inputs = set()
        for record in self.hooks:
            if 'native_writer_state' in record and record['native_writer_state'] != 'confirmed':
                raise BatchStopped('native literal writer completion is unconfirmed')
            root = Path(record['root']).absolute()
            if not root.is_relative_to(self.case_root):
                raise BatchStopped('hook root escaped fixed case')
            setup = record.get('setup_inventory', {})
            paths = record.get('explicit_produced_paths', [])
            subtrees = record.get('explicit_produced_subtrees', [])
            for item in inventory(root):
                name = item['path']; absolute = str(root / name)
                named = name in paths or any(name == stem or name.startswith(stem.rstrip('/') + '/')
                                             for stem in subtrees)
                produced = (named or (record.get('setup_complete', True) is True and (
                    name in record.get('surviving_produced_paths', []) or
                    (record.get('all_new_paths_are_output') is True and name not in setup))))
                if produced:
                    explicit.add(absolute)
                else:
                    observed_inputs.add(absolute)
        rows = inventory(self.case_root, durable=True)
        if len(rows) > self.current_row['maximum_inventory_rows']:
            raise BatchStopped('native retained path count contradicts its fixed reservation', 'integrity_invalid')
        out_rows, input_rows = [], []
        control_names = ({'start.json'} | {f'observation-{i+1:04d}.json' for i in range(len(self.observations))} |
                         {'input-witness-' + slot + '.json' for slot in self.input_attempted_slots} |
                         {'loader-context-' + slot + '.json' for slot in self.loader_attempted_slots} |
                         {'transport-input-' + slot + '.json' for slot in self.transport_attempted_slots})
        committed_witnesses = {
            'version-' + item['slot'] + '.bin': item for item in self.version_identities}
        committed_witnesses.update({
            'input-witness-' + item['slot'] + '.json': item for item in self.input_witnesses})
        committed_witnesses.update({
            'loader-context-' + item['slot'] + '.json': item for item in self.loader_contexts})
        committed_witnesses.update({
            'transport-input-' + item['slot'] + '.json': item for item in self.transport_inputs})
        found_witnesses = set()
        output_rules = self.current_row['output_rules']
        input_rules = self.current_row['input_rules']
        for item in rows:
            relative = item['path']; absolute = str(self.case_root / relative)
            if relative in committed_witnesses:
                expected_identity = committed_witnesses[relative]
                if (item['type'] != 'file' or item['size_bytes'] != expected_identity['size_bytes'] or
                        item.get('sha256') != expected_identity['sha256']):
                    raise BatchStopped('committed witness bytes changed', 'integrity_invalid')
                found_witnesses.add(relative)
            compact = [relative, item['type'], item['size_bytes'], item.get('sha256'),
                       item['mode'], item['device'], item['inode'], item['nlink']]
            if len(canonical(compact)) > 192 + 6 * len(relative.encode('ascii')):
                raise BatchStopped('inventory scalar domain differs', 'integrity_invalid')
            if relative in control_names:
                out_rows.append(compact)
                continue
            matched_output = [rule for rule in output_rules if fnmatch.fnmatchcase(relative, rule['pattern'])]
            if absolute in explicit and not matched_output:
                raise BatchStopped('hook names output absent from frozen sink map', 'integrity_invalid')
            if matched_output:
                if (len(matched_output) != 1 or
                        item['type'] != matched_output[0]['expected_type'] or
                        item['size_bytes'] > matched_output[0]['maximum_bytes']):
                    raise BatchStopped('produced file contradicts frozen sink type or size', 'integrity_invalid')
                self.output_files[absolute] = {**item, 'absolute_path': absolute, 'selector': self.current}
                out_rows.append(compact)
                continue
            matched_input = [rule for rule in input_rules if fnmatch.fnmatchcase(relative, rule['pattern'])]
            if len(matched_input) != 1:
                raise BatchStopped('unclassified retained fixture path', 'integrity_invalid')
            rule = matched_input[0]
            if (item['type'] != rule['expected_type'] or
                    item.get('sha256') not in rule['allowed_sha256'] or
                    item['size_bytes'] > rule['maximum_bytes']):
                # An interrupted/divergent setup file is not an immutable
                # input. Its possible prefix was reserved before setup.
                if item['size_bytes'] <= rule['maximum_bytes']:
                    self.output_files[absolute] = {**item, 'absolute_path': absolute,
                                                   'selector': self.current, 'setup_prefix': True}
                raise BatchStopped('retained literal setup is incomplete or differs from fixed pins', 'integrity_invalid')
            self.input_files[absolute] = {**item, 'absolute_path': absolute, 'selector': self.current}
            input_rows.append(compact)
        if found_witnesses != set(committed_witnesses):
            raise BatchStopped('committed witness is missing', 'integrity_invalid')
        case_payload = sum(item['size_bytes'] for item in self.output_files.values()
                           if item['selector'] == self.current)
        for group, ceiling in self.current_row.get('output_groups', {}).items():
            members = {rule['pattern'] for rule in output_rules if rule.get('group') == group}
            actual = sum(item['size_bytes'] for item in self.output_files.values()
                         if item['selector'] == self.current and
                         Path(item['absolute_path']).relative_to(self.case_root).as_posix() in members)
            if actual > ceiling:
                raise BatchStopped('produced group contradicts certified sink allowance', 'integrity_invalid')
        if case_payload + self.case_record_bytes > self.active_prefix_reservation:
            raise BatchStopped('observed native bytes contradict certified reservation', 'integrity_invalid')
        record = {'schema': 'worker38-native-case-inventory-v1', 'selector': self.current,
                  'input_rows': input_rows, 'produced_rows': out_rows,
                  'produced_payload_bytes': case_payload, 'input_bytes': sum(row[2] for row in input_rows),
                  'logical_paths_are_charged_individually': True,
                  'excluded_later_native_records': ['inventory.json', 'method.json']}
        if self.version_identities:
            record['captured_versions'] = self.version_identities
        if self.input_witnesses:
            record['input_witnesses'] = self.input_witnesses
        if self.loader_contexts:
            record['loader_contexts'] = self.loader_contexts
        if self.transport_inputs:
            record['transport_inputs'] = self.transport_inputs
        self.write_record(self.case_root / 'inventory.json', record,
                          self.current_row['inventory_record_bytes_upper'])
        raw = canonical(record)
        self.pending_inventory_pin = [int(self.case_root.name[1:]), sha(raw), len(raw)]
        self.case_payload_bytes = case_payload

    def end(self, status):
        if runtime_isolation_snapshot() != self.case_runtime_before:
            raise BatchStopped('native process state restoration is unconfirmed', 'integrity_invalid')
        if self.capture_failed:
            raise BatchStopped('native evidence capture failed', self.failure['status'])
        if status == 'passed' and self.failure is None:
            if (len(self.version_identities) != len(self.current_row.get('version_witnesses', [])) or
                    len(self.input_witnesses) != len(self.current_row.get('input_witnesses', []))):
                raise BatchStopped('required witness sequence is incomplete', 'integrity_invalid')
            self.finite_settlement_contract()
        self.collect()
        if self.log.overflow or self.log.write_failure or self.log.size - self.case_log_started > self.active_log_reservation:
            raise BatchStopped('native case log capture is incomplete')
        result = {'selector': self.current, 'status': status,
            'elapsed_seconds': NOW() - self.case_started, 'temporary_roots': self.temp_count,
            'observation_records': len(self.observations),
            'produced_files': sum(x['selector'] == self.current for x in self.output_files.values()),
            'produced_bytes': sum(x['size_bytes'] for x in self.output_files.values() if x['selector'] == self.current)}
        if not (0 <= result['elapsed_seconds'] < 600 and result['observation_records'] <= 9999 and
                result['produced_files'] <= 999999 and result['produced_bytes'] <= PREFIX_CAP):
            raise BatchStopped('native method observation outside frozen scalar domain')
        self.write_record(self.case_root / 'method.json', result, 512)
        if self.case_payload_bytes + self.case_record_bytes > self.active_prefix_reservation:
            raise BatchStopped('settled case exceeds certified reservation', 'integrity_invalid')
        self.method_results.append(result)
        if status != 'passed':
            raise BatchStopped('fixed preparation case failed; reservation remains committed')
        self.settled_prefix_bytes += self.case_payload_bytes + self.case_record_bytes
        self.inventory_index.append(self.pending_inventory_pin)
        self.active_prefix_reservation = 0
        self.active_log_reservation = 0
        self.current = self.current_row = None


def main():
    # GNU timeout owns the hard600-second interval from its actual invocation.
    # The trusted shell samples earlier only for a conservative cooperative
    # cutoff; this is not a claim that the two start instants are identical.
    # Pair monotonic first and boottime second; floor and subtract1ms so this
    # conversion can only shorten the cooperative interval, including suspend.
    raw_deadline = os.environ.get('WORKER38_NATIVE_DEADLINE_CS', '')
    if not raw_deadline.isascii() or not raw_deadline.isdigit() or not 1 <= len(raw_deadline) <= 20:
        raise SystemExit('original shell boottime deadline is required')
    mono_before = time.monotonic_ns()
    remaining_ns = int(raw_deadline) * 10000000 - time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    if not 0 < remaining_ns <= 600000000000:
        raise SystemExit('original native wall interval is unavailable or expired')
    deadline = ((mono_before + remaining_ns) // 1000000 - 1) / 1000.0
    started = deadline - 600.0
    before_as = GETRLIMIT(resource.RLIMIT_AS)
    if before_as not in ((resource.RLIM_INFINITY,) * 2, (MEMORY_CAP,) * 2):
        raise SystemExit('native inherited address-space limit differs')
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP,) * 2)
    if GETRLIMIT(resource.RLIMIT_AS) != (MEMORY_CAP,) * 2:
        raise SystemExit('native512MiB installation unconfirmed')
    expected = os.environ.get('WORKER38_FIXED_MAP_SHA256', '')
    if len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
        raise SystemExit('explicit independently approved fixed map SHA256 required')
    with OPEN(MAP_PATH, 'rb') as stream:
        raw = stream.read(8 * 1024 ** 2 + 1)
    if len(raw) > 8 * 1024 ** 2 or sha(raw) != expected:
        raise SystemExit('fixed preparation map bytes differ')
    plan = json.loads(raw)
    if plan['schema'] != 'worker38-fixed-preparation-map-v1' or len(plan['cases']) != 397:
        raise SystemExit('exact397-method map required')
    if plan['caps'] != {'wall_seconds': 600, 'address_space_bytes': MEMORY_CAP,
                        'case_prefix_bytes': PREFIX_CAP, 'log_bytes': LOG_CAP}:
        raise SystemExit('native cap map differs')
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise SystemExit('exclusive native output destination already exists')
    for name, info in plan['source_files'].items():
        path = ROOT / name
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise SystemExit('source path is not a contained regular file')
        size, digest = hash_file(path)
        if size != info['size_bytes'] or digest != info['sha256']:
            raise SystemExit('source pin mismatch: ' + name)
    for name, info in plan['support_files'].items():
        size, digest = hash_file(ROOT / name)
        if size != info['size_bytes'] or digest != info['sha256']:
            raise SystemExit('preparation support pin mismatch: ' + name)
    native_environment_files = verify_native_environment(plan['native_environment'], plan['environment'], deadline)
    OUTPUT.mkdir(mode=0o700)
    sync_directory(OUTPUT.parent)
    capture = Capture(plan, started, deadline, int(raw_deadline) * 10000000)
    log = LogStream(OUTPUT / 'stdout-stderr.log')
    capture.log = log
    original_stdout, original_stderr = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = log
    modules = {}
    stopped = None
    capture.write_global('start.json', {'schema': 'worker38-native-batch-start-v1',
        'fixed_map_sha256': expected, 'planned_methods': 397,
        'global_prefix_reserve_bytes': GLOBAL_RESERVE,
        'cooperative_deadline_monotonic': capture.deadline,
        'cooperative_deadline_boottime_ns': capture.boottime_deadline_ns,
        'external_hard_timeout_seconds': 600,
        'clock_boundary': 'GNU timeout owns its invocation interval; earlier cooperative cutoff may only shorten work',
        'native_pid': GETPID(), 'status': 'started_no_completion_claim'})
    try:
        def bounded_os_write(fd, raw):
            if fd in (1, 2):
                return log.write(bytes(raw))
            return OS_WRITE(fd, raw)
        os.write = bounded_os_write
        sys.meta_path.insert(0, DenyScientificImports())
        socket.socket.connect = deny_network
        socket.create_connection = deny_network
        socket.getaddrinfo = deny_network
        tempfile.TemporaryDirectory = capture.temporary
        sys.path.insert(0, str(ROOT / 'tests'))
        sys.path.insert(0, str(ROOT / 'scripts'))
        def load_literal_module(name):
            if name not in plan['test_modules']:
                raise BatchStopped('unregistered lazy test-module dependency')
            module_name = Path(name).stem
            if module_name in sys.modules:
                module = sys.modules[module_name]
            else:
                spec = importlib.util.spec_from_file_location(module_name, ROOT / name)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
            modules[name] = module
            if hasattr(module, 'PRODUCTION_OUTPUT_HOOK'):
                module.PRODUCTION_OUTPUT_HOOK = capture.hook
            if hasattr(module, 'NATIVE_BATCH_DEADLINE_MONOTONIC'):
                module.NATIVE_BATCH_DEADLINE_MONOTONIC = capture.deadline
            if hasattr(module, 'NATIVE_CURRENT_SELECTOR'):
                module.NATIVE_CURRENT_SELECTOR = capture.current
            if hasattr(module, 'CURRENT_PRODUCTION_SELECTOR'):
                module.CURRENT_PRODUCTION_SELECTOR = capture.current
            return module
        for index, row in enumerate(plan['cases'], 1):
            capture.begin(index, row)
            observation_root = capture.case_root / 'retained-observations'
            observation_root.mkdir(mode=0o700)
            legacy_directory = observation_root / 'worker37'
            modern_directory = observation_root / 'worker38'
            legacy_directory.mkdir(mode=0o700)
            modern_directory.mkdir(mode=0o700)
            os.environ['WORKER37_LITERAL_EVIDENCE_DIRECTORY'] = str(legacy_directory)
            os.environ['WORKER38_LITERAL_EVIDENCE_DIRECTORY'] = str(modern_directory)
            # All literal module construction is inside this selector's
            # certified reservation, before setUp and after its durable start.
            for name in row['test_module_dependencies']:
                load_literal_module(name)
            for module in modules.values():
                if hasattr(module, 'EVIDENCE_DIRECTORY'):
                    module.EVIDENCE_DIRECTORY = str(legacy_directory)
                if hasattr(module, 'NATIVE_CURRENT_SELECTOR'):
                    module.NATIVE_CURRENT_SELECTOR = capture.current
                if hasattr(module, 'CURRENT_PRODUCTION_SELECTOR'):
                    module.CURRENT_PRODUCTION_SELECTOR = capture.current
            path, qualified = row['selector'].split(':', 1)
            class_name, method_name = qualified.split('.', 1)
            test = getattr(modules[path], class_name)(method_name)
            class Result(unittest.TextTestResult):
                def addError(self, test, err):
                    capture.fail(err[1], 'unittest_setup_body_or_cleanup')
                    super().addError(test, err)
                def addFailure(self, test, err):
                    capture.fail(err[1], 'unittest_assertion')
                    super().addFailure(test, err)
                def addSubTest(self, test, subtest, err):
                    if err is not None:
                        capture.fail(err[1], 'unittest_subtest')
                    capture.observe('success' if err is None else 'failure', str(subtest))
                    super().addSubTest(test, subtest, err)
            result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=Result).run(test)
            status = 'passed' if result.wasSuccessful() and not result.skipped else 'failed'
            if not capture.observations:
                capture.observe('success' if status == 'passed' else 'failure', 'fixed whole-method outcome')
            capture.end(status)
        capture.check_time()
    except BaseException as caught:
        capture.fail(caught, 'case_or_schedule')
        # Never repeat a full scan/hash/fsync pass after a failed scan or an
        # exhausted one-shot deadline. Original files already remain owned.
        if capture.current is not None and not capture.collect_attempted and NOW() < capture.deadline:
            try:
                capture.collect()
            except BaseException as capture_error:
                capture.fail(capture_error, 'failure_reconciliation')
    finally:
        os.write = OS_WRITE
        tempfile.TemporaryDirectory = ORIGINAL_TEMPORARY_DIRECTORY
        sys.stdout, sys.stderr = original_stdout, original_stderr
        try:
            log.durable()
        except BaseException as log_error:
            capture.fail(log_error, 'log_finalization', 'native_log_durability_unconfirmed')
        if log.overflow:
            capture.fail(BatchStopped('native stdout/stderr allowance exhausted', 'resource_incomplete'),
                         'log_finalization')
        if log.write_failure:
            capture.fail(BatchStopped('native log capture is incomplete'), 'log_finalization')
        capture.merge_failure(log.failure)
    stopped = capture.failure
    if stopped is not None:
        stopped['active_reservation_retained'] = capture.active_prefix_reservation
    success = stopped is None and len(capture.method_results) == 397 and all(
        row['status'] == 'passed' for row in capture.method_results)
    counters = {path: {key: getattr(module, key) for key in (
        'STUB_CALLS', 'STUB_PROCESS_STARTS', 'STUB_SUPERVISOR_INVOCATIONS', 'STUB_MOCKED_PROCESS_STARTS')
        if hasattr(module, key)} for path, module in modules.items()}
    receipt = {'schema': 'worker38-fixed-preparation-receipt-v1', 'success': success,
        'success_scope': 'observed_method_outcomes_and_local_publication_only',
        'acceptance_requires_original_outer_command_exit_zero': True,
        'no_full_pass_on_timeout_or_unknown_outer_exit': True,
        'status': 'execution_complete' if success else (stopped or {}).get('status', 'execution_incomplete'),
        'fixed_map_sha256': expected, 'testsRun': len(capture.started_selectors),
        'completed_methods': len(capture.method_results),
        'passed_methods': sum(x['status'] == 'passed' for x in capture.method_results),
        'planned_prefix_completed': len(capture.method_results) == plan['certified_fixed_prefix_methods'] and
            all(x['status'] == 'passed' for x in capture.method_results),
        'unexecuted_methods': 397 - len(capture.started_selectors),
        'unexecuted_suffix_first_ordinal': len(capture.started_selectors) + 1 if len(capture.started_selectors) < 397 else None,
        'failures': sum(x['status'] == 'failed' for x in capture.method_results),
        'errors': int(stopped is not None), 'stopped': stopped, 'elapsed_seconds': NOW() - started,
        'native_executable': sys.executable, 'native_version': sys.version, 'native_argv': sys.orig_argv,
        'native_pid': GETPID(), 'address_space': list(GETRLIMIT(resource.RLIMIT_AS)),
        'log_bytes': log.size, 'log_bytes_complete': log.size_complete,
        'produced_prefix_bytes_before_receipt': capture.prefix_bytes(),
        'settled_prefix_bytes': capture.settled_prefix_bytes,
        'active_prefix_reservation_bytes': capture.active_prefix_reservation,
        'global_reserve_bytes': GLOBAL_RESERVE,
        'active_case_bytes_are_complete': capture.current is None,
        'literal_counters': counters, 'candidate_evaluator_calls': 0, 'reference_evaluator_calls': 0,
        'games': 0, 'measurement_fixture_constructions': 0, 'historical_source_imports': 0,
        'checked_file_sha256': {**{name: info['sha256'] for name, info in plan['source_files'].items()},
                                'evidence-design/worker38-fixed-fixtures.json': expected}}
    # These two exclusive slots are the only final publication. Their cost is
    # inside the original64KiB reserve and original600-second deadline.
    capture.write_global('index.json', {'schema': 'worker38-native-index-v1',
        'fixed_map_sha256': expected, 'settled_case_inventories': capture.inventory_index})
    capture.write_global('receipt.json', receipt)
    if NOW() >= capture.deadline:
        return 1
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
