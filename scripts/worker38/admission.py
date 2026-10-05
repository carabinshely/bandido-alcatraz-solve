"""Closed Worker38 seven-JSON admission leaf and offline semantic replay.

No science import, subprocess, credential persistence, retry, discovery or archive
client exists here. The shell consumes the sole allocation before this leaf.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import http.client
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import resource
import signal
import ssl
import stat
import sys
import time
import urllib.error
import urllib.request

if __name__ == '__main__' and not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from worker38.common import (IntegrityError, RUNTIME, RESOURCES, SCHEDULE, loader_pin,
                             CONTRACT_SHA256, FINITE_PLAN_SHA256, STARTUP_RESOURCES,
                             UPLOAD_AMENDMENT_SHA256, UPLOAD_CONTRACT_SHA256,
                             UPLOAD_FINITE_PLAN_SHA256, UPLOAD_ADOPTION)

REPOSITORY = 'carabinshely/bandido-alcatraz-solve'
OWNER = 'carabinshely'
BRANCH = 'research/worker38-synthetic-profile'
CONSUMER = 'worker38-synthetic-profile-v1'
ALLOCATION = 'worker38-synthetic-profile-01'
RUNNER = 'bandido-alcatraz-ci'
BASE_HEAD = '6ff861bba828e78d8f5b75d8355f2f4a56018898'
BASE_TREE = '7a97c827c75c135d2fbbb5cd97873d1418e069fb'
CI_RUN = 37250449266
PROTOCOL_SHA256 = '17abf2d644106bb7c10fbec5481deb7da33e17867ee2f08ea065ca591e8499a7'
WEB = 'https://github.com/' + REPOSITORY
API = 'https://api.github.com/repos/' + REPOSITORY
PREREGISTRATION = WEB + '/issues/2#issuecomment-5987629515'
PREREGISTRATION_BODY_SHA256 = 'e4665052aa57ec82d65e1d7a47de2f3bd22bd44d5ac247156db7a72083a1d62d'
MARKER = 'WORKER38_SYNTHETIC_ADMISSION'
START, END, DIGEST = MARKER + '_JSON', 'END_' + MARKER + '_JSON', MARKER + '_SHA256'
REVIEW_START, REVIEW_END = 'WORKER38_NATIVE_REVIEW_JSON', 'END_WORKER38_NATIVE_REVIEW_JSON'
INPUT_NAMES = ('pull-request.json', 'postmerge-ci.json', 'current-source-ci.json',
               'review-exhaustive.json', 'review-adversarial.json', 'preregistration.json',
               'diagnostic-commit.json')
PREREQUISITE_NAMES = INPUT_NAMES[1:]
MAX_INPUT = MAX_INPUT_BYTES = 2097152
MAX_BODY_BYTES = MAX_GO_BYTES = 65536
MAX_RECEIVED = 14680065
LIBRARY_SHA256 = 'ba4450817186fbe1e3c477f6aefeee7c353cba3593cc9950382ad9d1f5e62896'
LIBRARY_SIZE = 23041360
EXPERIMENT = 'experiments/worker38-synthetic-profile/'
FOCUSED_SOURCE_RECEIPT = EXPERIMENT + 'focused-preparation-receipt.json'
METADATA_PATHS = (EXPERIMENT + 'PROTOCOL.md', EXPERIMENT + 'INTEGRATION-CONTRACT.json',
                  EXPERIMENT + 'FINITE-PREPARATION-PLAN.json', EXPERIMENT + 'SOURCE-GROUNDING.json',
                  EXPERIMENT + 'comparator-source-manifest.json')
REQUIRED_PRODUCTION_PATHS = ('.github/workflows/worker38-synthetic-profile.yml',
    'scripts/worker_bootstrap_shared.sh', 'scripts/worker_bootstrap_shared.py',
    'scripts/worker37-bootstrap.sh', 'scripts/worker37_bootstrap.py',
    'scripts/worker38-bootstrap.sh', 'scripts/run_worker38_synthetic.py',
    'scripts/worker38/__init__.py', 'scripts/worker38/admission.py', 'scripts/worker38/common.py',
    'scripts/worker38/sources.py', 'scripts/worker38/supervision.py', 'scripts/worker38/cell.py',
    'scripts/worker38/driver.py', 'scripts/worker38/transport.py', 'scripts/worker38/verify.py',
    '.github/actions/worker38-upload/action.yml')
UPLOAD_RECORD_PINS = {
    EXPERIMENT + 'upload-amendment/AMENDMENT.md': UPLOAD_AMENDMENT_SHA256,
    EXPERIMENT + 'upload-amendment/AMENDMENT-CONTRACT.json': UPLOAD_CONTRACT_SHA256,
    EXPERIMENT + 'upload-amendment/FINITE-COVERAGE-AMENDMENT.json': UPLOAD_FINITE_PLAN_SHA256,
    EXPERIMENT + 'upload-amendment/SOURCE-OBSERVATION.json': 'c0b2efd71fc498b6beb8dd8f5fc7b90c047a803c1e2003467978191911f5e9d8',
    EXPERIMENT + 'upload-amendment/REPAIR-DISPOSITION.json': 'f291ecfd3b5d10f96bb594f4e6945e0beef1625a2ecfa994368243897c2329a8',
    EXPERIMENT + 'upload-amendment/HANDOFF.json': '54e30bca1fb6c754c211f319789a018255113c35ade1dc0404c197d8c2b0adbe',
}
METADATA_PATHS += tuple(UPLOAD_RECORD_PINS)
OUTPUT_NAMES = frozenset(INPUT_NAMES + ('event.json', 'request-context.json', 'admission.json',
    'provenance.json', 'startup-receipt.json', 'startup-handoff.json', 'measurement-handoff.txt',
    'startup-failure.json', 'startup-failure-handoff.json', 'startup-preservation-handoff.txt', 'source-manifest.json', 'reservation.txt', 'restored-inventory.json', 'runtime.json'))
PRIORITY = {'execution_blocked': 0, 'execution_incomplete': 1,
            'resource_incomplete': 2, 'integrity_invalid': 3}
EXIT_CODES = {'execution_blocked': 78, 'execution_incomplete': 74,
              'resource_incomplete': 75, 'integrity_invalid': 65}


class AdmissionError(IntegrityError):
    """Fixed, credential-free error codes plus ordered secondary failures."""
    def __init__(self, code, classification='integrity_invalid'):
        self.code, self.classification = code, classification
        self.secondary_failures = []
        super().__init__(code)


Failure = AdmissionError


def require(condition, code, classification='integrity_invalid'):
    if not condition:
        raise AdmissionError(code, classification)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                       allow_nan=False) + '\n').encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    def number(text):
        value = float(text)
        require(math.isfinite(value), 'nonfinite_json')
        return value
    def constant(_text):
        raise AdmissionError('nonfinite_json')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_float=number, parse_constant=constant)
    except (MemoryError, RecursionError):
        raise AdmissionError('json_resource_exhausted', 'resource_incomplete') from None
    except (UnicodeError, json.JSONDecodeError):
        raise AdmissionError('invalid_json') from None


def keys(value, expected, code='descriptor_schema'):
    require(type(value) is dict and set(value) == set(expected), code)
    return value


def positive_int(value, code='positive_integer'):
    require(type(value) is int and 0 < value <= 9223372036854775807, code)
    return value


def hex_digest(value, label='digest', width=64):
    require(type(value) is str and re.fullmatch('[0-9a-f]{' + str(width) + '}', value) is not None,
            'invalid_' + label)
    return value


def bounded_body(value):
    require(type(value) is str and '\r' not in value and len(value.encode('utf-8')) <= MAX_BODY_BYTES,
            'body_shape_or_bound')
    return value


def object_at(value, key):
    require(type(value) is dict and type(value.get(key)) is dict, 'missing_object_' + key)
    return value[key]


def identity(value):
    require(type(value) is dict and value.get('login') == OWNER and value.get('type') == 'User',
            'owner_identity')
    return {'login': OWNER, 'id': positive_int(value.get('id'), 'owner_id'), 'type': 'User'}


def repository(value, owner):
    require(type(value) is dict and value.get('full_name') == REPOSITORY and value.get('url') == API
            and value.get('html_url') == WEB and identity(value.get('owner')) == owner, 'repository_identity')


def timestamp(value):
    require(type(value) is str and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', value) is not None,
            'timestamp_shape')
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    except ValueError:
        raise AdmissionError('timestamp_value') from None


def admitted_loader_pin(value):
    try:
        pin = loader_pin(value)
    except IntegrityError:
        raise AdmissionError('loader_pin_schema') from None
    require(value == pin and pin['library_sha256'] == LIBRARY_SHA256 and
            pin['library_size_bytes'] == LIBRARY_SIZE, 'loader_pin_binding')
    return pin


def descriptor_from_body(body):
    body = bounded_body(body)
    lines = body.split('\n')
    require(lines.count(START) == lines.count(END) == 1 and body.count(START) == 2 and
            body.count(END) == 1 and body.count(DIGEST) == 1, 'admission_markers')
    first, last = lines.index(START), lines.index(END)
    require(first < last, 'admission_marker_order')
    positions = [(i, line) for i, line in enumerate(lines) if DIGEST in line]
    index, line = positions[0]
    match = re.fullmatch(DIGEST + ': ([0-9a-f]{64})', line)
    require(match is not None and not first < index < last, 'admission_digest_line')
    raw = ('\n'.join(lines[first + 1:last]) + '\n').encode('utf-8')
    require(1 < len(raw) <= MAX_GO_BYTES and sha(raw) == match.group(1), 'admission_raw_binding')
    descriptor = strict_json(raw)
    validate_descriptor(descriptor)
    return descriptor, raw, body


DESCRIPTOR_KEYS = ('schema', 'admitted', 'repository', 'owner', 'branch', 'base_head', 'base_tree',
    'allocation_id', 'pr_number', 'preregistration_url', 'protocol_sha256', 'contract_sha256',
    'finite_plan_sha256', 'upload_amendment_sha256', 'upload_contract_sha256',
    'upload_finite_plan_sha256', 'upload_adoption_comment_id', 'admission_url', 'head', 'tree', 'runner', 'runtime', 'loader_pin',
    'resources', 'startup_resources', 'schedule', 'maximum_evaluator_calls', 'games',
    'source_manifest_sha256', 'diagnostic_files_sha256', 'checked_file_sha256',
    'cell_preflight_modules', 'inherited_limits', 'stub_test_receipt_sha256',
    'focused_source_receipt', 'postmerge_ci', 'current_source_ci', 'reviews', 'preregistration')
REVIEW_KEYS = ('role', 'native_reviewer_id', 'head', 'tree', 'verdict', 'url', 'comment_id',
               'body_sha256', 'handoff_sha256', 'report_sha256')


def validate_source_map(value):
    require(type(value) is dict and 0 < len(value) <= 256, 'source_map_count')
    for name, pin in value.items():
        require(type(name) is str and len(name) <= 512 and '\\' not in name, 'source_path')
        path = PurePosixPath(name)
        require(not path.is_absolute() and '..' not in path.parts and str(path) == name,
                'source_path')
        hex_digest(pin, 'source_hash')
    require(set(REQUIRED_PRODUCTION_PATHS + METADATA_PATHS) <= set(value), 'source_map_missing_required')
    require(all(value[name] == pin for name, pin in UPLOAD_RECORD_PINS.items()), 'upload_record_source_pins')
    return value


def validate_descriptor(go):
    keys(go, DESCRIPTOR_KEYS)
    expected = {'schema': 'worker38-one-shot-admission-v1', 'admitted': True,
        'repository': REPOSITORY, 'owner': OWNER, 'branch': BRANCH, 'base_head': BASE_HEAD,
        'base_tree': BASE_TREE, 'allocation_id': ALLOCATION, 'runner': RUNNER,
        'protocol_sha256': PROTOCOL_SHA256, 'contract_sha256': CONTRACT_SHA256,
        'finite_plan_sha256': FINITE_PLAN_SHA256, 'upload_amendment_sha256': UPLOAD_AMENDMENT_SHA256,
        'upload_contract_sha256': UPLOAD_CONTRACT_SHA256, 'upload_finite_plan_sha256': UPLOAD_FINITE_PLAN_SHA256,
        'upload_adoption_comment_id': UPLOAD_ADOPTION, 'maximum_evaluator_calls': 40, 'games': 0}
    for name, value in expected.items():
        require(type(go[name]) is type(value) and go[name] == value, 'descriptor_' + name)
    number = positive_int(go['pr_number'], 'pr_number')
    require(go['admission_url'] == WEB + '/pull/' + str(number), 'admission_url')
    for name in ('head', 'tree'):
        hex_digest(go[name], name, 40)
    for name in ('protocol_sha256', 'contract_sha256', 'finite_plan_sha256',
                 'source_manifest_sha256', 'stub_test_receipt_sha256'):
        hex_digest(go[name], name)
    require(canonical(go['runtime']) == canonical(RUNTIME) and
            canonical(go['resources']) == canonical(RESOURCES) and
            canonical(go['schedule']) == canonical(list(SCHEDULE)), 'frozen_science_runtime_caps')
    require(canonical(go['startup_resources']) == canonical(STARTUP_RESOURCES), 'startup_caps')
    admitted_loader_pin(go['loader_pin'])
    validate_source_map(go['diagnostic_files_sha256'])
    validate_source_map(go['checked_file_sha256'])
    require(all(go['checked_file_sha256'].get(name) == pin for name, pin in
                go['diagnostic_files_sha256'].items()), 'checked_diagnostic_agreement')
    receipt = keys(go['focused_source_receipt'], ('path', 'size_bytes', 'sha256'), 'focused_receipt_schema')
    require(receipt['path'] == FOCUSED_SOURCE_RECEIPT and 0 < positive_int(receipt['size_bytes']) <= MAX_INPUT
            and hex_digest(receipt['sha256']) == go['stub_test_receipt_sha256'], 'focused_receipt_binding')
    require(type(go['cell_preflight_modules']) is list and bool(go['cell_preflight_modules']) and
            all(type(name) is str for name in go['cell_preflight_modules']) and
            len(set(go['cell_preflight_modules'])) == len(go['cell_preflight_modules']), 'cell_modules')
    require(type(go['inherited_limits']) is dict and all(type(pair) is list and len(pair) == 2 and
            all(type(n) is int and n >= -1 for n in pair) for pair in go['inherited_limits'].values()), 'inherited_limits')
    require(go['postmerge_ci'] == {'run_id': CI_RUN, 'head': BASE_HEAD, 'status': 'completed',
                                  'conclusion': 'success'}, 'postmerge_descriptor')
    ci = keys(go['current_source_ci'], ('run_id', 'head', 'status', 'conclusion', 'completed_at'), 'source_ci_schema')
    positive_int(ci['run_id'], 'source_ci_run')
    require(ci['run_id'] != CI_RUN and ci['head'] == go['head'] and ci['status'] == 'completed' and
            ci['conclusion'] == 'success', 'source_ci_descriptor')
    timestamp(ci['completed_at'])
    require(type(go['reviews']) is list and len(go['reviews']) == 2, 'review_count')
    for review, role in zip(go['reviews'], ('exhaustive', 'adversarial')):
        keys(review, REVIEW_KEYS, 'review_schema')
        require(review['role'] == role and review['head'] == go['head'] and review['tree'] == go['tree'] and
                review['verdict'] == 'clean', 'review_scope')
        require(type(review['native_reviewer_id']) is str and
                re.fullmatch('[A-Za-z0-9_.:/-]{1,160}', review['native_reviewer_id']) is not None, 'reviewer_id')
        positive_int(review['comment_id'], 'review_comment_id')
        require(review['url'] == go['admission_url'] + '#issuecomment-' + str(review['comment_id']), 'review_url')
        for name in ('body_sha256', 'handoff_sha256', 'report_sha256'):
            hex_digest(review[name], name)
    for name in ('native_reviewer_id', 'comment_id', 'report_sha256'):
        require(go['reviews'][0][name] != go['reviews'][1][name], 'review_independence')
    prereg = keys(go['preregistration'], ('comment_id', 'url', 'body_sha256', 'protocol_sha256',
                  'contract_sha256', 'finite_plan_sha256'), 'preregistration_schema')
    positive_int(prereg['comment_id'], 'preregistration_comment_id')
    require(prereg['url'] == WEB + '/issues/2#issuecomment-' + str(prereg['comment_id']) == go['preregistration_url'],
            'preregistration_url')
    for name in ('body_sha256', 'protocol_sha256', 'contract_sha256', 'finite_plan_sha256'):
        hex_digest(prereg[name], name)
    require(all(prereg[name] == go[name] for name in
                ('protocol_sha256', 'contract_sha256', 'finite_plan_sha256')), 'preregistration_bindings')
    return go


def validate_pr(pr, go, owner, body):
    number = go['pr_number']
    require(type(pr) is dict and type(pr.get('number')) is int and pr['number'] == number and
            pr.get('html_url') == go['admission_url'] and pr.get('url') == API + '/pulls/' + str(number) and
            pr.get('issue_url') == API + '/issues/' + str(number), 'pr_identity')
    require(pr.get('state') == 'open' and pr.get('merged') is False and pr.get('merged_at') is None,
            'pr_open_unmerged')
    require(identity(pr.get('user')) == owner, 'pr_author')
    for key, branch, head in (('head', BRANCH, go['head']), ('base', 'main', BASE_HEAD)):
        ref = object_at(pr, key)
        require(ref.get('ref') == branch and ref.get('sha') == head, 'pr_' + key)
        repository(ref.get('repo'), owner)
    require(bounded_body(pr.get('body')) == body, 'current_pr_body_drift')
    timestamp(pr.get('updated_at'))


def validate_event(event, go, body, context):
    require(type(event) is dict and event.get('action') == 'edited', 'event_action')
    owner = identity(object_at(object_at(event, 'repository'), 'owner'))
    repository(event['repository'], owner)
    require(identity(event.get('sender')) == owner, 'event_sender')
    require(type(event.get('number')) is int and event['number'] == go['pr_number'], 'event_pr_number')
    validate_pr(object_at(event, 'pull_request'), go, owner, body)
    previous = bounded_body(object_at(object_at(event, 'changes'), 'body').get('from'))
    require(previous != body and MARKER not in previous, 'first_admission_transition')
    validate_context(context, go)
    require(int(context['workflow_run']) != go['current_source_ci']['run_id'], 'circular_source_ci')
    require(timestamp(go['current_source_ci']['completed_at']) < timestamp(event['pull_request']['updated_at']),
            'source_ci_does_not_precede_admission_event')
    return owner


def validate_context(context, go):
    fields = ('schema', 'repository', 'actor', 'triggering_actor', 'event_name', 'workflow_run',
        'workflow_attempt', 'runner_name', 'runner_tool_cache', 'checkout_path', 'runner_temp',
        'durable_root', 'attempt_path', 'attempt_id', 'authentication', 'requests')
    keys(context, fields, 'request_context_schema')
    expected = {'schema': 'worker38-github-request-context-v1', 'repository': REPOSITORY,
        'actor': OWNER, 'triggering_actor': OWNER, 'event_name': 'pull_request', 'workflow_attempt': '1',
        'runner_name': RUNNER, 'authentication': 'github-repository-read-token'}
    require(all(type(context[k]) is str and context[k] == v for k, v in expected.items()), 'context_identity')
    run = context['workflow_run']
    require(type(run) is str and re.fullmatch('[1-9][0-9]{0,18}', run) is not None, 'context_run_id')
    paths = {}
    for key in ('runner_tool_cache', 'checkout_path', 'runner_temp', 'durable_root', 'attempt_path'):
        value = context[key]
        require(type(value) is str and 0 < len(value) <= 4096 and
                all(32 <= ord(c) < 127 for c in value), 'context_path')
        path = PurePosixPath(value)
        require(path.is_absolute() and '..' not in path.parts and str(path) == value, 'context_path')
        paths[key] = path
    durable = paths['runner_tool_cache'] / 'worker38-synthetic-profile'
    attempt = durable / 'allocations' / ALLOCATION / ('run-' + run + '-attempt-1')
    require(paths['durable_root'] == durable and paths['attempt_path'] == attempt and
            context['attempt_id'] == 'worker38-' + run + '-1', 'new_namespace_only')
    base_paths = [paths[k] for k in ('runner_tool_cache', 'checkout_path', 'runner_temp')]
    require(all(not left.is_relative_to(right) and not right.is_relative_to(left)
                for i, left in enumerate(base_paths) for right in base_paths[i + 1:]), 'overlapping_roots')
    require(context['requests'] == [{'name': name, 'method': 'GET', 'path': path}
                                    for name, path in request_map(go)], 'fixed_requests')
    return context


def request_map(go):
    return tuple(zip(INPUT_NAMES, ('/pulls/' + str(go['pr_number']), '/actions/runs/' + str(CI_RUN),
        '/actions/runs/' + str(go['current_source_ci']['run_id']),
        '/issues/comments/' + str(go['reviews'][0]['comment_id']),
        '/issues/comments/' + str(go['reviews'][1]['comment_id']),
        '/issues/comments/' + str(go['preregistration']['comment_id']), '/git/commits/' + go['head'])))


def _review_attestation(value, review, go, owner):
    comment(value, review, go['pr_number'], owner)
    body = bounded_body(value.get('body'))
    require(sha(body.encode()) == review['body_sha256'], 'review_body_hash')
    prefix, suffix = REVIEW_START + '\n', REVIEW_END + '\n'
    require(body.startswith(prefix) and body.endswith(suffix) and body.count(REVIEW_START) == 2 and
            body.count(REVIEW_END) == 1, 'review_single_block')
    actual = strict_json(body[len(prefix):-len(suffix)])
    expected = {'schema': 'worker38-owner-attested-native-review-v1', 'repository': REPOSITORY,
        'pr_number': go['pr_number'], 'role': review['role'], 'native_reviewer_id': review['native_reviewer_id'],
        'head': go['head'], 'tree': go['tree'], 'verdict': 'clean', 'complete_review': True,
        'independent_review_attested': True, 'actionable_findings': {'P0': 0, 'P1': 0, 'P2': 0, 'P3': 0},
        'handoff_sha256': review['handoff_sha256'], 'report_sha256': review['report_sha256']}
    require(canonical(actual) == canonical(expected), 'review_clean_exact_scope')


def comment(value, binding, issue, owner):
    require(type(value) is dict and type(value.get('id')) is int and value['id'] == binding['comment_id']
            and value.get('url') == API + '/issues/comments/' + str(binding['comment_id'])
            and value.get('html_url') == binding['url'] and value.get('issue_url') == API + '/issues/' + str(issue),
            'comment_identity')
    require(identity(value.get('user')) == owner, 'comment_owner')


def validate_response(index, raw, go, body, event, context):
    require(type(raw) is bytes and len(raw) <= MAX_INPUT, 'response_bound')
    value = strict_json(raw)
    require(type(value) is dict, 'response_object')
    owner = identity(event['repository']['owner'])
    if index == 0:
        validate_pr(value, go, owner, body)
        require(value['updated_at'] == event['pull_request']['updated_at'], 'pr_event_timestamp_drift')
    elif index in (1, 2):
        is_base = index == 1
        binding = go['postmerge_ci' if is_base else 'current_source_ci']
        run = binding['run_id']
        repository(value.get('repository'), owner)
        require(type(value.get('id')) is int and value['id'] == run and
                value.get('url') == API + '/actions/runs/' + str(run) and
                value.get('html_url') == WEB + '/actions/runs/' + str(run), 'ci_run_identity')
        require(value.get('head_sha') == binding['head'] and
                value.get('head_branch') == ('main' if is_base else BRANCH) and
                value.get('event') == ('push' if is_base else 'pull_request') and
                value.get('path') == '.github/workflows/test.yml' and value.get('name') == 'tests' and
                value.get('status') == 'completed' and value.get('conclusion') == 'success', 'ci_run_scope')
        if not is_base:
            require(value.get('updated_at') == binding['completed_at'] and
                    timestamp(value['updated_at']) < timestamp(event['pull_request']['updated_at']) and
                    run != int(context['workflow_run']), 'ci_prior_completion')
    elif index in (3, 4):
        _review_attestation(value, go['reviews'][index - 3], go, owner)
    elif index == 5:
        binding = go['preregistration']
        comment(value, binding, 2, owner)
        require(sha(bounded_body(value.get('body')).encode()) == binding['body_sha256'], 'preregistration_body_hash')
    else:
        require(index == 6 and value.get('sha') == go['head'] and
                object_at(value, 'tree').get('sha') == go['tree'], 'diagnostic_commit_tree')
    return value


def reconcile(event_raw, context_raw, inputs):
    require(type(inputs) is dict and tuple(inputs) == INPUT_NAMES, 'seven_inputs_only')
    event, context = strict_json(event_raw), strict_json(context_raw)
    go, raw, body = descriptor_from_body(object_at(event, 'pull_request').get('body'))
    owner = validate_event(event, go, body, context)
    for index, name in enumerate(INPUT_NAMES):
        validate_response(index, inputs[name], go, body, event, context)
    proof = {'schema': 'worker38-authenticated-pr-admission-v1', 'repository': REPOSITORY,
        'event_name': 'pull_request', 'action': 'edited', 'first_admission': True,
        'pull_request_number': go['pr_number'], 'admission_url': go['admission_url'],
        'admission_sha256': sha(raw), 'body_sha256': sha(body.encode()),
        'previous_body_sha256': sha(event['changes']['body']['from'].encode()),
        'head': go['head'], 'tree': go['tree'], 'branch': BRANCH, 'base_head': BASE_HEAD,
        'sender': owner, 'author': owner, 'postmerge_ci': go['postmerge_ci'],
        'current_source_ci': go['current_source_ci'], 'reviews': go['reviews'],
        'preregistration': go['preregistration'], 'workflow_run': context['workflow_run'],
        'workflow_attempt': '1', 'attempt_path': context['attempt_path'],
        'attempt_id': context['attempt_id'], 'durable_root': context['durable_root'],
        'event_sha256': sha(event_raw), 'request_context_sha256': sha(context_raw),
        'admission_input_hashes': {name: sha(inputs[name]) for name in INPUT_NAMES}}
    return raw, proof


def verify_provenance(provenance_path, admission_path, expected_admission_sha256):
    """Revalidate original retained bytes; never access original runner paths."""
    parent = Path(provenance_path).parent
    require(Path(admission_path).parent == parent, 'admission_directory')
    stored = strict_json(bounded_read(provenance_path, MAX_INPUT))
    inputs = {name: bounded_read(parent / name, MAX_INPUT) for name in INPUT_NAMES}
    raw, verified = reconcile(bounded_read(parent / 'event.json', MAX_INPUT),
                              bounded_read(parent / 'request-context.json', MAX_INPUT), inputs)
    require(raw == bounded_read(admission_path, MAX_GO_BYTES) and sha(raw) == expected_admission_sha256,
            'retained_admission_binding')
    require(canonical(stored) == canonical(verified), 'provenance_semantic_replay')
    return verified


def typed_failure(error, code='local_operation_failed', phase='admission'):
    if isinstance(error, AdmissionError):
        result = {'classification': error.classification, 'code': error.code, 'phase': phase}
    elif isinstance(error, (MemoryError, RecursionError)):
        result = {'classification': 'resource_incomplete', 'code': 'memory_or_parser_exhausted', 'phase': phase}
    elif isinstance(error, OSError):
        result = {'classification': 'execution_incomplete', 'code': code, 'phase': phase}
    elif hasattr(error, 'classification') and hasattr(error, 'code'):
        result = {'classification': ('execution_incomplete' if error.classification == 'evidence_incomplete' else error.classification), 'code': error.code, 'phase': phase}
    else:
        result = {'classification': 'integrity_invalid', 'code': code, 'phase': phase}
    known_types = {'AdmissionError', 'MemoryError', 'RecursionError', 'SSLCertVerificationError',
                   'TimeoutError', 'IncompleteRead', 'PermissionError', 'FileNotFoundError',
                   'OSError', 'IntegrityError', 'RuntimeFailure'}
    name = type(error).__name__
    result['error_type'] = name if name in known_types else 'unclassified_exception'
    return result


def new_report():
    return {'schema': 'worker38-startup-receipt-v1', 'allocation_id': ALLOCATION,
        'admission_verified': False, 'classification': None, 'scientific_classification': None,
        'evaluator_starts': 0, 'actual_starts_upper_bound': 0, 'historical_source_imports': 0,
        'measurement_fixture_constructions': 0, 'games': 0, 'phase': 'admission',
        'primary_failure': None, 'secondary_failures': [], 'transition_attempted': False,
        'first_failure_monotonic': None, 'preservation_deadline_monotonic': None,
        'requested_prefix': [], 'completed_prefix': [], 'requests': [], 'response_body_bytes': 0,
        'runtime': {}, 'input_persistence': {}}


class PreservationStop(BaseException):
    classification = 'resource_incomplete'
    code = 'startup_preservation_expired'


_ACTIVE_FAILURE_SCOPE = None
FAILURE_HANDOFF_EXIT = 79


class _FailureDeadline:
    """One admission leaf's private original failure timer; never a GO flag."""
    def __init__(self, report):
        self.report = report
        self.pid = os.getpid()
        self.deadline_ns = None
        self.owned = self.confirmed = self.restored = False
        self.old_handler = None
        self.handler = self._expired

    def _expired(self, signum, frame):
        raise PreservationStop()

    def arm(self, deadline_ns):
        require(self.deadline_ns is None and os.getpid() == self.pid, 'failure_deadline_already_attempted')
        self.deadline_ns = deadline_ns
        before = time.monotonic_ns()
        remaining = deadline_ns - before
        require(remaining > 0, 'failure_deadline_expired', 'resource_incomplete')
        require(all(signal.getitimer(kind) == (0.0, 0.0) for kind in
                    (signal.ITIMER_REAL, signal.ITIMER_VIRTUAL, signal.ITIMER_PROF)), 'failure_timer_occupied', 'execution_blocked')
        self.old_handler = signal.getsignal(signal.SIGALRM)
        self.owned = True
        signal.signal(signal.SIGALRM, self.handler)
        seconds = (remaining // 1000000 - 1) / 1000
        require(seconds > 0, 'failure_timer_remainder', 'resource_incomplete')
        signal.setitimer(signal.ITIMER_REAL, seconds)
        countdown, interval = signal.getitimer(signal.ITIMER_REAL)
        after = time.monotonic_ns()
        require(signal.getsignal(signal.SIGALRM) is self.handler and type(countdown) in (int, float)
                and math.isfinite(countdown) and 0 < countdown <= seconds and interval == 0
                and after + math.ceil(countdown * 1000000000) <= deadline_ns,
                'failure_timer_unconfirmed')
        self.confirmed = True
        self.report['preservation_timer_arm'] = {'before_monotonic_ns': before,
            'after_monotonic_ns': after, 'requested_seconds': seconds, 'readback_seconds': countdown,
            'interval_seconds': interval, 'deadline_monotonic_ns': deadline_ns}

    def permit(self):
        return self.confirmed and self.deadline_ns is not None and time.monotonic_ns() < self.deadline_ns

    def close(self):
        if not self.owned:
            return []
        failures = []
        for operation in (lambda: signal.setitimer(signal.ITIMER_REAL, 0),
                          lambda: signal.signal(signal.SIGALRM, self.old_handler)):
            try:
                operation()
            except BaseException as error:
                failures.append(error)
        try:
            self.restored = (signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0) and
                signal.getsignal(signal.SIGALRM) is self.old_handler)
        except BaseException as error:
            failures.append(error)
        if not self.restored:
            failures.append(AdmissionError('failure_timer_restoration_unconfirmed'))
        self.owned = False
        return failures


def failure_work_permitted(report):
    scope = _ACTIVE_FAILURE_SCOPE
    if scope is None or scope.report is not report or not report['transition_attempted']:
        return True
    return scope.permit()


def record_failure(report, error, phase, code='local_operation_failed'):
    first = not report['transition_attempted']
    clock_error = None
    if first:
        # Deny science before clocks, handler installation or persistence.
        report['transition_attempted'] = True
        report['admission_verified'] = False
        try:
            scope = _ACTIVE_FAILURE_SCOPE
            if scope is not None and scope.report is report:
                now_ns = time.monotonic_ns()
            else:
                now = time.monotonic()
                require(type(now) in (int, float) and math.isfinite(now) and now >= 0, 'failure_clock')
                now_ns = math.floor(now * 1000000000)
            require(type(now_ns) is int and now_ns >= 0, 'failure_clock')
            deadline_ns = now_ns + 600000000000
            report['first_failure_monotonic_ns'] = now_ns
            report['preservation_deadline_monotonic_ns'] = deadline_ns
            report['first_failure_monotonic'] = now_ns / 1000000000
            report['preservation_deadline_monotonic'] = deadline_ns / 1000000000
            if scope is not None and scope.report is report:
                scope.arm(deadline_ns)
        except BaseException as caught:
            clock_error = caught
            report['transition_unconfirmed'] = True
    failure = typed_failure(error, code, phase)
    if report['primary_failure'] is None:
        report['primary_failure'] = failure
    else:
        report['secondary_failures'].append(failure)
    if clock_error is not None:
        report['secondary_failures'].append(typed_failure(clock_error, 'failure_clock_setup_failed', 'preservation_clock_setup'))
    for secondary in getattr(error, 'secondary_failures', ()):
        detail = dict(secondary)
        detail.setdefault('phase', 'descriptor_close')
        if detail.get('classification') == 'evidence_incomplete': detail['classification'] = 'execution_incomplete'
        report['secondary_failures'].append(detail)
    for secondary in getattr(error, '_bootstrap_cleanup_failures', ()):
        detail = {**secondary, 'phase': 'descriptor_close'}
        if detail.get('classification') == 'evidence_incomplete': detail['classification'] = 'execution_incomplete'
        if detail not in report['secondary_failures']: report['secondary_failures'].append(detail)
    causes = [report['primary_failure'], *report['secondary_failures']]
    winner = max(causes, key=lambda item: PRIORITY[item['classification']])
    report['classification'] = winner['classification']
    report['selected_failure'] = dict(winner)
    return failure


def close_descriptor(fd, pending=None):
    try:
        os.close(fd)
    except BaseException as error:
        failure = typed_failure(error, 'descriptor_close_failed', 'descriptor_close')
        if pending is None:
            raise AdmissionError(failure['code'], failure['classification']) from None
        if not hasattr(pending, 'secondary_failures'):
            pending.secondary_failures = []
        pending.secondary_failures.append(failure)


def bounded_read(path, cap=MAX_INPUT):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_size <= cap, 'bounded_regular_file')
        pieces, received = [], 0
        while True:
            part = os.read(fd, min(65536, cap + 1 - received))
            if not part:
                break
            received += len(part)
            require(received <= cap, 'local_input_overflow', 'resource_incomplete')
            pieces.append(part)
        after = os.fstat(fd)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'local_file_drift')
        require(received == before.st_size or str(path) == '/proc/sys/kernel/random/boot_id',
                'local_file_short_read', 'execution_incomplete')
        return b''.join(pieces)
    finally:
        close_descriptor(fd, sys.exc_info()[1])


read_raw_input = bounded_read


def read_input(path):
    raw = bounded_read(path)
    return raw, strict_json(raw)


class Evidence:
    """Exclusive writes with received, written, durable and readback facts apart."""
    def __init__(self, output):
        self.output = Path(output)
        self.files = {}
        self.directory_fd = None
        self.payload_bytes = 0
        self.terminal_bytes = 0
        self.close_confirmed = False

    def open(self):
        require(self.output.is_absolute() and os.path.realpath(self.output) == str(self.output), 'output_path')
        fd = os.open(self.output, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700, 'output_custody')
        except BaseException as error:
            close_descriptor(fd, error)
            raise
        self.directory_fd = fd

    def close(self):
        if self.directory_fd is not None:
            fd, self.directory_fd = self.directory_fd, None
            close_descriptor(fd)
            self.close_confirmed = True

    def write(self, name, raw, terminal=False):
        require(self.directory_fd is not None and name in OUTPUT_NAMES and name not in self.files,
                'exclusive_output_allowlist')
        require(type(raw) is bytes and len(raw) <= MAX_INPUT, 'local_metadata_bound')
        require(self.payload_bytes + len(raw) <= 63 * 1024 ** 2 and
                (not terminal or self.terminal_bytes + len(raw) <= 1024 ** 2),
                'evidence_bytes', 'resource_incomplete')
        record = {'size_bytes': 0, 'sha256': None, 'buffered_bytes': len(raw),
            'write_complete': False, 'file_fsync_confirmed': False, 'fsync_confirmed_bytes': 0,
            'directory_fsync_confirmed': False, 'readback_confirmed': False, 'close_confirmed': False}
        self.files[name] = record
        fd = None
        atomic = name in ('startup-handoff.json', 'measurement-handoff.txt',
                          'startup-failure-handoff.json', 'startup-preservation-handoff.txt')
        physical = name + '.tmp' if atomic else name
        try:
            fd = os.open(physical, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=self.directory_fd)
            offset = 0
            while offset < len(raw):
                count = os.write(fd, raw[offset:])
                require(type(count) is int and 0 < count <= len(raw) - offset,
                        'write_no_progress', 'execution_incomplete')
                offset += count
                self.payload_bytes += count
                record['size_bytes'] = offset
            record['write_complete'] = True
            record['sha256'] = sha(raw)
            os.fsync(fd)
            record['file_fsync_confirmed'] = True
            record['fsync_confirmed_bytes'] = offset
        except BaseException:
            if fd is not None:
                try:
                    actual = os.fstat(fd).st_size
                    self.payload_bytes += max(0, actual - record['size_bytes'])
                    record['size_bytes'] = actual
                except BaseException:
                    record['surviving_prefix_unconfirmed'] = True
            raise
        finally:
            if fd is not None:
                pending = sys.exc_info()[1]
                before_close = len(getattr(pending, 'secondary_failures', ())) if pending is not None else 0
                close_descriptor(fd, pending)
                record['close_confirmed'] = pending is None or len(getattr(pending, 'secondary_failures', ())) == before_close
        if atomic:
            # An incomplete .tmp is never a committed handoff. Both names
            # remain prospectively charged until publication and unlink fsync.
            require(self.payload_bytes + len(raw) <= 63 * 1024 ** 2, 'atomic_stage_budget', 'resource_incomplete')
            os.link(physical, name, src_dir_fd=self.directory_fd, dst_dir_fd=self.directory_fd,
                    follow_symlinks=False)
            self.payload_bytes += len(raw)
            record['staging_retained'] = physical
        os.fsync(self.directory_fd)
        record['directory_fsync_confirmed'] = True
        if atomic:
            os.unlink(physical, dir_fd=self.directory_fd)
            os.fsync(self.directory_fd)
            self.payload_bytes -= len(raw)
            record['staging_unlink_confirmed'] = True
        actual = bounded_read(self.output / name, MAX_INPUT)
        require(actual == raw, 'committed_readback_changed')
        record['readback_confirmed'] = True
        if terminal:
            self.terminal_bytes += len(raw)
        return record


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class Client:
    """Exactly the seven authenticated fixed routes; a failure ends the prefix."""
    def __init__(self, evidence, token, deadline_boottime_ns, report):
        self.evidence, self.token, self.deadline_boottime_ns, self.report = evidence, token, deadline_boottime_ns, report
        self._routes = None
        require(type(token) is str and bool(token) and token.isascii() and
                all(32 < ord(c) < 127 for c in token), 'token_absent', 'execution_blocked')
        require(not any(name in os.environ for name in ('SSL_CERT_FILE', 'SSL_CERT_DIR', 'OPENSSL_CONF',
                'OPENSSL_MODULES', 'SSLKEYLOGFILE')), 'alternate_tls_configuration', 'execution_blocked')
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
                urllib.request.HTTPSHandler(context=ssl.create_default_context()))

    def remaining(self):
        remaining = self.deadline_boottime_ns - time.clock_gettime_ns(time.CLOCK_BOOTTIME)
        require(remaining > 0, 'admission_deadline', 'resource_incomplete')
        return min(10, remaining / 1000000000)

    def fetch(self, url, name):
        ordinal = len(self.report['requests'])
        require(self._routes is not None and ordinal < 7 and
                (name, url) == (self._routes[ordinal][0], API + self._routes[ordinal][1]),
                'fixed_request_order_and_destination')
        record = {'name': name, 'status': None, 'received_bytes': 0, 'buffered_bytes': 0,
            'retained_bytes': 0, 'fsync_confirmed_bytes': 0, 'eof_confirmed': False,
            'complete': False, 'close_confirmed': False, 'semantic_validated': False}
        self.report['requests'].append(record)
        response, primary, raw, pieces = None, None, b'', []
        omit = False
        def failure(error, phase, code):
            nonlocal primary
            if primary is None:
                primary = error
            record_failure(self.report, error, phase, code)
        try:
            request = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + self.token,
                'Accept': 'application/vnd.github+json', 'Accept-Encoding': 'identity',
                'User-Agent': CONSUMER, 'X-GitHub-Api-Version': '2022-11-28'}, method='GET')
            try:
                response = self.opener.open(request, timeout=self.remaining())
            except urllib.error.HTTPError as error:
                response = error
            status = getattr(response, 'status', None)
            require(type(status) is int and 100 <= status <= 599, 'http_status_unknown')
            record['status'] = status
            omit = 300 <= status <= 399
            if omit:
                record['omission_reason'] = 'redirect_body_and_location_may_contain_signed_url'
            encoding = response.headers.get('Content-Encoding', 'identity')
            require(type(encoding) is str and encoding.lower() in ('', 'identity'), 'content_encoding')
            length = response.headers.get('Content-Length')
            require(length is None or (type(length) is str and len(length) <= 16 and
                    re.fullmatch('[0-9]+', length) is not None), 'content_length')
            declared = int(length) if length is not None else None
            require(declared is None or declared <= MAX_INPUT, 'content_length_overflow', 'resource_incomplete')
            while True:
                self.remaining()
                size = min(65536, MAX_INPUT + 1 - record['received_bytes'],
                           MAX_RECEIVED - self.report['response_body_bytes'])
                require(size > 0, 'response_budget', 'resource_incomplete')
                incomplete = False
                try:
                    part = response.read(size)
                except http.client.IncompleteRead as error:
                    part = error.partial
                    incomplete = True
                    record['incomplete_read'] = True
                    record['unknown_remainder'] = True
                require(type(part) is bytes, 'response_read_type')
                before = record['received_bytes']
                record['received_bytes'] += len(part)
                self.report['response_body_bytes'] += len(part)
                if record['received_bytes'] > MAX_INPUT:
                    record['overflow_witness_bytes'] = min(1, record['received_bytes'] - MAX_INPUT)
                    record['unbuffered_received_bytes'] = record['received_bytes'] - MAX_INPUT
                if not omit and before < MAX_INPUT:
                    chunk = part[:MAX_INPUT - before]
                    pieces.append(chunk)
                    record['buffered_bytes'] += len(chunk)
                require(record['received_bytes'] <= MAX_INPUT and self.report['response_body_bytes'] < MAX_RECEIVED,
                        'input_body_overflow', 'resource_incomplete')
                require(len(part) <= size, 'response_read_contract')
                require(not incomplete, 'response_incomplete_read', 'execution_incomplete')
                if not part:
                    record['eof_confirmed'] = True
                    break
            require(declared is None or declared == record['received_bytes'], 'response_length_mismatch')
            require(status == 200, 'http_redirect' if omit else 'http_status', 'execution_blocked')
        except BaseException as error:
            # Exception strings are deliberately never retained.
            failure(error, 'network_read', 'transport_failed')
        finally:
            if response is not None:
                try:
                    response.close()
                    require(response.closed is True, 'response_close_unconfirmed', 'execution_incomplete')
                    record['close_confirmed'] = True
                except BaseException as error:
                    failure(error, 'response_close', 'response_close_failed')
        if primary is not None:
            record['incomplete_input'] = True
        if not omit and failure_work_permitted(self.report):
            try:
                raw = b''.join(pieces)
                self.evidence.write(name, raw)
            except BaseException as error:
                failure(error, 'input_persistence', 'input_persistence_failed')
            finally:
                stored = self.evidence.files.get(name, {})
                record['retained_bytes'] = stored.get('size_bytes', 0)
                record['fsync_confirmed_bytes'] = stored.get('fsync_confirmed_bytes', 0)
                self.report['input_persistence'][name] = dict(stored)
        if not omit and not failure_work_permitted(self.report):
            record['omission_reason'] = 'preservation_authority_unconfirmed_or_expired'
        if primary is not None:
            if isinstance(primary, PreservationStop):
                raise primary
            if isinstance(primary, AdmissionError):
                raise primary
            cause = self.report['primary_failure']
            raise AdmissionError(cause['code'], cause['classification']) from None
        record['complete'] = True
        return raw

    def inputs(self, go, body, event, context):
        require(self._routes is None and not self.report['requests'], 'single_request_sequence')
        self._routes = request_map(go)
        values = {}
        for index, (name, path) in enumerate(self._routes):
            self.report['requested_prefix'].append(name)
            raw = self.fetch(API + path, name)
            try:
                validate_response(index, raw, go, body, event, context)
            except BaseException as error:
                record_failure(self.report, error, 'input_validation')
                raise
            values[name] = raw
            self.report['requests'][-1]['semantic_validated'] = True
            self.report['completed_prefix'].append(name)
        return values


def verify_local_sources(source, go, observed_runtime):
    source = Path(source)
    require(source.is_absolute() and os.path.realpath(source) == str(source), 'checkout_path')
    require(go['head'] == os.environ.get('WORKER38_HEAD') and go['tree'] == os.environ.get('WORKER38_TREE'),
            'checkout_head_tree')
    for name, expected in go['checked_file_sha256'].items():
        path = source / name
        require(os.path.realpath(path) == str(path), 'source_symlink')
        raw = bounded_read(path, MAX_INPUT)
        require(sha(raw) == expected, 'checked_source_changed')
    pins = {'PROTOCOL.md': go['protocol_sha256'], 'INTEGRATION-CONTRACT.json': go['contract_sha256'],
            'FINITE-PREPARATION-PLAN.json': go['finite_plan_sha256'],
            'comparator-source-manifest.json': go['source_manifest_sha256']}
    for name, expected in pins.items():
        require(sha(bounded_read(source / EXPERIMENT / name)) == expected, 'metadata_source_binding')
    contract = strict_json(bounded_read(source / EXPERIMENT / 'INTEGRATION-CONTRACT.json'))
    require(canonical(go['startup_resources']) == canonical(contract['budgets']) and
            canonical(go['inherited_limits']) == canonical(contract['runtime']['inherited_initial_limits']) and
            go['cell_preflight_modules'] == contract['staging']['initial_scientific_modules'],
            'registered_runtime_source_contract')
    receipt_binding = go['focused_source_receipt']
    raw = bounded_read(source / receipt_binding['path'])
    require(len(raw) == receipt_binding['size_bytes'] and sha(raw) == receipt_binding['sha256'], 'focused_receipt_raw_binding')
    receipt = strict_json(raw)
    require(receipt.get('success') is True and type(receipt.get('failures')) is int and receipt['failures'] == 0
            and type(receipt.get('errors')) is int and receipt['errors'] == 0, 'focused_receipt_success')
    for name in ('candidate_evaluator_calls', 'reference_evaluator_calls', 'games',
                 'measurement_fixture_constructions', 'historical_source_imports'):
        require(type(receipt.get(name)) is int and receipt[name] == 0, 'focused_receipt_zero_science')
    require(receipt.get('checked_file_sha256') == go['checked_file_sha256'], 'focused_checked_source_map')
    # Shared runtime uses executable/library observations; the scientific helper
    # also understands the loader identity format used by offline evidence.
    require(canonical(observed_runtime.get('inherited_limits')) == canonical(go['inherited_limits']),
            'observed_inherited_limits')
    library_hash = observed_runtime.get('library_sha256')
    executable_hash = observed_runtime.get('executable_sha256')
    if library_hash is None and type(observed_runtime.get('files')) is dict:
        library_hash = observed_runtime['files'].get('library', {}).get('sha256')
        executable_hash = observed_runtime['files'].get('executable', {}).get('sha256')
    if library_hash is None and type(observed_runtime.get('loader_identity')) is dict:
        library_hash = observed_runtime['loader_identity'].get('library_sha256')
        executable_hash = observed_runtime['loader_identity'].get('executable_sha256')
    require(library_hash == go['loader_pin']['library_sha256'] and
            executable_hash == go['loader_pin']['executable_sha256'], 'authenticated_runtime_mapping')
    return receipt


def context_from_environment(go, output, source):
    env = os.environ
    require(env.get('GITHUB_SERVER_URL') == 'https://github.com' and
            env.get('GITHUB_API_URL') == 'https://api.github.com', 'github_origin')
    cache = env.get('RUNNER_TOOL_CACHE', '')
    context = {'schema': 'worker38-github-request-context-v1', 'repository': env.get('GITHUB_REPOSITORY'),
        'actor': env.get('GITHUB_ACTOR'), 'triggering_actor': env.get('GITHUB_TRIGGERING_ACTOR'),
        'event_name': env.get('GITHUB_EVENT_NAME'), 'workflow_run': env.get('GITHUB_RUN_ID'),
        'workflow_attempt': env.get('GITHUB_RUN_ATTEMPT'), 'runner_name': env.get('RUNNER_NAME'),
        'runner_tool_cache': cache, 'checkout_path': str(source), 'runner_temp': env.get('RUNNER_TEMP'),
        'durable_root': cache + '/worker38-synthetic-profile', 'attempt_path': str(output),
        'attempt_id': 'worker38-' + str(env.get('GITHUB_RUN_ID')) + '-1',
        'authentication': 'github-repository-read-token',
        'requests': [{'name': name, 'method': 'GET', 'path': path} for name, path in request_map(go)]}
    validate_context(context, go)
    return context


def validate_reservation(output, context, head):
    """Inspect only this newly consumed Worker38 claim; no old namespace IO."""
    output = Path(output)
    require(str(output) == context['attempt_path'], 'reservation_attempt')
    expected = ('schema=worker38-observed-reservation-v1\nallocation_id=' + ALLOCATION + '\nrun_id=' +
        context['workflow_run'] + '\nrun_attempt=1\nobserved_head=' + head +
        '\ndescriptor_binding=not_yet_validated\nevaluator_starts=0\nscientific_classification=null\n').encode()
    require(bounded_read(output / 'reservation.txt', 4096) == expected and
            bounded_read(output.parent / 'reservation.txt', 4096) == expected, 'consumed_reservation_binding')


def check_deadline(deadline_ns, code='admission_deadline'):
    require(type(deadline_ns) is int and deadline_ns > 0 and
            time.clock_gettime_ns(time.CLOCK_BOOTTIME) < deadline_ns, code, 'resource_incomplete')


def startup_deadline():
    def integer_env(name):
        value = os.environ.get(name)
        require(type(value) is str and re.fullmatch('[1-9][0-9]{0,18}', value) is not None, 'startup_clock_field')
        return int(value)
    start = integer_env('WORKER38_STARTUP_BOOTTIME_NS')
    outer = integer_env('WORKER38_STARTUP_DEADLINE_BOOTTIME_NS')
    leaf = integer_env('WORKER38_ADMISSION_DEADLINE_BOOTTIME_NS')
    now = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    require(outer == start + 120000000000 and start <= now and leaf <= outer and
            leaf <= now + 90000000000, 'original_startup_deadlines')
    check_deadline(leaf)
    return leaf


HANDOFF_KEYS = ('schema', 'consumer', 'boot_id', 'measurement_monotonic_ns', 'measurement_boottime_ns',
    'measurement_deadline_monotonic_ns', 'measurement_deadline_boottime_ns', 'attempt_path', 'source_path',
    'head', 'tree', 'workflow_run', 'workflow_attempt', 'admission_sha256', 'provenance_sha256',
    'runtime_sha256', 'source_map_sha256', 'restored_inventory_sha256', 'startup_receipt_sha256')
HANDOFF_LINES = ('boot_id', 'measurement_monotonic_ns', 'measurement_boottime_ns',
    'measurement_deadline_boottime_ns', 'attempt_path', 'source_path', 'head', 'tree',
    'admission_sha256', 'provenance_sha256', 'runtime_sha256', 'source_map_sha256')


def validate_handoff(value):
    keys(value, HANDOFF_KEYS, 'handoff_schema')
    require(value['schema'] == 'worker38-startup-handoff-v1' and value['consumer'] == CONSUMER,
            'handoff_consumer')
    require(type(value['boot_id']) is str and re.fullmatch('[0-9a-f-]{36}', value['boot_id']) is not None,
            'handoff_boot')
    for name in ('measurement_monotonic_ns', 'measurement_boottime_ns', 'measurement_deadline_monotonic_ns',
                 'measurement_deadline_boottime_ns'):
        positive_int(value[name], 'handoff_clock')
    require(value['measurement_deadline_monotonic_ns'] == value['measurement_monotonic_ns'] + 1800000000000 and
            value['measurement_deadline_boottime_ns'] == value['measurement_boottime_ns'] + 1800000000000,
            'handoff_original_deadline')
    for name in ('admission_sha256', 'provenance_sha256', 'runtime_sha256', 'source_map_sha256',
                 'restored_inventory_sha256', 'startup_receipt_sha256'):
        hex_digest(value[name], 'handoff_hash')
    for name in ('head', 'tree'):
        hex_digest(value[name], name, 40)
    for name in ('attempt_path', 'source_path'):
        text = value[name]
        require(type(text) is str and len(text) <= 4096 and all(32 <= ord(c) < 127 for c in text)
                and str(PurePosixPath(text)) == text and text.startswith('/') and '..' not in PurePosixPath(text).parts,
                'handoff_path')
    run = value['workflow_run']
    require(type(run) is str and re.fullmatch('[1-9][0-9]{0,18}', run) is not None and
            value['workflow_attempt'] == '1' and value['attempt_path'].endswith(
                '/worker38-synthetic-profile/allocations/' + ALLOCATION + '/run-' + run + '-attempt-1'),
            'handoff_new_attempt')
    return value


def publish_handoff(evidence, go, context, proof, runtime_raw, receipt_raw, manifest, deadline):
    check_deadline(deadline)
    boot_id = bounded_read('/proc/sys/kernel/random/boot_id', 64).decode('ascii').strip()
    # Earlier BOOTTIME sample makes the shell's cutoff conservative.
    boottime = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    monotonic = time.monotonic_ns()
    value = {'schema': 'worker38-startup-handoff-v1', 'consumer': CONSUMER, 'boot_id': boot_id,
        'measurement_monotonic_ns': monotonic, 'measurement_boottime_ns': boottime,
        'measurement_deadline_monotonic_ns': monotonic + 1800000000000,
        'measurement_deadline_boottime_ns': boottime + 1800000000000,
        'attempt_path': context['attempt_path'], 'source_path': context['checkout_path'],
        'head': go['head'], 'tree': go['tree'], 'workflow_run': context['workflow_run'], 'workflow_attempt': '1',
        'admission_sha256': proof['admission_sha256'], 'provenance_sha256': sha(canonical(proof)),
        'runtime_sha256': sha(runtime_raw), 'source_map_sha256': sha(canonical(go['checked_file_sha256'])),
        'restored_inventory_sha256': sha(canonical(manifest['files'])), 'startup_receipt_sha256': sha(receipt_raw)}
    validate_handoff(value)
    raw = canonical(value)
    evidence.write('startup-handoff.json', raw)
    check_deadline(deadline)
    companion = 'version=worker38-handoff-v1\nhandoff_sha256=' + sha(raw) + '\n'
    companion += ''.join(name + '=' + str(value[name]) + '\n' for name in HANDOFF_LINES)
    require(len(companion.encode('ascii')) <= 4096, 'handoff_shell_bound')
    evidence.write('measurement-handoff.txt', companion.encode('ascii'))
    check_deadline(deadline)
    return value


FAILURE_HANDOFF_KEYS = ('schema', 'consumer', 'origin', 'allocation_id', 'workflow_run', 'workflow_attempt',
    'attempt_path', 'source_path', 'head', 'tree', 'boot_id', 'first_failure_monotonic_ns',
    'preservation_deadline_monotonic_ns', 'clock_pair_boottime_ns', 'clock_pair_monotonic_ns',
    'preservation_deadline_boottime_ns', 'failure_receipt', 'shell_runtime',
    'runtime_observation_sha256', 'loader_pin', 'http_descriptors_closed', 'body_descriptors_closed',
    'failure_timer_restored', 'admitted', 'measurement_started', 'actual_entry_lower_bound', 'actual_entry_upper_bound')
FAILURE_HANDOFF_LINES = ('version', 'startup_failure_handoff_sha256', 'preservation_deadline_monotonic_ms',
                         'preservation_deadline_boottime_ms', 'preservation_boot_id')


def failure_descriptors_closed(report, evidence, input_closed):
    """Unknown network/body closure cannot be promoted to failure custody."""
    if input_closed is not True:
        return False
    if not all(record.get('close_confirmed') is True for record in report['requests']):
        return False
    if not all(record.get('close_confirmed') is True for record in evidence.files.values()):
        return False
    if not all(record.get('close_confirmed') is True for record in report['input_persistence'].values()):
        return False
    causes = [report['primary_failure'], *report['secondary_failures']]
    return not any(item is not None and ('close' in item.get('phase', '') or
        'close' in item.get('code', '') or 'restoration_unconfirmed' in item.get('code', '')) for item in causes)


def publish_failure_handoff(evidence, report, scope, source, *, runtime_passed, input_closed):
    require(scope is _ACTIVE_FAILURE_SCOPE and scope.report is report and scope.confirmed and
            scope.restored and scope.permit() and not report.get('transition_unconfirmed'), 'failure_authority_unconfirmed')
    require(runtime_passed is True and failure_descriptors_closed(report, evidence, input_closed),
            'failure_runtime_or_close_unconfirmed')
    require(report['admission_verified'] is False and report['primary_failure'] is not None and
            report['evaluator_starts'] == report['actual_starts_upper_bound'] == 0, 'failure_zero_entry_boundary')
    root = evidence.output
    source = Path(source)
    run = os.environ.get('GITHUB_RUN_ID')
    require(type(run) is str and re.fullmatch('[1-9][0-9]{0,18}', run) is not None and
            os.environ.get('GITHUB_RUN_ATTEMPT') == '1', 'failure_run_identity')
    expected = Path(os.environ.get('RUNNER_TOOL_CACHE', '')) / 'worker38-synthetic-profile/allocations' / ALLOCATION / ('run-' + run + '-attempt-1')
    require(root == expected and os.path.realpath(root) == str(root) and source.is_absolute() and
            str(source) == os.environ.get('GITHUB_WORKSPACE') and os.path.realpath(source) == str(source),
            'failure_source_attempt_binding')
    head, tree = os.environ.get('WORKER38_HEAD'), os.environ.get('WORKER38_TREE')
    hex_digest(head, 'failure_head', 40); hex_digest(tree, 'failure_tree', 40)
    runtime = report['runtime']
    files = runtime.get('files', {})
    require(runtime.get('memory_cap', {}).get('confirmed') is True and
            set(files) == {'executable', 'library'} and
            all(files[name].get('mapped_identity_confirmed') is True for name in files) and
            files['executable'].get('sha256') == RUNTIME['executable_sha256'] and
            files['library'].get('sha256') == LIBRARY_SHA256 and
            files['library'].get('size_bytes') == LIBRARY_SIZE, 'failure_observed_runtime')
    shell_raw = bounded_read(root / 'shell-runtime.txt', 4096)
    shell_lines = shell_raw.decode('ascii').splitlines()
    require(len(shell_lines) == 7 and shell_lines[0] == 'version=worker38-shell-runtime-v1' and
            shell_lines[3] == 'head=' + head and shell_lines[4] == 'tree=' + tree,
            'failure_shell_runtime_binding')
    report['http_descriptors_closed'] = True
    report['body_descriptors_closed'] = True
    report['failure_timer_restored'] = True
    failure_raw = canonical(report)
    if 'startup-failure.json' not in evidence.files:
        evidence.write('startup-failure.json', failure_raw, terminal=True)
    else:
        require(bounded_read(root / 'startup-failure.json') == failure_raw, 'failure_receipt_changed')
    require(scope.permit(), 'failure_preservation_expired', 'resource_incomplete')
    boot_id = bounded_read('/proc/sys/kernel/random/boot_id', 64).decode('ascii').strip()
    require(re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', boot_id) is not None, 'failure_boot_identity')
    boot = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    mono = time.monotonic_ns()
    deadline = scope.deadline_ns
    require(report['first_failure_monotonic_ns'] <= mono < deadline and
            deadline == report['first_failure_monotonic_ns'] + 600000000000,
            'failure_original_deadline')
    value = {'schema': 'worker38-startup-failure-handoff-v1', 'consumer': CONSUMER,
        'origin': 'admission_failure', 'allocation_id': ALLOCATION, 'workflow_run': run, 'workflow_attempt': '1',
        'attempt_path': str(root), 'source_path': str(source), 'head': head, 'tree': tree, 'boot_id': boot_id,
        'first_failure_monotonic_ns': report['first_failure_monotonic_ns'],
        'preservation_deadline_monotonic_ns': deadline, 'clock_pair_boottime_ns': boot,
        'clock_pair_monotonic_ns': mono, 'preservation_deadline_boottime_ns': boot + deadline - mono,
        'failure_receipt': {'path': 'startup-failure.json', 'size_bytes': len(failure_raw), 'sha256': sha(failure_raw)},
        'shell_runtime': {'path': 'shell-runtime.txt', 'size_bytes': len(shell_raw), 'sha256': sha(shell_raw)},
        'runtime_observation_sha256': sha(canonical(runtime)),
        'loader_pin': {'schema': 'worker38-loader-pin-v1', 'executable_sha256': RUNTIME['executable_sha256'],
            'library_relative_path': 'Python/3.11.16/x64/lib/libpython3.11.so.1.0',
            'library_sha256': LIBRARY_SHA256, 'library_size_bytes': LIBRARY_SIZE},
        'http_descriptors_closed': True, 'body_descriptors_closed': True, 'failure_timer_restored': True,
        'admitted': False, 'measurement_started': False, 'actual_entry_lower_bound': 0, 'actual_entry_upper_bound': 0}
    keys(value, FAILURE_HANDOFF_KEYS, 'failure_handoff_schema')
    raw = canonical(value)
    require(len(raw) <= 4096, 'failure_handoff_bound')
    evidence.write('startup-failure-handoff.json', raw, terminal=True)
    companion = ('version=worker38-startup-failure-v1\nstartup_failure_handoff_sha256=' + sha(raw) +
        '\npreservation_deadline_monotonic_ms=' + str(deadline // 1000000) +
        '\npreservation_deadline_boottime_ms=' + str(value['preservation_deadline_boottime_ns'] // 1000000) +
        '\npreservation_boot_id=' + boot_id + '\n').encode('ascii')
    require(len(companion) <= 1024 and scope.permit(), 'failure_companion_bound')
    evidence.write('startup-preservation-handoff.txt', companion, terminal=True)
    require(scope.permit(), 'failure_preservation_expired', 'resource_incomplete')
    return value


def main(argv=None):
    global _ACTIVE_FAILURE_SCOPE
    parser = argparse.ArgumentParser(description='Worker38 fixed admission leaf')
    for name in ('event', 'output', 'source'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(argv)
    report, inputs_evidence, root_evidence, client = new_report(), None, None, None
    scope = _FailureDeadline(report)
    _ACTIVE_FAILURE_SCOPE = scope
    runtime_passed = False
    input_closed = True
    unknown_source_close = False
    try:
        deadline = startup_deadline()
        report['administrative_deadlines'] = {
            'startup_boottime_ns': int(os.environ['WORKER38_STARTUP_BOOTTIME_NS']),
            'startup_deadline_boottime_ns': int(os.environ['WORKER38_STARTUP_DEADLINE_BOOTTIME_NS']),
            'admission_deadline_boottime_ns': deadline,
            'observed_leaf_entry_boottime_ns': time.clock_gettime_ns(time.CLOCK_BOOTTIME)}
        output, source = Path(args.output), Path(args.source)
        # Lexical namespace validation precedes all attempt reads.
        expected = Path(os.environ.get('RUNNER_TOOL_CACHE', '')) / 'worker38-synthetic-profile' / 'allocations' / ALLOCATION / (
            'run-' + os.environ.get('GITHUB_RUN_ID', '') + '-attempt-1')
        require(output.is_absolute() and output == expected and Path(args.event) == output / 'event.json', 'fixed_attempt_path')
        root_evidence = Evidence(output)
        root_evidence.open()
        from worker_bootstrap_shared import runtime_start
        observed = {}
        runtime = runtime_start(observed, CONSUMER)
        report['runtime'] = runtime
        runtime_passed = True
        resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
        report['admission_CPU_limit'] = list(resource.getrlimit(resource.RLIMIT_CPU))
        require(report['admission_CPU_limit'] == [90, 90], 'admission_cpu_cap')
        event_raw = bounded_read(args.event)
        require(sha(event_raw) == os.environ.get('WORKER38_EVENT_SHA256') and
                os.environ.get('WORKER38_EVENT_FSYNC_CONFIRMED') == '1', 'event_snapshot_binding')
        event = strict_json(event_raw)
        go, admission_raw, body = descriptor_from_body(object_at(event, 'pull_request').get('body'))
        require(go['preregistration_url'] == PREREGISTRATION and
                go['preregistration']['body_sha256'] == PREREGISTRATION_BODY_SHA256,
                'registered_preregistration_anchor')
        context = context_from_environment(go, output, source)
        validate_event(event, go, body, context)
        validate_reservation(output, context, go['head'])
        check_deadline(deadline)
        input_root = output / 'admission-inputs'
        input_root.mkdir(mode=0o700, exist_ok=False)
        os.fsync(root_evidence.directory_fd)
        inputs_evidence = Evidence(input_root)
        input_closed = False
        inputs_evidence.open()
        context_raw = canonical(context)
        inputs_evidence.write('event.json', event_raw)
        inputs_evidence.write('request-context.json', context_raw)
        token = os.environ.get('GH_TOKEN', '')
        client = Client(inputs_evidence, token, deadline, report)
        inputs = client.inputs(go, body, event, context)
        client.token = None
        token = None
        raw, proof = reconcile(event_raw, context_raw, inputs)
        require(raw == admission_raw, 'descriptor_replay')
        report['phase'] = 'source_validation'
        verify_local_sources(source, go, runtime)
        check_deadline(deadline)
        from worker38.common import Budget
        from worker38.sources import read_manifest, restore_staged
        manifest_path = source / EXPERIMENT / 'comparator-source-manifest.json'
        manifest = read_manifest(manifest_path)
        free = os.statvfs(output)
        require(free.f_bavail * free.f_frsize >= 1073741824, 'free_space', 'resource_incomplete')
        report['free_bytes_before_source'] = free.f_bavail * free.f_frsize
        root_evidence.write('source-manifest.json', bounded_read(manifest_path))
        report['phase'] = 'source_staging'
        restore_staged(source, output / 'restored', manifest, Budget(output))
        report['phase'] = 'admission'
        check_deadline(deadline)
        root_evidence.write('restored-inventory.json', canonical(manifest['files']))
        inputs_evidence.write('admission.json', raw)
        inputs_evidence.write('provenance.json', canonical(proof))
        inputs_evidence.close()
        input_closed = inputs_evidence.close_confirmed and all(record.get('close_confirmed') is True for record in inputs_evidence.files.values())
        inputs_evidence = None
        report['admission_verified'] = True
        report['phase'] = 'admission_complete'
        report['admission_CPU_seconds'] = time.process_time()
        require(report['admission_CPU_seconds'] < 90, 'admission_cpu_deadline', 'resource_incomplete')
        report['restored_source_inventory'] = manifest['files']
        runtime_raw = canonical(runtime)
        root_evidence.write('runtime.json', runtime_raw)
        report['input_persistence'] = {name: record for name, record in report['input_persistence'].items()}
        receipt_raw = canonical(report)
        root_evidence.write('startup-receipt.json', receipt_raw)
        publish_handoff(root_evidence, go, context, proof, runtime_raw, receipt_raw, manifest, deadline)
        root_evidence.close()
        root_evidence = None
        check_deadline(deadline)
        require(time.process_time() < 90, 'admission_cpu_deadline', 'resource_incomplete')
        _ACTIVE_FAILURE_SCOPE = None
        return 0
    except BaseException as error:
        if report['phase'] == 'source_staging':
            unknown_source_close = True
        if not report['primary_failure'] or typed_failure(error)['code'] != report['primary_failure']['code']:
            record_failure(report, error, report['phase'])
    finally:
        if client is not None:
            client.token = None
        for evidence in (inputs_evidence,):
            if evidence is not None:
                try:
                    evidence.close()
                    input_closed = input_closed or (evidence.close_confirmed and all(record.get('close_confirmed') is True for record in evidence.files.values()))
                except BaseException as error:
                    input_closed = False
                    record_failure(report, error, 'custody_close')
    for error in scope.close():
        record_failure(report, error, 'failure_timer_restoration')
    ready = False
    if root_evidence is not None:
        try:
            if (scope.confirmed and scope.restored and scope.permit() and runtime_passed and
                    not unknown_source_close and failure_descriptors_closed(report, root_evidence, input_closed)):
                publish_failure_handoff(root_evidence, report, scope, Path(args.source),
                                        runtime_passed=runtime_passed, input_closed=input_closed)
                ready = True
            elif 'startup-failure.json' not in root_evidence.files:
                # One bounded last-known marker only. Unconfirmed authority
                # never enables response draining, scanning or packaging.
                root_evidence.write('startup-failure.json', canonical(report), terminal=True)
        except BaseException as error:
            ready = False
            record_failure(report, error, 'failure_handoff_persistence')
        finally:
            try:
                root_evidence.close()
                ready = ready and root_evidence.close_confirmed
            except BaseException as error:
                ready = False
                record_failure(report, error, 'custody_close')
    if ready:
        try:
            require(scope.permit(), 'failure_preservation_expired', 'resource_incomplete')
            check_deadline(deadline)
        except BaseException as error:
            ready = False
            record_failure(report, error, 'failure_handoff_final_check')
    _ACTIVE_FAILURE_SCOPE = None
    return FAILURE_HANDOFF_EXIT if ready else EXIT_CODES.get(report['classification'], 65)



if __name__ == '__main__':
    raise SystemExit(main())
