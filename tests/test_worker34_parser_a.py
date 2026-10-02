"""Invented JSON-only fixtures; never load original observations or game modules."""
import copy
import errno
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

SPEC = importlib.util.spec_from_file_location('worker34_parser_a', Path(__file__).resolve().parents[1] / 'scripts/worker34_parser_a.py')
a = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(a)


def action(kind='place', index=0, origin=None, turns=0):
    return dict(action=kind, hand_index=index, origin=([0, 0] if origin is None and kind == 'place' else origin), quarter_turns=turns)


def card(name, material=None, exit=False):
    return dict(card_id=name, cells=[], is_exit=exit, material=material)


def snapshot(hand=None, r=0, p=0, x=False):
    return dict(board=dict(cells=[], placements=[]), hand=hand if hand is not None else [card('a'), card('b', 'raincoat'), card('c'), card('d', 'rope'), card('e'), card('f')],
                raincoats=r, ropes=p, exit_placed=x, exit_seen=x, turns=0, set_aside_unplayable=0,
                collected_equipment=[], setup=dict(hand_size=6, player_count=1, start_side='easy-5-exit', starting_player=0), player_index=0)


def leaf(sequence, h, reason='horizon', key=None):
    return dict(sequence=sequence, key=[1, 0, h] if key is None else key,
                reason=reason, transition_sha256='a' * 64)


def identity(position=1, seed=1000000, ordinal=1, source_pass=1):
    return dict(position=position, seed=seed, ordinal=ordinal, source_pass=source_pass,
                source_implementation='candidate' if source_pass == 1 else 'reference', call_number=position + 80 * (source_pass - 1))


def row(s, sequence, h, root=0, leaf_index=0, ident=None, reason='horizon'):
    return a.normalize_leaf(s, leaf(sequence, h, reason), ident or identity(), root, leaf_index)


def envelope(entry, source_pass, physical):
    return {'pass': source_pass, 'call': entry['position'] + 80 * (source_pass - 1),
            'implementation': 'candidate' if source_pass == 1 else 'reference',
            'seed': entry['seed'], 'ordinal': entry['ordinal'], 'run_id': '36961069413', 'run_attempt': '1',
            'started': '2026-01-01T00:00:00+00:00', 'finished': '2026-01-01T00:00:01+00:00',
            'wall_seconds': 1.0, 'cpu_seconds': 0.5, 'peak_rss_kib': 1000, 'physical_legal_moves': physical}


def synthetic_call(s, entry, source_pass=1, carry=False):
    definitions = [([action('place', 0), action('place', 0)], 20100, 'horizon'),
                   ([action('collect', 1), action('place', 0)], 30090, 'horizon')]
    if carry:
        definitions.append(([action('place', 5, [-5, -2], 3)], 29900, 'omitted_draw_dead_end'))
    roots = []
    for seq, h, reason in definitions:
        leaves = [leaf(seq, h, reason)]
        seconds = seq[1:]
        roots.append(dict(root=seq[0], first_transition_sha256='b' * 64, second_moves=seconds,
                          second_moves_sha256=a.sha(seconds), leaves=leaves, leaves_sha256=a.sha(leaves),
                          maximum=[1, 0, h], witness=seq))
    root_moves = [r['root'] for r in roots]
    nchildren = sum(len(r['second_moves']) for r in roots)
    counts = dict(roots=len(roots), children=nchildren, previews=len(roots) + nchildren,
                  expanded_nodes=1 + len(roots), enumerations=1 + len(roots), leaves=len(roots))
    best = max(r['maximum'] for r in roots)
    tier = [r['root'] for r in roots if r['maximum'] == best]
    science = dict(schema='worker32-scientific-v1', input_before=a.sha(s), input_after=a.sha(s),
                   root_moves_sha256=a.sha(root_moves), roots=roots, maximal_roots=tier,
                   chosen=tier[0], best=best, rng_before='c' * 64, rng_after='d' * 64, counts=counts)
    physical = counts['enumerations'] + (counts['previews'] if source_pass == 2 else 0)
    baseline = dict(collect_count=1, legal_move_count=len(roots), place_count=len(roots) - 1,
                    root_moves_sha256=a.sha(root_moves), score=10000, tier=[action('collect', 1)])
    return dict(envelope=envelope(entry, source_pass, physical), scientific=science), baseline


def fixture(directory):
    """Complete invented 80/160 input set; temporary pins never affect production."""
    frozen, accepted, output = (directory / n for n in ('frozen', 'accepted', 'output'))
    for path in (frozen, accepted, output):
        path.mkdir()
    seeds = [1000000 + i for i in range(70)] + [1000089]
    seeds[61], seeds[70] = seeds[70], seeds[61]
    seeds += seeds[:9]
    entries, observations, audits, baselines, order = [], [], [], [], []
    members = {}
    for index, seed in enumerate(seeds, 1):
        ordinal = 15 if index == 62 else 1
        s = snapshot(r=1, p=1)
        carry = index == 62
        e = dict(B=3 if carry else 2, C=1, action_type_class='mixed', collect_count_metadata=1,
                 group='hash64' if index <= 64 else 'stress16', ordinal=ordinal, place_count_metadata=2 if carry else 1,
                 position=index, public_observation_sha256=a.sha(s), seed=seed,
                 selection_key_input='invented', selection_key_sha256='a' * 64, snapshot_file='invented.json',
                 snapshot_sha256=a.sha(s), snapshot_size_bytes=len(a.encode(s)), source_trace_member='unused.jsonl',
                 source_trace_sha256='b' * 64, stress_cost_proxy=1)
        # Repeated seeds need distinct observation identities.
        if index > 71:
            e['ordinal'] = 2
        entries.append(e)
        observations.append(s)
        candidate, baseline = synthetic_call(s, e, 1, carry)
        reference, _ = synthetic_call(s, e, 2, carry)
        members[f'call-{index:03}.json'] = a.encode(candidate)
        members[f'call-{index + 80:03}.json'] = a.encode(reference)
        baselines.append(baseline)
        audits.append(dict(legal_move_count=e['B'], ordinal=e['ordinal'], position=index,
                           primary_score=10000, primary_tier=baseline['tier'], primary_tier_sha256=a.sha(baseline['tier']),
                           public_observation_sha256=a.sha(s), seed=seed))
    for source_pass in (1, 2):
        order.extend(dict(pass_number=source_pass, position=e['position'], seed=e['seed'], ordinal=e['ordinal']) for e in entries)
    manifest = {key: {} for key in 'audit_reference_contract candidate_core_constraint canonical_source_accepted_main execution_prerequisite files observation_contract previous_worker32_exclusion selection selector_script selector_script_sha256 source status'.split()}
    manifest.update(entries=entries, new_seeds_or_games_allocated=0, no_policy_search_or_game_execution=True,
                    schema='worker33-mixed-public-state-selection-preparation-v1')
    members['baseline-gates.json'] = a.encode(baselines)
    members['call-order.json'] = a.encode(order)
    members['result.json'] = a.encode(dict(completed_calls=160, scope='invented fixture', status=a.OLD_STATUS, strict_departures=[]))
    for index in range(9):
        members[f'inert-{index}.txt'] = b'invented evidence\n'
    inventory = dict(files={name: dict(size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()) for name, raw in members.items()}, finalized='invented')
    members['inventory.json'] = a.encode(inventory)
    artifact = directory / 'artifact.zip'
    with zipfile.ZipFile(artifact, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in members.items():
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw)
    input_raw = {
        'worker33-evidence/actions-artifact.zip': artifact.read_bytes(),
        'worker33-preparation/selection-manifest.json': a.encode(manifest),
        'worker33-preparation/selected-corpus.jsonl': b''.join(a.encode(s) for s in observations),
        'worker33-preparation/audit-reference.jsonl': b''.join(a.encode(ref) for ref in audits),
    }
    zip_hash = hashlib.sha256(input_raw['worker33-evidence/actions-artifact.zip']).hexdigest()
    review = dict(schema='worker33-exact-head-source-review-v1', status='approved', head=a.EXECUTION_HEAD,
                  tree=a.EXECUTION_TREE, claims=dict(invented=True))
    input_raw['worker33-evidence/source-review.json'] = a.encode(review)
    pins = dict(schema='worker33-offline-execution-pins-v1', head=a.EXECUTION_HEAD, tree=a.EXECUTION_TREE,
                run_id=36961069413, run_attempt=1, artifact_id=11208266885, job_id=110694654983,
                zip_size_bytes=artifact.stat().st_size, zip_sha256=zip_hash,
                source_review_sha256=hashlib.sha256(a.encode(review)).hexdigest())
    input_raw['worker33-evidence/execution-pins.json'] = a.encode(pins)
    verification = dict(head=a.EXECUTION_HEAD, tree=a.EXECUTION_TREE, status='accepted', classification=a.OLD_STATUS,
                        completed_calls=160, exact_scientific_matches=80, fresh_seeds=0, new_games=0, run_id=36961069413,
                        artifact_id=11208266885, job_id=110694654983, strict_departures=[], zip_sha256=zip_hash)
    input_raw['worker33-evidence/independent-verification.json'] = a.encode(verification)
    for relative, raw in input_raw.items():
        if relative.endswith('actions-artifact.zip'):
            continue
        target = frozen if relative.startswith('worker33-preparation/') else accepted
        (target / relative.rsplit('/', 1)[-1]).write_bytes(raw)
    patches = dict(PINS={name: (len(raw), hashlib.sha256(raw).hexdigest()) for name, raw in input_raw.items()},
                   MEMBER_PINS={name: (len(members[name]), hashlib.sha256(members[name]).hexdigest()) for name in a.MEMBER_PINS},
                   ZIP_TOTAL=sum(map(len, members.values())), ZIP_LARGEST=max(map(len, members.values())),
                   EXPECTED_COUNTS=dict(total_leaves=161, horizon_leaves=160, carry_leaves=1, visible_victory_leaves=0, closed_tunnel_loss_leaves=0))
    return artifact, frozen, accepted, output, patches


class StrictWireTests(unittest.TestCase):
    def test_duplicate_keys_at_any_depth(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":{"b":1,"b":2}}'):
            with self.assertRaises(a.IntegrityError):
                a.strict_json(raw)

    def test_nonfinite_and_encoding(self):
        for raw in (b'NaN', b'Infinity', b'-Infinity', b'1e9999', b'\xef\xbb\xbf{}', b'"\xff"', b'{'):
            with self.subTest(raw=raw), self.assertRaises(a.IntegrityError):
                a.strict_json(raw)

    def test_jsonl_blank_and_trailing_newline(self):
        for raw in (b'{}', b'{}\n\n', b'{}\n \n'):
            with self.assertRaises(a.IntegrityError):
                a.jsonl(raw)

    def test_exact_wire_encoding(self):
        self.assertEqual(a.encode({'z': None, 'a': {'\u00e9': True}, 'b': [0, -4]}), b'{"a":{"\\u00e9":true},"b":[0,-4],"z":null}\n')

    def test_actions_reject_all_malformed_forms(self):
        bad = [dict(action(), extra=0), {k: v for k, v in action().items() if k != 'origin'},
               action(index=True), action(index=1.0), action(index='1'), action(index=-1),
               action(turns=True), action(turns=4), action(turns=1.5), action(origin=[0]),
               action(origin=[False, 0]), action(origin=(0, 0)), action('collect', origin=[0, 0]),
               action('collect', turns=1), action('refresh'), action(origin=['0', 0])]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(a.IntegrityError):
                a.action_schema(value)

    def test_pins_reject_size_hash_corruption(self):
        pin = (3, hashlib.sha256(b'abc').hexdigest())
        self.assertEqual(a.pinned_bytes(b'abc', pin, 'fixture'), b'abc')
        for raw in (b'abd', b'ab', b'abcd'):
            with self.assertRaises(a.IntegrityError):
                a.pinned_bytes(raw, pin, 'fixture')


class MetadataTests(unittest.TestCase):
    def test_shifted_indices(self):
        s = snapshot([card('a', 'raincoat'), card('b', 'rope'), card('c')])
        result, r, p, x = a.bookkeep(s, [action('collect', 0), action('collect', 0)])
        self.assertEqual([v['original_hand_index'] for v in result], [0, 1])
        self.assertEqual([v['card_id'] for v in result], ['a', 'b'])
        self.assertEqual((r, p, x), (1, 1, False))
        with self.assertRaises(a.IntegrityError):
            a.bookkeep(s, [action(index=2), action(index=2)])

    def test_two_same_material_cards_and_quota_boundary(self):
        s = snapshot([card('a', 'raincoat'), card('b', 'raincoat')], r=1)
        self.assertEqual(a.bookkeep(s, [action('collect'), action('collect')])[1:3], (3, 0))
        s['raincoats'] = 2
        with self.assertRaises(a.IntegrityError):
            a.bookkeep(s, [action('collect'), action('collect')])
        s['raincoats'] = 3
        with self.assertRaises(a.IntegrityError):
            a.bookkeep(s, [action('collect')])
        self.assertEqual(a.bookkeep(s, [action()])[1], 3)

    def test_rope_quota_and_prohibited_collect(self):
        for s in (snapshot([card('a', 'rope')], p=2), snapshot([card('a')]), snapshot([card('a', exit=True)])):
            with self.assertRaises(a.IntegrityError):
                a.bookkeep(s, [action('collect')])

    def test_original_card_validation(self):
        cases = [snapshot([card('a'), card('a')]), snapshot([card('')]),
                 snapshot([card('a', 'rope', True)]), snapshot([card('a', exit=True), card('b', exit=True)]),
                 snapshot([card('a', exit=True)], x=True), snapshot(r=True), snapshot(p=2.0), snapshot(x=0)]
        for s in cases:
            with self.subTest(s=s), self.assertRaises(a.IntegrityError):
                a.snapshot_schema(s)

    def test_exact_boolean_card_and_material(self):
        for field, value in (('is_exit', 1), ('material', False), ('material', 'coat'), ('card_id', 7)):
            s = snapshot()
            s['hand'][0][field] = value
            with self.assertRaises(a.IntegrityError):
                a.snapshot_schema(s)

    def test_exit_readiness_uses_endpoint_in_both_orders(self):
        s = snapshot([card('exit', exit=True), card('rain', 'raincoat')], r=2, p=2)
        for seq in ([action('place'), action('collect')], [action('collect', 1), action('place')]):
            result = row(s, seq, 55123)
            self.assertEqual(result['inventory'], dict(raincoats=3, ropes=2))
            self.assertTrue(result['exit_placed'])
            self.assertEqual((result['equipment_term'], result['exit_term'], result['geometric_score']), (50000, 5000, 123))

    def test_unready_exit_and_initial_exit(self):
        s = snapshot([card('exit', exit=True), card('b')], r=1, p=1)
        result = row(s, [action(), action()], 15111)
        self.assertEqual((result['exit_term'], result['geometric_score']), (-5000, 111))
        s = snapshot([card('a'), card('b')], r=1, p=1, x=True)
        self.assertTrue(row(s, [action(), action()], 15111)['exit_placed'])

    def test_terminal_keys_never_decompose(self):
        s = snapshot()
        for key, reason in (([2, -2, 0], 'visible_victory'), ([0, 0, 123], 'closed_tunnel_loss'), ([2, -1, 0], 'horizon'), ([1, 1, 0], 'horizon'), ([1, 0, True], 'horizon')):
            with self.subTest(key=key, reason=reason), self.assertRaises(a.IntegrityError):
                a.normalize_leaf(s, leaf([action(), action()], 0, reason, key), identity(), 0, 0)

    def test_carry_separation_and_exact_binding(self):
        s = snapshot(r=1, p=1)
        ident = identity(62, 1000089, 15)
        c = row(s, [action('place', 5, [-5, -2], 3)], 29900, ident=ident, reason='omitted_draw_dead_end')
        self.assertEqual((c['role'], c['pattern'], c['geometric_score']), ('excluded_depth_one_carry', 'P', 9900))
        a.classify([c])
        self.assertIsNone(c['pp_classification'])
        self.assertIsNone(c['witness'])
        o = a.observation_row(ident, [c])
        self.assertEqual((o['horizon_leaf_count'], o['carry_leaf_count']), (0, 1))
        self.assertTrue(o['has_no_eligible_pp'])
        self.assertEqual(sum(x['pp_count'] + x['collection_count'] for x in o['strata']), 0)
        for wrong in (identity(), identity(62, 1000089, 14)):
            with self.assertRaises(a.IntegrityError):
                row(s, [action('place', 5, [-5, -2], 3)], 29900, ident=wrong, reason='omitted_draw_dead_end')


class DominanceTests(unittest.TestCase):
    def rows(self, pp_g=100, c_g=100):
        s = snapshot([card('a'), card('r', 'raincoat'), card('p', 'rope')])
        return [row(s, [action(), action()], pp_g, root=0),
                row(s, [action('collect', 1), action()], 10000 + c_g, root=1)]

    def test_exact_g_tie_component_dominates(self):
        rows = self.rows()
        a.classify(rows)
        self.assertEqual(rows[0]['pp_classification'], 'component_dominated')
        self.assertEqual(rows[0]['witness'], dict(root_index=1, leaf_index=0))
        self.assertIsNone(rows[1]['pp_classification'])
        self.assertIsNone(rows[1]['witness'])

    def test_strict_geometric_tradeoff(self):
        rows = self.rows(pp_g=101)
        a.classify(rows)
        self.assertEqual(rows[0]['pp_classification'], 'geometric_tradeoff')
        self.assertEqual(rows[0]['witness'], dict(root_index=1, leaf_index=0))

    def test_unequal_inventory_groups_canonical_first_witness(self):
        s = snapshot([card('a'), card('r', 'raincoat'), card('p', 'rope')])
        rows = [row(s, [action(), action()], 100, root=0),
                row(s, [action('collect', 2), action()], 10099, root=1),
                row(s, [action('collect', 1), action()], 10100, root=2),
                row(s, [action('collect', 1), action()], 10200, root=3)]
        a.classify(rows)
        self.assertEqual(rows[0]['witness'], dict(root_index=2, leaf_index=0))
        self.assertEqual(rows[1]['inventory'], dict(raincoats=0, ropes=1))
        self.assertEqual(rows[2]['inventory'], dict(raincoats=1, ropes=0))

    def test_tradeoff_witness_first_of_best_g(self):
        rows = self.rows(pp_g=500, c_g=100)
        second = copy.deepcopy(rows[1]); second['root_index'] = 2; second['geometric_score'] = 200
        third = copy.deepcopy(second); third['root_index'] = 3
        rows.extend([second, third])
        a.classify(rows)
        self.assertEqual(rows[0]['witness'], dict(root_index=2, leaf_index=0))

    def test_duplicate_vectors_retained_and_counted(self):
        rows = self.rows()
        dup = copy.deepcopy(rows[0]); dup['leaf_index'] = 1
        rows.insert(1, dup)
        a.classify(rows)
        self.assertEqual(rows[0]['pp_classification'], rows[1]['pp_classification'])
        self.assertEqual(rows[0]['witness'], rows[1]['witness'])
        o = a.observation_row(identity(), rows)
        self.assertEqual(o['strata'][0]['vector_multiplicities'][3], dict(pattern='PP', vectors=[[0, 0, 100, 2]]))
        self.assertEqual(o['strata'][0]['class_counts'], dict(component_dominated=2, geometric_tradeoff=0, unmatched_exit_stratum=0))

    def test_unmatched_exit_is_not_tradeoff(self):
        rows = self.rows()
        rows[0]['exit_placed'] = True
        rows[0]['stratum']['exit_placed'] = True
        a.classify(rows)
        self.assertEqual(rows[0]['pp_classification'], 'unmatched_exit_stratum')
        self.assertIsNone(rows[0]['witness'])
        o = a.observation_row(identity(), rows)
        self.assertTrue(o['has_unmatched_exit_stratum'])
        self.assertFalse(o['has_tradeoff'])
        self.assertEqual([s['exit_placed'] for s in o['strata']], [False, True])

    def test_empty_strata_nulls_and_pattern_order(self):
        o = a.observation_row(identity(), [])
        self.assertTrue(o['has_no_eligible_pp'])
        for s in o['strata']:
            self.assertIsNone(s['pp_max_geometric_score'])
            self.assertIsNone(s['collection_max_geometric_score'])
            self.assertEqual([p['pattern'] for p in s['vector_multiplicities']], list(a.PATTERNS))
            self.assertEqual([p['vectors'] for p in s['vector_multiplicities']], [[], [], [], []])


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.s = snapshot(r=1, p=1)
        self.e = dict(position=1, seed=1000000, ordinal=1, B=2, public_observation_sha256=a.sha(self.s),
                      collect_count_metadata=1, place_count_metadata=1)
        self.call, self.baseline = synthetic_call(self.s, self.e)

    def test_synthetic_source_call_and_reference(self):
        left = a.analyze_call(self.call, self.s, self.e, self.baseline, 1)
        right, _ = synthetic_call(self.s, self.e, 2)
        right = a.analyze_call(right, self.s, self.e, self.baseline, 2)
        self.assertEqual(a.observation_row(self.e, left), a.observation_row(self.e, right))
        self.assertEqual(left[0]['geometric_score'], 100)
        self.assertEqual(left[1]['geometric_score'], 90)
        self.assertEqual(left[0]['pp_classification'], 'geometric_tradeoff')

    def test_envelope_identity_and_numeric_types(self):
        for field, value in (('pass', True), ('call', 81), ('seed', '1000000'), ('ordinal', 1.0), ('implementation', 'reference'), ('run_id', 36961069413), ('run_attempt', 1), ('peak_rss_kib', True), ('physical_legal_moves', 4), ('cpu_seconds', float('inf')), ('started', '2026-01-01')):
            bad = copy.deepcopy(self.call); bad['envelope'][field] = value
            with self.subTest(field=field), self.assertRaises(a.IntegrityError):
                a.analyze_call(bad, self.s, self.e, self.baseline, 1)

    def test_science_hash_binding_count_and_reason_rejection(self):
        cases = []
        bad = copy.deepcopy(self.call); bad['scientific']['input_after'] = 'e' * 64; cases.append(bad)
        bad = copy.deepcopy(self.call); bad['scientific']['counts']['roots'] = True; cases.append(bad)
        bad = copy.deepcopy(self.call); bad['scientific']['roots'][0]['second_moves_sha256'] = 'e' * 64; cases.append(bad)
        bad = copy.deepcopy(self.call); bad['scientific']['roots'][0]['leaves'][0]['reason'] = 'invented'; cases.append(bad)
        bad = copy.deepcopy(self.call); bad['scientific']['best'] = [1, 0, 1]; cases.append(bad)
        bad = copy.deepcopy(self.call); bad['scientific']['chosen'] = action(index=4); cases.append(bad)
        for bad in cases:
            with self.assertRaises(a.IntegrityError):
                a.analyze_call(bad, self.s, self.e, self.baseline, 1)

    def test_root_second_sequence_inconsistency_after_valid_hash(self):
        bad = copy.deepcopy(self.call)
        root = bad['scientific']['roots'][0]
        root['leaves'][0]['sequence'] = copy.deepcopy(root['leaves'][0]['sequence'])
        root['leaves'][0]['sequence'][1]['hand_index'] = 2
        root['leaves_sha256'] = a.sha(root['leaves'])
        with self.assertRaisesRegex(a.IntegrityError, 'sequence binding'):
            a.analyze_call(bad, self.s, self.e, self.baseline, 1)

    def test_malformed_leaf_object_establishes_integrity(self):
        bad = copy.deepcopy(self.call)
        root = bad['scientific']['roots'][0]
        root['leaves'] = [False]
        root['leaves_sha256'] = a.sha(root['leaves'])
        with self.assertRaises(a.IntegrityError):
            a.analyze_call(bad, self.s, self.e, self.baseline, 1)

    def test_no_terminal_summary_or_wrong_population(self):
        totals = {name: dict(a.EXPECTED_COUNTS) for name in ('candidate', 'reference')}
        with self.assertRaises(a.IntegrityError):
            a.scientific_summary([], totals)
        observations = [a.observation_row(dict(position=i, seed=1000000, ordinal=i), []) for i in range(1, 81)]
        totals['candidate']['horizon_leaves'] -= 1
        with self.assertRaises(a.IntegrityError):
            a.scientific_summary(observations, totals)

    def test_summary_labels_overlap_and_denominator(self):
        observations = [a.observation_row(dict(position=i, seed=1000000, ordinal=i), []) for i in range(1, 81)]
        totals = {name: dict(a.EXPECTED_COUNTS) for name in ('candidate', 'reference')}
        self.assertEqual(a.scientific_summary(observations, totals)['status'], 'recorded_component_tradeoff_absent')
        observations[0]['has_unmatched_exit_stratum'] = True
        self.assertEqual(a.scientific_summary(observations, totals)['status'], 'recorded_component_tradeoff_absent_with_unmatched_strata')
        observations[0]['has_tradeoff'] = True
        summary = a.scientific_summary(observations, totals)
        self.assertEqual((summary['N'], summary['U'], summary['N_U_overlap'], summary['denominator']), (1, 1, 1, 80))
        self.assertEqual(summary['status'], 'recorded_component_tradeoff_present')


class FullSyntheticTests(unittest.TestCase):
    def test_complete_80_160_fixture_and_all_wire_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact, frozen, accepted, output, patches = fixture(Path(directory))
            progress = dict(verified_inputs=[], verified_zip_members=0, completed_source_calls=0, matched_source_pairs=0)
            with mock.patch.multiple(a, **patches):
                result = a.run_analysis(artifact, frozen, accepted, output, progress)
            self.assertEqual((result['N'], result['U'], result['N_U_overlap']), (80, 0, 0))
            self.assertEqual(result['denominator'], 80)
            self.assertEqual((progress['completed_source_calls'], progress['matched_source_pairs'], progress['verified_zip_members']), (160, 80, 173))
            rows = a.jsonl((output / 'leaves.jsonl.incomplete').read_bytes())
            self.assertEqual(len(rows), 322)
            self.assertEqual([(r['position'], r['source_pass'], r['root_index'], r['leaf_index']) for r in rows], sorted((r['position'], r['source_pass'], r['root_index'], r['leaf_index']) for r in rows))
            self.assertEqual(len(a.jsonl((output / 'observations.jsonl.incomplete').read_bytes())), 80)
            self.assertEqual(len([r for r in rows if r['role'] == 'excluded_depth_one_carry']), 2)
            required = set('schema position seed ordinal source_pass call_number root_index leaf_index depth source_implementation sequence recorded_key reason inventory exit_placed equipment_term exit_term geometric_score pattern role stratum pp_classification witness'.split())
            for r in rows:
                self.assertEqual(set(r), required)
                self.assertEqual(set(r['sequence'][0]), set('action hand_index original_hand_index card_id origin quarter_turns'.split()))
            for name in ('leaves.jsonl', 'observations.jsonl', 'summary.json'):
                raw = (output / (name + '.incomplete')).read_bytes()
                self.assertTrue(raw.endswith(b'\n'))
                self.assertEqual(raw, b''.join(a.encode(v) for v in a.jsonl(raw)))

    def test_population_missing_duplicate_and_boolean(self):
        with tempfile.TemporaryDirectory() as directory:
            _, frozen, _, _, _ = fixture(Path(directory))
            manifest = a.strict_json((frozen / 'selection-manifest.json').read_bytes())
            observations = a.jsonl((frozen / 'selected-corpus.jsonl').read_bytes())
            audits = a.jsonl((frozen / 'audit-reference.jsonl').read_bytes())
            a.validate_population(manifest, observations, audits)
            with self.assertRaises(a.IntegrityError):
                a.validate_population(manifest, observations[:-1], audits)
            bad = copy.deepcopy(manifest); bad['entries'][1]['position'] = True
            with self.assertRaises(a.IntegrityError):
                a.validate_population(bad, observations, audits)
            bad = copy.deepcopy(manifest); bad['entries'][1]['seed'] = bad['entries'][0]['seed']; bad['entries'][1]['ordinal'] = bad['entries'][0]['ordinal']
            with self.assertRaises(a.IntegrityError):
                a.validate_population(bad, observations, audits)

    def test_fixed_inputs_corruption_and_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact, frozen, accepted, output, patches = fixture(Path(directory))
            (frozen / 'selected-corpus.jsonl').write_bytes(b'corrupt\n')
            progress = dict(verified_inputs=[])
            with mock.patch.multiple(a, **patches), self.assertRaises(a.IntegrityError):
                a.run_analysis(artifact, frozen, accepted, output, progress)
            with self.assertRaises(a.ExecutionBlocked):
                a.read_pinned(Path(directory) / 'absent', (1, 'a' * 64))
            self.assertFalse((output / 'summary.json').exists())

    def test_duplicate_zip_and_unsafe_member(self):
        for name in ('../escape', '/absolute', 'a/b', 'a\\b'):
            with tempfile.TemporaryDirectory() as directory:
                artifact, _, _, _, patches = fixture(Path(directory))
                with zipfile.ZipFile(artifact) as z:
                    members = [(i, z.read(i)) for i in z.infolist()]
                with zipfile.ZipFile(artifact, 'w') as z:
                    for index, (info, raw) in enumerate(members):
                        if index == 0:
                            info.filename = name
                        z.writestr(info, raw)
                with mock.patch.multiple(a, **patches), self.assertRaises(a.IntegrityError):
                    a.Archive(artifact)

    def test_duplicate_name_symlink_and_expansion_rejected(self):
        for mutation in ('duplicate', 'symlink', 'size'):
            with tempfile.TemporaryDirectory() as directory:
                artifact, _, _, _, patches = fixture(Path(directory))
                with zipfile.ZipFile(artifact) as z:
                    members = [(i, z.read(i)) for i in z.infolist()]
                with zipfile.ZipFile(artifact, 'w') as z:
                    for index, (info, raw) in enumerate(members):
                        if index == 0 and mutation == 'symlink':
                            info.external_attr = 0o120777 << 16
                        if index == 0 and mutation == 'size':
                            raw += b'x'
                        z.writestr(info, raw)
                    if mutation == 'duplicate':
                        import warnings
                        with warnings.catch_warnings():
                            warnings.simplefilter('ignore', UserWarning)
                            z.writestr(members[0][0], members[0][1])
                with mock.patch.multiple(a, **patches), self.assertRaises(a.IntegrityError):
                    a.Archive(artifact)

    def test_pair_mismatch_preserves_only_incomplete_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact, frozen, accepted, output, patches = fixture(Path(directory))
            original_json = a.Archive.json
            def mismatch(archive, name):
                value = original_json(archive, name)
                if name == 'call-081.json':
                    # A different valid opaque RNG provenance string establishes a
                    # complete-payload mismatch without changing endpoint metadata.
                    value['scientific']['rng_after'] = 'f' * 64
                return value
            progress = dict(verified_inputs=[], verified_zip_members=0, completed_source_calls=0, matched_source_pairs=0)
            with mock.patch.multiple(a, **patches), mock.patch.object(a.Archive, 'json', mismatch), self.assertRaisesRegex(a.IntegrityError, 'entire candidate/reference'):
                a.run_analysis(artifact, frozen, accepted, output, progress)
            self.assertFalse((output / 'summary.json').exists())
            self.assertFalse((output / 'summary.json.incomplete').exists())
            self.assertTrue((output / 'leaves.jsonl.incomplete').exists())

    def test_integrity_failure_receipt_and_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact, frozen, accepted, output, patches = fixture(Path(directory))
            output.rmdir()
            (frozen / 'selected-corpus.jsonl').write_bytes(b'corrupt\n')
            args = ['--artifact', str(artifact), '--frozen', str(frozen), '--accepted-evidence', str(accepted), '--output-dir', str(output)]
            with mock.patch.multiple(a, **patches), mock.patch.object(a, 'enforce_memory_limit', return_value=[2147483648, 2147483648]):
                self.assertEqual(a.main(args), 2)
            raw = (output / 'parser-receipt.json').read_bytes()
            receipt = a.strict_json(raw)
            self.assertEqual(receipt['status'], 'integrity_invalid')
            self.assertTrue(receipt['established_integrity_failure'])
            self.assertFalse(receipt['completed'])
            self.assertTrue(receipt['errors'])
            with mock.patch.object(a, 'run_analysis') as run, mock.patch('sys.stderr'):
                self.assertEqual(a.main(args), 4)
                run.assert_not_called()
            self.assertEqual((output / 'parser-receipt.json').read_bytes(), raw)

    def test_member_missing_and_corrupt_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact, _, _, _, patches = fixture(Path(directory))
            with mock.patch.multiple(a, **patches):
                z = a.Archive(artifact)
                try:
                    z.pins['call-001.json'] = (z.pins['call-001.json'][0], '0' * 64)
                    with self.assertRaises(a.IntegrityError):
                        z.raw('call-001.json')
                    with self.assertRaises(a.IntegrityError):
                        z._raw('absent.json', (0, 'a' * 64))
                finally:
                    z.close()

    def test_receipt_contract_with_mocked_resource_only(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact, frozen, accepted, output, patches = fixture(Path(directory))
            output.rmdir()
            with mock.patch.multiple(a, **patches), mock.patch.object(a, 'enforce_memory_limit', return_value=[2147483648, 2147483648]):
                rc = a.main(['--artifact', str(artifact), '--frozen', str(frozen), '--accepted-evidence', str(accepted), '--output-dir', str(output)])
            self.assertEqual(rc, 0)
            receipt = a.strict_json((output / 'parser-receipt.json').read_bytes())
            required = set('parser_id source_sha256 interpreter_executable interpreter_version pid rlimit_as_soft rlimit_as_hard status completed elapsed_seconds maxrss_kib established_integrity_failure errors'.split())
            self.assertTrue(required <= set(receipt))
            self.assertEqual(receipt['status'], 'complete')
            self.assertTrue(receipt['completed'])
            self.assertFalse(receipt['established_integrity_failure'])
            self.assertEqual(receipt['errors'], [])
            self.assertEqual(receipt['parser_id'], 'a')
            self.assertFalse(list(output.glob('*.incomplete')))
            self.assertEqual(a.file_hash(output / 'leaves.jsonl'), receipt['scientific_files']['leaves.jsonl']['sha256'])


class ResourceTests(unittest.TestCase):
    def test_production_limit_exact_and_verified_before_inputs(self):
        with mock.patch.object(a.resource, 'setrlimit') as setter, mock.patch.object(a.resource, 'getrlimit', return_value=(2147483648, 2147483648)):
            self.assertEqual(a.enforce_memory_limit(), [2147483648, 2147483648])
            setter.assert_called_once_with(a.resource.RLIMIT_AS, (2147483648, 2147483648))
        with mock.patch.object(a.resource, 'setrlimit'), mock.patch.object(a.resource, 'getrlimit', return_value=(1, 1)), self.assertRaises(a.ExecutionBlocked):
            a.enforce_memory_limit()

    def test_resource_block_precedes_real_input_read(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'new-output'
            args = ['--artifact', 'unread.zip', '--frozen', 'unread', '--accepted-evidence', 'unread', '--output-dir', str(output)]
            with mock.patch.object(a, 'enforce_memory_limit', side_effect=a.ExecutionBlocked('unavailable limit')), mock.patch.object(a, 'run_analysis') as run:
                self.assertEqual(a.main(args), 4)
                run.assert_not_called()
            receipt = a.strict_json((output / 'parser-receipt.json').read_bytes())
            self.assertFalse(receipt['established_integrity_failure'])
            self.assertEqual(receipt['status'], 'execution_blocked')
            self.assertEqual(receipt['progress']['verified_inputs'], [])

    def test_resource_errors_are_not_integrity_evidence(self):
        for exc in (MemoryError(), TimeoutError(), OSError(errno.ENOSPC, 'full'), RuntimeError('unknown implementation defect')):
            self.assertEqual(a.failure_status(exc), 'resource_incomplete')
        self.assertEqual(a.failure_status(a.IntegrityError('completed hash mismatch')), 'integrity_invalid')
        self.assertEqual(a.failure_status(a.ExecutionBlocked('missing prerequisite')), 'execution_blocked')

    def test_no_engine_or_process_imports(self):
        import ast
        tree = ast.parse(Path(a.__file__).read_text())
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.append(node.module or '')
        self.assertFalse(any(name.startswith(('bandido', 'subprocess', 'multiprocessing', 'random')) for name in names))


if __name__ == '__main__':
    unittest.main()
