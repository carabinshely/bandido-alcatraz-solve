"""Metadata assembly only: no project imports or fixture/helper execution."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(name):
    return json.loads((ROOT / name).read_bytes())

def pin(name):
    data = (ROOT / name).read_bytes()
    return {'size_bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

draft = read('evidence-design/worker38-selector-materialization-draft.json')
new = read('evidence/NEW64-HARD-RESERVATIONS.json')
legacy = read('evidence-design/WORKER37-HARD-RESERVATIONS.json')
inputs = read('evidence-design/FIRST33-INDEPENDENT-INPUT-PINS.json')
first = {row['selector']: row for row in new['selectors']}
input_rows = {row['selector']: row for row in inputs['cases']}
expected = {row['selector']: row for row in read('evidence-design/F07-NEW64-OUTPUT-BOUND.json')['per_selector']}
ordered = [row['selector'] for row in draft['methods']]
assert len(ordered) == len(set(ordered)) == 397
assert [row['selector'] for row in inputs['cases']] == ordered[:33]
assert first[ordered[33]]['id'] == 'C04'

api_names = ('pull-request.json', 'postmerge-ci.json', 'current-source-ci.json',
             'review-exhaustive.json', 'review-adversarial.json', 'preregistration.json',
             'diagnostic-commit.json')
cases = []
for ordinal, selector in enumerate(ordered, 1):
    path, definition = selector.split(':')
    class_name, method_name = definition.split('.')
    raw = (ROOT / path).read_bytes(); lines = raw.decode().splitlines(keepends=True)
    module = ast.parse(raw)
    cls = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == method_name)
    span = ''.join(lines[method.lineno-1:method.end_lineno]).encode()
    row = {'ordinal': ordinal, 'selector': selector, 'source_path': path,
           'method_span_sha256': hashlib.sha256(span).hexdigest(),
           'reservation_certified': False, 'expected_output_upper_bytes': None,
           'reservation_upper_bytes': None, 'log_reservation_upper_bytes': None,
           'capture_record_bytes_upper': None, 'test_module_dependencies': [],
           'input_rules': [], 'output_rules': [], 'version_witnesses': [],
           'not_admitted_reason': 'Fixed prefix ends before C04; no later selector may be skipped to or run'}
    if ordinal > 33:
        if ordinal == 34:
            row['not_admitted_reason'] = 'C04 actual package/seal exceptional/staged sink reservation remains unproved'
        cases.append(row); continue
    proof = first[selector]
    assert proof['reservation_certified'] is True
    row.update(reservation_certified=True, expected_output_upper_bytes=proof['expected_output_upper_bytes'],
        reservation_upper_bytes=proof['reservation_upper_bytes'],
        log_reservation_upper_bytes=16384,
        capture_record_bytes_upper=proof['native_control_reservation_upper_bytes'],
        maximum_inventory_rows=proof['inventory_rows_max'],
        maximum_temporary_roots=proof['capture_roots_max'],
        maximum_observation_records=proof['fixed_observation_units'],
        input_rules=input_rows[selector]['input_rules'],
        test_module_dependencies=[path], not_admitted_reason=None,
        reservation_proof={'path': 'evidence/NEW64-HARD-RESERVATIONS.json', 'selector': selector},
        setup_prefix_reservation_bytes=proof['setup_partial_reserve_bytes'])
    row['inventory_record_bytes_upper'] = row['capture_record_bytes_upper'] - 1024 - 256 * row['maximum_observation_records']
    out = []
    def add(name, maximum, group=None):
        out.append({'pattern': name, 'maximum_bytes': maximum, 'expected_type': 'file',
                    'maximum_occurrences': 1, **({'group': group} if group else {})})
    ident = proof['id']
    row['literal_case_id'] = ident
    row['planned_Bash_roots'] = int(ident in ('S01','S02','S03','S05','S06','S08','C01','C02'))
    row['planned_generic_child_roots'] = 0
    row['planned_mock_GETs'] = proof['mocked_GET_total']
    if ident == 'S01':
        row['test_module_dependencies'].append('tests/test_worker37_bootstrap.py')
        ext = legacy['extra_S01']
        for entry in ext['original_output_roster']:
            add('t02/' + entry['path'], entry['maximum_bytes'])
        for entry in ext['in_memory_observation_roster']:
            add('retained-observations/worker37/W38-S01/' + entry['path'], entry['maximum_bytes'])
    elif row['planned_Bash_roots']:
        base = 't01/' + ident
        allocation = base + '/cache/worker38-synthetic-profile/allocations/worker38-synthetic-profile-01'
        attempt = allocation + '/run-501-attempt-1'
        def expand(name):
            if name.startswith('ALLOCATION/'):
                return allocation + name[len('ALLOCATION'):]
            if name.startswith('ATTEMPT/'):
                return attempt + name[len('ATTEMPT'):]
            return base + '/' + name
        names = set(proof['produced_paths'])
        for entry in (new['Bash_sink_certificate']['native_diagnostics'] +
                      new['Bash_sink_certificate']['fixed_files'] +
                      new['Bash_sink_certificate']['additional_files']):
            if entry['path'] in names:
                add(expand(entry['path']), entry['maximum_bytes'])
        observation = 'retained-observations/worker38/' + method_name + '/1/'
        add(observation + 'observed-report.json', 8388608, 'retainer')
        add(observation + 'commands.log', 0, 'retainer')
        row['output_groups'] = {'retainer': 8388608}
    elif ident.startswith('A'):
        for name in api_names:
            add('t01/consumed-0/admission-inputs/' + name, 32768, 'response_table')
        observation = 'retained-observations/worker38/' + method_name + '/1/'
        add(observation + 'observed-report.json', 8388608, 'retainer')
        add(observation + 'consumed-reservation.txt', 251, 'retainer')
        row['output_groups'] = {'response_table': 32768, 'retainer': 8388608}
    row['output_rules'] = out
    assert len({entry['pattern'] for entry in out}) == len(out)
    assert not {entry['pattern'] for entry in out} & {entry['pattern'] for entry in row['input_rules']}
    cases.append(row)

driver_ast = ast.parse((ROOT/'scripts/worker38/driver.py').read_bytes())
fixed_sets = {}
for node in driver_ast.body:
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ('PRODUCTION_PATHS','TEST_PATHS'):
        fixed_sets[node.targets[0].id] = set(ast.literal_eval(node.value.args[0]))
prefix = 'experiments/worker38-synthetic-profile/'
names = fixed_sets['PRODUCTION_PATHS'] | fixed_sets['TEST_PATHS']
names |= {prefix + name for name in ('PROTOCOL.md','INTEGRATION-CONTRACT.json','FINITE-PREPARATION-PLAN.json',
                                    'SOURCE-GROUNDING.json','comparator-source-manifest.json')}
names |= {prefix + 'upload-amendment/' + name for name in ('AMENDMENT.md','AMENDMENT-CONTRACT.json',
    'FINITE-COVERAGE-AMENDMENT.json','SOURCE-OBSERVATION.json','REPAIR-DISPOSITION.json','HANDOFF.json')}
names |= {prefix + 'inputs/comparator-7ac2f62c/' + entry['path'] + '.blob'
          for entry in read(prefix+'comparator-source-manifest.json')['files']}
map_name = 'evidence-design/worker38-fixed-fixtures.json'
names.remove(map_name)
support = ['evidence/NEW64-HARD-RESERVATIONS.json','evidence/DRIVER-HARD-RESERVATIONS.json',
    'evidence-design/WORKER37-HARD-RESERVATIONS.json','evidence-design/worker38-reservations-177.json',
    'evidence-design/FIRST33-INDEPENDENT-INPUT-PINS.json','evidence-design/NATIVE-ENVIRONMENT-CLOSURE.json',
    'evidence-design/worker38-selector-materialization-draft.json',
    'evidence-design/assemble-worker38-prefix-map.py',
    'evidence-design/PREFIX33-REPAIR01-DISPOSITION.json',
    'evidence/budget-amendment-adoption-5990100199.json']
environment = read('evidence-design/NATIVE-ENVIRONMENT-CLOSURE.json')['planned_owner_environment']
plan = {'schema':'worker38-fixed-preparation-map-v1','status':'UNADMITTED_EXACT_MAP_FOR_STATIC_REVIEW',
    'source_files':{name:pin(name) for name in sorted(names)},
    'support_files':{name:pin(name) for name in support},
    'native_environment':{'path':'evidence-design/NATIVE-ENVIRONMENT-CLOSURE.json',
                          **pin('evidence-design/NATIVE-ENVIRONMENT-CLOSURE.json')},
    'environment':environment,
    'caps':{'wall_seconds':600,'address_space_bytes':536870912,'case_prefix_bytes':25165824,'log_bytes':8388608},
    'global_prefix_reserve_bytes':65536,
    'test_modules':sorted({item.split(':')[0] for item in ordered}),
    'allowed_temporary_prefixes':[None,'worker38-fixed-case-','worker37-literal-bash-',
                                  'worker37-literal-python-','worker38-supervision-stub-','worker38-stub-tests-'],
    'cases':cases,'planned_complete_roster_methods':397,'certified_fixed_prefix_methods':33,
    'first_unstartable_ordinal':34,'remaining_unexecuted_methods':364,
    'order_authority':'Root prospectively selected existing saved draft order new64, Worker37, diagnostic module/list order; original cross-group order was unspecified. No outcome-dependent reorder.',
    'expected_native_exit_if_prefix_passes':1,
    'expected_terminal_status_if_prefix_passes':'execution_incomplete',
    'expected_stop':'C04 uncertified reservation before fixture construction',
    'full_preparation_success_possible_in_this_map':False,
    'partial_prefix_is_not_scientific_readiness':True,
    'mocked_GETs_prefix_max':sum(row.get('planned_mock_GETs',0) for row in cases[:33]),
    'Bash_roots_prefix_max':sum(row.get('planned_Bash_roots',0) for row in cases[:33]),
    'generic_children_prefix_max':0,'scientific_calls':0,'actual_live_HTTP_calls':0,
    'historical_expected_ceiling_bytes':29035551,
    'source_checked_map_excludes_itself_then_receipt_adds_external_map_hash':True,
    'execution_authority':'None; exact map, command, native binding and both independent static reviews plus root gate are required'}
raw=(json.dumps(plan,indent=2,sort_keys=True)+'\n').encode()
(ROOT/map_name).write_bytes(raw)
print(json.dumps({'path':map_name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
                  'cases':len(cases),'certified_prefix':33,'planned_Bash_roots':plan['Bash_roots_prefix_max'],
                  'mocked_GETs_max':plan['mocked_GETs_prefix_max']}))
