"""Ten finite prospective literal-stub auth cases. Never import policy or run it."""
import ast
import copy
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from worker36 import admission as a


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
              'postmerge_ci': {'run_id': a.CI_RUN, 'head': a.BASE_HEAD,
                              'status': 'completed', 'conclusion': 'success'}}
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


def write_literal_auth_inputs(folder, go=None, **options):
    """Retain literal fixtures and genuinely reconcile them, without any bypass."""
    folder = Path(folder)
    folder.mkdir(parents=True, mode=0o700, exist_ok=True)
    event, pr, ci, context, raw = literal_auth_inputs(go, **options)
    values = dict(zip(a.INPUT_NAMES, (event, pr, ci, context)))
    for name, value in values.items():
        (folder / name).write_bytes(a.canonical(value))
    actual, provenance = a.extract_pr_admission(event, pr, ci)
    if actual != raw:
        raise ValueError('literal helper raw mismatch')
    provenance.update(a.verified_context(context, provenance, context['workflow_run'], '1'))
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
            args = ['authenticate', '--event', str(folder/'event.json'), '--pull-request', str(folder/'pull-request.json'),
                    '--ci', str(folder/'postmerge-ci.json'), '--request-context', str(folder/'request-context.json'),
                    '--destination', str(folder/'admission.json'), '--provenance', str(folder/'provenance.json'),
                    '--workflow-run', '9001', '--workflow-attempt', '1']
            env = {'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1', 'RUNNER_TOOL_CACHE': str(cache),
                   'GITHUB_WORKSPACE': str(checkout), 'RUNNER_TEMP': str(temporary), 'GITHUB_RUN_ID': '9001',
                   'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_EVENT_NAME': 'pull_request', 'GITHUB_REPOSITORY': a.REPOSITORY,
                   'GITHUB_ACTOR': a.OWNER, 'RUNNER_NAME': 'bandido-alcatraz-ci'}
            flags = types.SimpleNamespace(dont_write_bytecode=1, no_user_site=1, optimize=0,
                                          ignore_environment=0, isolated=0, no_site=0)
            with patch.dict(a.os.environ, env, clear=True), patch.object(a.sys, 'flags', flags):
                self.assertEqual(a.main(args), 0)
                with self.assertRaises(FileExistsError): a.main(args)
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
        self.assertEqual(source.count('timeout --signal=TERM --kill-after=5s 600s'), 1)
        self.assertNotIn('rm -', source)
        for step in source.split('      - '):
            if 'python -B -s ' in step:
                self.assertIn('unset LD_PRELOAD LD_LIBRARY_PATH', step)
                self.assertIn('[[ "$name" == PYTHON* ]] && unset "$name"', step)
                self.assertLess(step.index('export PYTHONHASHSEED=0'), step.index('python -B -s '))
        self.assertIn('"$GITHUB_WORKSPACE/scripts/run_worker36_synthetic.py" measure', source)
        self.assertIn('"$GITHUB_WORKSPACE/scripts/run_worker36_synthetic.py" preserve', source)


if __name__ == '__main__':
    unittest.main()
