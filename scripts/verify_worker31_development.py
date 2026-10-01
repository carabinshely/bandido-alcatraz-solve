"""Streaming, offline Worker31 gate. No engine, policy, producer, network or Git.

Authority is external: authenticate terminal GitHub metadata and compute the
inventory from downloaded bytes independently of receipt claims. See README.md.
All input is bounded, hash checked and read without extraction or modification.
A rejected/partial/failed run is never interpreted as a negative research result.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import stat
import struct
import sys
import zipfile
import zlib

HELPER_SHA256 = 'a9ef3fce518ad5ce0ed02ae6cb69664f775c732a750f7f739f1ccda1e04c7bcb'

def load_geometry():
    path = Path(__file__).with_name('worker31_geometry.py')
    if path.stat().st_size > 64 * 1024:
        raise ValueError('pinned dependency exceeds byte bound')
    with path.open('rb') as stream:
        raw = stream.read(64 * 1024 + 1)
    if len(raw) > 64 * 1024:
        raise ValueError('pinned dependency exceeds byte bound')
    if hashlib.sha256(raw).hexdigest() != HELPER_SHA256:
        raise ValueError('pinned pure geometry dependency changed')
    spec = importlib.util.spec_from_loader('_worker31_pinned_geometry', loader=None)
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module

g = load_geometry()
Rejected, require, same, keys, integer = g.Rejected, g.require, g.same, g.keys, g.integer
canonical, strict_json = g.canonical, g.strict_json
REPOSITORY = 'carabinshely/bandido-alcatraz-solve'
RUN_ID = 36848990406
RUN_ATTEMPT = 1
HEAD = '7a2b681f2d78c9e4cef466eb5250c4bd6c6c52ed'
EXECUTION_TREE = 'dc073c8484beef1f63734f177790ca46f1331a67'
ACCEPTED_MAIN = '7be68ee6eac1337663b960791812c8092c7d53e4'
ACCEPTED_TREE = '7ed3b7f1f5a8d09991542f5d22f102e0b83fe612'
SOURCE_MAP_SHA256 = '27b4a000202d5e22b3e37ea128571cd7a5b8a4ef1a882514616c361cf2da0aed'
CANDIDATE_PATH = 'src/bandido_alcatraz/equipment_opportunity.py'
CANDIDATE_BLOB = '3c10b6253ab272fa0b91a8ef967a7c03b9939538'
CANDIDATE_SHA256 = 'e6f2b7d0241a2f473888222de9c3173568c97e7b77c4173ba2d1c3ad55347cce'
HARNESS_BLOB = '2615059581d5eb24ac67c9eb787cdc11a98940c3'
HARNESS_SHA256 = '638947894a21976c608cc9a4975db501c794d3383de4e3f6fb72a9efd2faad65'
PREREGISTRATION = f'https://github.com/{REPOSITORY}/issues/2#issuecomment-5928556762'
AUDIT_CLARIFICATION = f'https://github.com/{REPOSITORY}/issues/2#issuecomment-5928626235'
EXECUTION_FREEZE = f'https://github.com/{REPOSITORY}/issues/2#issuecomment-5929472507'
CONTROL_ARRAY_SHA256 = 'a4d2d06e5592caa35c03d00337d0254c07f767d5cb8ee0777cbb51f543803021'
CONTROL_WINS = 45
MIN_NET_WINS = 8
CLASSIFICATION = 'equipment_opportunity_tie_development_no_advancement'
ADVANCED_CLASSIFICATION = 'equipment_opportunity_tie_development_advanced'
RULESET, SETUP_ID, SETUP = g.RULESET, g.SETUP_ID, g.SETUP
SEEDS = range(1000000, 1000400)
PASSES = (1, 2, 3)
MAX_STEPS = 1000
# These are safety limits, not outcome/size predictions. 1.5 GiB uncompressed
# traces fit comfortably; never silently increase a limit on suspect evidence.
MIB = 1024**2
MAX_ARCHIVE = 4 * 1024**3 - 1
MAX_EXPANSION = 16 * 1024**3
MAX_TRACE = 64 * MIB
MAX_LINE = 8 * MIB
MAX_RECEIPT = 2 * MIB
MAX_RAW = 512 * 1024
MAX_JOURNAL = 256 * MIB
MAX_METADATA = 4 * MIB
CHUNK = 1024 * 1024
COMMON = 'public_observation_sha256 chosen_move rng_before_sha256 rng_after_sha256'
CANDIDATE_FIELDS = COMMON + ' legal_move_count primary_tier primary_tier_sha256 primary_score eligible_collect_tier collection_opportunities opportunity_null_is_lowest narrowed_tier narrowed_tier_sha256 narrowed_tier_count strict_narrowing'


def hash_json(value):
    return hashlib.sha256(canonical(value, newline=True)).hexdigest()


def validate_pins():
    integer(RUN_ID, 1, 10**15, 'frozen run ID')
    same(RUN_ATTEMPT, 1, 'frozen first attempt')
    for name in ('HEAD', 'EXECUTION_TREE', 'ACCEPTED_MAIN', 'ACCEPTED_TREE', 'CANDIDATE_BLOB', 'HARNESS_BLOB',
                 'SOURCE_MAP_SHA256', 'CANDIDATE_SHA256', 'HARNESS_SHA256', 'CONTROL_ARRAY_SHA256'):
        value = globals()[name]
        length = 64 if 'SHA256' in name else 40
        require(type(value) is str and re.fullmatch('[0-9a-f]{%d}' % length, value)
                and value != '0' * length, 'missing/invalid independent freeze: ' + name)
    load_geometry()  # Detect dependency mutation after module import as well.


def hash_shape(value, label, maximum):
    keys(value, 'sha256 size_bytes', label)
    require(type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']), label + ': hash')
    integer(value['size_bytes'], 1, maximum, label + ': bytes')


def hash_stream(stream, limit):
    digest, size = hashlib.sha256(), 0
    while True:
        part = stream.read(min(CHUNK, limit - size + 1))
        if not part:
            break
        size += len(part)
        require(size <= limit, 'stream exceeds byte bound')
        digest.update(part)
    return {'sha256': digest.hexdigest(), 'size_bytes': size}


def read_json(path, limit=MAX_METADATA):
    require(path.stat().st_size <= limit, 'JSON input exceeds byte bound')
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    require(len(data) <= limit, 'JSON input exceeds byte bound')
    return strict_json(data)


def validate_metadata(metadata, inventory):
    keys(metadata, 'run job artifact execution_commit', 'metadata')
    run, job, artifact, commit = (metadata[k] for k in ('run', 'job', 'artifact', 'execution_commit'))
    require(all(type(x) is dict for x in (run, job, artifact, commit)), 'metadata objects')
    same(commit.get('sha'), HEAD, 'authenticated execution commit')
    same(commit.get('tree', {}).get('sha'), EXECUTION_TREE, 'authenticated execution tree')
    for value, label in ((run, 'run'), (job, 'job')):
        for key, expected in [('status', 'completed'), ('conclusion', 'success'), ('head_sha', HEAD)]:
            same(value.get(key), expected, f'authoritative {label} {key}')
        same(value.get('run_attempt'), RUN_ATTEMPT, f'authoritative {label} attempt')
    for key, expected in [('id', RUN_ID), ('event', 'pull_request'),
                          ('path', '.github/workflows/equipment-opportunity-development.yml'),
                          ('head_branch', 'research/worker31-equipment-opportunity')]:
        same(run.get(key), expected, 'authoritative run ' + key)
    for key in ('repository', 'head_repository'):
        same(run.get(key, {}).get('full_name'), REPOSITORY, 'run ' + key)
    same(job.get('run_id'), RUN_ID, 'job run ID')
    integer(job.get('id'), 1, 10**15, 'job ID')
    same(job.get('name'), 'development', 'job name')
    same(job.get('runner_name'), 'bandido-alcatraz-ci', 'runner')
    labels = job.get('labels')
    require(type(labels) is list and all(type(x) is str for x in labels), 'runner labels')
    require({'self-hosted', 'Linux', 'X64', 'bandido-alcatraz-ci'} <= set(labels), 'runner labels')
    steps = job.get('steps')
    require(type(steps) is list and steps, 'job steps missing')
    names = []
    for step in steps:
        require(type(step) is dict and type(step.get('name')) is str, 'malformed job step')
        same(step.get('status'), 'completed', 'unfinished job step')
        same(step.get('conclusion'), 'success', 'unsuccessful job step')
        names.append(step['name'])
    required = ['Initialize evidence before dependencies and tests', 'Worker31 focused synthetic tests',
                'Three complete fixed development phases', 'Reconcile final status', 'Run actions/upload-artifact@v4']
    require(all(names.count(n) == 1 for n in required), 'missing/duplicate required job steps')
    require([names.index(n) for n in required] == sorted(names.index(n) for n in required), 'job step order')
    same(artifact.get('id'), inventory['artifact_id'], 'artifact ID')
    same(artifact.get('name'), f'worker31-equipment-opportunity-{RUN_ID}-{RUN_ATTEMPT}', 'artifact name')
    same(artifact.get('expired'), False, 'expired artifact')
    same(artifact.get('size_in_bytes'), inventory['archive']['size_bytes'], 'artifact bytes')
    same(artifact.get('digest'), 'sha256:' + inventory['archive']['sha256'], 'artifact SHA256')
    same(artifact.get('workflow_run', {}).get('id'), RUN_ID, 'artifact run')
    same(artifact.get('workflow_run', {}).get('head_sha'), HEAD, 'artifact head')


class Archive:
    """One open file descriptor; hash before parsing; bounded central directory.

    ZIP64 is deliberately unsupported: the population is only 2402 files and
    each file <=256 MiB. Compressed archives <4 GiB suffice for the declared
    legitimate input envelope. No extraction, global bytes object or read-all.
    """
    def __init__(self, path, inventory):
        self.path, self.inventory, self.stream, self.zip = path, inventory, None, None

    def __enter__(self):
        keys(self.inventory, 'schema artifact_id archive receipt journal', 'inventory')
        same(self.inventory['schema'], 'worker31-artifact-inventory-v1', 'inventory schema')
        integer(self.inventory['artifact_id'], 1, 10**15, 'artifact ID')
        for key, bound in [('archive', MAX_ARCHIVE), ('receipt', MAX_RECEIPT), ('journal', MAX_JOURNAL)]:
            hash_shape(self.inventory[key], key, bound)
        try:
            self.stream = self.path.open('rb')
            same(hash_stream(self.stream, MAX_ARCHIVE), self.inventory['archive'], 'archive SHA256/size')
            size = self.inventory['archive']['size_bytes']
            self.stream.seek(max(0, size - 65557))
            tail = self.stream.read(65557)
            marker = tail.rfind(b'PK\x05\x06')
            require(marker >= 0 and len(tail) - marker >= 22, 'ZIP end directory missing')
            end = tail[marker:]
            sig, disk, cd_disk, count_disk, count, cd_size, cd_offset, comment_len = struct.unpack('<4s4H2LH', end[:22])
            require(disk == cd_disk == 0 and count_disk == count, 'split ZIP unsupported')
            require(count <= 2410 and cd_size <= 2 * MIB, 'ZIP directory exceeds closed population bound')
            require(len(end) == 22 + comment_len, 'trailing/ambiguous ZIP bytes')
            require(cd_offset + cd_size == size - len(end), 'ZIP64/prefixed/ambiguous directory rejected')
            self.stream.seek(0)
            self.zip = zipfile.ZipFile(self.stream)
            infos = self.zip.infolist()
            require(len(infos) == count, 'ZIP directory count')
            names = [i.filename for i in infos]
            require(len(names) == len(set(names)), 'duplicate ZIP members')
            offsets = [i.header_offset for i in infos]
            require(offsets and min(offsets) == 0 and len(offsets) == len(set(offsets))
                    and all(0 <= offset < cd_offset for offset in offsets), 'prefixed/aliased ZIP local headers')
            files = {'receipt.json', 'completed.jsonl'} | {f'{kind}/pass-{p}/{s}.{suffix}'
                for kind, suffix in [('raw-results', 'json'), ('decision-traces', 'jsonl')]
                for p in PASSES for s in SEEDS}
            directories = {kind + '/' for kind in ('raw-results', 'decision-traces')} | {
                f'{kind}/pass-{p}/' for kind in ('raw-results', 'decision-traces') for p in PASSES}
            require(sum(i.file_size for i in infos) <= MAX_EXPANSION, 'ZIP expansion bound')
            for info in infos:
                mode = stat.S_IFMT(info.external_attr >> 16)
                require(info.orig_filename == info.filename, 'ambiguous member name')
                require(mode in (0, stat.S_IFREG, stat.S_IFDIR), 'nonregular member')
                require(not info.flag_bits & 1, 'encrypted member')
                require(info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), 'unsupported ZIP compression')
                if info.is_dir():
                    require(info.filename in directories and info.file_size == 0, 'unexpected ZIP directory')
                else:
                    require(info.filename in files and mode != stat.S_IFDIR, 'unexpected ZIP member')
                    bound = MAX_RECEIPT if info.filename == 'receipt.json' else MAX_JOURNAL if info.filename == 'completed.jsonl' else MAX_RAW if info.filename.startswith('raw-results/') else MAX_TRACE
                    integer(info.file_size, 1, bound, 'member byte bound')
            require({i.filename for i in infos if not i.is_dir()} == files, 'incomplete ZIP population')
            for key, filename, bound in [('receipt', 'receipt.json', MAX_RECEIPT), ('journal', 'completed.jsonl', MAX_JOURNAL)]:
                with self.zip.open(filename) as stream:
                    same(hash_stream(stream, bound), self.inventory[key], key + ' SHA256/size')
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *unused):
        if self.zip is not None:
            self.zip.close()
        if self.stream is not None:
            self.stream.close()

    def json(self, name, bound):
        with self.zip.open(name) as stream:
            raw = stream.read(bound + 1)
        require(len(raw) <= bound, 'member byte bound')
        value = strict_json(raw)
        require(raw == canonical(value, newline=True), 'noncanonical JSON bytes: ' + name)
        return value

    def lines(self, name, limit):
        with self.zip.open(name) as stream:
            total = 0
            while True:
                raw = stream.readline(MAX_LINE + 1)
                if not raw:
                    break
                total += len(raw)
                require(total <= limit and len(raw) <= MAX_LINE, 'JSONL byte bound')
                require(raw.endswith(b'\n') and raw.strip(), 'partial/empty JSONL line')
                value = strict_json(raw)
                require(raw == canonical(value, newline=True), 'noncanonical JSONL bytes')
                yield value, raw

    def equal_members(self, left, right):
        same(self.zip.getinfo(left).file_size, self.zip.getinfo(right).file_size, 'candidate/replay trace bytes differ')
        with self.zip.open(left) as a, self.zip.open(right) as b:
            while True:
                x, y = a.read(CHUNK), b.read(CHUNK)
                require(x == y, 'candidate/replay trace bytes differ')
                if not x:
                    return


def validate_receipt(receipt, source):
    require(type(receipt) is dict and type(receipt.get('source_before')) is dict, 'receipt schema')
    version = receipt['source_before'].get('python_version')
    require(type(version) is str and re.fullmatch(r'3\.11\.(0|[1-9][0-9]*)', version), 'CPython 3.11 runtime')
    snapshot = {'head': HEAD, 'harness_blob': HARNESS_BLOB, 'harness_sha256': HARNESS_SHA256,
        'source_blobs': source, 'candidate_blob': CANDIDATE_BLOB, 'candidate_sha256': CANDIDATE_SHA256,
        'python_implementation': 'CPython', 'python_version': version}
    expected = {'schema': 'bandido-equipment-opportunity-development-v1', 'expected_head': HEAD,
        'preregistration_url': PREREGISTRATION, 'audit_clarification_url': AUDIT_CLARIFICATION,
        'run_id': str(RUN_ID), 'run_attempt': str(RUN_ATTEMPT), 'accepted_main': ACCEPTED_MAIN,
        'accepted_tree': ACCEPTED_TREE, 'worker': 31, 'ruleset_id': RULESET, 'setup_id': SETUP_ID,
        'setup': SETUP, 'policy': {'class': 'BoundedMergeV4Policy', 'setup_weight': 250},
        'max_steps': MAX_STEPS, 'seed_start': SEEDS.start, 'seed_end': SEEDS.stop - 1,
        'population': len(SEEDS), 'passes': list(PASSES),
        'phases': {'1': 'v4_control', '2': 'candidate', '3': 'candidate_replay'},
        'candidate': {'class': 'EquipmentOpportunityTiePolicy', 'module': CANDIDATE_PATH},
        'control_array_sha256': CONTROL_ARRAY_SHA256, 'min_net_wins': MIN_NET_WINS,
        'fresh_seeds_used': False, 'status': 'complete', 'research_interpretation_performed': True,
        'attempted': [{'pass': p, 'seed': s} for p in PASSES for s in SEEDS], 'current': None,
        'completed_records': 3 * len(SEEDS), 'errors': [], 'source_before': snapshot,
        'source_after': snapshot, 'source_at_finalization': snapshot,
        'last_durable_completed_records': 3 * len(SEEDS), 'observed_journal_records': 3 * len(SEEDS),
        'step_outcomes': {'tests': 'success', 'cohort': 'success'}}
    keys(receipt, ' '.join(expected) + ' source_at_initialization classification summary', 'receipt')
    for key, value in expected.items():
        same(receipt[key], value, 'receipt ' + key)
    initial = receipt['source_at_initialization']
    keys(initial, ' '.join(snapshot), 'initial source snapshot')
    for key, value in snapshot.items():
        if key not in ('python_implementation', 'python_version'):
            same(initial[key], value, 'initial source ' + key)
    # Initialization precedes actions/setup-python; its runtime is recorded, not
    # falsely forced to the research interpreter installed by the next step.
    require(type(initial['python_implementation']) is str and initial['python_implementation'], 'initial implementation')
    require(type(initial['python_version']) is str and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', initial['python_version']), 'initial runtime version')


def card_schema(card, cards):
    keys(card, 'card_id material is_exit cells', 'public card')
    identity = card['card_id']
    require(type(identity) is str and identity in cards and identity != 'start_easy', 'public card identity')
    same(card, {'card_id': identity, 'material': cards[identity]['material'], 'is_exit': identity == 'exit',
                'cells': cards[identity]['cells']}, 'public card vs pinned physical card')


def public_record(observation, seed, cards):
    keys(observation, 'board hand raincoats ropes exit_placed exit_seen turns set_aside_unplayable collected_equipment setup player_index', 'public observation')
    keys(observation['board'], 'placements cells', 'public board')
    same(observation['setup'], SETUP, 'public setup')
    same(observation['player_index'], 0, 'public player')
    integer(observation['turns'], 0, 69, 'public turns')
    integer(observation['set_aside_unplayable'], 0, 69, 'public set-aside count')
    require(type(observation['exit_seen']) is bool, 'exit_seen boolean')
    collected = observation['collected_equipment']
    require(type(collected) is list and len(collected) <= 5, 'public collection list')
    out = []
    for index, item in enumerate(collected, 1):
        keys(item, 'card turn player_index', 'public collection')
        card_schema(item['card'], cards)
        out.append({'order': index, 'card_id': item['card']['card_id'], 'material': item['card']['material'],
                    'turn': item['turn'], 'player_index': item['player_index'], 'cells': item['card']['cells']})
    visible = g.validate_cells(observation['board']['cells'])
    opens = sum(edge in cell['tunnel_edges'] for (x, y), cell in visible.items()
        for edge, (dx, dy) in g.DELTAS.items() if (x + dx, y + dy) not in visible)
    water = sum(cell['water'] for cell in visible.values())
    won = observation['exit_placed'] and opens == water == 0 and observation['raincoats'] == 3 and observation['ropes'] == 2
    record = {'seed': seed, 'setup': observation['setup'], 'collected_equipment': out,
        'board': {'placements': observation['board']['placements'], 'visible_cells': observation['board']['cells']},
        'result': {key: observation[key] for key in ('turns', 'raincoats', 'ropes', 'exit_placed')}}
    record['result'].update(won=bool(won), open_tunnels=opens, visible_water_cells=water,
        reason='win' if won else 'closed_tunnels_conditions_failed' if opens == 0 else 'no_legal_move',
        ruleset_id=RULESET, setup_id=SETUP_ID)
    g.validate_record(record, seed, cards)
    hand = observation['hand']
    require(type(hand) is list and 1 <= len(hand) <= SETUP['hand_size'], 'public hand size')
    used = {p['card_id'] for p in record['board']['placements']} | {c['card_id'] for c in out}
    hand_ids = []
    for card in hand:
        card_schema(card, cards)
        require(card['card_id'] not in used, 'public hand reuses consumed card')
        hand_ids.append(card['card_id'])
    require(len(set(hand_ids)) == len(hand_ids), 'duplicate hand card')
    require(not (observation['exit_placed'] or 'exit' in hand_ids) or observation['exit_seen'], 'EXIT observation consistency')
    require(len(used) - 1 + len(hand) + observation['set_aside_unplayable'] <= 69, 'public card population')
    return record


def move_schema(move, hand):
    if move is None:
        return
    keys(move, 'action hand_index origin quarter_turns', 'public move')
    require(type(move['action']) is str and move['action'] in ('place', 'collect'), 'move action')
    integer(move['hand_index'], 0, len(hand) - 1, 'move index')
    integer(move['quarter_turns'], 0, 3, 'move rotation')
    if move['action'] == 'collect':
        same(move['origin'], None, 'collect origin')
        same(move['quarter_turns'], 0, 'collect rotation')
        require(hand[move['hand_index']]['material'] in ('raincoat', 'rope'), 'non-equipment collect')
    else:
        g.coordinate(move['origin'])


def trace_counts_schema(value):
    keys(value, 'decision_count non_null_choices', 'trace counts')
    integer(value['decision_count'], 0, MAX_STEPS, 'decision count')
    integer(value['non_null_choices'], 0, min(69, value['decision_count']), 'non-null choices')


def visible_identity(record):
    return {'board': record['board'], 'collected_equipment': record['collected_equipment'],
            'turns': record['result']['turns']}


def post_choice(record, move, hand, cards):
    # Reconstruct only the exposed placement/collection transition. This is not
    # an engine replay, legal-move enumeration or score recomputation.
    expected = strict_json(canonical(visible_identity(record)))
    if move is None:
        return expected
    card = hand[move['hand_index']]
    expected['turns'] += 1
    if move['action'] == 'collect':
        expected['collected_equipment'].append({'order': len(expected['collected_equipment']) + 1,
            'card_id': card['card_id'], 'material': card['material'], 'turn': expected['turns'],
            'player_index': 0, 'cells': card['cells']})
    else:
        board = expected['board']
        visible = {(c['x'], c['y']): c for c in board['visible_cells']}
        geometry = g.physical_placement(cards[card['card_id']], move['quarter_turns'], move['origin'])
        overlap = sorted(set(visible) & set(geometry))
        require(len(overlap) <= 1, 'choice overlaps multiple cells')
        owner = None
        if overlap:
            require(visible[overlap[0]]['water'], 'choice covers non-water cell')
            same(geometry[overlap[0]]['tunnel_edges'], visible[overlap[0]]['tunnel_edges'],
                 'water cover changes tunnel pattern')
            owner = next(p['placement_index'] for p in reversed(board['placements']) if list(overlap[0]) in p['cells'])
        attached = bool(overlap)
        for (x, y), cell in geometry.items():
            for edge, (dx, dy) in g.DELTAS.items():
                point = (x + dx, y + dy)
                neighbor = geometry.get(point, visible.get(point))
                if neighbor is None:
                    continue
                has_tunnel = edge in cell['tunnel_edges']
                same(has_tunnel, g.OPPOSITE[edge] in neighbor['tunnel_edges'],
                     'chosen placement tunnel adjacency')
                if point not in geometry and has_tunnel:
                    attached = True
        require(attached, 'chosen placement disconnected from visible tunnels')
        board['placements'].append({'card_id': card['card_id'], 'origin': move['origin'],
            'quarter_turns': move['quarter_turns'], 'placement_index': len(board['placements']),
            'kind': 'exit' if card['is_exit'] else 'ordinary', 'cells': [list(p) for p in sorted(geometry)],
            'overlaps': [list(p) for p in overlap], 'covered_placement_index': owner})
        visible.update(geometry)
        board['visible_cells'] = [visible[p] for p in sorted(visible)]
    return expected


def validate_audit(audit, started, hand, pass_number):
    keys(audit, COMMON if pass_number == 1 else CANDIDATE_FIELDS, 'audit (private/unknown fields forbidden)')
    same(audit['public_observation_sha256'], hash_json(started['observation']), 'observation digest')
    same(audit['rng_before_sha256'], started['rng_before_sha256'], 'RNG before digest')
    for key in ('public_observation_sha256', 'rng_before_sha256', 'rng_after_sha256'):
        require(type(audit[key]) is str and re.fullmatch('[0-9a-f]{64}', audit[key]), 'invalid trace hash')
    move_schema(audit['chosen_move'], hand)
    if audit['chosen_move'] is None:
        same(audit['rng_before_sha256'], audit['rng_after_sha256'], 'null decision consumed RNG')
    else:
        require(audit['rng_before_sha256'] != audit['rng_after_sha256'], 'non-null choice did not advance RNG hash')
    if pass_number == 1:
        return 0
    primary, narrowed = audit['primary_tier'], audit['narrowed_tier']
    require(type(primary) is list and type(narrowed) is list, 'tier arrays')
    integer(audit['legal_move_count'], len(primary), 100000, 'legal move count')
    integer(audit['narrowed_tier_count'], 0, len(primary), 'narrowed tier count')
    same(audit['narrowed_tier_count'], len(narrowed), 'narrowed tier length')
    same(audit['primary_tier_sha256'], hash_json(primary), 'primary tier digest')
    same(audit['narrowed_tier_sha256'], hash_json(narrowed), 'narrowed tier digest')
    for tier in (primary, narrowed):
        require(len({canonical(m) for m in tier}) == len(tier), 'duplicate tier move')
        for move in tier:
            require(move is not None, 'null tier move')
            move_schema(move, hand)
    eligible = bool(primary) and all(m['action'] == 'collect' for m in primary)
    same(audit['eligible_collect_tier'], eligible, 'collect eligibility')
    same(audit['opportunity_null_is_lowest'], True, 'null opportunity ordering')
    opportunities = audit['collection_opportunities']
    require(type(opportunities) is list, 'opportunity array')
    if eligible:
        same(len(opportunities), len(primary), 'opportunity count')
        scores = []
        for move, item in zip(primary, opportunities):
            keys(item, 'hand_index card_id opportunity_score', 'opportunity')
            same(item['hand_index'], move['hand_index'], 'opportunity index')
            same(item['card_id'], hand[move['hand_index']]['card_id'], 'opportunity card')
            score = item['opportunity_score']
            require(score is None or type(score) is int, 'opportunity score')
            scores.append((score is not None, score if score is not None else 0))
        expected = [m for m, score in zip(primary, scores) if score == min(scores)]
    else:
        same(opportunities, [], 'opportunities outside collect tier')
        expected = primary
    same(narrowed, expected, 'frozen narrowed-tier rule')
    strict = len(narrowed) < len(primary)
    same(audit['strict_narrowing'], strict, 'strict narrowing flag')
    require(any(canonical(audit['chosen_move']) == canonical(m) for m in narrowed) if narrowed
            else audit['chosen_move'] is None, 'chosen move outside final tier')
    if primary:
        require(type(audit['primary_score']) is int, 'primary score integer')
    else:
        same(audit['primary_score'], None, 'empty primary score')
        same(audit['legal_move_count'], 0, 'empty tier hid legal moves')
    return int(strict)



def validate_public_progression(previous, chosen, observation):
    """Check public hand/aside transitions without opening any hidden zone."""
    if previous is None:
        same(len(observation['hand']), SETUP['hand_size'], 'initial hand population')
        same(observation['set_aside_unplayable'], 0, 'initial set-aside count')
        same(observation['exit_seen'], any(c['is_exit'] for c in observation['hand']), 'initial EXIT seen')
        return
    old_hand, new_hand = previous['hand'], observation['hand']
    consumed = len(previous['board']['placements']) - 1 + len(previous['collected_equipment'])
    remaining = 69 - consumed - len(old_hand) - previous['set_aside_unplayable']
    if chosen is not None:
        kept = old_hand[:chosen['hand_index']] + old_hand[chosen['hand_index'] + 1:]
        same(len(new_hand), len(kept) + int(remaining > 0), 'post-action hand population')
        same(new_hand[:len(kept)], kept, 'post-action ordered hand remainder')
        same(observation['set_aside_unplayable'], previous['set_aside_unplayable'], 'action changed set-aside count')
    else:
        require(old_hand and remaining > 0, 'decision after impossible null refresh')
        require(not ({c['card_id'] for c in old_hand} & {c['card_id'] for c in new_hand}),
                'refresh retained old hand card')
        same(len(new_hand), min(len(old_hand), remaining), 'refreshed hand population')
        expected_aside = previous['set_aside_unplayable'] + (len(old_hand) if remaining <= len(old_hand) else 0)
        same(observation['set_aside_unplayable'], expected_aside, 'refresh set-aside count')
    same(observation['exit_seen'], previous['exit_seen'] or any(c['is_exit'] for c in new_hand),
         'public EXIT seen progression')


def trace_name(pass_number, seed):
    return f'decision-traces/pass-{pass_number}/{seed}.jsonl'


def control_contexts(archive, seed):
    # Called only after the entire control trace passed its independent gate.
    for event, unused in archive.lines(trace_name(1, seed), MAX_TRACE):
        if event['event'] == 'decision_completed':
            yield event['audit']


def validate_trace(archive, record, pass_number, cards):
    events = iter(archive.lines(trace_name(pass_number, record['seed']), MAX_TRACE))
    count = actions = strict = comparable = differing = 0
    prior_rng = expected_visible = previous_observation = last_choice = None
    control = iter(control_contexts(archive, record['seed'])) if pass_number == 2 else None
    previous_seen = False
    previous_aside = 0
    for started, unused in events:
        if started.get('event') == 'game_returned':
            same(started, {'event': 'game_returned', 'result': record['result']}, 'trace result')
            completion, unused = next(events, (None, None))
            keys(completion, 'event record_sha256 trace_counts', 'game completion')
            same(completion['event'], 'game_completed', 'trace terminal event')
            same(completion['record_sha256'], hash_json(record), 'trace record hash')
            trace_counts_schema(completion['trace_counts'])
            counts = {'decision_count': count, 'non_null_choices': actions}
            same(completion['trace_counts'], counts, 'durable trace counts')
            same(actions, record['result']['turns'], 'action count vs final turns')
            require(count > 0, 'fixed setup requires an initial decision')
            if record['result']['reason'] == 'no_legal_move':
                require(last_choice is None, 'no_legal_move must follow a null choice')
                consumed = len(previous_observation['board']['placements']) - 1 + len(previous_observation['collected_equipment'])
                remaining = 69 - consumed - len(previous_observation['hand']) - previous_observation['set_aside_unplayable']
                require(remaining == 0 or remaining > len(previous_observation['hand']),
                        'terminal null choice skipped mandatory short-pile refresh')
            require(count < MAX_STEPS or last_choice is None, 'last step action must return forbidden step_limit')
            if record['result']['reason'] == 'deck_exhausted':
                require(last_choice is not None and len(previous_observation['hand']) == 1,
                        'deck_exhausted requires final single-card action')
                consumed = len(previous_observation['board']['placements']) - 1 + len(previous_observation['collected_equipment'])
                same(consumed + len(previous_observation['hand']) + previous_observation['set_aside_unplayable'],
                     69, 'deck_exhausted requires no draw cards')
            if expected_visible is not None:
                same(visible_identity(record), expected_visible, 'final record vs last public choice')
            require(next(events, None) is None, 'events after terminal completion')
            # Drain the verified-control reader to close its ZIP handle/CRC check.
            if control is not None:
                for ignored in control:
                    pass
            return counts, strict, comparable, differing
        count += 1
        integer(count, 1, MAX_STEPS, 'decision count bound')
        keys(started, 'event ordinal observation rng_before_sha256', 'decision start')
        same(started['event'], 'decision_started', 'decision start kind')
        same(started['ordinal'], count, 'decision start ordinal')
        observation = started['observation']
        observed_record = public_record(observation, record['seed'], cards)
        require(not observed_record['result']['won'] and observed_record['result']['open_tunnels'] > 0,
                'decision after observable terminal state')
        same(observation['turns'], actions, 'observed turn progression')
        validate_public_progression(previous_observation, last_choice, observation)
        require(not previous_seen or observation['exit_seen'], 'EXIT seen regressed')
        require(observation['set_aside_unplayable'] >= previous_aside, 'set-aside count regressed')
        previous_seen, previous_aside = observation['exit_seen'], observation['set_aside_unplayable']
        if expected_visible is not None:
            same(visible_identity(observed_record), expected_visible, 'public transition vs prior choice')
        completed, unused = next(events, (None, None))
        keys(completed, 'event ordinal audit', 'decision completion')
        same(completed['event'], 'decision_completed', 'decision completion kind')
        same(completed['ordinal'], count, 'decision completion ordinal')
        audit = completed['audit']
        strict += validate_audit(audit, started, observation['hand'], pass_number)
        if prior_rng is not None:
            same(audit['rng_before_sha256'], prior_rng, 'RNG hash chain')
        prior_rng = audit['rng_after_sha256']
        last_choice = audit['chosen_move']
        expected_visible = post_choice(observed_record, last_choice, observation['hand'], cards)
        actions += audit['chosen_move'] is not None
        previous_observation = observation
        if control is not None:
            other = next(control, None)
            if count == 1:
                require(other is not None, 'missing initial control decision')
                same([audit['public_observation_sha256'], audit['rng_before_sha256']],
                     [other['public_observation_sha256'], other['rng_before_sha256']],
                     'control/candidate initial public context')
            if other is not None and (other['public_observation_sha256'], other['rng_before_sha256']) == (audit['public_observation_sha256'], audit['rng_before_sha256']):
                comparable += 1
                differing += canonical(other['chosen_move']) != canonical(audit['chosen_move'])
    raise Rejected('trace missing terminal returned/completed events')


def summarize(control, candidate, failures, control_hash, candidate_hash, trace_summary):
    wins, base, all_seeds = set(candidate), set(control), set(SEEDS)
    gained, lost = wins - base, base - wins
    net = len(wins) - len(base)
    return {'games_per_pass': len(SEEDS), 'matching_records': len(SEEDS), 'quota_overshoots': 0,
        'control_wins': len(base), 'wins': len(wins), 'win_rate': len(wins) / len(SEEDS),
        'winning_seed_ids': sorted(wins), 'net_wins': net, 'min_net_wins': MIN_NET_WINS,
        'classification': ADVANCED_CLASSIFICATION if net >= MIN_NET_WINS else CLASSIFICATION,
        'paired_2x2': {'both_win': len(wins & base), 'control_only': len(lost), 'candidate_only': len(gained),
                       'both_lose': len(all_seeds - (wins | base))},
        'gained_seed_ids': sorted(gained), 'lost_seed_ids': sorted(lost), 'shared_win_seed_ids': sorted(wins & base),
        'both_loss_seed_ids': sorted(all_seeds - (wins | base)), 'candidate_loss_seed_ids': sorted(all_seeds - wins),
        'control_loss_seed_ids': sorted(all_seeds - base), 'failure_reasons': dict(sorted(failures.items())),
        'interpretation': 'Spent development screen only; next validation requires separate preregistration',
        'normalized_control_sha256': control_hash, 'normalized_candidate_sha256': candidate_hash,
        'trace_summary': trace_summary}


def verify(path, inventory, metadata, source, data_dir):
    validate_pins()
    same(hashlib.sha256(canonical(source)).hexdigest(), SOURCE_MAP_SHA256, 'accepted source map fingerprint')
    # Keep the helper's map pin immutable in production, explicit monkeypatches
    # for a synthetic deck occur only in tests.
    cards = g.load_cards(data_dir, source)
    with Archive(path, inventory) as archive:
        validate_metadata(metadata, inventory)
        receipt = archive.json('receipt.json', MAX_RECEIPT)
        validate_receipt(receipt, source)
        wins = {1: [], 2: [], 3: []}
        failures = Counter()
        hashes = {p: hashlib.sha256(b'[') for p in PASSES}
        traces = {'candidate_strict_tier_narrowings': 0, 'matched_observation_rng_decisions': 0,
                  'selected_action_differences_in_matched_contexts': 0, 'candidate_replay_trace_matches': len(SEEDS),
                  'action_difference_scope': 'same seed and ordinal with identical public observation and pre-choice RNG hashes'}
        rows = iter(archive.lines('completed.jsonl', MAX_JOURNAL))
        for p in PASSES:
            for position, seed in enumerate(SEEDS):
                row, unused = next(rows, (None, None))
                keys(row, 'pass record', 'journal envelope')
                same(row['pass'], p, 'journal pass ordering')
                record = row['record']
                g.validate_record(record, seed, cards)
                raw = archive.json(f'raw-results/pass-{p}/{seed}.json', MAX_RAW)
                keys(raw, 'pass seed result public_capture_count public_captures trace_counts', 'raw sidecar')
                trace_counts_schema(raw['trace_counts'])
                same(raw, {'pass': p, 'seed': seed, 'result': record['result'], 'public_capture_count': 1,
                           'public_captures': [record], 'trace_counts': raw['trace_counts']}, 'raw sidecar discrepancy')
                record_bytes = canonical(record)
                if position:
                    hashes[p].update(b',')
                hashes[p].update(record_bytes)
                if p == 2:
                    archive.equal_members(trace_name(2, seed), trace_name(3, seed))
                elif p == 3:
                    peer = archive.json(f'raw-results/pass-2/{seed}.json', MAX_RAW)
                    require(record_bytes == canonical(peer['public_captures'][0]),
                            'candidate/replay record byte identity')
                counts, strict, comparable, differing = validate_trace(archive, record, p, cards)
                same(raw['trace_counts'], counts, 'raw/trace counts')
                if p == 2:
                    traces['candidate_strict_tier_narrowings'] += strict
                    traces['matched_observation_rng_decisions'] += comparable
                    traces['selected_action_differences_in_matched_contexts'] += differing
                    if not record['result']['won']:
                        failures[record['result']['reason']] += 1
                if record['result']['won']:
                    wins[p].append(seed)
            hashes[p].update(b']\n')
            if p == 1:
                same(hashes[1].hexdigest(), CONTROL_ARRAY_SHA256, 'control full-array Worker30 fingerprint')
                same(len(wins[1]), CONTROL_WINS, 'control Worker30 win count')
        require(next(rows, None) is None, 'extra journal records')
        same(hashes[2].hexdigest(), hashes[3].hexdigest(), 'candidate/replay normalized array')
        summary = summarize(wins[1], wins[2], failures, hashes[1].hexdigest(), hashes[2].hexdigest(), traces)
        same(receipt['summary'], summary, 'producer summary vs independent recomputation')
        same(receipt['classification'], summary['classification'], 'producer classification')
        return {'verified': True, 'classification': summary['classification'], 'worker': 31,
            'run_id': RUN_ID, 'run_attempt': RUN_ATTEMPT, 'head': HEAD, 'execution_tree': EXECUTION_TREE,
            'accepted_main': ACCEPTED_MAIN, 'accepted_tree': ACCEPTED_TREE, 'source_map_sha256': SOURCE_MAP_SHA256,
            'candidate_blob': CANDIDATE_BLOB, 'candidate_sha256': CANDIDATE_SHA256, 'harness_blob': HARNESS_BLOB,
            'harness_sha256': HARNESS_SHA256, 'geometry_helper_sha256': HELPER_SHA256,
            'runtime': {k: receipt['source_before'][k] for k in ('python_implementation', 'python_version')},
            'preregistration_url': PREREGISTRATION, 'audit_clarification_url': AUDIT_CLARIFICATION,
            'execution_freeze_url': EXECUTION_FREEZE, 'ruleset_id': RULESET, 'setup_id': SETUP_ID,
            'artifact_id': inventory['artifact_id'], 'archive': inventory['archive'], 'receipt': inventory['receipt'],
            'journal': inventory['journal'], 'verified_records': 3 * len(SEEDS), 'verified_sidecars': 3 * len(SEEDS),
            'verified_traces': 3 * len(SEEDS), 'summary': summary}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    for option in ('inventory', 'metadata', 'source-manifest', 'data-dir'):
        parser.add_argument('--' + option, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = verify(args.archive, read_json(args.inventory), read_json(args.metadata),
                        read_json(args.source_manifest), args.data_dir)
    except (ValueError, TypeError, KeyError, AttributeError, IndexError, OSError, zipfile.BadZipFile,
            RuntimeError, OverflowError, RecursionError, EOFError, StopIteration, struct.error, zlib.error, MemoryError) as error:
        print(f'REJECTED: {type(error).__name__}: {error}; inputs preserved; no research classification accepted', file=sys.stderr)
        return 1
    print(canonical(result).decode())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
