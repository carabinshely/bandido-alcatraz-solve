"""Worker32 preflight repairs: synthetic process trees and invented states only."""
import errno
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from random import Random

import pytest
from bandido_alcatraz.worker32 import containment, runtime
from bandido_alcatraz.worker32.candidate import Candidate
from bandido_alcatraz.worker32.reference import Reference
from bandido_alcatraz.worker32.evidence import sha, observation, move
from bandido_alcatraz.model import Material
from test_worker32 import state, card


def wait_for(predicate, seconds=5):
    until = time.monotonic()+seconds
    while time.monotonic()<until:
        if predicate():
            return
        time.sleep(.01)
    raise AssertionError('bounded fixture wait expired')


def alive(pid):
    s = containment._stat(pid)
    return bool(s and s['state'] != 'Z')


def tree_command(directory, exit_code=None):
    # Grandchild ignores TERM. Leader writes both PIDs before exiting or sleeping.
    # This is a real descendant, not merely a sleeping process-group leader.
    child = 'import os,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)'
    code = ('import os,subprocess,sys,time,json; from pathlib import Path; '
            f'p=subprocess.Popen([sys.executable,"-c",{child!r}]); '
            f'Path({str(directory/"pids.json")!r}).write_text(json.dumps([os.getpid(),p.pid])); '
            + (f'time.sleep(.1); sys.exit({exit_code})' if exit_code is not None else 'time.sleep(60)'))
    return [sys.executable,'-c',code]


@pytest.mark.parametrize('exit_code',[0,1,None])
def test_descendants_cleaned_on_leader_exit_and_timeout(tmp_path,exit_code):
    command = tree_command(tmp_path,exit_code)
    if exit_code is None:
        with pytest.raises(TimeoutError):
            runtime.run_group(command,tmp_path/'compute.log',timeout=.3,grace=.1)
    else:
        assert runtime.run_group(command,tmp_path/'compute.log',timeout=2,grace=.1)==exit_code
    pids = json.loads((tmp_path/'pids.json').read_text())
    # Subreaper cleanup has reaped both leader and orphaned descendant.
    assert all(containment._stat(pid) is None for pid in pids)
    runtime.finalize(tmp_path)


def start_supervisor(directory):
    command = tree_command(directory)
    code = ('from bandido_alcatraz.worker32.runtime import run_group; '
            f'run_group({command!r},{str(directory/"compute.log")!r},timeout=30,grace=.1)')
    # Honor installed-package tests as well as checkout tests: import the exact
    # package under test in the subprocess instead of a stale alternate install.
    import bandido_alcatraz
    env = {**os.environ,'PYTHONPATH':str(Path(bandido_alcatraz.__file__).resolve().parent.parent)}
    output = (directory/'supervisor.log').open('wb')
    p = subprocess.Popen([sys.executable,'-c',code],env=env,stdout=output,stderr=subprocess.STDOUT)
    output.close()
    wait_for(lambda:(directory/'pids.json').exists())
    return p


@pytest.mark.parametrize('sig',[signal.SIGTERM,signal.SIGINT])
def test_supervisor_signals_kill_and_reap_descendants(tmp_path,sig):
    supervisor = start_supervisor(tmp_path)
    pids=json.loads((tmp_path/'pids.json').read_text())
    try:
        supervisor.send_signal(sig)
        supervisor.wait(timeout=5)
        assert supervisor.returncode != 0
        assert all(containment._stat(pid) is None for pid in pids)
        runtime.finalize(tmp_path)
    finally:
        if supervisor.poll() is None:
            supervisor.kill(); supervisor.wait(timeout=5)
        containment.residual_gate(tmp_path,grace=.1)


def test_sigkill_supervisor_residual_cleanup_and_unrelated_process_survives(tmp_path):
    supervisor = start_supervisor(tmp_path)
    unrelated=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])
    pids=json.loads((tmp_path/'pids.json').read_text())
    try:
        supervisor.kill(); supervisor.wait(timeout=5)
        # Bootstrap PDEATHSIG kills leader; descendant is settled by the token
        # gate using pidfds. The unrelated newer same-user process is untouched.
        containment.residual_gate(tmp_path,grace=.1)
        assert all(not alive(pid) for pid in pids)
        assert unrelated.poll() is None
        runtime.finalize(tmp_path)
    finally:
        unrelated.terminate(); unrelated.wait(timeout=5)
        if supervisor.poll() is None:
            supervisor.kill(); supervisor.wait(timeout=5)
        containment.residual_gate(tmp_path,grace=.1)


def test_active_supervisor_blocks_finalization(tmp_path):
    supervisor=start_supervisor(tmp_path)
    try:
        with pytest.raises(RuntimeError,match='supervisor still active'):
            runtime.finalize(tmp_path)
        assert not (tmp_path/'inventory.json').exists()
    finally:
        supervisor.terminate();supervisor.wait(timeout=5)


@pytest.mark.parametrize('exception',[KeyboardInterrupt(),RuntimeError('synthetic wait failure')])
def test_exception_cleanup_reaps_real_descendant(tmp_path,monkeypatch,exception):
    original=containment.os.waitid
    fired=False
    def waitid(*args):
        nonlocal fired
        if (tmp_path/'pids.json').exists() and not fired:
            fired=True
            raise exception
        return original(*args)
    monkeypatch.setattr(containment.os,'waitid',waitid)
    with pytest.raises(type(exception)):
        runtime.run_group(tree_command(tmp_path),tmp_path/'compute.log',timeout=2,grace=.1)
    assert all(containment._stat(pid) is None for pid in json.loads((tmp_path/'pids.json').read_text()))


def test_processlookup_signal_race_is_harmless(monkeypatch):
    def gone(*args): raise ProcessLookupError()
    monkeypatch.setattr(containment.os,'killpg',gone)
    containment._kill_group(99999999,signal.SIGTERM)
    containment._kill_group(99999999,signal.SIGKILL)


@pytest.mark.parametrize('exc,status',[
    (subprocess.TimeoutExpired(['git'],30),'resource_incomplete'),
    (OSError(errno.ENOMEM,'synthetic'),'resource_incomplete'),
    (OSError(errno.ENOSPC,'synthetic'),'resource_incomplete'),
    (OSError(errno.EIO,'synthetic'),'integrity_invalid'),
    (OSError(errno.EACCES,'synthetic'),'integrity_invalid'),
    (runtime.ExecutionBlocked('input missing'),'execution_blocked'),
])
def test_resource_taxonomy(exc,status):
    assert runtime.failure_status(exc)==status


def test_production_git_timeout_becomes_resource_incomplete(tmp_path,monkeypatch):
    root=tmp_path/'checkout';root.mkdir()
    evidence=tmp_path/'evidence';evidence.mkdir()
    monkeypatch.setattr(runtime,'runner_guard',lambda root:'synthetic-head')
    monkeypatch.setattr(runtime,'load_population',lambda *a:([],[],[],None))
    def expire(command,**kwargs):
        assert command[0]=='git' and kwargs['timeout']==30
        raise subprocess.TimeoutExpired(command,30)
    monkeypatch.setattr(runtime.subprocess,'check_output',expire)
    monkeypatch.setenv('RUNNER_TEMP',str(tmp_path/'runner-temp'))
    monkeypatch.setenv('GITHUB_RUN_ID','123')
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT','1')
    monkeypatch.setattr(sys,'argv',['runtime','compute','--root',str(root),'--evidence',str(evidence)])
    with pytest.raises(subprocess.TimeoutExpired):runtime.main()
    receipt=json.loads((evidence/'failure.json').read_text())
    assert receipt['status']=='resource_incomplete' and receipt['error']['type']=='TimeoutExpired'
    assert (evidence/'provenance-started.json').exists()
    assert not list(evidence.glob('call-*.json'))


def envelope():
    return {'pass':1,'call':1,'implementation':'candidate','seed':1000000,'ordinal':1,
            'started':'2026-10-02T00:00:00+00:00','finished':'2026-10-02T00:00:01+00:00',
            'wall_seconds':1.0,'cpu_seconds':.5,'peak_rss_kib':1000,'physical_legal_moves':1,
            'run_id':'123','run_attempt':'1'}


@pytest.mark.parametrize('change',[
    {'call':81},{'call':1.5},{'call':True},{'pass':True},{'pass':2},
    {'seed':None},{'seed':True},{'seed':1000001},{'ordinal':-1},{'ordinal':True},{'ordinal':2},
    {'run_id':'arbitrary'},{'run_id':'124'},{'run_id':123},{'run_attempt':'2'},{'run_attempt':1},
    {'started':'2026-10-02T00:00:02+00:00'}, {'started':'2026-10-02T00:00:00'},
    {'finished':'2026-10-02T00:00:01+01:00'},{'peak_rss_kib':1.5},
])
def test_strict_expected_envelope(change):
    e=envelope()
    expected={k:e[k] for k in ('pass','call','implementation','seed','ordinal','run_id','run_attempt')}
    runtime.validate_envelope(e,expected=expected)
    with pytest.raises(ValueError):runtime.validate_envelope({**e,**change},expected=expected)


@pytest.fixture
def synthetic_compute(tmp_path,monkeypatch):
    obs=state([card('rope',material=Material.ROPE)]).observation()
    legal=obs.legal_moves()
    entries=[dict(position=i+1,seed=1000000+i,ordinal=1,public_observation_sha256=sha(observation(obs))) for i in range(80)]
    monkeypatch.setattr(runtime,'runner_guard',lambda root:'synthetic-head')
    monkeypatch.setattr(runtime,'installed_tree',lambda *a:{'head':'synthetic-head','tree':'synthetic-tree','files':{}})
    monkeypatch.setattr(runtime,'load_population',lambda *a:(entries,[{}]*80,[{}]*80,None))
    monkeypatch.setattr(runtime,'accepted_cards',lambda *a:{})
    monkeypatch.setattr(runtime,'reconstruct',lambda *a:obs)
    monkeypatch.setattr(runtime,'baseline_gate',lambda *a:dict(tier=[move(legal[0])],legal_move_count=len(legal),root_moves_sha256=sha([move(m) for m in legal])))
    for k,v in dict(RUNNER_NAME='synthetic',PYTHONHASHSEED='0',GITHUB_RUN_ID='123',GITHUB_RUN_ATTEMPT='1').items():monkeypatch.setenv(k,v)
    return tmp_path,obs


@pytest.mark.parametrize('fault',['science','envelope','physical','reference','serialization','size'])
def test_rejected_raw_output_preserved_exclusively(synthetic_compute,monkeypatch,fault):
    directory,obs=synthetic_compute
    target=Reference if fault=='reference' else Candidate
    original=target.evaluate
    def bad(self,*args):
        chosen,p,c=original(self,*args)
        if fault=='science':p['counts']['children']+=1
        if fault=='envelope':c['call']=81
        if fault=='physical':c['physical_legal_moves']+=1
        if fault=='reference':p['roots'][0]['first_transition_sha256']='0'*64
        if fault=='serialization':p['unserializable']=object()
        if fault=='size':p['oversize']='x'*10000
        return chosen,p,c
    monkeypatch.setattr(target,'evaluate',bad)
    if fault=='size':monkeypatch.setattr(runtime,'MAX_RETURN_BYTES',4000)
    with pytest.raises((ValueError,TypeError)):runtime.compute(directory,directory)
    call=81 if fault=='reference' else 1
    raw=directory/f'rejected-call-{call:03}.raw'
    receipt=directory/f'rejected-call-{call:03}.json'
    info=json.loads(receipt.read_text())
    assert raw.stat().st_size<=runtime.MAX_RETURN_BYTES
    assert info['validation_error']['message']
    assert info['complete']==(fault not in ('serialization','size'))
    if fault=='science':assert json.loads(raw.read_bytes())['scientific']['counts']['children']==1
    if fault=='envelope':assert json.loads(raw.read_bytes())['envelope']['call']==81
    if fault=='physical':assert json.loads(raw.read_bytes())['cost']['physical_legal_moves']==3
    assert not (directory/f'call-{call:03}.json').exists()
    assert not (directory/'result.json').exists()
    events=[json.loads(x) for x in (directory/'journal.jsonl').read_text().splitlines()]
    assert events[-1]['event']=='failed'
    assert not any(e['event']=='completed' and e['call']==call for e in events)
    before=raw.read_bytes(),receipt.read_bytes()
    with pytest.raises(FileExistsError):runtime.preserve_rejected(directory,call,({}, {}, {}),None,ValueError('another'))
    assert before==(raw.read_bytes(),receipt.read_bytes())


@pytest.mark.parametrize('forge_input_hash',[False,True])
def test_shared_wrong_observation_or_root_omission_cannot_be_green(synthetic_compute,monkeypatch,forge_input_hash):
    directory,obs=synthetic_compute
    empty=state().observation()
    original=Candidate.evaluate
    def wrong(self,*args):
        chosen,p,c=original(Candidate(),empty,Random(0))
        if forge_input_hash:
            p['input_before']=p['input_after']=sha(observation(obs))
        return chosen,p,c
    monkeypatch.setattr(Candidate,'evaluate',wrong)
    monkeypatch.setattr(Reference,'evaluate',wrong)
    with pytest.raises(ValueError,match='canonical baseline roots' if forge_input_hash else 'frozen observation'):
        runtime.compute(directory,directory)
    assert not (directory/'result.json').exists()
    assert not (directory/'call-001.json').exists()
    assert (directory/'rejected-call-001.raw').exists()


def test_wrapped_resource_error_is_not_mistaken_for_inaccessible_input():
    blocked=runtime.ExecutionBlocked('input read failed')
    blocked.__cause__=OSError(errno.ENOMEM,'synthetic allocation failure')
    assert runtime.failure_status(blocked)=='resource_incomplete'
    blocked.__cause__=FileNotFoundError(errno.ENOENT,'synthetic unavailable input')
    assert runtime.failure_status(blocked)=='execution_blocked'
    blocked.__cause__=OSError(errno.EIO,'synthetic I/O corruption')
    assert runtime.failure_status(blocked)=='integrity_invalid'
    blocked.__cause__=PermissionError(errno.EACCES,'synthetic inaccessible input')
    assert runtime.failure_status(blocked)=='execution_blocked'


def test_stale_supervisor_identity_does_not_signal_reused_pid(tmp_path):
    unrelated=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],start_new_session=True)
    try:
        start=containment._stat(unrelated.pid)['start']
        runtime.durable(tmp_path/'compute.log.group.json',dict(schema='worker32-process-group-v1',
            token='0'*64,boot=containment._boot(),uid=os.getuid(),supervisor_pid=unrelated.pid,
            supervisor_start=start-1))
        runtime.durable(tmp_path/'compute.log.group-leader.json',
                        dict(pid=unrelated.pid,start=start-1,token='0'*64))
        containment.residual_gate(tmp_path,grace=.1)
        assert unrelated.poll() is None
    finally:
        unrelated.terminate();unrelated.wait(timeout=5)


def test_cleanup_scan_exception_still_kills_and_reaps(tmp_path,monkeypatch):
    original=containment._members
    fired=False
    def broken(group):
        nonlocal fired
        if not fired:
            fired=True
            raise RuntimeError('synthetic process inventory failure')
        return original(group)
    monkeypatch.setattr(containment,'_members',broken)
    with pytest.raises(RuntimeError,match='inventory failure'):
        runtime.run_group(tree_command(tmp_path,exit_code=1),tmp_path/'compute.log',timeout=2,grace=.1)
    assert all(containment._stat(pid) is None for pid in json.loads((tmp_path/'pids.json').read_text()))


def test_abnormal_supervisor_death_overrides_existing_result_at_finalization(tmp_path,monkeypatch):
    root=tmp_path/'checkout';root.mkdir()
    evidence=tmp_path/'evidence';evidence.mkdir()
    runtime.journal(evidence,event='whole_compute_started')
    runtime.durable(evidence/'result.json',{'status':'synthetic result before supervisor death'})
    supervisor=start_supervisor(evidence)
    try:
        supervisor.kill();supervisor.wait(timeout=5)
        monkeypatch.setattr(runtime,'residual_gate',lambda d:containment.residual_gate(d,grace=.1))
        monkeypatch.setenv('RUNNER_TEMP',str(tmp_path/'runner-temp'))
        monkeypatch.setattr(sys,'argv',['runtime','finalize','--root',str(root),'--evidence',str(evidence)])
        runtime.main()
        assert json.loads((evidence/'failure.json').read_text())['status']=='resource_incomplete'
        assert (evidence/'result.json').exists() and (evidence/'inventory.json').exists()
        assert all(not alive(pid) for pid in json.loads((evidence/'pids.json').read_text()))
    finally:
        if supervisor.poll() is None:
            supervisor.kill();supervisor.wait(timeout=5)
        containment.residual_gate(evidence,grace=.1)


def test_closed_group_does_not_allow_racing_live_supervisor_metadata(tmp_path):
    import bandido_alcatraz
    command=[sys.executable,'-c','pass']
    code=('from pathlib import Path; import time; from bandido_alcatraz.worker32.runtime import run_group; '
          f'run_group({command!r},{str(tmp_path/"compute.log")!r}); '
          f'Path({str(tmp_path/"ready")!r}).write_text("ready"); time.sleep(60)')
    env={**os.environ,'PYTHONPATH':str(Path(bandido_alcatraz.__file__).resolve().parent.parent)}
    supervisor=subprocess.Popen([sys.executable,'-c',code],env=env)
    try:
        wait_for(lambda:(tmp_path/'ready').exists())
        assert (tmp_path/'compute.log.group-closed.json').exists()
        with pytest.raises(RuntimeError,match='supervisor still active'):
            runtime.finalize(tmp_path)
        assert not (tmp_path/'inventory.json').exists()
    finally:
        supervisor.terminate();supervisor.wait(timeout=5)
    runtime.finalize(tmp_path)
