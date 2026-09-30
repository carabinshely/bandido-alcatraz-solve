"""Synthetic-only tests: all photographed-deck simulations are mocked."""
from concurrent.futures import Future
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from scripts import run_worker27 as w

class Tests(unittest.TestCase):
    def test_exact_four_shards(self):
        seeds=sum((w.shard_seeds(i) for i in range(4)),[])
        self.assertEqual(seeds,list(range(1000000,1000400)))
        self.assertEqual(len(set(seeds)),400)
        for invalid in (-1,4,True,"0"):
            with self.assertRaises(w.common.IntegrityError): w.shard_seeds(invalid)

    def test_ancestry_mismatch_vs_unavailable(self):
        with patch.object(w.subprocess,'run',return_value=SimpleNamespace(returncode=0,stderr='')):
            w.check_ancestry()
        with patch.object(w.subprocess,'run',return_value=SimpleNamespace(returncode=1,stderr='')):
            with self.assertRaises(w.common.IntegrityError):w.check_ancestry()
        with patch.object(w.subprocess,'run',return_value=SimpleNamespace(returncode=128,stderr='missing object')):
            with self.assertRaises(w.common.InfrastructureError):w.check_ancestry()
        with patch.object(w.common,'preflight',side_effect=AssertionError('legacy preflight must not be used')),patch.object(w.common,'git',return_value='head'),patch.dict(w.os.environ,{'EVALUATED_COMMIT':'head','RUNNER_NAME':'bandido-alcatraz-ci'}),patch.object(w,'check_ancestry',side_effect=w.common.InfrastructureError('unavailable')):
            with self.assertRaises(w.common.InfrastructureError):w.preflight()

    def test_pair_identical_seed_and_partial_persistence(self):
        played=SimpleNamespace(won=False,reason="deck_exhausted",turns=2,open_tunnels=3,visible_water_cells=0,raincoats=0,ropes=0,exit_placed=False)
        deck=SimpleNamespace(start_easy=object(),draw_deck=lambda:[])
        for failing in (False,True):
            with tempfile.TemporaryDirectory() as tmp, patch.object(w.common,"load_real_deck",return_value=deck), patch.object(w.common,"play_game",side_effect=[played,OSError("worker IO")] if failing else [played,played]) as game:
                result=w.pair((1000000,tmp))
                self.assertEqual(game.call_count,2)
                self.assertEqual([c.kwargs["seed"] for c in game.call_args_list],[1000000,1000000])
                self.assertIsNotNone(result["v4"])
                self.assertEqual(result["status"],"execution_blocked" if failing else "complete")
                self.assertEqual(json.loads((Path(tmp)/"1000000.json").read_text()),result)
                self.assertFalse(result["research_interpretation_performed"])

    def test_pair_rejects_nonpopulation_before_game(self):
        with patch.object(w.common,"play_game",side_effect=AssertionError("no game")):
            for seed in (999999,1000400):
                with self.assertRaises(w.common.IntegrityError): w.pair((seed,"unused"))

    def test_partial_submission_harvests_success(self):
        class Pool:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def submit(self,fn,task):
                if task[0]==1000001:raise OSError("submit failed")
                f=Future();f.set_result({"seed":task[0],"status":"complete","v4":{},"v7":{}});return f
        r={"submission_attempted_seeds":[],"submitted_seeds":[],"pairs":[]}
        with tempfile.TemporaryDirectory() as tmp, patch.object(w,"ProcessPoolExecutor",return_value=Pool()):
            with self.assertRaises(w.common.InfrastructureError):w.run_shard(w.shard_seeds(0),Path(tmp),r,lambda:None)
            self.assertEqual(r["submission_attempted_seeds"],[1000000,1000001])
            self.assertEqual(r["submitted_seeds"],[1000000])
            self.assertEqual(len(r["pairs"]),1)

    def test_complete_shard_is_sorted_and_uninterpreted(self):
        class Pool:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def submit(self,fn,task):
                f=Future();f.set_result({"seed":task[0],"status":"complete","v4":{},"v7":{}});return f
        r={"submission_attempted_seeds":[],"submitted_seeds":[],"pairs":[]}
        with tempfile.TemporaryDirectory() as tmp, patch.object(w,"ProcessPoolExecutor",return_value=Pool()):
            w.run_shard(w.shard_seeds(1),Path(tmp),r,lambda:None)
            self.assertEqual([p['seed'] for p in r['pairs']],w.shard_seeds(1))
            self.assertNotIn('summary',r)
            self.assertEqual(len((Path(tmp)/'completed.jsonl').read_text().splitlines()),100)

    def test_finalizer_requires_successful_external_outcomes(self):
        for outcome,tests,status in [('success','success','complete'),('failure','success','execution_blocked'),('cancelled','success','execution_blocked'),('success','failure','diagnostic_invalid')]:
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp);w.common.write_json(p/'receipt.json',{'status':'complete','pairs':[{'seed':1000000}]})
                w.finalize(p,outcome,tests);r=json.loads((p/'receipt.json').read_text())
                self.assertEqual(r['status'],status);self.assertEqual(r['pairs'],[{'seed':1000000}])

    def test_preflight_failures_execute_no_games(self):
        for error,status in [(OSError('inaccessible'),'execution_blocked'),(w.common.IntegrityError('source'),'diagnostic_invalid')]:
            with tempfile.TemporaryDirectory() as tmp, patch.object(w,'preflight',side_effect=error),patch.object(w,'run_shard',side_effect=AssertionError('no fresh execution')),patch('sys.argv',['test','--shard','0','--output',tmp]):
                self.assertEqual(w.main(),1);r=json.loads((Path(tmp)/'receipt.json').read_text());self.assertEqual(r['status'],status);self.assertFalse(r['submission_attempted_seeds'])

    def test_baseline_mismatch_blocks(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(w,'preflight',return_value=([{'seed':1000,'won':True}],{})),patch.object(w.common,'one_game',return_value={'seed':1000,'won':False}),patch('sys.argv',['test','--baseline','--output',tmp]):
            self.assertEqual(w.main(),1);r=json.loads((Path(tmp)/'receipt.json').read_text());self.assertEqual(r['status'],'diagnostic_invalid');self.assertEqual(len(r['baseline']),1)

if __name__=='__main__':unittest.main()
