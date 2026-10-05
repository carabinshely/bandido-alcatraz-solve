"""Eighty-four frozen, metadata-only Worker37 engineering cases.

The declared case IDs are the entire suite. There is no discovery, fuzzing,
parameterization, scientific import, measurement fixture, game, or live HTTP.
Python cases call production main with narrow environmental observations mocked.
Shell cases execute the factored production bodies using fixed inert command stubs.
These fixtures are invented; their IDs, hashes, reviews and report prove nothing
about an authenticated runner, a historical result, or timeout kill behavior.
"""
from __future__ import annotations

import ast
import base64
import builtins
import copy
from contextlib import ExitStack, redirect_stdout, redirect_stderr
import hashlib
import http.client
import importlib.abc
import importlib.util
import io
import json
import os
from pathlib import Path
import resource
import socket
import ssl
import stat
import subprocess
import sys
import tempfile
import textwrap
import types
import unittest
from unittest.mock import patch
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'scripts/worker37_bootstrap.py'
LAUNCHER_PATH = ROOT / 'scripts/worker37-bootstrap.sh'
WORKFLOW_PATH = ROOT / '.github/workflows/worker37-bootstrap-readiness.yml'
SHARED_SHELL_PATH = ROOT / 'scripts/worker_bootstrap_shared.sh'
SHARED_PYTHON_PATH = ROOT / 'scripts/worker_bootstrap_shared.py'
MEMORY_BYTES = 536870912
TOKEN = 'SENTINEL_SECRET_42'
REPOSITORY = 'carabinshely/bandido-alcatraz-solve'
API = 'https://api.github.com/repos/' + REPOSITORY
STORAGE = 'https://worker37fixture.blob.core.windows.net/a?signature=fixture'
SOURCE_BYTES = b'# invented source metadata only\n'
EVIDENCE_DIRECTORY = os.environ.get('WORKER37_LITERAL_EVIDENCE_DIRECTORY')
EVIDENCE_BYTES = 0
CURRENT_CASE_ID = None
REQUEST_PATHS = (
    '/pulls/101', '/actions/runs/102', '/issues/comments/103',
    '/issues/comments/104', '/actions/runs/105', '/actions/artifacts/106',
    '/actions/artifacts/106/zip',
)
RETAINED_NAMES = (
    'pull-request.json', 'postmerge-ci.json', 'review-exhaustive.json',
    'review-adversarial.json', 'preflight-run.json',
    'preflight-artifact.json', 'preflight.zip',
)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def retain_case_file(name, raw):
    global EVIDENCE_BYTES
    if not EVIDENCE_DIRECTORY:
        return
    if CURRENT_CASE_ID is None:
        raise AssertionError('case evidence requires an explicit case ID')
    if EVIDENCE_BYTES + len(raw) > 8388608:
        raise AssertionError('fixed 8MiB case evidence reserve exhausted')
    directory = Path(EVIDENCE_DIRECTORY)/CURRENT_CASE_ID
    directory.mkdir(mode=0o700,exist_ok=True)
    with open(directory/name,'xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    EVIDENCE_BYTES += len(raw)


def retain_python_prefix(s, output, stdout, stderr):
    s.output=(stdout.getvalue()+stderr.getvalue()).encode()
    s.retained={path.name:path.read_bytes() for path in output.iterdir() if path.is_file()}
    for name,raw in s.retained.items():
        retain_case_file(name,raw)
    retain_case_file('captured-output.txt',s.output)
    request_evidence=[{'ordinal':index+1,'method':r['method'],'received_bytes':r['received'],
                       'authenticated':r['headers'].get('authorization')=='Bearer '+TOKEN}
                      for index,r in enumerate(s.requests)]
    retain_case_file('mock-request-observations.json',canonical(request_evidence))


class DenyScienceImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('bandido_alcatraz', 'worker36', 'scripts.worker36')):
            raise AssertionError('forbidden scientific or historical import: ' + fullname)
        return None


def denied_socket(*args, **kwargs):
    raise AssertionError('live sockets are prohibited in this literal suite')


class LiteralResponse:
    """A fixed decoded HTTP body; chunked framing is truthfully represented."""
    def __init__(self, body, status=200, headers=None):
        self.body = body
        self.status = status
        self.code = status
        self.headers = dict(headers if headers is not None else
                            {'Content-Length': str(len(body))})
        self.offset = 0
        self.closed = False
        self.close_unconfirmed = False

    def read(self, amount=-1):
        if amount < 0:
            raise AssertionError('production attempted an unbounded HTTP read')
        chunk = self.body[self.offset:self.offset + amount]
        self.offset += len(chunk)
        return chunk

    def getcode(self):
        return self.status

    def close(self):
        self.closed = not self.close_unconfirmed

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class LiteralIncompleteResponse(LiteralResponse):
    """Actual IncompleteRead carries observed decoded bytes after a fixed prefix."""
    def __init__(self,prefix,partial,status=200,headers=None):
        super().__init__(prefix+partial,status,
                         headers if headers is not None else {'Transfer-Encoding':'chunked'})
        self.prefix=prefix
        self.partial=partial
        self.incomplete_raised=False

    def read(self,amount=-1):
        if amount < 0:
            raise AssertionError('unbounded incomplete-response read')
        if self.offset < len(self.prefix):
            raw=self.prefix[self.offset:self.offset+amount]
            self.offset+=len(raw)
            return raw
        if self.incomplete_raised:
            raise AssertionError('read retried after actual IncompleteRead')
        if len(self.partial)>amount:
            raise AssertionError('literal partial exceeds the requested decoded-byte allowance')
        self.incomplete_raised=True
        self.offset+=len(self.partial)
        raise http.client.IncompleteRead(self.partial,expected=1)


class LiteralScenario:
    """One baseline copy with the single mutation in its named test method."""
    def __init__(self):
        self.descriptor = copy.deepcopy(FROZEN_DESCRIPTOR)
        self.zip_bytes = base64.b64decode(FROZEN_ZIPS['baseline'])
        self.token = TOKEN
        self.flags = types.SimpleNamespace(optimize=0, ignore_environment=0,
            isolated=0, no_site=0, no_user_site=1, dont_write_bytecode=1)
        self.gc_threshold = (700, 10, 10)
        self.inherited_limits = copy.deepcopy(self.descriptor['runtime']['inherited_limits'])
        self.setrlimit_failure = False
        self.occupied_profile = None
        self.mapped_inode = 11
        self.restoration_failure = False
        self.readback_mismatch = False
        self.readback_after_requests = 7
        self.readback_memory_failure = False
        self.restoration_limit_failure = False
        self.source_cap_failure = False
        self.source_identity_failure = False
        self.descriptor_close_operation = None
        self.injected_close_failures = 0
        self.event_hash_override = None
        self.extra_numeric_literal = None
        self.short_write = False
        self.directory_fsync_failure = False
        self.tls_failure = False
        self.expired_after_third = False
        self.extra_environment = {}
        self.response_replacements = {}
        self.review_head_override = None
        self.new_head_override = None
        self.new_body_override = None
        self.prior_head_override = None
        self.prior_association_override = None
        self.omit_prior_association = False
        self.fixed_historical_pin_override = None
        self.artifact_run_id_override = None
        self.base_conclusion = 'success'
        self.requests = []
        self.openers = []
        self.observed_getrlimit = []
        self.observed_setrlimit = []
        self.output = b''
        self.retained = {}
        self.result = None
        self.exit_code = None
        self.closed_responses = []

    def repin_zip(self, case_id):
        self.zip_bytes = base64.b64decode(FROZEN_ZIPS[case_id])
        self.descriptor['historical_fixture']['zip_sha256'] = sha(self.zip_bytes)
        self.descriptor['historical_fixture']['zip_size_bytes'] = len(self.zip_bytes)

    def inputs(self):
        descriptor_bytes = canonical(self.descriptor).rstrip(b'\n')
        body = ('WORKER37_ENGINEERING_ADMISSION_JSON\n' + descriptor_bytes.decode() +
                '\nEND_WORKER37_ENGINEERING_ADMISSION_JSON\n' +
                'WORKER37_ENGINEERING_ADMISSION_SHA256 ' + sha(descriptor_bytes))
        pr = {'number':101, 'state':'open', 'merged':False,
              'user':{'login':'carabinshely'},
              'head':{'sha':'1'*40, 'ref':'research/worker37-bootstrap-readiness',
                      'repo':{'full_name':REPOSITORY}},
              'base':{'sha':'5'*40, 'ref':'main', 'repo':{'full_name':REPOSITORY}},
              'body':body}
        event = {'action':'edited', 'number':101, 'repository':{'full_name':REPOSITORY},
                 'sender':{'login':'carabinshely'},
                 'changes':{'body':{'from':'Prior ordinary body'}},
                 'pull_request':copy.deepcopy(pr)}
        if self.new_head_override is not None:
            pr['head']['sha'] = self.new_head_override
        if self.new_body_override is not None:
            pr['body'] = self.new_body_override
        ci = {'id':102, 'run_attempt':1, 'status':'completed',
              'conclusion':self.base_conclusion, 'head_sha':'5'*40,
              'event':'push', 'head_branch':'main', 'repository':{'full_name':REPOSITORY}}
        exhaustive = {'id':103, 'user':{'login':'carabinshely'},
                      'body':'INVENTED exhaustive review head '+'1'*40+' tree '+'2'*40+'\n',
                      'issue_url':API+'/issues/101'}
        adversarial = {'id':104, 'user':{'login':'carabinshely'},
                      'body':'INVENTED adversarial review head '+
                          (self.review_head_override or '1'*40)+' tree '+'2'*40+'\n',
                      'issue_url':API+'/issues/101'}
        prior = {'id':105, 'run_attempt':1, 'status':'completed', 'conclusion':'success',
                 'head_sha':self.prior_head_override or '3'*40, 'event':'pull_request',
                 'repository':{'full_name':REPOSITORY},
                 'pull_requests':[{'number':40, 'head':{'sha':'3'*40}}]}
        if self.prior_association_override is not None:
            prior['pull_requests'] = copy.deepcopy(self.prior_association_override)
        if self.omit_prior_association:
            prior.pop('pull_requests')
        artifact = {'id':106, 'name':self.descriptor['historical_fixture']['artifact_name'],
                    'expired':False,
                    'size_in_bytes':self.descriptor['historical_fixture']['zip_size_bytes'],
                    'digest':'sha256:'+self.descriptor['historical_fixture']['zip_sha256'],
                    'workflow_run':{'id':105, 'head_sha':'3'*40}}
        if self.artifact_run_id_override is not None:
            artifact['workflow_run']['id'] = self.artifact_run_id_override
        responses = [LiteralResponse(canonical(item)) for item in
                     (pr, ci, exhaustive, adversarial, prior, artifact)]
        if self.extra_numeric_literal is not None:
            pr_raw=canonical(pr)
            responses[0]=LiteralResponse(pr_raw[:-2]+b',"literal_number":'+self.extra_numeric_literal+b'}\n')
        responses.append(LiteralResponse(self.zip_bytes))
        if self.restoration_failure:
            responses[0].close_unconfirmed = True
        for index, response in self.response_replacements.items():
            if index == len(responses):
                responses.append(response)
            else:
                responses[index] = response
        return canonical(event), responses
FROZEN_DESCRIPTOR = {'schema': 'worker37-engineering-admission-v1', 'preparation_only': True, 'measurement_admitted': False, 'allocation_id': 'worker37-bootstrap-readiness-01', 'repository': 'carabinshely/bandido-alcatraz-solve', 'actor': 'carabinshely', 'runner': 'bandido-alcatraz-ci', 'pr_number': 101, 'branch': 'research/worker37-bootstrap-readiness', 'head': '1111111111111111111111111111111111111111', 'tree': '2222222222222222222222222222222222222222', 'base': {'head': '5555555555555555555555555555555555555555', 'tree': '6666666666666666666666666666666666666666', 'run_id': 102}, 'preregistration': {'protocol_sha256': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'record_sha256': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'}, 'reviews': [{'role': 'exhaustive', 'comment_id': 103, 'author': 'carabinshely', 'head': '1111111111111111111111111111111111111111', 'tree': '2222222222222222222222222222222222222222', 'body_sha256': '2e7f18f1c54718920b0d1ab133e8fe5f119adb831f0b0b2d979ce4ab6a8ce159'}, {'role': 'adversarial', 'comment_id': 104, 'author': 'carabinshely', 'head': '1111111111111111111111111111111111111111', 'tree': '2222222222222222222222222222222222222222', 'body_sha256': '0ac6b70d3a1d046c8870df82d69beaee50077cc5d55255a98fc24c629b4f51bd'}], 'historical_fixture': {'run_id': 105, 'run_attempt': 1, 'artifact_id': 106, 'artifact_name': 'invented-worker37-prior-fixture-105-1', 'pr_number': 40, 'head': '3333333333333333333333333333333333333333', 'tree': '4444444444444444444444444444444444444444', 'zip_size_bytes': 1476, 'zip_sha256': 'b4c08e63908a88c498786928e01d9327e39324c161a7458ab2091bf241e0f8e0', 'report_size_bytes': 346, 'report_sha256': '2a8e8f23634ab9690e466affdac3d7b92546107fa971caf86f15047a7f3b329c'}, 'runtime': {'executable_sha256': 'a15ccdaf07655a8667a3687b13171486c9a265d92273ba3ad820fbb64d2cfecc', 'library_sha256': 'ba4450817186fbe1e3c477f6aefeee7c353cba3593cc9950382ad9d1f5e62896', 'library_size_bytes': 23041360, 'inherited_limits': {'RLIMIT_AS': [536870912, 536870912], 'RLIMIT_CORE': [-1, -1], 'RLIMIT_CPU': [-1, -1], 'RLIMIT_DATA': [-1, -1], 'RLIMIT_FSIZE': [-1, -1], 'RLIMIT_MEMLOCK': [-1, -1], 'RLIMIT_MSGQUEUE': [-1, -1], 'RLIMIT_NICE': [-1, -1], 'RLIMIT_NOFILE': [-1, -1], 'RLIMIT_OFILE': [-1, -1], 'RLIMIT_NPROC': [-1, -1], 'RLIMIT_RSS': [-1, -1], 'RLIMIT_RTPRIO': [-1, -1], 'RLIMIT_RTTIME': [-1, -1], 'RLIMIT_SIGPENDING': [-1, -1], 'RLIMIT_STACK': [-1, -1]}}, 'budgets': {'memory_bytes': 536870912, 'scope_seconds': 120, 'socket_seconds': 10, 'response_body_bytes': 16777216, 'input_bytes': 2097152, 'expanded_zip_bytes': 2097152, 'evidence_bytes': 31457280, 'terminal_reserve_bytes': 1048576}, 'source_files': {'scripts/worker37_bootstrap.py': {'sha256': '2c629f2a38abc202b5889474fd320962884b41acc3a7d1ed6ed7d062984fb223', 'size_bytes': 32}}}
FROZEN_SOURCE = b'# invented source metadata only\n'
FROZEN_ZIPS = {'baseline': 'UEsDBBQAAAAIAAAAIVAvxxOuLgAAACwAAAAYAAAAZnJlc2gtY2hpbGQtcHJvY2Vzcy5qc29uq1bKySxJLUrMUbJSyswrS80rSU2JLyjKT04tLo7Py49PrUhNLi3JzM9TquUCAFBLAwQUAAAACAAAACFQAAAAAAIAAAAAAAAAEgAAAGZyZXNoLWNoaWxkLnN0ZGVycgMAUEsDBBQAAAAIAAAAIVB60yQlHwAAAB0AAAAQAAAAZnJlc2gtY2hpbGQuanNvbqtWysksSS1KzFGyUsrMK0vNK0lNiU/OyMxJUarlAgBQSwMEFAAAAAgAAAAhUAAAAAACAAAAAAAAABIAAABmcmVzaC1jaGlsZC5zdGRvdXQDAFBLAwQUAAAACAAAACFQS+Q9yBkAAAAXAAAADAAAAGxhdW5jaGVyLnR4dPP0C3P1C3F1ifd1DXF0cQxxjPf384nkAgBQSwMEFAAAAAgAAAAhUNNWcis1AAAASwAAABMAAABwYXJlbnQtcnVudGltZS5qc29uq1bKySxJLUrMUbJSyswrS80rSU2JL0gsAjKUdJSKM1JzcuJz8hNTUouUrKqxqYVK1tZyAQBQSwMEFAAAAAgAAAAhUAAAAAACAAAAAAAAAA0AAABwYXJlbnQuc3RkZXJyAwBQSwMEFAAAAAgAAAAhUAAAAAACAAAAAAAAAA0AAABwYXJlbnQuc3Rkb3V0AwBQSwMEFAAAAAgAAAAhUMPeCoedAAAAWgEAABUAAABydW5uZXItcHJlZmxpZ2h0Lmpzb26NTksOgjAQ3XuMWUPUqBsv0wztYBvHlkwrBAl3d0hYsCHhLd9/AhfwFVMuwRpP6OAJt4OAahsuQqTh+0FouBXK3lgfWFcn4FBIkLUjxJ5iIbdqcwUdijI7rlWsIHtiNpzQkex4V3HWTqEu5VCSjGqwKNiEuDSM5wajCy7VyBaL4K/OiXvSgSHJu+U0GCyFPp0eguuWlm9cqMsD5tMfUEsDBBQAAAAIAAAAIVAOEBF5IAAAAB4AAAARAAAAc2hlbGwtbG9hZGVyLmpzb26rVsrJLEktSsxRslLKzCtLzStJTYnPyU9MSS1SquUCAFBLAQIUAxQAAAAIAAAAIVAvxxOuLgAAACwAAAAYAAAAAAAAAAAAAACAgQAAAABmcmVzaC1jaGlsZC1wcm9jZXNzLmpzb25QSwECFAMUAAAACAAAACFQAAAAAAIAAAAAAAAAEgAAAAAAAAAAAAAAgIFkAAAAZnJlc2gtY2hpbGQuc3RkZXJyUEsBAhQDFAAAAAgAAAAhUHrTJCUfAAAAHQAAABAAAAAAAAAAAAAAAICBlgAAAGZyZXNoLWNoaWxkLmpzb25QSwECFAMUAAAACAAAACFQAAAAAAIAAAAAAAAAEgAAAAAAAAAAAAAAgIHjAAAAZnJlc2gtY2hpbGQuc3Rkb3V0UEsBAhQDFAAAAAgAAAAhUEvkPcgZAAAAFwAAAAwAAAAAAAAAAAAAAICBFQEAAGxhdW5jaGVyLnR4dFBLAQIUAxQAAAAIAAAAIVDTVnIrNQAAAEsAAAATAAAAAAAAAAAAAACAgVgBAABwYXJlbnQtcnVudGltZS5qc29uUEsBAhQDFAAAAAgAAAAhUAAAAAACAAAAAAAAAA0AAAAAAAAAAAAAAICBvgEAAHBhcmVudC5zdGRlcnJQSwECFAMUAAAACAAAACFQAAAAAAIAAAAAAAAADQAAAAAAAAAAAAAAgIHrAQAAcGFyZW50LnN0ZG91dFBLAQIUAxQAAAAIAAAAIVDD3gqHnQAAAFoBAAAVAAAAAAAAAAAAAACAgRgCAABydW5uZXItcHJlZmxpZ2h0Lmpzb25QSwECFAMUAAAACAAAACFQDhAReSAAAAAeAAAAEQAAAAAAAAAAAAAAgIHoAgAAc2hlbGwtbG9hZGVyLmpzb25QSwUGAAAAAAoACgB3AgAANwMAAAAA', 'T052': 'UEsDBBQAAAAIAAAAIVAvxxOuLgAAACwAAAAYAAAAZ3Jlc2gtY2hpbGQtcHJvY2Vzcy5qc29uq1bKySxJLUrMUbJSyswrS80rSU2JLyjKT04tLo7Py49PrUhNLi3JzM9TquUCAFBLAwQUAAAACAAAACFQAAAAAAIAAAAAAAAAEgAAAGZyZXNoLWNoaWxkLnN0ZGVycgMAUEsDBBQAAAAIAAAAIVB60yQlHwAAAB0AAAAQAAAAZnJlc2gtY2hpbGQuanNvbqtWysksSS1KzFGyUsrMK0vNK0lNiU/OyMxJUarlAgBQSwMEFAAAAAgAAAAhUAAAAAACAAAAAAAAABIAAABmcmVzaC1jaGlsZC5zdGRvdXQDAFBLAwQUAAAACAAAACFQS+Q9yBkAAAAXAAAADAAAAGxhdW5jaGVyLnR4dPP0C3P1C3F1ifd1DXF0cQxxjPf384nkAgBQSwMEFAAAAAgAAAAhUNNWcis1AAAASwAAABMAAABwYXJlbnQtcnVudGltZS5qc29uq1bKySxJLUrMUbJSyswrS80rSU2JL0gsAjKUdJSKM1JzcuJz8hNTUouUrKqxqYVK1tZyAQBQSwMEFAAAAAgAAAAhUAAAAAACAAAAAAAAAA0AAABwYXJlbnQuc3RkZXJyAwBQSwMEFAAAAAgAAAAhUAAAAAACAAAAAAAAAA0AAABwYXJlbnQuc3Rkb3V0AwBQSwMEFAAAAAgAAAAhUMPeCoedAAAAWgEAABUAAABydW5uZXItcHJlZmxpZ2h0Lmpzb26NTksOgjAQ3XuMWUPUqBsv0wztYBvHlkwrBAl3d0hYsCHhLd9/AhfwFVMuwRpP6OAJt4OAahsuQqTh+0FouBXK3lgfWFcn4FBIkLUjxJ5iIbdqcwUdijI7rlWsIHtiNpzQkex4V3HWTqEu5VCSjGqwKNiEuDSM5wajCy7VyBaL4K/OiXvSgSHJu+U0GCyFPp0eguuWlm9cqMsD5tMfUEsDBBQAAAAIAAAAIVAOEBF5IAAAAB4AAAARAAAAc2hlbGwtbG9hZGVyLmpzb26rVsrJLEktSsxRslLKzCtLzStJTYnPyU9MSS1SquUCAFBLAQIUAxQAAAAIAAAAIVAvxxOuLgAAACwAAAAYAAAAAAAAAAAAAACAgQAAAABmcmVzaC1jaGlsZC1wcm9jZXNzLmpzb25QSwECFAMUAAAACAAAACFQAAAAAAIAAAAAAAAAEgAAAAAAAAAAAAAAgIFkAAAAZnJlc2gtY2hpbGQuc3RkZXJyUEsBAhQDFAAAAAgAAAAhUHrTJCUfAAAAHQAAABAAAAAAAAAAAAAAAICBlgAAAGZyZXNoLWNoaWxkLmpzb25QSwECFAMUAAAACAAAACFQAAAAAAIAAAAAAAAAEgAAAAAAAAAAAAAAgIHjAAAAZnJlc2gtY2hpbGQuc3Rkb3V0UEsBAhQDFAAAAAgAAAAhUEvkPcgZAAAAFwAAAAwAAAAAAAAAAAAAAICBFQEAAGxhdW5jaGVyLnR4dFBLAQIUAxQAAAAIAAAAIVDTVnIrNQAAAEsAAAATAAAAAAAAAAAAAACAgVgBAABwYXJlbnQtcnVudGltZS5qc29uUEsBAhQDFAAAAAgAAAAhUAAAAAACAAAAAAAAAA0AAAAAAAAAAAAAAICBvgEAAHBhcmVudC5zdGRlcnJQSwECFAMUAAAACAAAACFQAAAAAAIAAAAAAAAADQAAAAAAAAAAAAAAgIHrAQAAcGFyZW50LnN0ZG91dFBLAQIUAxQAAAAIAAAAIVDD3gqHnQAAAFoBAAAVAAAAAAAAAAAAAACAgRgCAABydW5uZXItcHJlZmxpZ2h0Lmpzb25QSwECFAMUAAAACAAAACFQDhAReSAAAAAeAAAAEQAAAAAAAAAAAAAAgIHoAgAAc2hlbGwtbG9hZGVyLmpzb25QSwUGAAAAAAoACgB3AgAANwMAAAAA', 'T053': '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', 'T054': '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', 'T055': 'UEsDBBQAAAAIAAAAIVAvxxOuLgAAACwAAAAYAAAAZnJlc2gtY2hpbGQtcHJvY2Vzcy5qc29uq1bKySxJLUrMUbJSyswrS80rSU2JLyjKT04tLo7Py49PrUhNLi3JzM9TquUCAFBLAwQUAAAACAAAACFQAAAAAAIAAAAAAAAAEgAAAGZyZXNoLWNoaWxkLnN0ZGVycgMAUEsDBBQAAAAIAAAAIVB60yQlHwAAAB0AAAAQAAAAZnJlc2gtY2hpbGQuanNvbqtWysksSS1KzFGyUsrMK0vNK0lNiU/OyMxJUarlAgBQSwMEFAAAAAgAAAAhUAAAAAACAAAAAAAAABIAAABmcmVzaC1jaGlsZC5zdGRvdXQDAFBLAwQUAAAACAAAACFQQXedPxsIAAD1/R8ADAAAAGxhdW5jaGVyLnR4dO3BsQ2AMAwAsJ2vIjUDEoQlQmXq/19wRTfbcwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA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', 'T056': 'UEsDBBQAAAAIAAAAIVAvxxOuLgAAACwAAAAYAAAAZnJlc2gtY2hpbGQtcHJvY2Vzcy5qc29uq1bKySxJLUrMUbJSyswrS80rSU2JLyjKT04tLo7Py49PrUhNLi3JzM9TquUCAFBLAwQUAAAACAAAACFQAAAAAAIAAAAAAAAAEgAAAGZyZXNoLWNoaWxkLnN0ZGVycgMAUEsDBBQAAAAIAAAAIVB60yQlHwAAAB0AAAAQAAAAZnJlc2gtY2hpbGQuanNvbqtWysksSS1KzFGyUsrMK0vNK0lNiU/OyMxJUarlAgBQSwMEFAAAAAgAAAAhUAAAAAACAAAAAAAAABIAAABmcmVzaC1jaGlsZC5zdGRvdXQDAFBLAwQUAAAACAAAACFQS+Q9yBkAAAAXAAAADAAAAGxhdW5jaGVyLnR4dPP0C3P1C3F1ifd1DXF0cQxxjPf384nkAgBQSwMEFAAAAAgAAAAhUCULEOg7AAAAUwAAABMAAABwYXJlbnQtcnVudGltZS5qc29uq1bKySxJLUrMUbJSyswrS80rSU2JT85IzEsH0gWJRUABJR2l4ozUnJz4nPzElNQiJatqbHqgkrW1XABQSwMEFAAAAAgAAAAhUAAAAAACAAAAAAAAAA0AAABwYXJlbnQuc3RkZXJyAwBQSwMEFAAAAAgAAAAhUAAAAAACAAAAAAAAAA0AAABwYXJlbnQuc3Rkb3V0AwBQSwMEFAAAAAgAAAAhUMPeCoedAAAAWgEAABUAAABydW5uZXItcHJlZmxpZ2h0Lmpzb26NTksOgjAQ3XuMWUPUqBsv0wztYBvHlkwrBAl3d0hYsCHhLd9/AhfwFVMuwRpP6OAJt4OAahsuQqTh+0FouBXK3lgfWFcn4FBIkLUjxJ5iIbdqcwUdijI7rlWsIHtiNpzQkex4V3HWTqEu5VCSjGqwKNiEuDSM5wajCy7VyBaL4K/OiXvSgSHJu+U0GCyFPp0eguuWlm9cqMsD5tMfUEsDBBQAAAAIAAAAIVAOEBF5IAAAAB4AAAARAAAAc2hlbGwtbG9hZGVyLmpzb26rVsrJLEktSsxRslLKzCtLzStJTYnPyU9MSS1SquUCAFBLAQIUAxQAAAAIAAAAIVAvxxOuLgAAACwAAAAYAAAAAAAAAAAAAACAgQAAAABmcmVzaC1jaGlsZC1wcm9jZXNzLmpzb25QSwECFAMUAAAACAAAACFQAAAAAAIAAAAAAAAAEgAAAAAAAAAAAAAAgIFkAAAAZnJlc2gtY2hpbGQuc3RkZXJyUEsBAhQDFAAAAAgAAAAhUHrTJCUfAAAAHQAAABAAAAAAAAAAAAAAAICBlgAAAGZyZXNoLWNoaWxkLmpzb25QSwECFAMUAAAACAAAACFQAAAAAAIAAAAAAAAAEgAAAAAAAAAAAAAAgIHjAAAAZnJlc2gtY2hpbGQuc3Rkb3V0UEsBAhQDFAAAAAgAAAAhUEvkPcgZAAAAFwAAAAwAAAAAAAAAAAAAAICBFQEAAGxhdW5jaGVyLnR4dFBLAQIUAxQAAAAIAAAAIVAlCxDoOwAAAFMAAAATAAAAAAAAAAAAAACAgVgBAABwYXJlbnQtcnVudGltZS5qc29uUEsBAhQDFAAAAAgAAAAhUAAAAAACAAAAAAAAAA0AAAAAAAAAAAAAAICBxAEAAHBhcmVudC5zdGRlcnJQSwECFAMUAAAACAAAACFQAAAAAAIAAAAAAAAADQAAAAAAAAAAAAAAgIHxAQAAcGFyZW50LnN0ZG91dFBLAQIUAxQAAAAIAAAAIVDD3gqHnQAAAFoBAAAVAAAAAAAAAAAAAACAgR4CAABydW5uZXItcHJlZmxpZ2h0Lmpzb25QSwECFAMUAAAACAAAACFQDhAReSAAAAAeAAAAEQAAAAAAAAAAAAAAgIHuAgAAc2hlbGwtbG9hZGVyLmpzb25QSwUGAAAAAAoACgB3AgAAPQMAAAAA'}

EXECUTABLE_BYTES = b'INVENTED_PINNED_EXECUTABLE_BYTES\n'
LIBRARY_BYTES = b'\0' * 23041360


def module_proxy(module):
    return types.SimpleNamespace(**vars(module))


def run_python(s):
    """Run actual main; only HTTP/OS/runtime observations are injected."""
    with tempfile.TemporaryDirectory(prefix='worker37-literal-python-') as temporary:
        root = Path(temporary)
        source = root / 'source'
        (source/'scripts').mkdir(parents=True)
        (source/'scripts/worker37_bootstrap.py').write_bytes(SOURCE_BYTES)
        output = root/'output'
        output.mkdir(mode=0o700)
        event_raw, responses = s.inputs()
        event = output/'event.json'
        event.write_bytes(event_raw)
        event_stat = event.stat()
        (root/'literal.netrc').write_text('machine api.github.com login invented password INVENTED_NETRC\n')
        (root/'literal.cookies').write_text('INVENTED_COOKIE_JAR\n')
        cache = root/'cache'
        cache.mkdir()
        executable = str(cache/'Python/3.11.16/x64/bin/python3.11')
        library = str(cache/'Python/3.11.16/x64/lib/libpython3.11.so.1.0')
        environment = {
            'GITHUB_REPOSITORY':REPOSITORY, 'GITHUB_ACTOR':'carabinshely',
            'GITHUB_TRIGGERING_ACTOR':'carabinshely', 'RUNNER_NAME':'bandido-alcatraz-ci',
            'GITHUB_SERVER_URL':'https://github.com', 'GITHUB_API_URL':'https://api.github.com',
            'GITHUB_EVENT_NAME':'pull_request', 'GITHUB_RUN_ATTEMPT':'1', 'GITHUB_RUN_ID':'107',
            'WORKER37_ALLOCATION_ID':'worker37-bootstrap-readiness-01',
            'WORKER37_PR_NUMBER':'101', 'WORKER37_RUN_ID':'107', 'WORKER37_HEAD':'1'*40,
            'WORKER37_TREE':'2'*40, 'WORKER37_BRANCH':s.descriptor['branch'],
            'WORKER37_EVENT_SHA256':s.event_hash_override or sha(event_raw),
            'WORKER37_EVENT_STAT':f'{event_stat.st_dev}:{event_stat.st_ino}:{event_stat.st_size}:{int(event_stat.st_mtime)}',
            'WORKER37_EVENT_FSYNC_CONFIRMED':'1',
            'WORKER37_JOB':'bootstrap', 'RUNNER_TOOL_CACHE':str(cache),
            'WORKER37_EXECUTABLE':executable, 'WORKER37_LIBRARY':library,
            'WORKER37_EXECUTABLE_STAT':f'1:10:{len(EXECUTABLE_BYTES)}:1',
            'WORKER37_LIBRARY_STAT':'1:11:23041360:1',
            'LD_LIBRARY_PATH':str(Path(library).parent),
            'PYTHONHASHSEED':'0', 'PYTHONDONTWRITEBYTECODE':'1',
            'HOME':str(root),
        }
        if s.token is not None:
            environment['GH_TOKEN'] = s.token
        environment.update(s.extra_environment)
        if 'NETRC' in s.extra_environment:
            environment['NETRC'] = str(root/'literal.netrc')
            environment['COOKIE_JAR'] = str(root/'literal.cookies')
        finder = DenyScienceImports()
        captured_stdout, captured_stderr = io.StringIO(), io.StringIO()
        original_open = os.open
        original_read = os.read
        original_write = os.write
        original_close = os.close
        original_stat = os.stat
        original_fstat = os.fstat
        original_fsync = os.fsync
        original_readlink = os.readlink
        original_builtin_open = builtins.open
        original_build_opener = urllib.request.build_opener
        original_sha256 = hashlib.sha256
        fd_paths = {}
        fd_roles = {}
        source_fstat_count = 0
        runtime_offsets = {}
        runtime_data = {executable:EXECUTABLE_BYTES,library:LIBRARY_BYTES}
        runtime_fds = {-10010:executable,-10011:library}
        runtime_info = {
            executable:types.SimpleNamespace(st_mode=stat.S_IFREG|0o700,st_dev=1,st_ino=10,
                st_size=len(EXECUTABLE_BYTES),st_mtime=1,st_mtime_ns=1000000000),
            library:types.SimpleNamespace(st_mode=stat.S_IFREG|0o600,st_dev=1,st_ino=11,
                st_size=23041360,st_mtime=1,st_mtime_ns=1000000000),
        }
        changed_readback = False
        failed_dirsync = False
        last_written = None
        actual_limit_pairs = {getattr(resource,name):tuple(value)
                              for name,value in s.inherited_limits.items()}

        def os_open(path, flags, mode=0o777, *, dir_fd=None):
            name = os.fsdecode(path)
            if name in runtime_data:
                fd = -10010 if name==executable else -10011
                runtime_offsets[fd] = 0
                return fd
            fd = original_open(path,flags,mode,dir_fd=dir_fd)
            absolute = str(Path(fd_paths[dir_fd])/name) if dir_fd is not None else name
            fd_paths[fd] = absolute
            if absolute == str(source/'scripts/worker37_bootstrap.py'):
                fd_roles[fd] = 'source_read'
            elif name == 'event.json' and dir_fd is not None:
                fd_roles[fd] = 'event_snapshot'
            elif name == 'pull-request.json' and flags & os.O_WRONLY:
                fd_roles[fd] = 'api_write'
            return fd

        def os_read(fd, amount):
            nonlocal changed_readback
            if fd in runtime_fds:
                data = runtime_data[runtime_fds[fd]]
                offset = runtime_offsets[fd]
                part = data[offset:offset+amount]
                runtime_offsets[fd] += len(part)
                return part
            if (s.readback_memory_failure and not changed_readback and len(s.requests)==7
                    and fd_paths.get(fd)==str(output/'event.json')):
                changed_readback=True
                raise MemoryError('INVENTED first P09 read memory failure')
            raw = original_read(fd,amount)
            if (s.readback_mismatch and not changed_readback and len(s.requests)==s.readback_after_requests
                    and fd_paths.get(fd)==str(output/'event.json') and raw):
                changed_readback=True
                return bytes([raw[0]^1])+raw[1:]
            return raw

        def os_write(fd, raw):
            nonlocal last_written
            last_written=fd_paths.get(fd)
            if s.short_write and last_written==str(output/'pull-request.json'):
                original_write(fd,raw[:3])
                raise OSError('INVENTED three-byte persistence failure')
            return original_write(fd,raw)

        def os_close(fd):
            if fd in runtime_fds:
                return
            role=fd_roles.pop(fd,None)
            fd_paths.pop(fd,None)
            result=original_close(fd)
            if role==s.descriptor_close_operation and role is not None and not s.injected_close_failures:
                s.injected_close_failures+=1
                raise OSError('INVENTED descriptor close failure after safe fixture close')
            return result

        def os_stat(path, *args, **kwargs):
            return runtime_info.get(os.fsdecode(path)) or original_stat(path,*args,**kwargs)

        def os_fstat(fd):
            nonlocal source_fstat_count
            if fd in runtime_fds:
                return runtime_info[runtime_fds[fd]]
            value=original_fstat(fd)
            if fd_roles.get(fd)=='source_read':
                source_fstat_count+=1
                if s.source_cap_failure or (s.source_identity_failure and source_fstat_count==2):
                    return types.SimpleNamespace(st_mode=value.st_mode,st_dev=value.st_dev,
                        st_ino=value.st_ino+(1 if s.source_identity_failure else 0),
                        st_size=2097153 if s.source_cap_failure else value.st_size,
                        st_mtime=value.st_mtime,st_mtime_ns=value.st_mtime_ns,
                        st_uid=value.st_uid,st_gid=value.st_gid)
            return value

        def os_fsync(fd):
            nonlocal failed_dirsync
            if (s.directory_fsync_failure and not failed_dirsync
                    and last_written==str(output/'pull-request.json')
                    and fd_paths.get(fd)==str(output)):
                failed_dirsync=True
                raise OSError('INVENTED directory fsync failure')
            return original_fsync(fd)

        def readlink(path, *args, **kwargs):
            if path=='/proc/self/exe':
                return executable
            return original_readlink(path,*args,**kwargs)

        def read_maps(path,*args,**kwargs):
            if str(path)=='/proc/self/maps':
                return io.BytesIO((f'1000-2000 r-xp 00000000 00:01 10 {executable}\n'
                    f'3000-4000 r-xp 00000000 00:01 {s.mapped_inode} {library}\n').encode())
            return original_builtin_open(path,*args,**kwargs)

        def hash_bytes(raw=b'', *args, **kwargs):
            if raw==EXECUTABLE_BYTES:
                return types.SimpleNamespace(hexdigest=lambda:FROZEN_DESCRIPTOR['runtime']['executable_sha256'])
            if len(raw)==23041360 and raw==LIBRARY_BYTES:
                return types.SimpleNamespace(hexdigest=lambda:FROZEN_DESCRIPTOR['runtime']['library_sha256'])
            return original_sha256(raw,*args,**kwargs)

        def getrlimit(kind):
            s.observed_getrlimit.append(kind)
            if s.restoration_limit_failure and s.requests and kind==resource.RLIMIT_AS:
                return (MEMORY_BYTES-1,MEMORY_BYTES)
            return actual_limit_pairs[kind]

        def setrlimit(kind,value):
            s.observed_setrlimit.append((kind,tuple(value)))
            if s.setrlimit_failure:
                raise OSError('INVENTED setrlimit failure')
            actual_limit_pairs[kind]=tuple(value)

        def monotonic():
            return 120.0 if s.expired_after_third and len(s.requests)>=3 else 0.0

        def http_open(opener, request, timeout=None):
            index=len(s.requests)
            record={'url':request.full_url,'method':request.get_method(),
                    'headers':{key.lower():value for key,value in request.header_items()},
                    'timeout':timeout,'received':0,'body':b''}
            s.requests.append(record)
            if s.tls_failure:
                raise ssl.SSLCertVerificationError('INVENTED_CERTIFICATE_SENTINEL')
            if index>=len(responses):
                raise AssertionError('unplanned extra HTTP request')
            response=responses[index]
            record['body']=response.body
            read=response.read
            def counted_read(amount):
                try:
                    raw=read(amount)
                except http.client.IncompleteRead as error:
                    record['received']+=len(error.partial)
                    raise
                record['received']+=len(raw)
                return raw
            response.read=counted_read
            return response

        def build_opener(*handlers):
            opener=original_build_opener(*handlers)
            s.openers.append(opener)
            return opener

        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ,environment,clear=True))
            stack.enter_context(patch.object(socket.socket,'connect',denied_socket))
            stack.enter_context(patch.object(socket,'create_connection',denied_socket))
            stack.enter_context(patch.object(socket,'getaddrinfo',denied_socket))
            stack.enter_context(patch.object(urllib.request.OpenerDirector,'open',http_open))
            stack.enter_context(patch.object(urllib.request,'build_opener',build_opener))
            sys.meta_path.insert(0,finder)
            stack.callback(sys.meta_path.remove,finder)
            stack.enter_context(patch.object(sys, 'path', [str(ROOT / 'scripts'), *sys.path]))
            spec=importlib.util.spec_from_file_location('worker37_literal_actual_module',MODULE_PATH)
            module=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            stack.enter_context(patch.object(module,'FIXED_BASE',copy.deepcopy(s.descriptor['base'])))
            fixed_historical = (s.fixed_historical_pin_override if s.fixed_historical_pin_override is not None
                                else s.descriptor['historical_fixture'])
            stack.enter_context(patch.object(module,'FIXED_HISTORICAL',copy.deepcopy(fixed_historical)))
            stack.enter_context(patch.object(module,'REQUIRED_SOURCE_PATHS',('scripts/worker37_bootstrap.py',)))
            os_proxy=module_proxy(os)
            os_proxy.open,os_proxy.read,os_proxy.write,os_proxy.close=os_open,os_read,os_write,os_close
            os_proxy.stat,os_proxy.fstat,os_proxy.fsync,os_proxy.readlink=os_stat,os_fstat,os_fsync,readlink
            sys_proxy=module_proxy(sys)
            sys_proxy.flags,sys_proxy.version_info,sys_proxy.executable=s.flags,(3,11,16),executable
            sys_proxy.getprofile=lambda:s.occupied_profile
            sys_proxy.gettrace=lambda:None
            # Observe a fixed clean leaf module inventory without importing science.
            sys_proxy.modules={name:types.ModuleType(name) for name in
                ('builtins','sys','os','json','hashlib','resource','urllib.request','zipfile')}
            resource_proxy=module_proxy(resource)
            resource_proxy.getrlimit,resource_proxy.setrlimit=getrlimit,setrlimit
            gc_proxy=module_proxy(module.gc)
            gc_proxy.isenabled=lambda:True
            gc_proxy.get_threshold=lambda:s.gc_threshold
            signal_proxy=module_proxy(module.signal)
            signal_proxy.getitimer=lambda timer:(0.0,0.0)
            threading_proxy=module_proxy(module.threading)
            threading_proxy.active_count=lambda:1
            time_proxy=module_proxy(module.time)
            time_proxy.monotonic=monotonic
            hash_proxy=module_proxy(hashlib)
            hash_proxy.sha256=hash_bytes
            ssl_proxy=module_proxy(ssl)
            ssl_proxy.create_default_context=lambda:types.SimpleNamespace(check_hostname=True,verify_mode=ssl.CERT_REQUIRED)
            for name,value in (('os',os_proxy),('sys',sys_proxy),('resource',resource_proxy),
                ('gc',gc_proxy),('signal',signal_proxy),('threading',threading_proxy),
                ('time',time_proxy),('hashlib',hash_proxy),('ssl',ssl_proxy),('open',read_maps)):
                stack.enter_context(patch.object(module,name,value,create=True))
                if name in ('os','sys','resource','gc','signal','threading','hashlib','open'):
                    stack.enter_context(patch.object(module.bootstrap_shared,name,value,create=True))
            try:
                with redirect_stdout(captured_stdout),redirect_stderr(captured_stderr):
                    s.exit_code=module.main(['--event',str(event),'--output',str(output),'--source',str(source)])
            finally:
                retain_python_prefix(s,output,captured_stdout,captured_stderr)
        s.output=(captured_stdout.getvalue()+captured_stderr.getvalue()).encode()
        s.retained={path.name:path.read_bytes() for path in output.iterdir() if path.is_file()}
        if 'result.json' in s.retained:
            s.result=json.loads(s.retained['result.json'])
        return s

BASH_CASE_OBSERVATIONS = []


def workflow_block(phase):
    raw = WORKFLOW_PATH.read_text()
    begin = '          # WORKER37_'+phase+'_BEGIN\n'
    end = '          # WORKER37_'+phase+'_END'
    if raw.count(begin)!=1 or raw.count(end)!=1:
        raise AssertionError('frozen workflow phase boundary missing or duplicated')
    body=raw.split(begin,1)[1].split(end,1)[0]
    if any(line and not line.startswith('          ') for line in body.splitlines()):
        raise AssertionError('workflow block indentation changed')
    return ''.join(line[10:] if line.strip() else line for line in body.splitlines(keepends=True))


def run_bash(case_id, *, entry, overrides=None):
    with tempfile.TemporaryDirectory(prefix='worker37-literal-bash-') as temporary:
        root=Path(temporary)
        commands=root/'commands'
        commands.mkdir()
        source=root/'workspace'
        (source/'scripts').mkdir(parents=True)
        launcher=source/'scripts/worker37-bootstrap.sh'
        launcher.write_bytes(LAUNCHER_PATH.read_bytes())
        (source/'scripts/worker37_bootstrap.py').write_bytes(MODULE_PATH.read_bytes())
        (source/'scripts/worker_bootstrap_shared.sh').write_bytes(SHARED_SHELL_PATH.read_bytes())
        (source/'scripts/worker_bootstrap_shared.py').write_bytes(SHARED_PYTHON_PATH.read_bytes())
        temporary_dir=root/'runner-temp'
        temporary_dir.mkdir()
        cache=root/'cache'
        if case_id=='T008':
            real_cache=root/'cache-target'
            real_cache.mkdir()
            cache.symlink_to(real_cache,target_is_directory=True)
        else:
            cache.mkdir()
        runtime=cache/'Python/3.11.16/x64'
        (runtime/'bin').mkdir(parents=True)
        (runtime/'lib').mkdir()
        pinned=runtime/'bin/python3.11'
        pinned.write_text(FROZEN_STUB)
        pinned.chmod(0o700)
        (runtime/'lib/libpython3.11.so.1.0').write_bytes(b'INVENTED_LIBRARY_BYTES_NOT_LOADABLE\n')
        durable=cache/'worker37-bootstrap-readiness'
        allocations=durable/'allocations'
        allocation=allocations/'worker37-bootstrap-readiness-01'
        attempt=allocation/'run-107-attempt-1'
        attempt.mkdir(parents=True,mode=0o700)
        durable.chmod(0o700)
        allocations.chmod(0o700)
        allocation.chmod(0o700)
        reservation=allocation/'reservation.txt'
        if case_id=='T013':
            reservation.write_bytes(b'INVENTED_PREVIOUS_RUN_108_RESERVATION\n')
        initial_reservation=reservation.read_bytes() if reservation.exists() else None
        event=root/'event.json'
        event.write_bytes(b'{}\n')
        log=root/'commands.bin'
        violation=root/'violations.txt'
        library_hashed=root/'library-hashed'
        names=('realpath','readlink','stat','id','mkdir','cat','sync','sha256sum','git','timeout')
        for name in names:
            if case_id=='T007' and name=='timeout':
                continue
            path=commands/name
            path.write_text(FROZEN_STUB)
            path.chmod(0o700)
        environment={
            'PATH':str(commands), 'LC_ALL':'C',
            'GITHUB_REPOSITORY':REPOSITORY, 'GITHUB_ACTOR':'carabinshely',
            'GITHUB_TRIGGERING_ACTOR':'carabinshely', 'WORKER37_SENDER':'carabinshely',
            'WORKER37_PR_AUTHOR':'carabinshely', 'RUNNER_NAME':'bandido-alcatraz-ci',
            'GITHUB_SERVER_URL':'https://github.com', 'GITHUB_API_URL':'https://api.github.com',
            'GITHUB_EVENT_NAME':'pull_request', 'GITHUB_RUN_ATTEMPT':'1', 'GITHUB_RUN_ID':'107',
            'GITHUB_JOB':'bootstrap','PR_NUMBER':'101','WORKER37_EVENT_ACTION':'edited',
            'WORKER37_HEAD':'1'*40,'WORKER37_HEAD_REF':'research/worker37-bootstrap-readiness',
            'WORKER37_BASE_REF':'main',
            'WORKER37_BASE_HEAD':'2b00e0d1e76364ae287946f7c0e3dc2baac4653f',
            'WORKER37_HEAD_REPOSITORY':REPOSITORY,'WORKER37_BASE_REPOSITORY':REPOSITORY,
            'WORKER37_BODY_CHANGED':'true','WORKER37_PREVIOUS_BODY':'Prior ordinary body',
            'WORKER37_CURRENT_BODY':'WORKER37_ENGINEERING_ADMISSION_JSON\n{}\nEND_WORKER37_ENGINEERING_ADMISSION_JSON\nWORKER37_ENGINEERING_ADMISSION_SHA256 '+('a'*64),
            'RUNNER_TOOL_CACHE':str(cache),'GITHUB_WORKSPACE':str(source),
            'RUNNER_TEMP':str(temporary_dir),'GITHUB_EVENT_PATH':str(event),
            'GH_TOKEN':TOKEN,'LITERAL_CASE':case_id,'LITERAL_COMMAND_LOG':str(log),
            'LITERAL_VIOLATION_LOG':str(violation),'LITERAL_LIBRARY_HASHED':str(library_hashed),
        }
        environment.update(overrides or {})
        if entry=='launcher':
            argv=['/bin/bash','--noprofile','--norc',str(launcher)]
            body_hash=sha(LAUNCHER_PATH.read_bytes())
        else:
            body=workflow_block(entry)
            argv=['/bin/bash','--noprofile','--norc','-c',body]
            body_hash=sha(body.encode())
        with patch.object(socket.socket,'connect',denied_socket),patch.object(socket,'getaddrinfo',denied_socket):
            process=subprocess.Popen(argv,env=environment,cwd=source,stdin=subprocess.DEVNULL,
                                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            stdout,stderr=process.communicate()
        retain_case_file('shell-stdout.txt',stdout.encode())
        retain_case_file('shell-stderr.txt',stderr.encode())
        retain_case_file('stub-command-log.bin',log.read_bytes() if log.exists() else b'')
        if reservation.exists():
            retain_case_file('allocation-reservation.txt',reservation.read_bytes())
        for path in attempt.iterdir():
            if path.is_file():
                retain_case_file(path.name,path.read_bytes())
        fields=log.read_bytes().split(b'\0')[:-1] if log.exists() else []
        records=[]
        index=0
        while index<len(fields):
            pid,parent,command,mask,loader,count=(v.decode() for v in fields[index:index+6])
            number=int(count)
            arguments=[v.decode() for v in fields[index+6:index+6+number]]
            index+=6+number
            records.append({'pid':int(pid),'parent_pid':int(parent),'command':command,
                            'umask':mask,'loader_environment':loader,'argv':arguments})
        observation={'case_id':case_id,'entrypoint':entry,'entrypoint_sha256':body_hash,
            'harness_started_bash_pid':process.pid,
            'stub_entry_records':len(records),
            'observed_stub_pids':sorted({r['pid'] for r in records}),
            'observed_shell_parent_pids':sorted({r['parent_pid'] for r in records}),
            'physical_process_count':'not_fully_measured; recorded PIDs are observations, not a claimed total',
            'returncode':process.returncode}
        BASH_CASE_OBSERVATIONS.append(observation)
        retain_case_file('bash-process-observations.json',canonical(observation))
        return types.SimpleNamespace(returncode=process.returncode,stdout=stdout,stderr=stderr,
            records=records,commands=[r['command'] for r in records],
            old_namespace_access=violation.exists(),
            reservation_preserved=(initial_reservation is not None and reservation.read_bytes()==initial_reservation),
            observation=observation)

FROZEN_STUB = '#!/bin/bash\nset -euo pipefail\ncommand_name=${0##*/}\nloader_environment=\nfor variable in ${!LD@} ${!PYTHON@}; do\n  loader_environment+="$variable=${!variable};"\ndone\nprintf \'%s\\0\' "$BASHPID" "$PPID" "$command_name" "$(umask)" "$loader_environment" "$#" "$@" >> "$LITERAL_COMMAND_LOG"\nfor argument in "$@"; do\n  case $argument in\n    *worker36-evidence*|*worker36-one-shot-claims*) printf \'old_namespace_access\\n\' >> "$LITERAL_VIOLATION_LOG"; exit 91;;\n  esac\ndone\nlast_argument=${!#}\ncase $command_name in\n  realpath|readlink)\n    if [[ $LITERAL_CASE == T009 && $last_argument == "$RUNNER_TOOL_CACHE/worker37-bootstrap-readiness" ]]; then\n      printf \'%s\\n\' "$GITHUB_WORKSPACE/bootstrap-readiness-evidence"\n    else\n      printf \'%s\\n\' "$last_argument"\n    fi\n    ;;\n  id) printf \'1000\\n\';;\n  stat)\n    if [[ ${1-} == -f ]]; then\n      printf \'1048576:4096\\n\'\n    elif [[ ${2-} == \'%u:%a\' ]]; then\n      if [[ $LITERAL_CASE == T010 && $last_argument == "$RUNNER_TOOL_CACHE/worker37-bootstrap-readiness" ]]; then\n        printf \'1001:700\\n\'\n      elif [[ $LITERAL_CASE == T011 && $last_argument == "$RUNNER_TOOL_CACHE/worker37-bootstrap-readiness" ]]; then\n        printf \'1000:755\\n\'\n      else\n        printf \'1000:700\\n\'\n      fi\n    elif [[ ${2-} == \'%d:%i:%s:%Y\' ]]; then\n      if [[ $last_argument == */libpython3.11.so.1.0 ]]; then\n        if [[ $LITERAL_CASE == T018 && -e $LITERAL_LIBRARY_HASHED ]]; then\n          printf \'1:12:23041360:1\\n\'\n        else\n          printf \'1:11:23041360:1\\n\'\n        fi\n      elif [[ $last_argument == */bin/python3.11 ]]; then\n        printf \'1:10:64:1\\n\'\n      else\n        contents=\n        IFS= read -r -d \'\' contents < "$last_argument" || :\n        printf \'1:20:%s:1\\n\' "${#contents}"\n      fi\n    elif [[ ${2-} == \'%s\' ]]; then\n      contents=\n      IFS= read -r -d \'\' contents < "$last_argument" || :\n      printf \'%s\\n\' "${#contents}"\n    else\n      exit 92\n    fi\n    ;;\n  mkdir)\n    if [[ $LITERAL_CASE == T012 && $last_argument == */run-107-attempt-1 ]]; then exit 1; fi\n    if [[ $LITERAL_CASE == T013 && $last_argument == */allocations/worker37-bootstrap-readiness-01 ]]; then exit 1; fi\n    # Every finite literal directory is prepared by the Python harness. This\n    # stub represents the preregistered exclusive-create result only.\n    [[ -d $last_argument ]]\n    ;;\n  cat)\n    while IFS= read -r line || [[ -n $line ]]; do printf \'%s\\n\' "$line"; done < "$last_argument"\n    ;;\n  sync) :;;\n  sha256sum)\n    if [[ $last_argument == */bin/python3.11 ]]; then\n      if [[ $LITERAL_CASE == T015 ]]; then\n        printf \'%064d  %s\\n\' 0 "$last_argument"\n      else\n        printf \'a15ccdaf07655a8667a3687b13171486c9a265d92273ba3ad820fbb64d2cfecc  %s\\n\' "$last_argument"\n      fi\n    elif [[ $last_argument == */libpython3.11.so.1.0 ]]; then\n      : > "$LITERAL_LIBRARY_HASHED"\n      if [[ $LITERAL_CASE == T016 ]]; then\n        printf \'%064d  %s\\n\' 0 "$last_argument"\n      else\n        printf \'ba4450817186fbe1e3c477f6aefeee7c353cba3593cc9950382ad9d1f5e62896  %s\\n\' "$last_argument"\n      fi\n    else\n      printf \'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa  %s\\n\' "$last_argument"\n    fi\n    ;;\n  git)\n    if [[ $last_argument == \'HEAD^{tree}\' ]]; then printf \'2222222222222222222222222222222222222222\\n\'\n    else printf \'1111111111111111111111111111111111111111\\n\'; fi\n    ;;\n  timeout)\n    outer=false\n    if [[ ${1-} == --signal=KILL && ${2-} == 600s ]]; then outer=true; shift 2\n    elif [[ ${1-} == --foreground && ${2-} == --signal=KILL && ${3-} == 120s ]]; then shift 3\n    else exit 93; fi\n    if [[ $outer == true && $LITERAL_CASE == T006 ]]; then\n      export LD_WORKER37_SENTINEL=invented_launcher_loader PYTHON_WORKER37_SENTINEL=invented_launcher_python\n      umask 022\n    fi\n    exec "$@"\n    ;;\n  python3.11)\n    if [[ $LITERAL_CASE == T038 ]]; then exit 137; fi\n    output=\n    while (( $# )); do\n      if [[ $1 == --output ]]; then shift; output=$1; fi\n      shift\n    done\n    [[ -n $output ]]\n    printf \'{"literal":"invented_inert_result"}\\n\' > "$output/result.json"\n    printf \'{"literal":"invented_inert_inventory"}\\n\' > "$output/inventory.json"\n    printf \'{"literal":"invented_inert_terminal"}\\n\' > "$output/terminal.json"\n    printf \'INVENTED_PINNED_STUB_EXIT=0\\n\'\n    ;;\n  *) exit 94;;\nesac\n'

class Worker37LiteralCases(unittest.TestCase):
    def setUp(self):
        global CURRENT_CASE_ID
        CURRENT_CASE_ID=self._testMethodName.split('_',2)[1]

    def test_T001_valid_direct_path(self):
        s = LiteralScenario()
        run_python(s)
        self.assertOutcome(s, 'bootstrap_ready', 'P09', 7)
        self.assertEqual(s.retained['preflight.zip'], s.zip_bytes)
        self.assertEqual(s.result['scientific_classification'], None)

    def test_T002_gh_jq_absent(self):
        s = run_bash('T002', entry='launcher')
        self.assertEqual(s.returncode, 0)
        self.assertPinnedInvocation(s)
        self.assertNotIn('gh', s.commands)
        self.assertNotIn('jq', s.commands)

    def test_T003_wrong_actor(self):
        s = run_bash('T003', entry='P00', overrides={'GITHUB_ACTOR':'other-user'})
        self.assertShellBlocked(s, 'P00')
        self.assertEqual(s.commands, [])

    def test_T004_attempt_two(self):
        s = run_bash('T004', entry='P00', overrides={'GITHUB_RUN_ATTEMPT':'2'})
        self.assertShellBlocked(s, 'P00')
        self.assertEqual(s.commands, [])

    def test_T005_invalid_identifiers(self):
        s = run_bash('T005', entry='P00', overrides={'PR_NUMBER':'01'})
        self.assertShellBlocked(s, 'P00')
        self.assertEqual(s.commands, [])

    def test_T006_inherited_loader_environment(self):
        s = run_bash('T006', entry='P02', overrides={
            'LD_WORKER37_SENTINEL':'invented-outer-loader',
            'PYTHON_WORKER37_SENTINEL':'invented-outer-python'})
        self.assertEqual(s.returncode, 0)
        self.assertPinnedInvocation(s)
        self.assertTrue(s.records)
        self.assertTrue(all(r['umask'] == '0077' for r in s.records))
        self.assertTrue(all('SENTINEL' not in r['loader_environment'] for r in s.records))
        self.assertEqual(len([r for r in s.records if r['command']=='timeout']), 2)

    def test_T007_required_timeout_missing(self):
        s = run_bash('T007', entry='P02')
        self.assertShellBlocked(s, 'P02')
        self.assertEqual(s.commands, [])

    def test_T008_toolcache_symlink(self):
        s = run_bash('T008', entry='launcher')
        self.assertShellBlocked(s, 'P03')
        self.assertNotIn('python3.11', s.commands)

    def test_T009_durable_inside_workspace(self):
        s = run_bash('T009', entry='launcher')
        self.assertShellBlocked(s, 'P03')
        self.assertNotIn('python3.11', s.commands)

    def test_T010_durable_owner_mismatch(self):
        s = run_bash('T010', entry='launcher')
        self.assertShellBlocked(s, 'P03')
        self.assertNotIn('chown', s.commands)

    def test_T011_durable_mode_mismatch(self):
        s = run_bash('T011', entry='launcher')
        self.assertShellBlocked(s, 'P03')
        self.assertNotIn('chmod', s.commands)

    def test_T012_existing_output(self):
        s = run_bash('T012', entry='launcher')
        self.assertShellBlocked(s, 'P03')
        self.assertNotIn('python3.11', s.commands)
        self.assertNotIn('rm', s.commands)

    def test_T013_exclusive_create_race(self):
        s = run_bash('T013', entry='launcher')
        self.assertShellBlocked(s, 'P03')
        self.assertNotIn('python3.11', s.commands)
        self.assertTrue(s.reservation_preserved)

    def test_T014_historical_namespace_sentinel(self):
        s = run_bash('T014', entry='launcher')
        self.assertEqual(s.returncode, 0)
        self.assertPinnedInvocation(s)
        self.assertFalse(s.old_namespace_access)

    def test_T015_executable_hash_mismatch(self):
        s = run_bash('T015', entry='launcher')
        self.assertShellBlocked(s, 'P04')
        self.assertNotIn('python3.11', s.commands)

    def test_T016_library_hash_mismatch(self):
        s = run_bash('T016', entry='launcher')
        self.assertShellBlocked(s, 'P04')
        self.assertNotIn('python3.11', s.commands)

    def test_T017_mapped_library_mismatch(self):
        s = LiteralScenario()
        s.mapped_inode = 12
        run_python(s)
        self.assertOutcome(s, 'integrity_invalid', 'P05', 0)

    def test_T018_loader_changes_during_hash(self):
        s = run_bash('T018', entry='launcher')
        self.assertShellBlocked(s, 'P04')
        self.assertNotIn('python3.11', s.commands)

    def test_T019_incorrect_python_flags(self):
        s = LiteralScenario()
        s.flags.no_user_site = 0
        run_python(s)
        self.assertOutcome(s, 'execution_blocked', 'P05', 0)

    def test_T020_gc_threshold_mismatch(self):
        s = LiteralScenario()
        s.gc_threshold = (700, 11, 10)
        run_python(s)
        self.assertOutcome(s, 'execution_blocked', 'P05', 0)

    def test_T021_unexpected_inherited_limit(self):
        s = LiteralScenario()
        s.inherited_limits['RLIMIT_AS'] = [268435456, 268435456]
        run_python(s)
        self.assertOutcome(s, 'execution_blocked', 'P05', 0)
        self.assertEqual(s.observed_setrlimit, [])

    def test_T022_memory_cap_install_failure(self):
        s = LiteralScenario()
        s.setrlimit_failure = True
        run_python(s)
        self.assertOutcome(s, 'execution_blocked', 'P05', 0)
        self.assertEqual(len(s.observed_setrlimit), 1)

    def test_T023_occupied_hook(self):
        s = LiteralScenario()
        s.occupied_profile = 'INVENTED_OCCUPIED_PROFILE'
        run_python(s)
        self.assertOutcome(s, 'execution_blocked', 'P05', 0)
        self.assertEqual(s.occupied_profile, 'INVENTED_OCCUPIED_PROFILE')

    def test_T024_restoration_failure(self):
        s = LiteralScenario()
        s.restoration_failure = True
        run_python(s)
        self.assertOutcome(s, 'evidence_incomplete', 'P07', 1)
        self.assertEqual(s.result['error_code'], 'response_close_unconfirmed')
        self.assertFalse(s.result['restoration']['confirmed'])

    def test_T025_exact_seven_request_mapping(self):
        s = LiteralScenario()
        run_python(s)
        self.assertOutcome(s, 'bootstrap_ready', 'P09', 7)
        self.assertEqual([r['url'] for r in s.requests], [API+p for p in REQUEST_PATHS])
        self.assertEqual([r['method'] for r in s.requests], ['GET']*7)
        self.assertTrue(all(r['headers'].get('authorization')=='Bearer '+TOKEN for r in s.requests))
        self.assertTrue(all(name in s.retained for name in RETAINED_NAMES))

    def test_T026_boolean_reference_id(self):
        s = LiteralScenario()
        s.descriptor['historical_fixture']['artifact_id'] = True
        run_python(s)
        self.assertOutcome(s, 'execution_blocked', 'P06', 0)

    def test_T027_arbitrary_fetch_url(self):
        s = LiteralScenario()
        s.descriptor['fetch_url'] = 'https://other.example.invalid/steal'
        run_python(s)
        self.assertOutcome(s, 'execution_blocked', 'P06', 0)

    def test_T028_missing_token(self):
        s = LiteralScenario()
        s.token = None
        run_python(s)
        self.assertOutcome(s, 'execution_blocked', 'P06', 0)

    def test_T029_new_head_mismatch(self):
        s = LiteralScenario()
        s.new_head_override = '1'*39+'a'
        run_python(s)
        self.assertOutcome(s, 'integrity_invalid', 'P07', 1)
        self.assertIn('pull-request.json', s.retained)

    def test_T030_new_body_mismatch(self):
        s = LiteralScenario()
        s.new_body_override = 'INVENTED changed live PR body'
        run_python(s)
        self.assertOutcome(s, 'integrity_invalid', 'P07', 1)
        self.assertIn('pull-request.json', s.retained)

    def test_T031_new_review_source_mismatch(self):
        s = LiteralScenario()
        s.review_head_override = '3'*40
        run_python(s)
        self.assertOutcome(s, 'integrity_invalid', 'P07', 4)
        self.assertIn('review-adversarial.json', s.retained)

    def test_T032_base_ci_not_successful(self):
        s = LiteralScenario()
        s.base_conclusion = 'failure'
        run_python(s)
        self.assertOutcome(s, 'execution_blocked', 'P07', 2)

    def test_T033_prior_fixture_wrong_source(self):
        s = LiteralScenario()
        s.prior_head_override = '1'*40
        run_python(s)
        self.assertOutcome(s, 'integrity_invalid', 'P07', 5)
        prior = json.loads(s.retained['preflight-run.json'])
        self.assertEqual(prior['head_sha'], '1'*40)
        self.assertNotIn('tree', prior)
        self.assertNotIn('preflight-artifact.json', s.retained)

    def test_T034_http_403(self):
        s = LiteralScenario()
        raw = b'{"message":"denied"}'
        s.response_replacements[0] = LiteralResponse(raw, 403)
        run_python(s)
        self.assertOutcome(s, 'execution_blocked', 'P07', 1)
        self.assertEqual(s.retained['pull-request.json'], raw)

    def test_T035_http_500(self):
        s = LiteralScenario()
        raw = b'{"message":"failed"}'
        s.response_replacements[2] = LiteralResponse(raw, 500)
        run_python(s)
        self.assertOutcome(s, 'execution_blocked', 'P07', 3)
        self.assertEqual(s.retained['review-exhaustive.json'], raw)

    def test_T036_tls_verification_failure(self):
        s = LiteralScenario()
        s.tls_failure = True
        run_python(s)
        self.assertOutcome(s, 'execution_blocked', 'P07', 1)
        self.assertNotIn(b'CERTIFICATE_SENTINEL', s.output)

    def test_T037_network_deadline_expired(self):
        s = LiteralScenario()
        s.expired_after_third = True
        run_python(s)
        self.assertOutcome(s, 'resource_incomplete', 'P07', 3)

    def test_T038_nested_timeout_group_contract(self):
        s = run_bash('T038', entry='P02')
        self.assertEqual(s.returncode, 137)
        timeouts = [r['argv'] for r in s.records if r['command']=='timeout']
        self.assertEqual(len(timeouts), 2)
        self.assertEqual(timeouts[0][:2], ['--signal=KILL','600s'])
        self.assertNotIn('--foreground', timeouts[0])
        self.assertEqual(timeouts[1][:3], ['--foreground','--signal=KILL','120s'])
        self.assertTrue(all('--kill-after' not in ' '.join(argv) for argv in timeouts))
        self.assertEqual(s.commands.count('python3.11'), 1)

    def test_T039_json_redirect_rejected(self):
        s = LiteralScenario()
        s.response_replacements[0] = LiteralResponse(b'',302,{'Location':STORAGE})
        run_python(s)
        self.assertOutcome(s, 'execution_blocked', 'P07', 1)

    def test_T040_zip_redirect_allowed(self):
        s = LiteralScenario()
        raw = ('INVENTED redirect '+STORAGE).encode()
        s.response_replacements[6] = LiteralResponse(raw,302,{'Location':STORAGE,'Content-Length':str(len(raw))})
        s.response_replacements[7] = LiteralResponse(s.zip_bytes)
        run_python(s)
        self.assertOutcome(s, 'bootstrap_ready', 'P09', 8)
        self.assertUnauthenticatedStorage(s)
        self.assertOmitted(s, raw, 'redirect_body_may_contain_signed_url',302)
        self.assertEqual(s.retained['preflight.zip'], s.zip_bytes)
        self.assertEqual(s.result['response_body_bytes'], sum(r['received'] for r in s.requests))

    def test_T041_zip_redirect_wrong_host(self):
        s = LiteralScenario()
        s.response_replacements[6] = LiteralResponse(b'',302,{'Location':'https://worker37fixture.blob.core.windows.net.evil.example/a'})
        run_python(s)
        self.assertOutcome(s, 'execution_blocked', 'P07', 7)

    def test_T042_zip_redirect_http_downgrade(self):
        s = LiteralScenario()
        s.response_replacements[6] = LiteralResponse(b'',302,{'Location':'http://worker37fixture.blob.core.windows.net/a'})
        run_python(s)
        self.assertOutcome(s, 'execution_blocked', 'P07', 7)

    def test_T043_zip_second_redirect(self):
        s = LiteralScenario()
        s.response_replacements[6] = LiteralResponse(b'',302,{'Location':STORAGE})
        s.response_replacements[7] = LiteralResponse(b'',302,{'Location':'https://worker37fixture.blob.core.windows.net/newpath'})
        run_python(s)
        self.assertOutcome(s, 'execution_blocked', 'P07', 8)
        self.assertUnauthenticatedStorage(s)

    def test_T044_token_redaction(self):
        s = LiteralScenario()
        url = 'https://worker37fixture.blob.core.windows.net/a?signature=SECRET_43'
        raw = ('INVENTED storage error '+url+' token '+TOKEN).encode()
        s.response_replacements[6] = LiteralResponse(b'',302,{'Location':url})
        s.response_replacements[7] = LiteralResponse(raw,403)
        run_python(s)
        self.assertOutcome(s, 'execution_blocked', 'P07', 8)
        self.assertUnauthenticatedStorage(s)
        self.assertOmitted(s, raw, 'storage_error_body_may_contain_signed_url',403)
        self.assertNotIn(b'SECRET_43', s.output+b''.join(s.retained.values()))
        self.assertNotIn(TOKEN.encode(), s.output+b''.join(s.retained.values()))

    def test_T045_ambient_proxy_ignored(self):
        s = LiteralScenario()
        s.extra_environment = {'HTTPS_PROXY':'https://proxy.example.invalid',
                               'NETRC':'literal.netrc', 'COOKIE_JAR':'literal.cookies'}
        run_python(s)
        self.assertOutcome(s, 'bootstrap_ready', 'P09', 7)
        self.assertTrue(all(r['url'].startswith(API+'/') for r in s.requests))
        self.assertTrue(s.openers)
        self.assertTrue(all(not isinstance(h, urllib.request.HTTPCookieProcessor)
                            for opener in s.openers for h in opener.handlers))
        self.assertTrue(all(not h.proxies for opener in s.openers for h in opener.handlers
                            if isinstance(h,urllib.request.ProxyHandler)))

    def test_T046_oversized_response(self):
        s = LiteralScenario()
        raw = b'X'*2097153
        s.response_replacements[0] = LiteralResponse(raw,200,{'Transfer-Encoding':'chunked'})
        run_python(s)
        self.assertOutcome(s, 'resource_incomplete', 'P07', 1)
        self.assertEqual(s.result['response_body_bytes'], 2097153)
        self.assertEqual(s.retained['pull-request.json'], raw[:2097152])
        self.assertTrue(any(r.get('truncated') or r.get('overflow') for r in s.result['requests']))

    def test_T047_truncated_response(self):
        s = LiteralScenario()
        raw = b'{"x":1}'
        s.response_replacements[0] = LiteralResponse(raw,200,{'Content-Length':'9'})
        run_python(s)
        self.assertOutcome(s, 'evidence_incomplete', 'P07', 1)
        self.assertEqual(s.retained['pull-request.json'], raw)

    def test_T048_duplicate_json_key(self):
        s = LiteralScenario()
        raw = b'{"id":1,"id":2}'
        s.response_replacements[0] = LiteralResponse(raw)
        run_python(s)
        self.assertOutcome(s, 'integrity_invalid', 'P07', 1)
        self.assertEqual(s.retained['pull-request.json'], raw)

    def test_T049_nonfinite_json(self):
        s = LiteralScenario()
        raw = b'{"value":NaN}'
        s.response_replacements[0] = LiteralResponse(raw)
        run_python(s)
        self.assertOutcome(s, 'integrity_invalid', 'P07', 1)
        self.assertEqual(s.retained['pull-request.json'], raw)

    def test_T050_invalid_utf8_json(self):
        s = LiteralScenario()
        raw = bytes.fromhex('7b2278223aff7d')
        s.response_replacements[0] = LiteralResponse(raw)
        run_python(s)
        self.assertOutcome(s, 'integrity_invalid', 'P07', 1)
        self.assertEqual(s.retained['pull-request.json'], raw)

    def test_T051_unsupported_content_encoding(self):
        s = LiteralScenario()
        s.response_replacements[0] = LiteralResponse(b'INVENTED_GZIP',200,{'Content-Encoding':'gzip'})
        run_python(s)
        self.assertOutcome(s, 'execution_blocked', 'P07', 1)

    def test_T052_archive_hash_mismatch(self):
        s = LiteralScenario()
        s.zip_bytes = base64.b64decode(FROZEN_ZIPS['T052'])
        run_python(s)
        self.assertOutcome(s, 'integrity_invalid', 'P08', 7)
        self.assertEqual(s.result['error_code'], 'archive_hash')

    def test_T053_archive_extra_member(self):
        s = LiteralScenario()
        s.repin_zip('T053')
        run_python(s)
        self.assertOutcome(s, 'integrity_invalid', 'P08', 7)
        self.assertIn('member', s.result['error_code'])

    def test_T054_archive_duplicate_member(self):
        s = LiteralScenario()
        s.repin_zip('T054')
        run_python(s)
        self.assertOutcome(s, 'integrity_invalid', 'P08', 7)
        self.assertIn('duplicate', s.result['error_code'])

    def test_T055_archive_expanded_overflow(self):
        s = LiteralScenario()
        s.repin_zip('T055')
        run_python(s)
        self.assertOutcome(s, 'integrity_invalid', 'P08', 7)
        self.assertIn('expan', s.result['error_code'])

    def test_T056_archive_component_mismatch(self):
        s = LiteralScenario()
        original_report = s.descriptor['historical_fixture']['report_sha256']
        s.repin_zip('T056')
        run_python(s)
        self.assertOutcome(s, 'integrity_invalid', 'P08', 7)
        self.assertIn('component', s.result['error_code'])
        self.assertEqual(s.descriptor['historical_fixture']['report_sha256'],original_report)

    def test_T057_persistence_short_write(self):
        s = LiteralScenario()
        s.short_write = True
        run_python(s)
        self.assertOutcome(s, 'evidence_incomplete', 'P07', 1)
        self.assertEqual(s.retained['pull-request.json'], s.requests[0]['body'][:3])
        record = s.result['inputs']['pull-request.json']
        self.assertFalse(record['file_fsync_confirmed'])
        self.assertFalse(record['directory_fsync_confirmed'])

    def test_T058_directory_fsync_failure(self):
        s = LiteralScenario()
        s.directory_fsync_failure = True
        run_python(s)
        self.assertOutcome(s, 'evidence_incomplete', 'P07', 1)
        self.assertEqual(s.retained['pull-request.json'], s.requests[0]['body'])
        record = s.result['inputs']['pull-request.json']
        self.assertTrue(record['file_fsync_confirmed'])
        self.assertFalse(record['directory_fsync_confirmed'])

    def test_T059_readback_digest_mismatch(self):
        s = LiteralScenario()
        s.readback_mismatch = True
        run_python(s)
        self.assertOutcome(s, 'integrity_invalid', 'P09', 7)
        self.assertIn('readback', s.result['error_code'])
        self.assertPrimary(s,'integrity_invalid','readback_digest','P09')

    def test_T060_source_graph_and_terminal_stop(self):
        workflow = WORKFLOW_PATH.read_text()
        launcher = LAUNCHER_PATH.read_text()
        module = MODULE_PATH.read_text()
        tree = ast.parse(module + '\n' + SHARED_PYTHON_PATH.read_text())
        imports = [n for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))]
        imported = [alias.name for n in imports for alias in n.names]
        self.assertNotIn('subprocess', imported)
        self.assertFalse(any(name.startswith(('bandido_alcatraz','worker36')) for name in imported))
        self.assertNotIn('setup-python', workflow)
        self.assertIn('types: [edited]', workflow)
        self.assertIn('persist-credentials: false', workflow)
        self.assertIn('timeout-minutes: 5', workflow)
        self.assertIn('timeout --signal=KILL 600s', workflow)
        self.assertIn('timeout --foreground --signal=KILL 120s', launcher)
        self.assertNotIn('--kill-after', launcher+workflow)
        self.assertNotIn('worker36-evidence', launcher)
        self.assertNotIn('worker36-one-shot-claims', launcher)
        self.assertNotIn('WORKER36_CLAIM_DIRECTORY', launcher+workflow+module)
        self.assertNotIn('admission.env', launcher+workflow+module)
        self.assertNotIn('setitimer(', module)
        self.assertNotIn('Thread(', module)
        self.assertNotIn('setup-python', launcher+workflow)
        self.assertNotIn(' gh ', launcher+workflow)
        self.assertNotIn(' jq ', launcher+workflow)
        self.assertIn('measurement_admitted', module)
        self.assertIn('scientific_classification', module)
        self.assertIn('\"scripts/worker_bootstrap_shared.sh\"', module)
        self.assertIn('\"scripts/worker_bootstrap_shared.py\"', module)
        self.assertIn('bootstrap_worker37_prepare', launcher)
        self.assertIn('bootstrap_shared.runtime_start(observation, \"worker37-preparation-v1\")', module)

    def test_T061_overflow_primary_survives_readback_failure(self):
        s = LiteralScenario()
        s.response_replacements[0] = LiteralResponse(b'X'*2097153,200,{'Transfer-Encoding':'chunked'})
        s.readback_mismatch = True
        s.readback_after_requests = 1
        run_python(s)
        self.assertOutcome(s,'resource_incomplete','P07',1)
        self.assertPrimary(s,'resource_incomplete','input_body_overflow','P07')
        self.assertSecondary(s,'integrity_invalid','readback_digest','P09')
        self.assertEqual(s.result['response_body_bytes'],2097153)
        self.assertEqual(s.retained['pull-request.json'],b'X'*2097152)

    def test_T062_integrity_primary_survives_restoration_failure(self):
        s = LiteralScenario()
        raw = b'{"id":1,"id":2}'
        s.response_replacements[0] = LiteralResponse(raw)
        s.restoration_limit_failure = True
        run_python(s)
        self.assertOutcome(s,'integrity_invalid','P07',1)
        self.assertPrimary(s,'integrity_invalid','duplicate_json_key','P07')
        self.assertSecondary(s,'evidence_incomplete','restoration_mismatch','P09')
        self.assertEqual(s.retained['pull-request.json'],raw)
        self.assertFalse(s.result['restoration']['confirmed'])

    def test_T063_first_p09_memory_failure_has_primary(self):
        s = LiteralScenario()
        s.readback_memory_failure = True
        run_python(s)
        self.assertOutcome(s,'resource_incomplete','P09',7)
        self.assertPrimary(s,'resource_incomplete','terminal_memory_exhausted','P09')

    def test_T064_source_cap_primary_survives_descriptor_close(self):
        s = LiteralScenario()
        s.source_cap_failure = True
        s.descriptor_close_operation = 'source_read'
        run_python(s)
        self.assertOutcome(s,'resource_incomplete','P06',0)
        self.assertPrimary(s,'resource_incomplete','local_file_cap','P06')
        self.assertSecondary(s,'evidence_incomplete','descriptor_close_failed','P06','bounded_read')
        self.assertEqual(s.injected_close_failures,1)

    def test_T065_source_identity_primary_survives_descriptor_close(self):
        s = LiteralScenario()
        s.source_identity_failure = True
        s.descriptor_close_operation = 'source_read'
        run_python(s)
        self.assertOutcome(s,'integrity_invalid','P06',0)
        self.assertPrimary(s,'integrity_invalid','local_file_changed','P06')
        self.assertSecondary(s,'evidence_incomplete','descriptor_close_failed','P06','bounded_read')
        self.assertEqual(s.injected_close_failures,1)

    def test_T066_event_integrity_primary_survives_descriptor_close(self):
        s = LiteralScenario()
        s.event_hash_override = '0'*64
        s.descriptor_close_operation = 'event_snapshot'
        run_python(s)
        self.assertOutcome(s,'integrity_invalid','P05',0)
        self.assertPrimary(s,'integrity_invalid','event_snapshot_agreement','P05')
        self.assertSecondary(s,'evidence_incomplete','descriptor_close_failed','P05','event_snapshot')
        self.assertEqual(s.injected_close_failures,1)

    def test_T067_persistence_primary_survives_descriptor_close(self):
        s = LiteralScenario()
        s.short_write = True
        s.descriptor_close_operation = 'api_write'
        run_python(s)
        self.assertOutcome(s,'evidence_incomplete','P07',1)
        self.assertPrimary(s,'evidence_incomplete','persistence_failed','P07')
        self.assertSecondary(s,'evidence_incomplete','descriptor_close_failed','P07','evidence_write')
        self.assertEqual(s.injected_close_failures,1)
        self.assertEqual(s.retained['pull-request.json'],s.requests[0]['body'][:3])
        self.assertFalse(s.result['inputs']['pull-request.json']['file_fsync_confirmed'])
        self.assertFalse(s.result['inputs']['pull-request.json']['directory_fsync_confirmed'])

    def test_T068_incomplete_read_partial_application_retained(self):
        s = LiteralScenario()
        s.response_replacements[0] = LiteralIncompleteResponse(b'{"x"',b':1}')
        run_python(s)
        self.assertOutcome(s,'evidence_incomplete','P07',1)
        self.assertPrimary(s,'evidence_incomplete','response_incomplete_read','P07')
        self.assertEqual(s.retained['pull-request.json'],b'{"x":1}')
        self.assertEqual(s.result['response_body_bytes'],7)
        self.assertEqual(s.requests[0]['received'],7)
        self.assertIncomplete(s.result['requests'][0],7,7)

    def test_T069_incomplete_redirect_partial_omitted(self):
        s = LiteralScenario()
        url = 'https://worker37fixture.blob.core.windows.net/a?signature=REPAIR01_SECRET'
        raw = ('INVENTED repair01 redirect '+url+' token '+TOKEN).encode()
        s.response_replacements[6] = LiteralIncompleteResponse(b'',raw,302,{'Location':url,'Transfer-Encoding':'chunked'})
        run_python(s)
        self.assertOutcome(s,'evidence_incomplete','P07',7)
        self.assertPrimary(s,'evidence_incomplete','response_incomplete_read','P07')
        self.assertIncomplete(s.result['requests'][6],len(raw),0)
        self.assertOmitted(s,raw,'redirect_body_may_contain_signed_url',302)
        self.assertEqual(s.result['response_body_bytes'],sum(r['received'] for r in s.requests))
        combined = s.output+b''.join(s.retained.values())
        self.assertNotIn(b'REPAIR01_SECRET',combined)
        self.assertNotIn(TOKEN.encode(),combined)
        self.assertNotIn('preflight.zip',s.retained)

    def test_T070_incomplete_storage_error_partial_omitted(self):
        s = LiteralScenario()
        url = 'https://worker37fixture.blob.core.windows.net/a?signature=REPAIR01_SECRET'
        raw = ('INVENTED repair01 storage error '+url+' token '+TOKEN).encode()
        s.response_replacements[6] = LiteralResponse(b'',302,{'Location':url})
        s.response_replacements[7] = LiteralIncompleteResponse(b'',raw,403,{'Transfer-Encoding':'chunked'})
        run_python(s)
        self.assertOutcome(s,'evidence_incomplete','P07',8)
        self.assertPrimary(s,'evidence_incomplete','response_incomplete_read','P07')
        self.assertUnauthenticatedStorage(s)
        self.assertIncomplete(s.result['requests'][7],len(raw),0)
        self.assertOmitted(s,raw,'storage_error_body_may_contain_signed_url',403)
        self.assertEqual(s.result['response_body_bytes'],sum(r['received'] for r in s.requests))
        combined = s.output+b''.join(s.retained.values())
        self.assertNotIn(b'REPAIR01_SECRET',combined)
        self.assertNotIn(TOKEN.encode(),combined)
        self.assertNotIn('preflight.zip',s.retained)

    def test_T071_incomplete_partial_detection_byte_overflow(self):
        s = LiteralScenario()
        s.response_replacements[0] = LiteralIncompleteResponse(b'X'*2097152,b'X')
        run_python(s)
        self.assertOutcome(s,'resource_incomplete','P07',1)
        self.assertPrimary(s,'resource_incomplete','input_body_overflow','P07')
        self.assertEqual(s.result['response_body_bytes'],2097153)
        self.assertEqual(s.requests[0]['received'],2097153)
        self.assertEqual(s.retained['pull-request.json'],b'X'*2097152)
        self.assertIncomplete(s.result['requests'][0],2097153,2097152)
        self.assertTrue(s.result['requests'][0]['truncated'])

    def test_T072_positive_float_overflow_rejected(self):
        s = LiteralScenario()
        s.extra_numeric_literal = b'1e999'
        run_python(s)
        self.assertOutcome(s,'integrity_invalid','P07',1)
        self.assertPrimary(s,'integrity_invalid','nonfinite_json','P07')
        self.assertEqual(s.retained['pull-request.json'],s.requests[0]['body'])
        self.assertIn(b'"literal_number":1e999',s.retained['pull-request.json'])

    def test_T073_negative_float_overflow_rejected(self):
        s = LiteralScenario()
        s.extra_numeric_literal = b'-1e999'
        run_python(s)
        self.assertOutcome(s,'integrity_invalid','P07',1)
        self.assertPrimary(s,'integrity_invalid','nonfinite_json','P07')
        self.assertEqual(s.retained['pull-request.json'],s.requests[0]['body'])
        self.assertIn(b'"literal_number":-1e999',s.retained['pull-request.json'])

    def test_T074_finite_float_boundary_accepted(self):
        s = LiteralScenario()
        s.extra_numeric_literal = b'1e308'
        run_python(s)
        self.assertOutcome(s,'bootstrap_ready','P09',7)
        self.assertEqual(s.retained['pull-request.json'],s.requests[0]['body'])
        self.assertIn(b'"literal_number":1e308',s.retained['pull-request.json'])

    def test_T075_descriptor_close_only_becomes_primary(self):
        s = LiteralScenario()
        s.descriptor_close_operation = 'source_read'
        run_python(s)
        self.assertOutcome(s,'evidence_incomplete','P06',0)
        self.assertPrimary(s,'evidence_incomplete','descriptor_close_failed','P06')
        self.assertEqual(s.injected_close_failures,1)
        self.assertFalse(any(item.get('code')=='descriptor_close_failed'
                             for item in s.result['secondary_failures']))

    def test_T076_empty_prior_association_valid(self):
        s = LiteralScenario()
        s.prior_association_override = []
        run_python(s)
        self.assertOutcome(s,'bootstrap_ready','P09',7)
        self.assertAbsentPriorAssociation(s)
        self.assertEqual(json.loads(s.retained['preflight-run.json'])['pull_requests'],[])

    def test_T077_prior_association_wrong_pr(self):
        s = LiteralScenario()
        s.prior_association_override = [{'number':41,'head':{'sha':'3'*40}}]
        run_python(s)
        self.assertOutcome(s,'integrity_invalid','P07',5)
        self.assertPrimary(s,'integrity_invalid','prior_pr','P07')
        self.assertNotIn('historical_pr_association',s.result)
        self.assertNotIn('preflight-artifact.json',s.retained)

    def test_T078_prior_association_wrong_head(self):
        s = LiteralScenario()
        s.prior_association_override = [{'number':40,'head':{'sha':'1'*40}}]
        run_python(s)
        self.assertOutcome(s,'integrity_invalid','P07',5)
        self.assertPrimary(s,'integrity_invalid','prior_pr','P07')
        self.assertNotIn('historical_pr_association',s.result)
        self.assertEqual(json.loads(s.retained['preflight-run.json'])['head_sha'],'3'*40)
        self.assertNotIn('preflight-artifact.json',s.retained)

    def test_T079_prior_association_missing(self):
        s = LiteralScenario()
        s.omit_prior_association = True
        run_python(s)
        self.assertOutcome(s,'integrity_invalid','P07',5)
        self.assertPrimary(s,'integrity_invalid','prior_pr','P07')
        self.assertNotIn('historical_pr_association',s.result)
        self.assertNotIn('pull_requests',json.loads(s.retained['preflight-run.json']))
        self.assertNotIn('preflight-artifact.json',s.retained)

    def test_T080_prior_association_not_list(self):
        s = LiteralScenario()
        s.prior_association_override = {}
        run_python(s)
        self.assertOutcome(s,'integrity_invalid','P07',5)
        self.assertPrimary(s,'integrity_invalid','prior_pr','P07')
        self.assertNotIn('historical_pr_association',s.result)
        self.assertEqual(json.loads(s.retained['preflight-run.json'])['pull_requests'],{})
        self.assertNotIn('preflight-artifact.json',s.retained)

    def test_T081_prior_association_ambiguous(self):
        s = LiteralScenario()
        s.prior_association_override = [
            {'number':40,'head':{'sha':'3'*40}},
            {'number':41,'head':{'sha':'3'*40}},
        ]
        run_python(s)
        self.assertOutcome(s,'integrity_invalid','P07',5)
        self.assertPrimary(s,'integrity_invalid','prior_pr','P07')
        self.assertNotIn('historical_pr_association',s.result)
        self.assertEqual(len(json.loads(s.retained['preflight-run.json'])['pull_requests']),2)
        self.assertNotIn('preflight-artifact.json',s.retained)

    def test_T082_frozen_historical_pr_mismatch(self):
        s = LiteralScenario()
        s.fixed_historical_pin_override = copy.deepcopy(s.descriptor['historical_fixture'])
        s.descriptor['historical_fixture']['pr_number'] = 41
        run_python(s)
        self.assertOutcome(s,'execution_blocked','P06',0)
        self.assertEqual(s.result['error_code'],'fixed_historical_fixture')
        self.assertEqual(s.result['primary_failure'],{
            'classification':'execution_blocked','code':'fixed_historical_fixture','phase':'P06'})
        self.assertEqual(s.fixed_historical_pin_override['pr_number'],40)
        self.assertNotIn('historical_pr_association',s.result)

    def test_T083_empty_association_artifact_run_mismatch(self):
        s = LiteralScenario()
        s.prior_association_override = []
        s.artifact_run_id_override = 107
        run_python(s)
        self.assertOutcome(s,'integrity_invalid','P07',6)
        self.assertPrimary(s,'integrity_invalid','artifact_source','P07')
        self.assertAbsentPriorAssociation(s)
        self.assertEqual(json.loads(s.retained['preflight-artifact.json'])['workflow_run']['id'],107)
        self.assertNotIn('preflight.zip',s.retained)

    def test_T084_empty_association_archive_hash_mismatch(self):
        s = LiteralScenario()
        s.prior_association_override = []
        s.zip_bytes = base64.b64decode(FROZEN_ZIPS['T052'])
        run_python(s)
        self.assertOutcome(s,'integrity_invalid','P08',7)
        self.assertPrimary(s,'integrity_invalid','archive_hash','P08')
        self.assertAbsentPriorAssociation(s)
        self.assertEqual(s.retained['preflight.zip'],s.zip_bytes)
        self.assertNotEqual(sha(s.zip_bytes),s.descriptor['historical_fixture']['zip_sha256'])

    def assertAbsentPriorAssociation(self,s):
        self.assertEqual(s.result['historical_pr_association'],{
            'live_array_count':0,
            'live_array_binding':'absent',
            'frozen_pr_number':40,
            'association_basis':'frozen_historical_provenance',
            'absence_cause':'not_established',
        })

    def assertPrimary(self,s,classification,code,phase):
        self.assertEqual(s.result['primary_failure'],{
            'classification':classification,'code':code,'phase':phase})
        self.assertEqual(s.result['classification'],classification)
        self.assertEqual(s.result['error_code'],code)
        self.assertEqual(s.result['failed_phase'],phase)
        self.assertEqual(s.exit_code,{'resource_incomplete':3,'integrity_invalid':4,'evidence_incomplete':5}[classification])
        lines=s.output.decode().splitlines()
        self.assertIn('WORKER37_PRIMARY_CLASSIFICATION='+classification,lines)
        self.assertIn('WORKER37_PRIMARY_ERROR='+code,lines)
        self.assertIn('WORKER37_PRIMARY_PHASE='+phase,lines)
        self.assertIn('WORKER37_METADATA_EXIT='+str(s.exit_code),lines)

    def assertSecondary(self,s,classification,code,phase,operation=None):
        matching=[item for item in s.result['secondary_failures']
                  if item.get('classification')==classification and item.get('code')==code
                  and item.get('phase')==phase]
        self.assertEqual(len(matching),1,s.result['secondary_failures'])
        if operation is not None:
            self.assertEqual(matching[0]['operation'],operation)

    def assertIncomplete(self,record,received,retained):
        self.assertEqual(record['received_bytes'],received)
        self.assertEqual(record['retained_bytes'],retained)
        self.assertTrue(record['incomplete_read'])
        self.assertTrue(record['unknown_remainder'])
        self.assertFalse(record['complete'])

    def assertOutcome(self, s, classification, phase, requests):
        self.assertIsNotNone(s.result, s.output.decode(errors='replace'))
        self.assertEqual(s.result['classification'], classification, s.result)
        observed_phase = s.result.get('failed_phase') if s.result['error_code'] else s.result['phase']
        self.assertEqual(observed_phase, phase, s.result)
        self.assertEqual(len(s.requests), requests)
        self.assertEqual(s.result['preparation_only'], True)
        self.assertEqual(s.result['measurement_admitted'], False)
        self.assertIsNone(s.result['scientific_classification'])
        self.assertEqual(s.exit_code, {'bootstrap_ready':0,'execution_blocked':2,'resource_incomplete':3,'integrity_invalid':4,'evidence_incomplete':5}[classification])
        if classification == 'bootstrap_ready':
            self.assertDurableSuccess(s)

    def assertDurableSuccess(self, s):
        self.assertEqual(s.exit_code, 0)
        self.assertEqual(s.output.decode().splitlines(), [
            'WORKER37_TERMINAL_CONFIRMED=1',
            'WORKER37_TERMINAL_ERROR=none',
            'WORKER37_METADATA_EXIT=0',
        ])
        self.assertEqual(s.result['terminal_state'], 'candidate_requires_terminal_receipt')
        self.assertTrue(s.result['restoration']['confirmed'])
        inventory_raw = s.retained['inventory.json']
        terminal = json.loads(s.retained['terminal.json'])
        inventory = json.loads(inventory_raw)
        self.assertTrue(terminal['terminal_candidate'])
        self.assertEqual(terminal['classification'], 'bootstrap_ready')
        self.assertEqual(terminal['exit_code'], 0)
        self.assertTrue(terminal['restoration_confirmed'])
        self.assertTrue(terminal['preparation_only'])
        self.assertFalse(terminal['measurement_admitted'])
        self.assertIsNone(terminal['scientific_classification'])
        self.assertEqual(terminal['result_sha256'], sha(s.retained['result.json']))
        self.assertEqual(terminal['inventory_sha256'], sha(inventory_raw))
        self.assertEqual(terminal['provider_wrapper_custody'], 'pending_external_readback')
        self.assertIn('result.json', inventory['files'])
        for name, record in inventory['files'].items():
            raw = s.retained[name]
            self.assertEqual(record['size_bytes'], len(raw), name)
            self.assertEqual(record['sha256'], sha(raw), name)
            self.assertTrue(record['write_complete'], name)
            self.assertTrue(record['file_fsync_confirmed'], name)
            self.assertTrue(record['directory_fsync_confirmed'], name)
            self.assertTrue(record['readback_confirmed'], name)

    def assertShellBlocked(self, s, phase):
        self.assertNotEqual(s.returncode, 0)
        self.assertIn(phase, s.stdout+s.stderr)

    def assertPinnedInvocation(self, s):
        python = [r for r in s.records if r['command']=='python3.11']
        self.assertEqual(len(python), 1)
        self.assertEqual(python[0]['argv'][:2], ['-B','-s'])
        self.assertTrue(python[0]['argv'][2].endswith('/scripts/worker37_bootstrap.py'))
        inner = [r for r in s.records if r['command']=='timeout' and '--foreground' in r['argv']]
        self.assertEqual(len(inner), 1)
        self.assertEqual(inner[0]['argv'][:3], ['--foreground','--signal=KILL','120s'])

    def assertUnauthenticatedStorage(self, s):
        self.assertEqual(len(s.requests), 8)
        self.assertTrue(all(r['headers'].get('authorization')=='Bearer '+TOKEN for r in s.requests[:7]))
        self.assertTrue(s.requests[7]['url'].startswith('https://worker37fixture.blob.core.windows.net/'))
        self.assertFalse({'authorization','cookie','referer'} & s.requests[7]['headers'].keys())

    def assertOmitted(self, s, raw, reason, status):
        combined = s.output+b''.join(s.retained.values())
        self.assertNotIn(raw, combined)
        self.assertNotIn(sha(raw).encode(), combined)
        self.assertNotIn(b'signature=', combined)
        omissions = [r for r in s.result['requests'] if r.get('omission_reason')==reason]
        self.assertEqual(len(omissions), 1)
        self.assertEqual(omissions[0]['status'], status)
        self.assertEqual(omissions[0]['received_bytes'], len(raw))


def frozen_suite():
    return unittest.TestSuite((
        Worker37LiteralCases('test_T001_valid_direct_path'),
        Worker37LiteralCases('test_T002_gh_jq_absent'),
        Worker37LiteralCases('test_T003_wrong_actor'),
        Worker37LiteralCases('test_T004_attempt_two'),
        Worker37LiteralCases('test_T005_invalid_identifiers'),
        Worker37LiteralCases('test_T006_inherited_loader_environment'),
        Worker37LiteralCases('test_T007_required_timeout_missing'),
        Worker37LiteralCases('test_T008_toolcache_symlink'),
        Worker37LiteralCases('test_T009_durable_inside_workspace'),
        Worker37LiteralCases('test_T010_durable_owner_mismatch'),
        Worker37LiteralCases('test_T011_durable_mode_mismatch'),
        Worker37LiteralCases('test_T012_existing_output'),
        Worker37LiteralCases('test_T013_exclusive_create_race'),
        Worker37LiteralCases('test_T014_historical_namespace_sentinel'),
        Worker37LiteralCases('test_T015_executable_hash_mismatch'),
        Worker37LiteralCases('test_T016_library_hash_mismatch'),
        Worker37LiteralCases('test_T017_mapped_library_mismatch'),
        Worker37LiteralCases('test_T018_loader_changes_during_hash'),
        Worker37LiteralCases('test_T019_incorrect_python_flags'),
        Worker37LiteralCases('test_T020_gc_threshold_mismatch'),
        Worker37LiteralCases('test_T021_unexpected_inherited_limit'),
        Worker37LiteralCases('test_T022_memory_cap_install_failure'),
        Worker37LiteralCases('test_T023_occupied_hook'),
        Worker37LiteralCases('test_T024_restoration_failure'),
        Worker37LiteralCases('test_T025_exact_seven_request_mapping'),
        Worker37LiteralCases('test_T026_boolean_reference_id'),
        Worker37LiteralCases('test_T027_arbitrary_fetch_url'),
        Worker37LiteralCases('test_T028_missing_token'),
        Worker37LiteralCases('test_T029_new_head_mismatch'),
        Worker37LiteralCases('test_T030_new_body_mismatch'),
        Worker37LiteralCases('test_T031_new_review_source_mismatch'),
        Worker37LiteralCases('test_T032_base_ci_not_successful'),
        Worker37LiteralCases('test_T033_prior_fixture_wrong_source'),
        Worker37LiteralCases('test_T034_http_403'),
        Worker37LiteralCases('test_T035_http_500'),
        Worker37LiteralCases('test_T036_tls_verification_failure'),
        Worker37LiteralCases('test_T037_network_deadline_expired'),
        Worker37LiteralCases('test_T038_nested_timeout_group_contract'),
        Worker37LiteralCases('test_T039_json_redirect_rejected'),
        Worker37LiteralCases('test_T040_zip_redirect_allowed'),
        Worker37LiteralCases('test_T041_zip_redirect_wrong_host'),
        Worker37LiteralCases('test_T042_zip_redirect_http_downgrade'),
        Worker37LiteralCases('test_T043_zip_second_redirect'),
        Worker37LiteralCases('test_T044_token_redaction'),
        Worker37LiteralCases('test_T045_ambient_proxy_ignored'),
        Worker37LiteralCases('test_T046_oversized_response'),
        Worker37LiteralCases('test_T047_truncated_response'),
        Worker37LiteralCases('test_T048_duplicate_json_key'),
        Worker37LiteralCases('test_T049_nonfinite_json'),
        Worker37LiteralCases('test_T050_invalid_utf8_json'),
        Worker37LiteralCases('test_T051_unsupported_content_encoding'),
        Worker37LiteralCases('test_T052_archive_hash_mismatch'),
        Worker37LiteralCases('test_T053_archive_extra_member'),
        Worker37LiteralCases('test_T054_archive_duplicate_member'),
        Worker37LiteralCases('test_T055_archive_expanded_overflow'),
        Worker37LiteralCases('test_T056_archive_component_mismatch'),
        Worker37LiteralCases('test_T057_persistence_short_write'),
        Worker37LiteralCases('test_T058_directory_fsync_failure'),
        Worker37LiteralCases('test_T059_readback_digest_mismatch'),
        Worker37LiteralCases('test_T060_source_graph_and_terminal_stop'),
        Worker37LiteralCases('test_T061_overflow_primary_survives_readback_failure'),
        Worker37LiteralCases('test_T062_integrity_primary_survives_restoration_failure'),
        Worker37LiteralCases('test_T063_first_p09_memory_failure_has_primary'),
        Worker37LiteralCases('test_T064_source_cap_primary_survives_descriptor_close'),
        Worker37LiteralCases('test_T065_source_identity_primary_survives_descriptor_close'),
        Worker37LiteralCases('test_T066_event_integrity_primary_survives_descriptor_close'),
        Worker37LiteralCases('test_T067_persistence_primary_survives_descriptor_close'),
        Worker37LiteralCases('test_T068_incomplete_read_partial_application_retained'),
        Worker37LiteralCases('test_T069_incomplete_redirect_partial_omitted'),
        Worker37LiteralCases('test_T070_incomplete_storage_error_partial_omitted'),
        Worker37LiteralCases('test_T071_incomplete_partial_detection_byte_overflow'),
        Worker37LiteralCases('test_T072_positive_float_overflow_rejected'),
        Worker37LiteralCases('test_T073_negative_float_overflow_rejected'),
        Worker37LiteralCases('test_T074_finite_float_boundary_accepted'),
        Worker37LiteralCases('test_T075_descriptor_close_only_becomes_primary'),
        Worker37LiteralCases('test_T076_empty_prior_association_valid'),
        Worker37LiteralCases('test_T077_prior_association_wrong_pr'),
        Worker37LiteralCases('test_T078_prior_association_wrong_head'),
        Worker37LiteralCases('test_T079_prior_association_missing'),
        Worker37LiteralCases('test_T080_prior_association_not_list'),
        Worker37LiteralCases('test_T081_prior_association_ambiguous'),
        Worker37LiteralCases('test_T082_frozen_historical_pr_mismatch'),
        Worker37LiteralCases('test_T083_empty_association_artifact_run_mismatch'),
        Worker37LiteralCases('test_T084_empty_association_archive_hash_mismatch'),
    ))


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(frozen_suite())
    print('WORKER37_BASH_CASE_OBSERVATIONS='+json.dumps(BASH_CASE_OBSERVATIONS,sort_keys=True,separators=(',',':')))
    sys.exit(0 if result.wasSuccessful() else 1)
