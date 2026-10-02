"""Frozen byte gates and exact public-history reconstruction. No search on load."""
import gzip
import hashlib
import importlib.util
from pathlib import Path
from .evidence import canonical, sha, card, observation, validate
from ..board import Board
from ..game import PlayerObservation, CollectedEquipment
from ..model import Material
from ..setup import SOLO_EASY
from ..physical_deck import load_real_deck
from ..policies import BoundedMergeV4Policy
from ..strategy import score_move_no_draw
from .evidence import move

PINS = {
 'selected-corpus.jsonl.gz': (53047,'5d51390514b529aa2a004d323e7ed0c412a74448841ee43b023fd2ccf43c7338'),
 'audit-reference.jsonl': (59325,'e5791c9dcb6d68029073f0e192fe85e0e666d462e6b3445029856aeb2d9f8d10'),
 'selection-manifest.json': (63959,'e5b672d3a97efa72abdc7f32e70a8eb50a3afb8d4813d81ddf4efd3479973410'),
 'select_public_snapshots.py': (18551,'b6d8c335296e21b29b9ee17d930d967eb677fe17dcb4bf9fc883e02951ec2873'),
}
RAW_PIN = (877584,'bb0f68bf1deac68578d21fb406c8e048ba82c39ec9c52e4bca572674ab1b7928')

class ExecutionBlocked(RuntimeError):
    pass


def checked(raw, pin):
    if (len(raw), hashlib.sha256(raw).hexdigest()) != pin:
        raise ValueError('frozen byte size/hash mismatch')
    return raw


def frozen_bytes(directory):
    result = {}
    for name, pin in PINS.items():
        try:
            with (Path(directory)/name).open('rb') as f:
                raw = f.read(pin[0]+1)
        except OSError as exc:
            raise ExecutionBlocked('input inaccessible before verification: '+name) from exc
        result[name] = checked(raw,pin)
    import io
    with gzip.GzipFile(fileobj=io.BytesIO(result['selected-corpus.jsonl.gz'])) as f:
        raw = f.read(RAW_PIN[0]+1)
    result['selected-corpus.jsonl'] = checked(raw,RAW_PIN)
    return result


def selector_module(raw):
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader('_frozen_selector',loader=None))
    exec(compile(raw,'<pinned-selector>','exec'),module.__dict__)
    return module


def load_population(directory):
    data = frozen_bytes(directory)
    parser = selector_module(data['select_public_snapshots.py'])
    manifest = parser.read_json(data['selection-manifest.json'])
    public = [parser.read_json(x) for x in data['selected-corpus.jsonl'].splitlines()]
    audit = [parser.read_json(x) for x in data['audit-reference.jsonl'].splitlines()]
    entries = manifest['entries']
    if len(public) != 80 or len(audit) != 80 or len(entries) != 80:
        raise ValueError('population size')
    identities = set()
    for i,(entry,value,ref) in enumerate(zip(entries,public,audit),1):
        parser.validate_observation(value)
        identity = (entry['seed'],entry['ordinal'])
        if identity in identities or entry['position'] != i:
            raise ValueError('population identity/order')
        identities.add(identity)
        for k in ('seed','ordinal','position','public_observation_sha256'):
            if ref[k] != entry[k]:
                raise ValueError('audit identity')
        if sha(value) != entry['public_observation_sha256']:
            raise ValueError('observation hash')
    return entries,public,audit,parser


def reconstruct(value, cards, parser):
    parser.validate_observation(value)
    def lookup(wire):
        found = cards[wire['card_id']]
        if canonical(card(found)) != canonical(wire):
            raise ValueError('card differs from accepted definition')
        return found
    board = Board()
    placements = value['board']['placements']
    if not placements or placements[0]['card_id'] != 'start_easy':
        raise ValueError('missing easy START')
    used = []
    for i,p in enumerate(placements):
        c = cards[p['card_id']]
        if i == 0:
            if p['origin'] != [0,0] or p['quarter_turns'] != 0:
                raise ValueError('START transform')
            board.seed(c)
        else:
            board.place(c,tuple(p['origin']),p['quarter_turns'])
        used.append(c.card_id)
    equipment = tuple(CollectedEquipment(lookup(e['card']),e['turn'],e['player_index'])
                      for e in value['collected_equipment'])
    turns = [e.turn for e in equipment]
    if turns != sorted(set(turns)) or any(t > value['turns'] for t in turns):
        raise ValueError('collection history turn')
    if any(e.player_index != 0 or e.material is None for e in equipment):
        raise ValueError('collection history player/material')
    hand = tuple(lookup(c) for c in value['hand'])
    used += [e.card_id for e in equipment]+[c.card_id for c in hand]
    if len(used) != len(set(used)):
        raise ValueError('duplicate physical card')
    if value['turns'] != len(placements)-1+len(equipment):
        raise ValueError('public action count')
    if value['raincoats'] != sum(e.material is Material.RAINCOAT for e in equipment) or value['ropes'] != sum(e.material is Material.ROPE for e in equipment):
        raise ValueError('equipment count/history')
    exit_placed = any(cards[p['card_id']].is_exit for p in placements)
    if value['exit_placed'] != exit_placed or ((exit_placed or any(c.is_exit for c in hand)) and not value['exit_seen']):
        raise ValueError('exit history')
    obs = PlayerObservation(board,hand,value['raincoats'],value['ropes'],value['exit_placed'],
                            value['exit_seen'],value['turns'],value['set_aside_unplayable'],equipment,SOLO_EASY,0)
    validate(obs)
    if canonical(observation(obs)) != canonical(value):
        raise ValueError('reconstructed observation mismatch')
    return obs


def accepted_cards(data_dir):
    deck = load_real_deck(data_dir)
    return {c.card_id:c for c in (*deck.ordinary_cards,deck.exit_card,deck.start_easy,deck.start_normal)}


def baseline_gate(obs, entry, audit):
    legal = obs.legal_moves()
    if not legal or len(legal) != entry['B'] or len(legal) != audit['legal_move_count'] or len(obs.board.cells) != entry['C']:
        raise ValueError('canonical B/C mismatch')
    scores = [score_move_no_draw(obs,m,BoundedMergeV4Policy(setup_weight=250).weights) for m in legal]
    best = max(scores)
    tier = [move(m) for m,s in zip(legal,scores) if s == best]
    if best != audit['primary_score'] or canonical(tier) != canonical(audit['primary_tier']) or sha(tier) != audit['primary_tier_sha256']:
        raise ValueError('unchanged V4 baseline mismatch')
    return dict(score=best,tier=tier,legal_move_count=len(legal))
