"""Worker28: frozen spent-development evaluation; no shard interpretation."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from concurrent.futures.process import BrokenProcessPool
import hashlib,json,os,subprocess,time,zipfile
from pathlib import Path
from scripts import run_worker26 as common

ROOT=Path(__file__).resolve().parents[1]
BASE='f26781b87451ceb49069c29276d60e03b18ba0d7'
OBSERVER_BOARD_BLOB='e04e9255ecc9c8181ca49903dfb6501a67c8a482'
PREREG='https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5917700044'
SOURCE_RECONCILIATION='https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5918019657'
MANIFEST='experiments/real-deck-policy-v7/fresh-development-1000000-1000399-2026-09-30.manifest.json'
SEEDS=list(range(1000000,1000400))

def reference_rows(folder,manifest):
    rows=[];hashes={}
    inventory={x['label']:x for x in manifest['raw_artifact']['contained_actions_archives']}
    for shard in range(4):
        label=f'shard-{shard}';expected=inventory[label]
        candidates=[folder/f'worker27-shard-{shard}-36740756141-1'/'receipt.json',folder/label/'receipt.json',folder/'artifacts'/f'{label}.zip']
        present=[p for p in candidates if p.exists()]
        if not present:raise FileNotFoundError(f'Accepted Worker27 {label} input is inaccessible')
        common.require(len(present)==1,f'ambiguous input for {label}')
        path=present[0]
        if path.suffix=='.zip':
            rawzip=path.read_bytes();common.require(hashlib.sha256(rawzip).hexdigest()==expected['archive_sha256'],f'archive hash {label}')
            with zipfile.ZipFile(path) as z:raw=z.read('receipt.json')
        else:raw=path.read_bytes()
        digest=hashlib.sha256(raw).hexdigest()
        common.require(len(raw)==expected['receipt_bytes'] and digest==expected['receipt_sha256'],f'receipt integrity {label}')
        r=json.loads(raw);expected_seeds=SEEDS[shard*100:(shard+1)*100]
        common.require(r['status']=='complete' and r['head']==manifest['evaluated_commit'] and r['shard']==shard,'accepted receipt identity')
        common.require(r['seeds']==expected_seeds and [p['seed'] for p in r['pairs']]==expected_seeds,'accepted population')
        rows.extend(p['v4'] for p in r['pairs']);hashes[label]=digest
    common.require([r['seed'] for r in rows]==SEEDS,'complete400reference')
    return rows,hashes

def preflight(folder):
    head=common.git('rev-parse','HEAD');common.require(head==os.environ.get('EVALUATED_COMMIT'),'execution head mismatch')
    common.require(os.environ.get('RUNNER_NAME')=='bandido-alcatraz-ci','unauthorized executor')
    ancestry=subprocess.run(['git','merge-base','--is-ancestor',BASE,'HEAD'],cwd=ROOT,text=True,capture_output=True)
    if ancestry.returncode not in (0,1):raise common.InfrastructureError(f'ancestry unavailable: {ancestry.returncode}: {ancestry.stderr}')
    common.require(ancestry.returncode==0,'starting main is not ancestor')
    manifest=json.loads(common.git('show',BASE+':'+MANIFEST));sources=dict(manifest['fixed_configuration']['canonical_source_blobs'])
    # Preregistered pre-execution observer-only source reconciliation after PR24.
    sources['src/bandido_alcatraz/board.py']=OBSERVER_BOARD_BLOB
    for path,sha in sources.items():common.require(common.git('hash-object',path)==sha,'canonical source mismatch: '+path)
    bound={}
    for path in ['scripts/run_worker26.py','scripts/run_worker28.py','scripts/worker28_policy.py','experiments/seed-ledger.json']:
        blob=common.git('hash-object',path);common.require(blob==common.git('rev-parse','HEAD:'+path),'dirty source: '+path);bound[path]=blob
    common.require(bound['scripts/run_worker26.py']==common.git('rev-parse',BASE+':scripts/run_worker26.py'),'common helper changed')
    ledger=json.loads((ROOT/'experiments/seed-ledger.json').read_text());a=[x for x in ledger['allocations'] if x['research_step']==28]
    common.require(len(a)==1 and a[0]['range_inclusive']==[1000000,1000399] and a[0]['confirmation_eligible'] is False and a[0]['role']=='spent development; never confirmation','ledger scope')
    from scripts.worker28_policy import VisibleEndStateBeamV8Policy
    common.require(VisibleEndStateBeamV8Policy.WIDTH==16 and VisibleEndStateBeamV8Policy.HORIZON==3,'frozen beam parameters')
    rows,hashes=reference_rows(folder,manifest)
    return rows,dict(head=head,source_blobs=sources,bound_files=bound,reference_receipt_hashes=hashes,
        accepted_worker27_head=manifest['evaluated_commit'],policy_sha256=hashlib.sha256((ROOT/'scripts/worker28_policy.py').read_bytes()).hexdigest())

def one_game(policy,seed):
    common.require(type(seed) is int and seed in SEEDS,'out-of-scope seed')
    common.require(policy in ('v4','v8'),'unknown policy')
    if policy=='v4':agent=common.BoundedMergeV4Policy(setup_weight=250)
    else:
        from scripts.worker28_policy import VisibleEndStateBeamV8Policy
        agent=VisibleEndStateBeamV8Policy()
    deck=common.load_real_deck(ROOT/'data')
    result=common.play_game(start_card=deck.start_easy,deck=deck.draw_deck(),hand_size=3,policy=agent,seed=seed)
    return common.final_record(seed,result)

def candidate(task):
    seed,folder=task;path=Path(folder)/f'{seed}.json';r={'seed':seed,'status':'running','record':None,'research_interpretation_performed':False};common.write_json(path,r)
    try:
        r['record']=one_game('v8',seed);common.write_json(path,r)
        common.require(r['record']['reason']!='step_limit','candidate step limit');r['status']='complete'
    except OSError as e:r.update(status='execution_blocked',error=f'{type(e).__name__}: {e}')
    except Exception as e:r.update(status='diagnostic_invalid',error=f'{type(e).__name__}: {e}')
    common.write_json(path,r);return r

def execute_shard(seeds,out,r,save):
    games=out/'games';games.mkdir(exist_ok=False)
    with (out/'completed.jsonl').open('x') as journal,ProcessPoolExecutor(max_workers=4) as pool:
        futures={};failures=[]
        for seed in seeds:
            r['submission_attempted_seeds'].append(seed);save()
            try:f=pool.submit(candidate,(seed,str(games)))
            except Exception as e:
                failures.append(dict(seed=seed,kind='infrastructure',error=f'{type(e).__name__}: {e}'));break
            futures[f]=seed;r['submitted_seeds'].append(seed);save()
        for f in as_completed(futures):
            try:row=f.result()
            except Exception as e:failures.append(dict(seed=futures[f],kind='infrastructure' if isinstance(e,(OSError,BrokenProcessPool)) else 'integrity',error=f'{type(e).__name__}: {e}'))
            else:
                common.require(row['seed']==futures[f],'worker seed mismatch');r['candidate_records'].append(row)
                journal.write(json.dumps(row,sort_keys=True)+'\n');journal.flush();os.fsync(journal.fileno())
                if row['status']!='complete':failures.append(dict(seed=row['seed'],kind='infrastructure' if row['status']=='execution_blocked' else 'integrity',error=row.get('error')))
            r['failures']=failures;save()
        if failures:
            if any(f['kind']=='integrity' for f in failures):raise common.IntegrityError('candidate integrity failure; no interpretation')
            raise common.InfrastructureError('candidate infrastructure failure; no interpretation')
    r['candidate_records'].sort(key=lambda x:x['seed']);common.require([x['seed'] for x in r['candidate_records']]==seeds,'incomplete shard')

def finalize(out,cohort,tests):
    out.mkdir(parents=True,exist_ok=True);path=out/'receipt.json';r=json.loads(path.read_text()) if path.exists() else dict(schema='bandido-worker28-v1',candidate_records=[],baseline=[],submission_attempted_seeds=[],submitted_seeds=[],preregistration_url=PREREG)
    if r.get('status')=='complete' and cohort==tests=='success':return
    invalid=tests=='failure' or r.get('status')=='diagnostic_invalid';r.pop('summary',None)
    r.update(status='diagnostic_invalid' if invalid else 'execution_blocked',classification='worker28_invalid' if invalid else None,research_interpretation_performed=False,finalizer_outcomes=dict(cohort=cohort,tests=tests),partial_evidence_note='Inspect sidecars and submission lists; unfinished submitted work may have executed')
    common.write_json(path,r)

def main():
    ap=argparse.ArgumentParser();mode=ap.add_mutually_exclusive_group(required=True);mode.add_argument('--baseline',action='store_true');mode.add_argument('--shard',type=int,choices=range(4));mode.add_argument('--finalize',action='store_true');ap.add_argument('--reference-directory',type=Path);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--cohort-outcome',default='unknown');ap.add_argument('--tests-outcome',default='unknown');a=ap.parse_args()
    if a.finalize:finalize(a.output,a.cohort_outcome,a.tests_outcome);return 0
    a.output.mkdir(parents=True,exist_ok=True);previous=common.preserve_previous_attempt(a.output)
    if (a.output/'games').exists():
        common.require(previous is not None,'orphan sidecars; reconcile before retry');(a.output/'games').rename(a.output/previous/'games')
    seeds=SEEDS if a.baseline else SEEDS[a.shard*100:(a.shard+1)*100]
    r=dict(schema='bandido-worker28-v1',preregistration_url=PREREG,source_reconciliation_url=SOURCE_RECONCILIATION,starting_main=BASE,head=os.environ.get('EVALUATED_COMMIT'),run_id=os.environ.get('GITHUB_RUN_ID'),run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),runner=os.environ.get('RUNNER_NAME'),python=os.sys.version,mode='baseline' if a.baseline else 'spent_candidate_shard',shard=a.shard,seeds=seeds,status='preflight',classification=None,research_interpretation_performed=False,candidate_records=[],baseline=[],submission_attempted_seeds=[],submitted_seeds=[],preserved_previous_attempt=previous)
    started=time.monotonic()
    def save():r['elapsed_seconds']=time.monotonic()-started;common.write_json(a.output/'receipt.json',r)
    save()
    try:
        if a.reference_directory is None:raise FileNotFoundError('reference directory required')
        expected,provenance=preflight(a.reference_directory);r['provenance']=provenance;r['status']='running';save()
        if a.baseline:
            for seed,accepted in zip(SEEDS,expected):
                r['submission_attempted_seeds'].append(seed);save();row=one_game('v4',seed);r['baseline'].append(row);save();common.require(row==accepted,f'baseline replay mismatch {seed}')
            common.require(len(r['baseline'])==400,'incomplete baseline');r['baseline_gate']='400/400 exact'
        else:execute_shard(seeds,a.output,r,save)
        _,after=preflight(a.reference_directory);common.require(after==provenance,'source changed during execution');r['status']='complete';save();return 0
    except (OSError,subprocess.CalledProcessError,common.InfrastructureError) as e:r.update(status='execution_blocked',classification=None,error=f'{type(e).__name__}: {e}')
    except Exception as e:r.update(status='diagnostic_invalid',classification='worker28_invalid',error=f'{type(e).__name__}: {e}')
    r.pop('summary',None);r['research_interpretation_performed']=False;save();return 1

if __name__=='__main__':raise SystemExit(main())
