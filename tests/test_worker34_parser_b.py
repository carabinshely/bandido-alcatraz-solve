"""Parser B synthetic-only tests. No repository engine and no real artifact reads."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

MODULE = Path(__file__).resolve().parents[1] / 'scripts' / 'worker34_parser_b.py'
spec = importlib.util.spec_from_file_location('worker34_parser_b_synthetic', MODULE)
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


def card(name, material=None, is_exit=False):
    return dict(card_id=name, material=material, is_exit=is_exit, cells=[])


def snapshot(hand=None, rain=1, rope=0, exit_flag=False):
    return dict(board=dict(cells=[], placements=[]), collected_equipment=[], exit_placed=exit_flag,
                exit_seen=False, hand=hand if hand is not None else [card('synthetic-r', 'raincoat'),
                card('synthetic-p', 'rope'), card('synthetic-plain'), card('synthetic-exit', is_exit=True)],
                player_index=0, raincoats=rain, ropes=rope, set_aside_unplayable=0,
                setup=dict(hand_size=6, player_count=1, start_side='easy-5-exit', starting_player=0), turns=0)


def action(kind, index, origin=(0, 0), turns=0):
    return dict(action=kind, hand_index=index, origin=None if kind == 'collect' else list(origin), quarter_turns=turns)


def entry(position=1, seed=1000000, ordinal=1):
    return dict(position=position, seed=seed, ordinal=ordinal)


def leaf(sequence, h, reason='horizon'):
    return dict(sequence=sequence, key=[1, 0, h], reason=reason, transition_sha256='a' * 64)


def row(s, sequence, h, root=0, index=0, e=None):
    return b.leaf_row(s, leaf(sequence, h), e or entry(), 1, root, index)


def payload_fixture(position=1, source_pass=1):
    """Two synthetic roots, with manually supplied H; this is not a game state."""
    s = snapshot([card('synthetic-r','raincoat'),card('plain-1'),card('plain-2'),card('exit',is_exit=True)])
    e = entry(position)
    e.update(B=2, collect_count_metadata=1, place_count_metadata=1,
             public_observation_sha256=b.digest(s))
    cp = [action('collect', 0), action('place', 0)]
    pp = [action('place', 0), action('place', 0)]
    roots = []
    for sequence, h in ((cp, 20005), (pp, 10005)):
        leaves = [leaf(sequence, h)]
        seconds = [sequence[1]]
        roots.append(dict(root=sequence[0], first_transition_sha256='b' * 64,
                          second_moves=seconds, second_moves_sha256=b.digest(seconds), leaves=leaves,
                          leaves_sha256=b.digest(leaves), maximum=[1, 0, h], witness=sequence))
    root_actions = [r['root'] for r in roots]
    baseline = dict(root_moves_sha256=b.digest(root_actions), collect_count=1, place_count=1)
    science = dict(schema='worker32-scientific-v1', best=[1, 0, 20005], chosen=cp[0],
                   counts=dict(roots=2, children=2, previews=4, expanded_nodes=3, enumerations=3, leaves=2),
                   input_before=b.digest(s), input_after=b.digest(s), maximal_roots=[cp[0]],
                   rng_before='c' * 64, rng_after='d' * 64, root_moves_sha256=b.digest(root_actions), roots=roots)
    envelope = dict(call=position + (source_pass - 1) * 80, cpu_seconds=0.0,
                    finished='2026-01-01T00:00:01+00:00', started='2026-01-01T00:00:00+00:00',
                    implementation='candidate' if source_pass == 1 else 'reference', ordinal=1,
                    seed=1000000, **{'pass': source_pass}, peak_rss_kib=1, physical_legal_moves=3,
                    run_attempt='1', run_id=str(b.RUN), wall_seconds=1.0)
    return dict(envelope=envelope, scientific=science), s, e, baseline


def population_fixture():
    s = snapshot([card('synthetic-r','raincoat'),card('plain-1'),card('plain-2'),card('exit',is_exit=True)])
    h = b.digest(s)
    entries, snapshots, audits = [], [], []
    for pos in range(1, 81):
        seed = 1000000 + ((pos - 1) % 71)
        ordinal = 1 if pos <= 71 else 2
        text = f'mixed-action-two-action-diagnostic-v1|{seed}|{ordinal}|{h}'
        e = dict(position=pos, seed=seed, ordinal=ordinal, B=2, C=1, action_type_class='mixed',
                 collect_count_metadata=1, place_count_metadata=1, group='hash64' if pos <= 64 else 'stress16',
                 public_observation_sha256=h, snapshot_sha256=h, snapshot_size_bytes=len(b.canonical(s)),
                 source_trace_member=f'decision-traces/pass-2/{seed}.jsonl', source_trace_sha256='a' * 64,
                 stress_cost_proxy=6, selection_key_input=text,
                 selection_key_sha256=hashlib.sha256(text.encode()).hexdigest(),
                 snapshot_file=f'snapshots/{pos:03d}-seed-{seed}-ordinal-{ordinal:03d}.json')
        tier = [action('collect', 0)]
        a = dict(position=pos, seed=seed, ordinal=ordinal, public_observation_sha256=h,
                 legal_move_count=2, primary_score=10000, primary_tier=tier, primary_tier_sha256=b.digest(tier))
        entries.append(e); snapshots.append(copy.deepcopy(s)); audits.append(a)
    return dict(schema='worker33-mixed-public-state-selection-preparation-v1', entries=entries), snapshots, audits


class JsonAndWireTests(unittest.TestCase):
    def test_duplicate_keys_rejected_at_every_depth(self):
        for raw in (b'{"a":1,"a":2}', b'{"nested":{"x":1,"x":2}}'):
            with self.subTest(raw=raw), self.assertRaises(b.IntegrityError):
                b.decode(raw, 'synthetic')

    def test_nonfinite_and_bad_utf8_rejected(self):
        for raw in (b'NaN', b'Infinity', b'-Infinity', b'1e999', b'\xff', b'\xef\xbb\xbf{}'):
            with self.subTest(raw=raw), self.assertRaises(b.IntegrityError):
                b.decode(raw, 'synthetic')

    def test_strict_jsonl_framing(self):
        for raw in (b'{}', b'{}\n\n', b'\n'):
            with self.assertRaises(b.IntegrityError):
                b.json_lines(raw, 'synthetic')
        self.assertEqual(b.json_lines(b'{}\n', 'synthetic'), [{}])

    def test_exact_canonical_wire(self):
        self.assertEqual(b.canonical({'z':None, '\u00e9':True, 'a':{'y':2,'b':1}}),
                         b'{"a":{"b":1,"y":2},"z":null,"\\u00e9":true}\n')
        with self.assertRaises(ValueError):
            b.canonical(float('nan'))

    def test_size_and_digest_corruption(self):
        pin = (3, hashlib.sha256(b'abc').hexdigest())
        self.assertEqual(b.checked_bytes(b'abc', pin, 'fixture'), b'abc')
        for raw in (b'ab', b'abd', b'abcd'):
            with self.assertRaises(b.IntegrityError):
                b.checked_bytes(raw, pin, 'fixture')


class BookkeepingTests(unittest.TestCase):
    def test_index_shift_and_separate_materials(self):
        s = snapshot()
        n, rain, rope, flag = b.resolve_sequence(s, [action('collect',0), action('collect',0)])
        self.assertEqual(([a['original_hand_index'] for a in n], [a['card_id'] for a in n]),
                         ([0,1], ['synthetic-r','synthetic-p']))
        self.assertEqual((rain,rope,flag),(2,1,False))
        n, rain, rope, _ = b.resolve_sequence(s, [action('place',1), action('collect',0)])
        self.assertEqual([a['original_hand_index'] for a in n],[1,0])
        self.assertEqual((rain,rope),(2,0))

    def test_two_same_material_cards_quota_boundary(self):
        s = snapshot([card('r1','raincoat'), card('r2','raincoat')])
        _, rain, rope, _ = b.resolve_sequence(s, [action('collect',0), action('collect',0)])
        self.assertEqual((rain,rope),(3,0))
        s['raincoats'] = 2
        with self.assertRaises(b.IntegrityError):
            b.resolve_sequence(s, [action('collect',0), action('collect',0)])

    def test_endpoint_exit_readiness_both_action_orders(self):
        s = snapshot([card('exit',is_exit=True),card('r','raincoat')],rain=2,rope=2)
        for seq in ([action('place',0),action('collect',0)], [action('collect',1),action('place',0)]):
            result = row(s,seq,55123)
            self.assertEqual((result['inventory'],result['exit_placed'],result['equipment_term'],result['exit_term'],result['geometric_score']),
                             ({'raincoats':3,'ropes':2},True,50000,5000,123))

    def test_exit_unready_and_initial_true(self):
        s = snapshot([card('exit',is_exit=True),card('plain')], rain=2,rope=1)
        result = row(s,[action('place',0),action('place',0)],24990)
        self.assertEqual((result['exit_term'],result['geometric_score']),(-5000,-10))
        s = snapshot([card('r','raincoat'),card('plain')],rain=2,rope=2,exit_flag=True)
        result = row(s,[action('collect',0),action('place',0)],55008)
        self.assertEqual((result['exit_term'],result['geometric_score']),(5000,8))

    def test_place_equipment_at_quota_is_valid(self):
        s = snapshot([card('r','raincoat'),card('p','rope')],rain=3,rope=2)
        result = row(s,[action('place',0),action('place',0)],50011)
        self.assertEqual((result['inventory'], result['geometric_score']),({'raincoats':3,'ropes':2},11))
        with self.assertRaises(b.IntegrityError):
            b.resolve_sequence(s,[action('collect',0)])

    def test_original_card_validation(self):
        mutations = [lambda s:s['hand'][1].update(card_id=s['hand'][0]['card_id']),
                     lambda s:s['hand'][0].update(card_id=''),
                     lambda s:s['hand'][0].update(material='gold'),
                     lambda s:s['hand'][0].update(is_exit=1),
                     lambda s:s['hand'][3].update(material='rope'),
                     lambda s:s['hand'][2].update(is_exit=True),
                     lambda s:s.update(exit_placed=True),
                     lambda s:s['hand'][0].update(unexpected=1)]
        for mutate in mutations:
            s=snapshot(); mutate(s)
            with self.subTest(mutation=mutate), self.assertRaises(b.IntegrityError):
                b.resolve_sequence(s,[action('place',0)])

    def test_exact_inventory_types(self):
        for key, values in [('raincoats',[True,1.0,'1',-1,4]), ('ropes',[False,1.0,'1',-1,3]),
                            ('exit_placed',[0,1,'false',None])]:
            for value in values:
                s=snapshot();s[key]=value
                with self.subTest(key=key,value=value),self.assertRaises(b.IntegrityError):
                    b.resolve_sequence(s,[action('place',0)])

    def test_malformed_actions(self):
        fixtures = []
        for value in [True,0.0,'0',-1,4]:
            fixtures.append(dict(action('place',0), hand_index=value))
        for value in [True,0.0,'0',-1,4]:
            fixtures.append(dict(action('place',0), quarter_turns=value))
        for origin in [None,[0],[0,0,0],[True,0],[0.0,0],['0',0]]:
            fixtures.append(dict(action('place',0), origin=origin))
        fixtures += [dict(action('collect',0),origin=[0,0]),dict(action('collect',0),quarter_turns=1),
                     dict(action('place',0),action='refresh'),dict(action('place',0),extra=0),
                     {'action':'place','hand_index':0,'origin':[0,0]}]
        for value in fixtures:
            with self.subTest(action=value),self.assertRaises(b.IntegrityError):
                b.resolve_sequence(snapshot(),[value])

    def test_retained_index_no_draw_or_reuse(self):
        for seq in ([action('place',3),action('place',3)],
                    [action('place',0),action('place',0),action('place',0)]):
            with self.assertRaises(b.IntegrityError):
                b.resolve_sequence(snapshot(),seq)
        for idx in (2,3):
            with self.assertRaises(b.IntegrityError):
                b.resolve_sequence(snapshot(),[action('collect',idx)])

    def test_terminal_placeholder_never_subtracted(self):
        for reason,key in [('visible_victory',[2,-2,0]),('closed_tunnel_loss',[0,0,100]),
                           ('horizon',[2,-2,0]),('horizon',[1,True,100]),('unknown',[1,0,100])]:
            item=leaf([action('place',0),action('place',0)],100,reason); item['key']=key
            with self.subTest(reason=reason,key=key),self.assertRaises(b.IntegrityError):
                b.leaf_row(snapshot(),item,entry(),1,0,0)

    def test_exact_carry_is_separate(self):
        s=snapshot([card('plain'+str(i)) for i in range(6)],rain=2)
        carry=leaf([action('place',5,(-5,-2),3)],29900,'omitted_draw_dead_end')
        e=entry(62,1000089,15)
        r=b.leaf_row(s,carry,e,2,17,0)
        observation=b.classify([r],s,e)
        self.assertEqual((r['role'],r['pattern'],r['geometric_score'],r['call_number']),
                         ('excluded_depth_one_carry','P',9900,142))
        self.assertIsNone(r['pp_classification']);self.assertIsNone(r['witness'])
        self.assertEqual((observation['carry_leaf_count'],observation['horizon_leaf_count']), (1,0))
        self.assertTrue(observation['has_no_eligible_pp'])
        self.assertEqual([x['pp_count']+x['collection_count'] for x in observation['strata']],[0,0])
        for wrong in [entry(61,1000089,15),entry(62,1000088,15),entry(62,1000089,14)]:
            with self.assertRaises(b.IntegrityError): b.leaf_row(s,carry,wrong,1,0,0)


class InertBoardSchemaTests(unittest.TestCase):
    @staticmethod
    def board():
        # Intentionally unrelated coordinates and indices. Wire validation does
        # not determine placement legality or reconstruct a board/history.
        return dict(cells=[dict(x=-17,y=100,water=True,tunnel_edges=['E','N','S','W']),
                           dict(x=450,y=-90,water=False,tunnel_edges=[])],
                    placements=[dict(card_id='synthetic-start',origin=[40,-50],quarter_turns=3,
                                     placement_index=999,kind='start',cells=[[4,8],[27,-40]],
                                     overlaps=[],covered_placement_index=None),
                                dict(card_id='synthetic-ordinary',origin=[9,31],quarter_turns=0,
                                     placement_index=4,kind='ordinary',cells=[[9,31]],
                                     overlaps=[[80,-65]],covered_placement_index=17),
                                dict(card_id='synthetic-exit-history',origin=[-30,11],quarter_turns=2,
                                     placement_index=0,kind='exit',cells=[],overlaps=[],
                                     covered_placement_index=0)])

    def reject_board(self,board):
        s=snapshot();s['board']=board
        with self.assertRaises(b.IntegrityError):b.validate_snapshot(s)

    def test_valid_inert_nested_values_preserved_without_geometry_checks(self):
        s=snapshot();s['board']=self.board();before=b.canonical(s)
        b.validate_snapshot(s)
        self.assertEqual(b.canonical(s),before)
        b.validate_snapshot(snapshot())  # Empty inert arrays retain valid wire types.

    def test_null_boolean_and_wrong_container_items_rejected(self):
        for field in ('cells','placements'):
            for value in (None,True,{},'array',1):
                board=self.board();board[field]=value
                with self.subTest(field=field,value=value):self.reject_board(board)
            for value in (None,True,[],{},'item',1):
                board=self.board();board[field]=[value]
                with self.subTest(field=field,item=value):self.reject_board(board)

    def test_cell_missing_and_extra_fields_rejected(self):
        for field in self.board()['cells'][0]:
            board=self.board();del board['cells'][0][field]
            with self.subTest(missing=field):self.reject_board(board)
        board=self.board();board['cells'][0]['extra']=0;self.reject_board(board)

    def test_cell_coordinate_boolean_and_edges_exact_types(self):
        for field in ('x','y'):
            for value in (True,False,1.0,'1',None,[],{}):
                board=self.board();board['cells'][0][field]=value
                with self.subTest(field=field,value=value):self.reject_board(board)
        for value in (0,1,1.0,'true',None,[],{}):
            board=self.board();board['cells'][0]['water']=value
            with self.subTest(water=value):self.reject_board(board)
        for value in (None,True,'N',{},0,[None],[True],[1],[[]],[{}],['invalid-direction']):
            board=self.board();board['cells'][0]['tunnel_edges']=value
            with self.subTest(edges=value):self.reject_board(board)

    def test_placement_missing_and_extra_fields_rejected(self):
        for field in self.board()['placements'][0]:
            board=self.board();del board['placements'][0][field]
            with self.subTest(missing=field):self.reject_board(board)
        board=self.board();board['placements'][0]['extra']=0;self.reject_board(board)

    def test_placement_scalar_exact_types_and_wire_enums(self):
        for field,values in [('card_id',[None,True,1,1.0,[],{},'']),
                             ('kind',[None,True,1,1.0,[],{},'unknown']),
                             ('placement_index',[None,True,False,1.0,'1',[],{},-1]),
                             ('covered_placement_index',[True,False,1.0,'1',[],{},-1]),
                             ('quarter_turns',[None,True,False,1.0,'1',[],{},-1,4])]:
            for value in values:
                board=self.board();board['placements'][0][field]=value
                with self.subTest(field=field,value=value):self.reject_board(board)

    def test_placement_nested_coordinates_exact_types(self):
        invalid=(None,True,1,1.0,'1',{},[],[0],[0,1,2],[True,0],[0,False],
                 [0.0,1],[0,1.0],['0',1],[0,'1'],[[0],1],[0,{}])
        for field in ('origin','cells','overlaps'):
            for value in invalid:
                board=self.board()
                board['placements'][0][field]=value if field=='origin' else [value]
                with self.subTest(field=field,value=value):self.reject_board(board)
        for field in ('cells','overlaps'):
            for value in (None,True,1,'coordinates',{}):
                board=self.board();board['placements'][0][field]=value
                with self.subTest(field=field,container=value):self.reject_board(board)


class InertTunnelEdgeRepresentationTests(unittest.TestCase):
    @staticmethod
    def snapshot_with_edges(location,edges):
        s=snapshot()
        cell=dict(x=-17,y=100,water=False,tunnel_edges=copy.deepcopy(edges))
        if location=='hand':
            s['hand'][0]['cells']=[cell]
        elif location=='collected':
            collected=card('synthetic-collected','raincoat');collected['cells']=[cell]
            s['collected_equipment']=[dict(card=collected,turn=1,player_index=0)]
        else:
            s['board']['cells']=[cell]
        return s

    def test_eight_reported_wire_gaps_rejected(self):
        cases=[('hand',['invalid-direction']),('collected',['invalid-direction']),
               ('hand',['N','N']),('collected',['N','N']),('board',['N','N']),
               ('hand',['N','E']),('collected',['N','E']),('board',['N','E'])]
        self.assertEqual(len(cases),8)
        for location,edges in cases:
            s=self.snapshot_with_edges(location,edges);before=b.canonical(s)
            with self.subTest(location=location,edges=edges),self.assertRaises(b.IntegrityError):
                b.validate_snapshot(s)
            self.assertEqual(b.canonical(s),before)  # Reject rather than silently normalize.

    def test_canonical_valid_edge_lists_preserved_in_all_three_locations(self):
        for location in ('hand','collected','board'):
            for edges in ([],['N'],['E','N'],['E','N','S','W']):
                s=self.snapshot_with_edges(location,edges);before=b.canonical(s)
                with self.subTest(location=location,edges=edges):b.validate_snapshot(s)
                self.assertEqual(b.canonical(s),before)

    def test_exact_edge_and_container_types_in_all_three_locations(self):
        for location in ('hand','collected','board'):
            for edges in (None,True,'N',{},[True],[1],[None],[[]],[{}]):
                with self.subTest(location=location,edges=edges),self.assertRaises(b.IntegrityError):
                    b.validate_snapshot(self.snapshot_with_edges(location,edges))


class DominanceTests(unittest.TestCase):
    def test_equal_g_dominates_pp_and_tradeoff_best_first_witness(self):
        s=snapshot()
        rows=[row(s,[action('collect',0),action('place',0)],20005,0),
              row(s,[action('place',0),action('collect',0)],20007,1),
              row(s,[action('collect',0),action('place',1)],20007,2),
              row(s,[action('place',0),action('place',0)],10005,3),
              row(s,[action('place',0),action('place',1)],10006,4),
              row(s,[action('place',1),action('place',1)],10008,5)]
        result=b.classify(rows,s,entry())
        self.assertEqual([r['pp_classification'] for r in rows[3:]],
                         ['component_dominated','component_dominated','geometric_tradeoff'])
        self.assertEqual([r['witness'] for r in rows[3:]],
                         [dict(root_index=0,leaf_index=0),dict(root_index=1,leaf_index=0),dict(root_index=1,leaf_index=0)])
        self.assertTrue(result['has_tradeoff'])
        self.assertEqual(result['strata'][0]['class_counts'],dict(component_dominated=2,geometric_tradeoff=1,unmatched_exit_stratum=0))

    def test_duplicate_vectors_ties_and_sorted_multiplicity(self):
        s=snapshot()
        rows=[row(s,[action('collect',0),action('place',0)],20005,0),
              row(s,[action('collect',0),action('place',1)],20005,1),
              row(s,[action('place',0),action('place',0)],10005,2),
              row(s,[action('place',0),action('place',1)],10005,3)]
        result=b.classify(rows,s,entry())
        vectors=result['strata'][0]['vector_multiplicities']
        self.assertEqual([v['pattern'] for v in vectors],['CC','CP','PC','PP'])
        self.assertEqual(vectors[1]['vectors'],[[2,0,5,2]])
        self.assertEqual(vectors[3]['vectors'],[[1,0,5,2]])
        self.assertEqual(rows[2]['witness'],rows[3]['witness'])

    def test_exit_strata_never_mix_and_empty_maxima_are_null(self):
        s=snapshot()
        rows=[row(s,[action('collect',0),action('place',0)],20050,0),
              row(s,[action('place',0),action('place',2)],5001,1)]
        result=b.classify(rows,s,entry())
        self.assertEqual(rows[1]['geometric_score'],1)
        self.assertEqual(rows[1]['pp_classification'],'unmatched_exit_stratum')
        self.assertIsNone(rows[1]['witness'])
        self.assertTrue(result['has_unmatched_exit_stratum']);self.assertFalse(result['has_tradeoff'])
        self.assertIsNone(result['strata'][0]['pp_max_geometric_score'])
        self.assertIsNone(result['strata'][1]['collection_max_geometric_score'])

    def test_no_pp_and_unequal_inventory_coordinates(self):
        s=snapshot()
        rows=[row(s,[action('collect',0),action('place',0)],20005,0),
              row(s,[action('place',0),action('collect',0)],20005,1),
              row(s,[action('collect',0),action('collect',0)],30005,2)]
        result=b.classify(rows,s,entry())
        self.assertTrue(result['has_no_eligible_pp'])
        self.assertEqual(result['strata'][0]['collection_count'],3)
        vectors=result['strata'][0]['vector_multiplicities']
        self.assertEqual([x['vectors'] for x in vectors],[[[2,1,5,1]],[[2,0,5,1]],[[1,1,5,1]],[]])

    def test_corrupt_inventory_cannot_exploit_pattern_label(self):
        s=snapshot()
        c=row(s,[action('collect',0),action('place',0)],20005,0)
        c['inventory']={'raincoats':0,'ropes':2}
        with self.assertRaises(b.IntegrityError): b.classify([c],s,entry())
        p=row(s,[action('place',0),action('place',0)],10005,0)
        p['inventory']={'raincoats':2,'ropes':0}
        with self.assertRaises(b.IntegrityError): b.classify([p],s,entry())


class PayloadTests(unittest.TestCase):
    def test_complete_synthetic_call_and_pass_identity(self):
        for source_pass in (1,2):
            payload,s,e,baseline=payload_fixture(source_pass=source_pass)
            rows,obs=b.parse_call(payload,s,e,baseline,source_pass)
            self.assertEqual(len(rows),2)
            self.assertEqual(rows[1]['pp_classification'],'component_dominated')
            self.assertEqual(rows[0]['source_implementation'],'candidate' if source_pass==1 else 'reference')
            self.assertEqual(rows[0]['call_number'],1 if source_pass==1 else 81)
            self.assertEqual(obs['horizon_leaf_count'],2)

    def test_pass_mismatch_and_boolean_identities(self):
        for name,value in [('pass',2),('call',81),('implementation','reference'),('seed',1000001),
                           ('ordinal',2),('run_id',str(b.RUN+1)),('run_attempt','2'),('pass',True),('call',True)]:
            p,s,e,base=payload_fixture();p['envelope'][name]=value
            with self.subTest(name=name,value=value),self.assertRaises(b.IntegrityError):b.parse_call(p,s,e,base,1)

    def test_corrupt_scientific_binding(self):
        changes=[lambda p:p['scientific'].update(input_after='f'*64),
                 lambda p:p['scientific'].update(root_moves_sha256='f'*64),
                 lambda p:p['scientific']['counts'].update(leaves=True),
                 lambda p:p['scientific'].update(best=[1,0,0]),
                 lambda p:p['scientific'].update(maximal_roots=[]),
                 lambda p:p['scientific'].update(schema='unsupported'),
                 lambda p:p['scientific']['roots'][0].update(maximum=[1,0,0]),
                 lambda p:p['scientific']['roots'][0].update(witness=[]),
                 lambda p:p['scientific']['roots'][0].update(leaves_sha256='f'*64),
                 lambda p:p['scientific']['roots'][0].update(second_moves_sha256='f'*64)]
        for mutate in changes:
            p,s,e,base=payload_fixture();mutate(p)
            with self.subTest(mutate=mutate),self.assertRaises(b.IntegrityError):b.parse_call(p,s,e,base,1)

    def test_rehashed_sequence_root_mismatch(self):
        p,s,e,base=payload_fixture();r=p['scientific']['roots'][0]
        r['leaves'][0]['sequence'][1]=action('place',1)
        r['leaves_sha256']=b.digest(r['leaves'])
        with self.assertRaises(b.IntegrityError):b.parse_call(p,s,e,base,1)


    def test_chosen_and_witness_reject_boolean_index_even_if_equal(self):
        for field in ('chosen','maximal_roots','witness'):
            p,s,e,base=payload_fixture()
            if field=='chosen':
                p['scientific']['chosen']=dict(p['scientific']['chosen'],hand_index=False)
            elif field=='maximal_roots':
                p['scientific']['maximal_roots']=[dict(p['scientific']['maximal_roots'][0],hand_index=False)]
            else:
                p['scientific']['roots'][0]['witness']=[dict(p['scientific']['roots'][0]['witness'][0],hand_index=False),action('place',0)]
            with self.subTest(field=field),self.assertRaises(b.IntegrityError):b.parse_call(p,s,e,base,1)

    def test_rehashed_duplicate_second_actions(self):
        p,s,e,base=payload_fixture();r=p['scientific']['roots'][0]
        r['second_moves']*=2;r['leaves']*=2
        r['leaves_sha256']=b.digest(r['leaves']);r['second_moves_sha256']=b.digest(r['second_moves'])
        with self.assertRaises(b.IntegrityError):b.parse_call(p,s,e,base,1)


class PopulationAndSummaryTests(unittest.TestCase):
    def test_fixed_80_observations_71_seeds_and_160_order(self):
        m,s,a=population_fixture();entries=b.validate_population(m,s,a)
        order=[dict(position=e['position'],seed=e['seed'],ordinal=e['ordinal'],pass_number=p)
               for p in (1,2) for e in entries]
        b.validate_call_order(order,entries)
        for wrong in (order[:-1],order+[order[-1]],list(reversed(order))):
            with self.assertRaises(b.IntegrityError):b.validate_call_order(wrong,entries)
        wrong=copy.deepcopy(order);wrong[0]['pass_number']=True
        with self.assertRaises(b.IntegrityError):b.validate_call_order(wrong,entries)

    def test_missing_duplicate_or_hash_corrupt_observation(self):
        for variant in ('missing','duplicate','order','hash','bool','extra'):
            m,s,a=population_fixture()
            if variant=='missing':s.pop()
            elif variant=='duplicate':m['entries'][1]=copy.deepcopy(m['entries'][0])
            elif variant=='order':m['entries'].reverse()
            elif variant=='hash':s[0]['raincoats']=2
            elif variant=='bool':m['entries'][0]['position']=True
            else:m['entries'][0]['extra']='unexpected'
            with self.subTest(variant=variant),self.assertRaises(b.IntegrityError):b.validate_population(m,s,a)

    def test_summary_overlap_and_leaf_counts(self):
        observations=[dict(has_tradeoff=False,has_unmatched_exit_stratum=False,has_no_eligible_pp=False) for _ in range(80)]
        observations[0].update(has_tradeoff=True,has_unmatched_exit_stratum=True)
        observations[1]['has_no_eligible_pp']=True
        counts={x:dict(b.EXPECTED_COUNTS) for x in ('candidate','reference')}
        result=b.scientific_summary(observations,counts)
        self.assertEqual((result['N'],result['U'],result['N_U_overlap'],result['observations_without_pp']),(1,1,1,1))
        self.assertEqual(result['status'],'recorded_component_tradeoff_present')
        observations[0]['has_tradeoff']=False
        self.assertEqual(b.scientific_summary(observations,counts)['status'], 'recorded_component_tradeoff_absent_with_unmatched_strata')
        observations[0]['has_unmatched_exit_stratum']=False
        self.assertEqual(b.scientific_summary(observations,counts)['status'],'recorded_component_tradeoff_absent')
        counts['candidate']['total_leaves']-=1
        with self.assertRaises(b.IntegrityError):b.scientific_summary(observations,counts)
        with self.assertRaises(b.IntegrityError):b.scientific_summary(observations[:-1],counts)


class ArchiveAndControlTests(unittest.TestCase):
    def zipped(self,name='plain.json',data=b'{}\n',mode=stat.S_IFREG|0o644):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:
            info=zipfile.ZipInfo(name);info.external_attr=mode<<16
            z.writestr(info,data)
        stream.seek(0)
        return zipfile.ZipFile(stream,'r')

    def test_bounded_read_and_crc_hash(self):
        with self.zipped() as z:
            pin=(3,hashlib.sha256(b'{}\n').hexdigest())
            self.assertEqual(b.read_member(z,'plain.json',pin),b'{}\n')
            with self.assertRaises(b.IntegrityError):b.read_member(z,'missing',pin)
            with self.assertRaises(b.IntegrityError):b.read_member(z,'plain.json',(2,pin[1]))
            with self.assertRaises(b.IntegrityError):b.read_member(z,'plain.json',(3,'0'*64))

    def test_zip_path_type_and_expansion(self):
        with patch.object(b,'ARCHIVE_TOTAL',3),patch.object(b,'ARCHIVE_MAX',3):
            with self.zipped() as z:self.assertEqual(b.validate_archive_directory(z),{'plain.json'})
            for name in ('../escape','/absolute','a/../b','a\\b','a//b','./plain'):
                with self.zipped(name) as z,self.assertRaises(b.IntegrityError):b.validate_archive_directory(z)
            with self.zipped(mode=stat.S_IFLNK|0o777) as z,self.assertRaises(b.IntegrityError):b.validate_archive_directory(z)
            with self.zipped(data=b'long') as z,self.assertRaises(b.IntegrityError):b.validate_archive_directory(z)
            with self.zipped(data=b'hi') as z,self.assertRaises(b.IntegrityError):b.validate_archive_directory(z)
            with self.zipped() as z:
                z.infolist()[0].flag_bits |= 1
                with self.assertRaises(b.IntegrityError):b.validate_archive_directory(z)
            with self.zipped() as z:
                z.filelist.append(z.filelist[0])
                with self.assertRaises(b.IntegrityError):b.validate_archive_directory(z)

    def test_production_limit_exact_and_before_real_input(self):
        calls=[]
        with patch.object(b.sys,'platform','linux'),patch.object(b.resource,'setrlimit',side_effect=lambda *a:calls.append(a)), \
             patch.object(b.resource,'getrlimit',return_value=(2147483648,2147483648)):
            self.assertEqual(b.enforce_address_space(),(2147483648,2147483648))
        self.assertEqual(calls,[(b.resource.RLIMIT_AS,(2147483648,2147483648))])
        with patch.object(b.resource,'setrlimit'),patch.object(b.resource,'getrlimit',return_value=(1,1)),self.assertRaises(b.ExecutionBlocked):
            b.enforce_address_space()

    def test_unavailable_inputs_block_before_reads(self):
        with tempfile.TemporaryDirectory(prefix='worker34-b-synthetic-') as td:
            path=Path(td)
            with patch.object(b,'read_pinned_file') as read,self.assertRaises(b.ExecutionBlocked):
                b.analyze(path/'absent.zip',path,path,path)
            read.assert_not_called()


    def test_entire_synthetic_80_160_pipeline_and_wire_closure(self):
        # Runtime pins are patched ONLY in this in-process unit test. There is no
        # production CLI override. The fixture uses 160 hand-authored leaves per
        # source, not the Worker33 corpus, and no engine or game reconstruction.
        with tempfile.TemporaryDirectory(prefix='worker34-b-synthetic-full-') as td:
            root=Path(td);frozen=root/'frozen';accepted=root/'accepted';out=root/'out'
            frozen.mkdir();accepted.mkdir();out.mkdir()
            manifest,snapshots,audits=population_fixture()
            members={};baselines=[]
            for e,a in zip(manifest['entries'],audits):
                for source_pass in (1,2):
                    payload,s,_,base=payload_fixture(e['position'],source_pass)
                    payload['envelope']['seed']=e['seed'];payload['envelope']['ordinal']=e['ordinal']
                    members[f"call-{payload['envelope']['call']:03d}.json"]=b.canonical(payload)
                baselines.append(dict(base,legal_move_count=2,score=10000,tier=a['primary_tier']))
            order=[dict(position=e['position'],seed=e['seed'],ordinal=e['ordinal'],pass_number=source_pass)
                   for source_pass in (1,2) for e in manifest['entries']]
            members['call-order.json']=b.canonical(order)
            members['baseline-gates.json']=b.canonical(baselines)
            members['result.json']=b.canonical(dict(completed_calls=160,scope='synthetic only',
                                                   status=b.ORIGINAL_STATUS,strict_departures=[]))
            inv=dict(files={name:dict(size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
                            for name,raw in members.items()},finalized='synthetic')
            members['inventory.json']=b.canonical(inv)
            artifact=root/'artifact.zip'
            with zipfile.ZipFile(artifact,'w',compression=zipfile.ZIP_DEFLATED) as z:
                for name,raw in members.items():z.writestr(name,raw)
            archive_hash=hashlib.sha256(artifact.read_bytes()).hexdigest()
            review=dict(head=b.HEAD,tree=b.TREE,schema='worker33-exact-head-source-review-v1',
                        status='approved',claims={'synthetic':True})
            review_raw=b.canonical(review)
            execution=dict(head=b.HEAD,tree=b.TREE,run_id=b.RUN,artifact_id=b.ARTIFACT,zip_sha256=archive_hash,
                           schema='worker33-offline-execution-pins-v1',run_attempt=1,
                           source_review_sha256=hashlib.sha256(review_raw).hexdigest())
            verification=dict(head=b.HEAD,tree=b.TREE,run_id=b.RUN,artifact_id=b.ARTIFACT,zip_sha256=archive_hash,
                              status='accepted',classification=b.ORIGINAL_STATUS,completed_calls=160,
                              exact_scientific_matches=80,strict_departures=[],fresh_seeds=0,new_games=0)
            blobs={'worker33-preparation/selection-manifest.json':b.canonical(manifest),
                   'worker33-preparation/selected-corpus.jsonl':b''.join(map(b.canonical,snapshots)),
                   'worker33-preparation/audit-reference.jsonl':b''.join(map(b.canonical,audits)),
                   'worker33-evidence/independent-verification.json':b.canonical(verification),
                   'worker33-evidence/execution-pins.json':b.canonical(execution),
                   'worker33-evidence/source-review.json':review_raw}
            for name,raw in blobs.items():
                dest=(frozen if name.startswith('worker33-preparation/') else accepted)/name.split('/')[-1]
                dest.write_bytes(raw)
            blobs['worker33-evidence/actions-artifact.zip']=artifact.read_bytes()
            pins={name:(len(raw),hashlib.sha256(raw).hexdigest()) for name,raw in blobs.items()}
            member_pins={name:(len(members[name]),hashlib.sha256(members[name]).hexdigest()) for name in b.MEMBER_PINS}
            counts=dict(total_leaves=160,horizon_leaves=160,carry_leaves=0,visible_victory_leaves=0,closed_tunnel_loss_leaves=0)
            with patch.object(b,'INPUT_PINS',pins),patch.object(b,'MEMBER_PINS',member_pins), \
                 patch.object(b,'ARCHIVE_TOTAL',sum(map(len,members.values()))), \
                 patch.object(b,'ARCHIVE_MAX',max(map(len,members.values()))),patch.object(b,'EXPECTED_COUNTS',counts):
                b.analyze(artifact,frozen,accepted,out)
            self.assertEqual(sorted(p.name for p in out.iterdir()),['leaves.jsonl','observations.jsonl','summary.json'])
            leaves=b.json_lines((out/'leaves.jsonl').read_bytes(),'output')
            observations=b.json_lines((out/'observations.jsonl').read_bytes(),'output')
            summary=b.decode((out/'summary.json').read_bytes(),'summary')
            self.assertEqual((len(leaves),len(observations)),(320,80))
            self.assertEqual((summary['N'],summary['U'],summary['N_U_overlap']),(0,0,0))
            self.assertEqual([(r['position'],r['source_pass'],r['root_index']) for r in leaves[:4]],
                             [(1,1,0),(1,1,1),(1,2,0),(1,2,1)])
            for filename in ('leaves.jsonl','observations.jsonl'):
                raw=(out/filename).read_bytes()
                self.assertEqual(raw,b''.join(b.canonical(b.decode(line,'line')) for line in raw.splitlines()))
            self.assertEqual((out/'summary.json').read_bytes(),b.canonical(summary))

    def test_cli_blocked_receipt_is_durable_and_previous_directory_untouched(self):
        with tempfile.TemporaryDirectory(prefix='worker34-b-synthetic-cli-') as td:
            root=Path(td);out=root/'output'
            args=['--artifact',str(root/'absent.zip'),'--frozen',str(root),
                  '--accepted-evidence',str(root),'--output-dir',str(out)]
            with patch.object(b,'enforce_address_space',return_value=(2147483648,2147483648)):
                code=b.main(args)
                self.assertEqual(code,3)
                receipt_raw=(out/'parser-receipt.json').read_bytes()
                receipt=b.decode(receipt_raw,'receipt')
                self.assertEqual(receipt['status'],'execution_blocked')
                self.assertFalse(receipt['completed']);self.assertFalse(receipt['established_integrity_failure'])
                self.assertFalse((out/'parser-receipt.json.incomplete').exists())
                self.assertEqual(receipt['source_sha256'],hashlib.sha256(MODULE.read_bytes()).hexdigest())
                with patch.object(b.sys,'stderr',io.StringIO()):self.assertEqual(b.main(args),3)
                self.assertEqual((out/'parser-receipt.json').read_bytes(),receipt_raw)


if __name__=='__main__':
    unittest.main()
