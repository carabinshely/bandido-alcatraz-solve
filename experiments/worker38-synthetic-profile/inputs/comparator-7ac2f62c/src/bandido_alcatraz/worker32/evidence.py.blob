"""Wire format only: no search, scoring or root aggregation."""
import hashlib
import json
from dataclasses import asdict
from ..game import PlayerObservation, GameState
from ..setup import SOLO_EASY, GameSetup

LIMIT = 32768

class BudgetExceeded(RuntimeError):
    pass


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                       allow_nan=False) + '\n').encode()


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def cell(x, y, c):
    return dict(x=x, y=y, tunnel_edges=sorted(c.tunnel_edges), water=c.water)


def card(c):
    return dict(card_id=c.card_id, cells=[cell(s.x, s.y, s) for s in c.cells],
                material=c.material, is_exit=c.is_exit)


def move(m):
    return None if m is None else json.loads(canonical(asdict(m)))


def observation(o):
    return dict(board=dict(cells=[cell(x,y,c) for (x,y),c in sorted(o.board.cells.items())],
                           placements=[json.loads(canonical(asdict(p))) for p in o.board.placements]),
                hand=[card(c) for c in o.hand], raincoats=o.raincoats, ropes=o.ropes,
                exit_placed=o.exit_placed, exit_seen=o.exit_seen, turns=o.turns,
                set_aside_unplayable=o.set_aside_unplayable,
                collected_equipment=[dict(card=card(e.card), turn=e.turn, player_index=e.player_index)
                                     for e in o.collected_equipment],
                setup=asdict(o.setup), player_index=o.player_index)


def validate(o):
    if type(o) is not PlayerObservation:
        raise ValueError('exact detached PlayerObservation required')
    if type(o.setup) is not GameSetup or canonical(asdict(o.setup)) != canonical(asdict(SOLO_EASY)) or type(o.hand) is not tuple or not 0 <= len(o.hand) <= 6:
        raise ValueError('solo easy5 hand6 required; retained hand 0..6')
    for v, top in ((o.raincoats,3),(o.ropes,2),(o.player_index,0)):
        if type(v) is not int or not 0 <= v <= top:
            raise ValueError('invalid quota/player')
    for v in (o.turns, o.set_aside_unplayable):
        if type(v) is not int or v < 0:
            raise ValueError('invalid public count')
    if type(o.exit_seen) is not bool or type(o.exit_placed) is not bool:
        raise ValueError('invalid exit flags')


def sanitized(o):
    return GameState(board=o.board.clone(), draw_pile=[], hand=list(o.hand),
                     raincoats=o.raincoats, ropes=o.ropes, exit_placed=o.exit_placed,
                     exit_seen=o.exit_seen, turns=o.turns,
                     set_aside_unplayable=o.set_aside_unplayable,
                     collected_equipment=o.collected_equipment, setup=o.setup,
                     player_index=o.player_index)


def leaf(sequence, state, key, reason):
    return dict(sequence=[move(m) for m in sequence], key=list(key), reason=reason,
                transition_sha256=sha(observation(state)))
