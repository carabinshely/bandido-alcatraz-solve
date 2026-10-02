"""Runner-only durable supervisor and whole-compute child. No import-time execution."""
import argparse
import datetime
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import platform
from random import Random
import resource
import re
import signal
import subprocess
import sys
import time
from .evidence import canonical, sha, BudgetExceeded
from .containment import run_group, residual_gate
from .inputs import ExecutionBlocked, load_population, reconstruct, accepted_cards, baseline_gate

BASE = 'c50a7ab8e73eaf3c497c5d1c9fef5cbe53261853'
BRANCH = 'research/worker32-visible-two-action-diagnostic'
REPO = 'carabinshely/bandido-alcatraz-solve'


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def durable(path, value):
    """Exclusive files preserve failed/superseded attempts, fsync file and directory."""
    raw = canonical(value)
    with Path(path).open('xb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())
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


def validate_envelope(e, *, expected):
    identity = {'pass','call','implementation','seed','ordinal','run_id','run_attempt'}
    if type(e) is not dict or set(e) != identity | {'started','finished','wall_seconds','cpu_seconds','peak_rss_kib','physical_legal_moves'}:
        raise ValueError('envelope schema')
    for key, lo, hi in (('pass',1,2),('call',1,160),('seed',1000000,1000399)):
        if type(e[key]) is not int or not lo <= e[key] <= hi:
            raise ValueError('envelope integer identity: '+key)
    if type(e['ordinal']) is not int or e['ordinal'] < 1:
        raise ValueError('envelope ordinal')
    if e['pass'] != (e['call']-1)//80+1 or e['implementation'] != ('candidate' if e['pass']==1 else 'reference'):
        raise ValueError('envelope pass/call/implementation')
    if type(e['run_id']) is not str or not re.fullmatch(r'[1-9][0-9]*',e['run_id']) or e['run_attempt'] != '1':
        raise ValueError('envelope run identity')
    if set(expected) != identity or canonical({k:e[k] for k in identity}) != canonical(expected):
        raise ValueError('envelope differs from frozen call/run identity')
    for k in ('wall_seconds','cpu_seconds'):
        if type(e[k]) not in (float,int) or not math.isfinite(e[k]) or e[k] < 0:
            raise ValueError('cost metadata')
    for k in ('peak_rss_kib','physical_legal_moves'):
        if type(e[k]) is not int or e[k] < (1 if k == 'physical_legal_moves' else 0):
            raise ValueError('integer cost metadata')
    timestamps = []
    for k in ('started','finished'):
        if type(e[k]) is not str:
            raise ValueError('timestamp type')
        stamp = datetime.datetime.fromisoformat(e[k])
        if stamp.tzinfo is None or stamp.utcoffset() != datetime.timedelta(0):
            raise ValueError('timezone-aware UTC timestamp required')
        timestamps.append(stamp)
    if timestamps[1] < timestamps[0]:
        raise ValueError('reversed call timestamps')


def bind_science(payload, entry, baseline):
    if (payload['input_before'] != entry['public_observation_sha256']
        or payload['input_after'] != entry['public_observation_sha256']):
        raise ValueError('scientific input does not match frozen observation')
    if (type(payload['counts']['roots']) is not int
        or payload['root_moves_sha256'] != baseline['root_moves_sha256']
        or payload['counts']['roots'] != baseline['legal_move_count']):
        raise ValueError('scientific roots do not match canonical baseline roots')


MAX_RETURN_BYTES = 64*1024*1024


def bounded_return_bytes(value):
    chunks = []
    size = 0
    encoder = json.JSONEncoder(sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
    for chunk in encoder.iterencode(value):
        raw = chunk.encode('utf-8')
        size += len(raw)
        if size+1 > MAX_RETURN_BYTES:
            raise ValueError('returned-call serialization exceeds evidence byte bound')
        chunks.append(raw)
    return b''.join(chunks)+b'\n'


def error_record(exc):
    record = dict(type=type(exc).__name__,message=str(exc)[:4096],errno=getattr(exc,'errno',None))
    if isinstance(exc,subprocess.TimeoutExpired):
        record['timeout_seconds'] = exc.timeout
        for name in ('output','stderr'):
            value = getattr(exc,name,None)
            if value is not None:
                prefix = value[:4096]
                record[name+'_prefix'] = prefix.decode('utf-8','backslashreplace') if isinstance(prefix,bytes) else prefix
                record[name+'_truncated'] = len(value)>4096
    if getattr(exc,'__notes__',None):
        record['notes'] = [str(x)[:4096] for x in exc.__notes__[:8]]
    return record


def preserve_rejected(directory, call, returned, envelope, exc):
    """Exclusive bounded JSON prefix plus its validation/encoding failure receipt.

    Prefix files deliberately use .raw: serialization errors or the evidence
    byte ceiling cannot masquerade as a complete JSON call. They are never
    counted as accepted calls. Existing evidence is never overwritten.
    """
    value = (dict(scientific=returned[1],cost=returned[2],envelope=envelope)
             if type(returned) in (tuple,list) and len(returned)==3 else dict(returned=returned,envelope=envelope))
    path = directory/f'rejected-call-{call:03}.raw'
    info = dict(validation_error=error_record(exc),complete=False,size_bytes=0,
                serialization_error=None,write_error=None,byte_limit=MAX_RETURN_BYTES)
    digest = hashlib.sha256()
    # Keep the forensic prefix even on encoding/size/disk failure. The metadata
    # receipt is attempted separately, so available failure evidence survives.
    with path.open('xb') as f:
        try:
            encoder = json.JSONEncoder(sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
            for chunk in encoder.iterencode(value):
                data = chunk.encode('utf-8')
                remaining = MAX_RETURN_BYTES-info['size_bytes']
                piece = data[:remaining]
                written = f.write(piece)
                digest.update(piece[:written]); info['size_bytes'] += written
                if len(data)>remaining:
                    raise ValueError('rejected-call prefix reached evidence byte bound')
            info['complete'] = True
        except (TypeError,ValueError,OverflowError,RecursionError) as encoding:
            info['serialization_error'] = error_record(encoding)
        except OSError as writing:
            info['write_error'] = error_record(writing)
        finally:
            f.flush(); os.fsync(f.fileno())
    info['sha256'] = digest.hexdigest()
    durable(directory/f'rejected-call-{call:03}.json',info)


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
    run_identity = {'run_id':os.environ['GITHUB_RUN_ID'],'run_attempt':os.environ['GITHUB_RUN_ATTEMPT']}
    durable(directory/'provenance-started.json',dict(expected_head=head,accepted_base=BASE,python=sys.version,
        executable=sys.executable,runner=os.environ.get('RUNNER_NAME'),run_id=os.environ.get('GITHUB_RUN_ID'),
        run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),timestamp=utc()))
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
            returned = None
            envelope = None
            have_returned = False
            try:
                started = utc(); wall = time.monotonic(); cpu = time.process_time()
                returned = implementation().evaluate(obs,Random(0))
                have_returned = True
                _,payload,cost = returned
                elapsed,cpu_elapsed = time.monotonic()-wall,time.process_time()-cpu
                expected_identity = {'pass':pass_number,'call':call,
                    'implementation':'candidate' if pass_number == 1 else 'reference',
                    'seed':entry['seed'],'ordinal':entry['ordinal'],
                    **run_identity}
                envelope = {**expected_identity,'started':started,'finished':utc(),
                    'wall_seconds':elapsed,'cpu_seconds':cpu_elapsed,
                    'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,**cost}
                # Pre-serialize with a bound before creating any accepted-call file.
                record = dict(scientific=payload,envelope=envelope)
                bounded_return_bytes(record)
                validate_science(payload)
                bind_science(payload,entry,baselines[index])
                validate_envelope(envelope,expected=expected_identity)
                expected_physical = payload['counts']['enumerations'] + (payload['counts']['previews'] if pass_number == 2 else 0)
                if set(cost) != {'physical_legal_moves'} or cost['physical_legal_moves'] != expected_physical:
                    raise ValueError('physical/legal enumeration accounting')
                if pass_number == 2:
                    prior = json.loads((directory/f'call-{index+1:03}.json').read_bytes())
                    if canonical(prior['scientific']) != canonical(payload):
                        raise ValueError('entire independent scientific payload differs')
                elif strict_departure(payload,baselines[index]):
                    departures.append([entry['seed'],entry['ordinal']])
                durable(directory/f'call-{call:03}.json',record)
                journal(directory,event='completed',scientific_sha256=sha(payload),**ident)
            except BaseException as exc:
                if have_returned and not (directory/f'call-{call:03}.json').exists():
                    try:
                        preserve_rejected(directory,call,returned,envelope,exc)
                    except BaseException as evidence_error:
                        exc.add_note('Rejected evidence persistence failed: '+str(error_record(evidence_error)))
                journal(directory,event='failed',error=error_record(exc),**ident)
                raise
    durable(directory/'result.json',dict(status='visible_two_action_diagnostic_mechanism_'+('exercised' if departures else 'not_exercised'),
        completed_calls=160,strict_departures=departures,scope='behavior/cost only; no win-rate or causal horizon claim'))


def failure_status(exc):
    if isinstance(exc,ExecutionBlocked):
        cause = exc.__cause__
        if cause is not None and failure_status(cause) == 'resource_incomplete':
            return 'resource_incomplete'
        return 'execution_blocked'
    if isinstance(exc,(TimeoutError,subprocess.TimeoutExpired,BudgetExceeded,MemoryError,KeyboardInterrupt)):
        return 'resource_incomplete'
    if isinstance(exc,OSError) and exc.errno in {errno.ENOMEM,errno.ENOSPC,errno.EDQUOT,errno.EAGAIN,errno.EMFILE,errno.ENFILE}:
        return 'resource_incomplete'
    return 'integrity_invalid'


def finalize(directory):
    residual_gate(directory)
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
        residual_gate(d)
        journal_bytes = (d/'journal.jsonl').read_bytes() if (d/'journal.jsonl').exists() else b''
        started_compute = b'\"event\":\"whole_compute_started\"' in journal_bytes
        completed_compute = b'\"event\":\"whole_compute_completed\"' in journal_bytes
        if not (d/'failure.json').exists() and (not (d/'result.json').exists() or (started_compute and not completed_compute)):
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
    except BaseException as exc:
        journal(d,event='whole_compute_failed',error=error_record(exc))
        if not (d/'failure.json').exists():
            durable(d/'failure.json',dict(status=failure_status(exc),error=error_record(exc),timestamp=utc()))
        raise

if __name__ == '__main__':
    main()
