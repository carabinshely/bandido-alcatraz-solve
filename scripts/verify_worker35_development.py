"""Independent, read-only Worker35 raw-evidence gate.

No engine, candidate, reference, producer, games, policy calls, Git or network.
The external freeze digest and authenticated Actions metadata are trust inputs,
not claims authenticated by the artifact itself. A partial/failed/rejected run
never receives a negative scientific classification. Reviewed Worker31 physical
geometry and exposed-transition checks are reused by exact byte hash.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import math
from pathlib import Path
import re
import sys
import zipfile

WORKER31_SHA256 = 'fd5d9efdf1a3b2bb1df2c77058758655049753735a93808e27b9e70c5f6664ab'


def load_reviewed():
    path = Path(__file__).with_name('verify_worker31_development.py')
    if path.stat().st_size > 128 * 1024:
        raise ValueError('reviewed dependency exceeds byte bound')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != WORKER31_SHA256:
        raise ValueError('reviewed Worker31 dependency changed')
    spec = importlib.util.spec_from_loader('_worker35_reviewed_trace', loader=None)
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


v31 = load_reviewed()
g = v31.g
Rejected, require, same, keys, integer = g.Rejected, g.require, g.same, g.keys, g.integer
canonical, strict_json = g.canonical, g.strict_json
SEEDS = range(1000000, 1000400)
PASSES = (1, 2, 3)
SETUP, RULESET, SETUP_ID = g.SETUP, g.RULESET, g.SETUP_ID
REPOSITORY = 'carabinshely/bandido-alcatraz-solve'
ACCEPTED_MAIN = '87ddc894668ec60e7a8419e65308cadb0ced6ed9'
ACCEPTED_TREE = '3e0c450ed82ecd47fdd1e239da47d97567d584a6'
MODEL_COMPARATOR = 'c50a7ab8e73eaf3c497c5d1c9fef5cbe53261853'
SOURCE_MAP_SHA256 = '27b4a000202d5e22b3e37ea128571cd7a5b8a4ef1a882514616c361cf2da0aed'
CONTROL_ARRAY_SHA256 = 'a4d2d06e5592caa35c03d00337d0254c07f767d5cb8ee0777cbb51f543803021'
BASELINE_ARCHIVE_SHA256 = '48e6af6595a737be332467b436aca94744b19c4b3d96d25d5dbbfe654d98a4b2'
CONTROL_WINS, CONTROL_EQUIPMENT_READY = 45, 396
MIN_NET_WINS = 8
CLASSIFICATION = 'quota_reserve_closure_development_no_advancement'
ADVANCED_CLASSIFICATION = 'quota_reserve_closure_development_advanced'
MAX_STEPS = 1000
MATERIALS = {'raincoat': (3, 12, 'raincoats'), 'rope': (2, 8, 'ropes')}
FLAGS = ('reserve_filter_active', 'reserve_primary_tier_changed', 'closure_branch_selected',
         'true_original_all_collect_crossover', 'reserve_filter_mediated_change')
COST_KEYS = 'legal_enumerations previews exit_geometry_checks roots'
SCIENCE_KEYS = 'schema input_before input_after roots supply tiers guards flags chosen_index chosen rng_before rng_after'
MAX_METADATA = 8 * 1024**2
MAX_LINE = 64 * 1024**2


def digest(value):
    return hashlib.sha256(canonical(value, newline=True)).hexdigest()


def valid_hash(value, label, length=64):
    require(type(value) is str and re.fullmatch('[0-9a-f]{%d}' % length, value) is not None,
            label + ': hash')


def read_json(path, limit=MAX_METADATA):
    require(not path.is_symlink() and path.is_file(), 'nonregular JSON input')
    require(path.stat().st_size <= limit, 'JSON exceeds byte bound')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, 'JSON exceeds byte bound')
    return strict_json(raw)


def board_metrics(cells):
    """Arithmetic over persisted exposed cells; no engine or search."""
    visible = g.validate_cells(cells)
    opens = obstruction = trapped = 0
    for (x, y), cell in visible.items():
        neighbors = [(x + dx, y + dy) in visible for dx, dy in g.DELTAS.values()]
        opens += sum(edge in cell['tunnel_edges'] and (x + dx, y + dy) not in visible
                     for edge, (dx, dy) in g.DELTAS.items())
        if cell['water']:
            obstruction += sum(neighbors)
            trapped += all(neighbors)
    return [opens, sum(c['water'] for c in visible.values()), obstruction, trapped]


def validate_public(observation, seed, cards):
    record = v31.public_record(observation, seed, cards)
    require(record['result']['open_tunnels'] > 0 and not record['result']['won'],
            'terminal observation is not a policy input')
    aside = observation['set_aside_unplayable']
    require(type(aside) is int and aside in (0, 6), 'canonical public set-aside count')
    remaining = 69 - observation['turns'] - aside
    require(remaining > 0, 'exhausted live observation')
    same(len(observation['hand']), min(6, remaining), 'exact live hand conservation')
    if aside:
        same(remaining, len(observation['hand']), 'short-pile refresh stock conservation')
    return record


def supply_for(observation, cards):
    placed = Counter(cards[p['card_id']]['material'] for p in observation['board']['placements'])
    hand = Counter(c['material'] for c in observation['hand'])
    supply = {}
    for material, (quota, total, counter) in MATERIALS.items():
        collected = observation[counter]
        available = total - collected - placed[material]
        require(available >= hand[material] >= 0, 'supply smaller than public own hand')
        if quota > collected and observation['set_aside_unplayable']:
            same(available, hand[material], 'still-needed short-pile supply invariant')
        supply[material] = {'quota': quota, 'collected': collected, 'total': total,
                            'placed': placed[material], 'deficit': quota - collected,
                            'available': available, 'own_hand': hand[material]}
    remaining = 69 - observation['turns'] - observation['set_aside_unplayable']
    require(sum(item['available'] for item in supply.values() if item['deficit'] > 0) <= remaining,
            'combined needed stock exceeds unconsumed inventory')
    return supply


def validate_roots(roots, observation, cards, record):
    require(type(roots) is list, 'roots list')
    require(len(roots) <= 1000000, 'root safety bound')
    identifiers, ordering = set(), []
    for root in roots:
        keys(root, 'move score', 'root')
        move = root['move']
        require(move is not None, 'null root')
        v31.move_schema(move, observation['hand'])
        require(type(root['score']) is int, 'integer canonical score')
        identity = canonical(move)
        require(identity not in identifiers, 'duplicate legal root')
        identifiers.add(identity)
        card = observation['hand'][move['hand_index']]
        if move['action'] == 'collect':
            quota, unused, counter = MATERIALS[card['material']]
            require(observation[counter] < quota, 'COLLECT after quota')
            key = (move['hand_index'], 0, 0, (0, 0))
        else:
            # Independent physical legality of every persisted root. Completeness
            # and exact scoring are attested by independently authored runner
            # reference output, never by a hidden local policy invocation.
            v31.post_choice(record, move, observation['hand'], cards)
            key = (move['hand_index'], 1, move['quarter_turns'], tuple(move['origin']))
        ordering.append(key)
    require(ordering == sorted(ordering), 'canonical relative root order')
    # COLLECT completeness can be established without any geometry enumeration.
    collect = {r['move']['hand_index'] for r in roots if r['move']['action'] == 'collect'}
    expected = {i for i, c in enumerate(observation['hand']) if c['material'] in MATERIALS
                and observation[MATERIALS[c['material']][2]] < MATERIALS[c['material']][0]}
    same(sorted(collect), sorted(expected), 'missing/extra legal COLLECT root')


def maximizers(indices, roots):
    if not indices:
        return []
    best = max(roots[i]['score'] for i in indices)
    return [i for i in indices if roots[i]['score'] == best]


def validate_science(science, observation, before, cards, seed):
    keys(science, SCIENCE_KEYS, 'scientific audit')
    same(science['schema'], 'worker35-scientific-v1', 'scientific schema')
    for name in ('input_before', 'input_after', 'rng_before', 'rng_after'):
        valid_hash(science[name], name)
    same(science['input_before'], digest(observation), 'science public input fingerprint')
    same(science['input_after'], science['input_before'], 'public observation mutation')
    same(science['rng_before'], before, 'science RNG input')
    record = validate_public(observation, seed, cards)
    roots = science['roots']
    validate_roots(roots, observation, cards, record)
    supply = supply_for(observation, cards)
    same(science['supply'], supply, 'independent physical public supply')
    all_indices = list(range(len(roots)))
    allowed = []
    for i, root in enumerate(roots):
        move = root['move']
        material = observation['hand'][move['hand_index']]['material']
        stock = supply.get(material)
        if not (move['action'] == 'place' and stock and stock['deficit'] > 0
                and stock['available'] <= stock['deficit']):
            allowed.append(i)
    original, primary = maximizers(all_indices, roots), maximizers(allowed, roots)
    require(not roots or primary, 'impossible empty filtered tier')
    active = bool(primary) and all(roots[i]['move']['action'] == 'collect' for i in primary)
    guards = science['guards']
    require(type(guards) is list and len(guards) == len(roots), 'guard population')
    before_metrics = board_metrics(observation['board']['cells'])
    closure = []
    for i, (root, guard) in enumerate(zip(roots, guards)):
        keys(guard, 'eligible reason after exit_legal_count', 'guard')
        require(type(guard['eligible']) is bool, 'guard eligible boolean')
        move = root['move']
        stock = supply.get(observation['hand'][move['hand_index']]['material'])
        after = None
        exit_count = None
        if not active:
            reason = 'branch_not_active'
        elif move['action'] != 'place':
            reason = 'not_place'
        elif i not in allowed:
            reason = 'reserve_filtered'
        elif not stock or stock['deficit'] <= 0:
            reason = 'not_needed_material'
        else:
            exposed = v31.post_choice(record, move, observation['hand'], cards)
            after = board_metrics(exposed['board']['visible_cells'])
            if after[0] >= before_metrics[0]:
                reason = 'not_reduced'
            elif after[0] <= 0:
                reason = 'closed_tunnels'
            elif after[1] > before_metrics[1]:
                reason = 'visible_water_increased'
            elif after[2] > before_metrics[2]:
                reason = 'water_obstruction_increased'
            elif after[3] > before_metrics[3]:
                reason = 'trapped_water_increased'
            elif not observation['exit_placed']:
                exit_count = guard['exit_legal_count']
                integer(exit_count, 0, 1000000, 'standalone EXIT capacity')
                reason = 'eligible' if exit_count else 'no_exit_capacity'
            else:
                reason = 'eligible'
        eligible = reason == 'eligible'
        same(guard, {'eligible': eligible, 'reason': reason, 'after': after,
                     'exit_legal_count': exit_count}, 'independent guard order/geometry')
        if eligible:
            closure.append(i)
    final = maximizers(closure, roots) if closure else primary
    same(science['tiers'], {'T0': original, 'F': allowed, 'T': primary, 'C': closure, 'final': final},
         'independent ordered tier arithmetic')
    original_collect = bool(original) and all(roots[i]['move']['action'] == 'collect' for i in original)
    flags = dict(zip(FLAGS, (allowed != all_indices, primary != original, bool(closure),
                            bool(closure) and original_collect,
                            bool(closure) and primary != original and not original_collect)))
    same(science['flags'], flags, 'mechanism attribution flags')
    selected = science['chosen_index']
    if not roots:
        same(selected, None, 'empty choice index')
        same(science['chosen'], None, 'empty choice')
        same(science['rng_before'], science['rng_after'], 'empty choice consumed RNG')
    else:
        integer(selected, 0, len(roots) - 1, 'selected root')
        require(selected in final, 'chosen root outside final tier')
        same(science['chosen'], roots[selected]['move'], 'chosen root/index agreement')
        require(science['rng_before'] != science['rng_after'], 'nonempty choice did not consume RNG')
    return flags


def validate_cost(cost, caps, roots, label):
    keys(cost, COST_KEYS, label)
    for name in COST_KEYS.split():
        integer(cost[name], 0, caps[name], label + ' ' + name)
    same(cost['roots'], roots, label + ' root count')
    require(cost['legal_enumerations'] >= 1, label + ' missing legal enumeration')
    require(cost['legal_enumerations'] >= cost['previews'] + cost['exit_geometry_checks'],
            label + ' impossible physical call counts')


def common_audit(science):
    return dict(public_observation_sha256=science['input_before'], chosen_move=science['chosen'],
                rng_before_sha256=science['rng_before'], rng_after_sha256=science['rng_after'])


def validate_freeze(freeze, expected_sha, raw=None):
    """The expected hash must come from the separately authenticated execution-go."""
    valid_hash(expected_sha, 'external freeze SHA256')
    if raw is None:
        raw = canonical(freeze, newline=True)
    require(type(raw) is bytes and len(raw) <= 1024**2, 'freeze byte bound')
    same(strict_json(raw), freeze, 'freeze parsed/raw agreement')
    same(hashlib.sha256(raw).hexdigest(), expected_sha, 'externally pinned execution freeze')
    keys(freeze, 'schema preregistration_url baseline_commit baseline_source_blobs execution_source_sha256 runtime resources reviews synthetic_preflight_sha256', 'freeze')
    same(freeze['schema'], 'worker35-execution-freeze-v1', 'freeze schema')
    same(freeze['baseline_commit'], MODEL_COMPARATOR, 'canonical model comparator')
    source = freeze['baseline_source_blobs']
    require(type(source) is dict and len(source) == 26, 'canonical 26-blob source map')
    same(hashlib.sha256(canonical(source)).hexdigest(), SOURCE_MAP_SHA256, 'canonical source map fingerprint')
    for path, blob in source.items():
        require(type(path) is str and path.startswith(('src/', 'data/')), 'baseline path')
        valid_hash(blob, 'baseline blob', 40)
    execution = freeze['execution_source_sha256']
    require(type(execution) is dict and execution, 'execution source pins')
    required = set(source) | {'src/bandido_alcatraz/quota_reserve_closure.py',
        'src/bandido_alcatraz/quota_reserve_closure_reference.py',
        'scripts/run_quota_reserve_closure_development.py', 'scripts/worker35_resources.py',
        'scripts/verify_worker35_development.py', 'scripts/verify_worker31_development.py',
        'scripts/worker31_geometry.py', 'src/bandido_alcatraz/worker32/evidence.py',
        'experiments/quota-reserve-closure-development/PROTOCOL.md',
        'experiments/quota-reserve-closure-development/AUDIT-CONTRACT.md',
        '.github/workflows/quota-reserve-closure-development.yml', 'pyproject.toml'}
    require(required <= set(execution), 'execution source closure omits required file')
    for path, value in execution.items():
        require(type(path) is str and path and not path.startswith('/')
                and all(part not in ('', '.', '..') for part in path.split('/')), 'execution path')
        valid_hash(value, 'execution source digest')
    same(execution['scripts/verify_worker35_development.py'],
         hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'independently frozen verifier bytes')
    same(execution['scripts/verify_worker31_development.py'], WORKER31_SHA256, 'reviewed trace pin')
    same(execution['scripts/worker31_geometry.py'], v31.HELPER_SHA256, 'reviewed geometry pin')
    runtime = freeze['runtime']
    keys(runtime, 'implementation version executable_sha256', 'runtime freeze')
    same(runtime['implementation'], 'CPython', 'runtime implementation')
    same(runtime['version'], '3.11.16', 'runtime exact patch')
    valid_hash(runtime['executable_sha256'], 'runtime executable')
    resources = freeze['resources']
    keys(resources, 'per_call total_operations cohort_wall_seconds verification_wall_seconds address_space_bytes evidence_bytes trace_bytes line_bytes receipt_bytes shard_bytes archive_bytes', 'resource freeze')
    keys(resources['per_call'], 'control candidate reference', 'per-call resource scopes')
    for scope, limits in resources['per_call'].items():
        keys(limits, COST_KEYS + ' wall_seconds cpu_seconds', 'per-call ' + scope)
        for name, value in limits.items():
            integer(value, 1, 2**63 - 1, 'frozen per-call ' + name)
    keys(resources['total_operations'], 'legal_enumerations previews exit_geometry_checks', 'total operation caps')
    for name, value in resources['total_operations'].items():
        integer(value, 1, 2**63 - 1, 'total ' + name)
    for name, value in resources.items():
        if name not in ('per_call', 'total_operations'):
            integer(value, 1, 2**63 - 1, 'frozen ' + name)
    require(resources['line_bytes'] <= MAX_LINE, 'line bound exceeds verifier safety envelope')
    require(resources['receipt_bytes'] <= MAX_METADATA, 'receipt bound exceeds verifier safety envelope')
    require(resources['shard_bytes'] <= 30 * 1024**2, 'frozen shard exceeds transfer bound')
    keys(freeze['reviews'], 'candidate reference harness independent_a independent_b', 'review gates')
    for name, value in freeze['reviews'].items():
        same(value, 'required-clean-exact-head-before-go', 'review role requirement ' + name)
    valid_hash(freeze['synthetic_preflight_sha256'], 'synthetic preflight')
    require(type(freeze['preregistration_url']) is str and re.fullmatch(
        r'https://github\.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-[0-9]+',
        freeze['preregistration_url']), 'preregistration URL')
    load_reviewed()


class Evidence:
    """Bounded read-only directory, authenticated against independent byte inventory.

    Materialization/ZIP extraction is deliberately outside this program. Only
    exact closed-population regular files are read, never links or traversal.
    Each stream is rehashed on use, preventing an earlier inventory from hiding
    replacement or truncation. The caller must authenticate inventory/metadata.
    """
    def __init__(self, root, inventory, resources):
        self.root, self.inventory, self.resources = root, inventory, resources
        require(root.is_dir() and not root.is_symlink(), 'evidence root must be a regular directory')
        require(type(inventory) is dict, 'inventory mapping')
        files = {'receipt.json', 'completed.jsonl', 'resource-metrics.jsonl'} | {
            f'{kind}/pass-{p}/{s}.{suffix}' for kind, suffix in
            [('raw-results', 'json'), ('decision-traces', 'jsonl'), ('call-results', 'jsonl')] for p in PASSES for s in SEEDS}
        same(sorted(inventory), sorted(files), 'complete closed evidence inventory')
        actual = set()
        total = 0
        for path in root.rglob('*'):
            require(not path.is_symlink(), 'symlink in evidence tree')
            if path.is_file():
                actual.add(path.relative_to(root).as_posix())
            else:
                require(path.is_dir(), 'nonregular evidence entry')
        same(sorted(actual), sorted(files), 'missing or extra evidence files')
        for name, entry in inventory.items():
            keys(entry, 'sha256 size_bytes', 'file inventory')
            valid_hash(entry['sha256'], 'inventory digest')
            integer(entry['size_bytes'], 1, resources['evidence_bytes'], 'inventory bytes')
            total += entry['size_bytes']
            with (root / name).open('rb') as stream:
                same(v31.hash_stream(stream, self.limit(name)), entry, 'inventory byte readback ' + name)
        require(total <= resources['evidence_bytes'], 'expanded evidence resource limit')
        self.size_bytes = total

    def limit(self, name):
        if name == 'receipt.json':
            return self.resources['receipt_bytes']
        if name.startswith('decision-traces/'):
            return self.resources['trace_bytes']
        return self.resources['evidence_bytes']

    def json(self, name, unused=None):
        limit = min(self.limit(name), MAX_METADATA)
        path = self.root / name
        require(not path.is_symlink(), 'evidence replaced with symlink')
        with path.open('rb') as stream:
            raw = stream.read(limit + 1)
        require(len(raw) <= limit, 'JSON member bound')
        same({'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)},
             self.inventory[name], 'JSON fresh byte readback')
        value = strict_json(raw)
        require(raw == canonical(value, newline=True), 'noncanonical JSON bytes')
        return value

    def lines(self, name, unused=None):
        path = self.root / name
        require(not path.is_symlink(), 'evidence replaced with symlink')
        digest_, total = hashlib.sha256(), 0
        with path.open('rb') as stream:
            while True:
                raw = stream.readline(self.resources['line_bytes'] + 1)
                if not raw:
                    break
                total += len(raw)
                require(total <= self.limit(name) and len(raw) <= self.resources['line_bytes'],
                        'JSONL member/line bound')
                require(raw.endswith(b'\n') and raw.strip(), 'partial/empty JSONL line')
                value = strict_json(raw)
                require(raw == canonical(value, newline=True), 'noncanonical JSONL bytes')
                digest_.update(raw)
                yield value, raw
        same({'sha256': digest_.hexdigest(), 'size_bytes': total}, self.inventory[name], 'JSONL fresh byte readback')

    def equal_members(self, first, second):
        same(self.inventory[first], self.inventory[second], 'candidate/replay trace byte identity')


def validate_boundary(boundary, public_sha, chosen, tier, candidate):
    keys(boundary, 'public_before public_after engine_before engine_after choice_calls choice_tier reference_choice_calls reference_choice_tier', 'policy boundary')
    for field in ('public_before', 'public_after', 'engine_before', 'engine_after'):
        valid_hash(boundary[field], 'boundary ' + field)
    same(boundary['public_before'], public_sha, 'boundary public before')
    same(boundary['public_after'], public_sha, 'boundary public immutability')
    same(boundary['engine_before'], boundary['engine_after'], 'real engine mutation during policy')
    same(boundary['choice_calls'], int(chosen is not None), 'exact choice-call count')
    same(boundary['choice_tier'], tier, 'actual RNG choice population')
    same(boundary['reference_choice_calls'], int(chosen is not None) if candidate else None,
         'independent RNG choice-call count')
    same(boundary['reference_choice_tier'], tier if candidate else None,
         'independent actual RNG choice population')


def validate_decision(audit, started, pass_number, cards, seed, caps, raw_calls):
    obs, before = started['observation'], started['rng_before_sha256']
    valid_hash(before, 'decision RNG before')
    if pass_number == 1:
        keys(audit, v31.COMMON + ' roots final cost boundary', 'control audit')
        record = validate_public(obs, seed, cards)
        validate_roots(audit['roots'], obs, cards, record)
        final = maximizers(list(range(len(audit['roots']))), audit['roots'])
        same(audit['final'], final, 'canonical V4 maximizers')
        tier = [audit['roots'][i]['move'] for i in final]
        v31.validate_audit({k: audit[k] for k in v31.COMMON.split()}, started, obs['hand'], 1)
        require(audit['chosen_move'] in tier if tier else audit['chosen_move'] is None,
                'control choice outside canonical tier')
        validate_cost(audit['cost'], caps['control'], len(audit['roots']), 'control')
        common = {k: audit[k] for k in v31.COMMON.split()}
        costs, flags = {'control': audit['cost']}, dict.fromkeys(FLAGS, False)
        call_results = {'control': {'chosen': audit['chosen_move'], 'roots': audit['roots'],
                                    'final': audit['final'], 'cost': audit['cost']}}
    else:
        keys(audit, 'scientific_sha256 reference_scientific_sha256 candidate_cost reference_cost boundary', 'candidate audit')
        keys(raw_calls['candidate'], 'chosen scientific cost', 'raw candidate output')
        keys(raw_calls['reference'], 'chosen scientific_sha256 cost', 'raw reference output')
        science = raw_calls['candidate']['scientific']
        flags = validate_science(science, obs, before, cards, seed)
        same(audit['scientific_sha256'], digest(science), 'full persisted scientific digest')
        same(audit['reference_scientific_sha256'], digest(science), 'full independently authored reference agreement')
        same(raw_calls['reference']['scientific_sha256'], digest(science), 'durable independent reference digest')
        common = common_audit(science)
        tier = [science['roots'][i]['move'] for i in science['tiers']['final']]
        costs, call_results = {}, {}
        for scope in ('candidate', 'reference'):
            cost = audit[scope + '_cost']
            validate_cost(cost, caps[scope], len(science['roots']), scope)
            # Actual profile receipts must fit the reviewed one-ply call graph.
            previews = sum(r['move']['action'] == 'place' for r in science['roots']) + sum(
                guard['after'] is not None for guard in science['guards'])
            exit_checks = sum(guard['exit_legal_count'] is not None for guard in science['guards'])
            same(cost, dict(legal_enumerations=1 + previews + exit_checks, previews=previews,
                            exit_geometry_checks=exit_checks, roots=len(science['roots'])),
                 scope + ' profiled call-graph conservation')
            costs[scope] = cost
            call_results[scope] = {'chosen': science['chosen'], 'scientific' if scope == 'candidate' else 'scientific_sha256': science if scope == 'candidate' else digest(science), 'cost': cost}
    validate_boundary(audit['boundary'], common['public_observation_sha256'],
                      common['chosen_move'], tier, pass_number != 1)
    return common, costs, flags, call_results


def validate_terminal(raw, record, cards, previous, choice):
    obs = raw['final_public_observation']
    # Terminal observations can have an empty hand, unlike live policy input.
    # Validate public board/count/history through the reviewed normalized record,
    # then directly bind every remaining public field and physical hand identity.
    keys(obs, 'board hand raincoats ropes exit_placed exit_seen turns set_aside_unplayable collected_equipment setup player_index', 'terminal public observation')
    same(obs['setup'], SETUP, 'terminal setup')
    same(obs['player_index'], 0, 'terminal player')
    same(obs['board'], {'placements': record['board']['placements'], 'cells': record['board']['visible_cells']}, 'terminal public geometry')
    for key in ('raincoats', 'ropes', 'exit_placed', 'turns'):
        same(obs[key], record['result'][key], 'terminal public ' + key)
    expected_collections = [{'card': dict(card_id=c['card_id'], material=c['material'], is_exit=False, cells=c['cells']),
                             'turn': c['turn'], 'player_index': 0} for c in record['collected_equipment']]
    same(obs['collected_equipment'], expected_collections, 'terminal public collection history')
    require(type(obs['hand']) is list and len(obs['hand']) <= 6, 'terminal hand')
    for card in obs['hand']:
        v31.card_schema(card, cards)
    require(type(obs['exit_seen']) is bool, 'terminal EXIT seen')
    require(type(obs['set_aside_unplayable']) is int and obs['set_aside_unplayable'] in (0, 6), 'terminal aside')
    if choice is not None:
        v31.validate_public_progression(previous, choice, obs)
    else:
        # A returned no-legal-move decision did not refresh or mutate state.
        same(obs, previous, 'terminal null choice state')
    conservation = raw['conservation']
    keys(conservation, 'inventory_count inventory_sha256 zones', 'terminal conservation')
    zones = conservation['zones']
    keys(zones, 'placed collected hand draw set_aside', 'physical zones')
    identities = []
    for name, values in zones.items():
        require(type(values) is list and all(type(i) is str and i in cards and i != 'start_easy' for i in values), 'physical zone IDs')
        require(values == sorted(set(values)), 'physical zone ordering/duplicates')
        identities.extend(values)
    same(sorted(identities), sorted(set(cards) - {'start_easy'}), 'full physical 69-card conservation')
    same(conservation['inventory_count'], 69, 'physical inventory count')
    same(conservation['inventory_sha256'], digest(sorted(identities)), 'physical inventory digest')
    same(zones['placed'], sorted(p['card_id'] for p in record['board']['placements'][1:]), 'placed zone history')
    same(zones['collected'], sorted(c['card_id'] for c in record['collected_equipment']), 'collected zone history')
    same(zones['hand'], sorted(c['card_id'] for c in obs['hand']), 'terminal own-hand zone')
    same(len(zones['set_aside']), obs['set_aside_unplayable'], 'set-aside zone count')
    same(len(obs['hand']), min(6, 69 - obs['turns'] - obs['set_aside_unplayable']), 'terminal hand conservation')
    if obs['set_aside_unplayable']:
        same(zones['draw'], [], 'short refresh permanently empties stock')
    for material, (quota, total, counter) in MATERIALS.items():
        unconsumed = sum(cards[identity]['material'] == material for identity in zones['hand'] + zones['draw'])
        placed = sum(cards[identity]['material'] == material for identity in zones['placed'])
        if obs[counter] < quota:
            same(total - obs[counter] - placed, unconsumed, 'terminal still-needed public-supply invariant')
    if record['result']['reason'] == 'deck_exhausted':
        same(zones['hand'] + zones['draw'], [], 'deck exhaustion physical zones')


def validate_metric(metric, identity, cost, caps, resources):
    expected_keys = 'kind pass seed ordinal scope wall_seconds cpu_seconds peak_rss_kib cost status' if cost is not None else 'kind pass seed wall_seconds cpu_seconds peak_rss_kib status operations'
    keys(metric, expected_keys, 'resource metric')
    for key, value in identity.items():
        same(metric[key], value, 'resource ' + key)
    same(metric['status'], 'returned' if cost is not None else 'complete', 'failed or partial resource receipt')
    for name in ('wall_seconds', 'cpu_seconds'):
        value = metric[name]
        require(type(value) in (int, float) and math.isfinite(value) and value >= 0, 'resource finite nonnegative time')
        bound = caps[name] if cost is not None else resources['cohort_wall_seconds']
        require(value <= bound, 'observed ' + name + ' exceeds prospective cap')
    integer(metric['peak_rss_kib'], 1, resources['address_space_bytes'] // 1024, 'observed peak memory')
    if cost is not None:
        same(metric['cost'], cost, 'metric vs deterministic physical operations')
    else:
        keys(metric['operations'], 'legal_enumerations previews exit_geometry_checks', 'game physical operations')
        for name, value in metric['operations'].items():
            integer(value, 0, resources['total_operations'][name], 'game physical ' + name)


class TraceAdapter:
    """Reuse reviewed public trace transitions while checking Worker35 payloads."""
    def __init__(self, evidence, record, pass_number, cards, freeze, metrics, historical):
        self.evidence, self.record, self.p, self.cards = evidence, record, pass_number, cards
        self.freeze, self.metrics, self.historical = freeze, metrics, historical
        self.flags, self.operations = Counter(), Counter()
        self.previous = self.choice = self.initial = None
        self.comparable = self.different = 0

    def control_contexts(self):
        for event, unused in self.evidence.lines(v31.trace_name(1, self.record['seed'])):
            if event.get('event') == 'decision_completed':
                yield event['audit']

    def lines(self, unused_name, unused_limit):
        seed = self.record['seed']
        calls = iter(self.evidence.lines(f'call-results/pass-{self.p}/{seed}.jsonl'))
        baseline = iter(self.historical.lines(seed)) if self.p == 1 else None
        control = iter(self.control_contexts()) if self.p == 2 else None
        started = None
        for event, raw in self.evidence.lines(v31.trace_name(self.p, seed)):
            if event.get('event') == 'decision_started':
                started = event
                if self.initial is None:
                    self.initial = [digest(event['observation']), event['rng_before_sha256']]
            elif event.get('event') == 'decision_completed':
                require(started is not None, 'completion without decision start')
                raw_calls = {}
                for scope in (('control',) if self.p == 1 else ('candidate', 'reference')):
                    output, unused = next(calls, (None, None))
                    keys(output, 'ordinal scope result', 'raw call envelope')
                    same(output['ordinal'], event['ordinal'], 'raw call ordinal')
                    same(output['scope'], scope, 'raw call scope/order')
                    raw_calls[scope] = output['result']
                common, costs, flags, outputs = validate_decision(event['audit'], started, self.p,
                    self.cards, seed, self.freeze['resources']['per_call'], raw_calls)
                for scope, cost in costs.items():
                    same(raw_calls[scope], outputs[scope], 'durable raw call result')
                    metric, unused = next(self.metrics, (None, None))
                    validate_metric(metric, dict(kind='decision', **{'pass': self.p}, seed=seed,
                        ordinal=event['ordinal'], scope=scope), cost,
                        self.freeze['resources']['per_call'][scope], self.freeze['resources'])
                    self.operations.update({k: cost[k] for k in ('legal_enumerations', 'previews', 'exit_geometry_checks')})
                self.flags.update({k: int(value) for k, value in flags.items()})
                if control is not None:
                    peer = next(control, None)
                    if peer is not None and all(peer[k] == common[k] for k in
                            ('public_observation_sha256', 'rng_before_sha256')):
                        self.comparable += 1
                        self.different += canonical(peer['chosen_move']) != canonical(common['chosen_move'])
                self.previous, self.choice = started['observation'], common['chosen_move']
                event = dict(event, audit=common)
                started = None
            if baseline is not None:
                same(event, next(baseline, None), 'exact historical control trace projection')
            yield event, raw
        if baseline is not None:
            require(next(baseline, None) is None, 'extra historical control events')
        require(next(calls, None) is None, 'extra raw call results')
        if control is not None:
            for unused in control:
                pass
        metric, unused = next(self.metrics, (None, None))
        validate_metric(metric, {'kind': 'game', 'pass': self.p, 'seed': seed}, None, None, self.freeze['resources'])
        self.game_wall = metric['wall_seconds']
        self.game_operations = metric['operations']
        for key, value in self.operations.items():
            require(value <= self.game_operations[key], 'game physical operations omit decision calls')


def validate_metadata(metadata, freeze_sha):
    keys(metadata, 'run job execution_commit execution_blobs execution_go', 'authenticated metadata')
    run, job, commit, go = (metadata[name] for name in ('run', 'job', 'execution_commit', 'execution_go'))
    keys(go, 'head tree freeze_sha256 execution_go_url', 'authenticated execution-go')
    valid_hash(go['head'], 'execution head', 40)
    valid_hash(go['tree'], 'execution tree', 40)
    same(go['freeze_sha256'], freeze_sha, 'execution-go freeze')
    require(type(go['execution_go_url']) is str and re.fullmatch(
        r'https://github\.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-[0-9]+',
        go['execution_go_url']), 'separate authenticated execution-go URL')
    same(commit.get('sha'), go['head'], 'authenticated execution commit')
    same(commit.get('tree', {}).get('sha'), go['tree'], 'authenticated execution tree')
    integer(run.get('id'), 1, 10**16, 'authenticated run ID')
    for value in (run, job):
        for name, expected in [('status', 'completed'), ('conclusion', 'success'),
                               ('head_sha', go['head']), ('run_attempt', 1)]:
            same(value.get(name), expected, 'successful exact-head first-attempt metadata ' + name)
    same(run.get('event'), 'pull_request', 'admission event')
    same(run.get('path'), '.github/workflows/quota-reserve-closure-development.yml', 'execution workflow')
    same(run.get('head_branch'), 'research/worker35-quota-reserve-closure', 'execution branch')
    for name in ('repository', 'head_repository'):
        same(run.get(name, {}).get('full_name'), REPOSITORY, 'authenticated repository')
    same(job.get('run_id'), run['id'], 'job run identity')
    same(job.get('runner_name'), 'bandido-alcatraz-ci', 'named research runner')
    same(job.get('name'), 'development', 'execution job')
    labels = job.get('labels')
    require(type(labels) is list and all(type(x) is str for x in labels) and
            {'self-hosted', 'Linux', 'X64', 'bandido-alcatraz-ci'} <= set(labels), 'runner labels')
    steps = job.get('steps')
    require(type(steps) is list and steps, 'authenticated step receipts')
    for step in steps:
        same(step.get('status'), 'completed', 'unfinished workflow step')
        require(step.get('conclusion') in ('success', 'skipped'), 'failed workflow step')
    names = [step.get('name') for step in steps]
    require(all(type(name) is str for name in names), 'step names')
    # Required scientific phases must execute, not merely be listed as skipped.
    for fragment in ('Initialize', 'synthetic', 'Three complete', 'Reconcile'):
        matching = [s for s in steps if fragment.lower() in s['name'].lower()]
        require(len(matching) == 1 and matching[0]['conclusion'] == 'success', 'required step ' + fragment)
    blobs = metadata['execution_blobs']
    require(type(blobs) is dict and blobs, 'independently authenticated execution blobs')
    for value in blobs.values():
        valid_hash(value, 'execution blob', 40)


def validate_receipt(receipt, freeze, freeze_sha, metadata):
    source = freeze['baseline_source_blobs']
    go, run = metadata['execution_go'], metadata['run']
    expected = {'schema': 'bandido-quota-reserve-closure-development-v1',
        'expected_head': go['head'], 'preregistration_url': freeze['preregistration_url'],
        'audit_clarification_url': freeze['preregistration_url'], 'freeze_sha256': freeze_sha,
        'freeze': freeze, 'run_id': str(run['id']), 'run_attempt': '1',
        'accepted_main': ACCEPTED_MAIN, 'accepted_tree': ACCEPTED_TREE, 'worker': 35,
        'ruleset_id': RULESET, 'setup_id': SETUP_ID, 'setup': SETUP,
        'policy': {'class': 'BoundedMergeV4Policy', 'setup_weight': 250}, 'max_steps': MAX_STEPS,
        'seed_start': SEEDS.start, 'seed_end': SEEDS.stop - 1, 'population': len(SEEDS),
        'passes': list(PASSES), 'phases': {'1': 'v4_control', '2': 'candidate', '3': 'candidate_replay'},
        'candidate': {'class': 'QuotaReserveClosurePolicy', 'module': 'src/bandido_alcatraz/quota_reserve_closure.py'},
        'control_array_sha256': CONTROL_ARRAY_SHA256, 'min_net_wins': MIN_NET_WINS,
        'fresh_seeds_used': False, 'status': 'complete', 'research_interpretation_performed': True,
        'attempted': [{'pass': p, 'seed': s} for p in PASSES for s in SEEDS], 'current': None,
        'completed_records': 3 * len(SEEDS), 'errors': [],
        'last_durable_completed_records': 3 * len(SEEDS), 'observed_journal_records': 3 * len(SEEDS),
        'step_outcomes': {'tests': 'success', 'cohort': 'success'}}
    keys(receipt, ' '.join(expected) + ' source_before source_after source_at_finalization source_at_initialization classification summary cohort_elapsed_seconds verification_elapsed_seconds total_operations memory_limit admission execution_go', 'complete attempt receipt')
    for name, value in expected.items():
        same(receipt.get(name), value, 'receipt ' + name)
    same(receipt['execution_go'], go, 'persisted admission execution-go')
    same(receipt['admission'], {'schema': 'worker35-exclusive-admission-v1',
        'expected_head': go['head'], 'preregistration_url': freeze['preregistration_url'],
        'audit_clarification_url': freeze['preregistration_url'], 'run_id': str(run['id']),
        'run_attempt': '1', 'freeze_sha256': freeze_sha, 'execution_go': go}, 'exclusive execution admission receipt')
    same(receipt['memory_limit'], {'mechanism': 'RLIMIT_AS', 'soft': freeze['resources']['address_space_bytes'],
        'hard': freeze['resources']['address_space_bytes']}, 'effective memory enforcement receipt')
    same(sorted(metadata['execution_blobs']), sorted(freeze['execution_source_sha256']), 'execution input closure')
    for name, blob in source.items():
        same(metadata['execution_blobs'].get(name), blob, 'unchanged canonical blob ' + name)
    snapshot = dict(head=go['head'], tree=go['tree'], baseline_commit=MODEL_COMPARATOR,
        source_blobs=source, execution_blobs=metadata['execution_blobs'],
        execution_sha256=freeze['execution_source_sha256'], python_implementation='CPython',
        python_version='3.11.16', executable_sha256=freeze['runtime']['executable_sha256'])
    for name in ('source_before', 'source_after', 'source_at_finalization'):
        same(receipt.get(name), snapshot, 'unchanged complete source/runtime ' + name)
    initial = receipt.get('source_at_initialization')
    keys(initial, ' '.join(snapshot), 'initial source snapshot')
    for key in snapshot:
        if key not in ('python_implementation', 'python_version', 'executable_sha256'):
            same(initial[key], snapshot[key], 'initial source ' + key)
    require(type(initial['python_implementation']) is str and initial['python_implementation'], 'initial interpreter')
    require(type(initial['python_version']) is str and re.fullmatch(r'\d+\.\d+\.\d+', initial['python_version']), 'initial runtime')
    valid_hash(initial['executable_sha256'], 'initial executable')


def summarize(control, candidate, failures, hashes, flags, readiness, terminal_diagnostics):
    base, wins = set(control), set(candidate)
    seeds = set(SEEDS)
    gained, lost = wins - base, base - wins
    net = len(wins) - len(base)
    result = {'games_per_pass': len(SEEDS), 'matching_records': len(SEEDS), 'quota_overshoots': 0,
        'control_wins': len(base), 'wins': len(wins), 'win_rate': len(wins) / len(SEEDS),
        'winning_seed_ids': sorted(wins), 'net_wins': net, 'min_net_wins': MIN_NET_WINS,
        'classification': ADVANCED_CLASSIFICATION if net >= MIN_NET_WINS else CLASSIFICATION,
        'paired_2x2': {'both_win': len(wins & base), 'control_only': len(lost), 'candidate_only': len(gained),
                       'both_lose': len(seeds - (wins | base))},
        'gained_seed_ids': sorted(gained), 'lost_seed_ids': sorted(lost), 'shared_win_seed_ids': sorted(wins & base),
        'both_loss_seed_ids': sorted(seeds - (wins | base)), 'candidate_loss_seed_ids': sorted(seeds - wins),
        'control_loss_seed_ids': sorted(seeds - base), 'failure_reasons': dict(sorted(failures.items())),
        'interpretation': 'Spent development screen only; next validation requires separate preregistration',
        'normalized_control_sha256': hashes[1], 'normalized_candidate_sha256': hashes[2]}
    result['descriptive_diagnostics'] = {'equipment_ready_terminal': readiness,
        'terminal_conditions': terminal_diagnostics, 'mechanism_counts': {name: flags[name] for name in FLAGS},
        'mechanism_attribution': ('Closure overrides observed; counts are descriptive, not causal evidence'
            if flags['closure_branch_selected'] else
            'No closure overrides observed; any effect supports only the complete observed policy behavior'),
        'equipment_completion_is_advancement_gate': False,
        'development_is_fresh_confirmation': False}
    return result


def _verify(root, inventory, metadata, freeze, freeze_sha, data_dir, historical, freeze_bytes):
    validate_freeze(freeze, freeze_sha, freeze_bytes)
    validate_metadata(metadata, freeze_sha)
    require(metadata['execution_go']['execution_go_url'] != freeze['preregistration_url'], 'execution-go must be separate')
    cards = g.load_cards(data_dir, freeze['baseline_source_blobs'])
    evidence = Evidence(root, inventory, freeze['resources'])
    receipt = evidence.json('receipt.json')
    validate_receipt(receipt, freeze, freeze_sha, metadata)
    rows = iter(evidence.lines('completed.jsonl'))
    metrics = iter(evidence.lines('resource-metrics.jsonl'))
    hashes = {p: hashlib.sha256(b'[') for p in PASSES}
    wins, readiness = {p: [] for p in PASSES}, {'control': 0, 'candidate': 0}
    terminal_diagnostics = {'control': Counter(), 'candidate': Counter()}
    flags, failures, operations, game_operations = Counter(), Counter(), Counter(), Counter()
    contexts, game_wall, comparable, different = {}, 0, 0, 0
    for p in PASSES:
        for index, seed in enumerate(SEEDS):
            row, unused = next(rows, (None, None))
            keys(row, 'pass record', 'completion journal')
            same(row['pass'], p, 'serial ascending phase order')
            record = row['record']
            g.validate_record(record, seed, cards)
            raw = evidence.json(f'raw-results/pass-{p}/{seed}.json')
            keys(raw, 'pass seed result public_capture_count public_captures trace_counts final_public_observation conservation', 'terminal raw result')
            for field, value in {'pass': p, 'seed': seed, 'result': record['result'], 'public_capture_count': 1,
                                 'public_captures': [record]}.items():
                same(raw[field], value, 'raw/journal ' + field)
            adapter = TraceAdapter(evidence, record, p, cards, freeze, metrics, historical)
            counts, unused1, unused2, unused3 = v31.validate_trace(adapter, record, 1, cards)
            same(raw['trace_counts'], counts, 'raw/trace decision counts')
            validate_terminal(raw, record, cards, adapter.previous, adapter.choice)
            operations.update(adapter.operations)
            game_operations.update(adapter.game_operations)
            game_wall += adapter.game_wall
            if p == 1:
                contexts[seed] = adapter.initial
            else:
                same(adapter.initial, contexts[seed], 'control/candidate initial observation and RNG')
            if p == 2:
                flags.update(adapter.flags)
                comparable += adapter.comparable
                different += adapter.different
                evidence.equal_members(v31.trace_name(2, seed), v31.trace_name(3, seed))
                evidence.equal_members(f'call-results/pass-2/{seed}.jsonl', f'call-results/pass-3/{seed}.jsonl')
            if p == 3:
                peer = evidence.json(f'raw-results/pass-2/{seed}.json')
                same({k: val for k, val in raw.items() if k != 'pass'},
                     {k: val for k, val in peer.items() if k != 'pass'}, 'full candidate/replay terminal evidence')
            if index:
                hashes[p].update(b',')
            hashes[p].update(canonical(record))
            result = record['result']
            if result['won']:
                wins[p].append(seed)
            if p in (1, 2):
                scope = 'control' if p == 1 else 'candidate'
                readiness[scope] += result['raincoats'] == 3 and result['ropes'] == 2
                for name, failed in [('water_remaining', result['visible_water_cells'] > 0),
                    ('exit_unplaced', not result['exit_placed']),
                    ('closed_tunnels_conditions_failed', result['reason'] == 'closed_tunnels_conditions_failed'), ('equipment_incomplete',
                    result['raincoats'] != 3 or result['ropes'] != 2), ('open_tunnels', result['open_tunnels'] > 0)]:
                    terminal_diagnostics[scope][name] += int(not result['won'] and failed)
                if p == 2 and not result['won']:
                    failures[result['reason']] += 1
        hashes[p].update(b']\n')
        if p == 1:
            same(hashes[p].hexdigest(), CONTROL_ARRAY_SHA256, 'full accepted normalized 400-control SHA256')
            same(len(wins[p]), CONTROL_WINS, 'accepted control wins')
            same(readiness['control'], CONTROL_EQUIPMENT_READY, 'accepted control equipment readiness')
    require(next(rows, None) is None, 'extra journal games')
    require(next(metrics, None) is None, 'extra resource metrics')
    same(hashes[2].hexdigest(), hashes[3].hexdigest(), 'candidate/replay normalized records')
    keys(receipt['total_operations'], 'legal_enumerations previews exit_geometry_checks', 'whole-run physical operations')
    same(receipt['total_operations'], dict(game_operations), 'whole-run/game-delta physical conservation')
    for key in ('legal_enumerations', 'previews', 'exit_geometry_checks'):
        integer(receipt['total_operations'][key], operations[key], freeze['resources']['total_operations'][key],
                'whole-run actual physical operation ceiling ' + key)
    require(game_wall <= freeze['resources']['cohort_wall_seconds'], 'whole-run game wall ceiling')
    for field, cap in [('cohort_elapsed_seconds', 'cohort_wall_seconds'),
                       ('verification_elapsed_seconds', 'verification_wall_seconds')]:
        elapsed = receipt.get(field)
        require(type(elapsed) in (int, float) and math.isfinite(elapsed) and
                0 <= elapsed <= freeze['resources'][cap], 'full elapsed resource receipt ' + field)
    require(game_wall <= receipt['cohort_elapsed_seconds'], 'game times exceed full cohort elapsed receipt')
    summary = summarize(wins[1], wins[2], failures, {p: h.hexdigest() for p, h in hashes.items()},
                        flags, readiness, {k: dict(v) for k, v in terminal_diagnostics.items()})
    summary['equipment_ready'] = readiness
    summary['terminal_components'] = {scope: {
        'visible_water_remaining': counts['water_remaining'],
        'exit_unplaced': counts['exit_unplaced'],
        'closed_tunnels_conditions_failed': counts['closed_tunnels_conditions_failed']}
        for scope, counts in terminal_diagnostics.items()}
    summary['trace_summary'] = {'mechanism_counts': dict(sorted((name, flags[name]) for name in FLAGS)),
        'matched_observation_rng_decisions': comparable,
        'selected_action_differences_in_matched_contexts': different,
        'candidate_replay_trace_matches': len(SEEDS),
        'action_difference_scope': 'same seed and ordinal with identical public observation and pre-choice RNG hashes'}
    # Producer's compact outcome claims must equal independent recomputation.
    for key, value in summary.items():
        if key != 'descriptive_diagnostics':
            same(receipt.get('summary', {}).get(key), value, 'producer summary ' + key)
    same(receipt['classification'], summary['classification'], 'producer research classification')
    return {'verified': True, 'worker': 35, 'classification': summary['classification'],
        'run_id': metadata['run']['id'], 'run_attempt': 1, 'head': metadata['execution_go']['head'],
        'tree': metadata['execution_go']['tree'], 'freeze_sha256': freeze_sha,
        'verified_records': 3 * len(SEEDS), 'verified_traces': 3 * len(SEEDS),
        'historical_control_trace_matches': len(SEEDS), 'historical_control_archive_sha256': BASELINE_ARCHIVE_SHA256,
        'verified_call_logs': 3 * len(SEEDS), 'source_map_sha256': SOURCE_MAP_SHA256,
        'decision_physical_operations': dict(operations), 'physical_operations': receipt['total_operations'], 'expanded_evidence_bytes': evidence.size_bytes,
        'reviewed_trace_sha256': WORKER31_SHA256, 'geometry_sha256': v31.HELPER_SHA256,
        'independence_scope': 'Persisted arithmetic, physical geometry and trace transitions independently checked; full reference decisions executed only by the frozen named-runner harness',
        'transport_and_drive_custody': {'established_by_this_verifier': False,
            'required_before_acceptance': 'Independent complete part count/hash/size, reassembly and ZIP member inventory, followed by fresh canonical Drive byte readback',
            'frozen_caps': {key: freeze['resources'][key] for key in ('archive_bytes', 'shard_bytes', 'evidence_bytes')}},
        'summary': summary}


class HistoricalControl:
    """Stream only accepted historical controls from the fixed authenticated ZIP."""
    def __init__(self, path):
        self.path, self.stream, self.archive = path, None, None

    def __enter__(self):
        require(not self.path.is_symlink(), 'historical archive symlink')
        self.stream = self.path.open('rb')
        try:
            observed = v31.hash_stream(self.stream, v31.MAX_ARCHIVE)
            same(observed['sha256'], BASELINE_ARCHIVE_SHA256, 'authenticated historical control archive bytes')
            self.stream.seek(0)
            self.archive = zipfile.ZipFile(self.stream)
            names = self.archive.namelist()
            require(len(names) == len(set(names)), 'duplicate historical members')
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *unused):
        if self.archive is not None:
            self.archive.close()
        if self.stream is not None:
            self.stream.close()

    def lines(self, seed):
        name = v31.trace_name(1, seed)
        require(self.archive.getinfo(name).file_size <= v31.MAX_TRACE, 'historical trace size bound')
        total = 0
        with self.archive.open(name) as stream:
            while True:
                raw = stream.readline(v31.MAX_LINE + 1)
                if not raw:
                    break
                total += len(raw)
                require(total <= v31.MAX_TRACE and len(raw) <= v31.MAX_LINE, 'historical trace byte bound')
                value = strict_json(raw)
                require(raw == canonical(value, newline=True), 'historical canonical JSONL')
                yield value


def verify(root, inventory, metadata, freeze, freeze_sha, data_dir, baseline_archive, freeze_bytes=None):
    with HistoricalControl(baseline_archive) as historical:
        return _verify(root, inventory, metadata, freeze, freeze_sha, data_dir, historical, freeze_bytes)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence_dir', type=Path)
    for option in ('inventory', 'metadata', 'freeze', 'data-dir', 'baseline-archive'):
        parser.add_argument('--' + option, type=Path, required=True)
    parser.add_argument('--freeze-sha256', required=True)
    args = parser.parse_args(argv)
    try:
        freeze = read_json(args.freeze, 1024**2)
        with args.freeze.open('rb') as stream:
            freeze_raw = stream.read(1024**2 + 1)
        result = verify(args.evidence_dir, read_json(args.inventory), read_json(args.metadata),
                        freeze, args.freeze_sha256, args.data_dir, args.baseline_archive, freeze_raw)
    except OSError as error:
        print(f'VERIFICATION_BLOCKED: {type(error).__name__}: {error}; inputs preserved; no research classification accepted', file=sys.stderr)
        return 2
    except (ValueError, TypeError, KeyError, AttributeError, IndexError, RuntimeError,
            OverflowError, RecursionError, EOFError, StopIteration, MemoryError, zipfile.BadZipFile) as error:
        print(f'INTEGRITY_INVALID: {type(error).__name__}: {error}; inputs preserved; no research classification accepted', file=sys.stderr)
        return 1
    print(canonical(result).decode())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
