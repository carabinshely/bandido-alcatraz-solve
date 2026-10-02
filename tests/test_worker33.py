"""Worker33 adapter regressions: frozen bytes/metadata and invented fixtures only.

The selected corpus is only decompressed and hashed. Never reconstruct, enumerate,
score, search, or continue any selected observation from these tests.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from random import Random
import re
import sys
from types import SimpleNamespace

import pytest

from bandido_alcatraz.model import Direction, Material
from bandido_alcatraz.moves import Action
from bandido_alcatraz.policies import BoundedMergeV4Policy
from bandido_alcatraz.strategy import score_move_no_draw
from bandido_alcatraz.worker32.candidate import Candidate
from bandido_alcatraz.worker32.reference import Reference
from bandido_alcatraz.worker32.evidence import BudgetExceeded, canonical, move, observation, sha
from bandido_alcatraz.worker33 import inputs, runtime
from test_worker32 import card, state


ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / 'experiments/mixed-action-two-action-diagnostic'
EXPECTED_PINS = {
    'selected-corpus.jsonl.gz': (14286, 'ab4133bd880fed194f7f22fcc3ad00371013f18d0c51f51ef8ffe36705ad4300'),
    'audit-reference.jsonl': (30132, '4ca2c08160b8e641f26d3dfbb2759727c522fe1d0235837cdaab35e3e967502e'),
    'selection-manifest.json': (73029, '3ad07d6237b3f7f24c60448fc346a013261d05b8e36fd998ffd440faceee9a78'),
    'select_public_snapshots.py': (25468, '30699b72adb5c731523c84bc298c04fca41de90df00d074e628a0fc5e55e82ca'),
}
EXPECTED_RAW = (326455, '2366287bd1e05d6b47ed47344996120f76bc02b297a81b3238099dc329066df5')


def invented_mixed_observation():
    return state([card('invented-rope', [Direction.WEST, Direction.EAST],
                       material=Material.ROPE)]).observation()


def invented_baseline(obs):
    """Compute baseline fixtures exclusively from the tiny invented state."""
    legal = obs.legal_moves()
    scores = [score_move_no_draw(obs, m, BoundedMergeV4Policy(250).weights) for m in legal]
    tier = [move(m) for m, score in zip(legal, scores) if score == max(scores)]
    entry = dict(B=len(legal), C=len(obs.board.cells),
                 collect_count_metadata=sum(m.action is Action.COLLECT for m in legal),
                 place_count_metadata=sum(m.action is Action.PLACE for m in legal))
    audit = dict(legal_move_count=len(legal), primary_score=max(scores),
                 primary_tier=tier, primary_tier_sha256=sha(tier))
    return entry, audit


def local_environment(monkeypatch, **values):
    """Replace the adapter's OS reference, never mutate the process environment."""
    isolated_os = SimpleNamespace(**vars(os))
    isolated_os.environ = {**os.environ, **values}
    monkeypatch.setattr(runtime, 'os', isolated_os)
    return isolated_os.environ


def test_frozen_worker33_bytes_only():
    assert inputs.PINS == EXPECTED_PINS
    assert inputs.RAW_PIN == EXPECTED_RAW
    data = inputs.frozen_bytes(FROZEN)
    for name, (size, digest) in {**EXPECTED_PINS, 'selected-corpus.jsonl': EXPECTED_RAW}.items():
        assert len(data[name]) == size
        assert hashlib.sha256(data[name]).hexdigest() == digest
    assert len(data['selected-corpus.jsonl'].splitlines()) == 80
    assert len(data['audit-reference.jsonl'].splitlines()) == 80


def test_frozen_population_metadata_only():
    raw = inputs.checked((FROZEN / 'selection-manifest.json').read_bytes(),
                         EXPECTED_PINS['selection-manifest.json'])
    manifest = json.loads(raw)
    entries = manifest['entries']
    identities = {(e['seed'], e['ordinal']) for e in entries}
    assert len(entries) == len(identities) == 80
    assert len({e['seed'] for e in entries}) == 71
    assert [e['position'] for e in entries] == list(range(1, 81))
    assert [e['group'] for e in entries] == ['hash64'] * 64 + ['stress16'] * 16
    assert all(e['action_type_class'] == 'mixed' for e in entries)
    assert all(type(e[k]) is int and e[k] > 0 for e in entries
               for k in ('collect_count_metadata', 'place_count_metadata'))
    assert all(e['collect_count_metadata'] + e['place_count_metadata'] == e['B'] for e in entries)
    for entry in entries:
        text = (f"mixed-action-two-action-diagnostic-v1|{entry['seed']}|"
                f"{entry['ordinal']}|{entry['public_observation_sha256']}")
        assert entry['selection_key_input'] == text
        assert entry['selection_key_sha256'] == hashlib.sha256(text.encode()).hexdigest()
        assert entry['stress_cost_proxy'] == entry['B'] * (entry['B'] + 1) * entry['C']
    assert entries[:64] == sorted(entries[:64], key=lambda e: (e['selection_key_sha256'], e['seed'], e['ordinal']))
    assert entries[64:] == sorted(entries[64:], key=lambda e: (-e['stress_cost_proxy'], e['seed'], e['ordinal']))
    old = ROOT / 'experiments/visible-two-action-diagnostic/selection-manifest.json'
    old_raw = inputs.checked(old.read_bytes(), (63959, 'e5b672d3a97efa72abdc7f32e70a8eb50a3afb8d4813d81ddf4efd3479973410'))
    old_identities = {(e['seed'], e['ordinal']) for e in json.loads(old_raw)['entries']}
    assert len(old_identities) == 80 and identities.isdisjoint(old_identities)
    assert manifest['selection']['eligible_count'] == 1981
    assert manifest['previous_worker32_exclusion']['mixed_identity_count_removed'] == 3


def test_unchanged_scientific_core_bytes():
    frozen = {
        'candidate.py': 'd806a40383566d82f8af4259179940feff0339ac786bcf6207e7f7e0503e1b01',
        'reference.py': '2a396aed1e303332d72b254f30dd58b57133364eafa29e50c5a51807f892e20b',
        'evidence.py': '292baa7966b8b96dc79ebb1b5b17ae86182d61fc11f37dbd86adb2d4cdc78a20',
        'containment.py': '189100959cbf2e14d2ce32c299e48d3a8bb4811c6da091f7e557f4343f36ab7b',
    }
    for name, digest in frozen.items():
        assert hashlib.sha256((ROOT / 'src/bandido_alcatraz/worker32' / name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize('raw', [b'synthetic corruption', b''])
def test_byte_corruption_remains_integrity_invalid(raw):
    with pytest.raises(ValueError) as error:
        inputs.checked(raw, EXPECTED_RAW)
    assert runtime.failure_status(error.value) == 'integrity_invalid'


def test_inaccessible_input_is_execution_blocked(tmp_path):
    with pytest.raises(inputs.ExecutionBlocked) as error:
        inputs.frozen_bytes(tmp_path)
    assert runtime.failure_status(error.value) == 'execution_blocked'


def test_canonical_mixed_counts_preserve_baseline_fields():
    obs = invented_mixed_observation()
    entry, audit = invented_baseline(obs)
    baseline = inputs.baseline_gate(obs, entry, audit)
    legal = obs.legal_moves()
    assert baseline == dict(score=audit['primary_score'], tier=audit['primary_tier'],
                            legal_move_count=len(legal),
                            collect_count=entry['collect_count_metadata'],
                            place_count=entry['place_count_metadata'],
                            root_moves_sha256=sha([move(m) for m in legal]))
    assert baseline['collect_count'] > 0 and baseline['place_count'] > 0


def test_mixed_gate_reuses_existing_canonical_enumeration():
    obs = invented_mixed_observation()
    entry, audit = invented_baseline(obs)
    callers = []
    def record_enumeration(frame, event, arg):
        if (event == 'call' and frame.f_code is type(obs).legal_moves.__code__
                and frame.f_locals['self'] is obs):
            callers.append(frame.f_back.f_code)
    previous_profile = sys.getprofile()
    try:
        sys.setprofile(record_enumeration)
        inputs.baseline_gate(obs, entry, audit)
    finally:
        sys.setprofile(previous_profile)
    # One gate enumeration plus unchanged canonical V4 legality previews for
    # PLACE roots. Counting action types introduces no extra enumeration.
    assert callers.count(inputs.baseline_gate.__code__) == 1
    assert len(callers) == 1 + entry['place_count_metadata']


@pytest.mark.parametrize('field,value', [
    ('collect_count_metadata', 0), ('collect_count_metadata', -1),
    ('collect_count_metadata', 2), ('collect_count_metadata', True),
    ('collect_count_metadata', 1.0), ('place_count_metadata', 0),
    ('place_count_metadata', -1), ('place_count_metadata', 999),
    ('place_count_metadata', True), ('place_count_metadata', 2.0),
])
def test_count_mismatch_rejected_before_any_score(monkeypatch, field, value):
    obs = invented_mixed_observation()
    entry, audit = invented_baseline(obs)
    entry[field] = value
    def forbidden_score(*args):
        raise AssertionError('invalid mixed eligibility reached the scorer')
    monkeypatch.setattr(inputs, 'score_move_no_draw', forbidden_score)
    with pytest.raises(ValueError, match='mixed-action'):
        inputs.baseline_gate(obs, entry, audit)


@pytest.mark.parametrize('hand', [
    [card('invented-collect-only', material=Material.ROPE)],
    [card('invented-place-only', [Direction.WEST, Direction.EAST])],
])
def test_single_action_type_is_never_eligible(hand):
    obs = state(hand).observation()
    entry, audit = invented_baseline(obs)
    with pytest.raises(ValueError, match='mixed-action'):
        inputs.baseline_gate(obs, entry, audit)


@pytest.mark.parametrize('change', ['B', 'C', 'score', 'tier', 'tier_digest'])
def test_original_canonical_and_v4_gates_remain(change):
    obs = invented_mixed_observation()
    entry, audit = invented_baseline(obs)
    if change in ('B', 'C'):
        entry[change] += 1
    elif change == 'score':
        audit['primary_score'] += 1
    elif change == 'tier':
        audit['primary_tier'] = []
    else:
        audit['primary_tier_sha256'] = '0' * 64
    with pytest.raises(ValueError) as error:
        inputs.baseline_gate(obs, entry, audit)
    assert runtime.failure_status(error.value) == 'integrity_invalid'


def guard_fixture(monkeypatch, tmp_path, version=(3, 11, 16), implementation='CPython'):
    event = dict(action='opened', pull_request=dict(
        draft=True, head=dict(ref=runtime.BRANCH, sha='invented-head',
                              repo=dict(full_name=runtime.REPO)),
        base=dict(repo=dict(full_name=runtime.REPO))))
    path = tmp_path / 'invented-event.json'
    path.write_text(json.dumps(event))
    env = local_environment(monkeypatch, RUNNER_NAME='bandido-alcatraz-ci',
                            GITHUB_EVENT_NAME='pull_request', PYTHONHASHSEED='0',
                            GITHUB_EVENT_PATH=str(path), GITHUB_RUN_ATTEMPT='1')
    monkeypatch.setattr(runtime, 'sys', SimpleNamespace(version_info=version))
    monkeypatch.setattr(runtime, 'platform', SimpleNamespace(python_implementation=lambda: implementation))
    return env


def test_exact_fixed_runtime_accepted(monkeypatch, tmp_path):
    guard_fixture(monkeypatch, tmp_path)
    assert runtime.runner_guard(tmp_path) == 'invented-head'


@pytest.mark.parametrize('version,implementation', [
    ((3, 11, 15), 'CPython'), ((3, 11, 17), 'CPython'),
    ((3, 12, 16), 'CPython'), ((3, 11, 16), 'PyPy'),
])
def test_fixed_runtime_unavailable_is_blocked(monkeypatch, tmp_path, version, implementation):
    guard_fixture(monkeypatch, tmp_path, version, implementation)
    with pytest.raises(inputs.ExecutionBlocked, match='3.11.16') as error:
        runtime.runner_guard(tmp_path)
    assert runtime.failure_status(error.value) == 'execution_blocked'


@pytest.mark.parametrize('hashseed', ['1', 'random', None])
def test_wrong_hashseed_is_integrity_invalid(monkeypatch, tmp_path, hashseed):
    env = guard_fixture(monkeypatch, tmp_path)
    if hashseed is None:
        env.pop('PYTHONHASHSEED')
    else:
        env['PYTHONHASHSEED'] = hashseed
    with pytest.raises(ValueError, match='hash seed') as error:
        runtime.runner_guard(tmp_path)
    assert runtime.failure_status(error.value) == 'integrity_invalid'


def test_fixed_parent_branch_and_resources():
    assert runtime.BASE == 'c50a7ab8e73eaf3c497c5d1c9fef5cbe53261853'
    assert runtime.REPOSITORY_BASE == '1b5881802fc995d301ed3eca6a0e75c1d2dcb90c'
    assert runtime.BRANCH == 'research/worker33-mixed-action-diagnostic'
    assert runtime.PROTOCOL == 'https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5944922245'
    assert runtime.COMPUTE_SECONDS == 5400
    assert runtime.TERMINATION_GRACE_SECONDS == 30
    assert runtime.failure_status(BudgetExceeded()) == 'resource_incomplete'
    assert runtime.failure_status(TimeoutError()) == 'resource_incomplete'


def test_workflow_frozen_trigger_runtime_and_deadline_budgets():
    workflow = (ROOT / '.github/workflows/worker33-mixed-action.yml').read_text()
    trigger = workflow.split('permissions:', 1)[0]
    assert '  pull_request:\n    types: [opened]\n' in trigger
    assert re.findall(r'^  ([a-z_]+):$', trigger, re.MULTILINE) == ['pull_request']
    for guard in (
        "github.event.action == 'opened'",
        'github.event.pull_request.draft == true',
        "github.event.pull_request.head.ref == 'research/worker33-mixed-action-diagnostic'",
        "github.event.pull_request.head.repo.full_name == 'carabinshely/bandido-alcatraz-solve'",
        "github.repository == 'carabinshely/bandido-alcatraz-solve'",
        'github.run_attempt == 1',
    ):
        assert guard in workflow
    assert 'runs-on: [self-hosted, Linux, X64, bandido-alcatraz-ci]' in workflow
    assert "python-version: '3.11.16'" in workflow
    assert "PYTHONHASHSEED: '0'" in workflow
    assert 'cancel-in-progress: false' in workflow
    assert 'ref: ${{ github.event.pull_request.head.sha }}' in workflow
    assert re.findall(r'^    timeout-minutes: (\d+)$', workflow, re.MULTILINE) == ['120']
    deadlines = [int(x) for x in re.findall(r'^        timeout-minutes: (\d+)$', workflow, re.MULTILINE)]
    assert deadlines == [1, 1, 2, 2, 4, 92, 2, 8]
    assert sum(deadlines[:5]) <= 10 and sum(deadlines[-2:]) <= 10
    assert sum(deadlines) <= 120
    assert workflow.count('-m bandido_alcatraz.worker33.runtime supervise') == 1
    assert 'tests/test_worker32.py tests/test_worker32_preflight.py tests/test_worker33.py' in workflow
    assert "if: always() && env.EVIDENCE != ''" in workflow
    assert "if: always() && env.SAFE_UPLOAD == 'true'" in workflow


@pytest.mark.parametrize('timeout', [False, True])
def test_supervisor_passes_explicit_5400_and_30(monkeypatch, tmp_path, timeout):
    root = tmp_path / 'invented-repo'
    evidence = tmp_path / 'invented-evidence'
    root.mkdir(); evidence.mkdir()
    local_environment(monkeypatch, RUNNER_TEMP=str(tmp_path / 'runner-temp'))
    arguments = ['supervise', '--root', str(root), '--evidence', str(evidence)]
    class SyntheticParser(argparse.ArgumentParser):
        def parse_args(self, args=None, namespace=None):
            return super().parse_args(arguments, namespace)
    monkeypatch.setattr(runtime, 'argparse', SimpleNamespace(ArgumentParser=SyntheticParser))
    monkeypatch.setattr(runtime, 'runner_guard', lambda root: 'invented-head')
    calls = []
    def invented_group(command, log, *, timeout, grace):
        calls.append((command, log, timeout, grace))
        if should_timeout:
            raise TimeoutError('invented supervisor timeout')
        runtime.durable(evidence / 'result.json', {'synthetic': True})
        return 0
    should_timeout = timeout
    monkeypatch.setattr(runtime, 'run_group', invented_group)
    if timeout:
        with pytest.raises(TimeoutError):
            runtime.main()
        assert json.loads((evidence / 'failure.json').read_text())['status'] == 'resource_incomplete'
        assert not (evidence / 'result.json').exists()
    else:
        runtime.main()
        assert not (evidence / 'failure.json').exists()
    assert len(calls) == 1
    command, log, ceiling, grace = calls[0]
    assert command == [sys.executable, '-m', 'bandido_alcatraz.worker33.runtime', 'compute',
                       '--root', str(root), '--evidence', str(evidence)]
    assert log == evidence / 'compute.log' and (ceiling, grace) == (5400, 30)


@pytest.mark.parametrize('exercise_label_branch', [False, True])
def test_real_160_call_order_fresh_instances_rng_and_labels(tmp_path, monkeypatch, exercise_label_branch):
    # Every object is invented here; no selected data or selected audit is loaded.
    observations = [invented_mixed_observation() for _ in range(80)]
    entries, audits = [], []
    for index, obs in enumerate(observations):
        entry, audit = invented_baseline(obs)
        entries.append(dict(entry, position=index + 1, seed=1000000 + index, ordinal=1,
                            public_observation_sha256=sha(observation(obs))))
        audits.append(audit)
    monkeypatch.setattr(runtime, 'runner_guard', lambda root: 'invented-head')
    monkeypatch.setattr(runtime, 'installed_tree', lambda *args: dict(head='invented-head', tree='invented-tree', files={}))
    monkeypatch.setattr(runtime, 'load_population', lambda *args: (entries, observations, audits, None))
    monkeypatch.setattr(runtime, 'accepted_cards', lambda *args: {})
    monkeypatch.setattr(runtime, 'reconstruct', lambda value, *args: value)
    local_environment(monkeypatch, RUNNER_NAME='synthetic', PYTHONHASHSEED='0',
                      GITHUB_RUN_ID='123', GITHUB_RUN_ATTEMPT='1')
    if exercise_label_branch:
        # Classification plumbing only; unchanged strict-set logic is tested below.
        # All 160 scientific calls and all 80 independent matches remain real.
        monkeypatch.setattr(runtime, 'strict_departure', lambda *args: True)
    seen = []
    code_objects = {Candidate.evaluate.__code__, Reference.evaluate.__code__}
    def record_call(frame, event, arg):
        if event == 'call' and frame.f_code in code_objects:
            values = frame.f_locals
            seen.append((values['self'], values['rng'], values['obs'], values['rng'].getstate()))
    previous_profile = sys.getprofile()
    try:
        sys.setprofile(record_call)
        runtime.compute(tmp_path, tmp_path)
    finally:
        sys.setprofile(previous_profile)
    assert len(seen) == 160
    assert [type(x[0]) for x in seen] == [Candidate] * 80 + [Reference] * 80
    assert len({id(x[0]) for x in seen}) == len({id(x[1]) for x in seen}) == 160
    assert all(type(x[1]) is Random and x[3] == Random(0).getstate() for x in seen)
    assert [id(x[2]) for x in seen] == [id(x) for x in observations] * 2
    order = json.loads((tmp_path / 'call-order.json').read_text())
    assert order == [dict(pass_number=p, position=e['position'], seed=e['seed'], ordinal=e['ordinal'])
                     for p in (1, 2) for e in entries]
    for index in range(80):
        first = json.loads((tmp_path / f'call-{index + 1:03}.json').read_text())
        second = json.loads((tmp_path / f'call-{index + 81:03}.json').read_text())
        assert canonical(first['scientific']) == canonical(second['scientific'])
        assert first['scientific']['schema'] == 'worker32-scientific-v1'
        assert {r['root']['action'] for r in first['scientific']['roots']} == {'place', 'collect'}
        assert first['envelope']['call'] == index + 1 and second['envelope']['call'] == index + 81
    result = json.loads((tmp_path / 'result.json').read_text())
    label = 'exercised' if exercise_label_branch else 'not_exercised'
    assert result['status'] == 'mixed_action_two_action_diagnostic_mechanism_' + label
    assert result['completed_calls'] == 160
    assert result['strict_departures'] == ([[e['seed'], e['ordinal']] for e in entries] if exercise_label_branch else [])
    assert len(list(tmp_path.glob('call-[0-9][0-9][0-9].json'))) == 160
    events = [json.loads(line) for line in (tmp_path / 'journal.jsonl').read_text().splitlines()]
    assert [e['event'] for e in events] == ['started', 'completed'] * 160
    assert not (tmp_path / 'failure.json').exists()


def test_strict_departure_still_requires_entire_opposite_tiers_and_better_key():
    place, collect = {'action': 'place'}, {'action': 'collect'}
    payload = dict(maximal_roots=[place], best=[1, 0, 10],
                   roots=[dict(root=place, maximum=[1, 0, 10]),
                          dict(root=collect, maximum=[1, 0, 9])])
    assert runtime.strict_departure(payload, {'tier': [collect]})
    assert not runtime.strict_departure(payload, {'tier': [collect, place]})
    assert not runtime.strict_departure({**payload, 'maximal_roots': [place, collect]}, {'tier': [collect]})
    assert not runtime.strict_departure({**payload, 'best': [1, 0, 9]}, {'tier': [collect]})
