"""Bounded visible lookahead only within V4's current best-score tier."""
from __future__ import annotations

from random import Random

from . import strategy
from .game import PlayerObservation
from .late_closure import LateClosurePolicy
from .moves import Move
from .policies import BoundedMergeV4Policy
from .quota_reserve_closure import OperationLimits, _PhysicalCalls, _require
from .worker32.evidence import move as move_wire, observation as observation_wire, sha


class V4TierBeamTwoPolicy(LateClosurePolicy):
    __slots__ = ()

    def evaluate(self, observation: PlayerObservation, rng: Random, *,
                 limits: OperationLimits | None = None) -> tuple[Move | None, dict, dict]:
        _require(type(rng) is Random, "exact canonical Random required")
        if limits is None:
            limits = OperationLimits()
        _require(type(limits) is OperationLimits, "invalid operation limits")
        meter = _PhysicalCalls(limits)
        try:
            meter.__enter__()
            self._validate(observation)
            before = sha(observation_wire(observation))
            rng_before = sha(rng.getstate())
            roots = observation.legal_moves()
            weights = BoundedMergeV4Policy(setup_weight=250).weights
            one_scores = [strategy.score_move_no_draw(observation, move, weights)
                          for move in roots]
            peak = max(one_scores, default=None)
            v4_top = [i for i, score in enumerate(one_scores) if score == peak]
            top = v4_top[:2] if len(v4_top) > 1 else []
            sequences = []
            for i in top:
                first = strategy.preview_move_without_draw(observation, roots[i]).successor
                if first.won or first.board.open_tunnels == 0:
                    second = []
                    total = one_scores[i]
                else:
                    second = first.legal_moves()
                    total = one_scores[i] + max(
                        (strategy.score_move_no_draw(first, move, weights)
                         for move in second), default=0)
                sequences.append(dict(index=i, first_score=one_scores[i],
                                      second_count=len(second), total=total))
            second_peak = max((row["total"] for row in sequences), default=None)
            beam_final = [row["index"] for row in sequences
                          if row["total"] == second_peak]
            unique_preference = len(beam_final) == 1
            final = beam_final if unique_preference else v4_top
            _require(sha(rng.getstate()) == rng_before, "scoring mutated RNG state")
            chosen = rng.choice([roots[i] for i in final]) if final else None
            chosen_index = roots.index(chosen) if chosen is not None else None
            after = sha(observation_wire(observation))
            _require(before == after, "public observation mutated by evaluation")
            audit = dict(schema="strategy30-v4-tier-beam2-v1",
                         input_before=before, input_after=after,
                         roots=[dict(move=move_wire(move), score=score, v4_score=score,
                                     one_score=score)
                                for move, score in zip(roots, one_scores)],
                         sequences=sequences,
                         tiers=dict(top=top, beam_final=beam_final,
                                    v4_top=v4_top, final=final),
                         flags=dict(beam_two_roots=len(top) == 2,
                                    unique_tie_break=unique_preference),
                         chosen_index=chosen_index, chosen=move_wire(chosen),
                         rng_before=rng_before, rng_after=sha(rng.getstate()))
        finally:
            meter.__exit__(None, None, None)
        return chosen, audit, dict(meter.counts, roots=len(roots))
