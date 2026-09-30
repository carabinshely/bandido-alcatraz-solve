"""Temporary synthetic preflight tests: no game initialization or seed execution."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import zipfile

import pytest

spec = importlib.util.spec_from_file_location(
    'worker25_preflight_under_test', Path(__file__).with_name('run_worker25_full_spent_tier_footprint.py'))
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    monkeypatch.setattr(w, 'ROOT', tmp_path)
    seed_calls = []

    def forbidden(*args, **kwargs):
        seed_calls.append(args)
        pytest.fail('research entry point reached by preflight test')

    for name in ('trace_seed', 'safe_trace', 'ProcessPoolExecutor'):
        monkeypatch.setattr(w, name, forbidden)
    monkeypatch.setattr(w.GameState, 'new', forbidden)
    changed = [1001,1009,1012,1013,1014,1015,1018,1021,1023,1024,1030,1039,1040,
               1045,1046,1047,1049,1050,1055,1066,1068,1071,1072,1075,1080,1081,
               1083,1084,1087,1091,1092,1098]
    receipt = {'v4_per_seed': [], 'v6_per_seed': []}
    for seed in w.SEEDS:
        a = b = 'deck_exhausted'
        if seed in changed:
            b = 'no_legal_move'
        if seed in (1008,1056,1097):
            a = b = 'win'
        if seed in (1017,1060,1094,1095):
            a = b = 'no_legal_move'
        if seed in (1012,1087):
            a = 'win'
        if seed in (1024,1083):
            b = 'win'
        for key, reason in [('v4_per_seed',a),('v6_per_seed',b)]:
            receipt[key].append(dict(seed=seed,won=reason=='win',reason=reason))
    archive = tmp_path/'synthetic.zip'
    baseline = dict(evaluated_commit='a463edfd2be52fe271642d5e8f07ddb008b48d6e',
                    traces=[dict(seed=s) for s in changed])
    members = {'worker24-changed-outcome-trace-audit.json': json.dumps(baseline).encode(),
               'worker24-changed-outcome-trace-summary.json': b'{}'}
    def byte_meta(data):
        return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    with zipfile.ZipFile(archive,'w') as z:
        for name,data in members.items():
            z.writestr(name,data)
    info = byte_meta(archive.read_bytes())
    provenance = dict(raw_artifact=dict(archive_bytes=info['bytes'],archive_sha256=info['sha256'],
                                       inner_files={n:byte_meta(b) for n,b in members.items()}),
                      seed_scope=changed, source_blobs={'src/model.py':'expected'})
    for name,data in [(w.PROVENANCE,provenance),(w.RECEIPT,receipt)]:
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(data))
    def git(*args):
        if args[0]=='ls-tree':
            return 'src/model.py'
        if args==('rev-parse','HEAD'):
            return 'synthetic-checkout'
        return 'expected'
    monkeypatch.setattr(w,'git',git)
    yield dict(root=tmp_path, archive=archive, receipt=receipt, provenance=provenance, git=git)
    assert seed_calls == [], 'zero-seed invariant'


def invoke(fixture, monkeypatch, *, preflight_only=False):
    output=fixture['root']/'output'
    argv=['worker25','--worker24-zip',str(fixture['archive']),'--output-dir',str(output)]
    if preflight_only:
        argv.append('--preflight-only')
    monkeypatch.setattr(sys,'argv',argv)
    with pytest.raises(SystemExit) as exc:
        w.main()
    return exc.value.code,json.loads((output/'worker25-preflight-failure.json').read_text())


def assert_invalid(result, check):
    code,receipt=result
    assert code==1
    assert receipt['classification']==w.PREFIX+'diagnostic_invalid'
    assert receipt['execution_status']=='diagnostic_invalid'
    assert check in receipt['failed_check']
    assert receipt['research_seeds_executed']==0
    assert receipt['research_interpretation'].startswith('None.')
    assert receipt['provenance']['starting_main']==w.STARTING_MAIN
    assert receipt['provenance']['checkout_commit']=='synthetic-checkout'
    assert receipt['error']['message']


@pytest.mark.parametrize('preflight_only',[False,True])
def test_archive_hash_mismatch(synthetic,monkeypatch,preflight_only):
    synthetic['archive'].write_bytes(b'corrupt input')
    result=invoke(synthetic,monkeypatch,preflight_only=preflight_only)
    assert_invalid(result,'verify_worker24_archive_bytes')
    assert result[1]['provenance']['preflight_progress']['observed_archive']['bytes']==13



def test_inner_hash_mismatch(synthetic,monkeypatch):
    meta=synthetic['provenance']['raw_artifact']['inner_files']
    meta['worker24-changed-outcome-trace-audit.json']['sha256']='0'*64
    (synthetic['root']/w.PROVENANCE).write_text(json.dumps(synthetic['provenance']))
    assert_invalid(invoke(synthetic,monkeypatch),'verify_worker24_inner_file:worker24-changed-outcome-trace-audit.json')


def test_malformed_input_schema(synthetic,monkeypatch):
    del synthetic['provenance']['raw_artifact']
    (synthetic['root']/w.PROVENANCE).write_text(json.dumps(synthetic['provenance']))
    result=invoke(synthetic,monkeypatch)
    assert_invalid(result,'read_worker24_artifact_metadata')
    assert result[1]['error']['type']=='KeyError'


def test_source_mismatch(synthetic,monkeypatch):
    original=synthetic['git']
    monkeypatch.setattr(w,'git',lambda *args:'drift' if args==('hash-object','src/model.py') else original(*args))
    result=invoke(synthetic,monkeypatch)
    assert_invalid(result,'verify_source:src/model.py')
    assert result[1]['provenance']['preflight_progress']['source_comparisons']['src/model.py']==dict(expected='expected',actual='drift')


def test_wrong_population(synthetic,monkeypatch):
    synthetic['receipt']['v4_per_seed'].pop()
    (synthetic['root']/w.RECEIPT).write_text(json.dumps(synthetic['receipt']))
    assert_invalid(invoke(synthetic,monkeypatch),'verify_worker23_population')


def test_malformed_provenance(synthetic,monkeypatch):
    (synthetic['root']/w.PROVENANCE).write_text('{')
    result=invoke(synthetic,monkeypatch)
    assert_invalid(result,'read_worker24_provenance')
    assert result[1]['error']['type']=='JSONDecodeError'


def test_corrupt_zip_with_matching_outer_hash(synthetic,monkeypatch):
    data=b'not a zip'
    synthetic['archive'].write_bytes(data)
    synthetic['provenance']['raw_artifact'].update(archive_bytes=len(data),archive_sha256=hashlib.sha256(data).hexdigest())
    (synthetic['root']/w.PROVENANCE).write_text(json.dumps(synthetic['provenance']))
    result=invoke(synthetic,monkeypatch)
    assert_invalid(result,'verify_worker24_archive_contents')
    assert result[1]['error']['type']=='BadZipFile'


@pytest.mark.parametrize('kind',['missing','inaccessible'])
def test_unavailable_archive_is_blocker(synthetic,monkeypatch,kind):
    if kind=='missing':
        synthetic['archive'].unlink()
    else:
        original=Path.read_bytes
        def read_bytes(path):
            if path==synthetic['archive']:
                raise PermissionError('synthetic inaccessible input')
            return original(path)
        monkeypatch.setattr(Path,'read_bytes',read_bytes)
    code,receipt=invoke(synthetic,monkeypatch)
    assert code==2
    assert receipt['classification'] is None
    assert receipt['execution_status']=='execution_blocked'
    assert receipt['failed_check']=='read_worker24_archive'
    assert receipt['research_seeds_executed']==0


def test_valid_preflight_only_remains_zero_seed(synthetic,monkeypatch,capsys):
    monkeypatch.setattr(sys,'argv',['worker25','--worker24-zip',str(synthetic['archive']),'--preflight-only'])
    w.main()
    assert json.loads(capsys.readouterr().out)['research_seeds_executed']==0
    assert not (synthetic['root']/'artifacts/raw/worker25/worker25-preflight-failure.json').exists()


def test_workflow_always_uploads_failure_receipt_directory():
    workflow=(Path(__file__).resolve().parents[1]/'.github/workflows/worker25-full-spent-tier-footprint.yml').read_text()
    upload=workflow.split('      - name: Upload evidence',1)[1]
    assert 'if: always()' in upload
    assert 'path: artifacts/raw/worker25/' in upload
