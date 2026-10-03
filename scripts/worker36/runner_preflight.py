"""Branch-only zero-evaluator runtime/static/stub preflight; never admission."""
from __future__ import annotations

import argparse
import ast
import importlib.abc
import io
import os
from pathlib import Path
import resource
import subprocess
import sys
import unittest

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from worker36 import common as c
from worker36 import sources as s
from worker36 import driver as d

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = 'experiments/synthetic-profile-overhead/'
MEMORY = (512 * 1024 ** 2,) * 2
TEST_MODULES = (
    'test_worker36_core', 'test_worker36_supervision', 'test_worker36_transport',
    'test_worker36_admission_integration', 'test_worker36_cell_integration',
    'test_worker36_driver_integration', 'test_worker36_verify_integration',
    'test_worker36_runner_preflight',
)
ZERO = {'preparation_only': True, 'measurement_admitted': False,
        'candidate_evaluator_calls': 0, 'reference_evaluator_calls': 0,
        'measurement_fixture_constructions': 0, 'historical_source_imports': 0, 'games': 0}


def limits():
    return {name: list(resource.getrlimit(getattr(resource, name)))
            for name in dir(resource) if name.startswith('RLIMIT_')}


def runtime_probe(*, child=False):
    c.require(dict(os.environ) == c.clean_environment(), 'preflight environment is not sanitized')
    before = c.runtime_check(child=child)
    inherited = limits()
    if not child:
        c.require(resource.getrlimit(resource.RLIMIT_AS) == (resource.RLIM_INFINITY,) * 2,
                  'unexpected initial preflight address-space ceiling')
        resource.setrlimit(resource.RLIMIT_AS, MEMORY)
    c.require(resource.getrlimit(resource.RLIMIT_AS) == MEMORY, 'exact512MiB preflight memory cap')
    return {'pid': os.getpid(), 'parent_pid': os.getppid(), 'initial_runtime': before,
            'inherited_limits': inherited, 'runtime': c.runtime_check(child=True),
            'capped_limits': limits(), 'sanitized_environment': True, **ZERO}


def write_json(path, value):
    # Exclusive output names prevent silently replacing any failed observation.
    with Path(path).open('xb') as stream:
        stream.write(c.canonical(value)); stream.flush(); os.fsync(stream.fileno())
    c.fsync_directory(Path(path).parent)


def spawn_probe(folder, parent):
    folder = Path(folder)
    report = folder / 'fresh-child.json'
    c.require(not report.exists(), 'fresh child report already exists')
    command = [str(Path(sys.executable).resolve()), '-B', '-s', str(Path(__file__).resolve()),
               '--child', '--report', str(report)]
    env = c.clean_environment()
    for key in ('GH_TOKEN', 'GITHUB_TOKEN', 'ACTIONS_RUNTIME_TOKEN'):
        env.pop(key, None)
    process = subprocess.Popen(command, env=env, cwd=ROOT,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        stdout, stderr = process.communicate()
    for name, raw in (('fresh-child.stdout', stdout), ('fresh-child.stderr', stderr)):
        with (folder / name).open('xb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    write_json(folder / 'fresh-child-process.json', {'command': command, 'pid': process.pid,
               'returncode': process.returncode, 'timed_out': timed_out, **ZERO})
    c.require(not timed_out and process.returncode == 0, 'sanitized fresh child startup failed')
    proof = c.strict_json(report.read_bytes())
    c.require(proof['pid'] == process.pid and proof['parent_pid'] == os.getpid(), 'fresh child identity mismatch')
    keys = ('implementation', 'version', 'executable_sha256', 'executable', 'effective_flags',
            'python_environment', 'gc_enabled', 'gc_threshold', 'address_space')
    c.require(all(proof['runtime'][key] == parent['runtime'][key] for key in keys),
              'fresh child runtime differs from parent')
    c.require(proof['inherited_limits'] == parent['capped_limits'] == proof['capped_limits'] and
              proof['sanitized_environment'] is True and all(proof[key] == value for key, value in ZERO.items()),
              'fresh child environment, limits or zero-call boundary differs')
    return proof


def checked_paths(root):
    root = Path(root)
    test_paths = {p.relative_to(root).as_posix() for p in (root / 'tests').glob('test_worker36_*.py')}
    c.require(test_paths == {'tests/' + name + '.py' for name in TEST_MODULES},
              'focused test files differ from explicit allowlist')
    return sorted(test_paths | {p.relative_to(root).as_posix() for p in (root / 'scripts/worker36').glob('*.py')}
                  | {p.relative_to(root).as_posix() for p in (root / 'evidence-design').glob('*-test-plan.json')}
                  | {'scripts/run_worker36_synthetic.py', 'tests/worker36_constructor_source.txt',
                     '.github/workflows/worker36-synthetic-profile.yml', '.github/workflows/worker36-runner-preflight.yml',
                     EXPERIMENT + 'PROTOCOL.md', EXPERIMENT + 'source-manifest.json',
                     EXPERIMENT + 'fault-test-manifest.json', d.TEST_RECEIPT.relative_to(d.ROOT).as_posix()})


def snapshot(root):
    result = {}
    for name in checked_paths(root):
        path = Path(root) / name
        c.require(not any(p.is_symlink() for p in (path, *path.parents)), 'symlink in checked source path')
        result[name] = c.file_info(path)['sha256']
        if path.suffix == '.py':
            ast.parse(path.read_bytes(), filename=name)
        elif path.suffix == '.json':
            c.strict_json(path.read_bytes())
    return result


def static_check(root, expected_head, expected_tree):
    root = Path(root)
    c.require(s.git(root, 'rev-parse', 'HEAD').decode().strip() == expected_head and
              s.git(root, 'rev-parse', 'HEAD^{tree}').decode().strip() == expected_tree, 'exact checkout head/tree mismatch')
    c.require(s.git(root, 'status', '--porcelain', '--untracked-files=normal') == b'', 'dirty preflight checkout')
    receipt_path = root / d.TEST_RECEIPT.relative_to(d.ROOT)
    d.verify_test_receipt(root, c.file_info(receipt_path)['sha256'])
    pins = snapshot(root)
    c.require(pins[EXPERIMENT + 'PROTOCOL.md'] == c.PROTOCOL_SHA256, 'canonical protocol drift')
    manifest = s.read_manifest(root / (EXPERIMENT + 'source-manifest.json'))
    names = {entry['module'] for entry in manifest['files']}
    c.require(all(set(entry['imports']) <= names for entry in manifest['files']) and
              set(manifest['roots']) <= names, 'historical static closure incomplete')
    for entry in manifest['files']:
        c.require(s.git(root, 'rev-parse', c.HISTORICAL + ':' + entry['path']).decode().strip() == entry['git_blob'],
                  'historical source tree identity mismatch')
        raw = s.git(root, 'cat-file', 'blob', entry['git_blob'])
        s.verify_blob(raw, entry)
        ast.parse(raw, filename=entry['path'])
        if entry['module'] == 'benchmark_worker35_synthetic':
            s.verify_constructor(raw, manifest['constructor'])
    return pins, names


class NoHistoricalImports(importlib.abc.MetaPathFinder):
    def __init__(self, names):
        self.names = set(names)

    def find_spec(self, fullname, path=None, target=None):
        c.require(fullname not in self.names and not fullname.startswith('bandido_alcatraz'),
                  'historical source import prohibited in runner preflight')
        return None

    def check_loaded(self):
        c.require(not any(name in self.names or name.startswith('bandido_alcatraz') for name in sys.modules),
                  'historical source already imported in runner preflight')


def run_focused_tests(root, historical_names):
    guard = NoHistoricalImports(historical_names)
    guard.check_loaded()
    sys.meta_path.insert(0, guard)
    old_path = list(sys.path)
    sys.path.insert(0, str(Path(root) / 'tests'))
    output = io.StringIO()
    try:
        # The literal allowlist is the only test entrypoint. Never discover.
        suite = unittest.defaultTestLoader.loadTestsFromNames(TEST_MODULES)
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
        guard.check_loaded()
    finally:
        sys.path[:] = old_path
        sys.meta_path.remove(guard)
    return {'success': result.wasSuccessful() and not result.skipped,
            'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
            'skipped': len(result.skipped), 'test_modules': list(TEST_MODULES),
            'log': output.getvalue(), **ZERO}


def preflight(folder, expected_head, expected_tree, report):
    report['parent'] = runtime_probe()
    write_json(Path(folder) / 'parent-runtime.json', report['parent'])
    report['fresh_child'] = spawn_probe(folder, report['parent'])
    before, names = static_check(ROOT, expected_head, expected_tree)
    report['checked_file_sha256'] = before
    report['focused_source_receipt'] = {'path': d.TEST_RECEIPT.relative_to(d.ROOT).as_posix(),
                                        **c.file_info(d.TEST_RECEIPT)}
    result = run_focused_tests(ROOT, names)
    report['focused_tests'] = result
    c.require(result['success'] and result['tests_run'] > 0 and
              result['failures'] == result['errors'] == result['skipped'] == 0, 'focused stub tests did not pass')
    c.require(snapshot(ROOT) == before, 'checked sources changed during focused stub tests')
    report['checked_sources_unchanged_during_run'] = True
    report['success'] = True
    report['status'] = 'preparation_passed'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child', action='store_true')
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--expected-head')
    parser.add_argument('--expected-tree')
    args = parser.parse_args(argv)
    record = {'schema': 'worker36-runner-preflight-v1', 'success': False,
              'status': 'execution_blocked', 'diagnostic_head': args.expected_head,
              'diagnostic_tree': args.expected_tree,
              'repository': os.environ.get('GITHUB_REPOSITORY'), 'runner_name': os.environ.get('RUNNER_NAME'),
              'workflow_run': os.environ.get('GITHUB_RUN_ID'), 'workflow_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
              'event_name': os.environ.get('GITHUB_EVENT_NAME'), **ZERO}
    try:
        if args.child:
            record = runtime_probe(child=True)
        else:
            c.require(args.expected_head and args.expected_tree, 'exact head/tree required')
            preflight(args.report.parent, args.expected_head, args.expected_tree, record)
    except Exception as error:
        record.update(success=False, status='execution_blocked', error_type=type(error).__name__, error=str(error)[:4096])
        write_json(args.report, record)
        return 1
    write_json(args.report, record)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
