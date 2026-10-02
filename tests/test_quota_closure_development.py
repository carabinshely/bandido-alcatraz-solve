"""Worker35 harness preflight: invented cards/receipts only, no game execution."""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from random import Random
import sys
import time
from unittest.mock import patch
import zipfile
import io

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('worker35_harness_test', ROOT / 'scripts/run_quota_reserve_closure_development.py')
h = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = h
spec.loader.exec_module(h)
r = h.bounded


def freeze():
    caps = {k: 10000 for k in (*r.OPS, 'roots')}
    caps.update(wall_seconds=15, cpu_seconds=15)
    return {'schema': 'worker35-execution-freeze-v1', 'preregistration_url': h.PREREGISTRATION_URL,
        'baseline_commit': h.BASELINE_COMMIT, 'baseline_source_blobs': {'data/invented.json': '1' * 40},
        'execution_source_sha256': {'scripts/invented.py': '2' * 64},
        'runtime': {'implementation': 'CPython', 'version': '3.11.16', 'executable_sha256': '3' * 64},
        'resources': {'per_call': {scope: dict(caps) for scope in r.SCOPES},
            'total_operations': {k: 1000000 for k in r.OPS},
            'cohort_wall_seconds': 100, 'verification_wall_seconds': 100,
            'address_space_bytes': 2 * 1024 ** 3, 'evidence_bytes': 4 * 1024 ** 2,
            'trace_bytes': 1024 ** 2, 'line_bytes': 512 * 1024, 'receipt_bytes': 128 * 1024,
            'shard_bytes': 4096, 'archive_bytes': 1024 ** 2},
        'reviews': {k: 'required-clean-exact-head-before-go' for k in ('candidate','reference','harness','independent_a','independent_b')},
        'synthetic_preflight_sha256': '4' * 64}


@pytest.fixture(autouse=True)
def config(monkeypatch):
    monkeypatch.setattr(h, 'FREEZE', freeze())
    monkeypatch.setattr(h, 'FREEZE_SHA256', '5' * 64)
    monkeypatch.setattr(h, 'BUDGET', None)
    monkeypatch.setattr(h, 'EXECUTION_ACTIVE', False)


def event():
    go = {'head': '6' * 40, 'tree': '7' * 40, 'freeze_sha256': '5' * 64,
          'execution_go_url': 'https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-123'}
    return {'action': 'edited', 'changes': {'body': {'from': 'Draft preflight only'}},
        'repository': {'full_name': h.REPOSITORY}, 'sender': {'login': 'carabinshely'},
        'pull_request': {'draft': True, 'state': 'open', 'user': {'login': 'carabinshely'},
            'body': h.MARKER + '\n' + json.dumps(go) + '\n' + h.END_MARKER,
            'head': {'sha': go['head'], 'ref': h.BRANCH, 'repo': {'full_name': h.REPOSITORY}},
            'base': {'repo': {'full_name': h.REPOSITORY}}}}


def invented():
    from bandido_alcatraz.board import Board
    from bandido_alcatraz.game import GameState
    from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
    from bandido_alcatraz.setup import SOLO_EASY
    from bandido_alcatraz.quota_reserve_closure import QuotaReserveClosurePolicy
    from bandido_alcatraz.quota_reserve_closure_reference import QuotaReserveClosureReference
    N,E,S,W = Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST
    def card(name, edges=(), material=None, exit=False):
        return CardDefinition(name, (CellSpec(0, 0, frozenset(edges), False),), material, exit)
    start = CardDefinition('start_easy', (CellSpec(0,0,frozenset((W,N,E))), CellSpec(1,0,frozenset((W,N,E,S)))))
    cards = [card(f'coat-{i}',(W,),Material.RAINCOAT) for i in range(12)]
    cards += [card(f'rope-{i}',(W,),Material.ROPE) for i in range(8)]
    cards += [card(f'plain-{i}') for i in range(48)]
    exit_card = card('exit', (W,), exit=True)
    cards.append(exit_card)
    catalog = tuple(cards)
    hand = [cards[0], *cards[20:25]]
    board = Board(); board.seed(start)
    state = GameState(board=board, draw_pile=[c for c in cards if c not in hand], hand=hand, setup=SOLO_EASY)
    options = dict(catalog=catalog, start_card=start, exit_card=exit_card)
    return state, catalog, QuotaReserveClosurePolicy(**options), QuotaReserveClosureReference(**options)


def wrapper(tmp_path, pass_number=2):
    from bandido_alcatraz.quota_reserve_closure import OperationLimits
    from bandido_alcatraz.quota_reserve_closure_reference import OperationLimits as ReferenceLimits
    from bandido_alcatraz.policies import BoundedMergeV4Policy
    state, catalog, policy, reference = invented()
    output = tmp_path / 'evidence'; output.mkdir()
    caps = h.FREEZE['resources']['per_call']
    audited = h.AuditPolicy(policy if pass_number != 1 else BoundedMergeV4Policy(250), reference=reference,
        catalog=catalog, output=output, pass_number=pass_number, seed=11, limits=caps,
        candidate_limits=OperationLimits(**{k:caps['candidate'][k] for k in r.OPS}),
        reference_limits=ReferenceLimits(**{k:caps['reference'][k] for k in r.OPS}), state_provider=lambda:state)
    return audited, state, output


def test_mandatory_complete_frozen_config_no_none_or_boolean_caps():
    assert r.validate_freeze(freeze())['schema'] == 'worker35-execution-freeze-v1'
    for change in ('missing', 'none', 'bool', 'zero'):
        value=freeze()
        if change=='missing': del value['resources']['per_call']['reference']['wall_seconds']
        else: value['resources']['per_call']['reference']['wall_seconds']={'none':None,'bool':True,'zero':0}[change]
        with pytest.raises(ValueError): r.validate_freeze(value)
    value=freeze(); value['resources']['shard_bytes']=31*1024**2
    with pytest.raises(ValueError):r.validate_freeze(value)
    value=freeze();value['runtime']['version']='3.11'
    with pytest.raises(ValueError):r.validate_freeze(value)


def test_strict_json_rejects_duplicate_or_nonfinite():
    for value in ('{"a":1,"a":2}', '{"v":NaN}', '{"v":1e999}'):
        with pytest.raises(ValueError):r.strict_json(value)


def test_exact_edited_admission_and_failed_transition_cases():
    good=event(); assert h.admission(good,'6'*40,'5'*64)['tree']=='7'*40
    changes = [lambda e:e.update(action='opened'),
        lambda e:e['changes']['body'].update({'from':h.MARKER}),
        lambda e:e['sender'].update(login='outsider'),
        lambda e:e['pull_request']['head'].update(ref='main'),
        lambda e:e['pull_request']['head'].update(sha='a'*40),
        lambda e:e['pull_request']['base']['repo'].update(full_name='other/repo'),
        lambda e:e['pull_request'].update(draft=False),
        lambda e:e['pull_request'].update(body=e['pull_request']['body']+'\n'+h.MARKER),
        lambda e:e['pull_request'].update(body=e['pull_request']['body'].replace('"head":','"head":"x","head":'))]
    for mutate in changes:
        bad=copy.deepcopy(good);mutate(bad)
        with pytest.raises(ValueError):h.admission(bad,'6'*40,'5'*64)


def test_exclusive_receipt_and_admission_guard(tmp_path):
    out=tmp_path/'attempt'/'1';out.parent.mkdir()
    h.initialize(out,'6'*40,h.PREREGISTRATION_URL)
    original=(out/'receipt.json').read_bytes()
    with pytest.raises(FileExistsError):h.initialize(out,'6'*40,h.PREREGISTRATION_URL)
    assert (out/'receipt.json').read_bytes()==original
    go=h.admission(event(),'6'*40,'5'*64)
    h.claim_admission(out,'6'*40,go)
    with pytest.raises(FileExistsError):h.claim_admission(out,'6'*40,go)


def test_direct_game_compute_is_blocked_before_import(tmp_path):
    with pytest.raises(h.IntegrityError,match='admitted bounded run'):
        h.one_game(1000000,output=tmp_path,pass_number=1)


@pytest.mark.parametrize('pass_number',[1,2])
def test_actual_synthetic_boundary_independent_rng_science_cost_and_dedup(tmp_path,pass_number):
    audit,state,out=wrapper(tmp_path,pass_number)
    before=h.state_witness(state,audit.catalog)[0]
    chosen=audit.choose(state.observation(),Random(11))
    assert chosen is not None
    events=h.read_trace(audit.path)
    assert [e['event'] for e in events]==['decision_started','decision_completed']
    completed=events[1]['audit'];boundary=completed['boundary']
    assert boundary['engine_before']==boundary['engine_after']==before
    assert boundary['choice_calls']==1
    calls=h.read_trace(audit.calls_path)
    metrics=h.read_trace(out/'resource-metrics.jsonl')
    assert [m['scope'] for m in metrics]==(['control'] if pass_number==1 else ['candidate','reference'])
    assert all(m['status']=='returned' for m in metrics)
    if pass_number==2:
        assert completed['scientific_sha256']==completed['reference_scientific_sha256']==h.digest(calls[0]['result']['scientific'])
        assert 'scientific' not in calls[1]['result'] and 'scientific' not in completed
        assert calls[0]['result']['cost']==metrics[0]['cost']
        assert calls[1]['result']['cost']==metrics[1]['cost']


def test_reference_disagreement_preserves_full_both_sides(tmp_path):
    audit,state,out=wrapper(tmp_path)
    original=audit.reference.evaluate
    def bad(*args,**kwargs):
        move,science,cost=original(*args,**kwargs);science['flags']['closure_branch_selected']=False
        return move,science,cost
    audit.reference.evaluate=bad
    with pytest.raises(h.IntegrityError,match='scientific audit disagreement'):
        audit.choose(state.observation(),Random(11))
    calls=h.read_trace(audit.calls_path)
    assert len(calls)==2 and 'scientific' in calls[0]['result'] and 'scientific' in calls[1]['result']
    assert len(h.read_trace(audit.path))==1


def test_public_and_real_state_mutation_are_explicit(tmp_path):
    audit,state,out=wrapper(tmp_path,1)
    original=audit.policy.choose
    def mutate(observation,rng):
        result=original(observation,rng);state.ropes=1;return result
    audit.policy.choose=mutate
    with pytest.raises(h.IntegrityError,match='real game state'):
        audit.choose(state.observation(),Random(11))
    assert len(h.read_trace(audit.path))==2


def test_failure_precedence_never_negative_screen():
    receipt={'status':'running','errors':[],'classification':'no_advancement','summary':{}}
    h.fail(receipt,r.ResourceExceeded('cap'),'call')
    assert receipt['status']=='resource_incomplete' and receipt['classification'] is None and 'summary' not in receipt
    h.fail(receipt,h.IntegrityError('mismatch'),'audit')
    h.fail(receipt,OSError('lost output'),'file')
    assert receipt['status']=='integrity_invalid' and not receipt['research_interpretation_performed']


def test_append_budget_keeps_prefix_and_receipt_reserve(tmp_path,monkeypatch):
    limits=freeze()['resources'];limits.update(evidence_bytes=150,receipt_bytes=50,line_bytes=100,trace_bytes=100)
    budget=r.EvidenceBudget(tmp_path,limits);monkeypatch.setattr(h,'BUDGET',budget)
    path=tmp_path/'partial.jsonl';h.append_jsonl(path,{'prefix':'x'*40});before=path.read_bytes()
    with pytest.raises(r.ResourceExceeded):h.append_jsonl(path,{'excess':'x'*40})
    assert path.read_bytes()==before
    h.write_json(tmp_path/'receipt.json',{'status':'resource_incomplete'})


def test_nested_deadline_restores_prior_alarm():
    import signal
    previous=signal.getsignal(signal.SIGALRM)
    with pytest.raises(r.ResourceExceeded):
        with r.deadline(.01,'invented wait'):time.sleep(.05)
    assert signal.getsignal(signal.SIGALRM)==previous and signal.getitimer(signal.ITIMER_REAL)[0]==0


def test_physical_meter_restores_prior_hook_on_cap_failure():
    from bandido_alcatraz import moves
    state,*unused=invented()
    seen=[]
    def prior(frame,event,arg):
        if frame.f_code is moves.legal_moves.__code__ and event=='call':seen.append('legal')
    old=sys.getprofile();sys.setprofile(prior)
    try:
        with pytest.raises(r.ResourceExceeded):
            with r.Meter(call_caps={k:0 for k in r.OPS}):state.observation().legal_moves()
        assert sys.getprofile() is prior and seen==['legal']
    finally:sys.setprofile(old)


def test_sharding_exact_reassembly_and_exclusive_destination(tmp_path):
    source=tmp_path/'raw';source.mkdir();(source/'trace.jsonl').write_bytes(b'{"invented":true}\n'*1000)
    limits=freeze()['resources'];limits['shard_bytes']=50;target=tmp_path/'transport'
    manifest=r.package_evidence(source,target,limits)
    archive=b''.join((target / p['name']).read_bytes() for p in manifest['parts'])
    assert len(manifest['parts'])>1
    assert all(p['size_bytes']<=limits['shard_bytes'] for p in manifest['parts'])
    assert hashlib.sha256(archive).hexdigest()==manifest['archive']['sha256']
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        assert z.read('trace.jsonl')==(source/'trace.jsonl').read_bytes()
    with pytest.raises(FileExistsError):r.package_evidence(source,target,limits)


def test_no_population_or_setup_cli_and_fixed_three_pass_order():
    assert h.SEEDS==tuple(range(1000000,1000400)) and h.PASSES==(1,2,3) and h.MAX_STEPS==1000
    text=Path(h.__file__).read_text()
    assert 'parser.add_argument("--seed"' not in text
    assert h.BASELINE_COMMIT=='c50a7ab8e73eaf3c497c5d1c9fef5cbe53261853'
    assert h.CONTROL_ARRAY_SHA256=='a4d2d06e5592caa35c03d00337d0254c07f767d5cb8ee0777cbb51f543803021'


def test_routine_edit_skips_without_freeze_or_guard(tmp_path,monkeypatch):
    event_path=tmp_path/'event.json';event_path.write_text(json.dumps({'action':'edited','pull_request':{'body':'normal edit'},'changes':{'body':{'from':'old'}}}))
    output=tmp_path/'github-output';monkeypatch.setenv('GITHUB_EVENT_PATH',str(event_path));monkeypatch.setenv('GITHUB_OUTPUT',str(output))
    never=tmp_path/'never-created'
    assert h.main(['admit','--output-dir',str(never),'--expected-head','6'*40,
        '--preregistration-url',h.PREREGISTRATION_URL,'--freeze',str(tmp_path/'missing-freeze.json')])==0
    assert output.read_text()=='admitted=false\n' and not never.exists()


def test_source_byte_identity_excludes_only_runtime_fields():
    a={k:'same' for k in ('head','tree','baseline_commit','source_blobs','execution_blobs','execution_sha256')}
    a['python_version']='bootstrap';b=dict(a,python_version='3.11.16')
    assert h.same_source_bytes(a,b)
    for key in ('head','tree','source_blobs','execution_blobs','execution_sha256'):
        c=dict(b);c[key]='changed';assert not h.same_source_bytes(a,c)


def test_memory_ceiling_uses_exact_frozen_limit_not_implicit_default(monkeypatch):
    called=[]
    monkeypatch.setattr(r.resource,'getrlimit',lambda kind:(4096,4096) if called else (-1,-1))
    monkeypatch.setattr(r.resource,'setrlimit',lambda kind,value:called.append(value))
    assert r.enforce_memory(4096)=={'mechanism':'RLIMIT_AS','soft':4096,'hard':4096}
    assert called==[(4096,4096)]


def test_cpu_deadline_is_hard_and_restores_profile_signal():
    import signal
    previous=signal.getsignal(signal.SIGPROF)
    with pytest.raises(r.ResourceExceeded):
        with r.cpu_deadline(.01,'invented CPU'):
            while True:pass
    assert signal.getsignal(signal.SIGPROF)==previous and signal.getitimer(signal.ITIMER_PROF)[0]==0


def test_archive_resource_stop_preserves_written_shards_and_all_raw_bytes(tmp_path):
    source=tmp_path/'raw';source.mkdir();raw=bytes(range(256))*400;(source/'invented.bin').write_bytes(raw)
    limits=freeze()['resources'];limits.update(shard_bytes=50,archive_bytes=100)
    target=tmp_path/'transport'
    with pytest.raises(r.ResourceExceeded):r.package_evidence(source,target,limits)
    assert (source/'invented.bin').read_bytes()==raw
    assert list(target.glob('evidence.part-*')) and not (target/'artifact-manifest.json').exists()


def test_native_profile_hook_not_destroyed():
    import cProfile
    profile=cProfile.Profile();profile.enable()
    try:
        prior=sys.getprofile()
        if prior is None or callable(prior):pytest.skip('runtime does not expose noncallable active C profiler')
        with pytest.raises(ValueError,match='native profile'):
            with r.Meter():pass
        assert sys.getprofile() is prior
    finally:profile.disable()


def test_workflow_benchmark_pipefail_unique_receipt_and_bounded_individual_uploads():
    text=(ROOT/'.github/workflows/quota-reserve-closure-development.yml').read_text()
    assert 'set -euo pipefail' in text and 'shell: bash' in text
    assert 'worker35-synthetic-resource-${{ github.run_id }}-${{ github.run_attempt }}.jsonl' in text
    assert '| tee "$BENCHMARK_OUTPUT"' in text
    assert "steps.benchmark.outcome != 'skipped'" in text
    assert 'tests/test_verify_worker35_development.py' in text
    assert 'part: ${{ fromJSON(needs.development.outputs.parts) }}' in text
    assert '${{ matrix.part }}' in text and 'compression-level: 0' in text
    assert 'cancel-in-progress: false' in text


@pytest.mark.parametrize('scope', ['candidate', 'reference'])
def test_returned_science_is_durable_before_post_return_root_cap(tmp_path, scope):
    audit, state, output = wrapper(tmp_path)
    audit.limits[scope]['roots'] = 1
    with pytest.raises(r.ResourceExceeded, match='root ceiling'):
        audit.choose(state.observation(), Random(11))
    rows = h.read_trace(audit.calls_path)
    assert [row['scope'] for row in rows] == (['candidate'] if scope == 'candidate' else ['candidate','reference'])
    assert len(rows[0]['result']['scientific']['roots']) == 6
    assert h.read_trace(output/'resource-metrics.jsonl')[-1]['status'] == 'failed'


def test_returned_science_survives_metrics_write_failure(tmp_path, monkeypatch):
    audit, state, output = wrapper(tmp_path)
    def unavailable(*args):raise OSError('invented metrics write unavailable')
    monkeypatch.setattr(h, 'append_metrics', unavailable)
    with pytest.raises(OSError, match='metrics write'):
        audit.choose(state.observation(), Random(11))
    rows=h.read_trace(audit.calls_path)
    assert len(rows)==1 and len(rows[0]['result']['scientific']['roots'])==6


def test_returned_science_precedes_post_return_cpu_check(tmp_path, monkeypatch):
    from contextlib import contextmanager
    @contextmanager
    def no_cpu_alarm(*args):
        yield
    stamp=[0.0]
    monkeypatch.setattr(h.time, 'process_time', lambda:stamp[0])
    monkeypatch.setattr(r, 'cpu_deadline', no_cpu_alarm)
    caps=dict(freeze()['resources']['per_call']['candidate'], cpu_seconds=1)
    result=(None, {'roots':[],'invented':'fully returned'}, {'roots':0})
    def invoke():stamp[0]=2.0;return result
    path=tmp_path/'calls.jsonl'
    with pytest.raises(r.ResourceExceeded,match='CPU ceiling'):
        h.decision_runtime(tmp_path,2,11,1,'candidate',invoke,Random(11),caps,
            lambda value,cost,meter:h.append_jsonl(path,{'scientific':value[1]}))
    assert h.read_trace(path)==[{'scientific':result[1]}]


def test_reader_writer_offline_verifier_artifact_class_parity(tmp_path, monkeypatch):
    caps=freeze()['resources'];caps.update(trace_bytes=100,line_bytes=100,evidence_bytes=10000,receipt_bytes=100)
    monkeypatch.setattr(h,'FREEZE',{'resources':caps})
    monkeypatch.setattr(h,'BUDGET',r.EvidenceBudget(tmp_path,caps))
    spec=importlib.util.spec_from_file_location('worker35_bound_parity',ROOT/'scripts/verify_worker35_development.py')
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    offline=object.__new__(verifier.Evidence);offline.resources=caps
    for name in ('resource-metrics.jsonl','call-results/pass-2/invented.jsonl','completed.jsonl'):
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True)
        for i in range(10):h.append_jsonl(path,{'metric':i,'fixture':True})
        assert path.stat().st_size>caps['trace_bytes']
        assert len(h.read_trace(path))==10
        assert r.jsonl_limit(path,caps)==offline.limit(name)==caps['evidence_bytes']
    trace=tmp_path/'decision-traces'/'pass-2'/'invented.jsonl';trace.parent.mkdir(parents=True)
    assert r.jsonl_limit(trace,caps)==offline.limit('decision-traces/pass-2/invented.jsonl')==100
    with pytest.raises(r.ResourceExceeded):
        for i in range(10):h.append_jsonl(trace,{'metric':i,'fixture':True})
    too_long=tmp_path/'too-long.jsonl';too_long.write_bytes(b'{"x":"'+b'x'*100+b'"}\n')
    with pytest.raises(r.ResourceExceeded):list(h.iter_jsonl(too_long))


def _benchmark_module():
    spec=importlib.util.spec_from_file_location('worker35_benchmark_regression',ROOT/'scripts/benchmark_worker35_synthetic.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('site',['decision','cohort','benchmark'])
@pytest.mark.parametrize('entry',['meter','contextlib'])
def test_all_production_meter_callers_restore_retained_entry_exception(tmp_path,monkeypatch,site,entry):
    import contextlib
    import signal
    target=r.Meter.__enter__.__code__ if entry=='meter' else contextlib._GeneratorContextManager.__enter__.__code__
    if site=='decision':
        audit,state,output=wrapper(tmp_path)
        work=lambda:audit.choose(state.observation(),Random(11))
    elif site=='benchmark':
        audit,state,output=wrapper(tmp_path)
        benchmark=_benchmark_module()
        work=lambda:benchmark.measure_wrapper(audit,state,{k:100000 for k in r.OPS},15)
    else:
        import worker31_geometry as geometry
        output=tmp_path/'attempt';receipt=h.initialize(output,'6'*40,h.PREREGISTRATION_URL)
        receipt['source_at_initialization']={'source_blobs':{}};h.write_json(output/'receipt.json',receipt)
        monkeypatch.setattr(h,'preflight',lambda *args:{'source_blobs':{}})
        monkeypatch.setattr(h,'verify_source',lambda *args:{'source_blobs':{}})
        monkeypatch.setattr(h,'observed_source_snapshot',lambda:{})
        monkeypatch.setattr(r,'enforce_memory',lambda n:{'mechanism':'invented','soft':n,'hard':n})
        monkeypatch.setattr(geometry,'load_cards',lambda *args:{})
        def forbidden_game(*args,**kwargs):raise AssertionError('game execution forbidden in preflight')
        monkeypatch.setattr(h,'one_game',forbidden_game)
        work=lambda:h.run(output,'6'*40,h.PREREGISTRATION_URL)
    previous=sys.getprofile();hits=[];problem=RuntimeError('retained invented entry failure')
    def hook(frame,event,arg):
        if event=='return' and frame.f_code is target and sys.getprofile() is not hook and not hits:
            hits.append(event);raise problem
    sys.setprofile(hook)
    try:
        if site=='cohort':assert work()==1
        else:
            with pytest.raises(RuntimeError) as caught:work()
            assert caught.value is problem
        assert hits and problem.__traceback__ is not None
        assert sys.getprofile() is hook
        assert signal.getitimer(signal.ITIMER_REAL)[0]==0
        assert signal.getitimer(signal.ITIMER_PROF)[0]==0
    finally:sys.setprofile(previous)


def test_exact_three_hook_wrapper_benchmark_includes_journal_fsync(tmp_path):
    audit,state,output=wrapper(tmp_path)
    benchmark=_benchmark_module()
    result=benchmark.measure_wrapper(audit,state,{k:100000 for k in r.OPS},15)
    metrics=h.read_trace(output/'resource-metrics.jsonl')
    assert [row['scope'] for row in metrics]==['candidate','reference']
    assert result['operations']=={k:sum(row['cost'][k] for row in metrics) for k in r.OPS}
    assert audit.path.stat().st_size>0 and audit.calls_path.stat().st_size>0
    assert len(h.read_trace(audit.path))==2


@pytest.mark.parametrize('damage',['corrupt','missing','identity'])
def test_quarantined_packaging_preserves_complete_raw_prefix(tmp_path,monkeypatch,damage):
    output=tmp_path/'attempt';output.mkdir()
    original=None
    if damage=='corrupt':original=b'{corrupt'
    if damage=='identity':original=r.canonical({'worker':999,'errors':[],'status':'initialized'})
    if original is not None:(output/'receipt.json').write_bytes(original)
    (output/'recovery-receipt-existing.json').write_bytes(b'{"status":"integrity_invalid"}\n')
    trace=output/'decision-traces'/'pass-2'/'11.jsonl';trace.parent.mkdir(parents=True)
    raw=b'{"event":"decision_started","invented":true}\n';trace.write_bytes(raw)
    github_output=tmp_path/'github-output';monkeypatch.setenv('GITHUB_OUTPUT',str(github_output))
    assert h.package_attempt(output,'6'*40,h.PREREGISTRATION_URL,h.admission(event(),'6'*40,'5'*64))==1
    assert (output/'receipt.json').read_bytes()==original if original is not None else not (output/'receipt.json').exists()
    transport=output.with_name('attempt-transport');manifest=json.loads((transport/'artifact-manifest.json').read_bytes())
    packed=b''.join((transport/item['name']).read_bytes() for item in manifest['parts'])
    with zipfile.ZipFile(io.BytesIO(packed)) as archive:
        assert archive.read('decision-traces/pass-2/11.jsonl')==raw
        assert archive.read('recovery-receipt-existing.json')==b'{"status":"integrity_invalid"}\n'
        if original is not None:assert archive.read('receipt.json')==original
        quarantined=[name for name in archive.namelist() if name.startswith('recovery-receipt-quarantined-')]
        assert len(quarantined)==1
        receipt=json.loads(archive.read(quarantined[0]))
        assert receipt['quarantined'] and receipt['classification'] is None and not receipt['research_interpretation_performed']
    assert 'parts=' in github_output.read_text()
