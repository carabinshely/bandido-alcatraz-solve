"""Authenticate retained GitHub inputs, never fetch, claim, import policy or run it.

The workflow supplies freshly authenticated API responses and the original event.
This gate authenticates the first PR-body edit; driver.read_admission separately
validates every source/runtime/resource/review field of the external full freeze.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

if __name__ == '__main__' and not __package__:
    # Direct script invocation has only this sibling module directory on sys.path.
    from common import IntegrityError as LoaderIntegrityError, loader_identity, loader_pin
else:
    from worker36.common import IntegrityError as LoaderIntegrityError, loader_identity, loader_pin

REPOSITORY = 'carabinshely/bandido-alcatraz-solve'
OWNER = 'carabinshely'
BRANCH = 'research/worker36-synthetic-profile-overhead'
BASE_HEAD = '9c1eeeb8a26868d41f8d8d89b17fc897a60cb38b'
PREREGISTRATION = 'https://github.com/' + REPOSITORY + '/issues/2#issuecomment-5967160389'
WEB = 'https://github.com/' + REPOSITORY
API = 'https://api.github.com/repos/' + REPOSITORY
CI_RUN = 37108669492
START = 'WORKER36_ADMISSION_JSON'
END = 'END_WORKER36_ADMISSION_JSON'
DIGEST = 'WORKER36_ADMISSION_SHA256'
MAX_BODY_BYTES = 65536
MAX_GO_BYTES = 60000
MAX_INPUT_BYTES = 2 * 1024 ** 2


class AdmissionError(ValueError):
    """Invalid or absent admission; always zero evaluator authority."""


def require(condition, message):
    # Deliberately not an assert: -O/PYTHONOPTIMIZE cannot erase authorization.
    if not condition:
        raise AdmissionError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    def number(value):
        parsed = float(value)
        require(math.isfinite(parsed), 'nonfinite JSON number')
        return parsed
    def constant(value):
        raise AdmissionError('nonfinite JSON constant')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_float=number,
                          parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AdmissionError('invalid JSON input') from error


def object_at(value, key):
    require(type(value) is dict and type(value.get(key)) is dict,
            'missing object: ' + key)
    return value[key]


def positive_int(value, label):
    require(type(value) is int and value > 0, 'invalid ' + label)
    return value


def identity(value):
    require(type(value) is dict and value.get('login') == OWNER and
            value.get('type') == 'User', 'unauthorized owner identity')
    return {'login': OWNER, 'id': positive_int(value.get('id'), 'owner ID'), 'type': 'User'}


def bounded_body(value):
    require(type(value) is str, 'body must be a string')
    require(len(value.encode('utf-8')) <= MAX_BODY_BYTES and '\r' not in value,
            'oversized body or nonliteral line endings')
    return value


def admitted_loader_pin(value):
    """Require the portable exact-key pin; no host file access or fallback."""
    try:
        pin = loader_pin(value)
    except LoaderIntegrityError as error:
        raise AdmissionError('invalid admitted loader pin: ' + str(error)) from error
    require(value == pin, 'admission requires the exact portable loader pin')
    return pin


def extract_pr_admission(event, live_pr, live_ci):
    """Return exact GO bytes and verified provenance from fixed input objects.

    Missing markers reject rather than admitting any default. This function is
    pure and independent of process environment, interpreter optimization and IO.
    Authenticity of inputs comes from the workflow's GitHub event and token-bound
    fresh GitHub API requests; raw input custody is recorded by authenticate.
    """
    require(type(event) is dict and type(live_pr) is dict and type(live_ci) is dict,
            'event, PR and CI objects required')
    require(event.get('action') == 'edited', 'only edited PR events can admit')
    repository = object_at(event, 'repository')
    require(repository.get('full_name') == REPOSITORY and
            repository.get('html_url') == WEB and repository.get('url') == API,
            'wrong event repository')
    owner = identity(object_at(repository, 'owner'))
    sender = identity(object_at(event, 'sender'))
    require(sender == owner, 'sender is not the authenticated repository owner')
    event_pr = object_at(event, 'pull_request')
    number = positive_int(event.get('number'), 'event PR number')
    pr_url, api_url = WEB + '/pull/' + str(number), API + '/pulls/' + str(number)
    require(event_pr.get('number') == live_pr.get('number') == number,
            'event/live PR number mismatch')
    for pr in (event_pr, live_pr):
        require(pr.get('html_url') == pr_url and pr.get('url') == api_url and
                pr.get('issue_url') == API + '/issues/' + str(number), 'wrong PR URLs')
        require(pr.get('state') == 'open' and pr.get('merged') is False and
                pr.get('merged_at') is None, 'PR must be open and unmerged')
        require(identity(object_at(pr, 'user')) == owner, 'PR author is not owner')
        head, base = object_at(pr, 'head'), object_at(pr, 'base')
        require(head.get('ref') == BRANCH and base.get('ref') == 'main' and
                base.get('sha') == BASE_HEAD, 'wrong branch or base head')
        for ref in (head, base):
            repo = object_at(ref, 'repo')
            require(repo.get('full_name') == REPOSITORY and repo.get('html_url') == WEB
                    and repo.get('url') == API and identity(object_at(repo, 'owner')) == owner,
                    'fork or unexpected PR repository')
        require(type(head.get('sha')) is str and
                re.fullmatch('[0-9a-f]{40}', head['sha']) is not None, 'invalid head SHA')
    require(event_pr['head']['sha'] == live_pr['head']['sha'], 'stale PR head')
    body = bounded_body(event_pr.get('body'))
    require(body == bounded_body(live_pr.get('body')), 'stale PR body')
    previous = bounded_body(object_at(object_at(event, 'changes'), 'body').get('from'))
    require(previous != body, 'body did not change')
    require('WORKER36_ADMISSION' not in previous, 'admission already appeared in previous body')
    require(body.count(START) == 2 and body.count(END) == 1 and
            body.count(DIGEST) == 1, 'exactly one admission block and digest required')
    lines = body.split('\n')
    require(lines.count(START) == lines.count(END) == 1, 'literal admission marker lines required')
    begin, end = lines.index(START), lines.index(END)
    require(begin < end, 'reversed admission markers')
    digest_lines = [(index, line) for index, line in enumerate(lines) if DIGEST in line]
    digest_index, digest_line = digest_lines[0]
    match = re.fullmatch(DIGEST + ': ([0-9a-f]{64})', digest_line)
    require(match is not None and not begin < digest_index < end, 'literal external digest field required')
    raw = ('\n'.join(lines[begin + 1:end]) + '\n').encode('utf-8')
    require(1 < len(raw) <= MAX_GO_BYTES and sha(raw) == match.group(1), 'admission payload length/hash')
    go = strict_json(raw)
    require(type(go) is dict and go.get('schema') == 'worker36-one-shot-admission-v1'
            and go.get('admitted') is True, 'no explicit one-shot GO')
    require(go.get('repository') == REPOSITORY and go.get('branch') == BRANCH and
            go.get('preregistration_url') == PREREGISTRATION, 'wrong admission repository/issue/branch')
    require(go.get('admission_url') == pr_url and go.get('head') == live_pr['head']['sha'],
            'GO PR URL/head mismatch')
    require(type(go.get('tree')) is str and re.fullmatch('[0-9a-f]{40}', go['tree']) is not None,
            'exact diagnostic tree required')
    admitted_loader_pin(go.get('loader_pin'))
    ci_repository = object_at(live_ci, 'repository')
    require(ci_repository.get('full_name') == REPOSITORY and ci_repository.get('html_url') == WEB
            and ci_repository.get('url') == API and identity(object_at(ci_repository, 'owner')) == owner,
            'wrong CI repository')
    require(type(live_ci.get('id')) is int and live_ci['id'] == CI_RUN and
            live_ci.get('url') == API + '/actions/runs/' + str(CI_RUN) and
            live_ci.get('html_url') == WEB + '/actions/runs/' + str(CI_RUN), 'wrong CI run')
    require(live_ci.get('head_sha') == BASE_HEAD and live_ci.get('head_branch') == 'main' and
            live_ci.get('event') == 'push' and live_ci.get('path') == '.github/workflows/test.yml' and
            live_ci.get('status') == 'completed' and live_ci.get('conclusion') == 'success',
            'postmerge main CI prerequisite not verified')
    ci = {'run_id': CI_RUN, 'head': BASE_HEAD, 'status': 'completed', 'conclusion': 'success'}
    require(go.get('postmerge_ci') == ci, 'GO CI prerequisite mismatch')
    provenance = {'schema': 'worker36-authenticated-pr-admission-v1', 'repository': REPOSITORY,
                  'event_name': 'pull_request', 'action': 'edited', 'first_admission': True,
                  'pull_request_number': number, 'admission_url': pr_url,
                  'admission_sha256': sha(raw), 'body_sha256': sha(body.encode('utf-8')),
                  'previous_body_sha256': sha(previous.encode('utf-8')),
                  'head': go['head'], 'tree': go['tree'], 'branch': BRANCH,
                  'base_head': BASE_HEAD, 'sender': sender, 'author': owner, 'postmerge_ci': ci}
    return raw, provenance


def validate_interpreter():
    require(sys.flags.dont_write_bytecode == 1 and sys.flags.no_user_site == 1 and
            sys.flags.optimize == 0 and sys.flags.ignore_environment == 0 and
            sys.flags.isolated == 0 and sys.flags.no_site == 0, 'exact -B -s auth interpreter required')
    require({key: value for key, value in os.environ.items() if key.startswith('PYTHON')} ==
            {'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1'}, 'unclean Python auth environment')
    # The shared helper admits only the corresponding trusted toolcache library.
    # The observer checks actual mapped device/inode/path, stable file bytes and
    # the exact singleton LD_LIBRARY_PATH environment, rather than trusting it.
    try:
        return loader_identity()
    except LoaderIntegrityError as error:
        raise AdmissionError('unverified authentication loader: ' + str(error)) from error


def read_input(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'regular non-symlink auth input required')
    with path.open('rb') as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    require(len(raw) <= MAX_INPUT_BYTES, 'auth input byte cap')
    return raw, strict_json(raw)


def write_exclusive(path, raw):
    path = Path(path)
    require(path.parent.is_dir() and not path.parent.is_symlink(), 'durable auth output parent required')
    require(stat.S_IMODE(path.parent.stat().st_mode) & 0o022 == 0 and
            path.parent.stat().st_uid == os.getuid(), 'runner-owned auth output directory required')
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


INPUT_NAMES = ('event.json', 'pull-request.json', 'postmerge-ci.json', 'request-context.json')


def verified_context(context, provenance, workflow_run, workflow_attempt):
    require(type(workflow_run) is str and re.fullmatch('[1-9][0-9]*', workflow_run) is not None
            and workflow_attempt == '1', 'first workflow attempt required')
    require(type(context) is dict, 'request context required')
    path_names = ('runner_tool_cache', 'checkout_path', 'runner_temp', 'durable_root', 'attempt_path')
    paths = {}
    for name in path_names:
        value = context.get(name)
        require(type(value) is str and '\n' not in value and '\r' not in value,
                'invalid context path: ' + name)
        path = PurePosixPath(value)
        require(path.is_absolute() and '..' not in path.parts and str(path) == value,
                'absolute normalized context path required: ' + name)
        paths[name] = path
    durable = paths['runner_tool_cache'] / 'worker36-evidence' / ('run-' + workflow_run + '-attempt-1')
    attempt_id = 'worker36-' + workflow_run + '-1'
    require(paths['durable_root'] == durable and paths['attempt_path'] == durable / attempt_id,
            'durable attempt location mismatch')
    require(not durable.is_relative_to(paths['checkout_path']) and
            not durable.is_relative_to(paths['runner_temp']), 'durable root is ephemeral or inside checkout')
    expected = {
        'schema': 'worker36-github-request-context-v1', 'repository': REPOSITORY,
        'event_name': 'pull_request', 'workflow_run': workflow_run,
        'workflow_attempt': '1', 'server_url': 'https://github.com',
        'api_url': 'https://api.github.com', 'authentication': 'github-repository-read-token',
        'pull_request_request': {'method': 'GET', 'url': API + '/pulls/' + str(provenance['pull_request_number'])},
        'postmerge_ci_request': {'method': 'GET', 'url': API + '/actions/runs/' + str(CI_RUN)},
        'runner_name': 'bandido-alcatraz-ci', 'actor': OWNER,
        'run_url': WEB + '/actions/runs/' + workflow_run, 'attempt_id': attempt_id,
        **{name: str(path) for name, path in paths.items()}}
    require(context == expected, 'retained authenticated request context mismatch')
    return {'workflow_run': workflow_run, 'workflow_attempt': '1',
            'attempt_path': str(paths['attempt_path']), 'attempt_id': attempt_id,
            'durable_root': str(durable)}


def verify_provenance(provenance_path, admission_path, expected_admission_sha256):
    """Read-only retained-input reconciliation; caller pins provenance raw SHA.

    The original runner's request-context paths remain provenance when evidence
    is copied elsewhere. No original path is accessed and no network is used.
    """
    parent = Path(provenance_path).parent
    require(Path(admission_path).parent.resolve() == parent.resolve(), 'admission input directory mismatch')
    _, stored = read_input(provenance_path)
    require(type(stored) is dict, 'provenance object required')
    inputs = {name: read_input(parent / name) for name in INPUT_NAMES}
    raw, verified = extract_pr_admission(*(inputs[name][1] for name in INPUT_NAMES[:3]))
    raw_admission, _ = read_input(admission_path)
    require(raw == raw_admission and sha(raw) == expected_admission_sha256,
            'retained admission bytes/hash mismatch')
    verified.update(verified_context(inputs['request-context.json'][1], verified,
                                     stored.get('workflow_run'), stored.get('workflow_attempt')))
    verified['admission_input_hashes'] = {name: sha(value[0]) for name, value in inputs.items()}
    require(stored == verified, 'stored provenance does not match authenticated input reconciliation')
    return verified


def authenticate(args):
    observed_loader = validate_interpreter()
    require(re.fullmatch('[1-9][0-9]*', args.workflow_run) is not None and
            args.workflow_attempt == '1', 'first workflow attempt required')
    inputs = {'event.json': args.event, 'pull-request.json': args.pull_request,
              'postmerge-ci.json': args.ci, 'request-context.json': args.request_context}
    raw_inputs, values = {}, {}
    parent = Path(args.provenance).parent.resolve()
    require(Path(args.destination).parent.resolve() == parent, 'same retained auth directory required')
    for name, path in inputs.items():
        require(Path(path).name == name and Path(path).parent.resolve() == parent,
                'exact retained auth input location required')
        raw_inputs[name], values[name] = read_input(path)
    raw, provenance = extract_pr_admission(values['event.json'], values['pull-request.json'],
                                         values['postmerge-ci.json'])
    require(admitted_loader_pin(strict_json(raw)['loader_pin']) == loader_pin(observed_loader),
            'authentication loader differs from the external admitted pin')
    context = values['request-context.json']
    provenance.update(verified_context(context, provenance, args.workflow_run, args.workflow_attempt))
    require(parent == Path(context['durable_root']) / 'admission-inputs', 'wrong original durable auth location')
    for key, environment in (('runner_tool_cache', 'RUNNER_TOOL_CACHE'),
                             ('checkout_path', 'GITHUB_WORKSPACE'), ('runner_temp', 'RUNNER_TEMP')):
        require(os.environ.get(environment) is not None and
                Path(os.environ[environment]).resolve() == Path(context[key]), 'runner context path mismatch')
    require(os.environ.get('GITHUB_RUN_ID') == args.workflow_run and
            os.environ.get('GITHUB_RUN_ATTEMPT') == args.workflow_attempt and
            os.environ.get('GITHUB_EVENT_NAME') == 'pull_request' and
            os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and
            os.environ.get('GITHUB_ACTOR') == OWNER and
            os.environ.get('RUNNER_NAME') == 'bandido-alcatraz-ci', 'runner auth context mismatch')
    provenance['admission_input_hashes'] = {name: sha(data) for name, data in raw_inputs.items()}
    # A partial write/failure remains retained; the workflow does not measure
    # unless both exclusive outputs and this command complete successfully.
    write_exclusive(args.destination, raw)
    write_exclusive(args.provenance, canonical(provenance))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('authenticate')
    for name in ('event', 'pull-request', 'ci', 'request-context', 'destination', 'provenance',
                 'workflow-run', 'workflow-attempt'):
        command.add_argument('--' + name, required=True)
    return authenticate(parser.parse_args(argv))


if __name__ == '__main__':
    raise SystemExit(main())
