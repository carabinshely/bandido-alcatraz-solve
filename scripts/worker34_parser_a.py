#!/usr/bin/env python3
"""Worker34 parser A: independent, standard-library recorded-metadata audit.

No engine imports, board reconstruction, RNG replay, game execution or subprocesses.
Production invocation is permitted only after the separate source/runtime freeze.
"""
import argparse
import bisect
import collections
import datetime
import errno
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import resource
import stat
import sys
import time
import zipfile

PROTOCOL_SHA256 = 'cad7dc56e16b6f12d34fac7cb5b5aa8c3c5e791cb18536880e9170b162e7258e'
ADDRESS_SPACE_LIMIT = 2147483648
PINS = {
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
ZIP_TOTAL = 136061225
ZIP_LARGEST = 6347785
ZIP_MEMBER_COUNT = 173
EXPECTED_COUNTS = dict(total_leaves=191920, horizon_leaves=191919, carry_leaves=1,
                       visible_victory_leaves=0, closed_tunnel_loss_leaves=0)
EXECUTION_HEAD = '99164d0212d50fce37f8a2a9656198ca08ccde32'
EXECUTION_TREE = '8351ff128c91c34276382e427dadcf10ba844591'
OLD_STATUS = 'mixed_action_two_action_diagnostic_mechanism_not_exercised'
CLASSIFICATIONS = ('component_dominated', 'geometric_tradeoff', 'unmatched_exit_stratum')
PATTERNS = ('CC', 'CP', 'PC', 'PP')


class IntegrityError(ValueError):
    """A completed validation established an input/contract mismatch."""


class ExecutionBlocked(RuntimeError):
    """A prerequisite was unavailable before admission/verification."""


def require(condition, message):
    if not condition:
        raise IntegrityError(message)


def keys(value, names, context):
    require(type(value) is dict and set(value) == set(names.split()), context + ': object keys')


def integer(value, context, low=None, high=None):
    require(type(value) is int, context + ': exact integer required')
    require((low is None or value >= low) and (high is None or value <= high), context + ': integer range')
    return value


def boolean(value, context):
    require(type(value) is bool, context + ': exact Boolean required')


def array(value, context):
    require(type(value) is list, context + ': array required')
    return value


def string(value, context):
    require(type(value) is str and bool(value), context + ': nonempty string required')


def digest_string(value, context):
    require(type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value), context + ': SHA256')


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')


def sha(value):
    return hashlib.sha256(encode(value)).hexdigest()


def strict_json(raw):
    def object_pairs(items):
        result = {}
        for name, value in items:
            require(name not in result, 'duplicate JSON key: ' + name)
            result[name] = value
        return result

    def nonfinite(value):
        raise IntegrityError('nonfinite JSON: ' + value)

    def finite_float(value):
        result = float(value)
        require(math.isfinite(result), 'nonfinite JSON exponent')
        return result

    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=object_pairs,
                          parse_constant=nonfinite, parse_float=finite_float)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise IntegrityError('invalid JSON encoding/syntax') from exc


def jsonl(raw):
    require(raw.endswith(b'\n') and not raw.startswith(b'\xef\xbb\xbf'), 'JSONL newline/BOM')
    lines = raw.split(b'\n')[:-1]
    require(all(line.strip() for line in lines), 'blank JSONL row')
    return [strict_json(line) for line in lines]


def pinned_bytes(raw, pin, context):
    require(len(raw) == pin[0], context + ': byte size mismatch')
    require(hashlib.sha256(raw).hexdigest() == pin[1], context + ': SHA256 mismatch')
    return raw


def read_pinned(path, pin, retain=True):
    digest = hashlib.sha256()
    chunks = []
    size = 0
    try:
        stream = Path(path).open('rb')
    except OSError as exc:
        if exc.errno in (errno.ENOMEM, errno.EMFILE, errno.ENFILE):
            raise
        raise ExecutionBlocked('required input inaccessible before verification: ' + str(path)) from exc
    with stream:
        while True:
            chunk = stream.read(min(1024 * 1024, pin[0] + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
            if retain:
                chunks.append(chunk)
            require(size <= pin[0], str(path) + ': byte size exceeded')
    require(size == pin[0] and digest.hexdigest() == pin[1], str(path) + ': byte size/SHA256 mismatch')
    return b''.join(chunks) if retain else None


def coordinate(value):
    require(type(value) is list and len(value) == 2, 'coordinate shape')
    for v in value:
        integer(v, 'coordinate')


def cell_schema(value):
    # Shape/type checks only: never infer connectivity, features or legality.
    keys(value, 'x y tunnel_edges water', 'inert cell')
    integer(value['x'], 'cell x')
    integer(value['y'], 'cell y')
    boolean(value['water'], 'cell water')
    edges = array(value['tunnel_edges'], 'cell edges')
    require(all(type(e) is str and e in ('N', 'E', 'S', 'W') for e in edges), 'cell edge enum')
    require(edges == sorted(set(edges)), 'cell edge source schema order')


def card_schema(card):
    keys(card, 'card_id cells is_exit material', 'card')
    string(card['card_id'], 'card ID')
    boolean(card['is_exit'], 'card EXIT')
    require(card['material'] is None or (type(card['material']) is str and card['material'] in ('raincoat', 'rope')), 'card material')
    require(not card['is_exit'] or card['material'] is None, 'EXIT material')
    for cell in array(card['cells'], 'card inert cells'):
        cell_schema(cell)


def snapshot_schema(value):
    keys(value, 'board hand raincoats ropes exit_placed exit_seen turns set_aside_unplayable collected_equipment setup player_index', 'snapshot')
    integer(value['raincoats'], 'raincoats', 0, 3)
    integer(value['ropes'], 'ropes', 0, 2)
    for field in ('turns', 'set_aside_unplayable'):
        integer(value[field], field, 0)
    integer(value['player_index'], 'player_index', 0, 0)
    boolean(value['exit_placed'], 'exit_placed')
    boolean(value['exit_seen'], 'exit_seen')
    keys(value['setup'], 'hand_size player_count start_side starting_player', 'setup')
    for name, fixed in (('hand_size', 6), ('player_count', 1), ('starting_player', 0)):
        integer(value['setup'][name], 'setup ' + name, fixed, fixed)
    require(value['setup']['start_side'] == 'easy-5-exit', 'setup start side')
    keys(value['board'], 'cells placements', 'inert board')
    for cell in array(value['board']['cells'], 'inert board cells'):
        cell_schema(cell)
    for placement in array(value['board']['placements'], 'inert placements'):
        keys(placement, 'card_id cells covered_placement_index kind origin overlaps placement_index quarter_turns', 'inert placement')
        string(placement['card_id'], 'placement card ID')
        require(placement['kind'] in ('start', 'ordinary', 'exit'), 'placement kind')
        integer(placement['placement_index'], 'placement index', 0)
        integer(placement['quarter_turns'], 'placement quarter turns', 0, 3)
        if placement['covered_placement_index'] is not None:
            integer(placement['covered_placement_index'], 'covered placement index', 0)
        coordinate(placement['origin'])
        for field in ('cells', 'overlaps'):
            for point in array(placement[field], 'inert placement coordinates'):
                coordinate(point)
    hand = array(value['hand'], 'hand')
    require(len(hand) <= 6, 'original hand size')
    for card in hand:
        card_schema(card)
    require(len({card['card_id'] for card in hand}) == len(hand), 'duplicate physical hand card')
    exit_count = sum(card['is_exit'] for card in hand)
    require(exit_count <= 1 and not (exit_count and value['exit_placed']), 'incompatible original EXIT inventory')
    for old in array(value['collected_equipment'], 'inert collected history'):
        keys(old, 'card turn player_index', 'inert collected record')
        integer(old['turn'], 'history turn', 1)
        integer(old['player_index'], 'history player', 0, 0)
        card_schema(old['card'])


def action_schema(action):
    keys(action, 'action hand_index origin quarter_turns', 'recorded action')
    require(type(action['action']) is str and action['action'] in ('place', 'collect'), 'action enum')
    integer(action['hand_index'], 'hand index', 0)
    integer(action['quarter_turns'], 'quarter turns', 0, 3)
    if action['action'] == 'collect':
        require(action['origin'] is None and action['quarter_turns'] == 0, 'COLLECT origin/rotation')
    else:
        coordinate(action['origin'])


def bookkeep(snapshot, sequence):
    """Delete recorded retained-hand indices only; no endpoint state is made."""
    remaining = list(range(len(snapshot['hand'])))
    r, p, x = snapshot['raincoats'], snapshot['ropes'], snapshot['exit_placed']
    integer(r, 'initial raincoats', 0, 3)
    integer(p, 'initial ropes', 0, 2)
    boolean(x, 'initial EXIT')
    mapped = []
    used = set()
    for action in array(sequence, 'sequence'):
        action_schema(action)
        index = action['hand_index']
        require(index < len(remaining), 'retained hand index out of bounds')
        original = remaining.pop(index)
        card = snapshot['hand'][original]
        require(card['card_id'] not in used, 'repeated physical card')
        used.add(card['card_id'])
        if action['action'] == 'collect':
            require(not card['is_exit'], 'collect EXIT')
            if card['material'] == 'raincoat':
                require(r < 3, 'raincoat quota history')
                r += 1
            elif card['material'] == 'rope':
                require(p < 2, 'rope quota history')
                p += 1
            else:
                raise IntegrityError('collect material-free card')
        elif card['is_exit']:
            require(not x, 'EXIT already placed')
            x = True
        mapped.append(dict(action, original_hand_index=original, card_id=card['card_id']))
    return mapped, r, p, x


def key_schema(key):
    require(type(key) is list and len(key) == 3, 'recorded key length')
    for component in key:
        integer(component, 'recorded key component')


def normalize_leaf(snapshot, leaf, identity, root_index, leaf_index):
    keys(leaf, 'sequence key reason transition_sha256', 'leaf')
    key_schema(leaf['key'])
    digest_string(leaf['transition_sha256'], 'leaf transition provenance')
    seq = array(leaf['sequence'], 'leaf sequence')
    require(type(leaf['reason']) is str, 'leaf reason type')
    if leaf['reason'] in ('visible_victory', 'closed_tunnel_loss') or leaf['key'][0] in (0, 2):
        raise IntegrityError('frozen contract prohibits terminal leaves/placeholders')
    require(leaf['key'][:2] == [1, 0], 'nonterminal key prefix')
    depth = len(seq)
    if leaf['reason'] == 'horizon':
        require(depth == 2, 'horizon sequence depth')
    else:
        require(leaf['reason'] == 'omitted_draw_dead_end' and depth == 1, 'unsupported reason/depth')
        require((identity['position'], identity['seed'], identity['ordinal']) == (62, 1000089, 15), 'carry identity')
        require(encode(seq) == encode([dict(action='place', hand_index=5, origin=[-5, -2], quarter_turns=3)]), 'carry action')
        require(leaf['key'] == [1, 0, 29900], 'carry key')
    mapped, r, p, x = bookkeep(snapshot, seq)
    pattern = ''.join('C' if a['action'] == 'collect' else 'P' for a in seq)
    require(pattern in PATTERNS or (depth == 1 and pattern == 'P'), 'pattern')
    equipment = 10000 * (r + p)
    exit_term = 0 if not x else (5000 if (r, p) == (3, 2) else -5000)
    role = 'excluded_depth_one_carry' if depth == 1 else ('primary_pp' if pattern == 'PP' else 'collection_comparator')
    if role == 'primary_pp':
        require((r, p) == (snapshot['raincoats'], snapshot['ropes']), 'PP inventory invariant')
    elif role == 'collection_comparator':
        require(r >= snapshot['raincoats'] and p >= snapshot['ropes'] and
                (r > snapshot['raincoats'] or p > snapshot['ropes']), 'collection inventory invariant')
    return dict(schema='worker33-endpoint-leaf-v1', **identity, root_index=root_index,
                leaf_index=leaf_index, depth=depth, sequence=mapped, recorded_key=leaf['key'],
                reason=leaf['reason'], inventory=dict(raincoats=r, ropes=p), exit_placed=x,
                equipment_term=equipment, exit_term=exit_term,
                geometric_score=leaf['key'][2] - equipment - exit_term, pattern=pattern, role=role,
                stratum=dict(depth=depth, exit_placed=x, key_class=leaf['key'][0], reason=leaf['reason']),
                pp_classification=None, witness=None)


def witness(row):
    return dict(root_index=row['root_index'], leaf_index=row['leaf_index'])


def order_key(row):
    return row['root_index'], row['leaf_index']


def classify(rows):
    """Dominance by separate inventory groups and canonical prefix G maxima."""
    for x in (False, True):
        members = [r for r in rows if r['depth'] == 2 and r['exit_placed'] is x]
        comparators = sorted((r for r in members if r['role'] == 'collection_comparator'), key=order_key)
        groups = {}
        for c in comparators:
            inv = (c['inventory']['raincoats'], c['inventory']['ropes'])
            scores, firsts = groups.setdefault(inv, ([], []))
            if not scores or c['geometric_score'] > scores[-1]:
                scores.append(c['geometric_score'])
                firsts.append(c)
        best = max((c['geometric_score'] for c in comparators), default=None)
        first_best = next((c for c in comparators if c['geometric_score'] == best), None)
        for b in members:
            if b['role'] != 'primary_pp':
                continue
            if not comparators:
                b['pp_classification'] = 'unmatched_exit_stratum'
                continue
            br, bp = b['inventory']['raincoats'], b['inventory']['ropes']
            dominators = []
            for (cr, cp), (scores, firsts) in groups.items():
                if cr < br or cp < bp:
                    continue
                # Equal inventory needs strict G; otherwise equal G suffices.
                index = (bisect.bisect_right(scores, b['geometric_score']) if (cr, cp) == (br, bp)
                         else bisect.bisect_left(scores, b['geometric_score']))
                if index < len(scores):
                    dominators.append(firsts[index])
            if dominators:
                b['pp_classification'] = 'component_dominated'
                b['witness'] = witness(min(dominators, key=order_key))
            else:
                # Metadata validation makes all C strictly inventory-superior to PP.
                require(all(c['inventory']['raincoats'] >= br and c['inventory']['ropes'] >= bp and
                            (c['inventory']['raincoats'] > br or c['inventory']['ropes'] > bp)
                            for c in comparators), 'collection versus PP inventory inequalities')
                require(b['geometric_score'] > best, 'tradeoff strict G equivalence')
                b['pp_classification'] = 'geometric_tradeoff'
                b['witness'] = witness(first_best)


def observation_row(entry, rows):
    strata = []
    for x in (False, True):
        values = [r for r in rows if r['depth'] == 2 and r['exit_placed'] is x]
        pp = [r for r in values if r['role'] == 'primary_pp']
        cc = [r for r in values if r['role'] == 'collection_comparator']
        classifications = collections.Counter(r['pp_classification'] for r in pp)
        patterns = []
        for pattern in PATTERNS:
            counts = collections.Counter((r['inventory']['raincoats'], r['inventory']['ropes'], r['geometric_score'])
                                         for r in values if r['pattern'] == pattern)
            patterns.append(dict(pattern=pattern, vectors=[[*vector, counts[vector]] for vector in sorted(counts)]))
        strata.append(dict(exit_placed=x, pp_count=len(pp), collection_count=len(cc),
                           pp_max_geometric_score=max((r['geometric_score'] for r in pp), default=None),
                           collection_max_geometric_score=max((r['geometric_score'] for r in cc), default=None),
                           class_counts={c: classifications[c] for c in CLASSIFICATIONS}, vector_multiplicities=patterns))
    return dict(schema='worker33-endpoint-observation-v1', position=entry['position'], seed=entry['seed'], ordinal=entry['ordinal'],
                horizon_leaf_count=sum(r['depth'] == 2 for r in rows), carry_leaf_count=sum(r['depth'] == 1 for r in rows),
                has_tradeoff=any(r['pp_classification'] == 'geometric_tradeoff' for r in rows),
                has_unmatched_exit_stratum=any(r['pp_classification'] == 'unmatched_exit_stratum' for r in rows),
                has_no_eligible_pp=not any(r['role'] == 'primary_pp' for r in rows), strata=strata)


def validate_envelope(envelope, identity):
    keys(envelope, 'pass call implementation seed ordinal run_id run_attempt started finished wall_seconds cpu_seconds peak_rss_kib physical_legal_moves', 'call envelope')
    for field, expected in (('pass', identity['source_pass']), ('call', identity['call_number']),
                            ('seed', identity['seed']), ('ordinal', identity['ordinal'])):
        integer(envelope[field], 'envelope ' + field, expected, expected)
    require(envelope['implementation'] == identity['source_implementation'], 'envelope implementation')
    require(envelope['run_id'] == '36961069413' and envelope['run_attempt'] == '1', 'original run binding')
    for field in ('wall_seconds', 'cpu_seconds'):
        v = envelope[field]
        require(type(v) in (int, float) and math.isfinite(v) and v >= 0, 'envelope cost')
    integer(envelope['peak_rss_kib'], 'envelope RSS', 0)
    integer(envelope['physical_legal_moves'], 'envelope physical calls', 1)
    timestamps = []
    for field in ('started', 'finished'):
        string(envelope[field], 'envelope timestamp')
        try:
            timestamp = datetime.datetime.fromisoformat(envelope[field])
        except ValueError as exc:
            raise IntegrityError('malformed envelope timestamp') from exc
        require(timestamp.tzinfo is not None and timestamp.utcoffset() == datetime.timedelta(0), 'envelope UTC timezone')
        timestamps.append(timestamp)
    require(timestamps[1] >= timestamps[0], 'reversed envelope times')


def analyze_call(value, snapshot, entry, baseline, source_pass):
    keys(value, 'envelope scientific', 'call')
    identity = dict(position=entry['position'], seed=entry['seed'], ordinal=entry['ordinal'], source_pass=source_pass,
                    source_implementation='candidate' if source_pass == 1 else 'reference', call_number=entry['position'] + 80 * (source_pass - 1))
    validate_envelope(value['envelope'], identity)
    sci = value['scientific']
    keys(sci, 'schema input_before input_after root_moves_sha256 roots maximal_roots chosen best rng_before rng_after counts', 'scientific')
    require(sci['schema'] == 'worker32-scientific-v1', 'original scientific schema')
    for name in ('input_before', 'input_after', 'root_moves_sha256', 'rng_before', 'rng_after'):
        digest_string(sci[name], 'scientific ' + name)
    require(sci['input_before'] == sci['input_after'] == entry['public_observation_sha256'], 'scientific snapshot binding')
    roots = array(sci['roots'], 'roots')
    require(bool(roots) and len(roots) == baseline['legal_move_count'] == entry['B'], 'root count binding')
    recorded_roots = []
    rows = []
    children = 0
    expanded = 0
    for ri, root in enumerate(roots):
        keys(root, 'root first_transition_sha256 second_moves second_moves_sha256 leaves leaves_sha256 maximum witness', 'root')
        action_schema(root['root'])
        recorded_roots.append(root['root'])
        digest_string(root['first_transition_sha256'], 'first transition provenance')
        for field in ('second_moves_sha256', 'leaves_sha256'):
            digest_string(root[field], field)
        seconds = array(root['second_moves'], 'second actions')
        leaves = array(root['leaves'], 'recorded leaves')
        require(root['second_moves_sha256'] == sha(seconds) and root['leaves_sha256'] == sha(leaves), 'ordered children/leaves hash')
        require(len(leaves) == max(1, len(seconds)), 'complete leaf coverage')
        for second in seconds:
            action_schema(second)
        require(len({encode(s) for s in seconds}) == len(seconds), 'duplicate recorded second action')
        children += len(seconds)
        keys(leaves[0], 'sequence key reason transition_sha256', 'leaf')
        expanded += int(bool(seconds) or leaves[0]['reason'] == 'omitted_draw_dead_end')
        for li, leaf in enumerate(leaves):
            keys(leaf, 'sequence key reason transition_sha256', 'leaf')
            expected = [root['root']] + ([seconds[li]] if seconds else [])
            require(encode(leaf['sequence']) == encode(expected), 'leaf/root/second sequence binding')
            rows.append(normalize_leaf(snapshot, leaf, identity, ri, li))
        key_schema(root['maximum'])
        maximum = max(leaf['key'] for leaf in leaves)
        require(root['maximum'] == maximum and encode(root['witness']) == encode(next(leaf['sequence'] for leaf in leaves if leaf['key'] == maximum)), 'root recorded maximum/witness')
    require(len({encode(r) for r in recorded_roots}) == len(recorded_roots), 'duplicate root action')
    require(sci['root_moves_sha256'] == sha(recorded_roots) == baseline['root_moves_sha256'], 'recorded root digest binding')
    counts = dict(roots=len(roots), children=children, previews=len(roots) + children,
                  expanded_nodes=1 + expanded, enumerations=1 + expanded, leaves=len(rows))
    keys(sci['counts'], 'roots children previews expanded_nodes enumerations leaves', 'scientific counts')
    for name in counts:
        integer(sci['counts'][name], 'count ' + name, counts[name], counts[name])
    require(counts['previews'] <= 32768, 'original preview bound')
    expected_physical = counts['enumerations'] + (counts['previews'] if source_pass == 2 else 0)
    require(value['envelope']['physical_legal_moves'] == expected_physical, 'original physical count')
    key_schema(sci['best'])
    best = max(root['maximum'] for root in roots)
    tiers = [root['root'] for root in roots if root['maximum'] == best]
    require(sci['best'] == best and encode(sci['maximal_roots']) == encode(tiers), 'recorded maximal tier')
    action_schema(sci['chosen'])
    require(any(encode(sci['chosen']) == encode(tier) for tier in tiers), 'chosen action outside recorded tier')
    actual_collect = sum(action['action'] == 'collect' for action in recorded_roots)
    require(actual_collect == baseline['collect_count'] == entry['collect_count_metadata'], 'recorded root COLLECT count')
    require(len(roots) - actual_collect == baseline['place_count'] == entry['place_count_metadata'], 'recorded root PLACE count')
    require(all(encode(action) in {encode(r) for r in recorded_roots} for action in baseline['tier']), 'baseline tier not in recorded roots')
    classify(rows)
    return rows


def validate_population(manifest, snapshots, audits):
    keys(manifest, 'audit_reference_contract candidate_core_constraint canonical_source_accepted_main entries execution_prerequisite files new_seeds_or_games_allocated no_policy_search_or_game_execution observation_contract previous_worker32_exclusion schema selection selector_script selector_script_sha256 source status', 'manifest')
    require(manifest['schema'] == 'worker33-mixed-public-state-selection-preparation-v1', 'selection schema')
    integer(manifest['new_seeds_or_games_allocated'], 'new seeds', 0, 0)
    require(manifest['no_policy_search_or_game_execution'] is True, 'source preparation scope')
    entries = array(manifest['entries'], 'manifest entries')
    require(len(entries) == len(snapshots) == len(audits) == 80, 'complete 80-observation population')
    identities = set()
    seeds = set()
    card_definitions = {}
    for position, (entry, snapshot, audit) in enumerate(zip(entries, snapshots, audits), 1):
        keys(entry, 'B C action_type_class collect_count_metadata group ordinal place_count_metadata position public_observation_sha256 seed selection_key_input selection_key_sha256 snapshot_file snapshot_sha256 snapshot_size_bytes source_trace_member source_trace_sha256 stress_cost_proxy', 'manifest entry')
        integer(entry['position'], 'position', position, position)
        integer(entry['seed'], 'seed', 1000000, 1000399)
        integer(entry['ordinal'], 'ordinal', 1)
        for name in ('B', 'C', 'collect_count_metadata', 'place_count_metadata', 'snapshot_size_bytes', 'stress_cost_proxy'):
            integer(entry[name], 'entry ' + name, 1)
        for name in ('public_observation_sha256', 'selection_key_sha256', 'snapshot_sha256', 'source_trace_sha256'):
            digest_string(entry[name], 'entry ' + name)
        require(entry['action_type_class'] == 'mixed' and entry['collect_count_metadata'] + entry['place_count_metadata'] == entry['B'], 'manifest mixed root counts')
        require(entry['group'] == ('hash64' if position <= 64 else 'stress16'), 'manifest group/order')
        identity = (entry['seed'], entry['ordinal'])
        require(identity not in identities, 'duplicate observation identity')
        identities.add(identity)
        seeds.add(entry['seed'])
        snapshot_schema(snapshot)
        raw = encode(snapshot)
        require(hashlib.sha256(raw).hexdigest() == entry['public_observation_sha256'] == entry['snapshot_sha256'] and len(raw) == entry['snapshot_size_bytes'], 'snapshot full inert JSON binding')
        for card in snapshot['hand']:
            previous = card_definitions.setdefault(card['card_id'], encode(card))
            require(previous == encode(card), 'inconsistent pinned original card definition')
        keys(audit, 'legal_move_count ordinal position primary_score primary_tier primary_tier_sha256 public_observation_sha256 seed', 'audit reference')
        for name in ('position', 'seed', 'ordinal'):
            integer(audit[name], 'audit ' + name, entry[name], entry[name])
        integer(audit['legal_move_count'], 'audit root count', entry['B'], entry['B'])
        integer(audit['primary_score'], 'audit score')
        require(audit['public_observation_sha256'] == entry['public_observation_sha256'], 'audit snapshot identity')
        digest_string(audit['primary_tier_sha256'], 'audit tier digest')
        tier = array(audit['primary_tier'], 'audit tier')
        require(bool(tier), 'empty baseline tier')
        for action in tier:
            action_schema(action)
        require(sha(tier) == audit['primary_tier_sha256'], 'audit tier hash')
    require(len(seeds) == 71, 'frozen 71-source-seed population')
    return entries


def accepted_evidence(values):
    verification, pins, review = (values[n] for n in ('independent-verification.json', 'execution-pins.json', 'source-review.json'))
    for obj in (verification, pins, review):
        require(type(obj) is dict and obj.get('head') == EXECUTION_HEAD and obj.get('tree') == EXECUTION_TREE, 'accepted execution source identity')
    require(verification.get('status') == 'accepted' and verification.get('classification') == OLD_STATUS, 'accepted verification status')
    for field, fixed in (('completed_calls', 160), ('exact_scientific_matches', 80), ('fresh_seeds', 0), ('new_games', 0), ('run_id', 36961069413), ('artifact_id', 11208266885), ('job_id', 110694654983)):
        integer(verification.get(field), 'accepted verification ' + field, fixed, fixed)
    require(verification.get('strict_departures') == [], 'accepted departures')
    require(pins.get('schema') == 'worker33-offline-execution-pins-v1', 'execution pins schema')
    for field, fixed in (('run_id', 36961069413), ('run_attempt', 1), ('artifact_id', 11208266885), ('job_id', 110694654983), ('zip_size_bytes', PINS['worker33-evidence/actions-artifact.zip'][0])):
        integer(pins.get(field), 'execution pins ' + field, fixed, fixed)
    for obj in (verification, pins):
        require(obj.get('zip_sha256') == PINS['worker33-evidence/actions-artifact.zip'][1], 'accepted ZIP binding')
    require(pins.get('source_review_sha256') == PINS['worker33-evidence/source-review.json'][1], 'accepted source-review binding')
    require(review.get('schema') == 'worker33-exact-head-source-review-v1' and review.get('status') == 'approved', 'source review acceptance')
    require(type(review.get('claims')) is dict and bool(review['claims']) and all(v is True for v in review['claims'].values()), 'source review claims')


class Archive:
    def __init__(self, path):
        self.zip = zipfile.ZipFile(path, 'r')
        infos = self.zip.infolist()
        names = [info.filename for info in infos]
        require(len(names) == len(set(names)), 'duplicate ZIP member name')
        require(len(infos) == ZIP_MEMBER_COUNT and sum(i.file_size for i in infos) == ZIP_TOTAL and max((i.file_size for i in infos), default=0) == ZIP_LARGEST, 'ZIP declared expansion contract')
        for info in infos:
            name = info.filename
            require(name == PurePosixPath(name).name and name not in ('', '.', '..') and '\\' not in name and '\x00' not in name, 'unsafe ZIP member path')
            require(not info.is_dir() and not info.flag_bits & 1, 'encrypted/directory ZIP member')
            require(info.create_system == 3 and stat.S_ISREG(info.external_attr >> 16), 'unexpected ZIP member type')
            require(info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), 'unexpected ZIP compression')
            require(0 <= info.file_size <= ZIP_LARGEST and 0 <= info.compress_size <= PINS['worker33-evidence/actions-artifact.zip'][0], 'ZIP member size')
        self.infos = {i.filename: i for i in infos}
        inventory = strict_json(self._raw('inventory.json', MEMBER_PINS['inventory.json']))
        keys(inventory, 'files finalized', 'archive inventory')
        require(type(inventory['files']) is dict, 'member inventory mapping')
        self.pins = dict(MEMBER_PINS)
        require(set(inventory['files']) | {'inventory.json'} == set(names), 'complete ZIP/inventory member set')
        require({name for name in names if name.startswith('call-') and name != 'call-order.json'} == {f'call-{i:03}.json' for i in range(1, 161)}, 'all and only 160 call members')
        for name, record in inventory['files'].items():
            keys(record, 'sha256 size_bytes', 'member pin')
            integer(record['size_bytes'], 'member size', 0, ZIP_LARGEST)
            digest_string(record['sha256'], 'member hash')
            pin = (record['size_bytes'], record['sha256'])
            if name in self.pins:
                require(pin == self.pins[name], 'direct/transitive member pins disagree')
            self.pins[name] = pin
            require(self.infos[name].file_size == pin[0], 'ZIP declared/inventory size mismatch')
        self.verified = {'inventory.json'}

    def _raw(self, name, pin):
        require(name in self.infos, 'missing ZIP member: ' + name)
        with self.zip.open(name, 'r') as stream:
            raw = stream.read(pin[0] + 1)
        return pinned_bytes(raw, pin, 'ZIP ' + name)

    def raw(self, name):
        raw = self._raw(name, self.pins[name])
        self.verified.add(name)
        return raw

    def json(self, name):
        return strict_json(self.raw(name))

    def verify_remaining(self):
        # Inert provenance/log bytes are checked, never interpreted as instructions.
        for name in sorted(set(self.infos) - self.verified):
            self.raw(name)

    def close(self):
        self.zip.close()


def validate_order_and_baselines(order, baselines, entries, audits):
    require(type(order) is list and len(order) == 160, 'complete call order')
    require(type(baselines) is list and len(baselines) == 80, 'complete baselines')
    for i, recorded in enumerate(order):
        entry = entries[i % 80]
        keys(recorded, 'pass_number position seed ordinal', 'call order')
        for name, expected in (('pass_number', 1 + i // 80), ('position', entry['position']), ('seed', entry['seed']), ('ordinal', entry['ordinal'])):
            integer(recorded[name], 'call-order ' + name, expected, expected)
    for baseline, entry, audit in zip(baselines, entries, audits):
        keys(baseline, 'collect_count legal_move_count place_count root_moves_sha256 score tier', 'baseline')
        for name, expected in (('collect_count', entry['collect_count_metadata']), ('legal_move_count', entry['B']), ('place_count', entry['place_count_metadata']), ('score', audit['primary_score'])):
            integer(baseline[name], 'baseline ' + name, expected, expected)
        digest_string(baseline['root_moves_sha256'], 'baseline root digest')
        require(encode(baseline['tier']) == encode(audit['primary_tier']), 'baseline audit tier binding')


def provenance():
    return dict(protocol_sha256=PROTOCOL_SHA256, original_run_id=36961069413, original_run_attempt=1,
                original_artifact_id=11208266885, original_execution_head=EXECUTION_HEAD,
                inputs_sha256={name: pin[1] for name, pin in PINS.items()})


def scientific_summary(observations, totals):
    require(len(observations) == 80, 'incomplete observation output')
    require(all(value == EXPECTED_COUNTS for value in totals.values()), 'full per-implementation leaf accounting')
    n = sum(o['has_tradeoff'] for o in observations)
    u = sum(o['has_unmatched_exit_stratum'] for o in observations)
    status = ('recorded_component_tradeoff_present' if n else
              'recorded_component_tradeoff_absent_with_unmatched_strata' if u else 'recorded_component_tradeoff_absent')
    return dict(schema='worker33-endpoint-summary-v1', status=status, denominator=80, N=n, U=u,
                N_U_overlap=sum(o['has_tradeoff'] and o['has_unmatched_exit_stratum'] for o in observations),
                observations_without_pp=sum(o['has_no_eligible_pp'] for o in observations), completed_source_calls=160,
                matched_source_pairs=80, counts_by_source_implementation=totals,
                all_integrity_checks_passed=True, provenance=provenance())


def run_analysis(artifact, frozen, accepted, output, progress):
    raw_inputs = {}
    for relative, pin in PINS.items():
        name = relative.rsplit('/', 1)[-1]
        path = artifact if name == 'actions-artifact.zip' else ((frozen if relative.startswith('worker33-preparation/') else accepted) / name)
        raw_inputs[name] = read_pinned(path, pin, retain=name != 'actions-artifact.zip')
        progress['verified_inputs'].append(relative)
    accepted_evidence({n: strict_json(raw_inputs[n]) for n in ('independent-verification.json', 'execution-pins.json', 'source-review.json')})
    snapshots = jsonl(raw_inputs['selected-corpus.jsonl'])
    audits = jsonl(raw_inputs['audit-reference.jsonl'])
    entries = validate_population(strict_json(raw_inputs['selection-manifest.json']), snapshots, audits)
    archive = Archive(artifact)
    try:
        order = archive.json('call-order.json')
        baselines = archive.json('baseline-gates.json')
        validate_order_and_baselines(order, baselines, entries, audits)
        result = archive.json('result.json')
        keys(result, 'completed_calls scope status strict_departures', 'original result')
        integer(result['completed_calls'], 'original completed calls', 160, 160)
        require(result['status'] == OLD_STATUS and result['strict_departures'] == [], 'original result status')
        archive.verify_remaining()
        progress['verified_zip_members'] = len(archive.verified)
        totals = {name: {key: 0 for key in EXPECTED_COUNTS} for name in ('candidate', 'reference')}
        observations = []
        with (output / 'leaves.jsonl.incomplete').open('xb') as leaves_file, (output / 'observations.jsonl.incomplete').open('xb') as obs_file:
            for entry, snapshot, baseline in zip(entries, snapshots, baselines):
                paired_science = None
                paired_observation = None
                for source_pass in (1, 2):
                    call = entry['position'] + 80 * (source_pass - 1)
                    payload = archive.json(f'call-{call:03}.json')
                    rows = analyze_call(payload, snapshot, entry, baseline, source_pass)
                    science = encode(payload['scientific'])
                    observation = observation_row(entry, rows)
                    if source_pass == 1:
                        paired_science = science
                        paired_observation = observation
                    else:
                        require(science == paired_science, 'entire candidate/reference scientific mismatch')
                        require(encode(observation) == encode(paired_observation), 'derived candidate/reference observation mismatch')
                    name = 'candidate' if source_pass == 1 else 'reference'
                    totals[name]['total_leaves'] += len(rows)
                    totals[name]['horizon_leaves'] += observation['horizon_leaf_count']
                    totals[name]['carry_leaves'] += observation['carry_leaf_count']
                    for row in rows:
                        leaves_file.write(encode(row))
                    progress['completed_source_calls'] += 1
                observations.append(paired_observation)
                obs_file.write(encode(paired_observation))
                progress['matched_source_pairs'] += 1
            summary = scientific_summary(observations, totals)
            for stream in (leaves_file, obs_file):
                stream.flush()
                os.fsync(stream.fileno())
        with (output / 'summary.json.incomplete').open('xb') as stream:
            stream.write(encode(summary))
            stream.flush()
            os.fsync(stream.fileno())
        return summary
    finally:
        archive.close()


def enforce_memory_limit():
    try:
        resource.setrlimit(resource.RLIMIT_AS, (ADDRESS_SPACE_LIMIT, ADDRESS_SPACE_LIMIT))
        effective = resource.getrlimit(resource.RLIMIT_AS)
    except (OSError, ValueError) as exc:
        raise ExecutionBlocked('RLIMIT_AS enforcement unavailable') from exc
    if effective != (ADDRESS_SPACE_LIMIT, ADDRESS_SPACE_LIMIT):
        raise ExecutionBlocked('RLIMIT_AS effective values are not exactly 2 GiB')
    return list(effective)


def failure_status(exc):
    if isinstance(exc, IntegrityError):
        return 'integrity_invalid'
    if isinstance(exc, (MemoryError, TimeoutError, KeyboardInterrupt)):
        return 'resource_incomplete'
    if isinstance(exc, OSError) and exc.errno in (errno.ENOMEM, errno.ENOSPC, errno.EDQUOT, errno.EAGAIN, errno.EMFILE, errno.ENFILE):
        return 'resource_incomplete'
    if isinstance(exc, ExecutionBlocked):
        return 'execution_blocked'
    if isinstance(exc, (zipfile.BadZipFile, zipfile.LargeZipFile, EOFError)):
        return 'integrity_invalid'
    # Unknown implementation/output failures cannot establish evidence corruption.
    return 'resource_incomplete'


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', required=True, type=Path)
    parser.add_argument('--frozen', required=True, type=Path)
    parser.add_argument('--accepted-evidence', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    started = time.monotonic()
    cpu = time.process_time()
    progress = dict(verified_inputs=[], verified_zip_members=0, completed_source_calls=0, matched_source_pairs=0)
    receipt = dict(schema='worker34-parser-execution-v1', parser_id='a', source_sha256=file_hash(__file__),
                   protocol_sha256=PROTOCOL_SHA256, interpreter_version=sys.version,
                   interpreter_executable=sys.executable, platform=platform.platform(), pid=os.getpid(),
                   descendants_allowed=False, started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   rlimit_as_soft=None, rlimit_as_hard=None, completed=False, status=None,
                   established_integrity_failure=False, errors=[], progress=progress, scientific_files={})
    output = args.output_dir
    output_created = False
    try:
        try:
            output.mkdir(parents=True, exist_ok=False)
            output_created = True
        except FileExistsError as exc:
            raise ExecutionBlocked('output directory already exists; refusing to overwrite evidence') from exc
        receipt['rlimit_as_soft'], receipt['rlimit_as_hard'] = enforce_memory_limit()
        protocol_path = Path(__file__).resolve().parent.parent / 'experiments/recorded-endpoint-decomposition/PROTOCOL.md'
        try:
            protocol_hash = file_hash(protocol_path)
        except OSError as exc:
            raise ExecutionBlocked('frozen protocol unavailable') from exc
        require(protocol_hash == PROTOCOL_SHA256, 'frozen protocol SHA256 mismatch')
        receipt['first_input_read_monotonic'] = time.monotonic()
        summary = run_analysis(args.artifact, args.frozen, args.accepted_evidence, output, progress)
        for name in ('leaves.jsonl', 'observations.jsonl', 'summary.json'):
            incomplete = output / (name + '.incomplete')
            receipt['scientific_files'][name] = dict(sha256=file_hash(incomplete), size_bytes=incomplete.stat().st_size)
        # Publish only complete scientific files; preserve unfinished names on failure.
        for name in ('leaves.jsonl', 'observations.jsonl', 'summary.json'):
            (output / (name + '.incomplete')).rename(output / name)
        receipt['completed'] = True
        receipt['status'] = 'complete'
        receipt['scientific_status'] = summary['status']
        code = 0
    except BaseException as exc:
        receipt['status'] = failure_status(exc)
        receipt['established_integrity_failure'] = receipt['status'] == 'integrity_invalid'
        receipt['errors'].append(type(exc).__name__ + ': ' + str(exc)[:4096])
        code = {'integrity_invalid': 2, 'resource_incomplete': 3, 'execution_blocked': 4}[receipt['status']]
    receipt['elapsed_seconds'] = time.monotonic() - started
    receipt['cpu_seconds'] = time.process_time() - cpu
    receipt['maxrss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    receipt['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if not output_created:
        print(json.dumps(receipt, sort_keys=True), file=sys.stderr)
        return code
    try:
        with (output / 'parser-receipt.json.incomplete').open('xb') as stream:
            stream.write(encode(receipt))
            stream.flush()
            os.fsync(stream.fileno())
        (output / 'parser-receipt.json.incomplete').rename(output / 'parser-receipt.json')
        fd = os.open(output, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        print(json.dumps(dict(status='resource_incomplete', receipt_write_error=str(exc))), file=sys.stderr)
        return code if code == 2 else 3
    print(json.dumps(dict(status=receipt['status'], completed=receipt['completed'])), file=sys.stderr)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
