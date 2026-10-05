"""Exactly64 registered consumer methods:8 Bash-inert,56 Python-mocked.

No live network, historical import, constructor or evaluator execution. These
literal cases are inert until the independently approved397-method batch runs.
"""
from contextlib import ExitStack, contextmanager
import ast
import copy
import http.client
import importlib.abc
import json
import io
import resource
import stat
import os
from pathlib import Path
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from worker38 import admission as a, common as c, sources, driver as d, supervision
import worker_bootstrap_shared as shared
from worker38_literal_fixtures import (literal_bundle, write_literal_bundle, CREDENTIAL, HEAD, TREE,
    OTHER_HEAD, OTHER_TREE, FIXED_INPUTS, LIBRARY_PIN, INITIAL_MODULES, INHERITED_LIMITS)

PREFIX_BYTES = 0
# The fixed native runner owns capture before cleanup; routine CI leaves None.
PRODUCTION_OUTPUT_HOOK = None
NATIVE_BATCH_DEADLINE_MONOTONIC = None
# Closed first33 admission expectations: code, classification, phase, GETs.
A_ACCEPTANCE = {
    'test_A01_seven_json_success': (None, None, None, 7),
    'test_A02_wrong_event_owner': ('owner_identity', 'integrity_invalid', 'admission', 0),
    'test_A03_current_body_digest_drift': ('current_pr_body_drift', 'integrity_invalid', 'input_validation', 1),
    'test_A04_current_PR_head_drift': ('pr_head', 'integrity_invalid', 'input_validation', 1),
    'test_A05_accepted_base_CI_mismatch': ('ci_run_scope', 'integrity_invalid', 'input_validation', 2),
    'test_A06_routine_CI_wrong_event': ('ci_run_scope', 'integrity_invalid', 'input_validation', 3),
    'test_A07_routine_CI_circular_run': ('circular_source_ci', 'integrity_invalid', 'admission', 0),
    'test_A08_routine_CI_wrong_workflow': ('ci_run_scope', 'integrity_invalid', 'input_validation', 3),
    'test_A09_routine_CI_failed': ('ci_run_scope', 'integrity_invalid', 'input_validation', 3),
    'test_A10_duplicate_review_identity': ('review_independence', 'integrity_invalid', 'admission', 0),
    'test_A11_review_author_mismatch': ('owner_identity', 'integrity_invalid', 'input_validation', 4),
    'test_A12_review_body_hash_mismatch': ('review_body_hash', 'integrity_invalid', 'input_validation', 4),
    'test_A13_preregistration_wrong_thread': ('comment_identity', 'integrity_invalid', 'input_validation', 6),
    'test_A14_preregistration_body_mismatch': ('preregistration_body_hash', 'integrity_invalid', 'input_validation', 6),
    'test_A15_Git_commit_tree_mismatch': ('diagnostic_commit_tree', 'integrity_invalid', 'input_validation', 7),
    'test_A16_HTTP_redirect_rejected': ('http_redirect', 'execution_blocked', 'network_read', 1),
    'test_A17_duplicate_JSON_key': ('duplicate_json_key', 'integrity_invalid', 'input_validation', 1),
    'test_A18_nonfinite_decimal_JSON': ('nonfinite_json', 'integrity_invalid', 'input_validation', 1),
}
BASH_OBSERVATIONS = []
H_SUBCASES = {'H01': 1, 'H02': 2, 'H03': 5, 'H04': 2, 'H05': 1, 'H06': 1, 'H07': 1,
    'H08': 1, 'H09': 1, 'H10': 2, 'H11': 4, 'H12': 2, 'H13': 8, 'H14': 6, 'H15': 6, 'H16': 3}


class Response:
    def __init__(self, raw, status=200, headers=None, *, tail=None, close_error=None):
        self.raw, self.status = raw, status
        self.headers = {'Content-Length': str(len(raw))} if headers is None else headers
        self.position, self.tail, self.close_error, self.closed = 0, tail, close_error, False
        self.read_sizes = []

    def read(self, count):
        if not 0 < count <= 65536:
            raise AssertionError('unbounded admission read')
        self.read_sizes.append(count)
        if self.position < len(self.raw):
            result = self.raw[self.position:self.position + count]
            self.position += len(result)
            return result
        if self.tail is not None:
            error, self.tail = self.tail, None
            raise error
        return b''

    def close(self):
        if self.close_error is not None:
            raise self.close_error
        self.closed = True


def deny_network(*args, **kwargs):
    raise AssertionError('live network is not an admitted literal operation')


class ScienceGuard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('bandido_alcatraz', 'worker36')) or fullname in (
                'benchmark_worker35_synthetic', 'worker35_resources', 'run_quota_reserve_closure_development'):
            raise AssertionError('historical scientific import is outside literal preparation')
        return None


class Worker38BootstrapIntegration(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        guard = ScienceGuard()
        sys.meta_path.insert(0, guard)
        self.addCleanup(sys.meta_path.remove, guard)
        self.stack.enter_context(patch.object(socket.socket, 'connect', deny_network))
        self.stack.enter_context(patch.object(socket, 'create_connection', deny_network))
        self.stack.enter_context(patch.object(socket, 'getaddrinfo', deny_network))
        self.temporary = tempfile.TemporaryDirectory(prefix='worker38-fixed-case-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bundle = literal_bundle()
        self.subcase = 0

    def watch_production(self, root, *, produced_paths=(), produced_subtrees=(), lineage):
        """Closed fixture output roster captured before any registered cleanup."""
        root = Path(root)
        setup = {}
        if root.exists():
            for path in sorted(root.rglob('*')):
                if path.is_file() and not path.is_symlink():
                    raw = path.read_bytes()
                    setup[path.relative_to(root).as_posix()] = {
                        'size_bytes': len(raw), 'sha256': a.sha(raw),
                        'mode': stat.S_IMODE(path.stat().st_mode)}
        record = {'root': str(root), 'setup_inventory': setup,
            'setup_inventory_sha256': a.sha(a.canonical(setup)),
            'explicit_produced_paths': list(produced_paths),
            'explicit_produced_subtrees': list(produced_subtrees),
            'all_new_paths_are_output': True, 'mutation_lineage': lineage,
            'partial_staging_policy': 'retain every surviving partial, temporary and staging file'}
        self.addCleanup(self.capture_production, record)
        return record

    def capture_production(self, record):
        if PRODUCTION_OUTPUT_HOOK is None:
            return
        root = Path(record['root'])
        produced = []
        partial = []
        if root.exists():
            for path in sorted(root.rglob('*')):
                if not path.is_file() or path.is_symlink():
                    continue
                name = path.relative_to(root).as_posix()
                explicit = name in record['explicit_produced_paths'] or any(
                    name == prefix or name.startswith(prefix.rstrip('/') + '/')
                    for prefix in record['explicit_produced_subtrees'])
                if explicit or name not in record['setup_inventory']:
                    produced.append(name)
                    if any(marker in path.name for marker in ('.tmp', '.partial', '.staging')):
                        partial.append(name)
        record['surviving_produced_paths'] = produced
        record['surviving_partial_staged_paths'] = partial
        PRODUCTION_OUTPUT_HOOK('tests/test_worker38_bootstrap_integration.py:Worker38BootstrapIntegration.' + self._testMethodName, [record])

    def retain(self, files, report, *, existing_paths=None):
        global PREFIX_BYTES
        destination = os.environ.get('WORKER38_LITERAL_EVIDENCE_DIRECTORY')
        self.subcase += 1
        if destination is None:
            return
        root = Path(destination) / self._testMethodName / str(self.subcase)
        root.mkdir(parents=True, exist_ok=False, mode=0o700)
        self.watch_production(root, lineage='Explicit observed evidence generated by this selector; every file is output')
        payloads = dict(files)
        if PRODUCTION_OUTPUT_HOOK is not None and existing_paths:
            report = copy.deepcopy(report)
            report['native_existing_output_paths'] = {}
            for name, path in existing_paths.items():
                path = Path(path)
                if name not in payloads or payloads[name] != path.read_bytes():
                    raise AssertionError('existing output must be explicitly named and byte-identical')
                report['native_existing_output_paths'][name] = str(path)
                del payloads[name]
        payloads['observed-report.json'] = a.canonical(report)
        for name, raw in payloads.items():
            if PREFIX_BYTES + len(raw) > 8388608:
                raise AssertionError('fixed new64 prefix budget exceeded')
            with (root / name).open('xb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            PREFIX_BYTES += len(raw)

    def pipeline(self, bundle=None, responses=None, *, fault=None, expect_failure=False):
        bundle = bundle or self.bundle
        claimed = self.root / ('consumed-' + str(self.subcase))
        claimed.mkdir(mode=0o700, exist_ok=False)
        reservation_raw = ('schema=worker38-observed-reservation-v1\nallocation_id=' + a.ALLOCATION +
            '\nrun_id=501\nrun_attempt=1\nobserved_head=' + HEAD +
            '\ndescriptor_binding=not_yet_validated\nevaluator_starts=0\nscientific_classification=null\n').encode()
        reservation = claimed / 'reservation.txt'
        reservation.write_bytes(reservation_raw)
        output = claimed / 'admission-inputs'
        output.mkdir(mode=0o700)
        output_record = self.watch_production(claimed, produced_subtrees=('admission-inputs',),
            lineage='One invented consumed reservation input; actual seven-input client writes and partial persistence are outputs')
        evidence = a.Evidence(output)
        evidence.open()
        report = a.new_report()
        responses = responses or [Response(bundle['inputs'][name]) for name in FIXED_INPUTS]
        requests = []
        def open_response(opener, request, timeout):
            index = len(requests)
            requests.append((request.full_url, request.get_method(), timeout, dict(request.header_items())))
            if index >= len(responses):
                raise AssertionError('unplanned GET')
            response = responses[index]
            if isinstance(response, BaseException):
                raise response
            return response
        caught = None
        try:
            try:
                with ExitStack() as stack:
                    stack.enter_context(patch.object(a.time, 'clock_gettime_ns', return_value=1000000000))
                    stack.enter_context(patch.object(a.time, 'monotonic', return_value=120.0))
                    stack.enter_context(patch.object(a.urllib.request.OpenerDirector, 'open', open_response))
                    stack.enter_context(patch.dict(os.environ, {}, clear=True))
                    if fault is not None:
                        fault(stack, evidence)
                    go, raw, body = a.descriptor_from_body(bundle['event']['pull_request']['body'])
                    a.validate_event(bundle['event'], go, body, bundle['context'])
                    client = a.Client(evidence, CREDENTIAL, 91000000000, report)
                    try:
                        result = client.inputs(go, body, bundle['event'], bundle['context'])
                    finally:
                        client.token = None
                    self.assertEqual(tuple(result), FIXED_INPUTS)
                    self.assertEqual(a.reconcile(a.canonical(bundle['event']), a.canonical(bundle['context']), result)[0], raw)
            except (a.AdmissionError, OSError, MemoryError) as error:
                caught = error
                if report['primary_failure'] is None:
                    a.record_failure(report, error, 'admission')
            finally:
                evidence.close()
            files = {p.name: p.read_bytes() for p in output.iterdir() if p.is_file()}
            self.assertEqual(reservation.read_bytes(), reservation_raw)
            self.assertEqual(sorted(path.name for path in claimed.iterdir()), ['admission-inputs', 'reservation.txt'])
            self.retain({**files, 'consumed-reservation.txt': reservation_raw}, report,
                existing_paths={name: output / name for name in files})
        except BaseException as retention_error:
            expected = A_ACCEPTANCE.get(self._testMethodName)
            intended_rejection = (expected is not None and type(caught) is a.AdmissionError and
                (caught.code, caught.classification, (report['primary_failure'] or {}).get('phase'), len(requests)) == expected)
            if expected is not None and caught is not None and not intended_rejection:
                try:
                    caught.worker38_prefix_retention_exception = retention_error
                    caught.add_note('admission prefix retention also failed: ' + type(retention_error).__name__[:64])
                except BaseException:
                    pass  # Secondary reporting cannot erase the first typed cause.
                raise caught from None
            raise
        self.check_A_acceptance(caught, report, requests, expect_failure)
        self.assertEqual(caught is not None, expect_failure)
        self.assertNotIn(CREDENTIAL, a.canonical(report).decode())
        self.assertLessEqual(len(requests), 7)
        return types.SimpleNamespace(report=report, requests=requests, files=files, error=caught, evidence=evidence, output_record=output_record)

    def check_A_acceptance(self, caught, report, requests, expect_failure):
        expected = A_ACCEPTANCE.get(self._testMethodName)
        if expected is None:
            return  # The later fixed H/other intentional faults keep their own intent.
        code, classification, phase, count = expected
        self.assertEqual(expect_failure, code is not None)
        if caught is not None and (type(caught) is not a.AdmissionError or
                (caught.code, caught.classification) != (code, classification)):
            raise caught  # Preserve unexpected native/resource exceptions as failures.
        if report['secondary_failures']:
            secondary = report['secondary_failures'][0]
            raise a.AdmissionError(secondary['code'], secondary['classification']) from caught
        if code is None:
            self.assertIsNone(caught)
            self.assertIsNone(report['primary_failure'])
        else:
            self.assertIsNotNone(caught, 'intended admission rejection was not reached')
            self.assertEqual((report['primary_failure']['code'], report['primary_failure']['classification'],
                report['primary_failure']['phase'], report['primary_failure']['error_type']),
                (code, classification, phase, 'AdmissionError'))
            self.assertEqual(report['classification'], classification)
            self.assertEqual(report['selected_failure'], report['primary_failure'])
        self.assertEqual(len(requests), count)
        self.assertTrue(all(request[1] == 'GET' for request in requests))
        self.assertEqual(report['requested_prefix'], list(FIXED_INPUTS[:count]))
        self.assertEqual([record['name'] for record in report['requests']], list(FIXED_INPUTS[:count]))
        completed = count if code is None else (count - 1 if phase == 'input_validation' else 0)
        self.assertEqual(report['completed_prefix'], list(FIXED_INPUTS[:completed]))
        self.assertEqual([record['semantic_validated'] for record in report['requests']],
                         [index < completed for index in range(count)])
        self.assertTrue(all(record['close_confirmed'] is True for record in report['requests']))
        self.assertEqual(report['evaluator_starts'], 0)

    def mutate_input(self, name, mutate):
        bundle = copy.deepcopy(self.bundle)
        value = a.strict_json(bundle['inputs'][name])
        mutate(value)
        bundle['inputs'][name] = a.canonical(value)
        return bundle

    def negative_input(self, name, mutate):
        result = self.pipeline(self.mutate_input(name, mutate), expect_failure=True)
        self.assertLessEqual(len(result.requests), FIXED_INPUTS.index(name) + 1)
        self.assertEqual(result.report['evaluator_starts'], 0)
        return result

    def rebuild_descriptor(self, bundle):
        raw = a.canonical(bundle['go'])
        body = a.START + '\n' + raw.decode() + a.END + '\n' + a.DIGEST + ': ' + a.sha(raw) + '\n'
        bundle['event']['pull_request']['body'] = body
        pr = a.strict_json(bundle['inputs']['pull-request.json'])
        pr['body'] = body
        bundle['inputs']['pull-request.json'] = a.canonical(pr)
        return bundle

    def test_S01_legacy_shared_path(self):
        import test_worker37_bootstrap as legacy
        original_popen = subprocess.Popen
        def bounded_popen(*args, **kwargs):
            process = original_popen(*args, **kwargs)
            communicate = process.communicate
            def bounded_communicate(*args, **kwargs):
                kwargs['timeout'] = 5
                try:
                    return communicate(*args, **kwargs)
                except subprocess.TimeoutExpired:
                    process.kill()
                    communicate(timeout=5)
                    raise
            process.communicate = bounded_communicate
            return process
        with patch.object(legacy, 'CURRENT_CASE_ID', 'W38-S01'), patch.object(legacy.subprocess, 'Popen', side_effect=bounded_popen):
            result = legacy.run_bash('S01', entry='launcher')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.commands.count('python3.11'), 1)
        self.assertFalse(result.old_namespace_access)
        self.assertIn('bootstrap_worker37_prepare', (ROOT / 'scripts/worker37-bootstrap.sh').read_text())

    def test_S02_new_closed_shared_path(self):
        result = self.bash_case('S02')
        self.assertEqual(result['entries'], ['admission', 'measure'])
        self.assertEqual(result['science_calls'], 0)
        workflow = (ROOT / '.github/workflows/worker38-synthetic-profile.yml').read_text()
        composite = (ROOT / '.github/actions/worker38-upload/action.yml').read_text()
        shell = (ROOT / 'scripts/worker_bootstrap_shared.sh').read_text()
        adopted = a.strict_json((ROOT / a.EXPERIMENT / 'upload-amendment/AMENDMENT-CONTRACT.json').read_bytes())
        self.assertEqual(tuple(adopted['production_source_paths']), a.REQUIRED_PRODUCTION_PATHS)
        self.assertEqual(len(a.REQUIRED_PRODUCTION_PATHS), 17)
        self.assertEqual(workflow.count('uses: ./.github/actions/worker38-upload'), 1)
        caller = workflow.split('uses: ./.github/actions/worker38-upload', 1)[1]
        self.assertIn('timeout-minutes: 1', caller)
        self.assertEqual(workflow.count('    timeout-minutes: 45'), 1)
        self.assertIn('  using: composite', composite)
        self.assertNotIn('inputs:', composite)
        self.assertNotIn('always()', composite)
        self.assertNotIn('continue-on-error', composite)
        action = 'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02'
        self.assertEqual(composite.count(action), 3)
        pieces = composite.split('uses: ' + action)
        for ordinal, prefix in enumerate(pieces[:-1], 1):
            self.assertIn('_bootstrap_worker38_upload_guard ' + str(ordinal), prefix)
        self.assertEqual(composite.count('outputs.manifest_path'), 1)
        self.assertEqual(composite.count('outputs.part_path'), 3)
        prepare = shell.split('bootstrap_worker38_prepare() {', 1)[1].split('\n}', 1)[0]
        self.assertLess(prepare.index('_bootstrap_worker38_upload_eligibility'), prepare.index('_bootstrap_paths_and_claim'))
        for literal in ('^/[A-Za-z0-9._/-]+$', '-d', '-f', '-L', '-O', '-r', '-w', '4097'):
            self.assertIn(literal, shell)
        for name, pin in a.UPLOAD_RECORD_PINS.items():
            self.assertEqual(a.sha((ROOT / name).read_bytes()), pin)

    def test_S03_shell_extra_argument(self):
        result = self.bash_case('S03', extra=True)
        self.assertNotEqual(result['returncode'], 0)
        self.assertEqual(result['commands'], [])
        self.assertEqual(result['entries'], [])

    def test_S04_python_unknown_consumer(self):
        with patch.object(shared.resource, 'setrlimit') as change:
            with self.assertRaises(shared.RuntimeFailure):
                shared.runtime_start({}, 'unknown-consumer-v1')
        change.assert_not_called()

    def test_S05_fresh_shell_sanitation(self):
        result = self.bash_case('S05', contaminated=True)
        self.assertEqual(result['entries'], ['admission', 'measure'])
        self.assertFalse(result['inherited_loader_seen'])

    def test_S06_occupied_new_allocation(self):
        result = self.bash_case('S06', occupied=True)
        self.assertNotEqual(result['returncode'], 0)
        self.assertTrue(result['reservation_preserved'])
        self.assertEqual(result['entries'], [])
        self.assertFalse(result['old_namespace_access'])

    def test_S07_forbidden_old_namespace(self):
        bundle = copy.deepcopy(self.bundle)
        bundle['context']['attempt_path'] = '/invented-cache/worker37-bootstrap-readiness/allocations/worker37-bootstrap-readiness-01/run-501-attempt-1'
        with patch.object(a.os, 'open') as opened:
            with self.assertRaisesRegex(a.AdmissionError, 'new_namespace_only'):
                a.validate_context(bundle['context'], bundle['go'])
        opened.assert_not_called()

    def test_S08_changed_descriptor_same_allocation(self):
        result = self.bash_case('S08', occupied=True, changed=True)
        self.assertTrue(result['reservation_preserved'])
        self.assertEqual(result['entries'], [])
        self.assertFalse(result['old_namespace_access'])

    def test_S09_symlinked_attempt_root(self):
        actual = self.root / 'actual'
        actual.mkdir(mode=0o700)
        link = self.root / 'attempt'
        link.symlink_to(actual, target_is_directory=True)
        with self.assertRaises(a.AdmissionError):
            a.Evidence(link).open()
        self.assertEqual(list(actual.iterdir()), [])

    def test_S10_outer_startup_120_expiry(self):
        values = {'WORKER38_STARTUP_BOOTTIME_NS': '1000000000',
            'WORKER38_STARTUP_DEADLINE_BOOTTIME_NS': '121000000000',
            'WORKER38_ADMISSION_DEADLINE_BOOTTIME_NS': '121000000000'}
        with patch.dict(os.environ, values), patch.object(a.time, 'clock_gettime_ns', return_value=121000000000):
            with self.assertRaises(a.AdmissionError) as caught:
                a.startup_deadline()
        self.assertEqual(caught.exception.classification, 'resource_incomplete')

    def test_S11_shell_30_wall_expiry(self):
        source = (ROOT / 'scripts/worker38-bootstrap.sh').read_text()
        self.assertIn('timeout --signal=KILL 30s', source)
        self.assertIn('shared_shell_deadline', source)
        with patch.object(a.time, 'clock_gettime_ns', return_value=31000000000):
            with self.assertRaises(a.AdmissionError) as caught:
                a.check_deadline(31000000000, 'shared_shell_deadline')
        self.assertEqual(caught.exception.classification, 'resource_incomplete')

    def test_S12_admission_90_nested_expiry(self):
        values = {'WORKER38_STARTUP_BOOTTIME_NS': '1000000000',
            'WORKER38_STARTUP_DEADLINE_BOOTTIME_NS': '121000000000',
            'WORKER38_ADMISSION_DEADLINE_BOOTTIME_NS': '91000000000'}
        with patch.dict(os.environ, values), patch.object(a.time, 'clock_gettime_ns', return_value=91000000000):
            with self.assertRaises(a.AdmissionError) as caught:
                a.startup_deadline()
        self.assertEqual(caught.exception.classification, 'resource_incomplete')

    def test_A01_seven_json_success(self):
        result = self.pipeline()
        self.assertEqual(len(result.requests), 7)
        self.assertEqual(result.report['completed_prefix'], list(FIXED_INPUTS))
        self.assertEqual([request[0] for request in result.requests], [a.API + path for _, path in a.request_map(self.bundle['go'])])

    def test_A02_wrong_event_owner(self):
        self.bundle['event']['sender']['login'] = 'invented-nonowner'
        result = self.pipeline(expect_failure=True)
        self.assertEqual(result.requests, [])

    def test_A03_current_body_digest_drift(self):
        self.negative_input('pull-request.json', lambda v: v.update(body=v['body'] + ' '))

    def test_A04_current_PR_head_drift(self):
        self.negative_input('pull-request.json', lambda v: v['head'].update(sha=OTHER_HEAD))

    def test_A05_accepted_base_CI_mismatch(self):
        self.negative_input('postmerge-ci.json', lambda v: v.update(head_sha=OTHER_HEAD))

    def test_A06_routine_CI_wrong_event(self):
        self.negative_input('current-source-ci.json', lambda v: v.update(event='workflow_dispatch'))

    def test_A07_routine_CI_circular_run(self):
        self.bundle['context']['workflow_run'] = '401'
        self.bundle['context']['attempt_id'] = 'worker38-401-1'
        self.bundle['context']['attempt_path'] = self.bundle['context']['attempt_path'].replace('run-501-', 'run-401-')
        result = self.pipeline(expect_failure=True)
        self.assertEqual(result.requests, [])

    def test_A08_routine_CI_wrong_workflow(self):
        self.negative_input('current-source-ci.json', lambda v: v.update(path='.github/workflows/other.yml'))

    def test_A09_routine_CI_failed(self):
        self.negative_input('current-source-ci.json', lambda v: v.update(conclusion='failure'))

    def test_A10_duplicate_review_identity(self):
        self.bundle['go']['reviews'][1]['native_reviewer_id'] = self.bundle['go']['reviews'][0]['native_reviewer_id']
        result = self.pipeline(self.rebuild_descriptor(self.bundle), expect_failure=True)
        self.assertEqual(result.requests, [])

    def test_A11_review_author_mismatch(self):
        self.negative_input('review-exhaustive.json', lambda v: v['user'].update(login='invented-nonowner'))

    def test_A12_review_body_hash_mismatch(self):
        self.negative_input('review-exhaustive.json', lambda v: v.update(body=v['body'] + ' '))

    def test_A13_preregistration_wrong_thread(self):
        self.negative_input('preregistration.json', lambda v: v.update(issue_url=a.API + '/issues/3'))

    def test_A14_preregistration_body_mismatch(self):
        self.negative_input('preregistration.json', lambda v: v.update(body=v['body'] + 'changed'))

    def test_A15_Git_commit_tree_mismatch(self):
        self.negative_input('diagnostic-commit.json', lambda v: v['tree'].update(sha=OTHER_TREE))

    def test_A16_HTTP_redirect_rejected(self):
        result = self.pipeline(responses=[Response(b'signed location omitted', 302,
            {'Location': 'https://invalid.example/?signature=literal'})], expect_failure=True)
        self.assertEqual(len(result.requests), 1)
        self.assertEqual(result.files, {})
        self.assertNotIn('signature', a.canonical(result.report).decode())

    def test_A17_duplicate_JSON_key(self):
        self.bundle['inputs']['pull-request.json'] = b'{"number":101,"number":101}\n'
        result = self.pipeline(expect_failure=True)
        self.assertEqual(result.report['primary_failure']['code'], 'duplicate_json_key')

    def test_A18_nonfinite_decimal_JSON(self):
        self.bundle['inputs']['pull-request.json'] = b'{"number":1e999}\n'
        result = self.pipeline(expect_failure=True)
        self.assertEqual(result.report['primary_failure']['code'], 'nonfinite_json')

    def test_C01_credential_free_exec_environment(self):
        result = self.bash_case('C01', contaminated=True)
        self.assertEqual(result['entries'], ['admission', 'measure'])
        self.assertFalse(result['science_secret_seen'])
        self.assertTrue(result['science_allowlist_checked'])

    def test_C02_credential_file_descriptors_closed(self):
        result = self.bash_case('C02', credential_fd=True)
        self.assertEqual(result['entries'], ['admission', 'measure'])
        self.assertFalse(result['science_fd_seen'])

    def test_C03_credential_contaminated_handoff(self):
        value = self.handoff()
        value['GH_TOKEN'] = CREDENTIAL
        with self.assertRaises(a.AdmissionError) as caught:
            a.validate_handoff(value)
        self.assertNotIn(CREDENTIAL, str(caught.exception))

    def test_C04_admission_failure_blocks_exec(self):
        response = Response(b'{"prefix', tail=OSError('literal interruption'), headers={})
        result = self.pipeline(responses=[response], expect_failure=True)
        self.assertEqual(result.files['pull-request.json'], b'{"prefix')
        self.assertFalse(result.report['admission_verified'])
        self.assertNotIn('measurement-handoff.txt', result.files)
        outcome = self.failure_preservation(existing=result)
        self.assertEqual(outcome['result'], 2)
        self.assertTrue((outcome['transport'] / 'upload-plan.txt').is_file())
        self.assertEqual(outcome['handoff']['actual_entry_upper_bound'], 0)

    def test_C05_torn_admission_handoff(self):
        (self.root / 'startup-handoff.json.tmp').write_bytes(b'{torn')
        with self.assertRaises(c.IntegrityError):
            d.read_startup_handoff(self.root, 'a' * 64, 'b' * 64)
        self.assertEqual((self.root / 'startup-handoff.json.tmp').read_bytes(), b'{torn')

    def test_C06_committed_handoff_tamper(self):
        raw = a.canonical(self.handoff())
        path = self.root / 'startup-handoff.json'
        path.write_bytes(raw + b' ')
        with patch.dict(os.environ, {'WORKER38_HANDOFF_SHA256': a.sha(raw)}):
            with self.assertRaises(c.IntegrityError) as caught:
                d.read_startup_handoff(self.root, 'a' * 64, 'b' * 64)
        report = a.new_report()
        a.record_failure(report, caught.exception, 'handoff')
        a.record_failure(report, OSError('write failed'), 'terminal_persistence')
        self.assertEqual(report['classification'], 'integrity_invalid')

    def test_C07_inert_blob_digest_drift(self):
        entry = {'size_bytes': len(b'INVENTED_SOURCE_BYTES_ONLY\n'), 'sha256': 'a' * 64, 'git_blob': 'a' * 40}
        with self.assertRaises(c.IntegrityError):
            sources.verify_blob(b'INVENTED_SOURCE_BYTES_ONLY\n', entry)

    def test_C08_closure_inventory_missing_file(self):
        staging = self.root / 'experiments/worker38-synthetic-profile/inputs/comparator-7ac2f62c'
        staging.mkdir(parents=True)
        entries = [{'path': 'src/literal_' + str(i) + '.py', 'module': 'literal_' + str(i),
            'size_bytes': 1, 'sha256': 'a' * 64, 'git_blob': 'a' * 40} for i in range(21)]
        for entry in entries[:20]:
            path = staging / (entry['path'] + '.blob')
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(b'x')
        self.watch_production(self.root, produced_subtrees=('restored',),
            lineage='Twenty fixed one-byte incomplete source inputs; actual restore rejects before creating output')
        with self.assertRaises(c.IntegrityError):
            sources.restore_staged(self.root, self.root / 'restored', {'files': entries}, c.Budget(self.root))
        self.assertFalse((self.root / 'restored').exists())

    def test_C09_new_runtime_drift_before_import(self):
        with self.runtime_observations() as state:
            state['library_drift'] = True
            with self.assertRaises((c.IntegrityError, shared.RuntimeFailure)):
                d.enter_measurement_runtime(1900.0)
            self.assertEqual(state['historical_imports'], 0)

    def test_C10_constructor_span_static_only(self):
        raw = (ROOT / 'tests/worker38_constructor_source.txt').read_bytes()
        nodes = sources.fixture_ast(raw)
        self.assertEqual(len(nodes), 19)
        with patch.object(sources, 'construct_fixture', side_effect=AssertionError('constructor called')):
            for node in nodes:
                self.assertIsInstance(node, ast.AST)
            self.assertTrue(all(sources.constructor_ast_bytes(node) for node in nodes))

    def test_F01_startup_failure_preservation_anchor(self):
        outcome = self.failure_preservation(expire=True)
        self.assertEqual(outcome['first_failure'], 120.0)
        self.assertEqual(outcome['deadline'], 720.0)
        self.assertEqual(outcome['result'], 1)
        self.assertFalse(outcome['transport'].exists())
        self.assertEqual(outcome['handoff']['preservation_deadline_monotonic_ns'], 720000000000)

    def test_F02_primary_integrity_then_resource(self):
        outcome = self.failure_preservation(unknown_close=True)
        self.assertEqual(outcome['report']['classification'], 'integrity_invalid')
        self.assertEqual(outcome['report']['primary_failure']['code'], 'integrity')
        self.assertEqual([row['phase'] for row in outcome['report']['secondary_failures']], ['persistence', 'close'])
        self.assertFalse(outcome['handoff_path'].exists())
        self.assertEqual(outcome['deadline'], 720.0)
        self.assertFalse(outcome['transport'].exists())

    def test_F03_measurement_outside_120_timer(self):
        for mutation in ('valid', 'foreign_timer', 'library_drift', 'handler_drift'):
            with self.subTest(mutation=mutation), self.runtime_observations() as state:
                if mutation == 'foreign_timer':
                    state['timers'][signal.ITIMER_REAL] = (25.0, 0.0)
                    with self.assertRaises((c.IntegrityError, shared.RuntimeFailure)):
                        d.enter_measurement_runtime(1900.0)
                    self.assertEqual(state['timers'][signal.ITIMER_REAL], (25.0, 0.0))
                    self.assertEqual(state['arms'], [])
                    continue
                runtime, scope = d.enter_measurement_runtime(1900.0)
                self.assertLessEqual(state['arms'][0], 1650.0)
                self.assertEqual(scope.measurement_deadline, 1900.0)
                if mutation == 'library_drift': state['library_drift'] = True
                if mutation == 'handler_drift': state['handlers'][signal.SIGUSR1] = object()
                if mutation == 'valid':
                    scope.check_runtime()
                else:
                    with self.assertRaises((c.IntegrityError, shared.RuntimeFailure)):
                        scope.check_runtime()
                self.assertEqual(scope.close(), [])
                self.assertEqual(state['timers'][signal.ITIMER_REAL], (0.0, 0.0))
                self.assertIs(state['handlers'][signal.SIGUSR1], state['original_usr1'])
                self.assertEqual(state['historical_imports'], 0)

    def test_F04_cell_CPU_backstop_record(self):
        self.parent_death_race()

    def test_F05_first_supervisor_failure_deadline_propagation(self):
        with self.runtime_observations() as state:
            runtime, scope = d.enter_measurement_runtime(1900.0)
            state['now'] = 300.0
            observed = []
            def propagate(value):
                observed.append(value)
                cutoff = value['first_failure_monotonic'] + 600.0
                scope.arm_preservation(cutoff)
                return cutoff
            result = {'status': 'resource_incomplete', 'reason': 'literal_cpu_limit',
                'returncode': None, 'exit_code': None, 'signal': None, 'secondary_failures': []}
            boundary = supervision._FailureBoundary(result, propagate)
            first = c.ResourceExceeded('literal independently observed CPU limit')
            boundary.start(phase='supervisor', status='resource_incomplete', reason='literal_cpu_limit', error=first)
            self.assertEqual(len(observed), 1)
            self.assertEqual(boundary.deadline, 900.0)
            self.assertEqual(scope.preservation_deadline, 900.0)
            original_signal = d.signal.signal
            def fail_restore(kind, value):
                if kind == signal.SIGUSR1 and value is state['original_usr1']:
                    raise OSError('restore failed')
                return original_signal(kind, value)
            with patch.object(d.signal, 'signal', side_effect=fail_restore):
                errors = scope.close()
            selected, secondary = d.reduce_failure(c.error_record(first, 'supervisor'),
                {'actual_starts_upper_bound': 0}, additional=errors)
            self.assertEqual(selected['status'], 'integrity_invalid')
            self.assertTrue(any(error['status'] == 'resource_incomplete' for error in secondary))
            self.assertEqual(boundary.deadline, 900.0)
            self.assertEqual(result['first_terminal_failure']['status'], 'resource_incomplete')

    def test_F06_per_input_overflow_witness(self):
        result = self.pipeline(responses=[Response(b'x' * (a.MAX_INPUT + 1), headers={})], expect_failure=True)
        self.assertEqual(result.report['response_body_bytes'], a.MAX_INPUT + 1)
        self.assertEqual(len(result.files['pull-request.json']), a.MAX_INPUT)
        self.assertEqual(len(result.requests), 1)

    def test_F07_complete_literal_20_cell_orchestration(self):
        self.literal_orchestration(failing=False)

    def test_F08_one_cell_failure_stops_schedule(self):
        self.literal_orchestration(failing=True)

    def test_H01_http_status_failure(self):
        result = self.pipeline(responses=[Response(b'{"error":"denied"}\n', 403)], expect_failure=True)
        self.assertEqual(result.report['primary_failure']['code'], 'http_status')
        self.assertEqual(len(result.requests), 1)
        self.assertEqual(result.report['requests'][0]['status'], 403)

    def test_H02_tls_and_timeout(self):
        for response, received in ((ssl.SSLCertVerificationError('literal certificate error'), 0),
            (Response(b'12345678', headers={}, tail=socket.timeout('literal timeout')), 8)):
            with self.subTest(received=received):
                result = self.pipeline(responses=[response], expect_failure=True)
                self.assertEqual(result.report['response_body_bytes'], received)
                self.assertEqual(len(result.requests), 1)
                self.assertEqual(result.report['primary_failure']['code'], 'transport_failed')
                self.assertEqual(result.report['primary_failure']['error_type'],
                                 'SSLCertVerificationError' if received == 0 else 'TimeoutError')

    def test_H03_content_length(self):
        for declared, raw, code in (('-1', b'12345678', 'content_length'),
            ('nonnumeric', b'12345678', 'content_length'), ('2097153', b'', 'content_length_overflow'),
            ('32', b'12345678', 'response_length_mismatch'), ('8', b'1234567890123456', 'response_length_mismatch')):
            with self.subTest(declared=declared):
                result = self.pipeline(responses=[Response(raw, headers={'Content-Length': declared})], expect_failure=True)
                self.assertEqual(result.report['primary_failure']['code'], code)
                self.assertEqual(len(result.requests), 1)

    def test_H04_content_encoding(self):
        for encoding in ('gzip', 'identity'):
            with self.subTest(encoding=encoding):
                responses = [Response(self.bundle['inputs'][name]) for name in FIXED_INPUTS]
                responses[0] = Response(b'1234567890123456' if encoding == 'gzip' else self.bundle['inputs'][FIXED_INPUTS[0]],
                                        headers={'Content-Encoding': encoding})
                result = self.pipeline(responses=responses, expect_failure=encoding == 'gzip')
                self.assertEqual(len(result.requests), 1 if encoding == 'gzip' else 7)

    def test_H05_exact_body_cap_eof(self):
        responses = [Response(self.bundle['inputs'][name]) for name in FIXED_INPUTS]
        responses[0] = Response(responses[0].raw + b' ' * (a.MAX_INPUT - len(responses[0].raw)))
        result = self.pipeline(responses=responses)
        first = result.report['requests'][0]
        self.assertTrue(first['eof_confirmed'])
        self.assertEqual(first['received_bytes'], a.MAX_INPUT)
        self.assertEqual(first['retained_bytes'], a.MAX_INPUT)
        self.assertEqual(responses[0].read_sizes[-1], 1)

    def test_H06_no_length_eof(self):
        responses = [Response(self.bundle['inputs'][name]) for name in FIXED_INPUTS]
        responses[0].headers = {}
        result = self.pipeline(responses=responses)
        self.assertTrue(result.report['requests'][0]['eof_confirmed'])
        self.assertEqual(len(result.requests), 7)

    def test_H07_partial_close_write_failure(self):
        response = Response(b'', headers={}, tail=http.client.IncompleteRead(b'123456789012', 1),
                            close_error=OSError('literal close'))
        def fault(stack, evidence):
            stack.enter_context(patch.object(evidence, 'write', side_effect=OSError('literal write')))
        result = self.pipeline(responses=[response], fault=fault, expect_failure=True)
        self.assertEqual(result.report['response_body_bytes'], 12)
        self.assertEqual(result.report['primary_failure']['code'], 'response_incomplete_read')
        self.assertEqual([x['phase'] for x in result.report['secondary_failures']], ['response_close', 'input_persistence'])
        self.assertEqual(result.report['requests'][0]['retained_bytes'], 0)

    def test_H08_partial_overflow(self):
        response = Response(b'x' * 2097149, headers={}, tail=http.client.IncompleteRead(b'xxxx', 1),
                            close_error=OSError('literal close'))
        result = self.pipeline(responses=[response], expect_failure=True)
        self.assertEqual(result.report['response_body_bytes'], 2097153)
        self.assertEqual(len(result.files['pull-request.json']), 2097152)
        self.assertEqual(result.report['classification'], 'resource_incomplete')
        self.assertEqual(result.report['secondary_failures'][0]['phase'], 'response_close')

    def test_H09_response_close_after_success(self):
        response = Response(self.bundle['inputs']['pull-request.json'], close_error=OSError('literal close'))
        result = self.pipeline(responses=[response], expect_failure=True)
        self.assertEqual(result.report['primary_failure']['phase'], 'response_close')
        self.assertEqual(result.files['pull-request.json'], response.raw)
        self.assertEqual(result.report['completed_prefix'], [])
        self.assertEqual(len(result.requests), 1)

    def test_H10_short_write(self):
        for first_write in (3, 0):
            with self.subTest(first_write=first_write):
                original_write = a.os.write
                calls = []
                def fault(stack, evidence):
                    def short(fd, raw):
                        calls.append(len(raw))
                        if len(calls) == 1:
                            return original_write(fd, raw[:3]) if first_write else 0
                        return original_write(fd, raw)
                    stack.enter_context(patch.object(a.os, 'write', side_effect=short))
                result = self.pipeline(fault=fault, expect_failure=first_write == 0)
                self.assertEqual(result.report['requests'][0]['retained_bytes'],
                                 len(self.bundle['inputs']['pull-request.json']) if first_write else 0)
                if first_write: self.assertEqual(result.files['pull-request.json'], self.bundle['inputs']['pull-request.json'])

    def test_H11_persistence_boundaries(self):
        for target in ('file_fsync', 'directory_fsync', 'read_permission', 'changed_readback'):
            with self.subTest(target=target):
                def fault(stack, evidence):
                    original_fsync = a.os.fsync
                    if target in ('file_fsync', 'directory_fsync'):
                        def fsync(fd):
                            is_directory = fd == evidence.directory_fd
                            if is_directory == (target == 'directory_fsync'):
                                raise OSError('literal fsync failure')
                            return original_fsync(fd)
                        stack.enter_context(patch.object(a.os, 'fsync', side_effect=fsync))
                    else:
                        stack.enter_context(patch.object(a, 'bounded_read', side_effect=PermissionError('literal denied')
                            if target == 'read_permission' else lambda path, cap: b'changed committed bytes'))
                result = self.pipeline(fault=fault, expect_failure=True)
                self.assertEqual(len(result.requests), 1)
                self.assertEqual(result.report['classification'],
                                 'integrity_invalid' if target == 'changed_readback' else 'execution_incomplete')
                self.assertEqual(result.files['pull-request.json'], self.bundle['inputs']['pull-request.json'])

    def test_H12_active_error_and_close(self):
        for failure in (MemoryError(), OSError('literal read')):
            with self.subTest(kind=type(failure).__name__):
                path = self.root / ('read-' + type(failure).__name__)
                path.write_bytes(b'12345678')
                original_close = a.os.close
                def close(fd):
                    original_close(fd)
                    raise OSError('literal close')
                with patch.object(a.os, 'read', side_effect=failure), patch.object(a.os, 'close', side_effect=close):
                    with self.assertRaises(type(failure)) as caught:
                        a.bounded_read(path)
                report = a.new_report()
                a.record_failure(report, caught.exception, 'bounded_read')
                self.assertEqual(report['classification'], 'resource_incomplete' if isinstance(failure, MemoryError) else 'execution_incomplete')
                self.assertEqual(report['secondary_failures'][0]['phase'], 'descriptor_close')
                self.retain({'bounded-read-input.bin': path.read_bytes()}, report)

    def test_H13_event_owner_destination_first_transition(self):
        for target in ('actor', 'triggering_actor', 'sender', 'author', 'repository', 'branch', 'attempt', 'old_marker'):
            with self.subTest(target=target):
                bundle = copy.deepcopy(self.bundle)
                if target in ('actor', 'triggering_actor'): bundle['context'][target] = 'invented-nonowner'
                elif target == 'sender': bundle['event']['sender']['login'] = 'invented-nonowner'
                elif target == 'author': bundle['event']['pull_request']['user']['login'] = 'invented-nonowner'
                elif target == 'repository': bundle['event']['repository']['full_name'] = 'invented/other'
                elif target == 'branch': bundle['event']['pull_request']['head']['ref'] = 'invented-other'
                elif target == 'attempt': bundle['context']['workflow_attempt'] = '2'
                else: bundle['event']['changes']['body']['from'] = a.MARKER
                result = self.pipeline(bundle, expect_failure=True)
                self.assertEqual(result.requests, [])
        tree = ast.parse((ROOT / 'scripts/worker38/admission.py').read_text())
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(tree)))

    def test_H14_markers_and_descriptor_types(self):
        for target in ('missing_digest', 'duplicate_begin', 'not_admitted', 'boolean_run', 'extra_field', 'bad_hash'):
            with self.subTest(target=target):
                bundle = copy.deepcopy(self.bundle)
                if target == 'missing_digest':
                    bundle['event']['pull_request']['body'] = bundle['event']['pull_request']['body'].split(a.DIGEST)[0]
                elif target == 'duplicate_begin': bundle['event']['pull_request']['body'] += a.START + '\n'
                elif target == 'boolean_run': bundle['context']['workflow_run'] = True
                else:
                    if target == 'not_admitted': bundle['go']['admitted'] = False
                    elif target == 'extra_field': bundle['go']['unknown'] = 'literal'
                    else: bundle['go']['source_manifest_sha256'] = 'bad'
                    self.rebuild_descriptor(bundle)
                result = self.pipeline(bundle, expect_failure=True)
                self.assertEqual(result.requests, [])

    def test_H15_structured_review_evidence(self):
        for target in ('comment_id', 'issue_url', 'duplicate_blocks', 'not_clean', 'same_reviewer', 'bad_report'):
            with self.subTest(target=target):
                bundle = copy.deepcopy(self.bundle)
                value = a.strict_json(bundle['inputs']['review-exhaustive.json'])
                if target == 'comment_id': value['id'] = 604
                elif target == 'issue_url': value['issue_url'] = a.API + '/issues/2'
                elif target == 'duplicate_blocks': value['body'] += value['body']
                else:
                    raw = value['body'][len(a.REVIEW_START) + 1:-(len(a.REVIEW_END) + 1)]
                    review = a.strict_json(raw)
                    if target == 'not_clean': review['verdict'] = 'not_clean'
                    elif target == 'same_reviewer': review['native_reviewer_id'] = bundle['go']['reviews'][1]['native_reviewer_id']
                    else: review['report_sha256'] = 'invalid'
                    value['body'] = a.REVIEW_START + '\n' + a.canonical(review).decode() + a.REVIEW_END + '\n'
                # Refresh byte hashes, retaining independently frozen semantic scope.
                bundle['go']['reviews'][0]['body_sha256'] = a.sha(value['body'].encode())
                bundle['inputs']['review-exhaustive.json'] = a.canonical(value)
                self.rebuild_descriptor(bundle)
                result = self.pipeline(bundle, expect_failure=True)
                self.assertEqual(len(result.requests), 4)

    def test_H16_loader_source_receipt_bindings(self):
        for target in ('loader', 'missing_shared', 'focused_receipt'):
            with self.subTest(target=target):
                source, go, runtime = self.local_sources(target)
                if target == 'loader': runtime['files']['library']['sha256'] = 'd' * 64
                elif target == 'missing_shared':
                    del go['checked_file_sha256']['scripts/worker_bootstrap_shared.py']
                else: (source / go['focused_source_receipt']['path']).write_bytes(b'changed focused receipt\n')
                report = a.new_report()
                with patch.dict(os.environ, {'WORKER38_HEAD': go['head'], 'WORKER38_TREE': go['tree']}):
                    with self.assertRaises(a.AdmissionError) as caught:
                        a.validate_descriptor(go)
                        a.verify_local_sources(source, go, runtime)
                a.record_failure(report, caught.exception, 'source_validation')
                self.assertFalse(report['admission_verified'])
                self.assertEqual(report['evaluator_starts'], 0)
                self.retain({'frozen-descriptor.json': a.canonical(go)}, report)

    def failure_preservation(self, *, expire=False, unknown_close=False, existing=None):
        with self.runtime_observations() as state, ExitStack() as stack:
            state['now'] = 120.0
            runtime = shared.runtime_start({}, a.CONSUMER)
            cache = Path(os.environ['RUNNER_TOOL_CACHE'])
            source = self.root / 'failure-checkout'
            source.mkdir()
            (source / '.git').mkdir(mode=0o700)
            (source / '.git/HEAD').write_bytes((HEAD + '\n').encode())
            root = cache / 'worker38-synthetic-profile/allocations' / a.ALLOCATION / 'run-501-attempt-1'
            for directory in (cache / 'worker38-synthetic-profile', root.parent.parent, root.parent, root):
                directory.mkdir(mode=0o700, parents=True, exist_ok=True)
                directory.chmod(0o700)
            shell_raw = ('version=worker38-shell-runtime-v1\nexecutable_stat=' + os.environ['WORKER38_EXECUTABLE_STAT'] +
                '\nlibrary_stat=' + os.environ['WORKER38_LIBRARY_STAT'] + '\nhead=' + HEAD + '\ntree=' + TREE +
                '\nevent_sha256=' + 'a' * 64 + '\nevent_stat=1:20:3:1\n').encode()
            (root / 'shell-runtime.txt').write_bytes(shell_raw)
            reservation = ('schema=worker38-observed-reservation-v1\nallocation_id=' + a.ALLOCATION +
                '\nrun_id=501\nrun_attempt=1\nobserved_head=' + HEAD +
                '\ndescriptor_binding=not_yet_validated\nevaluator_starts=0\nscientific_classification=null\n').encode()
            (root / 'reservation.txt').write_bytes(reservation)
            (root.parent / 'reservation.txt').write_bytes(reservation)
            self.watch_production(root.parent, produced_subtrees=(root.name + '/admission-inputs',),
                lineage='Fixed reservation and shell-runtime inputs; actual admission failure receipt/handoff, writer observation, reports and package/seal are outputs')
            report = existing.report if existing is not None else a.new_report()
            report['runtime'] = runtime
            evidence = a.Evidence(root); evidence.open()
            scope = a._FailureDeadline(report)
            stack.enter_context(patch.object(a, '_ACTIVE_FAILURE_SCOPE', scope))
            stack.enter_context(patch.dict(os.environ, {'GITHUB_RUN_ID': '501', 'GITHUB_RUN_ATTEMPT': '1',
                'WORKER38_HEAD': HEAD, 'WORKER38_TREE': TREE, 'GITHUB_WORKSPACE': str(source),
                'WORKER38_SOURCE_DIRECTORY': str(source)}))
            original_read = a.bounded_read
            boot_id = '11111111-2222-3333-4444-555555555555'
            stack.enter_context(patch.object(a, 'bounded_read', side_effect=lambda path, cap=a.MAX_INPUT:
                (boot_id + '\n').encode() if str(path) == '/proc/sys/kernel/random/boot_id' else original_read(path, cap)))
            original_text = Path.read_text
            stack.enter_context(patch.object(Path, 'read_text', lambda path, *args, **kwargs:
                boot_id + '\n' if str(path) == '/proc/sys/kernel/random/boot_id' else original_text(path, *args, **kwargs)))
            if existing is None:
                a.record_failure(report, a.AdmissionError('integrity' if unknown_close else 'first',
                    'integrity_invalid' if unknown_close else 'resource_incomplete'), 'startup')
            else:
                existing.evidence.output.rename(root / 'admission-inputs')
                existing.output_record['mutation_lineage'] += '; output subtree moved without copying to ' + str(root / 'admission-inputs')
                scope.arm(report['preservation_deadline_monotonic_ns'])
            if unknown_close:
                a.record_failure(report, MemoryError(), 'persistence')
                a.record_failure(report, OSError('literal unknown descriptor close'), 'close')
            self.assertEqual(scope.close(), [])
            handoff_path = root / 'startup-failure-handoff.json'
            transport = root.parent / 'transport-501-attempt-1'
            report_path = root.parent / 'verification-501.json'
            recovery_path = root.parent / 'recovery-501.json'
            stack.enter_context(patch.object(d, 'ROOT', source))
            stack.enter_context(patch.object(supervision, 'process_identity', side_effect=lambda pid: (pid, 700)))
            if unknown_close:
                with self.assertRaises(a.AdmissionError):
                    a.publish_failure_handoff(evidence, report, scope, source, runtime_passed=True, input_closed=True)
                evidence.write('startup-failure.json', a.canonical(report), terminal=True)
                evidence.close()
                with self.assertRaises(c.IntegrityError):
                    d._preserve_startup_failure(root, transport, report_path, recovery_path,
                        handoff_sha256='a' * 64, expected_head=HEAD, expected_tree=TREE,
                        expected_workflow_run='501', deadline=720.0, admission_exit_status=65,
                        coordinator_exit_status='not_started', failure_state={})
                return {'report': report, 'deadline': 720.0, 'handoff_path': handoff_path, 'transport': transport}
            handoff = a.publish_failure_handoff(evidence, report, scope, source,
                runtime_passed=True, input_closed=existing is None or existing.evidence.close_confirmed)
            evidence.close()
            (root / 'admission-process-exit.txt').write_bytes(
                b'schema=worker38-admission-process-exit-v1\nexit_status=79\nadmission_process_returned=true\n')
            state['now'] = 121.0
            state['limits'][resource.RLIMIT_AS] = (-1, -1)
            state['limits'][resource.RLIMIT_CPU] = (-1, -1)
            if expire:
                original_fsync = os.fsync
                def crossing_fsync(fd):
                    original_fsync(fd)
                    state['now'] = 721.0
                stack.enter_context(patch.object(os, 'fsync', side_effect=crossing_fsync))
            result = d.preserve(root, transport, report_path, recovery_path,
                admission=None, admission_sha256=None, admission_provenance=None,
                admission_provenance_sha256=None, expected_head=HEAD, expected_tree=TREE,
                expected_workflow_run='501', preservation_deadline_monotonic_ms='720000',
                admission_exit_status=79, coordinator_exit_status='not_started',
                startup_failure_handoff_sha256=a.sha(handoff_path.read_bytes()))
            self.assertEqual(a.strict_json(handoff_path.read_bytes()), handoff)
            return {'report': report, 'first_failure': report['first_failure_monotonic'],
                'deadline': report['preservation_deadline_monotonic'], 'handoff': handoff,
                'result': result, 'transport': transport, 'root': root}

    def local_sources(self, name):
        source = self.root / ('source-' + name)
        source.mkdir()
        go = copy.deepcopy(self.bundle['go'])
        mapping = {}
        for path in a.REQUIRED_PRODUCTION_PATHS + a.METADATA_PATHS:
            raw = (ROOT / path).read_bytes() if path in a.METADATA_PATHS else b'INVENTED_SOURCE_BYTES_ONLY\n'
            destination = source / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            mapping[path] = a.sha(raw)
        go['diagnostic_files_sha256'] = dict(mapping)
        go['checked_file_sha256'] = dict(mapping)
        receipt = {'success': True, 'errors': 0, 'failures': 0, 'checked_file_sha256': mapping,
            'candidate_evaluator_calls': 0, 'reference_evaluator_calls': 0, 'games': 0,
            'measurement_fixture_constructions': 0, 'historical_source_imports': 0}
        raw = a.canonical(receipt)
        (source / a.FOCUSED_SOURCE_RECEIPT).write_bytes(raw)
        go['focused_source_receipt'] = {'path': a.FOCUSED_SOURCE_RECEIPT, 'size_bytes': len(raw), 'sha256': a.sha(raw)}
        go['stub_test_receipt_sha256'] = a.sha(raw)
        runtime = {'inherited_limits': copy.deepcopy(INHERITED_LIMITS), 'files': {
            'library': {'sha256': a.LIBRARY_SHA256}, 'executable': {'sha256': c.RUNTIME['executable_sha256']}}}
        return source, go, runtime

    def handoff(self):
        return {'schema': 'worker38-startup-handoff-v1', 'consumer': a.CONSUMER,
            'boot_id': '11111111-2222-3333-4444-555555555555', 'measurement_monotonic_ns': 100000000000,
            'measurement_boottime_ns': 100000000000, 'measurement_deadline_monotonic_ns': 1900000000000,
            'measurement_deadline_boottime_ns': 1900000000000, 'attempt_path': self.bundle['context']['attempt_path'],
            'source_path': '/invented-checkout', 'head': HEAD, 'tree': TREE, 'workflow_run': '501', 'workflow_attempt': '1',
            'admission_sha256': 'a' * 64, 'provenance_sha256': 'b' * 64, 'runtime_sha256': 'c' * 64,
            'source_map_sha256': 'd' * 64, 'restored_inventory_sha256': 'e' * 64, 'startup_receipt_sha256': 'f' * 64}

    @contextmanager
    def runtime_observations(self, *, cache_override=None, loader_override=None):
        cache = Path(cache_override) if cache_override is not None else self.root / ('runtime-' + str(len(list(self.root.glob('runtime-*')))))
        library_inode = loader_override['library_inode'] if loader_override is not None else 11
        executable_inode = 1233 if loader_override is not None else 10
        executable = cache / 'Python/3.11.16/x64/bin/python3.11'
        library = cache / 'Python/3.11.16/x64/lib/libpython3.11.so.1.0'
        executable.parent.mkdir(parents=True, exist_ok=True)
        library.parent.mkdir(exist_ok=True)
        executable.write_bytes(b'E')
        library.write_bytes(b'L')
        originals = {signal.SIGALRM: object(), signal.SIGUSR1: object()}
        state = {'timers': {kind: (0.0, 0.0) for kind in (signal.ITIMER_REAL, signal.ITIMER_VIRTUAL, signal.ITIMER_PROF)},
            'handlers': dict(originals), 'original_usr1': originals[signal.SIGUSR1], 'arms': [],
            'library_drift': False, 'historical_imports': 0, 'now': 250.0}
        limits = {getattr(resource, name): tuple(value) for name, value in INHERITED_LIMITS.items()}
        state['limits'] = limits
        def proxy(module):
            return types.SimpleNamespace(**{name: getattr(module, name) for name in dir(module)})
        sys_proxy = proxy(sys)
        sys_proxy.executable = str(executable)
        sys_proxy.version_info = (3, 11, 16)
        sys_proxy.flags = types.SimpleNamespace(**shared.FLAGS)
        sys_proxy.getprofile, sys_proxy.gettrace = lambda: None, lambda: None
        os_proxy = proxy(os)
        original_stat = os.stat
        def file_stat(path, *args, **kwargs):
            if str(path) in (str(executable), str(library)):
                is_library = str(path) == str(library)
                return types.SimpleNamespace(st_dev=os.makedev(8, 1), st_ino=library_inode if is_library else executable_inode,
                    st_size=a.LIBRARY_SIZE if is_library else 1, st_mtime=1, st_mtime_ns=1000000000,
                    st_ctime_ns=1000000000, st_mode=stat.S_IFREG | 0o700, st_nlink=1)
            return original_stat(path, *args, **kwargs)
        os_proxy.stat = file_stat
        os_proxy.readlink = lambda path: str(executable) if str(path) == '/proc/self/exe' else os.readlink(path)
        resource_proxy = proxy(resource)
        resource_proxy.getrlimit = lambda kind: limits[kind]
        resource_proxy.setrlimit = lambda kind, value: limits.__setitem__(kind, tuple(value))
        signal_proxy = proxy(signal)
        signal_proxy.getitimer = lambda kind: state['timers'][kind]
        signal_proxy.getsignal = lambda kind: state['handlers'][kind]
        def set_timer(kind, duration, interval=0.0):
            before = state['timers'][kind]
            state['timers'][kind] = (float(duration), float(interval))
            state['arms'].append(duration)
            return before
        def set_handler(kind, value):
            before = state['handlers'][kind]
            state['handlers'][kind] = value
            return before
        signal_proxy.setitimer, signal_proxy.signal = set_timer, set_handler
        def maps():
            inode = library_inode + 1 if state['library_drift'] else library_inode
            return ('1000-2000 r-xp 00000000 08:01 ' + str(executable_inode) + ' ' + str(executable) + '\n' +
                    '3000-4000 r-xp 00000000 08:01 ' + str(inode) + ' ' + str(library) + '\n')
        def stable(path):
            is_library = str(path) == str(library)
            return {'sha256': a.LIBRARY_SHA256 if is_library else c.RUNTIME['executable_sha256'],
                'size_bytes': a.LIBRARY_SIZE if is_library else 1, 'device': {'major': 8, 'minor': 1},
                'inode': library_inode if is_library else executable_inode, '_stat': (8, library_inode if is_library else executable_inode)}
        environment = {'GITHUB_ACTIONS': 'true', 'GITHUB_REPOSITORY': a.REPOSITORY, 'RUNNER_NAME': a.RUNNER,
            'RUNNER_TOOL_CACHE': str(cache), 'WORKER38_EXECUTABLE': str(executable), 'WORKER38_LIBRARY': str(library),
            'WORKER38_EXECUTABLE_STAT': shared.shell_stat(file_stat(executable)),
            'WORKER38_LIBRARY_STAT': shared.shell_stat(file_stat(library)),
            'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1', 'LD_LIBRARY_PATH': str(library.parent)}
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, environment, clear=True))
            for module in (shared, c):
                stack.enter_context(patch.object(module, 'sys', sys_proxy))
                stack.enter_context(patch.object(module, 'resource', resource_proxy))
                stack.enter_context(patch.object(module, 'signal', signal_proxy))
                stack.enter_context(patch.object(module.threading, 'active_count', return_value=1))
                stack.enter_context(patch.object(module.gc, 'isenabled', return_value=True))
                stack.enter_context(patch.object(module.gc, 'get_threshold', return_value=(700, 10, 10)))
            stack.enter_context(patch.object(d, 'signal', signal_proxy))
            stack.enter_context(patch.object(d, 'resource', resource_proxy))
            stack.enter_context(patch.object(shared, 'os', os_proxy))
            stack.enter_context(patch.object(shared, 'bounded_read', side_effect=lambda path, cap:
                b'L' * a.LIBRARY_SIZE if str(path) == str(library) else b'E'))
            stack.enter_context(patch.object(shared, 'sha', side_effect=lambda raw:
                a.LIBRARY_SHA256 if len(raw) == a.LIBRARY_SIZE else c.RUNTIME['executable_sha256']))
            stack.enter_context(patch.object(shared, 'open', side_effect=lambda path, mode: io.BytesIO(maps().encode()), create=True))
            stack.enter_context(patch.object(c, '_stable_loader_file', side_effect=stable))
            stack.enter_context(patch.object(c, '_loader_maps', side_effect=maps))
            original_file_info = c.file_info
            stack.enter_context(patch.object(c, 'file_info', side_effect=lambda path:
                {'sha256': c.RUNTIME['executable_sha256'], 'size_bytes': 1} if str(path) == str(executable) else original_file_info(path)))
            stack.enter_context(patch.object(c.platform, 'python_implementation', return_value='CPython'))
            stack.enter_context(patch.object(c.platform, 'python_version', return_value='3.11.16'))
            stack.enter_context(patch.object(d.time, 'monotonic', side_effect=lambda: state['now']))
            stack.enter_context(patch.object(a.time, 'monotonic_ns', side_effect=lambda: int(state['now'] * 1000000000)))
            stack.enter_context(patch.object(a.time, 'clock_gettime_ns', side_effect=lambda kind: int(state['now'] * 1000000000)))
            stack.enter_context(patch.object(a, 'signal', signal_proxy))
            yield state

    def parent_death_race(self):
        from test_worker38_supervision import LiteralSupervisorBoundaryHarness
        events = []
        class ExitSentinel(BaseException): pass
        def prctl(option, value, *unused):
            events.append(('prctl', option))
            if option == 2: value._obj.value = signal.SIGKILL
            return 0
        with patch.object(supervision.ctypes, 'CDLL', return_value=types.SimpleNamespace(prctl=prctl)), \
                patch.object(supervision.os, 'getppid', return_value=100), \
                patch.object(supervision, 'process_identity', side_effect=[(100, 1000), (100, 1001)]), \
                patch.object(supervision.os, 'kill', side_effect=lambda pid, sig: events.append(('kill', sig))), \
                patch.object(supervision.os, '_exit', side_effect=ExitSentinel):
            with self.assertRaises(ExitSentinel):
                supervision._arm_parent_death_signal(100, 1000)
        self.assertIn(('prctl', 1), events)
        self.assertIn(('prctl', 2), events)
        self.assertIn(('kill', signal.SIGKILL), events)
        # The raced guard aborts before any unsafe scientific setup can occur.
        # Fixed kernel-cap values are also read from the actual supervisor seam.
        with LiteralSupervisorBoundaryHarness(self.root / 'guard-contract', 'success') as harness:
            self.assertEqual(harness.kwargs['cpu_seconds'], 720)
            self.assertEqual(harness.kwargs['address_space_bytes'], 536870912)

    def literal_orchestration(self, failing):
        if not failing:
            return self.complete_orchestration()
        # The retained driver harness supplies administrative mocks only. Actual
        # driver schedule, reducer, receipts and fixed stop branch still execute.
        from test_worker38_driver_integration import DriverIntegration
        case = DriverIntegration(methodName='test_D02_one_fabricated_cell_completes_driver')
        case.production_output_hook = None
        case.setUp()
        self.addCleanup(case.doCleanups)
        launched = []
        reread = {'armed': False, 'failed': False}
        with case.patches() as stack:
            self.watch_production(case.root, produced_subtrees=('attempt/cells',),
                lineage='Fixed driver startup inputs; one modeled child writes literal capture prefix, actual driver records failure and rescan outputs')
            stack.enter_context(patch.object(d, 'SCHEDULE', c.SCHEDULE))
            original_open = Path.open
            def open_literal(path, *args, **kwargs):
                if failing and reread['armed'] and not reread['failed'] and path.name == 'candidate-return.json' and args and args[0] == 'rb':
                    reread['failed'] = True
                    raise PermissionError('literal post-capture reread unavailable')
                return original_open(path, *args, **kwargs)
            stack.enter_context(patch.object(Path, 'open', open_literal))
            def child(*args, **kwargs):
                index = len(launched) + 1
                launched.append(index)
                folder = case.attempt / 'cells' / f'{index:02d}'
                budget = c.Budget(case.attempt)
                budget.mkdir(folder)
                calls = {}
                for scope in ('candidate', 'reference'):
                    if failing and scope == 'reference': break
                    info = budget.write(folder / (scope + '-return.json'), {'literal': 'fixed-equal-return'})
                    budget.write(folder / (scope + '-start.json'), {'literal': 'fixed-marker'})
                    budget.write(folder / (scope + '-capture-confirmed.json'), info)
                    calls[scope] = {'method_entered': True, 'invocation_attempted': True, 'start_marker_durable': True,
                        'returned': True, 'durable_capture_confirmed': True}
                count = len(calls)
                failure = c.error_record(PermissionError('literal unavailable reread'), 'cell_measurement') if failing else None
                budget.write(folder / 'cell-receipt.json', {'status': 'execution_incomplete' if failing else 'complete',
                    'failure': failure, 'calls': calls, 'actual_starts': count, 'actual_starts_upper_bound': count,
                    'actual_returns': count, 'confirmed_captures': count, 'pre_call_markers': count})
                for name in ('source-runtime-preflight.json', 'cell-start.json', 'cell-boundaries.json', 'unmeasured-accounting.json'):
                    budget.write(folder / name, {'literal': 'fixed committed administrative record'})
                budget.write(folder / 'active-call.json', {'active': False})
                (case.attempt / f'supervisor-cell-{index:02d}.log').write_bytes(b'')
                reread['armed'] = failing
                return {'status': 'execution_incomplete' if failing else 'completed',
                        'reason': 'child_nonzero_exit' if failing else 'child_exit_zero', 'exit_code': 74 if failing else 0}
            stack.enter_context(patch.object(supervision, 'run_cell_child', side_effect=child))
            result = case.run_measure()
        receipt = case.read_receipt()
        self.assertEqual(result, 1 if failing else 0)
        self.assertEqual(launched, [1] if failing else list(range(1, 21)))
        self.assertEqual(receipt['confirmed_captures'], 0 if failing else 40)
        if failing:
            self.assertTrue(reread['failed'])
            self.assertEqual(receipt['actual_returns'], 1)
            self.assertTrue(receipt['capture_gaps'])
            self.assertTrue(receipt['unavailable_evidence'])
        self.assertEqual(receipt['completed_prefix'], [] if failing else list(range(1, 21)))
        self.assertIsNone(receipt.get('classification'))

    def complete_orchestration(self):
        from test_worker38_driver_integration import DriverIntegration
        import test_worker38_verify_integration as offline
        case = DriverIntegration(methodName='test_D02_one_fabricated_cell_completes_driver')
        case.production_output_hook = None
        case.setUp()
        self.addCleanup(case.doCleanups)
        checkout = self.root / 'complete-checkout'
        checkout.mkdir()
        cache = self.root / 'complete-cache'
        target = cache / 'worker38-synthetic-profile/allocations/worker38-synthetic-profile-01/run-123-attempt-1'
        literal_loader = copy.deepcopy(offline.LOADER_IDENTITY)
        literal_loader.update(tool_cache=str(cache),
            executable_path=str(cache / c.LOADER_EXECUTABLE_RELATIVE_PATH),
            library_path=str(cache / c.LOADER_RELATIVE_PATH),
            library_directory=str((cache / c.LOADER_RELATIVE_PATH).parent))
        literal_loader['mapped_library']['path'] = literal_loader['library_path']
        literal_loader['loader_environment'] = {'LD_LIBRARY_PATH': literal_loader['library_directory']}
        with ExitStack() as fixture:
            fixture.enter_context(patch.object(offline, 'ORIGINAL', str(target)))
            fixture.enter_context(patch.object(offline, 'SCRIPT', str(checkout / 'scripts/run_worker38_synthetic.py')))
            fixture.enter_context(patch.object(offline, 'LOADER_IDENTITY', literal_loader))
            external = self.root / 'complete-external'
            external.mkdir()
            bundle = offline.LiteralBundle(external, driver_target=target)
            checkout_git = checkout / '.git'
            checkout_git.mkdir(mode=0o700)
            checkout_head = checkout_git / 'HEAD'
            checkout_head.write_bytes((bundle.go['head'] + '\n').encode('ascii'))
            checkout_head.chmod(0o600)
            pending = self.root / 'complete-pending'
            pending.mkdir()
            # Move the one prebuilt cohort out of the admitted attempt. The real
            # driver will consume these exact records once in its fixed order.
            names = ['cells', 'receipt.json', 'source-runtime-preflight.json',
                'measurement-phase-close.json', 'coordinator-restoration.json',
                'external-admission.json', 'stub-test-receipt.json', 'writer-exit-observation.json']
            names += [f'supervisor-cell-{index:02d}.{suffix}' for index in range(1, 21) for suffix in ('json', 'log')]
            for name in names:
                (target / name).rename(pending / name)
            case.root, case.attempt, case.auth = checkout, target, bundle.auth
            case.claim = target.parent
            case.admission, case.provenance = bundle.admission, bundle.provenance
            case.test_receipt = pending / 'stub-test-receipt.json'
            case.go = bundle.go
            case.prov = a.verify_provenance(bundle.provenance, bundle.admission, a.sha(bundle.admission.read_bytes()))
            case.now = 9340.0
            case.ns = 9340000000000
            case.experiment = checkout / a.EXPERIMENT
            parent_runtime = bundle.runtime()
            parent_runtime['flags'] = [literal_loader['executable_path'], '-B', '-s', offline.SCRIPT, 'measure']
            case.literal_runtime = lambda: copy.deepcopy(parent_runtime)
            launched, guard_calls = [], []
            manifest_hash = c.sha(c.canonical(bundle.manifest))
            with case.patches() as stack:
                self.watch_production(target.parent, produced_subtrees=(target.name + '/cells',),
                    lineage='One fixed twenty-cell cohort moved from pending input store once; actual driver, preservation, archive, part, manifest and seal outputs all charged')
                self.watch_production(external,
                    lineage='Fixed external admission and offline anchors are inputs; provider/Drive copies made from actual sealed production bytes are outputs')
                stack.enter_context(patch.dict(os.environ, {'WORKER38_HEAD': bundle.go['head'],
                    'WORKER38_TREE': bundle.go['tree'], 'WORKER38_SOURCE_DIRECTORY': str(checkout)}))
                self.assertEqual(d.verify_checkout_binding(checkout, bundle.go['head'], bundle.go['tree']),
                                 (bundle.go['head'], bundle.go['tree']))
                stack.enter_context(patch.object(d, 'SCHEDULE', c.SCHEDULE))
                stack.enter_context(patch.object(d, 'SOURCE_MANIFEST_SHA256', manifest_hash))
                stack.enter_context(patch.object(sources, 'SOURCE_MANIFEST_SHA256', manifest_hash))
                stack.enter_context(patch.object(d, 'read_manifest', side_effect=sources.read_manifest))
                stack.enter_context(patch.object(d, 'verify_files', side_effect=sources.verify_files))
                stack.enter_context(patch.object(c, 'loader_identity', return_value=literal_loader))
                stack.enter_context(patch.object(d.os, 'getpid', return_value=1000))
                stack.enter_context(patch.object(supervision, 'process_identity', side_effect=lambda pid: (pid, case.literal_start_ticks)))
                stack.enter_context(patch.object(supervision, '_usage', side_effect=lambda who:
                    float(len(launched)) if who == resource.RUSAGE_SELF else 30.0 * len(launched)))
                def checked_file(path):
                    path = Path(path)
                    if path.is_relative_to(checkout):
                        relative = path.relative_to(checkout).as_posix()
                        if relative in bundle.go['diagnostic_files_sha256']:
                            return {'size_bytes': 27, 'sha256': bundle.go['diagnostic_files_sha256'][relative]}
                    return c.file_info(path)
                stack.enter_context(patch.object(d, 'file_info', side_effect=checked_file))
                def child(attempt, index, env, phase, **kwargs):
                    self.assertEqual(Path(attempt), target)
                    self.assertEqual(index, len(launched) + 1)
                    # Positive direct-child guard uses the real fixed prctl/race
                    # checker and literal kernel observations; no OS child exists.
                    def prctl(option, value, *unused):
                        guard_calls.append((index, option))
                        if option == 2: value._obj.value = signal.SIGKILL
                        return 0
                    with patch.object(supervision.ctypes, 'CDLL', return_value=types.SimpleNamespace(prctl=prctl)), \
                            patch.object(supervision.os, 'getppid', return_value=1000), \
                            patch.object(supervision.os, 'kill', side_effect=AssertionError('no actual guard signal permitted')), \
                            patch.object(supervision.os, '_exit', side_effect=AssertionError('no actual guard exit permitted')):
                        supervision._arm_parent_death_signal(1000, case.literal_start_ticks)
                    source = pending / 'cells' / f'{index:02d}'
                    folder = target / 'cells' / f'{index:02d}'
                    self.assertEqual(list(folder.iterdir()), [])
                    for record in list(source.iterdir()):
                        record.rename(folder / record.name)
                    (pending / f'supervisor-cell-{index:02d}.log').rename(target / f'supervisor-cell-{index:02d}.log')
                    result = a.strict_json((pending / f'supervisor-cell-{index:02d}.json').read_bytes())
                    launched.append(index)
                    case.now = 9340.0 + 30.0 * index
                    self.assertEqual(result['phase'], phase.snapshot())
                    return result
                stack.enter_context(patch.object(supervision, 'run_cell_child', side_effect=child))
                self.assertEqual(case.run_measure(), 0)
                transport_destination = target.parent / 'transport-123-attempt-1'
                with self.runtime_observations(cache_override=cache, loader_override=literal_loader) as preserving, ExitStack() as preserve_stack:
                    preserving['now'] = 9941.0
                    preserve_stack.enter_context(patch.dict(os.environ, {'GITHUB_RUN_ID': '123', 'GITHUB_RUN_ATTEMPT': '1',
                        'GITHUB_EVENT_NAME': 'pull_request', 'WORKER38_HEAD': HEAD, 'WORKER38_TREE': TREE,
                        'WORKER38_SOURCE_DIRECTORY': str(checkout)}))
                    preserve_stack.enter_context(patch.object(d, 'runtime_check', side_effect=c.runtime_check))
                    preserve_stack.enter_context(patch.object(c, 'loader_identity', side_effect=d.loader_identity))
                    preserve_stack.enter_context(patch.object(d.os, 'getpid', return_value=1001))
                    preserve_stack.enter_context(patch.object(d.os, 'getppid', return_value=1002))
                    def preservation_identity(pid):
                        if pid == 1000: raise FileNotFoundError('literal former coordinator exited')
                        return (pid, 934100)
                    preserve_stack.enter_context(patch.object(supervision, 'process_identity', side_effect=preservation_identity))
                    result = d.preserve(target, transport_destination, target.parent / 'verification-123.json',
                        target.parent / 'recovery-123.json', admission=bundle.admission,
                        admission_sha256=c.sha(bundle.admission.read_bytes()), admission_provenance=bundle.provenance,
                        admission_provenance_sha256=c.sha(bundle.provenance.read_bytes()), expected_head=HEAD,
                        expected_tree=TREE, expected_workflow_run='123', preservation_deadline_monotonic_ms='10540000',
                        admission_exit_status=0, coordinator_exit_status=0)
                    self.assertEqual(result, 0)
                    self.assertTrue((transport_destination / 'upload-plan.txt').is_file())
            self.assertEqual(launched, list(range(1, 21)))
            self.assertEqual(guard_calls, [(index, option) for index in range(1, 21) for option in (1, 2)])
            receipt = case.read_receipt()
            self.assertEqual(receipt['confirmed_captures'], 40)
            self.assertEqual(receipt['completed_prefix'], list(range(1, 21)))
            computational_raw = (target / 'receipt.json').read_bytes()
            close_raw = (target / 'measurement-phase-close.json').read_bytes()
            verified = bundle.verify()
            custody = bundle.custody_from_production(verified, transport_destination)
            timing = bundle.timing(verified, custody)
            self.assertTrue(verified['complete'])
            self.assertEqual(len(verified['cells']), 20)
            self.assertEqual(timing['custody'], 'verified')
            self.assertEqual((target / 'receipt.json').read_bytes(), computational_raw)
            self.assertEqual((target / 'measurement-phase-close.json').read_bytes(), close_raw)
            self.retain({'driver-receipt.json': computational_raw, 'driver-close.json': close_raw,
                'verification.json': a.canonical(verified), 'custody.json': a.canonical(custody)},
                {'literal_child_invocations': 20, 'literal_returns': 40, 'scientific_calls': 0,
                 'historical_imports': 0, 'same_attempt_verified': True, 'timing': timing},
                existing_paths={'driver-receipt.json': target / 'receipt.json',
                    'driver-close.json': target / 'measurement-phase-close.json',
                    'custody.json': bundle.custody_path})

    def bash_case(self, case_id, *, extra=False, occupied=False, changed=False, contaminated=False, credential_fd=False):
        base = self.root / case_id
        commands, source, cache, temp = (base / name for name in ('commands', 'source', 'cache', 'temp'))
        for directory in (commands, source / 'scripts/worker38', cache / 'Python/3.11.16/x64/bin',
                          cache / 'Python/3.11.16/x64/lib', temp):
            directory.mkdir(parents=True, mode=0o700)
        for name in ('worker_bootstrap_shared.sh', 'worker38-bootstrap.sh'):
            (source / 'scripts' / name).write_bytes((ROOT / 'scripts' / name).read_bytes())
        (source / 'scripts/worker38/admission.py').write_bytes(b'# invented nonexecuted metadata path\n')
        (source / 'scripts/run_worker38_synthetic.py').write_bytes(b'# invented nonexecuted science path\n')
        pinned = cache / 'Python/3.11.16/x64/bin/python3.11'
        pinned.write_text(BASH_STUB)
        pinned.chmod(0o700)
        (cache / 'Python/3.11.16/x64/lib/libpython3.11.so.1.0').write_bytes(b'INERT_LIBRARY\n')
        allocation = cache / 'worker38-synthetic-profile/allocations' / a.ALLOCATION
        attempt = allocation / 'run-501-attempt-1'
        for path in (attempt / 'home', attempt / 'tmp', attempt / 'admission-inputs'):
            path.mkdir(parents=True, mode=0o700)
        reservation = allocation / 'reservation.txt'
        if occupied:
            reservation.write_bytes(b'INVENTED_PREVIOUS_RESERVATION\n')
        event = base / 'event.json'
        event.write_bytes(b'{}\n')
        log = base / 'commands.log'
        for name in ('realpath', 'readlink', 'stat', 'id', 'mkdir', 'cat', 'sync', 'sha256sum', 'git', 'timeout'):
            path = commands / name
            path.write_text(BASH_STUB)
            path.chmod(0o700)
        environment = {'PATH': str(commands), 'LC_ALL': 'C', 'RUNNER_TOOL_CACHE': str(cache),
            'GITHUB_WORKSPACE': str(source), 'RUNNER_TEMP': str(temp), 'GITHUB_EVENT_PATH': str(event),
            'GITHUB_REPOSITORY': a.REPOSITORY, 'GITHUB_ACTOR': a.OWNER, 'GITHUB_TRIGGERING_ACTOR': a.OWNER,
            'GITHUB_SERVER_URL': 'https://github.com', 'GITHUB_API_URL': 'https://api.github.com',
            'RUNNER_NAME': a.RUNNER, 'GITHUB_EVENT_NAME': 'pull_request', 'GITHUB_RUN_ATTEMPT': '1',
            'GITHUB_RUN_ID': '501', 'GITHUB_JOB': 'measure', 'PR_NUMBER': '101', 'GITHUB_ACTIONS': 'true',
            'WORKER38_SENDER': a.OWNER, 'WORKER38_PR_AUTHOR': a.OWNER, 'WORKER38_EVENT_ACTION': 'edited',
            'WORKER38_HEAD': HEAD, 'WORKER38_HEAD_REF': a.BRANCH, 'WORKER38_BASE_REF': 'main',
            'WORKER38_BASE_HEAD': a.BASE_HEAD, 'WORKER38_HEAD_REPOSITORY': a.REPOSITORY,
            'WORKER38_BASE_REPOSITORY': a.REPOSITORY, 'WORKER38_BODY_CHANGED': 'true',
            'WORKER38_PREVIOUS_BODY': 'Invented previous body',
            'WORKER38_CURRENT_BODY': a.START + '\n{}\n' + a.END + '\n' + a.DIGEST + ': ' + ('b' if changed else 'a') * 64,
            'GH_TOKEN': CREDENTIAL, 'LITERAL_COMMAND_LOG': str(log), 'LITERAL_CASE': case_id,
            'LITERAL_OCCUPIED': '1' if occupied else '0', 'LITERAL_ATTEMPT': str(attempt)}
        if contaminated:
            # Set loader sentinels after the fresh Bash loader has started, then
            # enter the actual boundary. No LD_PRELOAD reaches a real loader.
            prelude = 'export LD_PRELOAD=INVENTED LD_LIBRARY_PATH=INVENTED PYTHONPATH=INVENTED PYTHONSTARTUP=INVENTED; '
            environment.update({'ACTIONS_ID_TOKEN_REQUEST_TOKEN': CREDENTIAL, 'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://invalid.example',
                'SSH_AUTH_SOCK': '/invented/socket', 'HTTPS_PROXY': 'https://invalid.example'})
        else:
            prelude = ''
        if credential_fd:
            credential = base / 'credential-fd.txt'
            credential.write_text(CREDENTIAL)
            environment['LITERAL_FD_PATH'] = str(credential)
            prelude += 'exec 9<"$LITERAL_FD_PATH"; '
        body = prelude + 'source "$GITHUB_WORKSPACE/scripts/worker38-bootstrap.sh"; _worker38_main' + (' arbitrary-command' if extra else '')
        output_record = self.watch_production(base, produced_paths=('commands.log',),
            lineage='Fixed source/command/executable/event/optional reservation inputs; actual shell and inert executable generated files are outputs')
        native_paths = None
        native_deadline = None
        native_timeout_args = None
        with ExitStack() as native_streams:
            output_args = {'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE}
            if PRODUCTION_OUTPUT_HOOK is not None:
                # One existing Bash root and its inherited process group. Every
                # descendant inherits this exact hard per-file ceiling.
                output_record['native_writer_state'] = 'unconfirmed'
                now = a.time.monotonic()
                if type(NATIVE_BATCH_DEADLINE_MONOTONIC) is not float or not a.math.isfinite(NATIVE_BATCH_DEADLINE_MONOTONIC):
                    raise AssertionError('native Bash requires the original injected batch cutoff')
                native_deadline = min(now + 5.0, NATIVE_BATCH_DEADLINE_MONOTONIC)
                native_timeout_args = (['/bin/bash', '--noprofile', '--norc', '-c', body],
                                       max(0.0, native_deadline - now))
                if native_deadline - now <= 0.1:
                    raise subprocess.TimeoutExpired(*native_timeout_args)
                native_paths = (base / 'native-stdout.txt', base / 'native-stderr.txt')
                for key, path in zip(('stdout', 'stderr'), native_paths):
                    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
                    stream = native_streams.enter_context(os.fdopen(fd, 'wb', buffering=0))
                    info = os.fstat(stream.fileno())
                    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid():
                        raise AssertionError('native Bash capture requires exclusive owned regular files')
                    output_args[key] = stream
                acknowledgment = base / 'native-fsize-confirmation.txt'
                ack_fd = os.open(acknowledgment, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
                ack_stream = native_streams.enter_context(os.fdopen(ack_fd, 'wb', buffering=0))
                ack_raw = b'RLIMIT_FSIZE=2097152:2097152\n'
                def fixed_file_ceiling():
                    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
                    if resource.getrlimit(resource.RLIMIT_CORE) != (0, 0):
                        raise RuntimeError('native Bash core ceiling readback failed')
                    resource.setrlimit(resource.RLIMIT_FSIZE, (2097152, 2097152))
                    if resource.getrlimit(resource.RLIMIT_FSIZE) != (2097152, 2097152):
                        raise RuntimeError('native Bash file ceiling readback failed')
                    if os.write(ack_fd, ack_raw) != len(ack_raw):
                        raise RuntimeError('native Bash file ceiling acknowledgment failed')
                    os.close(ack_fd)
                output_args.update(preexec_fn=fixed_file_ceiling, pass_fds=(ack_fd,))
            process = subprocess.Popen(['/bin/bash', '--noprofile', '--norc', '-c', body], env=environment,
                cwd=source, stdin=subprocess.DEVNULL, **output_args)
            if native_paths is None:
                try:
                    stdout, stderr = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                    self.fail('registered5-second Bash case exhausted')
            else:
                try:
                    remaining = native_deadline - a.time.monotonic() - 0.1
                    if remaining <= 0:
                        raise subprocess.TimeoutExpired(*native_timeout_args)
                    process.wait(timeout=remaining)
                    if a.time.monotonic() >= native_deadline:
                        raise subprocess.TimeoutExpired(*native_timeout_args)
                    if process.returncode < 0:
                        raise AssertionError('native Bash writer exit unconfirmed')
                    os.fsync(ack_stream.fileno())
                    ack_stream.close()
                    if acknowledgment.read_bytes() != ack_raw:
                        raise AssertionError('native Bash file ceiling acknowledgment unavailable')
                    for key in ('stdout', 'stderr'):
                        if a.time.monotonic() >= native_deadline:
                            raise subprocess.TimeoutExpired(*native_timeout_args)
                        os.fsync(output_args[key].fileno())
                    stdout, stderr = (path.read_bytes() for path in native_paths)
                    if a.time.monotonic() >= native_deadline:
                        raise subprocess.TimeoutExpired(*native_timeout_args)
                except BaseException as original_error:
                    # Never replace the original timeout/cause during the two
                    # existing cleanup operations or grant another interval.
                    kill_error = wait_error = None
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                    except BaseException as cleanup_error:
                        kill_error = cleanup_error
                    try:
                        process.wait(timeout=max(0.0, native_deadline - a.time.monotonic()))
                    except BaseException as cleanup_error:
                        wait_error = cleanup_error
                    try:
                        for operation, error in (('kill', kill_error), ('wait', wait_error)):
                            if error is not None:
                                original_error.add_note('native cleanup ' + operation + ': ' + type(error).__name__[:64])
                    except BaseException:
                        pass  # Best-effort notes cannot replace the original failure.
                    raise
        if native_paths is not None and a.time.monotonic() >= native_deadline:
            raise subprocess.TimeoutExpired(*native_timeout_args)
        self.assertLessEqual(len(stdout) + len(stderr), 4096)
        self.assertLessEqual(log.stat().st_size if log.exists() else 0, 65536)
        records = log.read_text().splitlines() if log.exists() else []
        entry_file = attempt / 'stub-entries.txt'
        entries = entry_file.read_text().splitlines() if entry_file.exists() else []
        facts_file = attempt / 'science-facts.json'
        facts = json.loads(facts_file.read_text()) if facts_file.exists() else {}
        report = {'case_id': case_id, 'returncode': process.returncode,
            'commands': [line.split('|')[2] for line in records], 'command_records': records,
            'entries': entries, 'science_calls': 0, 'inherited_loader_seen': any('contaminated' in line for line in records),
            'reservation_preserved': occupied and reservation.read_bytes() == b'INVENTED_PREVIOUS_RESERVATION\n',
            'old_namespace_access': any('worker36-evidence' in line or 'worker37-bootstrap-readiness/allocations' in line for line in records),
            'science_secret_seen': facts.get('secret_seen', True), 'science_fd_seen': facts.get('fd9_seen', True),
            'science_allowlist_checked': facts.get('allowlist_checked', False),
            'physical_process_count': 'not fully measured; command PID and parent PID observations retained'}
        BASH_OBSERVATIONS.append(report)
        files = {'shell-stdout.txt': stdout, 'shell-stderr.txt': stderr,
                 'commands.log': log.read_bytes() if log.exists() else b''}
        files.update({path.name: path.read_bytes() for path in attempt.iterdir() if path.is_file()})
        self.assertLessEqual(sum(map(len, files.values())) + len(a.canonical(report)), 131072)
        existing = {path.name: path for path in attempt.iterdir() if path.is_file()}
        if log.exists(): existing['commands.log'] = log
        if native_paths is not None:
            existing.update({'shell-stdout.txt': native_paths[0], 'shell-stderr.txt': native_paths[1]})
        self.retain(files, report, existing_paths=existing)
        if native_paths is not None:
            if a.time.monotonic() >= native_deadline:
                raise subprocess.TimeoutExpired(*native_timeout_args)
            output_record['native_writer_state'] = 'confirmed'
            output_record['native_process_exit_status'] = process.returncode
        return report


BASH_STUB = r'''#!/bin/bash
set -euo pipefail
name=${0##*/}
if [[ $name == python3.11 && ${4-} == measure ]]; then
  attempt=
  while (( $# )); do
    if [[ $1 == --attempt ]]; then shift; attempt=$1; fi
    shift
  done
  [[ -n $attempt ]]
  printf 'measure\n' >> "$attempt/stub-entries.txt"
  secret=false fd9=false allowed=true
  for variable in $(compgen -e); do
    case $variable in
      PATH|LC_ALL|HOME|TMPDIR|PYTHONHASHSEED|PYTHONDONTWRITEBYTECODE|LD_LIBRARY_PATH|RUNNER_TOOL_CACHE|RUNNER_NAME|GITHUB_REPOSITORY|GITHUB_RUN_ID|GITHUB_RUN_ATTEMPT|GITHUB_ACTIONS|GITHUB_EVENT_NAME|WORKER38_EXECUTABLE|WORKER38_LIBRARY|WORKER38_EXECUTABLE_STAT|WORKER38_LIBRARY_STAT|WORKER38_HEAD|WORKER38_TREE|WORKER38_RUN_ID|WORKER38_PR_NUMBER|WORKER38_BRANCH|WORKER38_JOB|WORKER38_ALLOCATION_ID|WORKER38_ATTEMPT_DIRECTORY|WORKER38_SOURCE_DIRECTORY|WORKER38_HANDOFF_SHA256|GITHUB_OUTPUT|PWD|SHLVL|_) ;;
      *) allowed=false;;
    esac
    [[ ${!variable} != *INVENTED_TEST_CREDENTIAL_NOT_A_SECRET* ]] || secret=true
  done
  [[ ! -e /proc/self/fd/9 ]] || fd9=true
  printf '{"secret_seen":%s,"fd9_seen":%s,"allowlist_checked":%s}\n' "$secret" "$fd9" "$allowed" > "$attempt/science-facts.json"
  exit 0
fi
loader=clean
for variable in ${!LD@} ${!PYTHON@}; do
  [[ ${!variable} != INVENTED ]] || loader=contaminated
done
printf '%s|%s|%s|%s|%s\n' "$BASHPID" "$PPID" "$name" "$loader" "$*" >> "$LITERAL_COMMAND_LOG"
last=${!#}
case $name in
  realpath|readlink) printf '%s\n' "$last";;
  id) printf '1000\n';;
  stat)
    if [[ ${1-} == -f ]]; then printf '1048576:4096\n'
    elif [[ ${2-} == '%u:%a' ]]; then printf '1000:700\n'
    elif [[ ${2-} == '%d:%i:%s:%Y' ]]; then
      if [[ $last == */libpython3.11.so.1.0 ]]; then printf '1:11:23041360:1\n'
      elif [[ $last == */bin/python3.11 ]]; then printf '1:10:1:1\n'
      else contents=; IFS= read -r -d '' contents < "$last" || :; printf '1:20:%s:1\n' "${#contents}"; fi
    elif [[ ${2-} == '%s' ]]; then
      contents=; IFS= read -r -d '' contents < "$last" || :; printf '%s\n' "${#contents}"
    else exit 92; fi;;
  mkdir)
    if [[ $LITERAL_OCCUPIED == 1 && $last == */allocations/worker38-synthetic-profile-01 ]]; then exit 1; fi
    [[ -d $last ]];;
  cat) while IFS= read -r line || [[ -n $line ]]; do printf '%s\n' "$line"; done < "$last";;
  sync) :;;
  sha256sum)
    if [[ $last == */bin/python3.11 ]]; then hash=a15ccdaf07655a8667a3687b13171486c9a265d92273ba3ad820fbb64d2cfecc
    elif [[ $last == */libpython3.11.so.1.0 ]]; then hash=ba4450817186fbe1e3c477f6aefeee7c353cba3593cc9950382ad9d1f5e62896
    else hash=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa; fi
    printf '%s  %s\n' "$hash" "$last";;
  git)
    if [[ $last == 'HEAD^{tree}' ]]; then printf '2222222222222222222222222222222222222222\n'
    else printf '1111111111111111111111111111111111111111\n'; fi;;
  timeout)
    if [[ ${1-} == --foreground ]]; then shift; fi
    [[ ${1-} == --signal=KILL ]] || exit 93
    shift
    [[ ${1-} =~ ^[0-9]+s$ ]] || exit 93
    shift
    exec "$@";;
  python3.11)
    output= source=
    while (( $# )); do
      if [[ $1 == --output ]]; then shift; output=$1;
      elif [[ $1 == --source ]]; then shift; source=$1; fi
      shift
    done
    [[ -n $output && -n $source ]]
    printf 'admission\n' >> "$output/stub-entries.txt"
    IFS=' ' read -r uptime ignored < /proc/uptime
    [[ $uptime =~ ^([0-9]+)\.([0-9]+)$ ]]
    seconds=${BASH_REMATCH[1]} fraction=${BASH_REMATCH[2]}000000000
    now=$((10#$seconds*1000000000+10#${fraction:0:9}))
    IFS= read -r boot < /proc/sys/kernel/random/boot_id
    printf '{"literal":"inert handoff never authenticated"}\n' > "$output/startup-handoff.json"
    hash=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    printf 'version=worker38-handoff-v1\nhandoff_sha256=%s\nboot_id=%s\nmeasurement_monotonic_ns=%s\nmeasurement_boottime_ns=%s\nmeasurement_deadline_boottime_ns=%s\nattempt_path=%s\nsource_path=%s\nhead=%s\ntree=%s\nadmission_sha256=%s\nprovenance_sha256=%s\nruntime_sha256=%s\nsource_map_sha256=%s\n' "$hash" "$boot" "$now" "$now" "$((now+1800000000000))" "$output" "$source" "$WORKER38_HEAD" "$WORKER38_TREE" "$hash" "$hash" "$hash" "$hash" > "$output/measurement-handoff.txt"
    ;;
  *) exit 94;;
esac
'''
