"""Two-root visible-hand lookahead that preserves V4's collect-only top tier."""
from __future__ import annotations

from random import Random

from . import strategy
from .game import PlayerObservation
from .late_closure import LateClosurePolicy
from .moves import Action, Move
from .policies import BoundedMergeV4Policy
from .quota_reserve_closure import OperationLimits, _PhysicalCalls, _require
from .worker32.evidence import move as move_wire, observation as observation_wire, sha


class CollectGuardBeamTwoPolicy(LateClosurePolicy):
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
            top = sorted(range(len(roots)), key=lambda i: (-one_scores[i], i))[:2]
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
            peak = max((row["total"] for row in sequences), default=None)
            beam_final = [row["index"] for row in sequences if row["total"] == peak]
            v4_peak = max(one_scores, default=None)
            v4_top = [i for i, score in enumerate(one_scores) if score == v4_peak]
            collect_guard = bool(v4_top) and all(
                roots[i].action is Action.COLLECT for i in v4_top)
            final = v4_top if collect_guard else beam_final
            _require(sha(rng.getstate()) == rng_before, "scoring mutated RNG state")
            chosen = rng.choice([roots[i] for i in final]) if final else None
            chosen_index = roots.index(chosen) if chosen is not None else None
            after = sha(observation_wire(observation))
            _require(before == after, "public observation mutated by evaluation")
            audit = dict(schema="strategy29-collect-guard-beam2-v1",
                         input_before=before, input_after=after,
                         roots=[dict(move=move_wire(move), score=score, v4_score=score,
                                     one_score=score)
                                for move, score in zip(roots, one_scores)],
                         sequences=sequences,
                         tiers=dict(top=top, beam_final=beam_final,
                                    v4_top=v4_top, final=final),
                         flags=dict(beam_two_roots=len(top) == 2,
                                    collect_guard_active=collect_guard),
                         chosen_index=chosen_index, chosen=move_wire(chosen),
                         rng_before=rng_before, rng_after=sha(rng.getstate()))
        finally:
            meter.__exit__(None, None, None)
        return chosen, audit, dict(meter.counts, roots=len(roots))
