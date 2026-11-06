"""Invented persisted evidence only. No games, real observations or policy calls."""
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'verify_worker35_development.py'
spec = importlib.util.spec_from_file_location('worker35_offline_verifier_test', PATH)
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def cell(x, y, edges, water=False):
    return dict(x=x, y=y, tunnel_edges=sorted(edges), water=water)


def make_fixture():
    # Neutral invented hand, no claims about an actual cohort observation.
    cards = {'start_easy': dict(material=None, cells=[cell(0, 0, 'ES'), cell(0, 1, 'N')]),
             'exit': dict(material=None, cells=[cell(0, 0, 'SW'), cell(0, 1, 'N')])}
    for i in range(68):
        cards[f'invented-{i}'] = dict(material='raincoat' if i < 12 else 'rope' if i < 20 else None,
                                    cells=[cell(0, 0, 'SW'), cell(0, 1, 'N')])
    hand = [dict(card_id=f'invented-{i}', is_exit=False, **deepcopy(cards[f'invented-{i}']))
            for i in range(20, 26)]
    obs = dict(board=dict(cells=deepcopy(cards['start_easy']['cells']), placements=[
        dict(card_id='start_easy', origin=[0, 0], quarter_turns=0, placement_index=0,
             kind='start', cells=[[0, 0], [0, 1]], overlaps=[], covered_placement_index=None)]),
        hand=hand, raincoats=0, ropes=0, exit_placed=False, exit_seen=False, turns=0,
        set_aside_unplayable=0, collected_equipment=[], setup=deepcopy(v.SETUP), player_index=0)
    science = dict(schema='worker35-scientific-v1', input_before=v.digest(obs), input_after=v.digest(obs),
        roots=[], supply={m: dict(quota=q, collected=0, total=t, placed=0, deficit=q,
                                 available=t, own_hand=0) for m, (q, t, unused) in v.MATERIALS.items()},
        tiers=dict(T0=[], F=[], T=[], C=[], final=[]), guards=[], flags=dict.fromkeys(v.FLAGS, False),
        chosen_index=None, chosen=None, rng_before='a'*64, rng_after='a'*64)
    return cards, obs, science


def validate(science, obs, cards):
    return v.validate_science(science, obs, 'a'*64, cards, v.SEEDS.start)


def collect_fixture():
    cards, obs, science = make_fixture()
    obs['hand'][0] = dict(card_id='invented-0', is_exit=False, **deepcopy(cards['invented-0']))
    move = dict(action='collect', hand_index=0, origin=None, quarter_turns=0)
    science.update(input_before=v.digest(obs), input_after=v.digest(obs),
        roots=[dict(move=move, score=10000)], chosen=move, chosen_index=0, rng_after='b'*64,
        tiers=dict(T0=[0], F=[0], T=[0], C=[], final=[0]),
        guards=[dict(eligible=False, reason='not_place', after=None, exit_legal_count=None)])
    science['supply']['raincoat']['own_hand'] = 1
    return cards, obs, science


def test_reviewed_helpers_have_independent_exact_byte_pins():
    assert v.load_reviewed().HELPER_SHA256 == v.v31.HELPER_SHA256
    assert v.WORKER31_SHA256 == hashlib.sha256(PATH.with_name('verify_worker31_development.py').read_bytes()).hexdigest()


def test_empty_live_audit_and_no_rng_draw():
    cards, obs, science = make_fixture()
    assert not any(validate(science, obs, cards).values())
    science['rng_after'] = 'b'*64
    with pytest.raises(v.Rejected, match='consumed RNG'):
        validate(science, obs, cards)


def test_collect_singleton_requires_choice_and_supplies():
    cards, obs, science = collect_fixture()
    assert not any(validate(science, obs, cards).values())
    for key, value in [('chosen_index', True), ('chosen_index', None), ('rng_after', 'a'*64)]:
        broken = deepcopy(science)
        broken[key] = value
        with pytest.raises(v.Rejected):
            validate(broken, obs, cards)


@pytest.mark.parametrize('mutation', ['supply', 'tier', 'flags', 'input', 'score_bool', 'private', 'missing_collect', 'duplicate_root'])
def test_corrupt_science_fails_closed(mutation):
    cards, obs, science = collect_fixture()
    if mutation == 'supply':
        science['supply']['raincoat']['available'] -= 1
    elif mutation == 'tier':
        science['tiers']['F'] = []
    elif mutation == 'flags':
        science['flags']['true_original_all_collect_crossover'] = True
    elif mutation == 'input':
        science['input_after'] = '0'*64
    elif mutation == 'score_bool':
        science['roots'][0]['score'] = True
    elif mutation == 'private':
        science['draw_pile'] = []
    elif mutation == 'missing_collect':
        science['roots'] = []
    else:
        science['roots'].append(deepcopy(science['roots'][0]))
    with pytest.raises(v.Rejected):
        validate(science, obs, cards)


@pytest.mark.parametrize('mutation', ['duplicate_hand', 'material', 'count', 'hand_size', 'aside', 'terminal'])
def test_public_contract_rejects_malformed_state(mutation):
    cards, obs, science = make_fixture()
    if mutation == 'duplicate_hand':
        obs['hand'][1] = deepcopy(obs['hand'][0])
    elif mutation == 'material':
        obs['hand'][0]['material'] = 'raincoat'
    elif mutation == 'count':
        obs['raincoats'] = 1
    elif mutation == 'hand_size':
        obs['hand'].pop()
    elif mutation == 'aside':
        obs['set_aside_unplayable'] = 1
    else:
        cards['start_easy']['cells'][0]['tunnel_edges'] = ['S']
        obs['board']['cells'][0]['tunnel_edges'] = ['S']
    with pytest.raises(v.Rejected):
        v.validate_public(obs, v.SEEDS.start, cards)


def test_selected_and_unselected_root_geometry_is_checked():
    cards, obs, science = make_fixture()
    place = dict(action='place', hand_index=0, origin=[1, 0], quarter_turns=0)
    science.update(roots=[dict(move=place, score=-1000000)], chosen=place,
        chosen_index=0, rng_after='b'*64, tiers=dict(T0=[0], F=[0], T=[0], C=[], final=[0]),
        guards=[dict(eligible=False, reason='branch_not_active', after=None, exit_legal_count=None)])
    validate(science, obs, cards)
    broken = deepcopy(science)
    broken['roots'][0]['move']['origin'] = [50, 50]
    with pytest.raises(v.Rejected, match='disconnected'):
        validate(broken, obs, cards)


def test_closure_guard_prevents_immediate_closed_tunnels():
    cards, obs, science = collect_fixture()
    place = dict(action='place', hand_index=0, origin=[1, 0], quarter_turns=0)
    science['roots'].append(dict(move=place, score=-1000000))
    science['tiers']['F'] = [0, 1]
    science['guards'].append(dict(eligible=False, reason='closed_tunnels',
                                 after=[0, 0, 0, 0], exit_legal_count=None))
    validate(science, obs, cards)
    science['guards'][1]['reason'] = 'eligible'
    science['guards'][1]['eligible'] = True
    with pytest.raises(v.Rejected, match='guard'):
        validate(science, obs, cards)


def test_root_order_and_illegal_quota_collection_are_rejected():
    cards, obs, science = collect_fixture()
    science['roots'].append(dict(move=dict(action='place', hand_index=0, origin=[1, 0], quarter_turns=0), score=-1))
    science['roots'].reverse()
    with pytest.raises(v.Rejected, match='order'):
        validate(science, obs, cards)


def test_actual_costs_are_bounded_and_not_bool():
    caps = dict(legal_enumerations=10, previews=10, exit_geometry_checks=10, roots=10)
    cost = dict(legal_enumerations=3, previews=1, exit_geometry_checks=1, roots=2)
    v.validate_cost(cost, caps, 2, 'fixture')
    for key, value in [('roots', 3), ('previews', 11), ('legal_enumerations', 0), ('roots', True)]:
        broken = dict(cost, **{key: value})
        with pytest.raises(v.Rejected):
            v.validate_cost(broken, caps, 2, 'fixture')


def test_missing_execution_freeze_can_never_interpret_results():
    with pytest.raises(v.Rejected):
        v.validate_freeze({}, 'a'*64)


@pytest.fixture
def synthetic_bundle(tmp_path, monkeypatch):
    import json
    cards, obs, science = make_fixture()
    data_dir, root = tmp_path / 'data', tmp_path / 'raw'
    data_dir.mkdir()
    root.mkdir()
    documents = {'deck-v1.json': {'instances': [dict(card_id=f'invented-{i}',
        material='raincoat' if i < 12 else 'rope' if i < 20 else None,
        external_ports=['LU'], internal_bridge=True, water_half=None) for i in range(68)]},
        'deck-observations-v0.json': {'special_geometry': {
            'start_easy': {'cells': cards['start_easy']['cells']},
            'exit': {'cells': cards['exit']['cells']}}}}
    source = {f'src/synthetic-{i}.py': f'{i+1:040x}' for i in range(24)}
    for name, document in documents.items():
        raw = v.canonical(document, newline=True)
        (data_dir / name).write_bytes(raw)
        source['data/' + name] = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    source_sha = hashlib.sha256(v.canonical(source)).hexdigest()
    monkeypatch.setattr(v, 'SOURCE_MAP_SHA256', source_sha)
    monkeypatch.setattr(v.g, 'SOURCE_MAP_SHA256', source_sha)
    cards = v.g.load_cards(data_dir, source)
    obs['hand'] = [dict(card_id=f'invented-{i}', is_exit=False, **deepcopy(cards[f'invented-{i}'])) for i in range(20, 26)]
    science['input_before'] = science['input_after'] = v.digest(obs)
    required = {'src/bandido_alcatraz/quota_reserve_closure.py',
        'src/bandido_alcatraz/quota_reserve_closure_reference.py',
        'scripts/run_quota_reserve_closure_development.py', 'scripts/worker35_resources.py',
        'scripts/verify_worker35_development.py', 'scripts/verify_worker31_development.py',
        'scripts/worker31_geometry.py', 'src/bandido_alcatraz/worker32/evidence.py',
        'experiments/quota-reserve-closure-development/PROTOCOL.md',
        'experiments/quota-reserve-closure-development/AUDIT-CONTRACT.md',
        '.github/workflows/quota-reserve-closure-development.yml', 'pyproject.toml'}
    execution = {name: 'e'*64 for name in set(source) | required}
    execution['scripts/verify_worker35_development.py'] = hashlib.sha256(PATH.read_bytes()).hexdigest()
    execution['scripts/verify_worker31_development.py'] = v.WORKER31_SHA256
    execution['scripts/worker31_geometry.py'] = v.v31.HELPER_SHA256
    resources = dict(per_call={scope: dict(legal_enumerations=100, previews=100,
        exit_geometry_checks=100, roots=100, wall_seconds=10, cpu_seconds=10)
        for scope in ('control', 'candidate', 'reference')},
        total_operations=dict(legal_enumerations=10000, previews=10000, exit_geometry_checks=10000),
        cohort_wall_seconds=10000, verification_wall_seconds=10000, address_space_bytes=1024**3,
        evidence_bytes=128*1024**2, trace_bytes=1024**2, line_bytes=1024**2,
        receipt_bytes=1024**2, shard_bytes=1024**2, archive_bytes=128*1024**2)
    freeze = dict(schema='worker35-execution-freeze-v1',
        preregistration_url='https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-123',
        baseline_commit=v.MODEL_COMPARATOR, baseline_source_blobs=source,
        execution_source_sha256=execution, runtime=dict(implementation='CPython', version='3.11.16', executable_sha256='b'*64),
        resources=resources, reviews=dict.fromkeys(('candidate', 'reference', 'harness', 'independent_a', 'independent_b'), 'required-clean-exact-head-before-go'),
        synthetic_preflight_sha256='f'*64)
    freeze_sha = v.digest(freeze)
    go = dict(head='a'*40, tree='b'*40, freeze_sha256=freeze_sha,
        execution_go_url='https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-456')
    blobs = {path: source.get(path, 'c'*40) for path in execution}
    metadata = dict(run=dict(id=123, status='completed', conclusion='success', head_sha=go['head'],
        run_attempt=1, event='pull_request', path='.github/workflows/quota-reserve-closure-development.yml',
        head_branch='research/worker35-quota-reserve-closure', repository=dict(full_name=v.REPOSITORY),
        head_repository=dict(full_name=v.REPOSITORY)),
        job=dict(id=456, run_id=123, status='completed', conclusion='success', head_sha=go['head'],
            run_attempt=1, runner_name='bandido-alcatraz-ci', name='development',
            labels=['self-hosted', 'Linux', 'X64', 'bandido-alcatraz-ci'],
            steps=[dict(name=name, status='completed', conclusion='success') for name in
                ['Initialize evidence', 'Worker35 synthetic tests', 'Three complete passes', 'Reconcile status']]),
        execution_commit=dict(sha=go['head'], tree=dict(sha=go['tree'])), execution_go=go,
        execution_blobs=blobs)
    record = v.v31.public_record(obs, v.SEEDS.start, cards)
    records = [dict(record, seed=seed) for seed in v.SEEDS]
    control_sha = v.digest(records)
    monkeypatch.setattr(v, 'CONTROL_ARRAY_SHA256', control_sha)
    monkeypatch.setattr(v, 'CONTROL_WINS', 0)
    monkeypatch.setattr(v, 'CONTROL_EQUIPMENT_READY', 0)
    snapshot = dict(head=go['head'], tree=go['tree'], baseline_commit=v.MODEL_COMPARATOR,
        source_blobs=source, execution_blobs=blobs, execution_sha256=execution,
        python_implementation='CPython', python_version='3.11.16', executable_sha256='b'*64)
    receipt = dict(schema='bandido-quota-reserve-closure-development-v1', expected_head=go['head'],
        preregistration_url=freeze['preregistration_url'], audit_clarification_url=freeze['preregistration_url'],
        freeze_sha256=freeze_sha, freeze=freeze, run_id='123', run_attempt='1',
        accepted_main=v.ACCEPTED_MAIN, accepted_tree=v.ACCEPTED_TREE, worker=35,
        ruleset_id=v.RULESET, setup_id=v.SETUP_ID, setup=v.SETUP,
        policy=dict(class_='BoundedMergeV4Policy', setup_weight=250), max_steps=1000,
        seed_start=v.SEEDS.start, seed_end=v.SEEDS.stop-1, population=400, passes=[1,2,3],
        phases={'1':'v4_control','2':'candidate','3':'candidate_replay'},
        candidate={'class':'QuotaReserveClosurePolicy','module':'src/bandido_alcatraz/quota_reserve_closure.py'},
        control_array_sha256=control_sha, min_net_wins=8, fresh_seeds_used=False,
        status='complete', research_interpretation_performed=True,
        attempted=[{'pass':p,'seed':seed} for p in v.PASSES for seed in v.SEEDS], current=None,
        completed_records=1200, errors=[], last_durable_completed_records=1200, observed_journal_records=1200,
        step_outcomes=dict(tests='success',cohort='success'), classification=v.CLASSIFICATION,
        cohort_elapsed_seconds=0, verification_elapsed_seconds=0,
        **{key: snapshot for key in ('source_before','source_after','source_at_initialization','source_at_finalization')})
    receipt['policy'] = {'class':'BoundedMergeV4Policy','setup_weight':250}
    receipt['memory_limit'] = {'mechanism':'RLIMIT_AS','soft':resources['address_space_bytes'],'hard':resources['address_space_bytes']}
    receipt['total_operations'] = {'legal_enumerations':2000,'previews':0,'exit_geometry_checks':0}
    receipt['execution_go'] = go
    receipt['admission'] = {'schema':'worker35-exclusive-admission-v1','expected_head':go['head'],
        'preregistration_url':freeze['preregistration_url'],'audit_clarification_url':freeze['preregistration_url'],
        'run_id':'123','run_attempt':'1','freeze_sha256':freeze_sha,'execution_go':go}
    receipt['summary'] = v.summarize([], [], {'no_legal_move':400},
        {1:control_sha,2:control_sha,3:control_sha}, dict.fromkeys(v.FLAGS,0),
        {'control':0,'candidate':0}, {})
    receipt['summary'].update(equipment_ready={'control':0,'candidate':0},
        terminal_components={scope:{'visible_water_remaining':0,'exit_unplaced':400,'closed_tunnels_conditions_failed':0} for scope in ('control','candidate')},
        trace_summary={'mechanism_counts':dict.fromkeys(v.FLAGS,0),'matched_observation_rng_decisions':400,
            'selected_action_differences_in_matched_contexts':0,'candidate_replay_trace_matches':400,
            'action_difference_scope':'same seed and ordinal with identical public observation and pre-choice RNG hashes'})
    files = {}
    def put(name, value, lines=False):
        raw = b''.join(v.canonical(x,newline=True) for x in value) if lines else v.canonical(value,newline=True)
        path = root / name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(raw)
        files[name] = dict(sha256=hashlib.sha256(raw).hexdigest(),size_bytes=len(raw))
    boundary = dict(public_before=v.digest(obs),public_after=v.digest(obs),engine_before='d'*64,
        engine_after='d'*64,choice_calls=0,choice_tier=[],reference_choice_calls=None,reference_choice_tier=None)
    cost = dict(legal_enumerations=1,previews=0,exit_geometry_checks=0,roots=0)
    journal, metrics = [], []
    zones = dict(placed=[],collected=[],hand=sorted(c['card_id'] for c in obs['hand']),set_aside=[])
    zones['draw'] = sorted(set(cards)-{'start_easy'}-set(zones['hand']))
    conserved = dict(inventory_count=69,inventory_sha256=v.digest(sorted(set(cards)-{'start_easy'})),zones=zones)
    for p in v.PASSES:
        for rec in records:
            seed=rec['seed']
            journal.append({'pass':p,'record':rec})
            scopes=('control',) if p==1 else ('candidate','reference')
            if p==1:
                audit=dict(public_observation_sha256=v.digest(obs),chosen_move=None,rng_before_sha256='a'*64,
                    rng_after_sha256='a'*64,roots=[],final=[],cost=cost,boundary=boundary)
                calls=[dict(ordinal=1,scope='control',result=dict(chosen=None,roots=[],final=[],cost=cost))]
            else:
                audit=dict(scientific_sha256=v.digest(science),reference_scientific_sha256=v.digest(science),
                    candidate_cost=cost,reference_cost=cost,boundary=dict(boundary,reference_choice_calls=0,reference_choice_tier=[]))
                calls=[dict(ordinal=1,scope='candidate',result=dict(chosen=None,scientific=science,cost=cost)),
                    dict(ordinal=1,scope='reference',result=dict(chosen=None,scientific_sha256=v.digest(science),cost=cost))]
            counts=dict(decision_count=1,non_null_choices=0)
            events=[dict(event='decision_started',ordinal=1,observation=obs,rng_before_sha256='a'*64),
                dict(event='decision_completed',ordinal=1,audit=audit),
                dict(event='game_returned',result=rec['result']),
                dict(event='game_completed',record_sha256=v.digest(rec),trace_counts=counts)]
            put(f'decision-traces/pass-{p}/{seed}.jsonl',events,True)
            put(f'call-results/pass-{p}/{seed}.jsonl',calls,True)
            put(f'raw-results/pass-{p}/{seed}.json',dict(pass_=p,seed=seed,result=rec['result'],
                public_capture_count=1,public_captures=[rec],trace_counts=counts,
                final_public_observation=obs,conservation=conserved))
            raw=v.read_json(root/f'raw-results/pass-{p}/{seed}.json')
            raw['pass']=raw.pop('pass_')
            put(f'raw-results/pass-{p}/{seed}.json',raw)
            for scope in scopes:
                metrics.append(dict(kind='decision',**{'pass':p},seed=seed,ordinal=1,scope=scope,
                    wall_seconds=0,cpu_seconds=0,peak_rss_kib=1,cost=cost,status='returned'))
            metrics.append(dict(kind='game',**{'pass':p},seed=seed,wall_seconds=0,cpu_seconds=0,peak_rss_kib=1,status='complete',
                operations=dict(legal_enumerations=len(scopes),previews=0,exit_geometry_checks=0)))
    put('completed.jsonl',journal,True)
    put('resource-metrics.jsonl',metrics,True)
    put('receipt.json',receipt)
    import zipfile
    baseline_archive=tmp_path/'invented-historical.zip'
    with zipfile.ZipFile(baseline_archive,'w') as archive:
        for seed in v.SEEDS:
            name=f'decision-traces/pass-1/{seed}.jsonl'
            events=[v.strict_json(line) for line in (root/name).read_bytes().splitlines()]
            events[1]['audit']={key:events[1]['audit'][key] for key in v.v31.COMMON.split()}
            archive.writestr(name,b''.join(v.canonical(e,newline=True) for e in events))
    monkeypatch.setattr(v,'BASELINE_ARCHIVE_SHA256',hashlib.sha256(baseline_archive.read_bytes()).hexdigest())
    return dict(root=root,inventory=files,metadata=metadata,freeze=freeze,freeze_sha=freeze_sha,
        data_dir=data_dir,baseline_archive=baseline_archive), put


def test_complete_1200_synthetic_records_pass_all_gates(synthetic_bundle):
    args, unused=synthetic_bundle
    result=v.verify(**args)
    assert result['verified_records']==1200
    assert result['verified_call_logs']==1200
    assert result['classification']==v.CLASSIFICATION
    assert result['summary']['net_wins']==0
    assert result['physical_operations']['legal_enumerations']==2000
    assert not result['transport_and_drive_custody']['established_by_this_verifier']
    assert result['historical_control_trace_matches']==400
    assert 'No closure overrides' in result['summary']['descriptive_diagnostics']['mechanism_attribution']


@pytest.mark.parametrize('mutation',['partial','reference','operations','terminal','phase','source','resource','replay'])
def test_full_population_adversarial_mutations_fail_without_classification(synthetic_bundle,mutation):
    args,put=synthetic_bundle
    root=args['root']
    if mutation=='partial':
        (root/'call-results/pass-3/1000399.jsonl').unlink()
    elif mutation=='reference':
        name='call-results/pass-2/1000000.jsonl'
        rows=[v.strict_json(line) for line in (root/name).read_bytes().splitlines()]
        rows[1]['result']['scientific_sha256']='0'*64
        put(name,rows,True)
    elif mutation=='operations':
        args['freeze']['resources']['total_operations']['legal_enumerations']=1999
        args['freeze_sha']=v.digest(args['freeze'])
        args['metadata']['execution_go']['freeze_sha256']=args['freeze_sha']
        receipt=v.read_json(root/'receipt.json')
        receipt['freeze']=args['freeze']
        receipt['freeze_sha256']=args['freeze_sha']
        receipt['execution_go']['freeze_sha256']=args['freeze_sha']
        receipt['admission']['freeze_sha256']=args['freeze_sha']
        receipt['admission']['execution_go']['freeze_sha256']=args['freeze_sha']
        put('receipt.json',receipt)
    elif mutation=='terminal':
        name='raw-results/pass-1/1000000.json'
        value=v.read_json(root/name)
        value['conservation']['zones']['draw'].pop()
        put(name,value)
    elif mutation=='phase':
        name='completed.jsonl'
        rows=[v.strict_json(line) for line in (root/name).read_bytes().splitlines()]
        rows[0],rows[1]=rows[1],rows[0]
        put(name,rows,True)
    elif mutation=='source':
        args['metadata']['execution_blobs']['scripts/worker35_resources.py']='f'*40
    elif mutation=='resource':
        name='resource-metrics.jsonl'
        rows=[v.strict_json(line) for line in (root/name).read_bytes().splitlines()]
        rows[0]['status']='failed'
        put(name,rows,True)
    else:
        name='decision-traces/pass-3/1000000.jsonl'
        rows=[v.strict_json(line) for line in (root/name).read_bytes().splitlines()]
        rows[1]['audit']['boundary']['engine_before']='f'*64
        put(name,rows,True)
    with pytest.raises(v.Rejected):
        v.verify(**args)


@pytest.mark.parametrize('net,expected',[(7,v.CLASSIFICATION),(8,v.ADVANCED_CLASSIFICATION)])
def test_fixed_net8_and_descriptive_only_equipment_gate(net,expected):
    seeds=list(v.SEEDS)
    result=v.summarize(seeds[:45],seeds[:45+net],{}, {1:'c'*64,2:'d'*64},
        dict.fromkeys(v.FLAGS,0),{'control':396,'candidate':300},{})
    assert result['classification']==expected
    assert result['net_wins']==net
    assert not result['descriptive_diagnostics']['equipment_completion_is_advancement_gate']


def test_true_original_collect_crossover_is_separate_from_reserve_mediation():
    cards, obs, science = collect_fixture()
    cards['start_easy']['cells'][0]['tunnel_edges'] = ['E','S','W']
    obs['board']['cells'] = deepcopy(cards['start_easy']['cells'])
    place = dict(action='place',hand_index=0,origin=[1,0],quarter_turns=0)
    science.update(input_before=v.digest(obs),input_after=v.digest(obs),
        chosen=place,chosen_index=1,
        roots=[science['roots'][0],dict(move=place,score=100)],
        tiers=dict(T0=[0],F=[0,1],T=[0],C=[1],final=[1]),
        guards=[science['guards'][0],dict(eligible=True,reason='eligible',after=[1,0,0,0],exit_legal_count=1)])
    science['flags'].update(closure_branch_selected=True,true_original_all_collect_crossover=True)
    flags=validate(science,obs,cards)
    assert flags['true_original_all_collect_crossover']
    assert not flags['reserve_filter_mediated_change']
    science['guards'][1]['exit_legal_count']=0
    with pytest.raises(v.Rejected,match='guard'):
        validate(science,obs,cards)


def test_reserve_filter_mediated_change_is_not_original_collect_crossover():
    cards, obs, science = make_fixture()
    cards['start_easy']['cells'][0]['tunnel_edges']=['E','S','W']
    obs['board']['cells']=deepcopy(cards['start_easy']['cells'])
    for i in range(9):
        identity=f'invented-{i}'
        cards[identity]['cells']=[cell(0,0,'ESW'),cell(0,1,'N')]
        x=i+1
        obs['board']['placements'].append(dict(card_id=identity,origin=[x,0],quarter_turns=0,
            placement_index=x,kind='ordinary',cells=[[x,0],[x,1]],overlaps=[],covered_placement_index=None))
        obs['board']['cells'].extend([cell(x,0,'ESW'),cell(x,1,'N')])
    obs['turns']=9
    ids=['invented-9','invented-12',*(f'invented-{i}' for i in range(20,24))]
    obs['hand']=[dict(card_id=i,is_exit=False,**deepcopy(cards[i])) for i in ids]
    roots=[]
    for index in range(2):
        roots.extend([dict(move=dict(action='collect',hand_index=index,origin=None,quarter_turns=0),score=10000),
            dict(move=dict(action='place',hand_index=index,origin=[10,0],quarter_turns=0),score=20000 if index==0 else 100)])
    science.update(input_before=v.digest(obs),input_after=v.digest(obs),roots=roots,
        supply={'raincoat':dict(quota=3,collected=0,total=12,placed=9,deficit=3,available=3,own_hand=1),
            'rope':dict(quota=2,collected=0,total=8,placed=0,deficit=2,available=8,own_hand=1)},
        tiers=dict(T0=[1],F=[0,2,3],T=[0,2],C=[3],final=[3]),chosen_index=3,chosen=roots[3]['move'],rng_after='b'*64,
        guards=[dict(eligible=False,reason='not_place',after=None,exit_legal_count=None),
            dict(eligible=False,reason='reserve_filtered',after=None,exit_legal_count=None),
            dict(eligible=False,reason='not_place',after=None,exit_legal_count=None),
            dict(eligible=True,reason='eligible',after=[1,0,0,0],exit_legal_count=1)],
        flags=dict(reserve_filter_active=True,reserve_primary_tier_changed=True,closure_branch_selected=True,
            true_original_all_collect_crossover=False,reserve_filter_mediated_change=True))
    flags=validate(science,obs,cards)
    assert flags['reserve_filter_mediated_change']
    assert not flags['true_original_all_collect_crossover']


def test_baseline_archive_unavailable_and_corrupt_are_distinct(tmp_path):
    with pytest.raises(FileNotFoundError):
        with v.HistoricalControl(tmp_path/'missing.zip'):
            pass
    (tmp_path/'wrong.zip').write_bytes(b'corrupt bytes')
    with pytest.raises(v.Rejected,match='historical control archive'):
        with v.HistoricalControl(tmp_path/'wrong.zip'):
            pass


def test_review_role_requirement_rejects_other_nonempty_strings(synthetic_bundle):
    args, unused = synthetic_bundle
    freeze = deepcopy(args['freeze'])
    v.validate_freeze(freeze, v.digest(freeze))
    freeze['reviews']['harness'] = 'invented-review'
    with pytest.raises(v.Rejected, match='review role requirement harness'):
        v.validate_freeze(freeze, v.digest(freeze))
