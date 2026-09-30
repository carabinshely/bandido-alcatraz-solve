import copy
import unittest
from scripts import aggregate_worker27 as a

def record(seed,win=False):
    return dict(seed=seed,won=win,reason='win' if win else 'deck_exhausted',turns=69,final_open_tunnels=0 if win else 3,visible_water=0,raincoats=3,ropes=2,exit_placed=True,equipment_ready=True,exit_equipment_water_ready=True)

def population(gains):
    return [dict(seed=s,status='complete',research_interpretation_performed=False,v4=record(s),v7=record(s,i<gains)) for i,s in enumerate(a.SEEDS)]

class Tests(unittest.TestCase):
    def test_threshold_fixed(self):
        self.assertFalse(a.summarize(population(7))['advance']);self.assertTrue(a.summarize(population(8))['advance'])
    def test_reject_partial_duplicate_wrong_population(self):
        x=population(0)
        for rows in (x[:-1],x+[x[0]],x[:-1]+[x[0]]):
            with self.assertRaises(ValueError):a.summarize(rows)
    def test_no_false_positive_terminal_record(self):
        x=population(0);x[0]['v7']['won']=True
        with self.assertRaises(ValueError):a.summarize(x)
    def test_no_interpreted_or_incomplete_pair(self):
        for key,value in [('status','execution_blocked'),('research_interpretation_performed',True)]:
            x=population(0);x[0][key]=value
            with self.assertRaises(ValueError):a.summarize(x)
    def test_loss_and_gain_arithmetic(self):
        x=population(8);x[10]['v4']=record(x[10]['seed'],True);s=a.summarize(x)
        self.assertEqual(s['net_wins'],7);self.assertFalse(s['advance']);self.assertEqual(len(s['lost']),1)

if __name__=='__main__':unittest.main()
