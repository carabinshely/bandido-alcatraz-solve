"""Independent fixed two-root visible-hand reference for paired28."""
from __future__ import annotations

from . import strategy
from .game import PlayerObservation
from .late_closure_reference import LateClosureReference
from .moves import Move
from .worker32.evidence import move as move_wire


class VisibleBeamTwoReference(LateClosureReference):
    def _compute(self, obs: PlayerObservation) -> tuple[list[Move], dict]:
        self._public_validation(obs)
        actions = obs.legal_moves()
        weights = strategy.PolicyWeights(
            collect_excess=0, delta_visible_water=20_000,
            delta_water_obstruction=1_000, new_trapped_water=-100_000,
            bounded_merge_setup_gain=250)
        first_scores = [strategy.score_features(strategy.move_features_no_draw(obs, a), weights)
                        for a in actions]
        ordered = sorted(range(len(actions)), key=lambda k: (-first_scores[k], k))
        top = ordered[:2]
        paths = []
        for index in top:
            node = strategy.preview_move_without_draw(obs, actions[index]).successor
            futures = [] if node.won or node.board.open_tunnels == 0 else node.legal_moves()
            next_best = max((strategy.score_features(
                                 strategy.move_features_no_draw(node, a), weights)
                             for a in futures), default=0)
            paths.append(dict(index=index, first_score=first_scores[index],
                              second_count=len(futures),
                              total=first_scores[index] + next_best))
        best = max((path["total"] for path in paths), default=None)
        final = [path["index"] for path in paths if path["total"] == best]
        science = dict(schema="strategy28-visible-beam2-v1",
                       roots=[dict(move=move_wire(a), score=s, v4_score=s,
                                   one_score=s)
                              for a, s in zip(actions, first_scores)],
                       sequences=paths, tiers=dict(top=top, final=final),
                       flags=dict(beam_two_roots=len(top) == 2))
        return [actions[index] for index in final], science
