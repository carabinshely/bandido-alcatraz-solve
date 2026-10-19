"""CI-only real filesystem regressions; no project imports or policy calls."""
import argparse
import importlib.util
import json
import resource
from pathlib import Path
import shutil
import sys


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--driver', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--work-root', type=Path, required=True)
    a = p.parse_args()
    resource.setrlimit(resource.RLIMIT_FSIZE, (65536, 65536))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
    spec = importlib.util.spec_from_file_location('cost02_gate_driver', a.driver)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)  # definitions/stdlib only; never main().
    manifest = json.loads(a.manifest.read_bytes())
    driver.verify_sources(a.source_root, manifest)
    a.work_root.mkdir(mode=0o700, exist_ok=False)
    shutil.copytree(a.source_root / 'src', a.work_root / 'src', symlinks=True)
    driver.verify_sources(a.work_root, manifest)
    cache = a.work_root / 'src/bandido_alcatraz/__pycache__'
    target = a.work_root / 'empty-external-cache'
    target.mkdir(mode=0o700)
    passed = []
    for kind in ('cache_directory_symlink', 'dangling_directory_symlink', 'unexpected_empty_directory'):
        if kind == 'cache_directory_symlink':
            cache.symlink_to(target, target_is_directory=True)
        elif kind == 'dangling_directory_symlink':
            cache.symlink_to(a.work_root / 'never-created-target', target_is_directory=True)
        else:
            cache.mkdir(mode=0o700)
        try:
            driver.verify_sources(a.work_root, manifest)
        except RuntimeError as error:
            expected = 'UNEXPECTED_SOURCE_DIRECTORY' if kind == 'unexpected_empty_directory' else 'SOURCE_ENTRY_SYMLINK'
            assert str(error) == expected
            passed.append(kind)
        else:
            raise AssertionError('source gate accepted ' + kind)
        if kind == 'unexpected_empty_directory':
            cache.rmdir()
        else:
            cache.unlink()
        driver.verify_sources(a.work_root, manifest)
    target.rmdir()
    assert not any(k == 'bandido_alcatraz' or k.startswith('bandido_alcatraz.') for k in sys.modules)
    print(json.dumps(dict(status='SOURCE_GATE_CASES_PASS', cases=passed, project_imports=0)))


if __name__ == '__main__':
    main()
