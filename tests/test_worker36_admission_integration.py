"""Finite A01-A19 literal auth cases; P06-P11 are frozen runner metadata repair."""
import ast
import copy
import io
from pathlib import Path
import sys
import struct
import tempfile
import types
import unittest
import zipfile
from unittest.mock import call, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from worker36 import admission as a

CLI_LIMIT_OBSERVATIONS = []

LITERAL_LOADER_PIN = {'schema': 'worker36-loader-pin-v1',
    'executable_sha256': 'a15ccdaf07655a8667a3687b13171486c9a265d92273ba3ad820fbb64d2cfecc',
    'library_relative_path': 'Python/3.11.16/x64/lib/libpython3.11.so.1.0',
    'library_sha256': '4' * 64, 'library_size_bytes': 4096}


def literal_loader_identity(cache='/literal-runner/tool-cache'):
    """Invented mapped identity only; these hashes never assert runner evidence."""
    library = cache + '/' + LITERAL_LOADER_PIN['library_relative_path']
    directory = library.rsplit('/', 1)[0]
    device = {'major': 8, 'minor': 1}
    return {**copy.deepcopy(LITERAL_LOADER_PIN), 'schema': 'worker36-loader-identity-v1',
            'tool_cache': cache, 'executable_path': cache + '/Python/3.11.16/x64/bin/python3.11',
            'library_path': library, 'library_directory': directory,
            'library_device': device, 'library_inode': 101,
            'mapped_library': {'path': library, 'device': dict(device), 'inode': 101},
            'loader_environment': {'LD_LIBRARY_PATH': directory}}


def literal_context_environment(context):
    return {'GITHUB_REPOSITORY': a.REPOSITORY, 'GITHUB_EVENT_NAME': 'pull_request',
            'GITHUB_ACTOR': a.OWNER, 'GITHUB_RUN_ID': context['workflow_run'],
            'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_SERVER_URL': 'https://github.com',
            'GITHUB_API_URL': 'https://api.github.com', 'RUNNER_NAME': 'bandido-alcatraz-ci',
            'PR_NUMBER': '41', 'RUNNER_TOOL_CACHE': context['runner_tool_cache'],
            'GITHUB_WORKSPACE': context['checkout_path'], 'RUNNER_TEMP': context['runner_temp'],
            'DURABLE': context['durable_root'], 'ATTEMPT': context['attempt_path'],
            'AUTH': context['durable_root'] + '/admission-inputs'}


def literal_shell_loader(loader):
    return {'WORKER36_PYTHON': loader['executable_path'],
            'WORKER36_LOADER_DIRECTORY': loader['library_directory'],
            'WORKER36_LOADER_LIBRARY': loader['library_path'],
            'WORKER36_LOADER_SHA256': loader['library_sha256'],
            'WORKER36_LOADER_SIZE_BYTES': str(loader['library_size_bytes'])}


def literal_prerequisite_bundle(go, *, pr_number=41, owner_id=71, cache='/literal-runner/tool-cache',
                                focused_source_receipt=None, checked_file_sha256=None):
    """Fixed invented proof chain. Only the two new GO descriptors are replaced.

    Existing runtime/resources/loader/source fields are deliberately preserved,
    including invalid values supplied by a finite negative test.
    """
    bound = copy.deepcopy(go)
    owner = {'login': a.OWNER, 'id': owner_id, 'type': 'User'}
    repo = {'id': 314, 'full_name': a.REPOSITORY, 'url': a.API, 'html_url': a.WEB, 'owner': owner}
    proofs = {}; reviews = []
    for index, role in enumerate(a.REVIEW_ROLES):
        review = {'role': role, 'native_reviewer_id': 'literal-native-' + role,
                  'comment_id': 8101 + index, 'url': a.WEB + '/pull/' + str(pr_number) + '#issuecomment-' + str(8101 + index),
                  'head': go['head'], 'tree': go['tree'], 'verdict': 'clean',
                  'handoff_sha256': '9' * 64, 'report_sha256': ('a' if index == 0 else 'b') * 64}
        record = {'schema': 'worker36-owner-attested-native-review-v1', 'repository': a.REPOSITORY,
                  'pr_number': pr_number, 'role': role, 'native_reviewer_id': review['native_reviewer_id'],
                  'head': go['head'], 'tree': go['tree'], 'verdict': 'clean', 'complete_review': True,
                  'independent_review_attested': True, 'actionable_findings': {'P0': 0, 'P1': 0, 'P2': 0, 'P3': 0},
                  'handoff_sha256': review['handoff_sha256'], 'report_sha256': review['report_sha256']}
        body = a.REVIEW_START + '\n' + a.canonical(record).decode() + a.REVIEW_END + '\n'
        review['body_sha256'] = a.sha(body.encode())
        comment = {'id': review['comment_id'], 'url': a.API + '/issues/comments/' + str(review['comment_id']),
                   'html_url': review['url'], 'issue_url': a.API + '/issues/' + str(pr_number),
                   'user': copy.deepcopy(owner), 'body': body}
        proofs['review-' + role + '.json'] = a.canonical(comment)
        reviews.append(review)
    bound['reviews'] = reviews
    receipt = copy.deepcopy(focused_source_receipt) if focused_source_receipt is not None else {
        'path': 'experiments/synthetic-profile-overhead/literal-receipt.json',
        'sha256': go.get('stub_test_receipt_sha256', '7' * 64), 'size_bytes': 128}
    pins = copy.deepcopy(checked_file_sha256) if checked_file_sha256 is not None else {
        **go.get('diagnostic_files_sha256', {}), receipt['path']: receipt['sha256']}
    loader = literal_loader_identity(cache)
    pin = go.get('loader_pin')
    if type(pin) is dict:
        for key in ('executable_sha256', 'library_sha256', 'library_size_bytes'):
            if key in pin: loader[key] = copy.deepcopy(pin[key])
    inherited = copy.deepcopy(go.get('inherited_limits', {'RLIMIT_AS': [-1, -1]}))
    capped = dict(inherited) if type(inherited) is dict else {'RLIMIT_AS': [-1, -1]}
    capped['RLIMIT_AS'] = [536870912, 536870912]
    output = '/literal-runner/temp/worker36-runner-preflight-9101-1'
    def process(child):
        command = [loader['executable_path'], '-B', '-s'] + (
            ['/literal-runner/work/scripts/worker36/runner_preflight.py', '--child', '--report', output + '/fresh-child.json']
            if child else ['scripts/worker36/runner_preflight.py', '--report', output + '/runner-preflight.json',
                           '--expected-head', go['head'], '--expected-tree', go['tree']])
        runtime = {**a.RUNTIME, 'executable': loader['executable_path'], 'flags': command,
            'effective_flags': {'dont_write_bytecode': 1, 'no_user_site': 1, 'ignore_environment': 0,
                                'isolated': 0, 'optimize': 0, 'no_site': 0},
            'python_environment': {'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1'},
            'gc_enabled': True, 'gc_threshold': [700, 10, 10],
            'address_space': [536870912, 536870912], 'loader': copy.deepcopy(loader)}
        initial = copy.deepcopy(runtime)
        if not child: initial['address_space'] = copy.deepcopy(inherited.get('RLIMIT_AS', [-1, -1])) if type(inherited) is dict else [-1, -1]
        return {**a.PREFLIGHT_ZERO, 'pid': 1202 if child else 1201, 'parent_pid': 1201 if child else 1200,
            'inherited_limits': copy.deepcopy(capped if child else inherited), 'capped_limits': copy.deepcopy(capped),
            'initial_runtime': initial, 'runtime': runtime, 'sanitized_environment': True,
            'shell_loader': {key: loader[key] for key in ('executable_path', 'library_directory', 'library_path',
                                                         'library_sha256', 'library_size_bytes')}}
    report = {**a.PREFLIGHT_ZERO, 'schema': 'worker36-runner-preflight-v1', 'success': True,
        'status': 'preparation_passed', 'repository': a.REPOSITORY, 'runner_name': 'bandido-alcatraz-ci',
        'diagnostic_head': go['head'], 'diagnostic_tree': go['tree'], 'workflow_run': '9101',
        'workflow_attempt': '1', 'event_name': 'pull_request', 'loader_pin': copy.deepcopy(go.get('loader_pin')),
        'checked_sources_unchanged_during_run': True, 'checked_file_sha256': pins, 'focused_source_receipt': receipt,
        'focused_tests': {**a.PREFLIGHT_ZERO, 'success': True, 'tests_run': 1, 'failures': 0, 'errors': 0,
                          'skipped': 0, 'test_modules': list(a.PREFLIGHT_TEST_MODULES), 'log': 'literal passed test\n'},
        'parent': process(False), 'fresh_child': process(True)}
    run = {'id': 9101, 'run_attempt': 1, 'url': a.API + '/actions/runs/9101', 'html_url': a.WEB + '/actions/runs/9101',
        'path': a.PREFLIGHT_WORKFLOW, 'event': 'pull_request', 'status': 'completed', 'conclusion': 'success',
        'head_branch': a.BRANCH, 'head_sha': go['head'], 'head_commit': {'id': go['head'], 'tree_id': go['tree']},
        'repository': copy.deepcopy(repo), 'head_repository': copy.deepcopy(repo),
        'actor': copy.deepcopy(owner), 'triggering_actor': copy.deepcopy(owner),
        'pull_requests': [{'number': pr_number, 'url': a.API + '/pulls/' + str(pr_number),
            'head': {'ref': a.BRANCH, 'sha': go['head'], 'repo': {'id': 314, 'url': a.API}},
            'base': {'ref': 'main', 'sha': a.BASE_HEAD, 'repo': {'id': 314, 'url': a.API}}}]}
    proofs['preflight-run.json'] = a.canonical(run)
    bound['runner_preflight'] = {'schema': 'worker36-preflight-binding-v1', 'run_id': 9101, 'run_attempt': 1,
        'artifact_id': 9201, 'artifact_name': 'worker36-zero-evaluator-preflight-9101-1',
        'checked_file_sha256': pins, 'focused_source_receipt': receipt}
    return rebind_literal_preflight(bound, proofs, report)


def rebind_literal_preflight(go, proof_bytes, report, *, members=None):
    """Rehash fixed mutated ZIP fixtures so tests reach the intended semantic gate."""
    bound, proofs = copy.deepcopy(go), copy.deepcopy(proof_bytes)
    report_raw = a.canonical(report)
    stream = io.BytesIO()
    loader = report['parent']['runtime']['loader']
    launcher = ('measurement_admitted=false\nevaluator_calls=0\nloader_setup_exit_code=0\n'
                + 'executable=' + loader['executable_path'] + '\n'
                + 'library=' + loader['library_path'] + '\n'
                + 'library_sha256=' + loader['library_sha256'] + '\n'
                + 'library_size_bytes=' + str(loader['library_size_bytes']) + '\nparent_exit_code=0\n')
    components = {name: b'' for name in a.PREFLIGHT_MEMBERS}
    components.update({'runner-preflight.json': report_raw, 'parent-runtime.json': a.canonical(report['parent']),
        'fresh-child.json': a.canonical(report['fresh_child']),
        'shell-loader.json': a.canonical(report['parent']['shell_loader']), 'launcher.txt': launcher.encode(),
        'fresh-child-process.json': a.canonical({**a.PREFLIGHT_ZERO,
            'command': report['fresh_child']['runtime']['flags'], 'pid': report['fresh_child']['pid'],
            'returncode': 0, 'timed_out': False})})
    entries = [(name, components[name]) for name in sorted(a.PREFLIGHT_MEMBERS)] \
        if members is None else members
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, raw in entries:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)); info.external_attr = (0o100600 << 16)
            archive.writestr(info, raw)
    raw_zip = stream.getvalue()
    descriptor = bound['runner_preflight']
    descriptor.update(artifact_sha256=a.sha(raw_zip), artifact_size_bytes=len(raw_zip),
                      report_sha256=a.sha(report_raw), report_size_bytes=len(report_raw))
    artifact = {'id': descriptor['artifact_id'], 'name': descriptor['artifact_name'], 'expired': False,
        'url': a.API + '/actions/artifacts/' + str(descriptor['artifact_id']),
        'archive_download_url': a.API + '/actions/artifacts/' + str(descriptor['artifact_id']) + '/zip',
        'digest': 'sha256:' + descriptor['artifact_sha256'], 'size_in_bytes': len(raw_zip),
        'workflow_run': {'id': descriptor['run_id'], 'head_sha': go['head'], 'head_branch': a.BRANCH,
                         'repository_id': 314, 'head_repository_id': 314}}
    proofs.update({'preflight-artifact.json': a.canonical(artifact), 'preflight.zip': raw_zip})
    return bound, proofs


def literal_auth_inputs(go=None, *, workflow_run='9001', cache='/literal-runner/tool-cache',
                        checkout='/literal-runner/work', temporary='/literal-runner/temp'):
    """Fixed invented GitHub objects; useful to other finite offline helper tests."""
    owner = {'login': 'carabinshely', 'id': 71, 'type': 'User'}
    repo = {'full_name': a.REPOSITORY, 'html_url': a.WEB, 'url': a.API, 'owner': owner}
    if go is None:
        go = {'schema': 'worker36-one-shot-admission-v1', 'admitted': True,
              'repository': a.REPOSITORY, 'branch': a.BRANCH,
              'preregistration_url': a.PREREGISTRATION,
              'admission_url': a.WEB + '/pull/41', 'head': '1' * 40, 'tree': '2' * 40,
              'loader_pin': copy.deepcopy(LITERAL_LOADER_PIN),
              'runtime': copy.deepcopy(a.RUNTIME), 'inherited_limits': {'RLIMIT_AS': [-1, -1]},
              'stub_test_receipt_sha256': '7' * 64,
              'diagnostic_files_sha256': {'scripts/worker36/admission.py': '8' * 64},
              'postmerge_ci': {'run_id': a.CI_RUN, 'head': a.BASE_HEAD,
                              'status': 'completed', 'conclusion': 'success'}}
        go, _ = literal_prerequisite_bundle(go, cache=cache)
    raw = a.canonical(go)
    body = 'Fixed literal stub admission\n' + a.START + '\n' + raw.decode() + a.END + '\n'
    body += a.DIGEST + ': ' + a.sha(raw) + '\n'
    pr = {'number': 41, 'html_url': a.WEB + '/pull/41', 'url': a.API + '/pulls/41',
          'issue_url': a.API + '/issues/41', 'state': 'open', 'merged': False,
          'merged_at': None, 'user': copy.deepcopy(owner), 'body': body,
          'head': {'ref': a.BRANCH, 'sha': '1' * 40, 'repo': copy.deepcopy(repo)},
          'base': {'ref': 'main', 'sha': a.BASE_HEAD, 'repo': copy.deepcopy(repo)}}
    event = {'action': 'edited', 'number': 41, 'repository': copy.deepcopy(repo),
             'sender': copy.deepcopy(owner), 'pull_request': copy.deepcopy(pr),
             'changes': {'body': {'from': 'Fixed pre-admission implementation body\n'}}}
    ci = {'id': a.CI_RUN, 'url': a.API + '/actions/runs/' + str(a.CI_RUN),
          'html_url': a.WEB + '/actions/runs/' + str(a.CI_RUN), 'repository': copy.deepcopy(repo),
          'head_sha': a.BASE_HEAD, 'head_branch': 'main', 'event': 'push',
          'path': '.github/workflows/test.yml', 'status': 'completed', 'conclusion': 'success'}
    durable = cache + '/worker36-evidence/run-' + workflow_run + '-attempt-1'
    attempt_id = 'worker36-' + workflow_run + '-1'
    context = {'schema': 'worker36-github-request-context-v1', 'repository': a.REPOSITORY,
               'event_name': 'pull_request', 'workflow_run': workflow_run, 'workflow_attempt': '1',
               'server_url': 'https://github.com', 'api_url': 'https://api.github.com',
               'authentication': 'github-repository-read-token',
               'pull_request_request': {'method': 'GET', 'url': a.API + '/pulls/41'},
               'postmerge_ci_request': {'method': 'GET', 'url': a.API + '/actions/runs/' + str(a.CI_RUN)},
               'runner_name': 'bandido-alcatraz-ci', 'actor': a.OWNER,
               'run_url': a.WEB + '/actions/runs/' + workflow_run, 'attempt_id': attempt_id,
               'runner_tool_cache': cache, 'checkout_path': checkout, 'runner_temp': temporary,
               'durable_root': durable, 'attempt_path': durable + '/' + attempt_id}
    return event, pr, ci, context, raw


def write_literal_auth_inputs(folder, go=None, *, focused_source_receipt=None, checked_file_sha256=None, **options):
    """Retain literal fixtures and genuinely reconcile them, without any bypass."""
    folder = Path(folder)
    folder.mkdir(parents=True, mode=0o700, exist_ok=True)
    event, pr, ci, context, raw = literal_auth_inputs(go, **options)
    bound, proofs = literal_prerequisite_bundle(a.strict_json(raw), cache=options.get('cache', '/literal-runner/tool-cache'),
        focused_source_receipt=focused_source_receipt, checked_file_sha256=checked_file_sha256)
    event, pr, ci, context, raw = literal_auth_inputs(bound, **options)
    values = dict(zip(a.INPUT_NAMES[:4], (event, pr, ci, context)))
    for name, value in values.items():
        (folder / name).write_bytes(a.canonical(value))
    for name, value in proofs.items():
        (folder / name).write_bytes(value)
    actual, provenance = a.extract_pr_admission(event, pr, ci)
    if actual != raw:
        raise ValueError('literal helper raw mismatch')
    provenance.update(a.verified_context(context, provenance, context['workflow_run'], '1'))
    provenance.update(a.validate_prerequisites(bound, provenance, proofs))
    provenance['admission_input_hashes'] = {name: a.sha((folder / name).read_bytes()) for name in a.INPUT_NAMES}
    (folder / 'admission.json').write_bytes(raw)
    (folder / 'provenance.json').write_bytes(a.canonical(provenance))
    verified = a.verify_provenance(folder / 'provenance.json', folder / 'admission.json', a.sha(raw))
    return raw, verified


class AdmissionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.event, self.pr, self.ci, self.context, self.raw = literal_auth_inputs()

    def reject(self, event=None, pr=None, ci=None):
        with self.assertRaises(a.AdmissionError):
            a.extract_pr_admission(self.event if event is None else event,
                                   self.pr if pr is None else pr, self.ci if ci is None else ci)

    def bodies(self, body):
        event, pr = copy.deepcopy(self.event), copy.deepcopy(self.pr)
        event['pull_request']['body'] = pr['body'] = body
        return event, pr

    def isolated_cli_main(self, args):
        """Exercise the production cap transition without mutating the test host."""
        real_getrlimit = a.resource.getrlimit
        target = a.resource.RLIMIT_AS
        before = real_getrlimit(target)
        unlimited = (a.resource.RLIM_INFINITY,) * 2
        capped = (512 * 1024 ** 2,) * 2
        try:
            with patch.object(a.resource, 'getrlimit', side_effect=[unlimited, capped]) as get_limit, \
                    patch.object(a.resource, 'setrlimit') as set_limit:
                try:
                    return a.main(args)
                finally:
                    self.assertEqual(get_limit.call_args_list, [call(target), call(target)])
                    set_limit.assert_called_once_with(target, capped)
        finally:
            after = real_getrlimit(target)
            CLI_LIMIT_OBSERVATIONS.append({'test': self._testMethodName,
                'before': list(before), 'after': list(after),
                'mocked_transition': [list(unlimited), list(capped)]})
            self.assertEqual(after, before, 'admission CLI test changed the real process limits')

    def prerequisite_fixture(self):
        go, proofs = literal_prerequisite_bundle(a.strict_json(self.raw))
        provenance = a.extract_pr_admission(self.event, self.pr, self.ci)[1]
        return go, provenance, proofs

    def reject_prerequisite(self, go, provenance, proofs):
        with self.assertRaises(a.AdmissionError): a.validate_prerequisites(go, provenance, proofs)

    def altered_review_body(self, go, proofs, body):
        go, proofs = copy.deepcopy(go), copy.deepcopy(proofs)
        comment = a.strict_json(proofs['review-exhaustive.json']); comment['body'] = body
        go['reviews'][0]['body_sha256'] = a.sha(body.encode())
        proofs['review-exhaustive.json'] = a.canonical(comment)
        return go, proofs

    def test_A01_valid_first_admission(self):
        raw, provenance = a.extract_pr_admission(self.event, self.pr, self.ci)
        self.assertEqual(raw, self.raw)
        self.assertTrue(provenance['first_admission'])
        self.assertEqual(provenance['admission_url'], a.WEB + '/pull/41')
        self.assertEqual(provenance['head'], '1' * 40)
        self.assertEqual(provenance['postmerge_ci']['run_id'], a.CI_RUN)

    def test_A02_unauthorized_identity(self):
        for target in ('sender', 'event_author', 'live_author', 'owner', 'sender_id'):
            event, pr = copy.deepcopy(self.event), copy.deepcopy(self.pr)
            if target == 'sender': event['sender']['login'] = 'other'
            if target == 'event_author': event['pull_request']['user']['login'] = 'other'
            if target == 'live_author': pr['user']['login'] = 'other'
            if target == 'owner': event['repository']['owner']['login'] = 'other'
            if target == 'sender_id': event['sender']['id'] = 72
            with self.subTest(target=target): self.reject(event, pr)

    def test_A03_stale_and_wrong_destination(self):
        for target in ('head', 'body', 'base', 'repository', 'number', 'html_url', 'url', 'issue_url'):
            pr = copy.deepcopy(self.pr)
            if target == 'head': pr['head']['sha'] = '3' * 40
            elif target == 'body': pr['body'] += 'stale\n'
            elif target == 'base': pr['base']['sha'] = '3' * 40
            elif target == 'repository': pr['head']['repo']['full_name'] = 'other/fork'
            elif target == 'number': pr['number'] = 42
            else: pr[target] = 'https://example.invalid/wrong'
            with self.subTest(target=target): self.reject(pr=pr)

    def test_A04_first_body_transition_only(self):
        for previous in (self.pr['body'], a.START, a.END, a.DIGEST):
            event = copy.deepcopy(self.event); event['changes']['body']['from'] = previous
            with self.subTest(previous=previous): self.reject(event)
        event = copy.deepcopy(self.event); event['changes'] = {}; self.reject(event)
        event = copy.deepcopy(self.event); event['action'] = 'synchronize'; self.reject(event)
        for field, value in (('state', 'closed'), ('merged', True), ('merged_at', '2026-01-01T00:00:00Z')):
            pr = copy.deepcopy(self.pr); pr[field] = value; self.reject(pr=pr)
        pr = copy.deepcopy(self.pr); pr['head']['ref'] = 'other-branch'; self.reject(pr=pr)

    def test_A05_bounded_literal_markers_and_json(self):
        body = self.pr['body']
        cases = ['', a.START, body + body, body + a.DIGEST + ': ' + '0' * 64,
                 body.replace(a.DIGEST + ': ', a.DIGEST + ':'),
                 body.replace(a.sha(self.raw), '0' * 64),
                 'x' * (a.MAX_BODY_BYTES + 1), body.replace('\n', '\r\n')]
        for payload in (b'', b'{"admitted":true,"admitted":false}\n', b'{"x":NaN}\n', b' ' * (a.MAX_GO_BYTES + 1)):
            cases.append(a.START + '\n' + payload.decode() + a.END + '\n' + a.DIGEST + ': ' + a.sha(payload) + '\n')
        for index, invalid in enumerate(cases):
            with self.subTest(case=index): self.reject(*self.bodies(invalid))

    def test_A06_GO_identity(self):
        go = a.strict_json(self.raw)
        mutations = {'preregistration_url': a.WEB + '/issues/3#issuecomment-1',
                     'admission_url': a.WEB + '/pull/42', 'head': '3' * 40, 'tree': 'not-a-tree',
                     'repository': 'other/repo', 'branch': 'main', 'schema': 'other', 'admitted': False}
        for field, value in mutations.items():
            bad = copy.deepcopy(go); bad[field] = value
            event, pr, ci, _, _ = literal_auth_inputs(bad)
            with self.subTest(field=field): self.reject(event, pr, ci)

    def test_A07_CI_provenance(self):
        changes = {'id': 1, 'head_sha': '3' * 40, 'head_branch': 'other', 'event': 'pull_request',
                   'path': '.github/workflows/other.yml', 'url': a.API + '/actions/runs/1',
                   'html_url': a.WEB + '/actions/runs/1', 'status': 'in_progress', 'conclusion': 'failure'}
        for field, value in changes.items():
            ci = copy.deepcopy(self.ci); ci[field] = value
            with self.subTest(field=field): self.reject(ci=ci)
        ci = copy.deepcopy(self.ci); ci['repository']['full_name'] = 'other/repo'; self.reject(ci=ci)

    def test_A08_optimization_cannot_erase_auth(self):
        source = Path(a.__file__).read_text()
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(ast.parse(source))))
        namespace = {'__name__': 'literal_worker36_auth_optimized', '__file__': a.__file__}
        exec(compile(source, a.__file__, 'exec', optimize=2), namespace)
        event = copy.deepcopy(self.event); event['sender']['login'] = 'other'
        with self.assertRaises(namespace['AdmissionError']):
            namespace['extract_pr_admission'](event, self.pr, self.ci)
        event, pr = self.bodies(self.pr['body'].replace(a.sha(self.raw), '0' * 64))
        with self.assertRaises(namespace['AdmissionError']):
            namespace['extract_pr_admission'](event, pr, self.ci)

    def test_A09_CLI_and_retained_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache, checkout, temporary = root / 'cache', root / 'work', root / 'temp'
            for path in (cache, checkout, temporary): path.mkdir()
            folder = cache / 'worker36-evidence/run-9001-attempt-1/admission-inputs'
            folder.mkdir(parents=True, mode=0o700)
            event, pr, ci, context, raw = literal_auth_inputs(cache=str(cache), checkout=str(checkout), temporary=str(temporary))
            for name, value in zip(a.INPUT_NAMES, (event, pr, ci, context)):
                (folder / name).write_bytes(a.canonical(value))
            _, proofs = literal_prerequisite_bundle(a.strict_json(raw), cache=str(cache))
            for name, value in proofs.items(): (folder/name).write_bytes(value)
            args = ['authenticate', '--event', str(folder/'event.json'), '--pull-request', str(folder/'pull-request.json'),
                    '--ci', str(folder/'postmerge-ci.json'), '--request-context', str(folder/'request-context.json'),
                    '--destination', str(folder/'admission.json'), '--provenance', str(folder/'provenance.json'),
                    '--workflow-run', '9001', '--workflow-attempt', '1', '--expected-head', '1' * 40,
                    '--expected-tree', '2' * 40, '--handoff', str(folder/'authenticated-handoff.env')]
            env = {'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1', 'RUNNER_TOOL_CACHE': str(cache),
                   'GITHUB_WORKSPACE': str(checkout), 'RUNNER_TEMP': str(temporary), 'GITHUB_RUN_ID': '9001',
                   'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_EVENT_NAME': 'pull_request', 'GITHUB_REPOSITORY': a.REPOSITORY,
                   'GITHUB_ACTOR': a.OWNER, 'RUNNER_NAME': 'bandido-alcatraz-ci'}
            flags = types.SimpleNamespace(dont_write_bytecode=1, no_user_site=1, optimize=0,
                                          ignore_environment=0, isolated=0, no_site=0, verbose=0)
            observed = literal_loader_identity(str(cache))
            env.update(observed['loader_environment'])
            env.update(literal_shell_loader(observed))
            with patch.dict(a.os.environ, env, clear=True), patch.object(a.sys, 'flags', flags), \
                    patch.object(a, 'loader_identity', return_value=observed):
                self.assertEqual(self.isolated_cli_main(args), 0)
                with self.assertRaises(FileExistsError): self.isolated_cli_main(args)
                a.os.environ['PYTHONOPTIMIZE'] = '1'
                with self.assertRaises(a.AdmissionError): a.validate_interpreter()
                del a.os.environ['PYTHONOPTIMIZE']; flags.optimize = 1
                with self.assertRaises(a.AdmissionError): a.validate_interpreter()
            provenance = a.verify_provenance(folder/'provenance.json', folder/'admission.json', a.sha(raw))
            self.assertEqual(provenance['attempt_path'], context['attempt_path'])
            self.assertEqual(provenance['workflow_run'], '9001')
            original = (folder/'event.json').read_bytes()
            (folder/'event.json').write_bytes(original + b' ')
            with self.assertRaises(a.AdmissionError):
                a.verify_provenance(folder/'provenance.json', folder/'admission.json', a.sha(raw))
            (folder/'event.json').write_bytes(original)
            (folder/'link.json').symlink_to(folder/'event.json')
            with self.assertRaises(a.AdmissionError): a.read_input(folder/'link.json')
            for key, value in (('workflow_attempt', '2'), ('attempt_path', '/outside/attempt'),
                               ('checkout_path', str(cache)), ('workflow_run', '9002')):
                bad = copy.deepcopy(context); bad[key] = value
                (folder/'request-context.json').write_bytes(a.canonical(bad))
                with self.assertRaises(a.AdmissionError):
                    a.verify_provenance(folder/'provenance.json', folder/'admission.json', a.sha(raw))

    def test_A10_static_workflow_contract(self):
        source = (ROOT/'.github/workflows/worker36-synthetic-profile.yml').read_text()
        self.assertIn('types: [edited]', source)
        self.assertIn('branches: [main]', source)
        self.assertNotIn('workflow_dispatch:', source)
        self.assertNotIn('${{ runner.temp }}', source)
        self.assertNotIn('${{ runner.tool_cache }}', source)
        self.assertNotIn(' || true\n            python', source)
        for literal in ('github.event.sender.login', 'github.event.pull_request.base.sha',
                        '!contains(github.event.changes.body.from', 'github.run_attempt == 1',
                        '"$cache/worker36-evidence"', '"$cache/worker36-one-shot-claims"',
                        '"$GITHUB_EVENT_PATH"', '"$GITHUB_ENV"', 'gh api --hostname github.com --method GET',
                        '--admission-provenance-sha256', '--expected-workflow-run', '--recovery-report',
                        'test "$(stat -c %u', 'mkdir -m 700 -- "$durable"'):
            self.assertIn(literal, source)
        self.assertNotIn('rm -', source)
        for step in source.split('      - '):
            if '"$WORKER36_PYTHON" -B -s ' in step:
                self.assertIn('source "$GITHUB_WORKSPACE/scripts/worker36-loader.sh"', step)
                self.assertLess(step.index('worker36_loader_setup'), step.index('"$WORKER36_PYTHON" -B -s '))
        self.assertIn('"$GITHUB_WORKSPACE/scripts/run_worker36_synthetic.py" measure', source)
        self.assertIn('"$GITHUB_WORKSPACE/scripts/run_worker36_synthetic.py" preserve', source)

    def test_A11_loader_pin_required_and_exact(self):
        go = a.strict_json(self.raw)
        for field, value in (('schema', 'other'), ('executable_sha256', '5' * 64),
                             ('library_relative_path', '../libpython3.11.so.1.0'),
                             ('library_sha256', 'invalid'), ('library_size_bytes', 0),
                             ('library_size_bytes', True), ('extra', 'forbidden')):
            bad = copy.deepcopy(go); bad['loader_pin'][field] = value
            event, pr, ci, _, _ = literal_auth_inputs(bad)
            with self.subTest(field=field, value=value): self.reject(event, pr, ci)
        missing = copy.deepcopy(go); del missing['loader_pin']
        event, pr, ci, _, _ = literal_auth_inputs(missing)
        self.reject(event, pr, ci)
        self.assertEqual(a.extract_pr_admission(self.event, self.pr, self.ci)[0], self.raw)

    def test_A12_authentication_binds_observed_loader(self):
        variants = ('matching', 'library_hash', 'library_size', 'actor', 'head',
                    'pythonoptimize', 'loader_observation')
        with tempfile.TemporaryDirectory() as directory:
            for variant in variants:
                with self.subTest(variant=variant):
                    root = Path(directory)/variant
                    cache, checkout, temporary = root/'cache', root/'work', root/'temp'
                    for path in (cache, checkout, temporary): path.mkdir(parents=True)
                    folder = cache/'worker36-evidence/run-9001-attempt-1/admission-inputs'
                    folder.mkdir(parents=True, mode=0o700)
                    event, pr, ci, context, raw = literal_auth_inputs(
                        cache=str(cache), checkout=str(checkout), temporary=str(temporary))
                    if variant == 'head': pr['head']['sha'] = '3' * 40
                    for name, value in zip(a.INPUT_NAMES, (event, pr, ci, context)):
                        (folder/name).write_bytes(a.canonical(value))
                    _, proofs = literal_prerequisite_bundle(a.strict_json(raw), cache=str(cache))
                    for name, value in proofs.items(): (folder/name).write_bytes(value)
                    args = ['authenticate', '--event', str(folder/'event.json'),
                            '--pull-request', str(folder/'pull-request.json'), '--ci', str(folder/'postmerge-ci.json'),
                            '--request-context', str(folder/'request-context.json'), '--destination', str(folder/'admission.json'),
                            '--provenance', str(folder/'provenance.json'), '--workflow-run', '9001', '--workflow-attempt', '1']
                    args += ['--expected-head', '1' * 40, '--expected-tree', '2' * 40,
                             '--handoff', str(folder/'authenticated-handoff.env')]
                    observed = literal_loader_identity(str(cache))
                    if variant == 'library_hash': observed['library_sha256'] = '5' * 64
                    if variant == 'library_size': observed['library_size_bytes'] = 4097
                    env = {'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1',
                           'RUNNER_TOOL_CACHE': str(cache), 'GITHUB_WORKSPACE': str(checkout),
                           'RUNNER_TEMP': str(temporary), 'GITHUB_RUN_ID': '9001', 'GITHUB_RUN_ATTEMPT': '1',
                           'GITHUB_EVENT_NAME': 'pull_request', 'GITHUB_REPOSITORY': a.REPOSITORY,
                           'GITHUB_ACTOR': 'other' if variant == 'actor' else a.OWNER,
                           'RUNNER_NAME': 'bandido-alcatraz-ci', **observed['loader_environment']}
                    env.update(literal_shell_loader(observed))
                    if variant == 'pythonoptimize': env['PYTHONOPTIMIZE'] = '1'
                    flags = types.SimpleNamespace(dont_write_bytecode=1, no_user_site=1,
                                optimize=0, ignore_environment=0, isolated=0, no_site=0, verbose=0)
                    observation_error = a.LoaderIntegrityError('literal unverified mapped loader') \
                        if variant == 'loader_observation' else None
                    with patch.dict(a.os.environ, env, clear=True), patch.object(a.sys, 'flags', flags), \
                            patch.object(a, 'loader_identity', return_value=observed, side_effect=observation_error):
                        if variant == 'matching':
                            self.assertEqual(self.isolated_cli_main(args), 0)
                        else:
                            with self.assertRaises(a.AdmissionError): self.isolated_cli_main(args)
                    self.assertEqual((folder/'admission.json').exists(), variant == 'matching')
                    self.assertEqual((folder/'provenance.json').exists(), variant == 'matching')

    def test_A13_loader_helper_workflow_contract(self):
        workflow = (ROOT/'.github/workflows/worker36-synthetic-profile.yml').read_text()
        authentication = next(step for step in workflow.split('      - ') if 'id: admission' in step)
        self.assertLess(authentication.index('worker36_loader_setup'),
                        authentication.index('scripts/worker36/admission.py authenticate'))
        source = Path(a.__file__).read_text()
        self.assertIn('observed_loader = validate_interpreter()', source)
        self.assertIn("admitted_loader_pin(strict_json(raw)['loader_pin']) == loader_pin(observed_loader)", source)
        driver = (ROOT/'scripts/worker36/driver.py').read_text()
        definition = next(node for node in ast.parse(driver).body if isinstance(node, ast.FunctionDef)
                          and node.name == 'required_diagnostic_paths')
        self.assertIn('scripts/worker36-loader.sh',
                      [node.value for node in ast.walk(definition) if isinstance(node, ast.Constant)])

    def test_A14_P06_request_context_exact_and_quoted_paths(self):
        self.assertTrue(hasattr(a, 'request_context_from_environment'), 'fixed-purpose context serializer missing')
        contexts = [self.context, literal_auth_inputs(cache='/literal-runner/cache"quoted\\name',
                    checkout='/literal-runner/work"quoted', temporary='/literal-runner/temp\\name')[3]]
        for context in contexts:
            env = literal_context_environment(context)
            self.assertEqual(a.request_context_from_environment(env), context)
            self.assertEqual(a.strict_json(a.canonical(a.request_context_from_environment(env))), context)
        variants = (('GITHUB_RUN_ID', None), ('GITHUB_RUN_ATTEMPT', '2'), ('PR_NUMBER', '41\n42'),
                    ('GITHUB_REPOSITORY', 'other/repo'), ('GITHUB_WORKSPACE', 'relative'),
                    ('AUTH', '/outside/admission-inputs'), ('DURABLE', '/outside/run'))
        for key, value in variants:
            with self.subTest(key=key):
                env = literal_context_environment(self.context)
                if value is None: del env[key]
                else: env[key] = value
                with self.assertRaises(a.AdmissionError): a.request_context_from_environment(env)

    def test_A15_P07_authenticated_handoff_exact_and_mismatches(self):
        self.assertTrue(hasattr(a, 'authentication_handoff'), 'fixed-purpose authentication handoff missing')
        raw, provenance = a.extract_pr_admission(self.event, self.pr, self.ci)
        observed = literal_loader_identity()
        kwargs = {'expected_head': '1' * 40, 'expected_tree': '2' * 40,
                  'admission_sha256': a.sha(raw), 'shell_loader': literal_shell_loader(observed)}
        result = a.authentication_handoff(raw, provenance, observed, **kwargs)
        values = dict(line.split('=', 1) for line in result.decode().splitlines())
        self.assertEqual(values, {'ADMISSION_SHA256': a.sha(raw),
            'ADMISSION_PROVENANCE_SHA256': a.sha(a.canonical(provenance)), 'EXPECTED_TREE': '2' * 40,
            'WORKER36_PRESERVE_EXECUTABLE': observed['executable_path'],
            'WORKER36_PRESERVE_LIBRARY_DIRECTORY': observed['library_directory'],
            'WORKER36_PRESERVE_LIBRARY_SHA256': observed['library_sha256'],
            'WORKER36_PRESERVE_LIBRARY_SIZE_BYTES': str(observed['library_size_bytes'])})
        for field, value in (('expected_head', '3' * 40), ('expected_tree', '3' * 40),
                             ('admission_sha256', '5' * 64), ('WORKER36_LOADER_SHA256', '5' * 64),
                             ('WORKER36_LOADER_SIZE_BYTES', '4097')):
            with self.subTest(field=field):
                bad = copy.deepcopy(kwargs)
                if field.startswith('WORKER36_'): bad['shell_loader'][field] = value
                else: bad[field] = value
                with self.assertRaises(a.AdmissionError): a.authentication_handoff(raw, provenance, observed, **bad)

    def test_A16_P08_no_jq_and_metadata_after_loader(self):
        source = (ROOT/'.github/workflows/worker36-synthetic-profile.yml').read_text()
        self.assertNotIn('jq', source)
        auth = next(step for step in source.split('      - ') if 'id: admission' in step)
        self.assertLess(source.index('uses: actions/checkout@v4'), source.index('admission.py request-context'))
        self.assertLess(source.index('uses: actions/setup-python@v5'), source.index('admission.py request-context'))
        self.assertLess(auth.index('worker36_loader_setup'), auth.index('admission.py request-context'))
        self.assertLess(auth.index('admission.py request-context'), auth.index('admission.py authenticate'))
        for literal in ('"$GITHUB_EVENT_PATH"', '"$AUTH/pull-request.json"', '"$AUTH/postmerge-ci.json"',
                        '--request-context "$AUTH/request-context.json"', '--expected-head "$EXPECTED_HEAD"',
                        '--expected-tree "$tree"', '--handoff "$AUTH/authenticated-handoff.env"'):
            self.assertIn(literal, source)
        self.assertIn('cat -- "$AUTH/authenticated-handoff.env" >> "$GITHUB_ENV"', auth)
        self.assertNotIn('continue-on-error', source)

    def test_A17_P09_measurement_uses_authenticated_library_fields(self):
        source = (ROOT/'.github/workflows/worker36-synthetic-profile.yml').read_text()
        measurement = next(step for step in source.split('      - ') if 'id: measurement' in step)
        self.assertIn('worker36_loader_setup "$WORKER36_PRESERVE_LIBRARY_SHA256" "$WORKER36_PRESERVE_LIBRARY_SIZE_BYTES"', measurement)
        self.assertNotIn('jq', measurement)
        self.assertNotIn('json', measurement.split('worker36_loader_setup', 1)[0])
        self.assertLess(measurement.index('worker36_loader_setup'), measurement.index('scripts/run_worker36_synthetic.py" measure'))

    def test_A18_P10_preservation_run_is_byte_identical(self):
        source = (ROOT/'.github/workflows/worker36-synthetic-profile.yml').read_bytes()
        marker = b'      - name: Preserve verification result and all partial transport without retry\n'
        preserved = source.split(marker, 1)[1].split(b'        run: |\n', 1)[1].split(b'      - uses:', 1)[0]
        self.assertEqual(len(preserved), 5304)
        self.assertEqual(a.sha(preserved), '81450dce731726fd3cad88f95681a64682773a498158b3930ecd42e546342a27')

    def test_A19_P11_metadata_failure_publishes_no_success(self):
        self.assertTrue(hasattr(a, 'request_context_from_environment'), 'fixed-purpose metadata entry missing')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache, checkout, temporary = root/'cache', root/'work', root/'temp'
            for path in (cache, checkout, temporary): path.mkdir()
            folder = cache/'worker36-evidence/run-9001-attempt-1/admission-inputs'
            folder.mkdir(parents=True, mode=0o700)
            event, pr, ci, context, raw = literal_auth_inputs(cache=str(cache), checkout=str(checkout), temporary=str(temporary))
            env = literal_context_environment(context)
            env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1')
            observed = literal_loader_identity(str(cache))
            env.update(observed['loader_environment']); env.update(literal_shell_loader(observed))
            flags = types.SimpleNamespace(dont_write_bytecode=1, no_user_site=1, optimize=0,
                                          ignore_environment=0, isolated=0, no_site=0, verbose=0)
            with patch.dict(a.os.environ, env, clear=True), patch.object(a.sys, 'flags', flags), \
                    patch.object(a, 'loader_identity', return_value=observed):
                del a.os.environ['GITHUB_RUN_ID']
                with self.assertRaises(a.AdmissionError):
                    self.isolated_cli_main(['request-context', '--destination', str(folder/'request-context.json')])
                self.assertFalse((folder/'request-context.json').exists())
                a.os.environ['GITHUB_RUN_ID'] = '9001'
                self.assertEqual(self.isolated_cli_main(['request-context', '--destination', str(folder/'request-context.json')]), 0)
                self.assertEqual(a.strict_json((folder/'request-context.json').read_bytes()), context)
                with self.assertRaises(FileExistsError):
                    self.isolated_cli_main(['request-context', '--destination', str(folder/'request-context.json')])
                for name, value in zip(a.INPUT_NAMES[:3], (event, pr, ci)):
                    (folder/name).write_bytes(a.canonical(value))
                _, proofs = literal_prerequisite_bundle(a.strict_json(raw), cache=str(cache))
                for name, value in proofs.items(): (folder/name).write_bytes(value)
                args = ['authenticate', '--event', str(folder/'event.json'), '--pull-request', str(folder/'pull-request.json'),
                        '--ci', str(folder/'postmerge-ci.json'), '--request-context', str(folder/'request-context.json'),
                        '--destination', str(folder/'admission.json'), '--provenance', str(folder/'provenance.json'),
                        '--workflow-run', '9001', '--workflow-attempt', '1', '--expected-head', '3' * 40,
                        '--expected-tree', '2' * 40, '--handoff', str(folder/'authenticated-handoff.env')]
                with self.assertRaises(a.AdmissionError): self.isolated_cli_main(args)
                for name in ('admission.json', 'provenance.json', 'authenticated-handoff.env'):
                    self.assertFalse((folder/name).exists())

    def test_A20_ER_A01_owner_attests_distinct_native_reviews(self):
        go, provenance, proofs = self.prerequisite_fixture()
        result = a.validate_prerequisites(go, provenance, proofs)
        self.assertEqual(result['reviews'], go['reviews'])
        self.assertEqual(result['runner_preflight'], go['runner_preflight'])
        users = [a.strict_json(proofs[name])['user'] for name in a.PREREQUISITE_NAMES[:2]]
        self.assertEqual(users[0], users[1])
        self.assertNotEqual(go['reviews'][0]['native_reviewer_id'], go['reviews'][1]['native_reviewer_id'])

    def test_A21_ER_A02_comment_identity_and_body_binding(self):
        go, provenance, proofs = self.prerequisite_fixture()
        for field, value in (('id', 1), ('url', a.API + '/issues/comments/1'),
                             ('html_url', a.WEB + '/pull/42#issuecomment-8101'),
                             ('issue_url', a.API + '/issues/42'), ('body', 'changed')):
            with self.subTest(field=field):
                bad = copy.deepcopy(proofs); record = a.strict_json(bad['review-exhaustive.json'])
                record[field] = value; bad['review-exhaustive.json'] = a.canonical(record)
                self.reject_prerequisite(go, provenance, bad)
        bad = copy.deepcopy(proofs); record = a.strict_json(bad['review-exhaustive.json'])
        record['user']['id'] = 72; bad['review-exhaustive.json'] = a.canonical(record)
        self.reject_prerequisite(go, provenance, bad)
        bad = copy.deepcopy(proofs); del bad['review-exhaustive.json']
        self.reject_prerequisite(go, provenance, bad)

    def test_A22_ER_A03_only_bounded_structured_attestations(self):
        go, provenance, proofs = self.prerequisite_fixture()
        body = a.strict_json(proofs['review-exhaustive.json'])['body']
        record = a.strict_json(body[len(a.REVIEW_START)+1:-(len(a.REVIEW_END)+1)])
        bad_schema = copy.deepcopy(record); bad_schema['schema'] = 'other'
        bodies = ('looks clean', body + body, a.REVIEW_START + '\n{}\n',
                  'x' * (a.MAX_BODY_BYTES + 1),
                  a.REVIEW_START + '\n{"schema":1,"schema":2}\n' + a.REVIEW_END + '\n',
                  a.REVIEW_START + '\n' + a.canonical(bad_schema).decode() + a.REVIEW_END + '\n')
        for index, value in enumerate(bodies):
            with self.subTest(case=index):
                bound, bad = self.altered_review_body(go, proofs, value)
                self.reject_prerequisite(bound, provenance, bad)
        bad = copy.deepcopy(go); bad['reviews'][0]['url'] = a.WEB + '/blob/main/README.md'
        self.reject_prerequisite(bad, provenance, proofs)

    def test_A23_ER_A04_review_identity_and_clean_scope(self):
        go, provenance, proofs = self.prerequisite_fixture()
        for key in ('role', 'comment_id', 'native_reviewer_id'):
            bad = copy.deepcopy(go); bad['reviews'][1][key] = bad['reviews'][0][key]
            with self.subTest(duplicate=key): self.reject_prerequisite(bad, provenance, proofs)
        original_body = a.strict_json(proofs['review-exhaustive.json'])['body']
        original = a.strict_json(original_body[len(a.REVIEW_START)+1:-(len(a.REVIEW_END)+1)])
        for field, value in (('verdict', 'not-clean'), ('complete_review', False),
                             ('independent_review_attested', False), ('actionable_findings', {'P0': 0, 'P1': 1, 'P2': 0, 'P3': 0}),
                             ('head', '3' * 40), ('tree', '3' * 40), ('handoff_sha256', '3' * 64),
                             ('report_sha256', '3' * 64)):
            with self.subTest(field=field):
                record = copy.deepcopy(original); record[field] = value
                body = a.REVIEW_START + '\n' + a.canonical(record).decode() + a.REVIEW_END + '\n'
                bound, bad = self.altered_review_body(go, proofs, body)
                self.reject_prerequisite(bound, provenance, bad)

    def test_A24_ER_P01_exact_run_artifact_report_chain(self):
        go, provenance, proofs = self.prerequisite_fixture()
        report = a._preflight_report_from_zip(proofs['preflight.zip'], go['runner_preflight'])
        self.assertEqual(report['diagnostic_head'], go['head'])
        self.assertEqual(report['diagnostic_tree'], go['tree'])
        self.assertEqual(a.validate_prerequisites(go, provenance, proofs)['runner_preflight'], go['runner_preflight'])

    def test_A25_ER_P02_preflight_run_gate(self):
        go, provenance, proofs = self.prerequisite_fixture()
        variants = [('status', 'queued'), ('status', 'in_progress'), ('conclusion', 'failure'),
                    ('conclusion', 'skipped'), ('conclusion', 'cancelled'), ('path', '.github/workflows/test.yml'),
                    ('event', 'push'), ('head_branch', 'other'), ('head_sha', '3' * 40), ('run_attempt', 2)]
        for field, value in variants:
            with self.subTest(field=field, value=value):
                bad = copy.deepcopy(proofs); run = a.strict_json(bad['preflight-run.json']); run[field] = value
                bad['preflight-run.json'] = a.canonical(run); self.reject_prerequisite(go, provenance, bad)
        for path, value in ((('head_commit', 'tree_id'), '3' * 40), (('repository', 'full_name'), 'other/repo'),
                            (('actor', 'id'), 72), (('triggering_actor', 'login'), 'other')):
            bad = copy.deepcopy(proofs); run = a.strict_json(bad['preflight-run.json']); run[path[0]][path[1]] = value
            bad['preflight-run.json'] = a.canonical(run); self.reject_prerequisite(go, provenance, bad)
        bad = copy.deepcopy(proofs); run = a.strict_json(bad['preflight-run.json']); run['pull_requests'][0]['number'] = 42
        bad['preflight-run.json'] = a.canonical(run); self.reject_prerequisite(go, provenance, bad)

    def test_A26_ER_P03_artifact_identity_and_bytes(self):
        go, provenance, proofs = self.prerequisite_fixture()
        for field, value in (('id', 1), ('name', 'wrong'), ('expired', True), ('digest', 'sha256:' + '3' * 64),
                             ('size_in_bytes', 1)):
            with self.subTest(field=field):
                bad = copy.deepcopy(proofs); artifact = a.strict_json(bad['preflight-artifact.json']); artifact[field] = value
                bad['preflight-artifact.json'] = a.canonical(artifact); self.reject_prerequisite(go, provenance, bad)
        bad = copy.deepcopy(proofs); artifact = a.strict_json(bad['preflight-artifact.json']); artifact['workflow_run']['id'] = 2
        bad['preflight-artifact.json'] = a.canonical(artifact); self.reject_prerequisite(go, provenance, bad)
        bad = copy.deepcopy(proofs); bad['preflight.zip'] += b'x'; self.reject_prerequisite(go, provenance, bad)
        for field in ('artifact_sha256', 'report_sha256'):
            bound = copy.deepcopy(go); bound['runner_preflight'][field] = '3' * 64
            self.reject_prerequisite(bound, provenance, proofs)

    def test_A27_ER_P04_safe_bounded_preflight_zip(self):
        go, provenance, proofs = self.prerequisite_fixture()
        report = a._preflight_report_from_zip(proofs['preflight.zip'], go['runner_preflight'])
        entries = [(name, a.canonical(report) if name == 'runner-preflight.json' else b'') for name in sorted(a.PREFLIGHT_MEMBERS)]
        for name, members in (('duplicate', entries + [('runner-preflight.json', a.canonical(report))]),
                              ('traversal', entries + [('../escape', b'')]),
                              ('missing', [(name, raw) for name, raw in entries if name != 'runner-preflight.json'])):
            with self.subTest(variant=name):
                bound, bad = rebind_literal_preflight(go, proofs, report, members=members)
                self.reject_prerequisite(bound, provenance, bad)
        for variant in ('link', 'encrypted', 'uncompressed_overflow'):
            with self.subTest(variant=variant):
                raw = bytearray(proofs['preflight.zip']); central = raw.index(b'PK\x01\x02')
                if variant == 'link': struct.pack_into('<I', raw, central + 38, 0o120777 << 16)
                elif variant == 'encrypted':
                    flags, = struct.unpack_from('<H', raw, central + 8); struct.pack_into('<H', raw, central + 8, flags | 1)
                else: struct.pack_into('<I', raw, central + 24, a.MAX_INPUT_BYTES + 1)
                bound, bad = copy.deepcopy(go), copy.deepcopy(proofs)
                bound['runner_preflight']['artifact_sha256'] = a.sha(bytes(raw))
                artifact = a.strict_json(bad['preflight-artifact.json']); artifact['digest'] = 'sha256:' + a.sha(bytes(raw))
                bad['preflight-artifact.json'] = a.canonical(artifact); bad['preflight.zip'] = bytes(raw)
                self.reject_prerequisite(bound, provenance, bad)
        bound = copy.deepcopy(go); bound['runner_preflight']['artifact_size_bytes'] = a.MAX_INPUT_BYTES + 1
        self.reject_prerequisite(bound, provenance, proofs)

    def test_A28_ER_P05_report_runtime_sources_and_zero_calls(self):
        go, provenance, proofs = self.prerequisite_fixture()
        original = a._preflight_report_from_zip(proofs['preflight.zip'], go['runner_preflight'])
        paths = [(('success',), False), (('candidate_evaluator_calls',), 1),
                 (('checked_sources_unchanged_during_run',), False), (('loader_pin', 'library_sha256'), '3' * 64),
                 (('focused_source_receipt', 'sha256'), '3' * 64),
                 (('checked_file_sha256', 'scripts/worker36/admission.py'), '3' * 64),
                 (('focused_tests', 'tests_run'), 0), (('focused_tests', 'failures'), 1),
                 (('focused_tests', 'skipped'), 1), (('parent', 'runtime', 'version'), '3.12.0'),
                 (('parent', 'capped_limits', 'RLIMIT_AS'), [-1, -1]),
                 (('fresh_child', 'parent_pid'), 999), (('fresh_child', 'runtime', 'gc_enabled'), False)]
        for path, value in paths:
            with self.subTest(path=path):
                report = copy.deepcopy(original); target = report
                for part in path[:-1]: target = target[part]
                target[path[-1]] = value
                bound, bad = rebind_literal_preflight(go, proofs, report)
                self.reject_prerequisite(bound, provenance, bad)
        with zipfile.ZipFile(io.BytesIO(proofs['preflight.zip'])) as archive:
            components = {name: archive.read(name) for name in archive.namelist()}
        for name, value in (('parent-runtime.json', b'{}\n'), ('fresh-child.json', b'{}\n'),
                            ('fresh-child-process.json', b'{}\n'), ('shell-loader.json', b'{}\n'),
                            ('launcher.txt', components['launcher.txt'].replace(b'parent_exit_code=0', b'parent_exit_code=1'))):
            with self.subTest(component=name):
                changed = dict(components); changed[name] = value
                bound, bad = rebind_literal_preflight(go, proofs, original, members=sorted(changed.items()))
                self.reject_prerequisite(bound, provenance, bad)
        changed = dict(components)
        for name in ('parent.stdout', 'parent.stderr', 'fresh-child.stdout', 'fresh-child.stderr'):
            changed[name] = b'fixed diagnostic text; structured result remains successful\n'
        bound, diagnostic = rebind_literal_preflight(go, proofs, original, members=sorted(changed.items()))
        self.assertEqual(a.validate_prerequisites(bound, provenance, diagnostic)['runner_preflight'], bound['runner_preflight'])
        for field, value in (('pid', 999), ('command', ['wrong']), ('returncode', 1), ('timed_out', True)):
            with self.subTest(process_field=field):
                changed = dict(components); process = a.strict_json(changed['fresh-child-process.json'])
                process[field] = value; changed['fresh-child-process.json'] = a.canonical(process)
                bound, bad = rebind_literal_preflight(go, proofs, original, members=sorted(changed.items()))
                self.reject_prerequisite(bound, provenance, bad)

    def test_A29_ER_I01_invalid_proof_blocks_authentication_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); cache, checkout, temporary = root/'cache', root/'work', root/'temp'
            for path in (cache, checkout, temporary): path.mkdir()
            folder = cache/'worker36-evidence/run-9001-attempt-1/admission-inputs'; folder.mkdir(parents=True, mode=0o700)
            event, pr, ci, context, raw = literal_auth_inputs(cache=str(cache), checkout=str(checkout), temporary=str(temporary))
            for name, value in zip(a.INPUT_NAMES[:4], (event, pr, ci, context)): (folder/name).write_bytes(a.canonical(value))
            _, proofs = literal_prerequisite_bundle(a.strict_json(raw), cache=str(cache))
            for name, value in proofs.items(): (folder/name).write_bytes(value)
            observed = literal_loader_identity(str(cache)); env = literal_context_environment(context)
            env.update(observed['loader_environment']); env.update(literal_shell_loader(observed))
            env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1')
            flags = types.SimpleNamespace(dont_write_bytecode=1, no_user_site=1, optimize=0,
                                          ignore_environment=0, isolated=0, no_site=0, verbose=0)
            args = ['authenticate', '--event', str(folder/'event.json'), '--pull-request', str(folder/'pull-request.json'),
                '--ci', str(folder/'postmerge-ci.json'), '--request-context', str(folder/'request-context.json'),
                '--destination', str(folder/'admission.json'), '--provenance', str(folder/'provenance.json'),
                '--workflow-run', '9001', '--workflow-attempt', '1', '--expected-head', '1' * 40,
                '--expected-tree', '2' * 40, '--handoff', str(folder/'authenticated-handoff.env')]
            for missing in a.PREREQUISITE_NAMES:
                with self.subTest(missing=missing):
                    saved = (folder/missing).read_bytes(); (folder/missing).unlink()
                    with patch.dict(a.os.environ, env, clear=True), patch.object(a.sys, 'flags', flags), \
                            patch.object(a, 'loader_identity', return_value=observed):
                        with self.assertRaises((a.AdmissionError, FileNotFoundError)): self.isolated_cli_main(args)
                    for name in ('admission.json', 'provenance.json', 'authenticated-handoff.env'):
                        self.assertFalse((folder/name).exists())
                    (folder/missing).write_bytes(saved)

    def test_A30_ER_I02_retained_proof_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)/'auth'
            raw, provenance = write_literal_auth_inputs(folder)
            self.assertEqual(a.verify_provenance(folder/'provenance.json', folder/'admission.json', a.sha(raw)), provenance)
            for name in a.INPUT_NAMES:
                with self.subTest(name=name):
                    path = folder/name; original = path.read_bytes(); path.write_bytes(original + b' ')
                    with self.assertRaises(a.AdmissionError):
                        a.verify_provenance(folder/'provenance.json', folder/'admission.json', a.sha(raw))
                    path.write_bytes(original)

    def test_A31_ER_I03_fixed_read_routes_and_safe_handoff(self):
        source = (ROOT/'.github/workflows/worker36-synthetic-profile.yml').read_text()
        for text in ('  actions: read', '  pull-requests: read', 'types: [edited]',
                     'test "${#evidence_refs[@]}" = 4', 'admission.py evidence-refs',
                     'admission.py retain-input', 'set -euo pipefail'):
            self.assertIn(text, source)
        for suffix in ('issues/comments/${evidence_refs[0]}', 'issues/comments/${evidence_refs[1]}',
                       'actions/runs/${evidence_refs[2]}', 'actions/artifacts/${evidence_refs[3]}',
                       'actions/artifacts/${evidence_refs[3]}/zip'):
            self.assertIn('"repos/$GITHUB_REPOSITORY/' + suffix + '"', source)
        self.assertLess(source.index('--name preflight.zip'), source.index('admission.py authenticate'))
        self.assertNotIn('continue-on-error', source)
        self.test_A18_P10_preservation_run_is_byte_identical()
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            arguments = types.SimpleNamespace(directory=str(folder), name='review-exhaustive.json')
            with patch.dict(a.os.environ, {'AUTH': str(folder)}), patch.object(a, 'validate_interpreter'), \
                    patch.object(a.sys, 'stdin', types.SimpleNamespace(buffer=io.BytesIO(b'{}\n'))):
                self.assertEqual(a.retain_network_input(arguments), 0)
            self.assertEqual((folder/'review-exhaustive.json').read_bytes(), b'{}\n')
            arguments.name = 'review-adversarial.json'
            with patch.dict(a.os.environ, {'AUTH': str(folder)}), patch.object(a, 'validate_interpreter'), \
                    patch.object(a.sys, 'stdin', types.SimpleNamespace(buffer=io.BytesIO(b'X' * (a.MAX_INPUT_BYTES + 1)))):
                with self.assertRaises(a.AdmissionError): a.retain_network_input(arguments)
            self.assertFalse((folder/'review-adversarial.json').exists())


if __name__ == '__main__':
    unittest.main()
