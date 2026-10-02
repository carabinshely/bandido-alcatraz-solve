"""Synthetic fixtures ONLY. Never load selected observations or execute their search."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from itertools import count
import json
import os
from pathlib import Path
from random import Random
import shutil
import subprocess
import sys
import time
import pytest
from bandido_alcatraz.board import Board
from bandido_alcatraz.game import GameState
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
from bandido_alcatraz.setup import SOLO_EASY, GameSetup
from bandido_alcatraz.strategy import preview_move_without_draw
from bandido_alcatraz.worker32.candidate import Candidate, prevalidated_preview, ranking
from bandido_alcatraz.worker32.reference import Reference, reference_key
from bandido_alcatraz.worker32.evidence import observation, canonical, sha, BudgetExceeded
from bandido_alcatraz.worker32.runtime import (validate_science,validate_envelope,installed_tree,
    durable,run_group,failure_status,strict_departure,finalize,runner_guard)
from bandido_alcatraz.worker32.inputs import ExecutionBlocked,checked,reconstruct,selector_module


def card(name, edges=(), material=None, exit=False, water=False):
    return CardDefinition(name,(CellSpec(0,0,frozenset(edges),water=water),),material,exit)


def state(hand=(), coats=0, ropes=0):
    board = Board(); board.seed(card('start_easy',[Direction.EAST]))
    return GameState(board,[],list(hand),raincoats=coats,ropes=ropes,setup=SOLO_EASY)


class CountingRandom(Random):
    def __init__(self):
        super().__init__(0); self.calls=0
    def choice(self,seq):
        self.calls+=1
        return super().choice(seq)


@pytest.mark.parametrize('coats,ropes',[(0,0),(2,1),(3,2)])
@pytest.mark.parametrize('hand',[
    (), (card('a',material=Material.ROPE),),
    (card('a',[Direction.WEST]),),
    (card('a',[Direction.EAST,Direction.WEST]),card('b',material=Material.RAINCOAT)),
    (card('exit',[Direction.WEST],exit=True),card('r',material=Material.ROPE)),
    (card('wet',[Direction.WEST,Direction.EAST],water=True),card('cover',[Direction.WEST])),
])
def test_independent_complete_science(hand,coats,ropes):
    obs=state(hand,coats,ropes).observation(); before=canonical(observation(obs))
    a,b=CountingRandom(),CountingRandom()
    _,x,cost=Candidate().evaluate(obs,a)
    _,y,refcost=Reference().evaluate(obs,b)
    assert canonical(x)==canonical(y)
    validate_science(x); validate_science(y)
    assert a.calls==b.calls==bool(obs.legal_moves())
    assert before==canonical(observation(obs))
    assert refcost['physical_legal_moves']==cost['physical_legal_moves']+x['counts']['previews']
    for root in x['roots']:
        if root['second_moves']:
            assert all(len(l['sequence'])==2 for l in root['leaves'])


def test_adapter_every_synthetic_successor_private_isolation():
    s=state([card('wet',[Direction.WEST,Direction.EAST],water=True),
             card('cover',[Direction.WEST,Direction.EAST]),card('coat',material=Material.RAINCOAT),
             card('exit',[Direction.WEST],exit=True)])
    class Poison:
        def __iter__(self): raise AssertionError('private read')
        def __bool__(self): raise AssertionError('private read')
    obs=s.observation(); s.draw_pile=Poison(); s.face_down_set_aside=Poison()
    before=sha(observation(obs)); types=set(); overlay=False
    for m in obs.legal_moves():
        types.add(m.action.value)
        a=prevalidated_preview(s,m,obs.legal_moves())
        b=preview_move_without_draw(obs,m).successor
        assert observation(a)==observation(b)
        assert not a.draw_pile and not a.face_down_set_aside
        for n in a.legal_moves():
            aa=prevalidated_preview(a,n,a.legal_moves())
            bb=preview_move_without_draw(b,n).successor
            assert observation(aa)==observation(bb)
            overlay |= any(p.overlaps for p in aa.board.placements)
    assert types=={'place','collect'} and overlay
    assert sha(observation(obs))==before


@pytest.mark.parametrize('impl',[Candidate,Reference])
def test_budget_before_next_preview_no_rng(monkeypatch,impl):
    module=sys.modules[impl.__module__]
    monkeypatch.setattr(module,'LIMIT',1)
    rng=CountingRandom()
    with pytest.raises(BudgetExceeded):
        impl().evaluate(state([card('a',material=Material.ROPE),card('b',material=Material.RAINCOAT)]).observation(),rng)
    assert rng.calls==0


@pytest.mark.parametrize('impl',[Candidate,Reference])
def test_input_rejection(impl):
    s=state(); obs=s.observation()
    for bad in (s,replace(obs,raincoats=True),replace(obs,ropes=3),replace(obs,setup=GameSetup(hand_size=3)),replace(obs,hand=tuple(card(str(i)) for i in range(7)))):
        with pytest.raises(ValueError): impl().evaluate(bad,Random(0))


def test_terminal_depth_and_dead_end():
    o=state([card('exit',[Direction.WEST],exit=True)],3,2).observation()
    p=Candidate().evaluate(o,Random(0))[1]
    assert any(l['key']==[2,-1,0] for r in p['roots'] for l in r['leaves'])
    o=state([card('coat',material=Material.RAINCOAT)]).observation()
    p=Candidate().evaluate(o,Random(0))[1]
    assert p['roots'][0]['leaves'][0]['reason']=='omitted_draw_dead_end'
    assert p['roots'][0]['maximum'][0]==1


def test_digest_and_coverage_tampering():
    p=Candidate().evaluate(state([card('a',material=Material.ROPE)]).observation(),Random(0))[1]
    p['counts']['previews']+=1
    with pytest.raises(ValueError): validate_science(p)


def test_real_git_installed_tree(tmp_path):
    repo=tmp_path/'repo'; repo.mkdir()
    def git(*args):
        return subprocess.check_output(['git','-C',str(repo),*args]).decode().strip()
    git('init','-q'); git('config','user.email','synthetic@example.invalid'); git('config','user.name','Synthetic')
    src=repo/'src/bandido_alcatraz'; src.mkdir(parents=True)
    (src/'__init__.py').write_text('# synthetic installed package\n')
    (repo/'data').mkdir(); (repo/'data/fixture.json').write_text('{}')
    git('add','.'); git('commit','-qm','synthetic baseline'); base=git('rev-parse','HEAD')
    (src/'diagnostic.py').write_text('# synthetic addition\n')
    git('add','.'); git('commit','-qm','synthetic implementation'); head=git('rev-parse','HEAD')
    target=tmp_path/'installed'; shutil.copytree(repo/'src',target)
    assert installed_tree(repo,target,head,base)['head']==head
    (target/'bandido_alcatraz/diagnostic.py').write_text('corrupt')
    with pytest.raises(ValueError,match='installed'): installed_tree(repo,target,head,base)
    shutil.copyfile(src/'diagnostic.py',target/'bandido_alcatraz/diagnostic.py')
    (target/'bandido_alcatraz/injected.py').write_text('')
    with pytest.raises(ValueError,match='module set'): installed_tree(repo,target,head,base)
    (target/'bandido_alcatraz/injected.py').unlink()
    (src/'__init__.py').write_text('changed canonical'); git('add','.'); git('commit','-qm','bad model')
    with pytest.raises(ValueError,match='canonical'): installed_tree(repo,target,git('rev-parse','HEAD'),base)


def test_timeout_and_preserved_evidence(tmp_path):
    durable(tmp_path/'result.json',{'synthetic':True})
    with pytest.raises(FileExistsError): durable(tmp_path/'result.json',{})
    with pytest.raises(TimeoutError):
        run_group([sys.executable,'-c','import time; time.sleep(30)'],tmp_path/'log',timeout=.1,grace=.1)
    finalize(tmp_path)
    assert json.loads((tmp_path/'inventory.json').read_text())['files']['result.json']['size_bytes']>0
    assert failure_status(BudgetExceeded())=='resource_incomplete'
    assert failure_status(ExecutionBlocked())=='execution_blocked'
    assert failure_status(ValueError())=='integrity_invalid'


def test_runner_guard_rejects_cloud(monkeypatch,tmp_path):
    monkeypatch.delenv('RUNNER_NAME',raising=False)
    with pytest.raises(ExecutionBlocked): runner_guard(tmp_path)


def test_byte_gate():
    with pytest.raises(ValueError): checked(b'bad',(3,'0'*64))


def test_reconstruction_and_baseline_synthetic_history():
    from bandido_alcatraz.worker32.inputs import baseline_gate
    from bandido_alcatraz.worker32.evidence import move
    from bandido_alcatraz.policies import BoundedMergeV4Policy
    from bandido_alcatraz.strategy import score_move_no_draw
    root=Path(__file__).resolve().parents[1]
    parser=selector_module((root/'experiments/visible-two-action-diagnostic/select_public_snapshots.py').read_bytes())
    coat=card('coat',material=Material.RAINCOAT); rope=card('rope',material=Material.ROPE)
    s=state([coat,rope]); s.apply(next(m for m in s.legal_moves() if m.hand_index==0))
    value=observation(s.observation())
    cards={c.card_id:c for c in (card('start_easy',[Direction.EAST]),coat,rope)}
    obs=reconstruct(value,cards,parser)
    legal=obs.legal_moves(); scores=[score_move_no_draw(obs,m,BoundedMergeV4Policy(250).weights) for m in legal]
    tier=[move(m) for m,v in zip(legal,scores) if v==max(scores)]
    audit=dict(legal_move_count=len(legal),primary_score=max(scores),primary_tier=tier,primary_tier_sha256=sha(tier))
    entry={'B':len(legal),'C':len(obs.board.cells)}
    baseline=baseline_gate(obs,entry,audit)
    assert baseline['root_moves_sha256']==sha([move(m) for m in legal])
    assert baseline['legal_move_count']==len(legal)
    with pytest.raises(ValueError): baseline_gate(obs,entry,{**audit,'primary_score':-999999})
    value['board']['cells'][0]['water']=True
    with pytest.raises(ValueError,match='reconstructed'): reconstruct(value,cards,parser)
    value=observation(s.observation());value['raincoats']=2
    with pytest.raises(ValueError,match='equipment'): reconstruct(value,cards,parser)


def test_strict_set_departure_not_arbitrary_choice():
    place={'action':'place'}; collect={'action':'collect'}
    p={'maximal_roots':[place],'best':[1,0,10],
       'roots':[{'root':place,'maximum':[1,0,10]},{'root':collect,'maximum':[1,0,9]}]}
    assert strict_departure(p,{'tier':[collect]})
    assert not strict_departure(p,{'tier':[collect,place]})
    p['maximal_roots']=[place,collect]
    assert not strict_departure(p,{'tier':[collect]})
    p['maximal_roots']=[place];p['best']=[1,0,9]
    assert not strict_departure(p,{'tier':[collect]})


def test_frozen_potential_arithmetic():
    s=state([],coats=2,ropes=1)
    # One open tunnel, no water, no merge, no EXIT.
    assert ranking(s,2)==(1,0,29900)
    assert reference_key(s,2)==[1,0,29900]
    s.exit_placed=True
    assert ranking(s,2)==(1,0,24900)
    assert reference_key(s,2)==[1,0,24900]


def test_supervisor_kills_term_ignoring_process(tmp_path):
    command=[sys.executable,'-c','import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(30)']
    start=time.monotonic()
    with pytest.raises(TimeoutError): run_group(command,tmp_path/'log',timeout=.15,grace=.15)
    assert time.monotonic()-start<5


@pytest.mark.parametrize("corrupt_reference",[False,True])
def test_full_160_call_harness_synthetic_only(tmp_path,monkeypatch,corrupt_reference):
    from bandido_alcatraz.worker32 import runtime
    from bandido_alcatraz.worker32.evidence import move
    # Isolate UTC metadata from the host clock, leaving monotonic/CPU timing real.
    timestamps = (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=tick)
                  for tick in count())
    monkeypatch.setattr(runtime, 'utc', lambda: next(timestamps).isoformat())
    obs=state([card('rope',material=Material.ROPE)]).observation()
    entries=[dict(position=i+1,seed=1000000+i,ordinal=1,public_observation_sha256=sha(observation(obs))) for i in range(80)]
    monkeypatch.setattr(runtime,'runner_guard',lambda root:'synthetic-head')
    monkeypatch.setattr(runtime,'installed_tree',lambda *a:{'head':'synthetic-head','tree':'synthetic-tree','files':{}})
    monkeypatch.setattr(runtime,'load_population',lambda *a:(entries,[{}]*80,[{}]*80,None))
    monkeypatch.setattr(runtime,'accepted_cards',lambda *a:{})
    monkeypatch.setattr(runtime,'reconstruct',lambda *a:obs)
    monkeypatch.setattr(runtime,'baseline_gate',lambda *a:{'tier':[move(obs.legal_moves()[0])], 'legal_move_count':len(obs.legal_moves()), 'root_moves_sha256':sha([move(m) for m in obs.legal_moves()])})
    for key,value in {'RUNNER_NAME':'synthetic','PYTHONHASHSEED':'0','GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1'}.items():
        monkeypatch.setenv(key,value)
    if corrupt_reference:
        original=Reference.evaluate
        def corrupt(self,*args):
            chosen,payload,cost=original(self,*args)
            payload['roots'][0]['first_transition_sha256']='0'*64
            return chosen,payload,cost
        monkeypatch.setattr(Reference,'evaluate',corrupt)
        with pytest.raises(ValueError,match='entire independent'):
            runtime.compute(tmp_path,tmp_path)
        assert not (tmp_path/'result.json').exists()
        events=[json.loads(x) for x in (tmp_path/'journal.jsonl').read_text().splitlines()]
        assert events[-1]['event']=='failed'
        assert (tmp_path/'rejected-call-081.raw').exists()
        assert not (tmp_path/'call-081.json').exists()
        return
    runtime.compute(tmp_path,tmp_path)
    assert len(list(tmp_path.glob('call-*.json')))==161 # 160 calls plus call-order
    result=json.loads((tmp_path/'result.json').read_text())
    assert result['completed_calls']==160 and result['status'].endswith('not_exercised')
    events=[json.loads(x) for x in (tmp_path/'journal.jsonl').read_text().splitlines()]
    assert len(events)==320 and all(e['event']=='completed' for e in events[1::2])


def test_envelope_is_separate_and_strict():
    e={'pass':1,'call':1,'implementation':'candidate','seed':1000000,'ordinal':1,
       'started':'2026-10-02T00:00:00+00:00','finished':'2026-10-02T00:00:01+00:00',
       'wall_seconds':1.0,'cpu_seconds':.5,'peak_rss_kib':1000,'physical_legal_moves':1,
       'run_id':'123','run_attempt':'1'}
    expected={k:e[k] for k in ('pass','call','implementation','seed','ordinal','run_id','run_attempt')}
    validate_envelope(e,expected=expected)
    with pytest.raises(ValueError): validate_envelope({**e,'wall_seconds':float('nan')},expected=expected)
    with pytest.raises(ValueError): validate_envelope({**e,'scientific':{}},expected=expected)


def test_invalid_adapter_and_filled_quota():
    from bandido_alcatraz.moves import Move,Action
    s=state([card('a',material=Material.RAINCOAT)],3,0)
    illegal=Move(Action.COLLECT,0)
    with pytest.raises(ValueError): prevalidated_preview(s,illegal,s.legal_moves())
    with pytest.raises(ValueError): prevalidated_preview(s,illegal,[illegal])


def test_inaccessible_input_is_blocked(tmp_path):
    from bandido_alcatraz.worker32.inputs import frozen_bytes
    with pytest.raises(ExecutionBlocked): frozen_bytes(tmp_path)


@pytest.mark.parametrize('impl',[Candidate,Reference])
def test_exact_32768_preview_boundary(monkeypatch,impl):
    from bandido_alcatraz.moves import Move,Action
    from bandido_alcatraz.game import PlayerObservation
    from types import SimpleNamespace
    module=sys.modules[impl.__module__]
    # Synthetic node stream isolates the hard counter; no corpus or game execution.
    obs=state().observation()
    actions=[Move(Action.PLACE,0,(i,0),0) for i in range(32769)]
    closed=state(); closed.board=Board(); closed.board.seed(card('closed'))
    calls=[]
    def preview(*args):
        calls.append(1)
        return closed if impl is Candidate else SimpleNamespace(successor=closed)
    monkeypatch.setattr(PlayerObservation,'legal_moves',lambda self:actions)
    monkeypatch.setattr(module,'prevalidated_preview' if impl is Candidate else 'preview_move_without_draw',preview)
    # Keep the test bounded in memory and serialization cost while exercising the
    # production counter and root loop at its exact boundary.
    monkeypatch.setattr(module,'sha',lambda value:'synthetic-digest')
    monkeypatch.setattr(module,'observation',lambda value:{})
    monkeypatch.setattr(module,'leaf',lambda seq,s,key,reason:dict(sequence=[],key=list(key)))
    rng=CountingRandom()
    with pytest.raises(BudgetExceeded): impl().evaluate(obs,rng)
    assert len(calls)==32768 and rng.calls==0
