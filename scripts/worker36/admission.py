"""Authenticate retained GitHub inputs, never fetch, claim, import policy or run it.

The workflow supplies freshly authenticated API responses and the original event.
This gate authenticates the first PR-body edit; driver.read_admission separately
validates every source/runtime/resource/review field of the external full freeze.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import resource
import stat
import sys
import zipfile

if __name__ == '__main__' and not __package__:
    # Direct script invocation has only this sibling module directory on sys.path.
    from common import IntegrityError as LoaderIntegrityError, RUNTIME, loader_identity, loader_pin
else:
    from worker36.common import IntegrityError as LoaderIntegrityError, RUNTIME, loader_identity, loader_pin

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
METADATA_MEMORY = (512 * 1024 ** 2,) * 2
SHELL_LOADER_FIELDS = ('WORKER36_PYTHON', 'WORKER36_LOADER_DIRECTORY',
                       'WORKER36_LOADER_LIBRARY', 'WORKER36_LOADER_SHA256',
                       'WORKER36_LOADER_SIZE_BYTES')
REVIEW_ROLES = ('exhaustive', 'adversarial')
REVIEW_START = 'WORKER36_NATIVE_REVIEW_JSON'
REVIEW_END = 'END_WORKER36_NATIVE_REVIEW_JSON'
PREFLIGHT_WORKFLOW = '.github/workflows/worker36-runner-preflight.yml'
PREFLIGHT_MEMBERS = frozenset(('fresh-child-process.json', 'fresh-child.stderr', 'fresh-child.json',
    'fresh-child.stdout', 'launcher.txt', 'parent-runtime.json', 'parent.stderr', 'parent.stdout',
    'runner-preflight.json', 'shell-loader.json'))
PREFLIGHT_TEST_MODULES = ('test_worker36_core', 'test_worker36_supervision', 'test_worker36_transport',
    'test_worker36_admission_integration', 'test_worker36_cell_integration', 'test_worker36_driver_integration',
    'test_worker36_verify_integration', 'test_worker36_runner_preflight')
PREFLIGHT_ZERO = {'preparation_only': True, 'measurement_admitted': False,
    'candidate_evaluator_calls': 0, 'reference_evaluator_calls': 0,
    'measurement_fixture_constructions': 0, 'historical_source_imports': 0, 'games': 0}


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


def read_raw_input(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'regular non-symlink auth input required')
    with path.open('rb') as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    require(len(raw) <= MAX_INPUT_BYTES, 'auth input byte cap')
    return raw


def read_input(path):
    raw = read_raw_input(path)
    return raw, strict_json(raw)


def write_exclusive(path, raw):
    require(type(raw) is bytes and len(raw) <= MAX_INPUT_BYTES, 'bounded metadata output required')
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


PREREQUISITE_NAMES = ('review-exhaustive.json', 'review-adversarial.json',
                     'preflight-run.json', 'preflight-artifact.json', 'preflight.zip')
INPUT_NAMES = ('event.json', 'pull-request.json', 'postmerge-ci.json', 'request-context.json',
               *PREREQUISITE_NAMES)
NETWORK_INPUT_NAMES = ('pull-request.json', 'postmerge-ci.json', *PREREQUISITE_NAMES)


def hex_digest(value, label):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None,
            'invalid ' + label)


def prerequisite_descriptors(go, provenance):
    """Only these two attestation roles and this one named preflight are supported."""
    reviews = go.get('reviews')
    keys = {'role', 'native_reviewer_id', 'comment_id', 'url', 'body_sha256',
            'head', 'tree', 'verdict', 'handoff_sha256', 'report_sha256'}
    require(type(reviews) is list and len(reviews) == 2, 'exactly two native review attestations required')
    for role, review in zip(REVIEW_ROLES, reviews):
        require(type(review) is dict and set(review) == keys and review['role'] == role,
                'fixed native review descriptor schema/role required')
        number = positive_int(review['comment_id'], 'review comment ID')
        require(review['url'] == provenance['admission_url'] + '#issuecomment-' + str(number),
                'exact attestation comment URL required')
        require(type(review['native_reviewer_id']) is str and
                re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', review['native_reviewer_id']) is not None,
                'explicit native reviewer identity required')
        require(review['head'] == go['head'] and review['tree'] == go['tree'] and
                review['verdict'] == 'clean', 'exact-head clean review required')
        for key in ('body_sha256', 'handoff_sha256', 'report_sha256'):
            hex_digest(review[key], key)
    require(reviews[0]['comment_id'] != reviews[1]['comment_id'] and
            reviews[0]['native_reviewer_id'] != reviews[1]['native_reviewer_id'] and
            reviews[0]['handoff_sha256'] == reviews[1]['handoff_sha256'],
            'distinct native review identities and one reviewed handoff required')
    preflight = go.get('runner_preflight')
    required = {'schema', 'run_id', 'run_attempt', 'artifact_id', 'artifact_name',
                'artifact_sha256', 'artifact_size_bytes', 'report_sha256', 'report_size_bytes',
                'checked_file_sha256', 'focused_source_receipt'}
    require(type(preflight) is dict and set(preflight) == required and
            preflight['schema'] == 'worker36-preflight-binding-v1', 'explicit runner preflight binding required')
    for key in ('run_id', 'run_attempt', 'artifact_id', 'artifact_size_bytes', 'report_size_bytes'):
        positive_int(preflight[key], key)
    require(preflight['artifact_size_bytes'] <= MAX_INPUT_BYTES and preflight['report_size_bytes'] <= MAX_INPUT_BYTES,
            'bounded preflight evidence required')
    require(preflight['artifact_name'] == 'worker36-zero-evaluator-preflight-' +
            str(preflight['run_id']) + '-' + str(preflight['run_attempt']), 'exact preflight artifact name required')
    for key in ('artifact_sha256', 'report_sha256'):
        hex_digest(preflight[key], key)
    pins = preflight['checked_file_sha256']
    require(type(pins) is dict and 0 < len(pins) <= 256, 'bounded preflight source map required')
    for path, digest_value in pins.items():
        require(type(path) is str and PurePosixPath(path).as_posix() == path and
                not PurePosixPath(path).is_absolute() and '..' not in PurePosixPath(path).parts and
                path not in ('', '.'), 'relative preflight source path required')
        hex_digest(digest_value, 'preflight source hash')
    source = preflight['focused_source_receipt']
    require(type(source) is dict and set(source) == {'path', 'sha256', 'size_bytes'} and
            type(source['path']) is str and source['path'].startswith('experiments/synthetic-profile-overhead/') and
            source['path'].endswith('.json') and source['path'] in pins and
            source['sha256'] == go.get('stub_test_receipt_sha256') == pins[source['path']],
            'preflight focused source receipt binding required')
    positive_int(source['size_bytes'], 'focused source receipt size')
    require(source['size_bytes'] <= MAX_INPUT_BYTES, 'focused source receipt byte cap')
    diagnostics = go.get('diagnostic_files_sha256')
    require(type(diagnostics) is dict and bool(diagnostics) and
            all(pins.get(path) == value for path, value in diagnostics.items()),
            'preflight source map must bind the diagnostic files')
    return reviews, preflight


def prerequisite_requests(go, provenance):
    reviews, preflight = prerequisite_descriptors(go, provenance)
    urls = [API + '/issues/comments/' + str(review['comment_id']) for review in reviews]
    urls += [API + '/actions/runs/' + str(preflight['run_id']),
             API + '/actions/artifacts/' + str(preflight['artifact_id']),
             API + '/actions/artifacts/' + str(preflight['artifact_id']) + '/zip']
    return {name: {'method': 'GET', 'url': url} for name, url in zip(PREREQUISITE_NAMES, urls)}


def _review_attestation(raw, review, provenance):
    comment = strict_json(raw)
    require(type(comment) is dict and type(comment.get('id')) is int and
            comment['id'] == review['comment_id'] and comment.get('url') == API + '/issues/comments/' + str(review['comment_id']) and
            comment.get('html_url') == review['url'] and
            comment.get('issue_url') == API + '/issues/' + str(provenance['pull_request_number']),
            'authenticated review comment identity mismatch')
    require(identity(object_at(comment, 'user')) == provenance['author'], 'review attestation owner mismatch')
    body = bounded_body(comment.get('body'))
    require(sha(body.encode('utf-8')) == review['body_sha256'], 'review attestation body hash mismatch')
    prefix, suffix = REVIEW_START + '\n', REVIEW_END + '\n'
    require(body.startswith(prefix) and body.endswith(suffix) and
            body.count(REVIEW_START) == 2 and body.count(REVIEW_END) == 1,
            'one exact structured native review block required')
    record = strict_json(body[len(prefix):-len(suffix)])
    expected = {'schema': 'worker36-owner-attested-native-review-v1', 'repository': REPOSITORY,
        'pr_number': provenance['pull_request_number'], 'role': review['role'],
        'native_reviewer_id': review['native_reviewer_id'], 'head': review['head'], 'tree': review['tree'],
        'verdict': 'clean', 'complete_review': True, 'independent_review_attested': True,
        'actionable_findings': {'P0': 0, 'P1': 0, 'P2': 0, 'P3': 0},
        'handoff_sha256': review['handoff_sha256'], 'report_sha256': review['report_sha256']}
    require(canonical(record) == canonical(expected), 'native review attestation differs from exact clean binding')
    # This is an authenticated OWNER ATTESTATION of native independence. It is
    # not a claim that two different GitHub authors or cryptographic native
    # signatures have been observed.


def _preflight_report_from_zip(raw, descriptor):
    require(type(raw) is bytes and len(raw) == descriptor['artifact_size_bytes'] <= MAX_INPUT_BYTES and
            sha(raw) == descriptor['artifact_sha256'], 'preflight archive bytes/hash mismatch')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            names = [member.filename for member in members]
            require(len(names) == len(set(names)) and set(names) == PREFLIGHT_MEMBERS,
                    'exact safe preflight artifact members required')
            require(sum(member.file_size for member in members) <= MAX_INPUT_BYTES,
                    'preflight uncompressed evidence cap')
            for member in members:
                mode = stat.S_IFMT(member.external_attr >> 16)
                require(not member.is_dir() and mode in (0, stat.S_IFREG) and
                        not member.flag_bits & 1 and member.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) and
                        0 <= member.file_size <= MAX_INPUT_BYTES and 0 <= member.compress_size <= MAX_INPUT_BYTES,
                        'unsupported preflight ZIP member')
            components = {}; expanded = 0
            for member in members:
                with archive.open(member) as stream:
                    component = stream.read(MAX_INPUT_BYTES - expanded + 1)
                expanded += len(component)
                require(expanded <= MAX_INPUT_BYTES and len(component) == member.file_size,
                        'preflight actual expanded evidence cap/size')
                components[member.filename] = component
            report_raw = components['runner-preflight.json']
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, UnicodeError) as error:
        raise AdmissionError('invalid preflight ZIP') from error
    require(len(report_raw) == descriptor['report_size_bytes'] <= MAX_INPUT_BYTES and
            sha(report_raw) == descriptor['report_sha256'], 'preflight report bytes/hash mismatch')
    report = strict_json(report_raw)
    parent, child = object_at(report, 'parent'), object_at(report, 'fresh_child')
    require(components['parent-runtime.json'] == canonical(parent) and
            components['fresh-child.json'] == canonical(child) and
            components['shell-loader.json'] == canonical(object_at(parent, 'shell_loader')),
            'preflight component bytes disagree with the report')
    runtime = object_at(parent, 'runtime'); loader = object_at(runtime, 'loader')
    child_runtime = object_at(child, 'runtime')
    process = {**PREFLIGHT_ZERO, 'command': child_runtime.get('flags'), 'pid': child.get('pid'),
               'returncode': 0, 'timed_out': False}
    require(components['fresh-child-process.json'] == canonical(process) and
            child.get('parent_pid') == parent.get('pid'),
            'preflight fresh-child process proof mismatch')
    # stdout/stderr are retained diagnostic bytes, not additional success gates.
    # Fixed negative tests can emit warnings/sidecar records while the structured
    # preflight remains successful; every member's bytes/CRC were checked above.
    try:
        loader_pin(loader)
    except LoaderIntegrityError as error:
        raise AdmissionError('invalid preflight launcher loader') from error
    launcher = ('measurement_admitted=false\nevaluator_calls=0\nloader_setup_exit_code=0\n'
                + 'executable=' + loader['executable_path'] + '\n'
                + 'library=' + loader['library_path'] + '\n'
                + 'library_sha256=' + loader['library_sha256'] + '\n'
                + 'library_size_bytes=' + str(loader['library_size_bytes']) + '\nparent_exit_code=0\n')
    require(components['launcher.txt'] == launcher.encode('utf-8'), 'preflight successful launcher proof mismatch')
    return report


def _preflight_runtime(record, go, *, child):
    require(type(record) is dict, 'preflight process record required')
    for key, value in PREFLIGHT_ZERO.items():
        require(canonical(record.get(key)) == canonical(value), 'preflight process zero-call boundary')
    require(record.get('sanitized_environment') is True, 'unsanitized preflight process')
    capped = dict(go['inherited_limits']); capped['RLIMIT_AS'] = list(METADATA_MEMORY)
    require(canonical(record.get('inherited_limits')) == canonical(capped if child else go['inherited_limits']) and
            canonical(record.get('capped_limits')) == canonical(capped), 'preflight inherited/capped limits mismatch')
    for initial, field in ((True, 'initial_runtime'), (False, 'runtime')):
        runtime = object_at(record, field)
        require(all(runtime.get(key) == value for key, value in RUNTIME.items()), 'preflight pinned runtime mismatch')
        try:
            require(loader_pin(runtime.get('loader')) == go['loader_pin'], 'preflight loader pin mismatch')
        except LoaderIntegrityError as error:
            raise AdmissionError('invalid preflight mapped loader') from error
        flags = runtime.get('flags')
        executable = runtime['loader'].get('executable_path')
        require(runtime.get('executable') == executable and type(flags) is list and
                len(flags) == (7 if child else 10) and flags[:3] == [executable, '-B', '-s'],
                'preflight executable/flags mismatch')
        require((child and type(flags[3]) is str and flags[3].startswith('/') and
                 flags[3].endswith('/scripts/worker36/runner_preflight.py') and
                 flags[4:6] == ['--child', '--report']) or
                (not child and flags[3:5] == ['scripts/worker36/runner_preflight.py', '--report'] and
                 flags[6:] == ['--expected-head', go['head'], '--expected-tree', go['tree']]),
                'preflight command identity mismatch')
        expected_flags = {'dont_write_bytecode': 1, 'no_user_site': 1, 'ignore_environment': 0,
                          'isolated': 0, 'optimize': 0, 'no_site': 0}
        require(canonical(runtime.get('effective_flags')) == canonical(expected_flags) and
                runtime.get('python_environment') == {'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1'} and
                runtime.get('gc_enabled') is True and canonical(runtime.get('gc_threshold')) == canonical([700, 10, 10]) and
                canonical(runtime.get('address_space')) == canonical(
                    go['inherited_limits']['RLIMIT_AS'] if initial and not child else list(METADATA_MEMORY)),
                'preflight flags/environment/GC/memory evidence mismatch')
    positive_int(record.get('pid'), 'preflight process PID')
    positive_int(record.get('parent_pid'), 'preflight parent PID')
    require(record['initial_runtime']['loader'] == record['runtime']['loader'], 'preflight loader changed in process')
    shell = {key: record['runtime']['loader'][key] for key in
             ('executable_path', 'library_directory', 'library_path', 'library_sha256', 'library_size_bytes')}
    require(record.get('shell_loader') == shell, 'preflight shell/runtime loader mismatch')
    return record['runtime']


def validate_prerequisites(go, provenance, proof_bytes):
    """Replay retained authenticated proof bytes; no networking or policy import."""
    reviews, preflight = prerequisite_descriptors(go, provenance)
    require(type(proof_bytes) is dict and set(proof_bytes) == set(PREREQUISITE_NAMES) and
            all(type(raw) is bytes and len(raw) <= MAX_INPUT_BYTES for raw in proof_bytes.values()),
            'all bounded authenticated prerequisite inputs required')
    for review, name in zip(reviews, PREREQUISITE_NAMES[:2]):
        _review_attestation(proof_bytes[name], review, provenance)
    run = strict_json(proof_bytes['preflight-run.json'])
    require(type(run) is dict and type(run.get('id')) is int and run['id'] == preflight['run_id'] and
            type(run.get('run_attempt')) is int and run['run_attempt'] == preflight['run_attempt'] and
            run.get('url') == API + '/actions/runs/' + str(preflight['run_id']) and
            run.get('html_url') == WEB + '/actions/runs/' + str(preflight['run_id']) and
            run.get('path') == PREFLIGHT_WORKFLOW and run.get('event') == 'pull_request' and
            run.get('status') == 'completed' and run.get('conclusion') == 'success' and
            run.get('head_branch') == BRANCH and run.get('head_sha') == go['head'],
            'successful exact-head preflight run required')
    repo = object_at(run, 'repository'); head_repo = object_at(run, 'head_repository')
    require(identity(object_at(run, 'actor')) == provenance['author'] and
            identity(object_at(run, 'triggering_actor')) == provenance['author'],
            'preflight run actor/triggering actor mismatch')
    repository_id = positive_int(repo.get('id'), 'preflight repository ID')
    require(repo.get('full_name') == head_repo.get('full_name') == REPOSITORY and
            head_repo.get('id') == repository_id and repo.get('url') == head_repo.get('url') == API and
            identity(object_at(repo, 'owner')) == provenance['author'], 'preflight run repository mismatch')
    commit = object_at(run, 'head_commit')
    require(commit.get('id') == go['head'] and commit.get('tree_id') == go['tree'], 'preflight head/tree mismatch')
    pulls = run.get('pull_requests')
    require(type(pulls) is list and len(pulls) == 1 and type(pulls[0]) is dict and
            pulls[0].get('number') == provenance['pull_request_number'] and
            pulls[0].get('url') == API + '/pulls/' + str(provenance['pull_request_number']), 'preflight PR binding mismatch')
    for key, ref, commit_sha in (('head', BRANCH, go['head']), ('base', 'main', BASE_HEAD)):
        endpoint = object_at(pulls[0], key); pr_repo = object_at(endpoint, 'repo')
        require(endpoint.get('ref') == ref and endpoint.get('sha') == commit_sha and
                pr_repo.get('id') == repository_id and pr_repo.get('url') == API, 'preflight PR head/base mismatch')
    artifact = strict_json(proof_bytes['preflight-artifact.json'])
    require(type(artifact) is dict and type(artifact.get('id')) is int and artifact['id'] == preflight['artifact_id'] and
            artifact.get('name') == preflight['artifact_name'] and artifact.get('expired') is False and
            artifact.get('url') == API + '/actions/artifacts/' + str(preflight['artifact_id']) and
            artifact.get('archive_download_url') == API + '/actions/artifacts/' + str(preflight['artifact_id']) + '/zip' and
            artifact.get('digest') == 'sha256:' + preflight['artifact_sha256'] and
            type(artifact.get('size_in_bytes')) is int and artifact['size_in_bytes'] == preflight['artifact_size_bytes'],
            'preflight artifact identity/hash/size mismatch')
    binding = object_at(artifact, 'workflow_run')
    require(binding.get('id') == preflight['run_id'] and binding.get('head_sha') == go['head'] and
            binding.get('head_branch') == BRANCH and binding.get('repository_id') ==
            binding.get('head_repository_id') == repository_id, 'preflight artifact run mismatch')
    report = _preflight_report_from_zip(proof_bytes['preflight.zip'], preflight)
    require(type(report) is dict and report.get('schema') == 'worker36-runner-preflight-v1' and
            report.get('success') is True and report.get('status') == 'preparation_passed' and
            report.get('repository') == REPOSITORY and report.get('runner_name') == 'bandido-alcatraz-ci' and
            report.get('diagnostic_head') == go['head'] and report.get('diagnostic_tree') == go['tree'] and
            report.get('workflow_run') == str(preflight['run_id']) and
            report.get('workflow_attempt') == str(preflight['run_attempt']) and report.get('event_name') == 'pull_request',
            'successful exact-head preflight report required')
    for key, value in PREFLIGHT_ZERO.items():
        require(canonical(report.get(key)) == canonical(value), 'preflight report zero-call boundary')
    require(report.get('loader_pin') == go['loader_pin'] and
            report.get('checked_sources_unchanged_during_run') is True and
            report.get('checked_file_sha256') == preflight['checked_file_sha256'] and
            report.get('focused_source_receipt') == preflight['focused_source_receipt'],
            'preflight report loader/source proof mismatch')
    focused = object_at(report, 'focused_tests')
    require(focused.get('success') is True and type(focused.get('tests_run')) is int and focused['tests_run'] > 0 and
            all(type(focused.get(key)) is int and focused[key] == 0 for key in ('failures', 'errors', 'skipped')) and
            focused.get('test_modules') == list(PREFLIGHT_TEST_MODULES), 'preflight focused test gate failed')
    for key, value in PREFLIGHT_ZERO.items():
        require(canonical(focused.get(key)) == canonical(value), 'focused test zero-call boundary')
    require(go.get('runtime') == RUNTIME and type(go.get('inherited_limits')) is dict and
            go['inherited_limits'].get('RLIMIT_AS') == [-1, -1], 'preflight runtime/initial limits binding required')
    parent = object_at(report, 'parent'); child = object_at(report, 'fresh_child')
    parent_runtime = _preflight_runtime(parent, go, child=False)
    child_runtime = _preflight_runtime(child, go, child=True)
    require(child['parent_pid'] == parent['pid'] and child['pid'] != parent['pid'], 'preflight fresh child identity mismatch')
    shared = ('implementation', 'version', 'executable_sha256', 'executable', 'effective_flags',
              'python_environment', 'gc_enabled', 'gc_threshold', 'address_space', 'loader')
    require(all(canonical(parent_runtime[key]) == canonical(child_runtime[key]) for key in shared),
            'preflight parent/fresh child runtime mismatch')
    return {'reviews': reviews, 'runner_preflight': preflight,
            'prerequisite_requests': prerequisite_requests(go, provenance)}


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


def request_context_from_environment(environ):
    """Serialize only the existing fixed request schema, never ambient secrets."""
    def required(name):
        value = environ.get(name)
        require(type(value) is str and 0 < len(value) <= 4096 and
                all(ord(char) >= 32 and ord(char) != 127 for char in value),
                'missing or invalid metadata environment: ' + name)
        return value
    for name, expected in {'GITHUB_REPOSITORY': REPOSITORY, 'GITHUB_EVENT_NAME': 'pull_request',
                           'GITHUB_ACTOR': OWNER, 'GITHUB_RUN_ATTEMPT': '1',
                           'GITHUB_SERVER_URL': 'https://github.com',
                           'GITHUB_API_URL': 'https://api.github.com',
                           'RUNNER_NAME': 'bandido-alcatraz-ci'}.items():
        require(required(name) == expected, 'wrong metadata environment: ' + name)
    run, number = required('GITHUB_RUN_ID'), required('PR_NUMBER')
    require(re.fullmatch('[1-9][0-9]{0,19}', run) is not None and
            re.fullmatch('[1-9][0-9]{0,19}', number) is not None, 'invalid run or PR identity')
    paths = {key: required(env) for key, env in (
        ('runner_tool_cache', 'RUNNER_TOOL_CACHE'), ('checkout_path', 'GITHUB_WORKSPACE'),
        ('runner_temp', 'RUNNER_TEMP'), ('durable_root', 'DURABLE'), ('attempt_path', 'ATTEMPT'))}
    require(required('AUTH') == paths['durable_root'] + '/admission-inputs', 'wrong retained metadata directory')
    context = {'schema': 'worker36-github-request-context-v1', 'repository': REPOSITORY,
        'event_name': 'pull_request', 'workflow_run': run, 'workflow_attempt': '1',
        'server_url': 'https://github.com', 'api_url': 'https://api.github.com',
        'authentication': 'github-repository-read-token',
        'pull_request_request': {'method': 'GET', 'url': API + '/pulls/' + number},
        'postmerge_ci_request': {'method': 'GET', 'url': API + '/actions/runs/' + str(CI_RUN)},
        'runner_name': 'bandido-alcatraz-ci', 'actor': OWNER,
        'run_url': WEB + '/actions/runs/' + run, 'attempt_id': 'worker36-' + run + '-1', **paths}
    verified_context(context, {'pull_request_number': int(number)}, run, '1')
    return context


def create_request_context(args):
    validate_interpreter()
    # Preserve the original shell realpath semantics for these existing paths.
    environ = dict(os.environ)
    for name in ('RUNNER_TOOL_CACHE', 'GITHUB_WORKSPACE', 'RUNNER_TEMP'):
        require(type(environ.get(name)) is str and environ[name].startswith('/'),
                'absolute metadata source path required: ' + name)
        environ[name] = str(Path(environ[name]).resolve(strict=True))
    context = request_context_from_environment(environ)
    expected = Path(context['durable_root']) / 'admission-inputs' / 'request-context.json'
    require(Path(args.destination).absolute() == expected, 'exact retained request-context output required')
    write_exclusive(args.destination, canonical(context))
    return 0


def authentication_handoff(raw, provenance, observed_loader, *, expected_head, expected_tree,
                           admission_sha256, shell_loader):
    """Validate the former shell metadata checks before exporting fixed fields."""
    require(type(raw) is bytes and len(raw) <= MAX_GO_BYTES and type(provenance) is dict,
            'bounded authenticated handoff inputs required')
    go = strict_json(raw)
    require(type(go) is dict and type(expected_head) is str and type(expected_tree) is str and
            re.fullmatch('[a-f0-9]{40}', expected_head) is not None and
            re.fullmatch('[a-f0-9]{40}', expected_tree) is not None, 'exact handoff head/tree required')
    require(go.get('head') == provenance.get('head') == expected_head, 'authenticated handoff head mismatch')
    require(go.get('tree') == provenance.get('tree') == expected_tree, 'authenticated handoff tree mismatch')
    require(type(admission_sha256) is str and re.fullmatch('[a-f0-9]{64}', admission_sha256) is not None and
            sha(raw) == provenance.get('admission_sha256') == admission_sha256,
            'authenticated handoff admission digest mismatch')
    pin = admitted_loader_pin(go.get('loader_pin'))
    try:
        require(loader_pin(observed_loader) == pin, 'authenticated handoff mapped loader mismatch')
    except LoaderIntegrityError as error:
        raise AdmissionError('invalid handoff loader identity: ' + str(error)) from error
    require(type(shell_loader) is dict and set(shell_loader) == set(SHELL_LOADER_FIELDS),
            'exact shell loader metadata required')
    require(shell_loader['WORKER36_PYTHON'] == observed_loader['executable_path'] and
            shell_loader['WORKER36_LOADER_DIRECTORY'] == observed_loader['library_directory'] and
            shell_loader['WORKER36_LOADER_LIBRARY'] == observed_loader['library_path'],
            'authenticated handoff loader path mismatch')
    require(shell_loader['WORKER36_LOADER_SHA256'] == pin['library_sha256'],
            'authenticated handoff library digest mismatch')
    require(type(shell_loader['WORKER36_LOADER_SIZE_BYTES']) is str and
            re.fullmatch('[1-9][0-9]{0,14}', shell_loader['WORKER36_LOADER_SIZE_BYTES']) is not None and
            shell_loader['WORKER36_LOADER_SIZE_BYTES'] == str(pin['library_size_bytes']),
            'authenticated handoff library size mismatch')
    values = {'ADMISSION_SHA256': admission_sha256,
        'ADMISSION_PROVENANCE_SHA256': sha(canonical(provenance)), 'EXPECTED_TREE': expected_tree,
        'WORKER36_PRESERVE_EXECUTABLE': observed_loader['executable_path'],
        'WORKER36_PRESERVE_LIBRARY_DIRECTORY': observed_loader['library_directory'],
        'WORKER36_PRESERVE_LIBRARY_SHA256': pin['library_sha256'],
        'WORKER36_PRESERVE_LIBRARY_SIZE_BYTES': str(pin['library_size_bytes'])}
    for value in values.values():
        require(type(value) is str and 0 < len(value) <= 4096 and
                all(ord(char) >= 32 and ord(char) != 127 for char in value),
                'invalid fixed-format workflow environment value')
    return ''.join(name + '=' + value + '\n' for name, value in values.items()).encode('utf-8')


def verify_provenance(provenance_path, admission_path, expected_admission_sha256):
    """Read-only retained-input reconciliation; caller pins provenance raw SHA.

    The original runner's request-context paths remain provenance when evidence
    is copied elsewhere. No original path is accessed and no network is used.
    """
    parent = Path(provenance_path).parent
    require(Path(admission_path).parent.resolve() == parent.resolve(), 'admission input directory mismatch')
    _, stored = read_input(provenance_path)
    require(type(stored) is dict, 'provenance object required')
    inputs = {name: read_raw_input(parent / name) for name in INPUT_NAMES}
    raw, verified = extract_pr_admission(*(strict_json(inputs[name]) for name in INPUT_NAMES[:3]))
    raw_admission, _ = read_input(admission_path)
    require(raw == raw_admission and sha(raw) == expected_admission_sha256,
            'retained admission bytes/hash mismatch')
    verified.update(verified_context(strict_json(inputs['request-context.json']), verified,
                                     stored.get('workflow_run'), stored.get('workflow_attempt')))
    verified.update(validate_prerequisites(strict_json(raw), verified,
                                          {name: inputs[name] for name in PREREQUISITE_NAMES}))
    verified['admission_input_hashes'] = {name: sha(value) for name, value in inputs.items()}
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
    require(Path(args.handoff).absolute() == parent / 'authenticated-handoff.env',
            'exact retained authentication handoff location required')
    for name, path in inputs.items():
        require(Path(path).name == name and Path(path).parent.resolve() == parent,
                'exact retained auth input location required')
        raw_inputs[name], values[name] = read_input(path)
    for name in PREREQUISITE_NAMES:
        raw_inputs[name] = read_raw_input(parent / name)
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
    provenance.update(validate_prerequisites(strict_json(raw), provenance,
                                            {name: raw_inputs[name] for name in PREREQUISITE_NAMES}))
    provenance['admission_input_hashes'] = {name: sha(data) for name, data in raw_inputs.items()}
    handoff = authentication_handoff(raw, provenance, observed_loader,
        expected_head=args.expected_head, expected_tree=args.expected_tree, admission_sha256=sha(raw),
        shell_loader={name: os.environ.get(name) for name in SHELL_LOADER_FIELDS})
    # A partial write/failure remains retained; the workflow does not measure
    # unless both exclusive outputs and this command complete successfully.
    write_exclusive(args.destination, raw)
    write_exclusive(args.provenance, canonical(provenance))
    write_exclusive(args.handoff, handoff)
    return 0


def evidence_references(args):
    """Produce four numeric read targets only; this cannot grant admission."""
    observed = validate_interpreter()
    raw, provenance = extract_pr_admission(*(read_input(path)[1] for path in (args.event, args.pull_request, args.ci)))
    go = strict_json(raw)
    require(go['head'] == args.expected_head and go['tree'] == args.expected_tree and
            go['loader_pin'] == loader_pin(observed), 'evidence discovery head/tree/loader mismatch')
    reviews, preflight = prerequisite_descriptors(go, provenance)
    output = Path(args.destination).absolute()
    require(os.environ.get('AUTH') and output == Path(os.environ['AUTH']) / 'evidence-refs.txt',
            'fixed durable evidence-reference output required')
    values = [review['comment_id'] for review in reviews] + [preflight['run_id'], preflight['artifact_id']]
    write_exclusive(output, ''.join(str(value) + '\n' for value in values).encode('ascii'))
    return 0


def retain_network_input(args):
    """Bound and retain only enumerated authentication responses, never execute."""
    validate_interpreter()
    directory = Path(args.directory).absolute()
    require(os.environ.get('AUTH') and directory == Path(os.environ['AUTH']) and args.name in NETWORK_INPUT_NAMES,
            'fixed durable authentication input required')
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    require(len(raw) <= MAX_INPUT_BYTES, 'authenticated network response byte cap')
    if args.name != 'preflight.zip':
        strict_json(raw)
    write_exclusive(directory / args.name, raw)
    return 0


def main(argv=None):
    inherited = resource.getrlimit(resource.RLIMIT_AS)
    require(inherited in ((resource.RLIM_INFINITY,) * 2, METADATA_MEMORY),
            'unexpected metadata address-space limit')
    if inherited != METADATA_MEMORY:
        resource.setrlimit(resource.RLIMIT_AS, METADATA_MEMORY)
    require(resource.getrlimit(resource.RLIMIT_AS) == METADATA_MEMORY, 'exact512MiB metadata memory cap')
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    context_command = commands.add_parser('request-context')
    context_command.add_argument('--destination', required=True)
    references = commands.add_parser('evidence-refs')
    for name in ('event', 'pull-request', 'ci', 'destination', 'expected-head', 'expected-tree'):
        references.add_argument('--' + name, required=True)
    retaining = commands.add_parser('retain-input')
    retaining.add_argument('--directory', required=True)
    retaining.add_argument('--name', required=True, choices=NETWORK_INPUT_NAMES)
    command = commands.add_parser('authenticate')
    for name in ('event', 'pull-request', 'ci', 'request-context', 'destination', 'provenance',
                 'workflow-run', 'workflow-attempt', 'expected-head', 'expected-tree', 'handoff'):
        command.add_argument('--' + name, required=True)
    args = parser.parse_args(argv)
    if args.command == 'request-context':
        return create_request_context(args)
    if args.command == 'evidence-refs':
        return evidence_references(args)
    if args.command == 'retain-input':
        return retain_network_input(args)
    return authenticate(args)


if __name__ == '__main__':
    raise SystemExit(main())
