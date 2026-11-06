"""Verify a single public decision for each frozen experimental policy; no draws."""
import hashlib
import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path
from random import Random

from replay import ROOT, SnapshotParser
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.strategy import preview_move_without_draw, move_features, score_features
from bandido_alcatraz.worker32.evidence import canonical, move, observation
from bandido_alcatraz.worker32.inputs import accepted_cards, reconstruct

HERE = Path(__file__).resolve().parent


def load_policy(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def replay_recent():
    inputs = HERE / 'inputs' if (HERE / 'inputs').exists() else HERE
    studies = json.loads((inputs / 'recent-research.json').read_text(encoding='utf-8'))['studies']
    snapshots = json.loads((inputs / 'recent-examples.json').read_text(encoding='utf-8'))
    code = inputs / 'research-code'
    baseline_path = code / 'local92_catalog_baseline.py.txt'
    baseline_hash = hashlib.sha256(baseline_path.read_bytes()).hexdigest()
    if any(s['control_policy_sha256'] != baseline_hash for s in studies):
        raise ValueError('Frozen baseline checksum mismatch')
    baseline_module = load_policy('local92_catalog_baseline', baseline_path)
    deck = load_real_deck(ROOT / 'data')
    result = {}
    for study in studies:
        number = study['number']
        snapshot = snapshots[str(number)]
        if hashlib.sha256(canonical(snapshot['original'])).hexdigest() != snapshot['source_snapshot_sha256']:
            raise ValueError('Public example checksum mismatch')
        source = code / study['code_file']
        if hashlib.sha256(source.read_bytes()).hexdigest() != study['policy_sha256']:
            raise ValueError('Frozen policy checksum mismatch')
        module = load_policy('guide_policy_' + str(number), source)
        policy = getattr(module, study['class_name'])(deck.ordinary_cards, deck.exit_card)
        for key, value in snapshot['state_before'].items():
            if getattr(policy, key) != value:
                raise ValueError('Unexpected policy entry state')
        obs = reconstruct(snapshot['original'], accepted_cards(ROOT / 'data'), SnapshotParser)
        before = canonical(observation(obs))
        chosen = policy.choose(obs, Random(0))
        baseline = baseline_module.CatalogSupportPolicy(deck.ordinary_cards, deck.exit_card)
        anchor = baseline.choose(obs, Random(0))
        assert chosen in obs.legal_moves() and anchor in obs.legal_moves()
        assert before == canonical(observation(obs))
        after = preview_move_without_draw(obs, chosen).successor
        other = preview_move_without_draw(obs, anchor).successor
        if number == 110:
            active = bool(policy.completed_comparisons and policy.planning_evidence.get('selected_exit'))
            diagnostics = policy.planning_evidence
        elif number == 113:
            active = obs.exit_placed and is_equipment_ready(obs.raincoats, obs.ropes)
            diagnostics = dict(branch='post-exit-closure')
        else:
            active = policy.last['status'] == 'EVALUATED'
            diagnostics = policy.last
            if number == 129:
                diagnostics['relaxed_anchor_certificate'] = sys.modules['guide_policy_127'].graph_certificate(other.board)
        assert active, f'Example does not demonstrate branch {number}'
        result[str(number)] = dict(
            number=number, adopted=False, policy_sha256=study['policy_sha256'],
            **{'class': study['class_name']}, rng_seed=0, state_before=snapshot['state_before'],
            provenance={k:v for k,v in snapshot.items() if k != 'original'},
            example=dict(kind='recalculated-public-position', game_seed=snapshot['game_seed'],
                decision=snapshot['decision'], original=snapshot['original'], move=move(chosen),
                baseline_move=move(anchor), after=observation(after.observation()),
                baseline_after=observation(other.observation()), open=after.board.open_tunnels,
                water=after.board.visible_water_cells, baseline_open=other.board.open_tunnels,
                baseline_water=other.board.visible_water_cells, input_unchanged=True, legal=True,
                branch_active=active, differs_from_catalog=chosen != anchor,
                v4_score=score_features(move_features(obs, chosen), policy.weights),
                baseline_v4_score=score_features(move_features(obs, anchor), policy.weights),
                diagnostics=diagnostics))
    return result


if __name__ == '__main__':
    rows = replay_recent()
    for number, row in rows.items():
        print(number, row['example']['move'], 'catalog:', row['example']['baseline_move'])
    print('PASS: four legal active-branch public decisions; input unchanged; RNG=0; no draws.')
