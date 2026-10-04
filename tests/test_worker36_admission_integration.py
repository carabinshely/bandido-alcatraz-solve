"""Finite A01-A19 literal auth cases; P06-P11 are frozen runner metadata repair."""
import ast
import copy
from pathlib import Path
import sys
import tempfile
import types
import unittest
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
                    '--workflow-run', '9001', '--workflow-attempt', '1', '--expected-head', '1' * 40,
                    '--expected-tree', '2' * 40, '--handoff', str(folder/'authenticated-handoff.env')]
            env = {'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1', 'RUNNER_TOOL_CACHE': str(cache),
                   'GITHUB_WORKSPACE': str(checkout), 'RUNNER_TEMP': str(temporary), 'GITHUB_RUN_ID': '9001',
                   'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_EVENT_NAME': 'pull_request', 'GITHUB_REPOSITORY': a.REPOSITORY,
                   'GITHUB_ACTOR': a.OWNER, 'RUNNER_NAME': 'bandido-alcatraz-ci'}
            flags = types.SimpleNamespace(dont_write_bytecode=1, no_user_site=1, optimize=0,
                                          ignore_environment=0, isolated=0, no_site=0)
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
                                optimize=0, ignore_environment=0, isolated=0, no_site=0)
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
                                          ignore_environment=0, isolated=0, no_site=0)
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
                args = ['authenticate', '--event', str(folder/'event.json'), '--pull-request', str(folder/'pull-request.json'),
                        '--ci', str(folder/'postmerge-ci.json'), '--request-context', str(folder/'request-context.json'),
                        '--destination', str(folder/'admission.json'), '--provenance', str(folder/'provenance.json'),
                        '--workflow-run', '9001', '--workflow-attempt', '1', '--expected-head', '3' * 40,
                        '--expected-tree', '2' * 40, '--handoff', str(folder/'authenticated-handoff.env')]
                with self.assertRaises(a.AdmissionError): self.isolated_cli_main(args)
                for name in ('admission.json', 'provenance.json', 'authenticated-handoff.env'):
                    self.assertFalse((folder/name).exists())


if __name__ == '__main__':
    unittest.main()
