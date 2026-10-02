"""Shared hand-computed invented metadata fixtures; no real inputs or engine imports."""
import copy
import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
A=module('worker34_parser_a');B=module('worker34_parser_b')
def action(kind,index,origin=None,turns=0):
    return {'action':kind,'hand_index':index,'origin':[0,0] if kind=='place' and origin is None else origin,'quarter_turns':turns}
def snapshot():
    return {'board':{'cells':[],'placements':[]},'hand':[{'card_id':n,'material':m,'is_exit':x,'cells':[]} for n,m,x in [('coat','raincoat',False),('plain',None,False),('exit',None,True),('rope','rope',False),('other',None,False),('last',None,False)]],'raincoats':1,'ropes':1,'exit_placed':False,'exit_seen':False,'turns':0,'set_aside_unplayable':0,'collected_equipment':[],'setup':{'hand_size':6,'player_count':1,'start_side':'easy-5-exit','starting_player':0},'player_index':0}
class CrossParserTests(unittest.TestCase):
    def test_hand_computed_components_and_wire(self):
        for g in (4,5,6):
            for exits in (False,True):
                for carry in (False,True):
                    for source_pass in (1,2):
                        with self.subTest(g=g,exits=exits,carry=carry,source_pass=source_pass):
                            s=snapshot();e={'position':62 if carry else 1,'seed':1000089 if carry else 1000000,'ordinal':15 if carry else 1}
                            ident=dict(e,source_pass=source_pass,source_implementation='candidate' if source_pass==1 else 'reference',call_number=e['position']+80*(source_pass-1))
                            definitions=[([action('collect',0),action('place',0)],30005,'horizon'),([action('place',2 if exits else 0),action('place',1 if exits else 0)],(15000 if exits else 20000)+g,'horizon')]
                            if carry:definitions.append(([action('place',5,[-5,-2],3)],29900,'omitted_draw_dead_end'))
                            ar=[];br=[]
                            for index,(seq,h,reason) in enumerate(definitions):
                                leaf={'sequence':seq,'key':[1,0,h],'reason':reason,'transition_sha256':'a'*64}
                                ar.append(A.normalize_leaf(copy.deepcopy(s),copy.deepcopy(leaf),ident,index,0))
                                br.append(B.leaf_row(copy.deepcopy(s),copy.deepcopy(leaf),e,source_pass,index,0))
                            A.classify(ar);ao=A.observation_row(e,ar);bo=B.classify(br,s,e)
                            self.assertEqual(A.encode(ar),B.canonical(br));self.assertEqual(A.encode(ao),B.canonical(bo))
                            pp=ar[1];self.assertEqual(pp['geometric_score'],g)
                            self.assertEqual(pp['pp_classification'],'unmatched_exit_stratum' if exits else ('geometric_tradeoff' if g>5 else 'component_dominated'))
                            self.assertEqual(pp['equipment_term'],20000);self.assertEqual(pp['exit_term'],-5000 if exits else 0)
                            self.assertEqual(ar[0]['geometric_score'],5)
                            if carry:self.assertEqual(ar[2]['role'],'excluded_depth_one_carry');self.assertIsNone(ar[2]['witness'])
    def test_impossible_collect_quota_rejected(self):
        s=snapshot();s['raincoats']=3;e={'position':1,'seed':1000000,'ordinal':1};ident=dict(e,source_pass=1,source_implementation='candidate',call_number=1)
        leaf={'sequence':[action('collect',0),action('place',0)],'key':[1,0,50000],'reason':'horizon','transition_sha256':'a'*64}
        with self.assertRaises(Exception):A.normalize_leaf(s,leaf,ident,0,0)
        with self.assertRaises(Exception):B.leaf_row(s,leaf,e,1,0,0)
if __name__=='__main__':unittest.main()
