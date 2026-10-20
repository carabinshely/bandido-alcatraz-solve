"""Independent tier-constrained selection over shared canonical V4 primitives."""
from __future__ import annotations

from . import strategy
from .game import PlayerObservation
from .late_closure_reference import LateClosureReference
from .moves import Move
from .worker32.evidence import move as move_wire


class V4TierBeamTwoReference(LateClosureReference):
    def _compute(self, obs: PlayerObservation) -> tuple[list[Move], dict]:
        self._public_validation(obs)
        actions = obs.legal_moves()
        weights = strategy.PolicyWeights(
            collect_excess=0, delta_visible_water=20_000,
            delta_water_obstruction=1_000, new_trapped_water=-100_000,
            bounded_merge_setup_gain=250)
        first_scores = [strategy.score_features(strategy.move_features_no_draw(obs, a), weights)
                        for a in actions]
        highest = max(first_scores, default=None)
        tied = [k for k, value in enumerate(first_scores) if value == highest]
        inspected = tied[:2] if len(tied) > 1 else []
        paths = []
        for index in inspected:
            node = strategy.preview_move_without_draw(obs, actions[index]).successor
            futures = [] if node.won or node.board.open_tunnels == 0 else node.legal_moves()
            next_best = max((strategy.score_features(
                                 strategy.move_features_no_draw(node, a), weights)
                             for a in futures), default=0)
            paths.append(dict(index=index, first_score=first_scores[index],
                              second_count=len(futures),
                              total=first_scores[index] + next_best))
        best = max((path["total"] for path in paths), default=None)
        favored = [path["index"] for path in paths if path["total"] == best]
        unique = len(favored) == 1
        final = favored if unique else tied
        science = dict(schema="strategy30-v4-tier-beam2-v1",
                       roots=[dict(move=move_wire(a), score=s, v4_score=s,
                                   one_score=s)
                              for a, s in zip(actions, first_scores)],
                       sequences=paths,
                       tiers=dict(top=inspected, beam_final=favored,
                                  v4_top=tied, final=final),
                       flags=dict(beam_two_roots=len(inspected) == 2,
                                  unique_tie_break=unique))
        return [actions[index] for index in final], science
