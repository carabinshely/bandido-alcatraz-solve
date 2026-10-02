"""Runner-only durable supervisor and whole-compute child. No import-time execution."""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import platform
from random import Random
import resource
import signal
import subprocess
import sys
import time
from .evidence import canonical, sha, BudgetExceeded
from .inputs import ExecutionBlocked, load_population, reconstruct, accepted_cards, baseline_gate

BASE = 'c50a7ab8e73eaf3c497c5d1c9fef5cbe53261853'
BRANCH = 'research/worker32-visible-two-action-diagnostic'
REPO = 'carabinshely/bandido-alcatraz-solve'


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def durable(path, value):
    """Exclusive files preserve failed/superseded attempts, fsync file and directory."""
    with Path(path).open('xb') as f:
        f.write(canonical(value)); f.flush(); os.fsync(f.fileno())
    fd = os.open(Path(path).parent,os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def journal(directory, **event):
    with (directory/'journal.jsonl').open('ab') as f:
        f.write(canonical(dict(timestamp=utc(),**event))); f.flush(); os.fsync(f.fileno())


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],timeout=30)


def installed_tree(root, installed, expected_head, base=BASE):
    """Real Git objects anchor checkout and the *installed* entire Python package."""
    root,installed = Path(root),Path(installed)
    head = git(root,'rev-parse','HEAD').decode().strip()
    if head != expected_head or git(root,'status','--porcelain','--untracked-files=normal').strip():
        raise ValueError('head/clean checkout gate')
    def entries(ref, *paths):
        result = {}
        for record in git(root,'ls-tree','-r','-z',ref,'--',*paths).split(b'\0'):
            if record:
                meta,name = record.split(b'\t')
                mode,kind,blob = meta.decode().split()
                if mode != '100644' and mode != '100755':
                    raise ValueError('nonregular source')
                result[name.decode()] = blob
        return result
    old = entries(base,'src','data')
    current = entries('HEAD')
    for name,blob in old.items():
        if current.get(name) != blob:
            raise ValueError('canonical source/data changed: '+name)
    inventory = {}
    for name,blob in current.items():
        path = root/name
        raw = path.read_bytes()
        if path.is_symlink():
            raise ValueError('source symlink')
        actual_blob = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if actual_blob != blob:
            raise ValueError('working source bytes mismatch')
        if name.startswith('src/bandido_alcatraz/') and name.endswith('.py'):
            target = installed/name.removeprefix('src/')
            if target.is_symlink() or target.read_bytes() != raw:
                raise ValueError('installed source mismatch: '+name)
        inventory[name] = dict(git_blob=blob,sha256=hashlib.sha256(raw).hexdigest(),size_bytes=len(raw))
    expected = {n.removeprefix('src/') for n in current if n.startswith('src/bandido_alcatraz/') and n.endswith('.py')}
    actual = {str(p.relative_to(installed)) for p in (installed/'bandido_alcatraz').rglob('*.py')}
    if expected != actual:
        raise ValueError('installed module set mismatch')
    return dict(head=head,tree=git(root,'rev-parse','HEAD^{tree}').decode().strip(),accepted_base=base,files=inventory)


def runner_guard(root):
    if os.environ.get('RUNNER_NAME') != 'bandido-alcatraz-ci' or os.environ.get('GITHUB_EVENT_NAME') != 'pull_request':
        raise ExecutionBlocked('research execution only on authorized existing runner')
    if sys.version_info[:2] != (3,11) or platform.python_implementation() != 'CPython' or os.environ.get('PYTHONHASHSEED') != '0':
        raise ValueError('runtime gate')
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    pr = event['pull_request']
    if (event['action'] != 'opened' or pr['draft'] is not True or pr['head']['ref'] != BRANCH
        or pr['head']['repo']['full_name'] != REPO or pr['base']['repo']['full_name'] != REPO
        or os.environ.get('GITHUB_RUN_ATTEMPT') != '1'):
        raise ExecutionBlocked('not first opened draft event on frozen branch')
    return pr['head']['sha']


def validate_science(p):
    required = {'schema','input_before','input_after','root_moves_sha256','roots','maximal_roots','chosen','best','rng_before','rng_after','counts'}
    if set(p) != required or p['schema'] != 'worker32-scientific-v1' or p['input_before'] != p['input_after']:
        raise ValueError('scientific schema/input gate')
    roots = p['roots']
    if sha([r['root'] for r in roots]) != p['root_moves_sha256'] or len({sha(r['root']) for r in roots}) != len(roots):
        raise ValueError('root list gate')
    children = leaves = expanded = 0
    for r in roots:
        if set(r) != {'root','first_transition_sha256','second_moves','second_moves_sha256','leaves','leaves_sha256','maximum','witness'}:
            raise ValueError('root schema')
        if sha(r['second_moves']) != r['second_moves_sha256'] or sha(r['leaves']) != r['leaves_sha256']:
            raise ValueError('ordered child/leaf digest')
        ll = r['leaves']; ss = r['second_moves']
        if not ll or len(ll) != max(1,len(ss)):
            raise ValueError('leaf coverage')
        for i,l in enumerate(ll):
            if set(l) != {'sequence','key','reason','transition_sha256'}:
                raise ValueError('leaf schema')
            seq = [r['root']] + ([ss[i]] if ss else [])
            if l['sequence'] != seq or l['reason'] not in {'visible_victory','closed_tunnel_loss','omitted_draw_dead_end','horizon'}:
                raise ValueError('witness sequence/reason')
            if len(l['key']) != 3 or any(type(x) is not int for x in l['key']):
                raise ValueError('leaf key')
        maximum = max(l['key'] for l in ll)
        if r['maximum'] != maximum or r['witness'] != next(l['sequence'] for l in ll if l['key'] == maximum):
            raise ValueError('root aggregation')
        children += len(ss); leaves += len(ll)
        expanded += bool(ss) or ll[0]['reason'] == 'omitted_draw_dead_end'
    maximum = max((r['maximum'] for r in roots),default=None)
    tier = [r['root'] for r in roots if r['maximum'] == maximum]
    expected = dict(roots=len(roots),children=children,previews=len(roots)+children,
                    expanded_nodes=1+expanded,enumerations=1+expanded,leaves=leaves)
    if p['counts'] != expected or expected['previews'] > 32768 or p['best'] != maximum or p['maximal_roots'] != tier:
        raise ValueError('coverage/counts/tier')
    rng = Random(0)
    if p['rng_before'] != sha(rng.getstate()) or p['chosen'] != (rng.choice(tier) if tier else None) or p['rng_after'] != sha(rng.getstate()):
        raise ValueError('deterministic RNG replay')


def validate_envelope(e):
    if set(e) != {'pass','call','implementation','seed','ordinal','started','finished','wall_seconds','cpu_seconds','peak_rss_kib','physical_legal_moves','run_id','run_attempt'}:
        raise ValueError('envelope schema')
    if e['pass'] not in (1,2) or e['implementation'] != ('candidate' if e['pass']==1 else 'reference') or not 1 <= e['call'] <= 160:
        raise ValueError('envelope identity')
    for k in ('wall_seconds','cpu_seconds','peak_rss_kib'):
        if type(e[k]) not in (float,int) or not math.isfinite(e[k]) or e[k] < 0:
            raise ValueError('cost metadata')
    for k in ('started','finished'):
        datetime.datetime.fromisoformat(e[k])
    if type(e['physical_legal_moves']) is not int or e['physical_legal_moves'] < 1:
        raise ValueError('physical cost count')


def strict_departure(payload, baseline):
    types = {m['action'] for m in payload['maximal_roots']}
    baseline_types = {m['action'] for m in baseline['tier']}
    if (types,baseline_types) not in (({'place'},{'collect'}),({'collect'},{'place'})):
        return False
    tier_ids = {sha(m) for m in baseline['tier']}
    restricted = [r['maximum'] for r in payload['roots'] if sha(r['root']) in tier_ids]
    if len(restricted) != len(tier_ids):
        raise ValueError('baseline root coverage')
    return bool(restricted) and payload['best'] > max(restricted)


def compute(root, directory):
    # Everything below, including provenance, reconstruction and baseline, is inside
    # the single supervisor deadline. No third policy pass and no retry path.
    from .candidate import Candidate
    from .reference import Reference
    head = runner_guard(root)
    entries,public,audits,parser = load_population(root/'experiments/visible-two-action-diagnostic')
    import bandido_alcatraz
    installed = Path(bandido_alcatraz.__file__).resolve().parent.parent
    provenance = installed_tree(root,installed,head)
    from ..rules import RULESET_ID
    if RULESET_ID != 'v2-exact-equipment-quota-limited-collect-full-hand-refresh':
        raise ValueError('ruleset gate')
    durable(directory/'provenance.json',dict(**provenance,python=sys.version,executable=sys.executable,
        runner=os.environ['RUNNER_NAME'],platform=platform.platform(),hashseed=os.environ['PYTHONHASHSEED'],
        run_id=os.environ['GITHUB_RUN_ID'],run_attempt=os.environ['GITHUB_RUN_ATTEMPT']))
    cards = accepted_cards(root/'data')
    observations = [reconstruct(v,cards,parser) for v in public]
    baselines = [baseline_gate(o,e,a) for o,e,a in zip(observations,entries,audits)]
    durable(directory/'baseline-gates.json',baselines)
    durable(directory/'call-order.json',[dict(pass_number=p,position=e['position'],seed=e['seed'],ordinal=e['ordinal']) for p in (1,2) for e in entries])
    departures = []
    for pass_number,implementation in ((1,Candidate),(2,Reference)):
        for index,(obs,entry) in enumerate(zip(observations,entries)):
            call = (pass_number-1)*80+index+1
            ident = dict(call=call,pass_number=pass_number,seed=entry['seed'],ordinal=entry['ordinal'])
            journal(directory,event='started',**ident)
            try:
                started = utc(); wall = time.monotonic(); cpu = time.process_time()
                _,payload,cost = implementation().evaluate(obs,Random(0))
                elapsed,cpu_elapsed = time.monotonic()-wall,time.process_time()-cpu
                validate_science(payload)
                envelope = {'pass':pass_number,'call':call,'implementation':implementation.__name__.lower(),
                    'seed':entry['seed'],'ordinal':entry['ordinal'],'started':started,'finished':utc(),
                    'wall_seconds':elapsed,'cpu_seconds':cpu_elapsed,
                    'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    **cost,'run_id':os.environ['GITHUB_RUN_ID'],'run_attempt':os.environ['GITHUB_RUN_ATTEMPT']}
                validate_envelope(envelope)
                expected_physical = payload['counts']['enumerations'] + (payload['counts']['previews'] if pass_number == 2 else 0)
                if cost['physical_legal_moves'] != expected_physical:
                    raise ValueError('physical/legal enumeration accounting')
                durable(directory/f'call-{call:03}.json',dict(scientific=payload,envelope=envelope))
                if pass_number == 2:
                    prior = json.loads((directory/f'call-{index+1:03}.json').read_bytes())
                    if canonical(prior['scientific']) != canonical(payload):
                        raise ValueError('entire independent scientific payload differs')
                elif strict_departure(payload,baselines[index]):
                    departures.append([entry['seed'],entry['ordinal']])
                journal(directory,event='completed',scientific_sha256=sha(payload),**ident)
            except BaseException as exc:
                journal(directory,event='failed',error=repr(exc),**ident)
                raise
    durable(directory/'result.json',dict(status='visible_two_action_diagnostic_mechanism_'+('exercised' if departures else 'not_exercised'),
        completed_calls=160,strict_departures=departures,scope='behavior/cost only; no win-rate or causal horizon claim'))


def run_group(command, log, timeout=1800, grace=30):
    with Path(log).open('xb') as stream:
        process = subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGTERM)
            try:
                process.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                pass
            # Always kill remaining descendants even if group leader exited.
            try:
                os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            raise TimeoutError('whole-compute process group exceeded deadline')


def failure_status(exc):
    if isinstance(exc,ExecutionBlocked):
        return 'execution_blocked'
    if isinstance(exc,(TimeoutError,BudgetExceeded,MemoryError)):
        return 'resource_incomplete'
    return 'integrity_invalid'


def finalize(directory):
    # Fixed local directory only. No source-controlled glob or symlink traversal.
    files = {}
    for path in sorted(directory.iterdir()):
        if path.name == 'inventory.json':
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError('unsafe evidence member')
        digest = hashlib.sha256(); size = 0
        with path.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):
                digest.update(chunk); size += len(chunk)
        files[path.name] = dict(sha256=digest.hexdigest(),size_bytes=size)
    durable(directory/'inventory.json',dict(files=files,finalized=utc()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode',choices=['supervise','compute','finalize'])
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    args = parser.parse_args()
    d = args.evidence.resolve(); root = args.root.resolve()
    if d.is_relative_to(root) or d.is_relative_to(Path(os.environ.get('RUNNER_TEMP','/tmp')).resolve()) or args.evidence.is_symlink():
        raise ValueError('evidence must be outside checkout and runner-temp')
    if args.mode == 'finalize':
        if not (d/'result.json').exists() and not (d/'failure.json').exists():
            started_compute = (d/'journal.jsonl').exists() and b'whole_compute_started' in (d/'journal.jsonl').read_bytes()
            durable(d/'failure.json',dict(status='resource_incomplete' if started_compute else 'execution_blocked',
                error='interrupted whole compute' if started_compute else 'setup/preflight did not complete',timestamp=utc()))
        finalize(d)
        return
    try:
        runner_guard(root)
        if args.mode == 'compute':
            compute(root,d)
        else:
            journal(d,event='whole_compute_started')
            rc = run_group([sys.executable,'-m','bandido_alcatraz.worker32.runtime','compute','--root',str(root),'--evidence',str(d)],d/'compute.log')
            if rc:
                if not (d/'failure.json').exists():
                    if rc in (-signal.SIGKILL,-signal.SIGTERM,137,143):
                        raise TimeoutError(f'compute process externally killed: {rc}')
                    raise ValueError(f'compute child exited {rc}')
                raise SystemExit(rc)
            if not (d/'result.json').exists():
                raise ValueError('child exited without complete result')
            journal(d,event='whole_compute_completed')
    except Exception as exc:
        journal(d,event='whole_compute_failed',error=repr(exc))
        if not (d/'failure.json').exists():
            durable(d/'failure.json',dict(status=failure_status(exc),error=repr(exc),timestamp=utc()))
        raise

if __name__ == '__main__':
    main()
