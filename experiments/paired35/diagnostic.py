"""Fixed 100-pair public visible-water priority policy versus V4-250; CI-only under root GO."""
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

TOTAL_BYTES = 1024 * 1024 * 1024
FILE_BYTES = 64 * 1024 * 1024
JOURNAL_RECORDS = 1200
TERMINAL_RESERVE = 4 * 1024 * 1024
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
    require(total == 197454, 'SOURCE_TOTAL')



def timeout(signum, frame):
    raise TimeoutError('FIXED_DIAGNOSTIC_WALL_BOUND')



SEEDS = tuple(range(1000739, 1000839))
CODEC_SHA = '0f855d6aec8e970458d6aa0192f681c5e3fcd7c15c93dfc03a3eeff8c7a16e68'
ISSUANCE_SHA = 'c72c31274cc531b9688a524fb6d6c6ae9b998453ea3fe0cbbd96cad0c8a72882'
WHOLE_SECONDS = 14400
BOUNDS_SHA = '0377da69625b9d8c0c04ed946342b89499d1a956851e62c44378521fd0bce5cd'
DATA = {
    'deck-v1.json': (35723, '31ea3a727f082f9f6bdd971b278b24e4b5cc004a162170e198d084726ff1e89a'),
    'deck-observations-v0.json': (4830, 'e967ca41b5ebf5883c89426c517a63e3965ad36e0e9975a0b6311cb7de20d985'),
}


def check_data(root):
    require((root / 'data').is_dir() and not (root / 'data').is_symlink(), 'DATA_DIRECTORY')
    for name, (size, sha) in DATA.items():
        path = root / 'data' / name
        require(not path.is_symlink() and stat.S_ISREG(path.lstat().st_mode), 'DATA_KIND')
        with path.open('rb') as stream:
            raw = stream.read(size + 1)
        require(len(raw) == size and digest(raw) == sha, 'ORIGINAL_DATA_PIN')


def deadline(seconds=180):
    remaining = WHOLE_SECONDS - (time.monotonic() - whole_started)
    require(remaining >= 1, 'WHOLE_GAME_BUDGET')
    signal.alarm(max(1, int(min(seconds, remaining))))


def v4_counterfactual(audit, rng_state):
    """Frozen V4-250 choice on the same public roots and pre-call RNG state."""
    from random import Random
    roots = audit['roots']
    require(all(type(row['v4_score']) is int for row in roots), 'COUNTERFACTUAL_SCORES')
    if not roots:
        return None
    peak = max(row['v4_score'] for row in roots)
    tied = [row['move'] for row in roots if row['v4_score'] == peak]
    copied = Random()
    copied.setstate(rng_state)
    return copied.choice(tied)


def paired_analysis(pairs):
    from collections import Counter
    from math import comb
    counts = dict(both_win=0, both_loss=0, control_only=0, candidate_only=0)
    terminal_open_tunnels = dict(control=[], candidate=[])
    terminal_reasons = dict(control=Counter(), candidate=Counter())
    terminal_visible_water = dict(control=[], candidate=[])
    for pair in pairs:
        arms = {row['arm']: row for row in pair['results']}
        control = arms['control']['result']['won']
        candidate = arms['candidate']['result']['won']
        key = ('both_win' if control and candidate else
               'both_loss' if not control and not candidate else
               'control_only' if control else 'candidate_only')
        counts[key] += 1
        for arm in terminal_open_tunnels:
            terminal_open_tunnels[arm].append(arms[arm]['terminal_open_tunnels'])
            terminal_reasons[arm][arms[arm]['result']['reason']] += 1
            terminal_visible_water[arm].append(arms[arm]['result']['visible_water_cells'])
    discordant = counts['control_only'] + counts['candidate_only']
    tail = sum(comb(discordant, k) for k in range(min(counts['control_only'],
                                                      counts['candidate_only']) + 1))
    denominator = 1 << discordant
    return dict(wins=dict(control=counts['both_win'] + counts['control_only'],
                          candidate=counts['both_win'] + counts['candidate_only']),
                paired_outcomes=counts,
                paired_net_wins=counts['candidate_only'] - counts['control_only'],
                paired_win_rate_difference=(counts['candidate_only'] - counts['control_only']) / len(pairs),
                discordant_pairs=discordant,
                exact_two_sided_binomial=dict(numerator=min(2 * tail, denominator),
                                              denominator=denominator),
                choice_changes=sum(row['choice_changes'] for pair in pairs
                                   for row in pair['results'] if row['arm'] == 'candidate'),
                terminal_open_tunnels=terminal_open_tunnels,
                terminal_reasons={arm: dict(value) for arm, value in terminal_reasons.items()},
                terminal_visible_water=terminal_visible_water)


def main():
    from collections import Counter
    from dataclasses import asdict
    from random import Random
    import types

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, 'REQUIRE_I_S_B')
    require(sys.platform == 'linux' and sys.version_info[:3] == (3, 11, 16), 'RUNTIME')
    require(digest(Path(sys.executable).resolve().read_bytes()) == EXPECTED_EXE, 'RUNTIME_PIN')
    os.umask(0o077)
    for kind, bound in ((resource.RLIMIT_AS, 512 * 1024 * 1024),
                        (resource.RLIMIT_CPU, WHOLE_SECONDS), (resource.RLIMIT_NOFILE, 64),
                        (resource.RLIMIT_FSIZE, FILE_BYTES)):
        resource.setrlimit(kind, (bound, bound))
        require(resource.getrlimit(kind) == (bound, bound), 'NATIVE_LIMIT')
    signal.signal(signal.SIGALRM, timeout)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGALRM})
    deadline(WHOLE_SECONDS)
    codec_path = Path(__file__).with_name('codec.py')
    require(not codec_path.is_symlink() and codec_path.stat().st_size <= 16384, 'CODEC_KIND_SIZE')
    codec_raw = codec_path.read_bytes()
    require(digest(codec_raw) == CODEC_SHA, 'CODEC_PIN')
    codec = types.ModuleType('paired35_verified_codec')
    exec(compile(codec_raw, str(codec_path), 'exec'), codec.__dict__)
    evidence = codec.Evidence(args.output_dir)
    seed = None
    results = []
    try:
        issuer_path = Path(__file__).with_name('issuance.py')
        require(not issuer_path.is_symlink() and issuer_path.stat().st_size <= 20480, 'ISSUANCE_KIND_SIZE')
        issuer_raw = issuer_path.read_bytes()
        require(digest(issuer_raw) == ISSUANCE_SHA, 'ISSUANCE_PIN')
        issuer = types.ModuleType('paired35_verified_issuance')
        exec(compile(issuer_raw, str(issuer_path), 'exec'), issuer.__dict__)
        issuance = issuer.admit(args.output_dir.parent)
        path = Path(__file__).with_name('bounds.py')
        require(not path.is_symlink() and path.stat().st_size <= 4096, 'BOUNDS_KIND_SIZE')
        raw_bounds = path.read_bytes()
        require(digest(raw_bounds) == BOUNDS_SHA, 'BOUNDS_PIN')
        bounds = types.ModuleType('paired35_verified_bounds')
        exec(compile(raw_bounds, str(path), 'exec'), bounds.__dict__)
        require(args.manifest.stat().st_size <= 16384, 'MANIFEST_SIZE')
        raw = args.manifest.read_bytes()
        require(digest(raw) == args.manifest_sha256, 'MANIFEST_PIN')
        manifest = json.loads(raw)
        require(manifest['schema'] == 'strategy35-source-pins-v1' and
                manifest['commit'] == 'd88b2e40219db014eaa983423aa13112e08639ad', 'SUBJECT')
        root = args.source_root.resolve(strict=True)

        def pins():
            verify_sources(root, manifest)
            check_data(root)

        pins()
        require(not any(k == 'bandido_alcatraz' or k.startswith('bandido_alcatraz.')
                        for k in sys.modules), 'PRELOADED_PROJECT')
        sys.path.insert(0, str(root / 'src'))
        from bandido_alcatraz.game import GameState
        from bandido_alcatraz.physical_deck import load_real_deck
        from bandido_alcatraz.setup import SOLO_EASY
        from bandido_alcatraz.simulate import _result
        from bandido_alcatraz.policies import BoundedMergeV4Policy
        from bandido_alcatraz import visible_water_priority as candidate
        from bandido_alcatraz import visible_water_priority_reference as reference
        from bandido_alcatraz import strategy
        from bandido_alcatraz.worker32.evidence import observation, move
        pins()
        deck = load_real_deck(root / 'data')
        start = deck.start_for_setup(SOLO_EASY)
        cards = tuple(deck.draw_deck())
        catalog = dict(catalog=cards, start_card=start, exit_card=deck.exit_card)
        expected_ids = Counter(c.card_id for c in cards)
        require(len(cards) == 69 and len(expected_ids) == 69, 'PHYSICAL_DECK')

        def physical(state):
            ids = ([c.card_id for c in state.hand] + [c.card_id for c in state.draw_pile]
                   + [c.card_id for c in state.face_down_set_aside]
                   + [e.card_id for e in state.collected_equipment]
                   + [p.card_id for p in state.board.placements[1:]])
            require(Counter(ids) == expected_ids, 'PHYSICAL_CONSERVATION')
            require(0 <= state.raincoats <= 3 and 0 <= state.ropes <= 2, 'QUOTA')
            return dict(public=observation(state.observation()),
                        private_draw=[c.card_id for c in state.draw_pile],
                        private_set_aside=[c.card_id for c in state.face_down_set_aside])

        def domain(public):
            require(len(public.board.cells) <= 140 and len(public.board.placements) <= 70,
                    'FINITE_BOARD')
            require(all(abs(x) <= 1024 and abs(y) <= 1024
                        for x, y in public.board.cells), 'COORDINATE_BOUND')

        changed_choices = 0
        visible_water_priority_decisions = 0
        changed_top_decisions = 0
        operation_totals = dict(control=Counter(), candidate=Counter(), reference=Counter())

        def evaluation(label, obj, module, public, rng, prefix):
            nonlocal changed_choices, visible_water_priority_decisions, changed_top_decisions
            deadline()
            pins()
            require(sys.getprofile() is None, 'PROFILE_HOOK')
            before = canonical(observation(public))
            rng_before = rng.getstate()
            began, cpu = time.monotonic(), time.process_time()
            if label == 'control':
                with candidate._PhysicalCalls(candidate.OperationLimits(
                        legal_enumerations=OP_LIMIT, previews=OP_LIMIT,
                        exit_geometry_checks=OP_LIMIT)) as cost:
                    chosen = obj.choose(public, rng)
                    legal = public.legal_moves()
                    scores = [strategy.score_move_no_draw(public, m, obj.weights) for m in legal]
                tier = [i for i, s in enumerate(scores) if s == max(scores)] if scores else []
                copied = Random()
                copied.setstate(rng_before)
                expected = copied.choice([legal[i] for i in tier]) if tier else None
                require(move(chosen) == move(expected) and rng.getstate() == copied.getstate(),
                        'CANONICAL_V4_AUDIT_MISMATCH')
                audit = dict(roots=[dict(move=move(m), score=s) for m, s in zip(legal, scores)],
                             final=tier, chosen=move(chosen))
                operations = dict(cost.counts, roots=len(legal))
            else:
                chosen, audit, operations = obj.evaluate(public, rng, limits=candidate.OperationLimits(
                    legal_enumerations=OP_LIMIT, previews=OP_LIMIT,
                    exit_geometry_checks=OP_LIMIT))
            operation_totals[label].update(operations)
            elapsed, cpu_used = time.monotonic() - began, time.process_time() - cpu
            require(sys.getprofile() is None, 'PROFILE_NOT_RESTORED')
            require(canonical(observation(public)) == before, 'PUBLIC_MUTATED')
            # Integers in the fixed physical model fit signed64; score schema is frozen.
            require(all(type(r['score']) is int and abs(r['score']) < 2**63
                        for r in audit['roots']), 'SCORE_DOMAIN')
            if label == 'candidate':
                require(all(type(r['v4_score']) is int and abs(r['v4_score']) < 2**63
                            for r in audit['roots']), 'COUNTERFACTUAL_SCORE_DOMAIN')
            counterfactual = None
            changed = False
            if label == 'candidate':
                roots = audit['roots']
                top = ([i for i, row in enumerate(roots)
                        if row['v4_score'] == max(r['v4_score'] for r in roots)]
                       if roots else [])
                final_expected = ([i for i, row in enumerate(roots)
                                   if row['score'] == max(r['score'] for r in roots)]
                                  if roots else [])
                require(audit['schema'] == 'strategy35-visible-water-priority-v1'
                        and audit['flags'] == {'visible_water_weight': 100_000}
                        and all(row['score'] == row['v4_score'] +
                                80_000 * row['delta_visible_water']
                                for row in roots)
                        and audit['tiers']['v4_top'] == top
                        and audit['tiers']['final'] == final_expected,
                        'VISIBLE_WATER_AUDIT_SCHEMA')
                counterfactual = v4_counterfactual(audit, rng_before)
                changed = move(chosen) != counterfactual
                changed_choices += int(changed)
                visible_water_priority_decisions += 1
                changed_top_decisions += int(audit['tiers']['final'] != audit['tiers']['v4_top'])
            result = dict(call=label, chosen=move(chosen), science=audit,
                          operations=operations, rng_before=rng_before, rng_after=rng.getstate(),
                          v4_counterfactual=counterfactual, choice_changed=changed,
                          wall_seconds=elapsed, cpu_seconds=cpu_used)
            evidence.write(prefix + '-' + label + '.json', result)
            pins()
            deadline(WHOLE_SECONDS)
            return chosen, audit, operations

        evidence.write('run-intent.json', dict(subject='paired35', seeds=SEEDS,
                       arms=['control', 'candidate'], purpose='FIXED100PAIR_DEVELOPMENT_NOT_CONFIRMATION',
                       source=manifest['commit'], setup=SOLO_EASY.setup_id, data=DATA,
                       runtime_executable_sha256=EXPECTED_EXE, codec_sha256=CODEC_SHA, issuance=issuance))
        batch_results = []
        for pair_index, seed in enumerate(SEEDS):
            baseline = BoundedMergeV4Policy(setup_weight=250)
            policy = candidate.VisibleWaterPriorityPolicy()
            checker = reference.VisibleWaterPriorityReference()
            evidence.prefix = 'p' + str(pair_index).zfill(2) + '/'
            evidence.rows = []
            results = []
            initial = None
            for arm in ('control', 'candidate'):
                changed_before = changed_choices
                active_before = visible_water_priority_decisions
                guard_before = changed_top_decisions
                rng = Random(seed)
                state = GameState.new(start_card=start, deck=list(cards), hand_size=6,
                                      rng=rng, setup=SOLO_EASY)
                began = time.monotonic()
                before_game = physical(state)
                initial_raw = canonical(dict(state=before_game, rng=rng.getstate()))
                if initial is None:
                    initial = initial_raw
                else:
                    require(initial == initial_raw, 'PAIRED_INITIAL_DECK_RNG_MISMATCH')
                evidence.write(arm + '-initial.json', dict(state=before_game, rng=rng.getstate()))
                reason = None
                for ordinal in range(1000):
                    deadline(WHOLE_SECONDS)
                    # Exact ordering and refresh behavior of frozen simulate.play_game.
                    if state.won:
                        reason = 'win'
                        break
                    if state.board.open_tunnels == 0:
                        reason = 'closed_tunnels_conditions_failed'
                        break
                    if not state.hand and not state.draw_pile:
                        reason = 'deck_exhausted'
                        break
                    public = state.observation()
                    domain(public)
                    before = physical(state)
                    public_size = len(canonical(before['public']))
                    roots = len(public.legal_moves())
                    need = bounds.decision_upper(public_size, roots, True)
                    bounds.reserve(evidence.total, need, TOTAL_BYTES)
                    bounds.reserve(evidence.compressed, codec.compressed_upper(need, 6), FILE_BYTES)
                    require(len(evidence.rows) + 6 <= JOURNAL_RECORDS, 'JOURNAL_CAP_BEFORE_CALL')
                    # Candidate final decision: intent, two audits, transition,
                    # arm result, pair result, and the reserved terminal record.
                    bounds.reserve_records(len(evidence.names), 7, codec.MAX_RECORDS)
                    prefix = arm + '-' + str(ordinal).zfill(4)
                    used = evidence.total
                    evidence.write(prefix + '-intent.json', dict(state=before, rng=rng.getstate(),
                                   public_bytes=public_size, roots=roots, reserved=need))
                    copied = Random()
                    copied.setstate(rng.getstate())
                    if arm == 'candidate':
                        chosen, audit, operations = evaluation(
                            'candidate', policy, candidate, public, rng, prefix)
                        expected, checked, reference_operations = evaluation(
                            'reference', checker, reference, public, copied, prefix)
                    else:
                        chosen, audit, operations = evaluation(
                            'control', baseline, None, public, rng, prefix)
                        expected, checked, reference_operations = chosen, audit, operations
                    require(audit == checked and move(chosen) == move(expected)
                            and operations == reference_operations
                            and (arm == 'control' or rng.getstate() == copied.getstate()),
                            'FULL_REFERENCE_MISMATCH')
                    require(physical(state) == before, 'REAL_STATE_MUTATED_BY_POLICY')
                    if chosen is None:
                        if state.refresh_unplayable_hand():
                            action = 'refresh'
                        else:
                            reason = 'deck_exhausted' if state.exhausted else 'no_legal_move'
                            action = 'terminal_no_move'
                    else:
                        state.apply(chosen)
                        action = 'apply'
                    evidence.write(prefix + '-transition.json',
                                   dict(action=action, chosen=move(chosen), state=physical(state),
                                        rng=rng.getstate()))
                    require(evidence.total - used <= need, 'PROOF_UPPER_VIOLATION')
                    if reason is not None:
                        break
                else:
                    reason = 'step_limit'
                require(reason != 'step_limit', 'ENGINE_STEP_LIMIT_INCOMPLETE')
                result = dict(arm=arm, seed=seed, result=asdict(_result(state, reason)),
                              terminal=physical(state), rng=rng.getstate(),
                              terminal_open_tunnels=state.board.open_tunnels,
                              choice_changes=changed_choices - changed_before,
                              visible_water_priority_decisions=visible_water_priority_decisions - active_before,
                              changed_top_decisions=changed_top_decisions - guard_before,
                              wall_seconds=time.monotonic() - began)
                evidence.write(arm + '-result.json', result)
                results.append(result)
            evidence.write('pair-result.json', dict(status='ONE_EXPLORATORY_PAIR_COMPLETE',
                           seed=seed, games=2,
                           results=[dict(arm=r['arm'], seed=seed, result=r['result'],
                                         choice_changes=r['choice_changes'],
                                         terminal_open_tunnels=r['terminal_open_tunnels'],
                                         visible_water_priority_decisions=r['visible_water_priority_decisions'],
                                         changed_top_decisions=r['changed_top_decisions'],
                                         wall_seconds=r['wall_seconds']) for r in results],
                           whole_seconds=time.monotonic() - whole_started,
                           journal=evidence.rows[:]), terminal=False)
            batch_results.append(dict(seed=seed, results=[
                dict(arm=r['arm'], result=r['result'],
                     choice_changes=r['choice_changes'],
                     terminal_open_tunnels=r['terminal_open_tunnels'],
                     visible_water_priority_decisions=r['visible_water_priority_decisions'],
                     changed_top_decisions=r['changed_top_decisions'],
                     wall_seconds=r['wall_seconds'])
                for r in results]))
        evidence.prefix = ''
        evidence.rows = []
        evidence.write('result.json', dict(status='FIXED100PAIR_COMPLETE_DEVELOPMENT_NO_ADOPTION',
                       seeds=SEEDS, pairs=100, games=200, results=batch_results,
                       analysis=paired_analysis(batch_results),
                       choice_changes=changed_choices,
                       visible_water_priority_decisions=visible_water_priority_decisions,
                       changed_top_decisions=changed_top_decisions,
                       operation_counts_by_evaluation={label: dict(value)
                                                       for label, value in operation_totals.items()},
                       raw_evidence_bytes_before_result=evidence.total,
                       whole_seconds=time.monotonic() - whole_started), terminal=True)
        evidence.finish()
        return 0
    except BaseException as exc:
        evidence.prefix = ''
        evidence.write('failure.json', dict(status='INCOMPLETE_NOT_GAME_LOSS',
                       error_type=type(exc).__name__, traceback=traceback.format_exc(),
                       seed=seed, completed_pairs=batch_results if 'batch_results' in locals() else [],
                       journal=evidence.rows[:]), terminal=True)
        evidence.finish()
        raise


if __name__ == '__main__':
    whole_started = time.monotonic()
    raise SystemExit(main())
