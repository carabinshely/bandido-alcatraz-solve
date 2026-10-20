"""Independent collect-tier/beam selection; canonical V4 primitives are shared."""
from __future__ import annotations

from . import strategy
from .game import PlayerObservation
from .late_closure_reference import LateClosureReference
from .moves import Action, Move
from .worker32.evidence import move as move_wire


class CollectGuardBeamTwoReference(LateClosureReference):
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
        beam_final = [path["index"] for path in paths if path["total"] == best]
        v4_peak = max(first_scores, default=None)
        v4_top = [i for i, score in enumerate(first_scores) if score == v4_peak]
        collect_guard = bool(v4_top) and all(
            actions[i].action is Action.COLLECT for i in v4_top)
        final = v4_top if collect_guard else beam_final
        science = dict(schema="strategy29-collect-guard-beam2-v1",
                       roots=[dict(move=move_wire(a), score=s, v4_score=s,
                                   one_score=s)
                              for a, s in zip(actions, first_scores)],
                       sequences=paths,
                       tiers=dict(top=top, beam_final=beam_final,
                                  v4_top=v4_top, final=final),
                       flags=dict(beam_two_roots=len(top) == 2,
                                  collect_guard_active=collect_guard))
        return [actions[index] for index in final], science
