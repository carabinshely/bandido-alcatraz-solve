"""One-off, read-only import of allowlisted public decisions from completed games."""
import base64
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent


def main():
    archive_root = HERE.parent / 'var/orchestrator'
    rows = {}
    studies = {s['number']:s for s in json.loads((HERE / 'inputs/recent-research.json').read_text(encoding='utf-8'))['studies']}
    original = json.loads((HERE / 'inputs/player-example.json').read_text(encoding='utf-8'))
    rows['110'] = dict(original=original['original'], game_seed=original['seed'],
                       decision=original['decision_ordinal'], source_snapshot_sha256=original['source_snapshot_sha256'],
                       source_kind='existing-published-public-position', state_before=dict(planned=False, returned_none=False))
    selections = {
        113: ('local113-b1-private-readback-base64-20261104.txt', 1006976, 6),
        127: ('local127-b1-canonical-readback-20261105.b64', 1010430, 6),
        129: ('local129-b1-canonical-readback-20261106.b64', 1011164, 47),
    }
    expected_fields = set(original['original'])
    for number, (filename, seed, call) in selections.items():
        packet = base64.b64decode((archive_root / filename).read_bytes())
        with ZipFile(io.BytesIO(packet)) as archive:
            member = f'evidence/s{seed}-candidate.json'
            raw_bytes = archive.read(member)
            raw = json.loads(raw_bytes)
            assert raw['seed'] == seed and raw['error'] is None
            assert raw['head'] == studies[number]['source_head']
            assert raw['candidate_policy_sha256'] == studies[number]['policy_sha256']
            context = next(c for c in raw['observer_contexts'] if c['call_index'] == call)
            public = context['public']
            assert set(public) == expected_fields
            assert public['exit_placed'] and (public['raincoats'],public['ropes']) == (3,2)
            if number == 113:
                assert 'first_departure' in context['roles']
            else:
                assert context['chosen'] != context['catalog']
            # Only public state and provenance leave the private archive.
            encoded = (json.dumps(public, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
            rows[str(number)] = dict(original=public, game_seed=seed, decision=call + 1,
                source_kind='recorded-first-departure-public-context',
                source_snapshot_sha256=hashlib.sha256(encoded).hexdigest(),
                source_packet_sha256=hashlib.sha256(packet).hexdigest(),
                source_member=member, source_member_sha256=hashlib.sha256(raw_bytes).hexdigest(),
                state_before={} if number == 113 else dict(departed=False))
    (HERE / 'inputs/recent-examples.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Imported four public decisions only; no hidden draws or operational records.')


if __name__ == '__main__':
    main()
