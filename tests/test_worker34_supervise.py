"""Invented administration/resource fixtures only. Never open Worker33 evidence."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import inspect
import ctypes
import shutil
from unittest import mock
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'scripts' / 'worker34_supervise.py'
PROTOCOL = ROOT / 'experiments' / 'recorded-endpoint-decomposition' / 'PROTOCOL.md'
SPEC = importlib.util.spec_from_file_location('worker34_supervise_tested', SOURCE)
SUP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SUP
SPEC.loader.exec_module(SUP)

FIXTURE = r'''
import argparse, hashlib, json, os, resource, signal, sys, time
from pathlib import Path
PARSER_ID = {parser_id!r}
MODE = {mode!r}
parser = argparse.ArgumentParser()
for name in ('artifact', 'frozen', 'accepted-evidence', 'output-dir'):
    parser.add_argument('--' + name, required=True)
a = parser.parse_args()
out = Path(a.output_dir)
out.mkdir(exist_ok=False)
started = time.monotonic()
resource.setrlimit(resource.RLIMIT_AS, (2147483648, 2147483648))
assert resource.getrlimit(resource.RLIMIT_AS) == (2147483648, 2147483648)
# This invented fixture JSON is the only input ever read in these tests.
assert json.loads(Path(a.artifact).read_text()) == {{'synthetic': True}}
status, complete, established, errors = 'complete', True, False, []
if MODE == 'early_exit':
    print('synthetic dynamic-loader startup diagnostic',file=sys.stderr)
    raise SystemExit(127)
if MODE == 'deadline_sentinel':
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    time.sleep(.45)
    (out / 'LATE-SENTINEL').write_text('parser computed after deadline')
    while True: time.sleep(.01)
if MODE == 'timeout':
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    (out / 'started.json').write_text(json.dumps({{'pid': os.getpid()}}))
    while True: time.sleep(.01)
if MODE == 'slow': time.sleep(.65)
if MODE == 'descendant':
    child = os.fork()
    if child == 0:
        os.setsid()
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        (out / 'descendant.json').write_text(json.dumps({{'pid': os.getpid()}}))
        while True: time.sleep(.01)
    while not (out / 'descendant.json').exists(): time.sleep(.001)
    while True: time.sleep(.01)
if MODE == 'orphan':
    child = os.fork()
    if child == 0:
        os.setsid()
        (out / 'descendant.json').write_text(json.dumps({{'pid': os.getpid()}}))
        while True: time.sleep(.01)
    while not (out / 'descendant.json').exists(): time.sleep(.001)
if MODE == 'memory':
    resource.setrlimit(resource.RLIMIT_AS, (67108864, 67108864))
    try:
        payload = bytearray(134217728)
        raise AssertionError('allocation unexpectedly survived reduced ceiling')
    except MemoryError:
        status, complete, errors = 'resource_incomplete', False, ['controlled synthetic MemoryError']
if MODE in ('integrity', 'integrity_bad_limit'):
    status, complete, established, errors = 'integrity_invalid', False, True, ['synthetic completed hash mismatch']
if MODE in ('complete', 'slow', 'mismatch', 'missing', 'orphan'):
    for name in ('leaves.jsonl', 'observations.jsonl', 'summary.json'):
        if MODE == 'missing' and name == 'leaves.jsonl': continue
        value = {{'status': 'recorded_component_tradeoff_absent'}} if name == 'summary.json' else {{'synthetic': True}}
        if MODE == 'mismatch' and name == 'leaves.jsonl': value['different'] = True
        with open(out / name, 'xb') as f:
            f.write((json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode())
            f.flush(); os.fsync(f.fileno())
soft, hard = resource.getrlimit(resource.RLIMIT_AS)
receipt = dict(parser_id=PARSER_ID, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 interpreter_executable=str(Path(sys.executable).resolve()), interpreter_version=sys.version,
 pid=os.getpid(), rlimit_as_soft=soft, rlimit_as_hard=hard, status=status, completed=complete,
 elapsed_seconds=time.monotonic()-started, maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
 established_integrity_failure=established, errors=errors)
if MODE in ('bad_runtime', 'integrity_bad_limit'): receipt['rlimit_as_hard'] = 0
with open(out / 'parser-receipt.json', 'xb') as f:
    f.write((json.dumps(receipt, sort_keys=True, separators=(',', ':')) + '\n').encode())
    f.flush(); os.fsync(f.fileno())
raise SystemExit(0 if complete else 1)
'''


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(tmp_path, modes=('complete', 'complete')):
    artifact = tmp_path / 'synthetic.json'
    artifact.write_text('{"synthetic":true}\n')
    frozen = tmp_path / 'synthetic-frozen'
    accepted = tmp_path / 'synthetic-accepted'
    frozen.mkdir()
    accepted.mkdir()
    a = tmp_path / 'parser_a.py'
    b = tmp_path / 'parser_b.py'
    a.write_text(FIXTURE.format(parser_id='a', mode=modes[0]))
    b.write_text(FIXTURE.format(parser_id='b', mode=modes[1]))
    test_receipt = tmp_path / 'synthetic-preflight.json'
    test_receipt.write_text('{"synthetic_fixture_preflight":true}\n')
    freeze = tmp_path / 'freeze.json'
    freeze.write_text(json.dumps(dict(
        schema='worker34-execution-freeze-v1',
        execution_go='Synthetic fixtures only; no research execution authority',
        sources=dict(a=digest(a), b=digest(b), supervisor=digest(SOURCE), protocol=digest(PROTOCOL)),
        runtime=SUP.runtime_fingerprint(),
        reviews=dict(a='synthetic fixture', b='synthetic fixture', supervisor='synthetic fixture'),
        resource_test_receipt=dict(path=str(test_receipt), sha256=digest(test_receipt)))))
    return dict(artifact=str(artifact), frozen=str(frozen), accepted_evidence=str(accepted),
                output_dir=str(tmp_path / 'attempt'), execution_freeze=str(freeze),
                parser_a=str(a), parser_b=str(b), protocol=str(PROTOCOL))


def execute(config, budget=3.0, extra=''):
    # Run a separate supervisor process so child-subreaper state never touches pytest.
    code = f'''import pathlib, runpy, json
s = runpy.run_path({str(SOURCE)!r})
c = s['Config'](**{{k:pathlib.Path(v) for k,v in json.loads({json.dumps(config)!r}).items()}})
{extra}
r=s['run_supervisor'](c,_budget_seconds={budget!r},_grace_seconds=2.0)
print(json.dumps({{'status':r['status']}}))
'''
    result = subprocess.run([sys.executable, '-I', '-B', '-c', code],
                            capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise AssertionError(f'supervisor process failed {result.returncode}: {result.stdout}\n{result.stderr}')
    receipt = json.loads((Path(config['output_dir']) / 'supervisor-receipt.json').read_text())
    return receipt


def assert_no_survivors(receipt):
    assert receipt['cleanup_confirmed'] is True
    for process in receipt.get('process_control', {}).get('observed_pids', []):
        path = Path(f"/proc/{process['pid']}/stat")
        if path.exists():
            # PIDs may be reused; the old birth identity must be gone.
            tail = path.read_text().rsplit(')', 1)[1].split()
            assert int(tail[19]) != process['start_ticks']


def test_production_2gib_limit_effective_without_payload_allocation():
    check = SUP.probe_production_limit()
    assert check == dict(soft=2147483648, hard=2147483648,
                         mechanism='resource.RLIMIT_AS', allocated_test_payload_bytes=0)


def test_serial_success_freezes_sources_and_streams_all_pairs(tmp_path):
    config = prepare(tmp_path)
    receipt = execute(config)
    assert receipt['status'] == 'recorded_component_tradeoff_absent'
    assert receipt['scientific_outputs_accepted'] is True
    assert list(receipt['comparisons']) == sorted(SUP.SCIENTIFIC_FILES)
    assert all(row['equal'] for row in receipt['comparisons'].values())
    assert [row['parser_id'] for row in receipt['parser_executions']] == ['a', 'b']
    assert len(receipt['process_control']['reaped']) == 2
    for row in receipt['parser_executions']:
        assert row['receipt']['rlimit_as_soft'] == row['receipt']['rlimit_as_hard'] == 2147483648
        assert row['command'][1:3] == ['-I', '-B']
    out = Path(config['output_dir'])
    assert digest(out / 'frozen-sources/scripts/worker34_parser_a.py') == digest(config['parser_a'])
    assert digest(out / 'frozen-sources/scripts/worker34_parser_b.py') == digest(config['parser_b'])
    assert_no_survivors(receipt)


def test_reduced_64mib_memoryerror_is_controlled_and_not_integrity(tmp_path):
    config = prepare(tmp_path, ('memory', 'complete'))
    receipt = execute(config)
    assert receipt['status'] == 'resource_incomplete'
    assert receipt['scientific_outputs_accepted'] is False
    child = json.loads((Path(config['output_dir']) / 'parser-a/parser-receipt.json').read_text())
    assert child['errors'] == ['controlled synthetic MemoryError']
    assert child['rlimit_as_soft'] == child['rlimit_as_hard'] == 67108864
    assert not (Path(config['output_dir']) / 'parser-b').exists()
    assert_no_survivors(receipt)


def test_timeout_terminates_and_reaps_term_ignoring_parser(tmp_path):
    config = prepare(tmp_path, ('timeout', 'complete'))
    receipt = execute(config, .25)
    assert receipt['status'] == 'resource_incomplete'
    assert any('deadline' in row['message'] for row in receipt['causes'])
    signals = [row['signal'] for row in receipt['process_control']['signals']]
    assert 15 in signals and 9 in signals
    assert not (Path(config['output_dir']) / 'parser-b').exists()
    assert_no_survivors(receipt)


def test_entire_serial_workload_uses_one_budget(tmp_path):
    config = prepare(tmp_path, ('slow', 'slow'))
    receipt = execute(config, 1.1)
    assert receipt['status'] == 'resource_incomplete'
    assert len(receipt['parser_executions']) == 1
    assert (Path(config['output_dir']) / 'parser-b').exists()
    assert receipt['elapsed_seconds_before_receipt_close'] < 2.0
    assert_no_survivors(receipt)


def check_detached_descendants(tmp_path, mode):
    config = prepare(tmp_path, (mode, 'complete'))
    receipt = execute(config)
    assert receipt['status'] == 'resource_incomplete'
    assert any('descendant' in row['message'] for row in receipt['causes'])
    assert len(receipt['process_control']['observed_pids']) >= 2
    assert len(receipt['process_control']['reaped']) >= 2
    assert_no_survivors(receipt)


def test_completed_byte_mismatch_is_integrity(tmp_path):
    config = prepare(tmp_path, ('complete', 'mismatch'))
    receipt = execute(config)
    assert receipt['status'] == 'integrity_invalid'
    assert receipt['comparisons']['leaves.jsonl']['equal'] is False
    assert len(receipt['comparisons']) == 3
    assert receipt['scientific_outputs_accepted'] is False
    assert_no_survivors(receipt)


def test_completed_integrity_receipt_is_not_resource_failure(tmp_path):
    receipt = execute(prepare(tmp_path, ('integrity', 'complete')))
    assert receipt['status'] == 'integrity_invalid'
    assert {row['status'] for row in receipt['causes']} == {'integrity_invalid'}
    assert_no_survivors(receipt)


def check_missing_output_or_unverified_limit(tmp_path, mode):
    receipt = execute(prepare(tmp_path, (mode, 'complete')))
    assert receipt['status'] == 'resource_incomplete'
    assert_no_survivors(receipt)


def test_hash_mismatch_is_integrity_before_admission(tmp_path):
    config = prepare(tmp_path)
    with open(config['parser_a'], 'a') as handle:
        handle.write('\n# changed after freeze\n')
    receipt = execute(config)
    assert receipt['status'] == 'integrity_invalid'
    assert receipt['admitted'] is False
    assert receipt['parser_executions'] == []


def test_missing_authority_is_blocked_before_admission(tmp_path):
    config = prepare(tmp_path)
    freeze = json.loads(Path(config['execution_freeze']).read_text())
    freeze['execution_go'] = ''
    Path(config['execution_freeze']).write_text(json.dumps(freeze))
    receipt = execute(config)
    assert receipt['status'] == 'execution_blocked'
    assert receipt['admitted'] is False


def test_duplicate_freeze_keys_rejected(tmp_path):
    config = prepare(tmp_path)
    Path(config['execution_freeze']).write_text('{"schema":"x","schema":"y"}')
    receipt = execute(config)
    assert receipt['status'] == 'execution_blocked'
    assert receipt['admitted'] is False


def test_existing_attempt_never_overwritten(tmp_path):
    config = prepare(tmp_path)
    execute(config)
    old = digest(Path(config['output_dir']) / 'supervisor-receipt.json')
    try:
        execute(config)
    except AssertionError as exc:
        assert 'FileExistsError' in str(exc)
    else:
        raise AssertionError('existing attempt was not rejected')
    assert digest(Path(config['output_dir']) / 'supervisor-receipt.json') == old


def test_comparison_is_inside_the_same_watchdog(tmp_path):
    config = prepare(tmp_path)
    extra = """import time
original=s['run_supervisor'].__globals__['compare_streams']
def delayed(*args):
    time.sleep(1)
    return original(*args)
s['run_supervisor'].__globals__['compare_streams']=delayed"""
    receipt = execute(config, .4, extra)
    assert receipt['status'] == 'resource_incomplete'
    assert len(receipt['parser_executions']) == 2
    assert receipt['comparisons'] == {}
    assert_no_survivors(receipt)


def test_final_receipt_closure_is_inside_the_watchdog(tmp_path):
    config = prepare(tmp_path)
    extra = """import time
original=s['run_supervisor'].__globals__['write_exclusive']
once=[True]
def delayed(path,value):
    if path.name == 'supervisor-receipt.pending.json' and once[0]:
        once[0]=False
        time.sleep(1)
    return original(path,value)
s['run_supervisor'].__globals__['write_exclusive']=delayed"""
    receipt = execute(config, .4, extra)
    assert receipt['status'] == 'resource_incomplete'
    assert receipt['scientific_outputs_accepted'] is False
    assert receipt['elapsed_seconds_before_receipt_close'] >= .4
    assert (Path(config['output_dir']) / 'parser-a/ATTEMPT-INCOMPLETE.json').exists()
    assert_no_survivors(receipt)


def test_failure_precedence_retains_all_established_causes():
    causes = [dict(status='execution_blocked', message='missing prerequisite'),
              dict(status='resource_incomplete', message='timeout'),
              dict(status='integrity_invalid', message='confirmed old hash mismatch')]
    assert SUP.failure_label(causes) == 'integrity_invalid'
    assert SUP.failure_label(causes[:2]) == 'resource_incomplete'
    assert SUP.failure_label(causes[:1]) == 'execution_blocked'
    assert len(causes) == 3


def test_streaming_comparison_hashes_full_unequal_lengths(tmp_path):
    left, right = tmp_path / 'left', tmp_path / 'right'
    left.write_bytes(b'a' * (3 * 1024 * 1024 + 7))
    right.write_bytes(b'a' * (3 * 1024 * 1024 + 8))
    result = SUP.compare_streams(left, right)
    assert result['equal'] is False
    assert result['a_sha256'] == digest(left)
    assert result['b_sha256'] == digest(right)
    assert result['a_bytes'] + 1 == result['b_bytes']


def test_detached_descendant_containment(tmp_path):
    check_detached_descendants(tmp_path, 'descendant')


def test_orphan_descendant_containment(tmp_path):
    check_detached_descendants(tmp_path, 'orphan')


def test_missing_output_is_resource_failure(tmp_path):
    check_missing_output_or_unverified_limit(tmp_path, 'missing')


def test_unverified_limit_is_resource_failure(tmp_path):
    check_missing_output_or_unverified_limit(tmp_path, 'bad_runtime')


def test_established_integrity_survives_unverified_runtime(tmp_path):
    receipt = execute(prepare(tmp_path, ('integrity_bad_limit', 'complete')))
    assert receipt['status'] == 'integrity_invalid'
    assert {row['status'] for row in receipt['causes']} == {'integrity_invalid', 'resource_incomplete'}
    assert_no_survivors(receipt)



def check_closure_failure(tmp_path, operation, integrity=False):
    config = prepare(tmp_path, ('integrity', 'complete') if integrity else ('complete', 'complete'))
    extra = """import errno, os
from pathlib import Path
g=s['run_supervisor'].__globals__
once=[True]
operation=OPERATION
if operation in ('file_fsync', 'persistent_fsync'):
    original=os.fsync
    def failing(fd):
        path=os.readlink('/proc/self/fd/'+str(fd))
        target=path.endswith('supervisor-receipt.pending.json')
        if operation == 'persistent_fsync':
            target=target or path.endswith('supervisor-receipt.json') or path.endswith('supervisor-abort-receipt.json')
        if target and (once[0] or operation == 'persistent_fsync'):
            once[0]=False
            raise OSError(errno.ENOSPC,'synthetic final fsync failure')
        return original(fd)
    os.fsync=failing
elif operation == 'directory_fsync':
    original=g['fsync_directory']
    def failing(path):
        if path == c.output_dir and (path / 'supervisor-receipt.json').exists() and once[0]:
            once[0]=False
            raise OSError(errno.ENOSPC,'synthetic final directory fsync failure')
        return original(path)
    g['fsync_directory']=failing
elif operation == 'rename':
    original=Path.rename
    def failing(path,target):
        if path.name == 'supervisor-receipt.pending.json' and once[0]:
            once[0]=False
            raise OSError(errno.ENOSPC,'synthetic final rename failure')
        return original(path,target)
    Path.rename=failing
elif operation == 'partial_write':
    original=g['write_exclusive']
    def failing(path,value):
        if path.name == 'supervisor-receipt.pending.json' and once[0]:
            once[0]=False
            with open(path,'xb') as f: f.write(b'{')
            raise OSError(errno.ENOSPC,'synthetic partial final write failure')
        return original(path,value)
    g['write_exclusive']=failing
""".replace('OPERATION', repr(operation))
    receipt = execute(config, extra=extra)
    assert receipt['status'] == ('integrity_invalid' if integrity else 'resource_incomplete')
    assert receipt['scientific_outputs_accepted'] is False
    assert any(row['status'] == 'resource_incomplete' for row in receipt['causes'])
    assert (Path(config['output_dir']) / 'parser-a/ATTEMPT-INCOMPLETE.json').exists()
    assert list(Path(config['output_dir']).glob('supervisor-receipt*.incomplete'))
    assert_no_survivors(receipt)


def test_final_file_fsync_failure_is_bounded_abort(tmp_path):
    check_closure_failure(tmp_path, 'file_fsync')


def test_final_directory_fsync_failure_is_bounded_abort(tmp_path):
    check_closure_failure(tmp_path, 'directory_fsync')


def test_final_rename_failure_is_bounded_abort(tmp_path):
    check_closure_failure(tmp_path, 'rename')


def test_final_partial_write_failure_is_bounded_abort(tmp_path):
    check_closure_failure(tmp_path, 'partial_write')


def test_persistent_final_fsync_failure_never_leaves_success(tmp_path):
    check_closure_failure(tmp_path, 'persistent_fsync')


def test_closure_failure_preserves_integrity_precedence(tmp_path):
    check_closure_failure(tmp_path, 'file_fsync', integrity=True)


def test_timeout_stops_parser_before_delayed_abort_persistence(tmp_path):
    config = prepare(tmp_path, ('deadline_sentinel', 'complete'))
    extra = """import os,time
original=os.fsync
once=[True]
def slow_fsync(fd):
    path=os.readlink('/proc/self/fd/'+str(fd))
    if path.endswith('events.jsonl') and once[0]:
        once[0]=False
        time.sleep(.6)
    return original(fd)
os.fsync=slow_fsync"""
    receipt=execute(config,.25,extra)
    assert receipt['status'] == 'resource_incomplete'
    assert receipt['elapsed_seconds_before_receipt_close'] >= .85
    assert not (Path(config['output_dir']) / 'parser-a/LATE-SENTINEL').exists()
    assert_no_survivors(receipt)


def test_malformed_administrative_mappings_are_blocked(tmp_path):
    malformed = [(None, value) for value in ([], None, True, 3, 'wrong', {})]
    malformed += [(field, value) for field in ('reviews','sources','runtime','resource_test_receipt')
                  for value in (None, [], 'wrong')]
    for index, (field, value) in enumerate(malformed):
        directory = tmp_path / str(index)
        directory.mkdir()
        config=prepare(directory)
        path=Path(config['execution_freeze'])
        current=json.loads(path.read_text())
        if field is None:
            current=value
        else:
            current[field]=value
        path.write_text(json.dumps(current))
        receipt=execute(config)
        assert receipt['status'] == 'execution_blocked'
        assert receipt['admitted'] is False
        assert receipt['scientific_outputs_accepted'] is False
        assert receipt['parser_executions'] == []



def check_cleanup_exception(tmp_path, integrity=False):
    config=prepare(tmp_path, ('integrity', 'complete') if integrity else ('timeout', 'complete'))
    extra = """import errno,time,signal
C=s['Containment']
original_send=C.send
def broken_cleanup(self,until):
    self.original_cleanup_deadline=until
    time.sleep(.08)
    raise OSError(errno.EIO,'synthetic cleanup inspection failure')
def checked_send(self,signum):
    if hasattr(self,'original_cleanup_deadline'):
        # This would fail if recovery reset the original abort grace.
        available=max(0,self.original_cleanup_deadline-time.monotonic())
        assert signal.getitimer(signal.ITIMER_REAL)[0] <= available+.02
    return original_send(self,signum)
C.cleanup=broken_cleanup
C.send=checked_send"""
    receipt=execute(config,.25 if not integrity else 3.0,extra)
    assert receipt['status'] == ('integrity_invalid' if integrity else 'resource_incomplete')
    assert receipt['scientific_outputs_accepted'] is False
    assert receipt['admitted'] is True
    assert receipt['cleanup_confirmed'] is False
    assert receipt['cleanup_recovery_confirmed'] is True
    assert receipt['cleanup_errors'] == ['[Errno 5] synthetic cleanup inspection failure']
    for field in ('process_control','source_sha256','runtime','parser_executions'):
        assert field in receipt
    assert receipt['runtime'] == SUP.runtime_fingerprint()
    freeze=json.loads(Path(config['execution_freeze']).read_text())
    assert receipt['source_sha256'] == freeze['sources']
    assert receipt['process_control']['reaped']
    assert receipt['elapsed_seconds_before_receipt_close'] < 2.25
    assert_no_survivors({**receipt,'cleanup_confirmed':receipt['cleanup_recovery_confirmed']})


def test_cleanup_exception_preserves_provenance_and_recovers_in_original_grace(tmp_path):
    check_cleanup_exception(tmp_path)


def test_cleanup_exception_preserves_established_integrity(tmp_path):
    check_cleanup_exception(tmp_path,integrity=True)


def check_portable_test_import(tmp_path, override):
    temp_root=tmp_path / 'portable-tmp'
    temp_root.mkdir()
    explicit=tmp_path / 'explicit-evidence'
    code=f"""import os,pathlib,runpy,tempfile,json
os.environ.pop('WORKER34_SYNTHETIC_RECEIPTS',None)
if {override!r}: os.environ['WORKER34_SYNTHETIC_RECEIPTS']={str(explicit)!r}
tempfile.tempdir={str(temp_root)!r}
original=pathlib.Path.mkdir
def forbidden(*args,**kwargs):
    raise AssertionError('module import attempted a directory creation')
pathlib.Path.mkdir=forbidden
module=runpy.run_path({str(Path(__file__).resolve())!r})
assert module['_EVIDENCE_ROOT'] is None
pathlib.Path.mkdir=original
root=module['evidence_root']()
assert module['evidence_root']() == root
assert root.is_dir()
if {override!r}:
    assert root == pathlib.Path({str(explicit)!r})
else:
    assert root.parent == pathlib.Path({str(temp_root)!r})
print(json.dumps({{'root':str(root)}}))
"""
    completed=subprocess.run([sys.executable,'-I','-B','-c',code],
                             capture_output=True,text=True,timeout=10)
    assert completed.returncode == 0, completed.stderr
    root=Path(json.loads(completed.stdout)['root'])
    assert root == explicit if override else root.parent == temp_root


def test_module_import_is_write_free_and_default_root_is_portable(tmp_path):
    check_portable_test_import(tmp_path,False)


def test_explicit_evidence_root_is_lazy_and_shared(tmp_path):
    check_portable_test_import(tmp_path,True)



def test_verified_shared_library_launch_environment_is_minimal(tmp_path):
    compiler=shutil.which('cc') or shutil.which('gcc')
    if not compiler:
        raise unittest.SkipTest('installed C compiler unavailable for harmless loader fixture')
    directory=tmp_path / 'lib'
    directory.mkdir()
    library=directory / 'libworker34_loader_fixture.so'
    source=tmp_path / 'library.c'
    source.write_text('int worker34_fixture(void) { return 0; }\n')
    launcher=tmp_path / 'launcher.c'
    launcher.write_text('#include <stdio.h>\nextern int worker34_fixture(void);\n'
                        'int main(void) { puts("worker34-isolated-runtime-launch-ok"); return worker34_fixture(); }\n')
    executable=tmp_path / 'synthetic-interpreter'
    for command in ([compiler,'-shared','-fPIC','-Wl,-soname,'+library.name,'-o',str(library),str(source)],
                    [compiler,'-o',str(executable),str(launcher),'-L'+str(directory),'-lworker34_loader_fixture']):
        result=subprocess.run(command,capture_output=True,text=True,timeout=15)
        assert result.returncode == 0, result.stderr
    clean={'PATH':os.defpath,'LANG':'C.UTF-8'}
    failed=subprocess.run([str(executable)],env=clean,capture_output=True,text=True,timeout=5)
    assert failed.returncode != 0
    assert library.name in failed.stderr
    # Map the exact synthetic library so the same inode/path verification used
    # for the running interpreter can be exercised without touching that interpreter.
    loaded=ctypes.CDLL(str(library))
    assert loaded.worker34_fixture() == 0
    configured={'LIBDIR':str(directory),'INSTSONAME':library.name,'LDLIBRARY':library.name}
    ambient={'LD_LIBRARY_PATH':str(directory)+os.pathsep+'/unrelated/private-loader-dir',
             'WORKER34_FAKE_SECRET':'must-not-pass','PYTHONPATH':'/untrusted-python','LD_PRELOAD':'/untrusted.so'}
    with mock.patch.object(SUP.sysconfig,'get_config_var',side_effect=lambda key:configured.get(key)), \
         mock.patch.dict(os.environ,ambient):
        environment,libraries=SUP.verified_launch_environment(executable)
    assert environment == {**clean,'LD_LIBRARY_PATH':str(directory.resolve())}
    assert libraries == {str(library.resolve()):digest(library)}
    succeeded=subprocess.run([str(executable)],env=environment,capture_output=True,text=True,timeout=5)
    assert succeeded.returncode == 0
    assert succeeded.stdout.strip() == 'worker34-isolated-runtime-launch-ok'
    SUP.write_exclusive(tmp_path / 'loader-regression.json',
        dict(synthetic_only=True,clean_returncode=failed.returncode,clean_stderr=failed.stderr,
             verified_returncode=succeeded.returncode,launch_environment=environment,
             loader_library_sha256=libraries))


def test_runtime_freeze_binds_launch_environment_and_library_hashes(tmp_path):
    config=prepare(tmp_path)
    freeze=json.loads(Path(config['execution_freeze']).read_text())
    freeze['runtime']['loader_library_sha256']={'/synthetic/changed-loader.so':'0'*64}
    Path(config['execution_freeze']).write_text(json.dumps(freeze))
    receipt=execute(config)
    assert receipt['status'] == 'execution_blocked'
    assert receipt['admitted'] is False
    assert receipt['parser_executions'] == []


def test_unneeded_ambient_environment_is_not_forwarded():
    with mock.patch.dict(os.environ,{'WORKER34_FAKE_SECRET':'do-not-forward','PYTHONPATH':'/untrusted'}):
        environment,libraries=SUP.verified_launch_environment(Path(sys.executable).resolve())
    assert set(environment) <= {'PATH','LANG','LD_LIBRARY_PATH'}
    assert 'WORKER34_FAKE_SECRET' not in environment and 'PYTHONPATH' not in environment
    if 'LD_LIBRARY_PATH' in environment:
        assert libraries


def fixture_diagnostics(location):
    sections=[]
    for path in sorted(location.rglob('parser-*.log')):
        sections.append(str(path)+':\n'+path.read_bytes()[:8192].decode('utf-8','replace'))
    for path in sorted(location.rglob('supervisor-receipt.json')):
        try:
            receipt=json.loads(path.read_text())
            sections.append(str(path)+': '+json.dumps(dict(status=receipt.get('status'),
                causes=receipt.get('causes'),parser_executions=receipt.get('parser_executions')),sort_keys=True))
        except (OSError,ValueError):
            pass
    return '\n'.join(sections)


def test_synthetic_failure_diagnostics_include_child_stderr(tmp_path):
    config=prepare(tmp_path,('early_exit','complete'))
    receipt=execute(config)
    assert receipt['status'] == 'resource_incomplete'
    diagnostics=fixture_diagnostics(tmp_path)
    assert 'synthetic dynamic-loader startup diagnostic' in diagnostics
    assert '127' in diagnostics


RUN_FIXTURES = []
_EVIDENCE_ROOT = None


def evidence_root():
    """Create one portable output root lazily, never during test collection."""
    global _EVIDENCE_ROOT
    if _EVIDENCE_ROOT is None:
        override = os.environ.get('WORKER34_SYNTHETIC_RECEIPTS')
        if override:
            root = Path(override)
            root.mkdir(parents=True, exist_ok=True)
        else:
            root = Path(tempfile.mkdtemp(prefix='worker34-supervisor-synthetic-'))
        _EVIDENCE_ROOT = root
    return _EVIDENCE_ROOT


class NativeSyntheticTests(unittest.TestCase):
    """Standalone stdlib adapter; fixture artifacts deliberately remain preserved."""


def _install_native_tests():
    for name, function in list(globals().items()):
        if name.startswith('test_') and callable(function):
            def invoke(self, function=function, name=name):
                if 'tmp_path' in inspect.signature(function).parameters:
                    location = Path(tempfile.mkdtemp(prefix=name + '-', dir=evidence_root()))
                    RUN_FIXTURES.append(location)
                    try:
                        function(location)
                    except unittest.SkipTest:
                        raise
                    except Exception as error:
                        raise AssertionError(f'{name} failed: {error}\n{fixture_diagnostics(location)}') from error
                else:
                    function()
            setattr(NativeSyntheticTests, name, invoke)
            globals().pop(name)


_install_native_tests()

if __name__ == '__main__':
    began = time.monotonic()
    outcome = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NativeSyntheticTests))
    manifest = dict(schema='worker34-supervisor-synthetic-tests-v1',
                    synthetic_only=True, tests_run=outcome.testsRun,
                    failures=len(outcome.failures), errors=len(outcome.errors),
                    skipped=[dict(test=str(test), reason=reason) for test, reason in outcome.skipped],
                    successful=outcome.wasSuccessful(), elapsed_seconds=time.monotonic()-began,
                    supervisor_sha256=digest(SOURCE), test_source_sha256=digest(__file__),
                    protocol_sha256=digest(PROTOCOL), runtime=SUP.runtime_fingerprint(),
                    production_limit_probe=SUP.probe_production_limit(),
                    reduced_test_address_space_bytes=67108864,
                    fixtures=[dict(directory=str(path),
                                   supervisor_receipt_sha256=digest(path / 'attempt/supervisor-receipt.json'))
                              for path in RUN_FIXTURES
                              if (path / 'attempt/supervisor-receipt.json').is_file()])
    output = evidence_root()
    receipt = output / ('suite-receipt-' + str(time.time_ns()) + '.json')
    SUP.write_exclusive(receipt, manifest)
    print('Synthetic suite receipt:', receipt)
    print('SHA256:', digest(receipt))
    raise SystemExit(0 if outcome.wasSuccessful() else 1)
