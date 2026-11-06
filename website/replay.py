"""Recalculate one recorded public position; never run games or draw cards."""
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from random import Random

ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / 'src').exists():
    ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

from bandido_alcatraz import policies
from bandido_alcatraz.catalog_support import CatalogSupportPolicy
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.strategy import move_features_no_draw, preview_move_without_draw, score_features
from bandido_alcatraz.worker32.evidence import canonical, move, observation
from bandido_alcatraz.worker32.inputs import accepted_cards, reconstruct
from scripts.run_worker26 import ImmediateTieV7Policy


class SnapshotParser:
    @staticmethod
    def validate_observation(value):
        expected = {'board', 'collected_equipment', 'exit_placed', 'exit_seen', 'hand',
                    'player_index', 'raincoats', 'ropes', 'set_aside_unplayable', 'setup', 'turns'}
        if set(value) != expected:
            raise ValueError('Unexpected fields in public snapshot')


def replay(content, example):
    if hashlib.sha256(canonical(example['original'])).hexdigest() != example['source_snapshot_sha256']:
        raise ValueError('Recorded example checksum mismatch')
    deck = load_real_deck(ROOT / 'data')
    obs = reconstruct(example['original'], accepted_cards(ROOT / 'data'), SnapshotParser)
    legal = obs.legal_moves()
    before = canonical(observation(obs))
    result = {}
    for item in content['policies']:
        name = item['code']
        parameters = {}
        source = 'src/bandido_alcatraz/policies.py'
        if name == 'ImmediateTieV7Policy':
            policy = ImmediateTieV7Policy()
            source = 'scripts/run_worker26.py'
        elif name == 'CatalogSupportPolicy':
            policy = CatalogSupportPolicy(deck.ordinary_cards, deck.exit_card)
            source = 'src/bandido_alcatraz/catalog_support.py'
        elif name == 'VisibleRepairReserveV5Policy':
            policy = policies.VisibleRepairReserveV5Policy(exit_card=deck.exit_card)
            parameters = {'exit_card': 'canonical photographed EXIT'}
        elif name == 'BoundedMergeV4Policy':
            parameters = {'setup_weight': 250}
            policy = policies.BoundedMergeV4Policy(**parameters)
        else:
            policy = getattr(policies, name)()
        chosen = policy.choose(obs, Random(0))
        assert chosen in legal, name
        assert canonical(observation(obs)) == before, name + ' mutated the input'
        successor = preview_move_without_draw(obs, chosen).successor
        weights = asdict(policy.weights) if hasattr(policy, 'weights') else None
        scores = None
        if weights:
            from bandido_alcatraz.moves import Action, Move
            scores = []
            for choice in example['choices']:
                raw = choice['move']
                m = Move(Action(raw['action']), raw['hand_index'], tuple(raw['origin']), raw['quarter_turns'])
                scores.append(score_features(move_features_no_draw(obs, m), policy.weights))
        result[item['id']] = {
            'class': name, 'parameters': parameters, 'weights': weights,
            'source': source, 'source_sha256': hashlib.sha256((ROOT / source).read_bytes()).hexdigest(),
            'ruleset': example['ruleset'], 'rng_seed': 0,
            'example': {'kind': 'recalculated-public-position', 'game_seed': example['seed'],
                        'decision': example['decision_ordinal'], 'move': move(chosen),
                        'after': observation(successor.observation()), 'open': successor.board.open_tunnels,
                        'water': successor.board.visible_water_cells, 'local_AB_scores': scores},
        }
    return result


if __name__ == '__main__':
    here = Path(__file__).resolve().parent
    example_path = here / 'inputs/player-example.json'
    if not example_path.exists():
        example_path = here / 'player-example.json'
    data = replay(json.loads((here / 'content.json').read_text(encoding='utf-8')),
                  json.loads(example_path.read_text(encoding='utf-8')))
    for id, row in data.items():
        print(id, row['example']['move'])
    print('PASS: 15 legal recalculated choices; public input unchanged; RNG=0; no hidden draws.')
