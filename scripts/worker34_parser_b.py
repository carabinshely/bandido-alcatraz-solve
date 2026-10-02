#!/usr/bin/env python3
"""Independent Worker34 parser B: recorded metadata only, never game execution.

This source implements the frozen recorded-endpoint-decomposition protocol.
Production input pins and population sizes are constants, not CLI options.
The caller must supply the separately frozen, whole-workload supervisor.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import resource
import stat
import sys
import time
import zipfile

PROTOCOL_SHA256 = 'cad7dc56e16b6f12d34fac7cb5b5aa8c3c5e791cb18536880e9170b162e7258e'
MEMORY_BYTES = 2147483648
OBSERVATIONS = 80
CALLS = 160
SEEDS = 71
HEAD = '99164d0212d50fce37f8a2a9656198ca08ccde32'
TREE = '8351ff128c91c34276382e427dadcf10ba844591'
RUN = 36961069413
ARTIFACT = 11208266885
ARCHIVE_TOTAL = 136061225
ARCHIVE_MAX = 6347785
INPUT_PINS = {
    'worker33-evidence/actions-artifact.zip': (19184749, '18a58ec0505d81eaf4b0cfb4798b7e38b0d9555d22ad77c5d4681b5fce89492a'),
    'worker33-preparation/selection-manifest.json': (73029, '3ad07d6237b3f7f24c60448fc346a013261d05b8e36fd998ffd440faceee9a78'),
    'worker33-preparation/selected-corpus.jsonl': (326455, '2366287bd1e05d6b47ed47344996120f76bc02b297a81b3238099dc329066df5'),
    'worker33-preparation/audit-reference.jsonl': (30132, '4ca2c08160b8e641f26d3dfbb2759727c522fe1d0235837cdaab35e3e967502e'),
    'worker33-evidence/independent-verification.json': (1061, 'e6d7f436d4144f120c4a3dceda9262a54c2a565279ae7a7e1bac376a7452ae60'),
    'worker33-evidence/execution-pins.json': (1725, 'fc2a4c57a3eed23f543e73b519905e97e21524eceb9781357ab600ef6cb0cc0d'),
    'worker33-evidence/source-review.json': (901, '4836168704d384d8b8b538dce4740ff8a6f61b4bbbd49475060f85e922e20441'),
}
MEMBER_PINS = {
    'inventory.json': (19740, '5fe0a2d930e893d52b2f18d604be1ffb3434fc57122130d9f65b5ce49c86eeab'),
    'call-order.json': (9480, '2ffb40f33bcd9dc69bbbb17f1c8822f493873b580def7d0e0beb6d1d62160804'),
    'baseline-gates.json': (20596, '2e689201b88cd70234d979c6872da01ebf0d9e6e4cd10795b0d4cec440525007'),
    'result.json': (183, '020dc924024c9bc1380f6442c9dc76ac0ccaecfa8b481261b2d183c6e04c6ed9'),
}
EXPECTED_COUNTS = dict(total_leaves=191920, horizon_leaves=191919, carry_leaves=1,
                       visible_victory_leaves=0, closed_tunnel_loss_leaves=0)
CLASS_NAMES = ('component_dominated', 'geometric_tradeoff', 'unmatched_exit_stratum')
PATTERNS = ('CC', 'CP', 'PC', 'PP')
ORIGINAL_STATUS = 'mixed_action_two_action_diagnostic_mechanism_not_exercised'
ACTION_FIELDS = {'action', 'hand_index', 'origin', 'quarter_turns'}


class IntegrityError(Exception):
    """An established fixed-input or recorded-contract mismatch."""


class ExecutionBlocked(Exception):
    """A prerequisite was unavailable before input admission."""


def demand(condition, explanation):
    if not condition:
        raise IntegrityError(explanation)


def exact_fields(value, names, location):
    demand(type(value) is dict and set(value) == set(names), location + ': object fields')


def integer(value, location, lower=None, upper=None):
    demand(type(value) is int, location + ': exact integer required')
    demand(lower is None or value >= lower, location + ': below range')
    demand(upper is None or value <= upper, location + ': above range')
    return value


def boolean(value, location):
    demand(type(value) is bool, location + ': exact Boolean required')
    return value


def array(value, location):
    demand(type(value) is list, location + ': array required')
    return value


def digest_string(value, location):
    demand(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None,
           location + ': SHA256 required')


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                       allow_nan=False) + '\n').encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        demand(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def _constant(value):
    raise IntegrityError('nonfinite JSON constant: ' + value)


def _float(value):
    number = float(value)
    demand(math.isfinite(number), 'nonfinite JSON number')
    return number


def decode(raw, location):
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                          parse_constant=_constant, parse_float=_float)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise IntegrityError(location + ': invalid JSON: ' + str(exc)) from exc


def json_lines(raw, location):
    demand(raw.endswith(b'\n'), location + ': final LF required')
    rows = raw.splitlines()
    demand(all(rows), location + ': blank JSONL row')
    return [decode(row, location) for row in rows]


def checked_bytes(raw, pin, location):
    demand(len(raw) == pin[0], location + ': byte-size mismatch')
    demand(hashlib.sha256(raw).hexdigest() == pin[1], location + ': SHA256 mismatch')
    return raw


def read_pinned_file(path, pin):
    # Read no more than the declared pin plus one byte, even for corrupt inputs.
    with path.open('rb') as stream:
        raw = stream.read(pin[0] + 1)
    return checked_bytes(raw, pin, str(path))


def hash_file(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def validate_action(action):
    exact_fields(action, ACTION_FIELDS, 'action')
    demand(action['action'] in ('place', 'collect'), 'unsupported action')
    integer(action['hand_index'], 'hand index', 0)
    q = integer(action['quarter_turns'], 'quarter turns', 0, 3)
    if action['action'] == 'collect':
        demand(action['origin'] is None and q == 0, 'COLLECT wire metadata')
    else:
        origin = array(action['origin'], 'PLACE origin')
        demand(len(origin) == 2, 'PLACE origin length')
        for coord in origin:
            integer(coord, 'PLACE coordinate')


def validate_inert_edges(edges):
    """Require the serializer's sorted frozenset wire representation unchanged."""
    array(edges, 'inert tunnel edges')
    for edge in edges:
        demand(type(edge) is str and edge in ('N', 'E', 'S', 'W'), 'inert tunnel direction')
    demand(edges == sorted(set(edges)), 'inert tunnel edges must be sorted and unique')


def validate_card(card):
    exact_fields(card, {'card_id', 'cells', 'material', 'is_exit'}, 'card')
    demand(type(card['card_id']) is str and bool(card['card_id']), 'empty/nonstring card ID')
    demand(card['material'] in (None, 'raincoat', 'rope'), 'unsupported material')
    boolean(card['is_exit'], 'card EXIT')
    demand(not card['is_exit'] or card['material'] is None, 'EXIT material must be null')
    # Cells are retained as inert source JSON; no adjacency or geometric inference.
    for cell in array(card['cells'], 'card cells'):
        exact_fields(cell, {'x', 'y', 'water', 'tunnel_edges'}, 'card cell schema')
        integer(cell['x'], 'inert cell x')
        integer(cell['y'], 'inert cell y')
        boolean(cell['water'], 'inert cell water')
        validate_inert_edges(cell['tunnel_edges'])



def validate_inert_board(board):
    """Check serialized field shapes only; no geometry or history reconstruction."""
    exact_fields(board, {'cells', 'placements'}, 'inert board')
    for cell in array(board['cells'], 'inert board cells'):
        exact_fields(cell, {'x', 'y', 'water', 'tunnel_edges'}, 'inert board cell')
        integer(cell['x'], 'inert board cell x')
        integer(cell['y'], 'inert board cell y')
        boolean(cell['water'], 'inert board cell water')
        validate_inert_edges(cell['tunnel_edges'])
    for placement in array(board['placements'], 'inert placement history'):
        exact_fields(placement, {'card_id', 'origin', 'quarter_turns', 'placement_index',
                                'kind', 'cells', 'overlaps', 'covered_placement_index'},
                     'inert placement')
        demand(type(placement['card_id']) is str and bool(placement['card_id']),
               'inert placement card ID')
        demand(type(placement['kind']) is str and placement['kind'] in ('start', 'ordinary', 'exit'),
               'inert placement kind')
        integer(placement['quarter_turns'], 'inert placement quarter turns', 0, 3)
        integer(placement['placement_index'], 'inert placement index', 0)
        if placement['covered_placement_index'] is not None:
            integer(placement['covered_placement_index'], 'inert covered placement index', 0)
        coordinates = [('origin', placement['origin'])]
        for field in ('cells', 'overlaps'):
            coordinates.extend((field, coordinate) for coordinate in array(placement[field], 'inert placement ' + field))
        for field, coordinate in coordinates:
            array(coordinate, 'inert placement ' + field + ' coordinate')
            demand(len(coordinate) == 2, 'inert placement coordinate length')
            for value in coordinate:
                integer(value, 'inert placement coordinate')


def validate_snapshot(snapshot):
    exact_fields(snapshot, {'board', 'collected_equipment', 'exit_placed', 'exit_seen', 'hand',
                           'player_index', 'raincoats', 'ropes', 'set_aside_unplayable',
                           'setup', 'turns'}, 'public snapshot')
    integer(snapshot['raincoats'], 'initial raincoats', 0, 3)
    integer(snapshot['ropes'], 'initial ropes', 0, 2)
    boolean(snapshot['exit_placed'], 'initial EXIT')
    boolean(snapshot['exit_seen'], 'EXIT seen')
    for name in ('turns', 'set_aside_unplayable'):
        integer(snapshot[name], name, 0)
    integer(snapshot['player_index'], 'player index', 0, 0)
    exact_fields(snapshot['setup'], {'hand_size', 'player_count', 'start_side', 'starting_player'},
                 'setup')
    for key, wanted in (('hand_size', 6), ('player_count', 1), ('starting_player', 0)):
        demand(integer(snapshot['setup'][key], key) == wanted, 'frozen setup mismatch')
    demand(snapshot['setup']['start_side'] == 'easy-5-exit', 'frozen start side mismatch')
    validate_inert_board(snapshot['board'])
    for item in array(snapshot['collected_equipment'], 'collected history'):
        exact_fields(item, {'card', 'turn', 'player_index'}, 'collected history item')
        validate_card(item['card'])
        integer(item['turn'], 'collection turn', 1)
        integer(item['player_index'], 'collection player', 0, 0)
    hand = array(snapshot['hand'], 'original hand')
    demand(0 <= len(hand) <= 6, 'original hand length')
    ids = set()
    exits = 0
    for card in hand:
        validate_card(card)
        demand(card['card_id'] not in ids, 'duplicate original hand card ID')
        ids.add(card['card_id'])
        exits += card['is_exit']
    demand(exits <= 1, 'multiple EXIT cards')
    demand(not (exits and snapshot['exit_placed']), 'EXIT in hand after EXIT placed')


def resolve_sequence(snapshot, sequence):
    """Delete recorded indices in an original-ID list; never apply a game action."""
    validate_snapshot(snapshot)
    array(sequence, 'sequence')
    demand(len(sequence) in (1, 2), 'unsupported sequence depth')
    remaining = list(range(len(snapshot['hand'])))
    rain, rope, exit_flag = snapshot['raincoats'], snapshot['ropes'], snapshot['exit_placed']
    normalized = []
    used = set()
    for action in sequence:
        validate_action(action)
        index = action['hand_index']
        demand(index < len(remaining), 'retained-hand index out of range')
        original = remaining.pop(index)
        card = snapshot['hand'][original]
        demand(card['card_id'] not in used, 'repeated physical card')
        used.add(card['card_id'])
        if action['action'] == 'collect':
            if card['material'] == 'raincoat':
                demand(rain < 3, 'raincoat quota exceeded')
                rain += 1
            elif card['material'] == 'rope':
                demand(rope < 2, 'rope quota exceeded')
                rope += 1
            else:
                raise IntegrityError('COLLECT requires material card')
        elif card['is_exit']:
            demand(not exit_flag, 'EXIT already placed')
            exit_flag = True
        normalized.append(dict(action, original_hand_index=original, card_id=card['card_id']))
    return normalized, rain, rope, exit_flag


def recorded_key(key):
    demand(type(key) is list and len(key) == 3, 'ranking key shape')
    for value in key:
        integer(value, 'ranking key coordinate')
    return key


def leaf_row(snapshot, leaf, entry, source_pass, root_index, leaf_index):
    exact_fields(leaf, {'sequence', 'key', 'reason', 'transition_sha256'}, 'leaf')
    key = recorded_key(leaf['key'])
    sequence = array(leaf['sequence'], 'leaf sequence')
    demand(len(sequence) in (1, 2), 'leaf depth')
    reason = leaf['reason']
    demand(reason in ('horizon', 'omitted_draw_dead_end', 'visible_victory', 'closed_tunnel_loss'),
           'unsupported reason')
    # The terminal placeholder is rejected before it can enter subtraction.
    demand(reason not in ('visible_victory', 'closed_tunnel_loss') and key[:2] == [1, 0],
           'fixed contract excludes terminal leaf or incompatible key')
    digest_string(leaf['transition_sha256'], 'transition provenance')
    if reason == 'horizon':
        demand(len(sequence) == 2, 'horizon must have depth two')
    else:
        demand(len(sequence) == 1, 'carry must have depth one')
        demand((entry['position'], entry['seed'], entry['ordinal']) == (62, 1000089, 15),
               'carry observation mismatch')
        demand(sequence == [dict(action='place', hand_index=5, origin=[-5, -2], quarter_turns=3)]
               and key == [1, 0, 29900], 'carry metadata mismatch')
    normalized, rain, rope, exit_flag = resolve_sequence(snapshot, sequence)
    pattern = ''.join('C' if a['action'] == 'collect' else 'P' for a in normalized)
    role = ('excluded_depth_one_carry' if len(sequence) == 1 else
            'primary_pp' if pattern == 'PP' else 'collection_comparator')
    equipment = 10000 * (rain + rope)
    exit_term = (5000 if (rain, rope) == (3, 2) else -5000) if exit_flag else 0
    return dict(schema='worker33-endpoint-leaf-v1', position=entry['position'], seed=entry['seed'],
                ordinal=entry['ordinal'], source_pass=source_pass,
                call_number=entry['position'] + (source_pass - 1) * OBSERVATIONS,
                source_implementation='candidate' if source_pass == 1 else 'reference',
                root_index=root_index, leaf_index=leaf_index, depth=len(sequence),
                sequence=normalized, recorded_key=key, reason=reason,
                inventory=dict(raincoats=rain, ropes=rope), exit_placed=exit_flag,
                equipment_term=equipment, exit_term=exit_term,
                geometric_score=key[2] - equipment - exit_term, pattern=pattern, role=role,
                stratum=dict(depth=len(sequence), exit_placed=exit_flag, key_class=key[0], reason=reason),
                pp_classification=None, witness=None)


def classify(rows, snapshot, entry):
    """Group integer inventory vectors; prefix maxima locate canonical witnesses."""
    strata = []
    for exit_flag in (False, True):
        population = [r for r in rows if r['depth'] == 2 and r['exit_placed'] is exit_flag]
        pp = [r for r in population if r['pattern'] == 'PP']
        comparators = [r for r in population if r['pattern'] != 'PP']
        base = (snapshot['raincoats'], snapshot['ropes'])
        groups = defaultdict(list)
        vectors = {p: Counter() for p in PATTERNS}
        for row in population:
            vector = (row['inventory']['raincoats'], row['inventory']['ropes'], row['geometric_score'])
            vectors[row['pattern']][vector] += 1
            if row['pattern'] == 'PP':
                demand(vector[:2] == base, 'PP changed acquired equipment')
            else:
                demand(vector[0] >= base[0] and vector[1] >= base[1] and vector[:2] != base,
                       'collection comparator inventory is not strictly larger')
                groups[vector[:2]].append(row)
        search = []
        for inventory, records in groups.items():
            prefix = []
            for record in records:
                score = record['geometric_score']
                prefix.append(score if not prefix else max(prefix[-1], score))
            search.append((inventory, records, prefix))
        best = max((r['geometric_score'] for r in comparators), default=None)
        best_record = next((r for r in comparators if r['geometric_score'] == best), None)
        class_counts = dict.fromkeys(CLASS_NAMES, 0)
        for row in pp:
            if not comparators:
                label, witness = 'unmatched_exit_stratum', None
            else:
                candidates = []
                for inventory, records, prefix in search:
                    # Explicit componentwise rule, including strictness and unequal vectors.
                    target = (row['inventory']['raincoats'], row['inventory']['ropes'])
                    if inventory[0] < target[0] or inventory[1] < target[1]:
                        continue
                    threshold = row['geometric_score'] + (inventory == target)
                    at = bisect_left(prefix, threshold)
                    if at < len(records):
                        candidates.append(records[at])
                if candidates:
                    label = 'component_dominated'
                    witness = min(candidates, key=lambda r: (r['root_index'], r['leaf_index']))
                else:
                    demand(row['geometric_score'] > best, 'dominance/tradeoff equivalence failed')
                    label, witness = 'geometric_tradeoff', best_record
            row['pp_classification'] = label
            row['witness'] = None if witness is None else {
                'root_index': witness['root_index'], 'leaf_index': witness['leaf_index']}
            class_counts[label] += 1
        strata.append(dict(exit_placed=exit_flag, pp_count=len(pp), collection_count=len(comparators),
                           pp_max_geometric_score=max((r['geometric_score'] for r in pp), default=None),
                           collection_max_geometric_score=best, class_counts=class_counts,
                           vector_multiplicities=[dict(pattern=p, vectors=[list(v) + [n] for v, n in
                                                  sorted(vectors[p].items())]) for p in PATTERNS]))
    return dict(schema='worker33-endpoint-observation-v1', position=entry['position'], seed=entry['seed'],
                ordinal=entry['ordinal'], horizon_leaf_count=sum(r['depth'] == 2 for r in rows),
                carry_leaf_count=sum(r['depth'] == 1 for r in rows),
                has_tradeoff=any(s['class_counts']['geometric_tradeoff'] > 0 for s in strata),
                has_unmatched_exit_stratum=any(s['class_counts']['unmatched_exit_stratum'] > 0 for s in strata),
                has_no_eligible_pp=not any(s['pp_count'] for s in strata), strata=strata)


def validate_envelope(envelope, entry, source_pass):
    exact_fields(envelope, {'call', 'cpu_seconds', 'finished', 'implementation', 'ordinal', 'pass',
                           'peak_rss_kib', 'physical_legal_moves', 'run_attempt', 'run_id', 'seed',
                           'started', 'wall_seconds'}, 'call envelope')
    expected = {'call': entry['position'] + (source_pass - 1) * OBSERVATIONS,
                'pass': source_pass, 'seed': entry['seed'], 'ordinal': entry['ordinal']}
    for name, wanted in expected.items():
        demand(integer(envelope[name], 'envelope ' + name) == wanted, 'envelope identity mismatch: ' + name)
    demand(envelope['implementation'] == ('candidate' if source_pass == 1 else 'reference'),
           'unexpected implementation label')
    demand(envelope['run_id'] == str(RUN) and envelope['run_attempt'] == '1', 'original run binding')
    for name in ('cpu_seconds', 'wall_seconds'):
        value = envelope[name]
        demand(type(value) in (int, float) and math.isfinite(value) and value >= 0,
               'invalid recorded cost')
    integer(envelope['peak_rss_kib'], 'recorded RSS', 0)
    integer(envelope['physical_legal_moves'], 'recorded enumeration count', 1)
    stamps = []
    for name in ('started', 'finished'):
        demand(type(envelope[name]) is str, 'timestamp must be string')
        try:
            value = datetime.fromisoformat(envelope[name])
        except ValueError as exc:
            raise IntegrityError('invalid timestamp') from exc
        demand(value.utcoffset() == timedelta(0), 'timestamp must be UTC')
        stamps.append(value)
    demand(stamps[0] <= stamps[1], 'reversed timestamps')


def parse_call(payload, snapshot, entry, baseline, source_pass):
    exact_fields(payload, {'envelope', 'scientific'}, 'call payload')
    validate_envelope(payload['envelope'], entry, source_pass)
    science = payload['scientific']
    exact_fields(science, {'best', 'chosen', 'counts', 'input_after', 'input_before', 'maximal_roots',
                          'rng_after', 'rng_before', 'root_moves_sha256', 'roots', 'schema'}, 'scientific payload')
    demand(science['schema'] == 'worker32-scientific-v1', 'scientific schema ID')
    demand(science['input_before'] == science['input_after'] == entry['public_observation_sha256'] == digest(snapshot),
           'public input binding')
    for name in ('rng_before', 'rng_after', 'root_moves_sha256'):
        digest_string(science[name], name)
    roots = array(science['roots'], 'roots')
    demand(len(roots) == entry['B'] and roots, 'manifest root count')
    root_actions, rows = [], []
    child_count = 0
    for root_index, root in enumerate(roots):
        exact_fields(root, {'first_transition_sha256', 'leaves', 'leaves_sha256', 'maximum', 'root',
                           'second_moves', 'second_moves_sha256', 'witness'}, 'root record')
        validate_action(root['root'])
        resolve_sequence(snapshot, [root['root']])
        root_actions.append(root['root'])
        digest_string(root['first_transition_sha256'], 'first transition provenance')
        seconds = array(root['second_moves'], 'second actions')
        leaves = array(root['leaves'], 'leaves')
        demand(len(leaves) == max(1, len(seconds)), 'one leaf per recorded second action or one carry')
        for action in seconds:
            validate_action(action)
        demand(len({canonical(action) for action in seconds}) == len(seconds), 'duplicate second actions')
        demand(digest(seconds) == root['second_moves_sha256'], 'second action digest')
        demand(digest(leaves) == root['leaves_sha256'], 'leaf digest')
        for leaf_index, leaf in enumerate(leaves):
            exact_fields(leaf, {'sequence', 'key', 'reason', 'transition_sha256'}, 'leaf')
            wanted = [root['root']] + ([seconds[leaf_index]] if seconds else [])
            demand(leaf['sequence'] == wanted, 'sequence/root/second-action binding')
            rows.append(leaf_row(snapshot, leaf, entry, source_pass, root_index, leaf_index))
            if not seconds:
                demand(leaf['transition_sha256'] == root['first_transition_sha256'], 'carry transition provenance binding')
        maximum = max(leaf['key'] for leaf in leaves)
        recorded_key(root['maximum'])
        demand(root['maximum'] == maximum, 'root maximum disagrees with recorded keys')
        for action in array(root['witness'], 'root witness'):
            validate_action(action)
        demand(root['witness'] == next(leaf['sequence'] for leaf in leaves if leaf['key'] == maximum),
               'root first maximum witness')
        child_count += len(seconds)
    demand(len({canonical(action) for action in root_actions}) == len(roots), 'duplicate root action')
    demand(digest(root_actions) == science['root_moves_sha256'] == baseline['root_moves_sha256'],
           'root action digest/baseline binding')
    collect_count = sum(a['action'] == 'collect' for a in root_actions)
    demand(collect_count == entry['collect_count_metadata'] == baseline['collect_count'], 'root COLLECT count')
    demand(len(roots) - collect_count == entry['place_count_metadata'] == baseline['place_count'], 'root PLACE count')
    expected_counts = dict(roots=len(roots), children=child_count, previews=len(roots) + child_count,
                           expanded_nodes=1 + len(roots), enumerations=1 + len(roots), leaves=len(rows))
    exact_fields(science['counts'], expected_counts, 'recorded counts')
    for name, expected in expected_counts.items():
        demand(integer(science['counts'][name], 'count ' + name, 0) == expected, 'recorded count mismatch: ' + name)
    demand(expected_counts['previews'] <= 32768, 'original per-call preview bound')
    best = max(root['maximum'] for root in roots)
    recorded_key(science['best'])
    demand(science['best'] == best, 'global recorded-key maximum')
    tier = [root['root'] for root in roots if root['maximum'] == best]
    for action in array(science['maximal_roots'], 'maximal roots'):
        validate_action(action)
    validate_action(science['chosen'])
    demand(science['maximal_roots'] == tier and science['chosen'] in tier, 'recorded maximal tier/chosen binding')
    observation = classify(rows, snapshot, entry)
    return rows, observation


def validate_population(manifest, snapshots, audits):
    demand(type(manifest) is dict and manifest.get('schema') == 'worker33-mixed-public-state-selection-preparation-v1',
           'manifest schema')
    entries = array(manifest.get('entries'), 'manifest entries')
    demand(len(entries) == len(snapshots) == len(audits) == OBSERVATIONS, 'fixed 80-observation population')
    seen = set()
    source_seeds = set()
    entry_fields = {'B', 'C', 'action_type_class', 'collect_count_metadata', 'group', 'ordinal',
                    'place_count_metadata', 'position', 'public_observation_sha256', 'seed',
                    'selection_key_input', 'selection_key_sha256', 'snapshot_file', 'snapshot_sha256',
                    'snapshot_size_bytes', 'source_trace_member', 'source_trace_sha256', 'stress_cost_proxy'}
    for position, (entry, snapshot, audit) in enumerate(zip(entries, snapshots, audits), 1):
        exact_fields(entry, entry_fields, 'manifest entry')
        demand(integer(entry['position'], 'manifest position') == position, 'manifest ordering')
        seed = integer(entry['seed'], 'seed', 1000000, 1000399)
        ordinal = integer(entry['ordinal'], 'ordinal', 1)
        demand((seed, ordinal) not in seen, 'duplicate observation identity')
        seen.add((seed, ordinal)); source_seeds.add(seed)
        for name in ('B', 'C', 'collect_count_metadata', 'place_count_metadata', 'snapshot_size_bytes', 'stress_cost_proxy'):
            integer(entry[name], 'manifest ' + name, 1)
        demand(entry['action_type_class'] == 'mixed', 'manifest action type')
        demand(entry['B'] == entry['collect_count_metadata'] + entry['place_count_metadata'], 'manifest action totals')
        validate_snapshot(snapshot)
        collectible = sum((card['material'] == 'raincoat' and snapshot['raincoats'] < 3) or
                          (card['material'] == 'rope' and snapshot['ropes'] < 2) for card in snapshot['hand'])
        demand(collectible == entry['collect_count_metadata'], 'original-hand collect metadata count')
        h = digest(snapshot)
        demand(entry['snapshot_size_bytes'] == len(canonical(snapshot)), 'snapshot byte-size binding')
        demand(entry['snapshot_file'] == f'snapshots/{position:03d}-seed-{seed}-ordinal-{ordinal:03d}.json',
               'snapshot member identity')
        demand(entry['source_trace_member'] == f'decision-traces/pass-2/{seed}.jsonl', 'source trace identity')
        demand(entry['group'] == ('hash64' if position <= 64 else 'stress16'), 'manifest group ordering')
        demand(entry['public_observation_sha256'] == entry['snapshot_sha256'] == h, 'snapshot hash binding')
        for name in ('source_trace_sha256', 'selection_key_sha256'):
            digest_string(entry[name], name)
        key_text = f'mixed-action-two-action-diagnostic-v1|{seed}|{ordinal}|{h}'
        demand(entry['selection_key_input'] == key_text and
               entry['selection_key_sha256'] == hashlib.sha256(key_text.encode()).hexdigest(), 'selection identity digest')
        exact_fields(audit, {'legal_move_count', 'ordinal', 'position', 'primary_score', 'primary_tier',
                             'primary_tier_sha256', 'public_observation_sha256', 'seed'}, 'audit reference row')
        for name in ('position', 'seed', 'ordinal'):
            demand(integer(audit[name], 'audit ' + name) == entry[name], 'audit identity')
        demand(audit['public_observation_sha256'] == h, 'audit public hash')
        demand(integer(audit['legal_move_count'], 'audit root count', 1) == entry['B'], 'audit root count binding')
        integer(audit['primary_score'], 'audit score')
        for action in array(audit['primary_tier'], 'audit primary tier'):
            resolve_sequence(snapshot, [action])
        demand(audit['primary_tier'] and digest(audit['primary_tier']) == audit['primary_tier_sha256'], 'audit tier digest')
    demand(len(source_seeds) == SEEDS, 'fixed 71-seed identity count')
    return entries


def validate_archive_directory(archive):
    infos = archive.infolist()
    names = [i.filename for i in infos]
    demand(len(names) == len(set(names)), 'duplicate ZIP member names')
    for info in infos:
        path = PurePosixPath(info.filename)
        demand(info.filename and not path.is_absolute() and not re.match(r'^[A-Za-z]:', info.filename)
               and all(p not in ('', '.', '..') for p in info.filename.split('/'))
               and '\\' not in info.filename and '\x00' not in info.filename, 'unsafe ZIP member path')
        mode = info.external_attr >> 16
        demand(not info.is_dir() and stat.S_IFMT(mode) in (0, stat.S_IFREG), 'unexpected ZIP member type')
        demand(not info.flag_bits & 1, 'encrypted ZIP member')
        demand(info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), 'unsupported ZIP compression')
        demand(0 <= info.file_size <= ARCHIVE_MAX, 'ZIP member expansion bound')
    demand(sum(i.file_size for i in infos) == ARCHIVE_TOTAL, 'ZIP total expansion mismatch')
    demand(max((i.file_size for i in infos), default=0) == ARCHIVE_MAX, 'ZIP largest member mismatch')
    return set(names)


def read_member(archive, name, pin):
    try:
        info = archive.getinfo(name)
        demand(info.file_size == pin[0], name + ': declared member size mismatch')
        with archive.open(info, 'r') as stream:
            raw = stream.read(pin[0] + 1)
    except (KeyError, zipfile.BadZipFile, RuntimeError, EOFError) as exc:
        raise IntegrityError(name + ': missing/corrupt archive member') from exc
    return checked_bytes(raw, pin, name)


def prepare_archive(archive):
    members = validate_archive_directory(archive)
    inventory = decode(read_member(archive, 'inventory.json', MEMBER_PINS['inventory.json']), 'inventory')
    exact_fields(inventory, {'files', 'finalized'}, 'archive inventory')
    demand(type(inventory['files']) is dict and type(inventory['finalized']) is str, 'inventory types')
    demand(members == set(inventory['files']) | {'inventory.json'}, 'complete ZIP/inventory member set')
    calls = {f'call-{i:03d}.json' for i in range(1, CALLS + 1)}
    demand({name for name in members if name.startswith('call-') and name != 'call-order.json'} == calls,
           'fixed 160-call member set')
    pins = {}
    for name, metadata in inventory['files'].items():
        exact_fields(metadata, {'sha256', 'size_bytes'}, 'inventory file')
        integer(metadata['size_bytes'], 'inventory size', 0, ARCHIVE_MAX)
        digest_string(metadata['sha256'], 'inventory hash')
        pin = (metadata['size_bytes'], metadata['sha256'])
        demand(archive.getinfo(name).file_size == pin[0], 'inventory/declaration size mismatch')
        if name in MEMBER_PINS:
            demand(pin == MEMBER_PINS[name], 'named member fixed pin mismatch')
        pins[name] = pin
        # Calls are verified immediately before their paired observation is parsed.
        if name not in calls:
            read_member(archive, name, pin)
    return pins


def validate_call_order(order, entries):
    demand(type(order) is list and len(order) == CALLS, 'fixed 160-call order')
    for index, item in enumerate(order):
        exact_fields(item, {'ordinal', 'pass_number', 'position', 'seed'}, 'call order entry')
        entry = entries[index % OBSERVATIONS]
        for key in ('position', 'seed', 'ordinal'):
            demand(integer(item[key], 'call order ' + key) == entry[key], 'call-order observation binding')
        demand(integer(item['pass_number'], 'call-order pass') == 1 + index // OBSERVATIONS, 'call-order pass binding')


def validate_baselines(baselines, audits, entries):
    demand(type(baselines) is list and len(baselines) == OBSERVATIONS, 'baseline population')
    for baseline, audit, entry in zip(baselines, audits, entries):
        exact_fields(baseline, {'collect_count', 'legal_move_count', 'place_count', 'root_moves_sha256', 'score', 'tier'},
                     'baseline gate')
        for name, value in [('collect_count', entry['collect_count_metadata']), ('place_count', entry['place_count_metadata']),
                            ('legal_move_count', entry['B']), ('score', audit['primary_score'])]:
            demand(integer(baseline[name], 'baseline ' + name) == value, 'baseline/audit metadata mismatch')
        digest_string(baseline['root_moves_sha256'], 'baseline root hash')
        demand(baseline['tier'] == audit['primary_tier'] and digest(baseline['tier']) == audit['primary_tier_sha256'],
               'baseline/audit tier binding')


def verify_accepted_evidence(evidence):
    verification = evidence['independent-verification.json']
    pins = evidence['execution-pins.json']
    review = evidence['source-review.json']
    for value in evidence.values():
        demand(type(value) is dict and value.get('head') == HEAD and value.get('tree') == TREE, 'accepted source binding')
    for value in (verification, pins):
        demand(type(value.get('run_id')) is int and value['run_id'] == RUN and
               type(value.get('artifact_id')) is int and value['artifact_id'] == ARTIFACT,
               'accepted run/artifact binding')
        demand(value.get('zip_sha256') == INPUT_PINS['worker33-evidence/actions-artifact.zip'][1], 'accepted ZIP binding')
    demand(verification.get('status') == 'accepted' and verification.get('classification') == ORIGINAL_STATUS,
           'original acceptance status')
    demand(integer(verification.get('completed_calls'), 'accepted calls') == CALLS and
           integer(verification.get('exact_scientific_matches'), 'accepted matches') == OBSERVATIONS,
           'accepted population count')
    demand(verification.get('strict_departures') == [] and integer(verification.get('fresh_seeds'), 'fresh seeds') == 0 and
           integer(verification.get('new_games'), 'new games') == 0, 'accepted scope')
    demand(pins.get('schema') == 'worker33-offline-execution-pins-v1' and
           integer(pins.get('run_attempt'), 'run attempt') == 1, 'execution pins schema/run attempt')
    demand(pins.get('source_review_sha256') == INPUT_PINS['worker33-evidence/source-review.json'][1], 'review pin binding')
    demand(review.get('schema') == 'worker33-exact-head-source-review-v1' and review.get('status') == 'approved', 'source review status')
    demand(type(review.get('claims')) is dict and review['claims'] and all(v is True for v in review['claims'].values()),
           'source review claims')


def scientific_summary(observations, counts):
    demand(len(observations) == OBSERVATIONS, 'complete observation output required')
    demand(set(counts) == {'candidate', 'reference'}, 'source implementation accounting')
    for label in counts:
        demand(counts[label] == EXPECTED_COUNTS, label + ': fixed leaf accounting mismatch')
    n = sum(o['has_tradeoff'] for o in observations)
    u = sum(o['has_unmatched_exit_stratum'] for o in observations)
    status = ('recorded_component_tradeoff_present' if n else
              'recorded_component_tradeoff_absent_with_unmatched_strata' if u else
              'recorded_component_tradeoff_absent')
    return dict(schema='worker33-endpoint-summary-v1', status=status, denominator=OBSERVATIONS, N=n, U=u,
                N_U_overlap=sum(o['has_tradeoff'] and o['has_unmatched_exit_stratum'] for o in observations),
                observations_without_pp=sum(o['has_no_eligible_pp'] for o in observations),
                completed_source_calls=CALLS, matched_source_pairs=OBSERVATIONS,
                counts_by_source_implementation=counts, all_integrity_checks_passed=True,
                provenance=dict(protocol_sha256=PROTOCOL_SHA256, original_run_id=RUN, original_run_attempt=1,
                                original_artifact_id=ARTIFACT, original_execution_head=HEAD,
                                inputs_sha256={name: pin[1] for name, pin in INPUT_PINS.items()}))


def analyze(artifact, frozen, accepted_evidence, output_dir):
    paths = {name: (artifact if name.endswith('actions-artifact.zip') else
                   (frozen if name.startswith('worker33-preparation/') else accepted_evidence) / name.split('/')[-1])
             for name in INPUT_PINS}
    # Verify availability as one gate before admission/hashing any real input.
    for name, path in paths.items():
        if not path.is_file():
            raise ExecutionBlocked('required input unavailable: ' + name)
    # The archive is hashed incrementally; only one observation pair is decoded at once.
    zip_pin = INPUT_PINS['worker33-evidence/actions-artifact.zip']
    demand(artifact.stat().st_size == zip_pin[0], 'outer ZIP byte-size mismatch')
    demand(hash_file(artifact) == zip_pin[1], 'outer ZIP SHA256 mismatch')
    raw_inputs = {name: read_pinned_file(path, INPUT_PINS[name]) for name, path in paths.items()
                  if not name.endswith('actions-artifact.zip')}
    manifest = decode(raw_inputs['worker33-preparation/selection-manifest.json'], 'manifest')
    snapshots = json_lines(raw_inputs['worker33-preparation/selected-corpus.jsonl'], 'corpus')
    audits = json_lines(raw_inputs['worker33-preparation/audit-reference.jsonl'], 'audit reference')
    evidence = {name.split('/')[-1]: decode(raw, name) for name, raw in raw_inputs.items()
                if name.startswith('worker33-evidence/') and name.endswith('.json')}
    verify_accepted_evidence(evidence)
    entries = validate_population(manifest, snapshots, audits)
    del raw_inputs
    observations = []
    counts = {name: dict.fromkeys(EXPECTED_COUNTS, 0) for name in ('candidate', 'reference')}
    with zipfile.ZipFile(artifact, 'r') as archive:
        member_pins = prepare_archive(archive)
        order = decode(read_member(archive, 'call-order.json', MEMBER_PINS['call-order.json']), 'call order')
        validate_call_order(order, entries)
        baselines = decode(read_member(archive, 'baseline-gates.json', MEMBER_PINS['baseline-gates.json']), 'baseline gates')
        validate_baselines(baselines, audits, entries)
        result = decode(read_member(archive, 'result.json', MEMBER_PINS['result.json']), 'original result')
        exact_fields(result, {'completed_calls', 'scope', 'status', 'strict_departures'}, 'original result')
        demand(integer(result['completed_calls'], 'original completed calls') == CALLS and
               result['status'] == ORIGINAL_STATUS and result['strict_departures'] == [] and type(result['scope']) is str,
               'original result binding')
        with (output_dir / 'leaves.jsonl.incomplete').open('xb') as leaves_out, \
             (output_dir / 'observations.jsonl.incomplete').open('xb') as observations_out:
            for entry, snapshot, baseline in zip(entries, snapshots, baselines):
                pair = []
                for source_pass in (1, 2):
                    call = entry['position'] + (source_pass - 1) * OBSERVATIONS
                    name = f'call-{call:03d}.json'
                    payload = decode(read_member(archive, name, member_pins[name]), name)
                    rows, observation = parse_call(payload, snapshot, entry, baseline, source_pass)
                    pair.append((payload['scientific'], rows, observation))
                demand(canonical(pair[0][0]) == canonical(pair[1][0]), 'complete candidate/reference scientific mismatch')
                demand(canonical(pair[0][2]) == canonical(pair[1][2]), 'derived observation disagreement')
                # Derived row equality excludes only the three intentional source identities.
                for left, right in zip(pair[0][1], pair[1][1]):
                    omitted = {'source_pass', 'call_number', 'source_implementation'}
                    demand(canonical({k: v for k, v in left.items() if k not in omitted}) ==
                           canonical({k: v for k, v in right.items() if k not in omitted}), 'derived paired leaf disagreement')
                for _, rows, observation in pair:
                    for row in rows:
                        leaves_out.write(canonical(row))
                        totals = counts[row['source_implementation']]
                        totals['total_leaves'] += 1
                        totals['horizon_leaves' if row['depth'] == 2 else 'carry_leaves'] += 1
                observations.append(pair[0][2])
                observations_out.write(canonical(pair[0][2]))
                del pair
            for stream in (leaves_out, observations_out):
                stream.flush()
                os.fsync(stream.fileno())
        summary = scientific_summary(observations, counts)
        with (output_dir / 'summary.json.incomplete').open('xb') as summary_out:
            summary_out.write(canonical(summary))
            summary_out.flush()
            os.fsync(summary_out.fileno())
    for name in ('leaves.jsonl', 'observations.jsonl', 'summary.json'):
        (output_dir / (name + '.incomplete')).rename(output_dir / name)
    sync_directory(output_dir)


def sync_directory(directory):
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def enforce_address_space():
    if sys.platform != 'linux':
        raise ExecutionBlocked('Linux RLIMIT_AS required')
    try:
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
        effective = resource.getrlimit(resource.RLIMIT_AS)
    except (ValueError, OSError) as exc:
        raise ExecutionBlocked('RLIMIT_AS unavailable: ' + str(exc)) from exc
    if effective != (MEMORY_BYTES, MEMORY_BYTES):
        raise ExecutionBlocked('RLIMIT_AS effective boundary differs from exactly 2 GiB')
    return effective


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--frozen', type=Path, required=True)
    parser.add_argument('--accepted-evidence', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    started = time.monotonic()
    receipt = dict(parser_id='b', source_sha256=hash_file(Path(__file__)),
                   interpreter_executable=sys.executable, interpreter_version=sys.version,
                   pid=os.getpid(), rlimit_as_soft=None, rlimit_as_hard=None, status='execution_blocked',
                   completed=False, elapsed_seconds=0, maxrss_kib=0,
                   established_integrity_failure=False, errors=[])
    output_created = False
    try:
        if args.output_dir.exists():
            raise ExecutionBlocked('output directory must not already exist; previous attempts are preserved')
        args.output_dir.mkdir(parents=True, exist_ok=False)
        output_created = True
        soft, hard = enforce_address_space()
        receipt.update(rlimit_as_soft=soft, rlimit_as_hard=hard)
        protocol = Path(__file__).resolve().parent.parent / 'experiments' / 'recorded-endpoint-decomposition' / 'PROTOCOL.md'
        if not protocol.is_file():
            raise ExecutionBlocked('frozen protocol file unavailable')
        demand(hash_file(protocol) == PROTOCOL_SHA256, 'frozen protocol hash mismatch')
        analyze(args.artifact, args.frozen, args.accepted_evidence, args.output_dir)
        receipt.update(status='complete', completed=True)
        code = 0
    except IntegrityError as exc:
        receipt.update(status='integrity_invalid', established_integrity_failure=True, errors=[str(exc)])
        code = 2
    except ExecutionBlocked as exc:
        receipt.update(status='execution_blocked', errors=[str(exc)])
        code = 3
    except (MemoryError, OSError) as exc:
        receipt.update(status='resource_incomplete', errors=[type(exc).__name__ + ': ' + str(exc)])
        code = 4
    except zipfile.BadZipFile as exc:
        receipt.update(status='integrity_invalid', established_integrity_failure=True, errors=[str(exc)])
        code = 2
    except Exception as exc:
        # An implementation exception or interrupted output is not proven input corruption.
        receipt.update(status='resource_incomplete', errors=['unresolved ' + type(exc).__name__ + ': ' + str(exc)])
        code = 4
    receipt['elapsed_seconds'] = time.monotonic() - started
    receipt['maxrss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if not output_created:
        print('; '.join(receipt['errors']), file=sys.stderr)
        return code
    try:
        temporary = args.output_dir / 'parser-receipt.json.incomplete'
        with temporary.open('xb') as stream:
            stream.write(canonical(receipt))
            stream.flush()
            os.fsync(stream.fileno())
        temporary.rename(args.output_dir / 'parser-receipt.json')
        sync_directory(args.output_dir)
    except OSError as exc:
        print('receipt could not be preserved: ' + str(exc), file=sys.stderr)
        return 4
    return code


if __name__ == '__main__':
    raise SystemExit(main())
