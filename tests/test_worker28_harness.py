import hashlib,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from concurrent.futures import Future
from scripts import run_worker28 as w

def inputs(root):
    inventory=[]
    for i in range(4):
        seeds=w.SEEDS[i*100:(i+1)*100]
        r=dict(status='complete',head='accepted',shard=i,seeds=seeds,pairs=[dict(seed=s,v4=dict(seed=s,won=False)) for s in seeds])
        raw=json.dumps(r).encode();p=root/f'shard-{i}'/'receipt.json';p.parent.mkdir();p.write_bytes(raw)
        inventory.append(dict(label=f'shard-{i}',receipt_bytes=len(raw),receipt_sha256=hashlib.sha256(raw).hexdigest()))
    return dict(evaluated_commit='accepted',raw_artifact=dict(contained_actions_archives=inventory))

class Tests(unittest.TestCase):
    def test_reference_complete_and_missing_vs_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);m=inputs(root);rows,h=w.reference_rows(root,m)
            self.assertEqual([r['seed'] for r in rows],w.SEEDS);self.assertEqual(len(h),4)
            p=root/'shard-0/receipt.json';b=p.read_bytes();p.write_bytes(b+b' ')
            with self.assertRaises(w.common.IntegrityError):w.reference_rows(root,m)
            p.unlink()
            with self.assertRaises(FileNotFoundError):w.reference_rows(root,m)

    def test_reject_seed_before_simulation(self):
        with patch.object(w.common,'play_game',side_effect=AssertionError('no real games')):
            with self.assertRaises(w.common.IntegrityError):w.one_game('v8',999999)

    def test_ancestry_error_vs_mismatch(self):
        with patch.object(w.common,'git',return_value='head'),patch.dict(w.os.environ,{'EVALUATED_COMMIT':'head','RUNNER_NAME':'bandido-alcatraz-ci'}):
            for code,exception in [(1,w.common.IntegrityError),(128,w.common.InfrastructureError)]:
                with patch.object(w.subprocess,'run',return_value=SimpleNamespace(returncode=code,stderr='reason')):
                    with self.assertRaises(exception):w.preflight(Path('unused'))

    def test_step_limit_record_is_retained(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(w,'one_game',return_value={'seed':1000000,'reason':'step_limit'}):
            r=w.candidate((1000000,tmp));self.assertEqual(r['status'],'diagnostic_invalid');self.assertEqual(r['record']['reason'],'step_limit');self.assertEqual(json.loads((Path(tmp)/'1000000.json').read_text()),r)

    def test_partial_submit_drains_completed(self):
        class Pool:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def submit(self,fn,task):
                if task[0]==1000001:raise OSError('scheduler')
                f=Future();f.set_result(dict(seed=task[0],status='complete',record={}));return f
        r=dict(submission_attempted_seeds=[],submitted_seeds=[],candidate_records=[])
        with tempfile.TemporaryDirectory() as tmp,patch.object(w,'ProcessPoolExecutor',return_value=Pool()):
            with self.assertRaises(w.common.InfrastructureError):w.execute_shard(w.SEEDS[:100],Path(tmp),r,lambda:None)
            self.assertEqual(r['submitted_seeds'],[1000000]);self.assertEqual(len(r['candidate_records']),1)

    def test_preflight_failure_has_zero_execution(self):
        for error,status in [(FileNotFoundError('input'),'execution_blocked'),(w.common.IntegrityError('corrupt'),'diagnostic_invalid')]:
            with tempfile.TemporaryDirectory() as tmp,patch.object(w,'preflight',side_effect=error),patch.object(w,'execute_shard',side_effect=AssertionError('no research')),patch('sys.argv',['test','--shard','0','--output',tmp,'--reference-directory',tmp]):
                self.assertEqual(w.main(),1);r=json.loads((Path(tmp)/'receipt.json').read_text());self.assertEqual(r['status'],status);self.assertEqual(r['submission_attempted_seeds'],[]);self.assertFalse(r['research_interpretation_performed'])

    def test_finalizer_reconciles_failed_outcomes(self):
        for cohort,tests,status in [('success','success','complete'),('failure','success','execution_blocked'),('success','failure','diagnostic_invalid'),('unknown','success','execution_blocked')]:
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp);w.common.write_json(p/'receipt.json',dict(status='complete',summary={'advance':True},research_interpretation_performed=True,candidate_records=[{'seed':1000000}]))
                w.finalize(p,cohort,tests);r=json.loads((p/'receipt.json').read_text());self.assertEqual(r['status'],status);self.assertEqual(r['candidate_records'],[{'seed':1000000}])
                if status!='complete':self.assertNotIn('summary',r);self.assertFalse(r['research_interpretation_performed'])

if __name__=='__main__':unittest.main()
