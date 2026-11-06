"""Read recorded aggregate results; never simulate, pool or infer missing wins."""
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def percent(wins, games):
    return str((Decimal(wins) * 100 / Decimal(games)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)).replace('.', ',') + '%'


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def recorded_results():
    rows = {}

    def add(policy, study, wins, games, model, source_file, source_url, seeds,
            source_commit, primary=True):
        if type(wins) is not int or type(games) is not int or not 0 <= wins <= games or games < 1:
            raise ValueError('Invalid recorded count: ' + study)
        row = dict(id=policy + '-' + study, study=study, wins=wins, games=games,
                   model=model, hand_size=6 if model == 'current' else 3,
                   source_file=source_file, source_url=source_url, seeds=seeds,
                   source_commit=source_commit, primary=primary)
        rows.setdefault(policy, []).append(row)

    smoke = read('website/inputs/current-smoke.json')
    for policy, key in [('random', 'random_legal'), ('min-open', 'min_open_tunnels'),
                        ('v0', 'greedy_v0'), ('v1', 'geometry_aware_v1')]:
        metric = smoke['payload'][key]
        add(policy, 'smoke', metric['wins'], metric['games'], 'current',
            'current-smoke.json', smoke['source_url'], smoke['payload']['seed_range'],
            smoke['source_commit'])

    keys = {
        'v1': {'v0': 'greedy_v0', 'v1': 'geometry_aware_v1'},
        'v2': {'v0': 'greedy_v0', 'discard-v2': 'discard_excess_v2',
               'water-v2': 'water_first_v2', 'combined-v2': 'combined_v2'},
        'v3': {'combined-v2': 'combined_v2', 'merge-v3': 'merge_aware_v3',
               'space-v3': 'water_space_v3', 'combined-v3': 'combined_v3'},
    }
    for study, policies in keys.items():
        source = read('website/inputs/historical-' + study + '.json')
        payload = source['payload']
        for policy, key in policies.items():
            add(policy, 'historical-' + study, payload['policies'][key]['wins'],
                payload['games_per_policy'], 'historical', 'historical-' + study + '.json',
                source['source_url'], [payload['seed_start'], payload['seed_end']],
                payload['simulator_commit'], primary=policy not in rows)

    path = 'experiments/canonical-quota-limited-solo-baseline/baseline-2026-10-01.manifest.json'
    baseline = read(path)
    add('v4', 'baseline', baseline['summary']['wins'], baseline['summary']['games_per_pass'],
        'current', 'baseline.manifest.json', 'https://github.com/carabinshely/bandido-alcatraz-solve/blob/main/' + path,
        baseline['population']['seeds_inclusive'], baseline['evaluated_commit'])

    path = 'experiments/real-deck-policy-v5/visible-repair-reserve-development-evaluation-2026-09-24.manifest.json'
    v5 = read(path)
    for policy in ('v5', 'v4'):
        add(policy, 'historical-v5', v5['paired_outcomes'][policy + '_wins'], len(v5['seed_scope']),
            'historical', 'v5.manifest.json', v5['issue_result_url'], v5['seed_scope'],
            v5['evaluated_commit'], primary=policy == 'v5')
    path = 'experiments/real-deck-policy-v6/current-model-spent-development-1000-1099-2026-09-28.json'
    v6 = read(path)
    for policy in ('v6', 'v4'):
        metric = v6[policy + '_metrics']
        add(policy, 'historical-v6', metric['wins'], metric['games'], 'historical',
            'v6.manifest.json', v6['authoritative_evaluation']['workflow_run_url'],
            v6['seed_range'], v6['evaluated_commit'], primary=policy == 'v6')
    path = 'experiments/real-deck-policy-v7/fresh-development-1000000-1000399-2026-09-30.manifest.json'
    v7 = read(path)
    for policy in ('v7', 'v4'):
        metric = v7['summary'][policy]
        add(policy, 'historical-v7', metric['wins'], metric['games'], 'historical',
            'v7.manifest.json', v7['execution']['run_url'], v7['seed_range_inclusive'],
            v7['evaluated_commit'], primary=policy == 'v7')

    document = (ROOT / 'docs/catalog-support-policy.md').read_text(encoding='utf-8')
    cohorts = re.findall(r'\| (100\d+)[–-](100\d+) \((\d+) pairs\) \| (\d+) \| (\d+) \|', document)
    if len(cohorts) != 2:
        raise ValueError('CatalogSupport cohort table changed; review results import')
    commit = re.search(r'snapshot commit\s+`([a-f0-9]{40})`', document).group(1)
    for index, (start, end, games, candidate, control) in enumerate(cohorts, 1):
        for policy, wins in [('catalog', candidate), ('v4', control)]:
            add(policy, 'catalog-' + str(index), int(wins), int(games), 'current',
                'docs--catalog-support-policy.md.txt',
                'https://github.com/carabinshely/bandido-alcatraz-solve/blob/main/docs/catalog-support-policy.md',
                [int(start), int(end)], commit, primary=policy == 'catalog')
    recent = read('website/inputs/recent-research.json')
    for row in rows['catalog']:
        row['primary'] = False
    for study in recent['studies']:
        add('catalog', 'recent-' + str(study['number']), study['wins_control'], study['pairs'],
            'current', 'recent-research.json',
            'https://carabinshely.github.io/bandido-alcatraz-solve/results.html#recent-' + str(study['number']),
            study['seeds'], study['source_head'], primary=study['number'] == 129)
    return rows
