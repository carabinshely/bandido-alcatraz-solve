"""Temporary Worker25 prefix-only diagnostic; execution restricted to the CI runner.

Serialization, decomposition and labels copied from accepted Worker24 diagnostic
commit a463edfd2be52fe271642d5e8f07ddb008b48d6e. No full outcome replay.
"""
from __future__ import annotations
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
from random import Random
from statistics import mean, median
import subprocess
import time
import traceback
import zipfile
from bandido_alcatraz.game import GameState
from bandido_alcatraz.moves import Move
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import BoundedMergeV4Policy, VisibleHandTwoActionV6Policy
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.strategy import (MoveFeatures, _bounded_merge_bank,
    move_features_no_draw, preview_move_without_draw)

ROOT = Path(__file__).resolve().parents[1]
STARTING_MAIN = "6f96a1eb9e83d05917d1a88962791603542e4e8c"
SEEDS = tuple(range(1000, 1100))
FEATURE_FIELDS = tuple(MoveFeatures.__dataclass_fields__)
WATER = ("delta_visible_water", "delta_water_obstruction", "new_trapped_water")
POSITIVE = ("collect_needed", "bounded_merge_setup_gain", "delta_open_tunnels")
STATUSES = ("tier_expansion", "lookahead_override", "lookahead_tiebreak",
            "other_semantic_difference", "no_tier_divergence_before_terminal")
PREFIX = "v6_full_spent_tier_footprint_"
RECEIPT = "experiments/real-deck-policy-v6/current-model-spent-development-1000-1099-2026-09-28.json"
PROVENANCE = "experiments/real-deck-policy-v6/changed-outcome-trace-audit-2026-09-29.manifest.json"
OVERLAP_FIELDS = ("seed", "decision_index", "turn_index", "loop_iteration", "label", "state",
    "v4_max_tier", "v6_best_first_tier", "v4_max_score", "v6_max_sequence_score",
    "all_legal_first_move_scores")

class TraceIntegrityError(RuntimeError):
    pass

def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))

def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def board_cells_record(state: GameState) -> list[dict[str, object]]:
    return [
        {
            "x": x,
            "y": y,
            "tunnel_edges": sorted(edge.value for edge in cell.tunnel_edges),
            "water": cell.water,
        }
        for (x, y), cell in sorted(state.board.cells.items())
    ]

def visible_state_record(state: GameState) -> dict[str, object]:
    cells = board_cells_record(state)
    return {
        "board_fingerprint_sha256": sha256_text(canonical_json(cells)),
        "board_cells": cells,
        "visible_hand_card_ids": [card.card_id for card in state.hand],
        "raincoats": state.raincoats,
        "ropes": state.ropes,
        "exit_placed": state.exit_placed,
        "exit_seen": state.exit_seen,
        "turns": state.turns,
        "set_aside_unplayable": state.set_aside_unplayable,
        "open_tunnels": state.board.open_tunnels,
        "visible_water": state.board.visible_water_cells,
        "merge_opportunities": state.board.merge_opportunities,
        "bounded_merge_bank": _bounded_merge_bank(state.board),
        "water_obstruction": state.board.water_obstruction,
        "trapped_water": state.board.trapped_water_cells,
    }

def visible_state_digest(state: GameState) -> str:
    return sha256_text(canonical_json(visible_state_record(state)))

def rng_digest(rng: Random) -> str:
    return sha256_text(repr(rng.getstate()))

def move_record(state: GameState, move: Move) -> dict[str, object]:
    card = state.hand[move.hand_index]
    return {
        "action": move.action.value,
        "hand_index": move.hand_index,
        "card_id": card.card_id,
        "origin": list(move.origin) if move.origin is not None else None,
        "quarter_turns": move.quarter_turns,
    }

def move_key(state: GameState, move: Move) -> tuple[object, ...]:
    item = move_record(state, move)
    origin = tuple(item["origin"]) if item["origin"] is not None else None
    return (
        item["action"],
        item["hand_index"],
        item["card_id"],
        origin,
        item["quarter_turns"],
    )

def features_record(features: MoveFeatures, weights) -> dict[str, object]:
    raw = asdict(features)
    weighted = {
        field: raw[field] * getattr(weights, field)
        for field in FEATURE_FIELDS
    }
    return {
        "features": raw,
        "weighted_contributions": weighted,
        "score": sum(weighted.values()),
    }

def first_step_result_record(state: GameState) -> dict[str, object]:
    return {
        "visible_hand_card_ids": [card.card_id for card in state.hand],
        "raincoats": state.raincoats,
        "ropes": state.ropes,
        "equipment_ready": is_equipment_ready(state.raincoats, state.ropes),
        "exit_placed": state.exit_placed,
        "exit_seen": state.exit_seen,
        "open_tunnels": state.board.open_tunnels,
        "visible_water": state.board.visible_water_cells,
        "merge_opportunities": state.board.merge_opportunities,
        "bounded_merge_bank": _bounded_merge_bank(state.board),
        "water_obstruction": state.board.water_obstruction,
        "trapped_water": state.board.trapped_water_cells,
        "won": state.won,
    }

def analyze_first_move(
    state: GameState,
    move: Move,
    weights,
) -> dict[str, object]:
    immediate_features = move_features_no_draw(state, move)
    immediate = features_record(immediate_features, weights)
    preview = preview_move_without_draw(state, move)
    successor = preview.successor

    terminal_after_first = None
    if successor.won:
        terminal_after_first = "win"
    elif successor.board.open_tunnels == 0:
        terminal_after_first = "closed_tunnels_conditions_failed"

    second_rows: list[dict[str, object]] = []
    best_second_score = 0
    if terminal_after_first is None:
        for second_move in successor.legal_moves():
            second_features = move_features_no_draw(successor, second_move)
            second_feature_record = features_record(second_features, weights)
            second_rows.append(
                {
                    "move": move_record(successor, second_move),
                    "features": second_feature_record["features"],
                    "weighted_contributions": second_feature_record[
                        "weighted_contributions"
                    ],
                    "score": second_feature_record["score"],
                }
            )
        if second_rows:
            best_second_score = max(row["score"] for row in second_rows)

    best_second_moves = [
        row for row in second_rows if row["score"] == best_second_score
    ] if second_rows else []

    return {
        "move": move_record(state, move),
        "immediate_features": immediate["features"],
        "immediate_weighted_contributions": immediate["weighted_contributions"],
        "score1": immediate["score"],
        "terminal_after_first": terminal_after_first,
        "first_step_result": first_step_result_record(successor),
        "best_score2": best_second_score,
        "best_second_moves": best_second_moves,
        "sequence_score": immediate["score"] + best_second_score,
    }

def tier_rows_public(tiers: dict[str, object]) -> list[dict[str, object]]:
    return [
        {
            "move": row["move"],
            "immediate_v4_score": row["immediate_v4_score"],
            "v6_sequence_score": row["v6_sequence_score"],
            "second_step_component": row["second_step_component"],
        }
        for row in tiers["rows"]
    ]

def tier_move_records(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [row["move"] for row in rows]

def tier_keys(rows: list[dict[str, object]]) -> tuple[tuple[object, ...], ...]:
    return tuple(row["key"] for row in rows)

def tier_label(tiers: dict[str, object]) -> str:
    v4 = set(tier_keys(tiers["v4_tier_rows"]))
    v6 = set(tier_keys(tiers["v6_tier_rows"]))
    if v4 == v6:
        raise TraceIntegrityError("tier_label called for equal tiers")

    outside = v6 - v4
    retained = v6 & v4

    if outside and retained:
        return "tier_expansion"

    if not outside and v6:
        return "lookahead_tiebreak"

    if outside and not retained:
        row_map = {row["key"]: row for row in tiers["rows"]}
        if all(
            row_map[key]["immediate_v4_score"] < tiers["v4_max"]
            and row_map[key]["v6_sequence_score"] == tiers["v6_max"]
            for key in outside
        ):
            return "lookahead_override"

    return "other_semantic_difference"

def pre_choice_terminal_reason(state: GameState) -> str | None:
    if state.won:
        return "win"
    if state.board.open_tunnels == 0:
        return "closed_tunnels_conditions_failed"
    if not state.hand and not state.draw_pile:
        return "deck_exhausted"
    return None

class SelectedStateConfounded(RuntimeError):
    pass


def visible_only(state):
    """Diagnostics receive no future cards, even as an unused object attribute."""
    return GameState(board=state.board.clone(), draw_pile=[], hand=list(state.hand),
                     raincoats=state.raincoats, ropes=state.ropes,
                     exit_placed=state.exit_placed, exit_seen=state.exit_seen,
                     turns=state.turns, set_aside_unplayable=state.set_aside_unplayable)


def deterministic_tiers(state, weights):
    rows = []
    for move in state.legal_moves():
        analysis = analyze_first_move(state, move, weights)
        rows.append(dict(move_object=move, move=analysis['move'], key=move_key(state, move),
                         immediate_v4_score=analysis['score1'],
                         v6_sequence_score=analysis['sequence_score'],
                         second_step_component=analysis['best_score2'], decomposition=analysis))
    if not rows:
        raise TraceIntegrityError('tier analysis requires legal moves')
    v4_max = max(row['immediate_v4_score'] for row in rows)
    v6_max = max(row['v6_sequence_score'] for row in rows)
    return dict(rows=rows, v4_max=v4_max, v6_max=v6_max,
                v4_tier_rows=[r for r in rows if r['immediate_v4_score'] == v4_max],
                v6_tier_rows=[r for r in rows if r['v6_sequence_score'] == v6_max])


def contributions(event):
    options = [second for first in event['all_first_move_decompositions']
               if 'v6_preferred' in first['roles'] for second in first['best_second_moves']]
    result = {'option_count': len(options), 'features': {}, 'presence': {}}
    for field in FEATURE_FIELDS:
        raw = [o['features'][field] for o in options]
        weighted = [o['weighted_contributions'][field] for o in options]
        result['features'][field] = {
            'raw_positive': sum(v > 0 for v in raw),
            'raw_negative': sum(v < 0 for v in raw),
            'raw_nonzero': sum(v != 0 for v in raw), 'raw_total': sum(raw),
            'weighted_positive': sum(v > 0 for v in weighted),
            'weighted_negative': sum(v < 0 for v in weighted),
            'weighted_nonzero': sum(v != 0 for v in weighted), 'weighted_total': sum(weighted)}
        result['presence'][field] = {
            'raw_positive': any(v > 0 for v in raw), 'raw_nonzero': any(v != 0 for v in raw),
            'weighted_positive': any(v > 0 for v in weighted),
            'weighted_nonzero': any(v != 0 for v in weighted)}
    return result


def event_record(seed, decision, iteration, state, tiers):
    v4 = set(tier_keys(tiers['v4_tier_rows']))
    v6 = set(tier_keys(tiers['v6_tier_rows']))
    decompositions = []
    for row in tiers['rows']:
        analysis = row['decomposition']
        analysis['roles'] = (["v4_max"] if row['key'] in v4 else []) + (
            ["v6_preferred"] if row['key'] in v6 else [])
        decompositions.append(analysis)
    event = dict(seed=seed, decision_index=decision, loop_iteration=iteration,
                 turn_index=state.turns, state=visible_state_record(state),
                 visible_state_sha256=visible_state_digest(state),
                 v4_max_score=tiers['v4_max'], v6_max_sequence_score=tiers['v6_max'],
                 v4_max_tier=tier_move_records(tiers['v4_tier_rows']),
                 v6_best_first_tier=tier_move_records(tiers['v6_tier_rows']),
                 all_legal_first_move_scores=tier_rows_public(tiers), label=tier_label(tiers),
                 all_first_move_decompositions=decompositions,
                 v6_outside_v4=bool(v6-v4), v6_retains_v4=bool(v6 & v4))
    event['action_types'] = {
        'v4': dict(sorted(Counter(m['action'] for m in event['v4_max_tier']).items())),
        'v6': dict(sorted(Counter(m['action'] for m in event['v6_best_first_tier']).items()))}
    event['contributions'] = contributions(event)
    return event


def require_shared(a, b, ra, rb):
    # Compare hidden piles for identity only; never expose them to diagnostics or logs.
    if (visible_state_record(a) != visible_state_record(b)
            or a.draw_pile != b.draw_pile or ra.getstate() != rb.getstate()):
        raise SelectedStateConfounded('shared state or RNG equality failed')


def trace_seed(seed):
    if seed not in SEEDS:
        raise TraceIntegrityError('seed outside preregistered scope')
    deck = load_real_deck(ROOT / 'data')
    policies = [BoundedMergeV4Policy(setup_weight=250), VisibleHandTwoActionV6Policy()]
    rngs = [Random(seed), Random(seed)]
    states = [GameState.new(start_card=deck.start_easy, deck=deck.draw_deck(),
                           hand_size=3, rng=rng) for rng in rngs]
    prefix = []
    decision = 0
    try:
        for iteration in range(1000):
            a, b = states
            ra, rb = rngs
            require_shared(a, b, ra, rb)
            terminal = pre_choice_terminal_reason(a)
            if terminal is not None:
                return dict(seed=seed, status=STATUSES[-1], first_tier_divergence=None,
                            shared_prefix=prefix, terminal_reason=terminal,
                            terminal_state=visible_state_record(a))
            if not a.legal_moves():
                before = visible_state_digest(a)
                refreshed = [s.refresh_unplayable_hand() for s in states]
                if refreshed[0] != refreshed[1]:
                    raise SelectedStateConfounded('refresh mismatch')
                require_shared(a, b, ra, rb)
                prefix.append(dict(loop_iteration=iteration, refresh=refreshed[0],
                                   state_before=before, state_after=visible_state_digest(a)))
                if not refreshed[0]:
                    return dict(seed=seed, status=STATUSES[-1], first_tier_divergence=None,
                                shared_prefix=prefix, terminal_reason=(
                                    'deck_exhausted' if a.exhausted else 'no_legal_move'),
                                terminal_state=visible_state_record(a))
                continue
            before_rng = [rng_digest(r) for r in rngs]
            before_state = visible_state_digest(a)
            tiers = deterministic_tiers(visible_only(a), policies[0].weights)
            if before_rng != [rng_digest(r) for r in rngs] or before_state != visible_state_digest(a):
                raise TraceIntegrityError('diagnostic mutation or RNG consumption')
            if tier_keys(tiers['v4_tier_rows']) != tier_keys(tiers['v6_tier_rows']):
                event = event_record(seed, decision, iteration, visible_only(a), tiers)
                return dict(seed=seed, status=event['label'], first_tier_divergence=event,
                            shared_prefix=prefix)
            # Only the actual frozen policies consume seeded RNG, and only while tiers match.
            moves = [p.choose(s, r) for p, s, r in zip(policies, states, rngs)]
            if moves[0] != moves[1] or moves[0] not in [r['move_object'] for r in tiers['v4_tier_rows']]:
                raise SelectedStateConfounded('actual selected move mismatch with equal tiers')
            if ra.getstate() != rb.getstate():
                raise SelectedStateConfounded('actual choice RNG mismatch')
            selected = move_record(a, moves[0])
            for s, m in zip(states, moves):
                s.apply(m)
            require_shared(a, b, ra, rb)
            prefix.append(dict(loop_iteration=iteration, decision_index=decision,
                               move=selected, state_before=before_state,
                               state_after=visible_state_digest(a),
                               ordered_common_tier=tier_move_records(tiers['v4_tier_rows']),
                               rng_before=before_rng[0], rng_after=rng_digest(ra)))
            decision += 1
        raise TraceIntegrityError('shared prefix step limit reached; evidence incomplete')
    except SelectedStateConfounded as exc:
        return dict(seed=seed, status=None, first_tier_divergence=None,
                    shared_prefix=prefix, confounded=str(exc))


def safe_trace(seed):
    try:
        return trace_seed(seed)
    except Exception:
        return dict(seed=seed, status=None, first_tier_divergence=None,
                    error=traceback.format_exc())


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def check_bytes(data, size, digest, label):
    actual = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    if actual != {'bytes': size, 'sha256': digest}:
        raise TraceIntegrityError(f'{label}: byte length or SHA256 mismatch: {actual}')
    return actual


def preflight(archive):
    provenance = json.loads((ROOT / PROVENANCE).read_text())
    baseline_bytes = archive.read_bytes()
    meta = provenance['raw_artifact']
    verified = {'archive': check_bytes(baseline_bytes, meta['archive_bytes'],
                                      meta['archive_sha256'], 'Worker24 ZIP')}
    with zipfile.ZipFile(archive) as z:
        if sorted(z.namelist()) != sorted(meta['inner_files']):
            raise TraceIntegrityError('unexpected Worker24 archive entries')
        inner = {}
        for name, expected in meta['inner_files'].items():
            data = z.read(name)
            verified[name] = check_bytes(data, expected['bytes'], expected['sha256'], name)
            inner[name] = json.loads(data)
    baseline = inner['worker24-changed-outcome-trace-audit.json']
    if baseline['evaluated_commit'] != 'a463edfd2be52fe271642d5e8f07ddb008b48d6e':
        raise TraceIntegrityError('Worker24 diagnostic commit mismatch')
    # Pin all production/data files, not just the subset listed in Worker24.
    source_blobs = {}
    paths = git('ls-tree', '-r', '--name-only', STARTING_MAIN, 'src', 'data').splitlines()
    paths += [RECEIPT, PROVENANCE]
    for path in paths:
        expected = git('rev-parse', f'{STARTING_MAIN}:{path}')
        actual = git('hash-object', path)
        if actual != expected:
            raise TraceIntegrityError(f'source drift: {path}')
        source_blobs[path] = actual
    for path, expected in provenance['source_blobs'].items():
        if source_blobs[path] != expected:
            raise TraceIntegrityError(f'Worker24 provenance drift: {path}')
    receipt = json.loads((ROOT / RECEIPT).read_text())
    v4, v6 = [{r['seed']: ('win' if r['won'] else r['reason'])
               for r in receipt[key]} for key in ('v4_per_seed', 'v6_per_seed')]
    if any(sorted(d) != list(SEEDS) for d in (v4, v6)) or any(
            len(receipt[key]) != 100 for key in ('v4_per_seed', 'v6_per_seed')):
        raise TraceIntegrityError('Worker23 population mismatch')
    strata = {
        'all100': list(SEEDS),
        'changed32': [s for s in SEEDS if v4[s] != v6[s]],
        'unchanged68': [s for s in SEEDS if v4[s] == v6[s]],
        'both_win3': [s for s in SEEDS if v4[s] == v6[s] == 'win'],
        'same_deck_exhausted61': [s for s in SEEDS if v4[s] == v6[s] == 'deck_exhausted'],
        'same_no_legal_move4': [s for s in SEEDS if v4[s] == v6[s] == 'no_legal_move'],
        'v4_only_win2': [s for s in SEEDS if v4[s] == 'win' and v6[s] != 'win'],
        'v6_only_win2': [s for s in SEEDS if v6[s] == 'win' and v4[s] != 'win']}
    if [len(v) for v in strata.values()] != [100,32,68,3,61,4,2,2]:
        raise TraceIntegrityError('fixed stratum sizes mismatch')
    exact = {'changed32': provenance['seed_scope'], 'both_win3': [1008,1056,1097],
             'same_no_legal_move4': [1017,1060,1094,1095],
             'v4_only_win2': [1012,1087], 'v6_only_win2': [1024,1083]}
    if any(strata[k] != v for k,v in exact.items()):
        raise TraceIntegrityError('fixed stratum membership mismatch')
    if sorted(t['seed'] for t in baseline['traces']) != strata['changed32']:
        raise TraceIntegrityError('Worker24 population mismatch')
    return baseline, strata, dict(verified_worker24_bytes=verified,
                                  source_blobs=source_blobs, source_gate_passed=True)


def overlap_gate(traces, baseline):
    current = {t['seed']: t for t in traces}
    checks = []
    for old in baseline['traces']:
        actual = current[old['seed']].get('first_tier_divergence')
        expected = old['first_tier_divergence']
        fields = {key: actual is not None and actual[key] == expected[key]
                  for key in OVERLAP_FIELDS}
        # Also compare every accepted target's full decomposition, ignoring only role labels.
        expected_parts = expected['target_decompositions']
        actual_parts = {canonical_json(p['move']): p for p in actual['all_first_move_decompositions']} if actual else {}
        fields['accepted_target_decompositions'] = all(
            canonical_json(p['move']) in actual_parts and
            {k:v for k,v in p.items() if k != 'roles'} ==
            {k:v for k,v in actual_parts[canonical_json(p['move'])].items() if k != 'roles'}
            for p in expected_parts)
        fields['accepted_label_tier_expansion'] = actual is not None and actual['label'] == expected['label'] == 'tier_expansion'
        checks.append(dict(seed=old['seed'], fields=fields, passed=all(fields.values())))
    return dict(required=32, exact_matches=sum(c['passed'] for c in checks), checks=checks,
                passed=len(checks) == 32 and all(c['passed'] for c in checks))


def distribution(values):
    return dict(count=len(values), histogram=dict(sorted(Counter(values).items())),
                min=min(values) if values else None, max=max(values) if values else None,
                mean=mean(values) if values else None, median=median(values) if values else None)


def summarize(traces, seeds):
    rows = [t for t in traces if t['seed'] in seeds]
    events = [t['first_tier_divergence'] for t in rows if t['first_tier_divergence']]
    features = {}
    for field in FEATURE_FIELDS:
        features[field] = {
            'option_occurrences_and_totals': dict(Counter({k: 0 for k in (
                'raw_positive','raw_negative','raw_nonzero','raw_total',
                'weighted_positive','weighted_negative','weighted_nonzero','weighted_total')})),
            'seed_presence': {k: 0 for k in ('raw_positive','raw_nonzero','weighted_positive','weighted_nonzero')}}
        for e in events:
            for k,v in e['contributions']['features'][field].items():
                features[field]['option_occurrences_and_totals'][k] += v
            for k,v in e['contributions']['presence'][field].items():
                features[field]['seed_presence'][k] += int(v)
    type_sets = Counter()
    unambiguous = Counter()
    for e in events:
        a,b = [tuple(e['action_types'][p]) for p in ('v4','v6')]
        type_sets[canonical_json({'v4':a,'v6':b})] += 1
        if len(a) == len(b) == 1:
            unambiguous[a[0]+'->'+b[0]] += 1
    expansions = sum(t['status'] == 'tier_expansion' for t in rows)
    return dict(seeds=seeds, seed_denominator=len(seeds), complete_status_count=sum(t['status'] in STATUSES for t in rows),
                divergence_denominator=len(events),
                status_counts={s:sum(t['status']==s for t in rows) for s in STATUSES},
                tier_expansion=dict(count=expansions, denominator=len(seeds), fraction=expansions/len(seeds)),
                divergence_turns=distribution([e['turn_index'] for e in events]),
                tier_cardinalities={p:distribution([len(e[key]) for e in events]) for p,key in (
                    ('v4','v4_max_tier'),('v6','v6_best_first_tier'))},
                action_type_set_pairs=dict(type_sets), unambiguous_action_type_pairs=dict(unambiguous),
                ambiguous_action_type_pair_count=len(events)-sum(unambiguous.values()),
                best_second_option_denominator=sum(e['contributions']['option_count'] for e in events),
                features=features,
                any_nonzero_direct_water_weighted_seeds=sum(any(e['contributions']['presence'][f]['weighted_nonzero'] for f in WATER) for e in events),
                any_nonzero_direct_water_raw_seeds=sum(any(e['contributions']['presence'][f]['raw_nonzero'] for f in WATER) for e in events))


def answers(traces, summaries):
    # Fixed mechanical Boolean signature, declared in code before execution.
    # No feature/threshold search, candidate rule, or grouping by results.
    def signature(t):
        e = t['first_tier_divergence']
        if e is None:
            return dict(status=t['status'])
        return dict(status=t['status'], outside=e['v6_outside_v4'], retains=e['v6_retains_v4'],
                    raw_positive={f:e['contributions']['presence'][f]['raw_positive'] for f in POSITIVE},
                    direct_water_nonzero={f:e['contributions']['presence'][f]['weighted_nonzero'] for f in WATER})
    by_seed = {t['seed']:t for t in traces}
    gain = [signature(by_seed[s]) for s in (1024,1083)]
    loss = [signature(by_seed[s]) for s in (1012,1087)]
    common = gain[0] if gain[0] == gain[1] else None
    control_matches = [s for s in summaries['unchanged68']['seeds']
                       if common is not None and signature(by_seed[s]) == common]
    comparison = dict(signature_definition='status, outside/retained flags, three raw-positive contribution booleans, three weighted-nonzero water booleans; fixed before execution',
                      gain_signatures=gain, loss_signatures=loss,
                      common_gain_signature=common,
                      absent_from_both_losses=common is not None and all(common != v for v in loss),
                      unchanged_control_matches=control_matches, unchanged_control_denominator=68,
                      interpretation='Descriptive diagnosis only. Control representation does not establish sufficient evidence against coincidence or population performance. No candidate rule.')
    return {
        '1_expansion_in_unchanged_and_changed': {k:summaries[k]['tier_expansion'] for k in ('changed32','unchanged68')},
        '2_expansion_in_preserved_wins': summaries['both_win3']['tier_expansion'],
        '3_contribution_specificity': {k:{f:summaries[k]['features'][f]['seed_presence'] for f in POSITIVE[:2]} | {'seed_denominator':summaries[k]['seed_denominator']} for k in ('changed32','unchanged68')},
        '4_water_outside_changed': {k:{'seed_denominator':summaries[k]['seed_denominator'], 'nonzero_weighted_seeds':summaries[k]['any_nonzero_direct_water_weighted_seeds'], 'nonzero_raw_seeds':summaries[k]['any_nonzero_direct_water_raw_seeds']} for k in ('changed32','unchanged68')},
        '5_fixed_mechanical_gain_loss_signature': comparison}


def write_json(path, data):
    path.write_text(json.dumps(data, sort_keys=True, indent=2)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker24-zip', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'artifacts/raw/worker25')
    parser.add_argument('--preflight-only', action='store_true', help='Verify bytes, sources and fixed strata; execute no seeds')
    args = parser.parse_args()
    baseline, strata, integrity = preflight(args.worker24_zip)
    if args.preflight_only:
        print(json.dumps(dict(preflight=integrity, strata=strata, research_seeds_executed=0), sort_keys=True))
        return
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('RUNNER_NAME') != 'bandido-alcatraz-ci':
        parser.error('research execution requires existing GitHub Actions runner bandido-alcatraz-ci')
    head = git('rev-parse','HEAD')
    if head != os.environ.get('EVALUATED_COMMIT'):
        raise TraceIntegrityError('checkout SHA mismatch')
    if git('status','--porcelain','--untracked-files=no'):
        raise TraceIntegrityError('tracked working tree is dirty')
    start = time.monotonic()
    with ProcessPoolExecutor(max_workers=4) as executor:
        traces = list(executor.map(safe_trace, SEEDS, chunksize=1))
    overlap = overlap_gate(traces, baseline)
    population_ok = [t['seed'] for t in traces] == list(SEEDS)
    errors = [t for t in traces if t.get('error')]
    confounded = [t['seed'] for t in traces if t.get('confounded')]
    complete = all(t['status'] in STATUSES for t in traces)
    classification = PREFIX+'diagnostic_invalid'
    if population_ok and not errors and overlap['passed']:
        if confounded:
            classification = PREFIX+'rng_or_state_confounded'
        elif complete:
            classification = PREFIX+'resolved'
    summaries = {k:summarize(traces,seeds) for k,seeds in strata.items()}
    output = dict(schema='bandido-worker25-full-spent-tier-footprint', schema_version=1,
                  starting_main=STARTING_MAIN, evaluated_commit=head,
                  preregistration_url='https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5908064472',
                  classification=classification, seed_scope=list(SEEDS), complete_status_count=sum(t['status'] in STATUSES for t in traces),
                  source_integrity=integrity, overlap=overlap, confounded_seeds=confounded,
                  fixed_configuration=dict(policies=['BoundedMergeV4Policy(setup_weight=250)','VisibleHandTwoActionV6Policy()'], hand_size=3, start='easy', ordering='canonical', workers=4),
                  execution=dict(runner=os.environ['RUNNER_NAME'], run_id=os.environ.get('GITHUB_RUN_ID'),
                                 run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'), job=os.environ.get('GITHUB_JOB'),
                                 checkout_tree=git('rev-parse','HEAD^{tree}'), runtime_seconds=time.monotonic()-start),
                  interpretation_limits=['already-spent development data only','strata overlap','prefix-only; no new outcome measurement','no policy-performance support classification','no candidate rule'],
                  contribution_definition='Every tied-best second option under every V6-best first move; count each first/second pair, no tie priority; raw and weighted signs separate. No-divergence seeds have no first-divergence observation.',
                  hidden_future_draw_diagnostic_input=False, strata=summaries, traces=traces)
    output['answers'] = answers(traces,summaries) if complete else {'unavailable':'incomplete statuses'}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw = args.output_dir/'worker25-full-spent-tier-footprint.json'
    summary = args.output_dir/'worker25-full-spent-tier-footprint-summary.json'
    write_json(raw,output)
    compact = {k:v for k,v in output.items() if k != 'traces'}
    compact['per_seed'] = [{k:v for k,v in t.items() if k != 'shared_prefix' and k != 'first_tier_divergence'} | {
        'first_divergence': ({k:e[k] for k in ('decision_index','turn_index','label','visible_state_sha256','action_types','v6_outside_v4','v6_retains_v4','contributions')} if (e:=t['first_tier_divergence']) else None)} for t in traces]
    write_json(summary,compact)
    archive = args.output_dir/'worker25-full-spent-tier-footprint-2026-09-30.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for path in (raw,summary):
            z.write(path,path.name)
    inventory = {p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in (raw,summary,archive)}
    write_json(args.output_dir/'inventory.json',inventory)
    print(json.dumps(dict(classification=classification,complete_status_count=output['complete_status_count'],overlap_matches=overlap['exact_matches'],inventory=inventory),sort_keys=True))
    if classification != PREFIX+'resolved':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
