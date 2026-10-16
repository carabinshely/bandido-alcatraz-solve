"""ONE invented n=16 position, direct candidate/reference cost; CI admission required.

No games, real deck, cohort seeds, production AuditPolicy or improvement claim.
The caller must supply an exclusive reviewed bandido-alcatraz-ci workspace and
an exact root admission. A source hash or this program is not that authority.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import stat
import sys
import time
import traceback

TOTAL_BYTES = 4 * 1024 * 1024
TERMINAL_RESERVE = 65536
OP_LIMIT = 32768
FIXTURE_PLACEMENTS = 16
EXPECTED_EXE = 'a15ccdaf07655a8667a3687b13171486c9a265d92273ba3ad820fbb64d2cfecc'


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode() + b'\n'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_sources(root, manifest):
    expected = {row['path']: row for row in manifest['files']}
    directories = {'src'}
    for relative in expected:
        directories.update(p.as_posix() for p in Path(relative).parents if p.as_posix() != '.')
    actual = set()
    require(not (root / 'src').is_symlink() and (root / 'src').is_dir(), 'SOURCE_ROOT_KIND')
    def walk_error(error):
        raise error
    for parent, dirs, names in os.walk(root / 'src', followlinks=False, onerror=walk_error):
        for name in dirs + names:
            entry = Path(parent) / name
            relative = entry.relative_to(root).as_posix()
            mode = entry.lstat().st_mode
            require(not stat.S_ISLNK(mode), 'SOURCE_ENTRY_SYMLINK')
            if stat.S_ISDIR(mode):
                require(relative in directories, 'UNEXPECTED_SOURCE_DIRECTORY')
            else:
                require(stat.S_ISREG(mode) and relative in expected, 'UNEXPECTED_SOURCE_ENTRY')
                actual.add(relative)
    require(len(expected) == 33 and actual == set(expected), 'SOURCE_SET_CHANGED')
    total = 0
    for relative, row in expected.items():
        require(relative.startswith('src/bandido_alcatraz/') and '..' not in Path(relative).parts,
                'SOURCE_PATH')
        path = root / relative
        require(not path.is_symlink() and not any(p.is_symlink() for p in path.parents),
                'SOURCE_SYMLINK')
        require(0 < row['bytes'] <= 32768, 'SOURCE_SIZE_BOUND')
        with path.open('rb') as stream:
            raw = stream.read(row['bytes'] + 1)
        require(len(raw) == row['bytes'] and digest(raw) == row['sha256'], 'SOURCE_BYTES')
        blob = b'blob ' + str(len(raw)).encode() + b'\0' + raw
        require(hashlib.sha1(blob).hexdigest() == row['git_blob'], 'SOURCE_GIT_BLOB')
        total += len(raw)
    require(total == 231929, 'SOURCE_TOTAL')


class Evidence:
    def __init__(self, folder):
        folder.mkdir(mode=0o700, parents=False, exist_ok=False)
        self.folder = folder
        self.total = 0
        self.rows = []

    def write(self, name, value, terminal=False):
        raw = canonical(value)
        limit = TOTAL_BYTES if terminal else TOTAL_BYTES - TERMINAL_RESERVE
        require(self.total + len(raw) <= limit, 'EVIDENCE_CAP_NO_TRUNCATION')
        began = time.monotonic()
        with (self.folder / name).open('xb') as stream:
            require(stream.write(raw) == len(raw), 'SHORT_EVIDENCE_WRITE')
            stream.flush()
            os.fsync(stream.fileno())
        self.total += len(raw)
        row = dict(name=name, bytes=len(raw), sha256=digest(raw),
                   write_flush_seconds=time.monotonic() - began)
        self.rows.append(row)
        return row


def timeout(signum, frame):
    raise TimeoutError('FIXED_DIAGNOSTIC_WALL_BOUND')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
            'REQUIRE_PYTHON_I_S_B')
    require(sys.platform == 'linux' and sys.version_info[:3] == (3, 11, 16), 'RUNTIME_VERSION')
    require(digest(Path(sys.executable).resolve().read_bytes()) == EXPECTED_EXE, 'RUNTIME_EXE_PIN')
    os.umask(0o077)
    for kind, bound in ((resource.RLIMIT_AS, 512 * 1024 * 1024),
                        (resource.RLIMIT_CPU, 600), (resource.RLIMIT_NOFILE, 64),
                        (resource.RLIMIT_FSIZE, TOTAL_BYTES)):
        resource.setrlimit(kind, (bound, bound))
        require(resource.getrlimit(kind) == (bound, bound), 'NATIVE_LIMIT_NOT_ENFORCED')
    signal.signal(signal.SIGALRM, timeout)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGALRM})
    require(time.monotonic() - whole_started < 600, 'WHOLE_STARTUP_BUDGET')
    signal.alarm(max(1, int(600 - (time.monotonic() - whole_started))))
    evidence = Evidence(args.output_dir)
    try:
        require(args.manifest.stat().st_size <= 16384, 'MANIFEST_SIZE')
        raw = args.manifest.read_bytes()
        require(digest(raw) == args.manifest_sha256, 'MANIFEST_PIN')
        manifest = json.loads(raw)
        require(manifest['schema'] == 'strategy-cost01-source-pins-v1' and
                manifest['commit'] == '7ac2f62c9c5c9dcac9ec9b8770382960f985acc2', 'SUBJECT_PIN')
        root = args.source_root.resolve(strict=True)
        verify_sources(root, manifest)
        require(not any(k == 'bandido_alcatraz' or k.startswith('bandido_alcatraz.')
                        for k in sys.modules), 'PRELOADED_PROJECT_MODULE')
        sys.path.insert(0, str(root / 'src'))
        from random import Random
        from bandido_alcatraz.board import Board
        from bandido_alcatraz.game import GameState
        from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
        from bandido_alcatraz.setup import SOLO_EASY
        from bandido_alcatraz import quota_reserve_closure as candidate
        from bandido_alcatraz import quota_reserve_closure_reference as reference
        from bandido_alcatraz.worker32.evidence import observation, move
        verify_sources(root, manifest)
        N, E, S, W = Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST

        def card(name, edges=(), material=None, exit=False):
            return CardDefinition(name, (CellSpec(0, 0, frozenset(edges), False),), material, exit)

        start = CardDefinition('start_easy', (CellSpec(0, 0, frozenset((W, N, E))),
                                             CellSpec(1, 0, frozenset((W, N, E, S)))))
        coats = [card('coat-' + str(i), (W,), Material.RAINCOAT) for i in range(12)]
        ropes = [card('rope-' + str(i), (W,), Material.ROPE) for i in range(8)]
        ordinary = [card('ordinary-' + str(i), (N, E, S, W) if i < 16 else ()) for i in range(48)]
        exit_card = card('exit', (W,), exit=True)
        catalog = tuple(coats + ropes + ordinary + [exit_card])
        board = Board()
        board.seed(start)
        for i in range(FIXTURE_PLACEMENTS):
            board.place(ordinary[i], (2 + i, 0), 0)
        used = {c.card_id for c in coats[:6] + ordinary[:16]}
        state = GameState(board=board, hand=list(coats[:6]),
                          draw_pile=[c for c in catalog if c.card_id not in used],
                          turns=16, setup=SOLO_EASY)
        public = state.observation()
        before = canonical(observation(public))
        evidence.write('fixture.json', dict(kind='NEW_INVENTED_N16_NOT_REAL_DECK',
                       public=json.loads(before), source_commit=manifest['commit'],
                       manifest_sha256=digest(raw), runtime_executable_sha256=EXPECTED_EXE,
                       purpose='DIRECT_POLICY_COST_NOT_FULL_AUDITPOLICY_OR_GAME_FIT'))
        inputs = dict(catalog=catalog, start_card=start, exit_card=exit_card)
        results = []
        for label, module, cls in (('candidate', candidate, candidate.QuotaReserveClosurePolicy),
                                  ('reference', reference, reference.QuotaReserveClosureReference)):
            require(sys.getprofile() is None, 'UNEXPECTED_PROFILE_HOOK')
            evidence.write(label + '-intent.json', dict(call=label, status='STARTED_ONE_SHOT'))
            remaining = 600 - (time.monotonic() - whole_started)
            require(remaining >= 1, 'WHOLE_DIAGNOSTIC_BUDGET')
            began, cpu = time.monotonic(), time.process_time()
            signal.alarm(max(1, int(min(180, remaining))))
            policy = cls(**inputs)
            chosen, science, operations = policy.evaluate(public, Random(11), limits=module.OperationLimits(
                legal_enumerations=OP_LIMIT, previews=OP_LIMIT, exit_geometry_checks=OP_LIMIT))
            remaining = 600 - (time.monotonic() - whole_started)
            require(remaining >= 1, 'WHOLE_DIAGNOSTIC_BUDGET')
            signal.alarm(int(remaining))
            elapsed, cpu_used = time.monotonic() - began, time.process_time() - cpu
            require(sys.getprofile() is None, 'PROFILE_HOOK_NOT_RESTORED')
            require(canonical(observation(public)) == before, 'PUBLIC_INPUT_MUTATED')
            encode_start = time.monotonic()
            science_bytes = canonical(science)
            encode_seconds = time.monotonic() - encode_start
            result = dict(call=label, chosen=move(chosen), science=science, operations=operations,
                          wall_seconds=elapsed, cpu_seconds=cpu_used,
                          science_encode_seconds=encode_seconds, science_bytes=len(science_bytes),
                          science_sha256=digest(science_bytes),
                          peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            evidence.write(label + '-result.json', result)
            results.append(result)
            verify_sources(root, manifest)
        require(results[0]['science'] == results[1]['science'] and
                results[0]['chosen'] == results[1]['chosen'], 'ENTIRE_DECISION_DISAGREEMENT')
        evidence.write('result.json', dict(status='INVENTED_PAIR_AGREED', games=0,
                       whole_seconds=time.monotonic() - whole_started, journal=evidence.rows[:],
                       science=False, full_game_fit=False, speedup_claim=False), terminal=True)
        return 0
    except BaseException as exc:
        evidence.write('failure.json', dict(status='INCOMPLETE', error_type=type(exc).__name__,
                       traceback=traceback.format_exc(), journal=evidence.rows[:], games=0), terminal=True)
        raise


if __name__ == '__main__':
    whole_started = time.monotonic()
    raise SystemExit(main())
