"""Closed invented seven-JSON fixtures. No legacy fixture imports or networking.

Functions only serialize fixed administrative objects. No historical scientific
module, constructor, source restore, game or evaluator is imported or called.
"""
import copy
from pathlib import Path
from worker38 import admission as a
from worker38 import common as c

HEAD = '1111111111111111111111111111111111111111'
TREE = '2222222222222222222222222222222222222222'
OTHER_HEAD = '3333333333333333333333333333333333333333'
OTHER_TREE = '4444444444444444444444444444444444444444'
CREDENTIAL = 'INVENTED_TEST_CREDENTIAL_NOT_A_SECRET'
SOURCE_BYTES = b'INVENTED_SOURCE_BYTES_ONLY\n'
FIXED_INPUTS = ('pull-request.json', 'postmerge-ci.json', 'current-source-ci.json',
    'review-exhaustive.json', 'review-adversarial.json', 'preregistration.json', 'diagnostic-commit.json')
OWNER = {'login': 'carabinshely', 'id': 456, 'type': 'User'}
LIBRARY_PIN = {'schema': 'worker38-loader-pin-v1', 'executable_sha256': c.RUNTIME['executable_sha256'],
    'library_relative_path': 'Python/3.11.16/x64/lib/libpython3.11.so.1.0',
    'library_sha256': a.LIBRARY_SHA256, 'library_size_bytes': a.LIBRARY_SIZE}
INITIAL_MODULES = ['bandido_alcatraz', 'bandido_alcatraz.board', 'bandido_alcatraz.game',
    'bandido_alcatraz.model', 'bandido_alcatraz.moves', 'bandido_alcatraz.policies',
    'bandido_alcatraz.quota_reserve_closure', 'bandido_alcatraz.quota_reserve_closure_reference',
    'bandido_alcatraz.rules', 'bandido_alcatraz.setup', 'bandido_alcatraz.strategy', 'bandido_alcatraz.worker32',
    'bandido_alcatraz.worker32.evidence', 'benchmark_worker35_synthetic',
    'run_quota_reserve_closure_development', 'worker35_resources']
INHERITED_LIMITS = {'RLIMIT_AS': [-1, -1], 'RLIMIT_CORE': [0, -1], 'RLIMIT_CPU': [-1, -1],
    'RLIMIT_DATA': [-1, -1], 'RLIMIT_FSIZE': [-1, -1], 'RLIMIT_MEMLOCK': [67108864, 67108864],
    'RLIMIT_MSGQUEUE': [819200, 819200], 'RLIMIT_NICE': [0, 0], 'RLIMIT_NOFILE': [1048576, 1048576],
    'RLIMIT_NPROC': [127622, 127622], 'RLIMIT_OFILE': [1048576, 1048576], 'RLIMIT_RSS': [-1, -1],
    'RLIMIT_RTPRIO': [0, 0], 'RLIMIT_RTTIME': [-1, -1], 'RLIMIT_SIGPENDING': [127622, 127622],
    'RLIMIT_STACK': [8388608, -1]}


def review_body(review, number):
    value = {'schema': 'worker38-owner-attested-native-review-v1', 'repository': a.REPOSITORY,
        'pr_number': number, 'role': review['role'], 'native_reviewer_id': review['native_reviewer_id'],
        'head': review['head'], 'tree': review['tree'], 'verdict': 'clean', 'complete_review': True,
        'independent_review_attested': True, 'actionable_findings': {'P0': 0, 'P1': 0, 'P2': 0, 'P3': 0},
        'handoff_sha256': review['handoff_sha256'], 'report_sha256': review['report_sha256']}
    return a.REVIEW_START + '\n' + a.canonical(value).decode() + a.REVIEW_END + '\n'


def literal_bundle(go=None, *, pr_number=101, owner_id=456, cache='/invented-cache',
                   focused_source_receipt=None, checked_file_sha256=None, workflow_run='501'):
    """Defaults fill only absent fields; supplied invalid values remain invalid."""
    value = copy.deepcopy(go) if go is not None else {}
    number = value.get('pr_number', pr_number)
    owner = {**OWNER, 'id': owner_id}
    repo = {'full_name': a.REPOSITORY, 'html_url': a.WEB, 'url': a.API, 'owner': owner}
    source_map = {path: c.sha(SOURCE_BYTES) for path in a.REQUIRED_PRODUCTION_PATHS + a.METADATA_PATHS}
    source_map.update({a.EXPERIMENT + 'PROTOCOL.md': c.PROTOCOL_SHA256,
        a.EXPERIMENT + 'INTEGRATION-CONTRACT.json': c.CONTRACT_SHA256,
        a.EXPERIMENT + 'FINITE-PREPARATION-PLAN.json': c.FINITE_PLAN_SHA256,
        a.EXPERIMENT + 'comparator-source-manifest.json': c.SOURCE_MANIFEST_SHA256})
    source_map.update(a.UPLOAD_RECORD_PINS)
    if checked_file_sha256 is None:
        checked_file_sha256 = value.get('checked_file_sha256', value.get('diagnostic_files_sha256', source_map))
    checked_file_sha256 = dict(checked_file_sha256)
    checked_file_sha256.pop(a.FOCUSED_SOURCE_RECEIPT, None)
    receipt = {'success': True, 'failures': 0, 'errors': 0, 'checked_file_sha256': checked_file_sha256,
        'candidate_evaluator_calls': 0, 'reference_evaluator_calls': 0, 'games': 0,
        'measurement_fixture_constructions': 0, 'historical_source_imports': 0}
    receipt_raw = c.canonical(receipt)
    receipt_pin = focused_source_receipt or {'path': a.FOCUSED_SOURCE_RECEIPT,
        'size_bytes': len(receipt_raw), 'sha256': c.sha(receipt_raw)}
    defaults = {'schema': 'worker38-one-shot-admission-v1', 'admitted': True, 'repository': a.REPOSITORY,
        'owner': a.OWNER, 'branch': a.BRANCH, 'base_head': a.BASE_HEAD, 'base_tree': a.BASE_TREE,
        'allocation_id': a.ALLOCATION, 'pr_number': number, 'protocol_sha256': c.PROTOCOL_SHA256,
        'contract_sha256': c.CONTRACT_SHA256, 'finite_plan_sha256': c.FINITE_PLAN_SHA256,
        'upload_amendment_sha256': c.UPLOAD_AMENDMENT_SHA256, 'upload_contract_sha256': c.UPLOAD_CONTRACT_SHA256,
        'upload_finite_plan_sha256': c.UPLOAD_FINITE_PLAN_SHA256, 'upload_adoption_comment_id': c.UPLOAD_ADOPTION,
        'preregistration_url': a.WEB + '/issues/2#issuecomment-603', 'admission_url': a.WEB + '/pull/' + str(number),
        'head': HEAD, 'tree': TREE, 'runner': a.RUNNER, 'runtime': c.RUNTIME, 'loader_pin': LIBRARY_PIN,
        'resources': c.RESOURCES, 'startup_resources': c.STARTUP_RESOURCES, 'schedule': list(c.SCHEDULE),
        'maximum_evaluator_calls': 40, 'games': 0, 'source_manifest_sha256': c.SOURCE_MANIFEST_SHA256,
        'diagnostic_files_sha256': source_map, 'checked_file_sha256': checked_file_sha256,
        'cell_preflight_modules': INITIAL_MODULES, 'inherited_limits': INHERITED_LIMITS,
        'stub_test_receipt_sha256': receipt_pin['sha256'], 'focused_source_receipt': receipt_pin,
        'postmerge_ci': {'run_id': a.CI_RUN, 'head': a.BASE_HEAD, 'status': 'completed', 'conclusion': 'success'},
        'current_source_ci': {'run_id': 401, 'head': value.get('head', HEAD), 'status': 'completed',
                              'conclusion': 'success', 'completed_at': '2026-10-05T00:00:00Z'}}
    for key, default in defaults.items():
        value.setdefault(key, copy.deepcopy(default))
    # Older literal bundles supplied only review display fields. Their complete
    # administrative fixture is materialized here once, never imported from an
    # excluded historical helper. Complete supplied reviews remain untouched.
    existing_reviews = value.get('reviews')
    if existing_reviews is None or not all(type(review) is dict and 'comment_id' in review for review in existing_reviews):
        value['reviews'] = []
        for role, reviewer, comment_id, report_hash in (('exhaustive', 'literal-reviewer-one', 601, 'a' * 64),
                ('adversarial', 'literal-reviewer-two', 602, 'b' * 64)):
            review = {'role': role, 'native_reviewer_id': reviewer, 'head': value['head'], 'tree': value['tree'],
                'verdict': 'clean', 'url': value['admission_url'] + '#issuecomment-' + str(comment_id),
                'comment_id': comment_id, 'handoff_sha256': 'c' * 64, 'report_sha256': report_hash}
            review['body_sha256'] = c.sha(review_body(review, number).encode())
            value['reviews'].append(review)
    prereg_body = ('Invented preregistration of ' + value['protocol_sha256'] + '\nContract ' +
                  value['contract_sha256'] + '\nFinite plan ' + value['finite_plan_sha256'] + '\n')
    if 'preregistration' not in value:
        match = value['preregistration_url'].rsplit('-', 1)[-1]
        prereg_id = int(match)
        value['preregistration'] = {'comment_id': prereg_id, 'url': value['preregistration_url'],
            'body_sha256': c.sha(prereg_body.encode()), 'protocol_sha256': value['protocol_sha256'],
            'contract_sha256': value['contract_sha256'], 'finite_plan_sha256': value['finite_plan_sha256']}
    raw = c.canonical(value)
    body = a.START + '\n' + raw.decode() + a.END + '\n' + a.DIGEST + ': ' + c.sha(raw) + '\n'
    pr = {'number': number, 'html_url': value['admission_url'], 'url': a.API + '/pulls/' + str(number),
        'issue_url': a.API + '/issues/' + str(number), 'state': 'open', 'merged': False, 'merged_at': None,
        'user': owner, 'head': {'ref': a.BRANCH, 'sha': value['head'], 'repo': repo},
        'base': {'ref': 'main', 'sha': a.BASE_HEAD, 'repo': repo}, 'body': body,
        'updated_at': '2026-10-05T00:01:00Z'}
    event = {'action': 'edited', 'repository': repo, 'sender': owner, 'number': number,
             'pull_request': copy.deepcopy(pr), 'changes': {'body': {'from': 'Invented previous body\n'}}}
    context = {'schema': 'worker38-github-request-context-v1', 'repository': a.REPOSITORY,
        'actor': a.OWNER, 'triggering_actor': a.OWNER, 'event_name': 'pull_request',
        'workflow_run': workflow_run, 'workflow_attempt': '1', 'runner_name': a.RUNNER,
        'runner_tool_cache': cache, 'checkout_path': '/invented-checkout', 'runner_temp': '/invented-temp',
        'durable_root': cache + '/worker38-synthetic-profile',
        'attempt_path': cache + '/worker38-synthetic-profile/allocations/' + a.ALLOCATION + '/run-' + str(workflow_run) + '-attempt-1',
        'attempt_id': 'worker38-' + str(workflow_run) + '-1', 'authentication': 'github-repository-read-token',
        'requests': [{'name': name, 'method': 'GET', 'path': path} for name, path in a.request_map(value)]}
    responses = [pr]
    for base in (True, False):
        binding = value['postmerge_ci' if base else 'current_source_ci']
        run = binding['run_id']
        responses.append({'repository': repo, 'id': run, 'url': a.API + '/actions/runs/' + str(run),
            'html_url': a.WEB + '/actions/runs/' + str(run), 'head_sha': binding['head'],
            'head_branch': 'main' if base else a.BRANCH, 'event': 'push' if base else 'pull_request',
            'path': '.github/workflows/test.yml', 'name': 'tests', 'status': 'completed', 'conclusion': 'success',
            'updated_at': '2026-10-04T23:00:00Z' if base else binding['completed_at']})
    for review in value['reviews']:
        responses.append({'id': review['comment_id'], 'url': a.API + '/issues/comments/' + str(review['comment_id']),
            'html_url': review['url'], 'issue_url': a.API + '/issues/' + str(number), 'user': owner,
            'body': review_body(review, number)})
    prereg = value['preregistration']
    responses.append({'id': prereg['comment_id'], 'url': a.API + '/issues/comments/' + str(prereg['comment_id']),
        'html_url': prereg['url'], 'issue_url': a.API + '/issues/2', 'user': owner, 'body': prereg_body})
    responses.append({'sha': value['head'], 'tree': {'sha': value['tree']}})
    inputs = dict(zip(FIXED_INPUTS, (c.canonical(response) for response in responses)))
    event_raw, context_raw = c.canonical(event), c.canonical(context)
    # Reconciliation is intentionally explicit; callers can retain invalid
    # literals for negative tests without this builder laundering their errors.
    return {'go': value, 'event': event, 'context': context, 'inputs': inputs,
        'admission_raw': raw, 'event_raw': event_raw, 'context_raw': context_raw,
        'stub_receipt_raw': receipt_raw}


def literal_prerequisite_bundle(go=None, **kwargs):
    bundle = literal_bundle(go, **kwargs)
    return bundle['go'], bundle['inputs']


def write_literal_bundle(directory, bundle):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    event_raw, context_raw = c.canonical(bundle['event']), c.canonical(bundle['context'])
    raw, proof = a.reconcile(event_raw, context_raw, bundle['inputs'])
    payloads = {'event.json': event_raw, 'request-context.json': context_raw,
                **bundle['inputs'], 'admission.json': raw, 'provenance.json': c.canonical(proof)}
    for name, payload in payloads.items():
        (directory / name).write_bytes(payload)
    bundle['provenance'] = proof
    return proof
