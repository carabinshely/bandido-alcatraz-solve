"""Worker35's frozen, public-input-only one-action quota/closure candidate.

Nothing runs on import. The runner must bind the immutable catalog arguments to
the prospectively pinned canonical deck and START/EXIT blobs. Invented catalogs
with the same physical inventory are useful for synthetic tests only.

Canonical geometry and V4-250 scoring are deliberately reused, including their
real repeated legal enumerations. A scoped Python profile hook measures those
physical calls; no geometry cache or alternative preview changes that call graph.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from random import Random
import sys
from types import MappingProxyType

from . import moves as canonical_moves
from . import strategy
from .board import Board, CardPlacement, PlacementKind, VisibleCell
from .game import CollectedEquipment, PlayerObservation
from .model import CardDefinition, CellSpec, Direction, Material
from .moves import Action, Move
from .policies import BoundedMergeV4Policy
from .setup import GameSetup, SOLO_EASY
from .worker32.evidence import move as move_wire, observation as observation_wire, sha


class IntegrityError(ValueError):
    """Input or decision evidence violates the frozen public contract."""


class ResourceExceeded(RuntimeError):
    """A prospectively supplied physical-operation limit was exceeded."""


@dataclass(frozen=True, slots=True)
class OperationLimits:
    """Optional per-call limits; no scientific/resource ceiling is invented here.

    A production runner must supply the separately frozen ceilings and supervise
    wall time, memory and evidence bytes outside the policy. An exceeded physical
    call is counted at entry and raises before that function's body executes.
    """

    legal_enumerations: int | None = None
    previews: int | None = None
    exit_geometry_checks: int | None = None

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("operation limits must be nonnegative integers or None")


class _PhysicalCalls:
    """Measure actual function entries without modifying canonical functions."""

    def __init__(self, limits: OperationLimits) -> None:
        self.limits = limits
        self.counts = dict(legal_enumerations=0, previews=0, exit_geometry_checks=0)
        self.codes = {
            canonical_moves.legal_moves.__code__: "legal_enumerations",
            canonical_moves.placement_moves.__code__: "legal_enumerations",
            strategy.preview_move_without_draw.__code__: "previews",
            strategy.standalone_exit_legal_move_count.__code__: "exit_geometry_checks",
        }

    def _profile(self, frame, event, arg):
        if event == "call":
            name = self.codes.get(frame.f_code)
            if name is not None:
                self.counts[name] += 1
                limit = getattr(self.limits, name)
                if limit is not None and self.counts[name] > limit:
                    raise ResourceExceeded(f"physical {name} exceeded {limit}")
        if self.previous is not None:
            self.previous(frame, event, arg)

    def __enter__(self):
        self.previous = sys.getprofile()
        _require(self.previous is None or callable(self.previous),
                 "non-callable native profile hook cannot be safely preserved")
        sys.setprofile(self._profile)
        return self

    def __exit__(self, exc_type, exc, traceback):
        sys.setprofile(self.previous)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise IntegrityError(message)


def _coord(value) -> bool:
    return (type(value) is tuple and len(value) == 2
            and all(type(x) is int for x in value))


def _card_shape(card: CardDefinition) -> None:
    _require(type(card) is CardDefinition, "exact CardDefinition required")
    _require(type(card.card_id) is str and bool(card.card_id), "invalid card identity")
    _require(type(card.cells) is tuple and bool(card.cells), "immutable card cells required")
    _require(card.material is None or type(card.material) is Material, "invalid material type")
    _require(type(card.is_exit) is bool, "invalid EXIT marker")
    for cell in card.cells:
        _require(type(cell) is CellSpec and type(cell.x) is int and type(cell.y) is int,
                 "invalid card cell")
        _require(type(cell.water) is bool and type(cell.tunnel_edges) is frozenset
                 and all(type(edge) is Direction for edge in cell.tunnel_edges),
                 "invalid card water/edges")


class QuotaReserveClosurePolicy:
    """Stateless candidate; the only instance data is an immutable public catalog."""

    __slots__ = ("_catalog", "_start_card", "_exit_card")

    def __init__(self, *, catalog: tuple[CardDefinition, ...],
                 start_card: CardDefinition, exit_card: CardDefinition) -> None:
        _require(type(catalog) is tuple, "immutable catalog tuple required")
        for card in (*catalog, start_card, exit_card):
            _card_shape(card)
        by_id = {card.card_id: card for card in catalog}
        _require(len(catalog) == len(by_id) == 69, "catalog must contain 69 unique physical cards")
        _require(sum(c.material is Material.RAINCOAT for c in catalog) == 12
                 and sum(c.material is Material.ROPE for c in catalog) == 8,
                 "canonical physical material totals required")
        _require(exit_card.is_exit and exit_card.material is None
                 and sum(c.is_exit for c in catalog) == 1
                 and by_id.get(exit_card.card_id) == exit_card,
                 "catalog must contain the supplied unique EXIT")
        _require(start_card.card_id == "start_easy" and start_card.material is None
                 and not start_card.is_exit and start_card.card_id not in by_id,
                 "separate easy START setup identity required")
        object.__setattr__(self, "_catalog", MappingProxyType(by_id))
        object.__setattr__(self, "_start_card", start_card)
        object.__setattr__(self, "_exit_card", exit_card)

    def __setattr__(self, name, value):
        raise AttributeError("policy catalog is immutable")

    def __delattr__(self, name):
        raise AttributeError("policy catalog is immutable")

    @property
    def catalog(self) -> Mapping[str, CardDefinition]:
        return self._catalog

    def _validate(self, obs: PlayerObservation) -> dict:
        _require(type(obs) is PlayerObservation, "exact detached PlayerObservation required")
        _require(type(obs.board) is Board and type(obs.setup) is GameSetup
                 and obs.setup == SOLO_EASY, "canonical solo/easy5/hand6 setup required")
        _require(type(obs.hand) is tuple and 0 <= len(obs.hand) <= 6, "invalid own hand")
        _require(type(obs.collected_equipment) is tuple, "immutable collection history required")
        for value, top in ((obs.raincoats, 3), (obs.ropes, 2), (obs.player_index, 0),
                           (obs.turns, 69), (obs.set_aside_unplayable, 6)):
            _require(type(value) is int and 0 <= value <= top, "invalid quota/player/public count")
        _require(type(obs.exit_placed) is bool and type(obs.exit_seen) is bool,
                 "invalid EXIT flags")
        # Before a short refresh, a canonical six-card hand stays full while
        # draw stock exists. That refresh discards all six and empties the draw
        # stock, so a second set-aside event is impossible.
        _require(obs.set_aside_unplayable in (0, 6), "invalid short-pile set-aside count")
        placements = obs.board.placements
        _require(1 <= len(placements) <= 70, "missing/oversized complete placement history")
        _require(obs.turns == len(placements) - 1 + len(obs.collected_equipment),
                 "public action count/history mismatch")
        remaining = 69 - obs.turns - obs.set_aside_unplayable
        _require(remaining > 0 and len(obs.hand) == min(6, remaining),
                 "live hand/physical conservation mismatch or exhausted terminal input")
        if obs.set_aside_unplayable:
            _require(remaining == len(obs.hand), "short-pile refresh must leave no draw stock")

        used: set[str] = set()
        def physical(card):
            _card_shape(card)
            _require(card.card_id in self._catalog, "unknown physical card identity")
            _require(card == self._catalog[card.card_id], "physical material/geometry mismatch")
            _require(card.card_id not in used, "duplicate or cross-zone physical identity")
            used.add(card.card_id)

        for card in obs.hand:
            physical(card)
        collected = Counter()
        previous_turn = 0
        for entry in obs.collected_equipment:
            _require(type(entry) is CollectedEquipment, "invalid collected history entry")
            physical(entry.card)
            _require(entry.material is not None, "non-equipment collection history")
            _require(type(entry.turn) is int and previous_turn < entry.turn <= obs.turns
                     and type(entry.player_index) is int and entry.player_index == 0,
                     "invalid collection turn/player chronology")
            collected[entry.material] += 1
            previous_turn = entry.turn
        _require(collected[Material.RAINCOAT] == obs.raincoats
                 and collected[Material.ROPE] == obs.ropes, "collected-count/history mismatch")

        reconstructed = Board()
        placed = Counter()
        saw_exit = False
        for index, record in enumerate(placements):
            _require(type(record) is CardPlacement and type(record.card_id) is str
                     and _coord(record.origin) and type(record.quarter_turns) is int
                     and 0 <= record.quarter_turns < 4
                     and type(record.placement_index) is int and record.placement_index == index
                     and type(record.kind) is PlacementKind
                     and type(record.cells) is tuple and all(_coord(c) for c in record.cells)
                     and type(record.overlaps) is tuple and all(_coord(c) for c in record.overlaps)
                     and (record.covered_placement_index is None
                          or type(record.covered_placement_index) is int),
                     "invalid placement history fields")
            if index == 0:
                _require(record.card_id == self._start_card.card_id
                         and record.origin == (0, 0) and record.quarter_turns == 0
                         and record.kind is PlacementKind.START, "canonical START identity/transform required")
                reconstructed.seed(self._start_card)
            else:
                _require(reconstructed.open_tunnels > 0, "action after terminal closure")
                _require(record.card_id in self._catalog, "unknown placement identity")
                card = self._catalog[record.card_id]
                physical(card)
                try:
                    reconstructed.place(card, record.origin, record.quarter_turns)
                except (ValueError, IndexError) as exc:
                    raise IntegrityError("illegal public placement history") from exc
                placed[card.material] += 1
                saw_exit |= card.is_exit
            _require(reconstructed.placements[-1] == record, "placement/covered history mismatch")
        for coord, cell in obs.board.cells.items():
            _require(_coord(coord) and type(cell) is VisibleCell and type(cell.water) is bool
                     and type(cell.tunnel_edges) is frozenset
                     and all(type(edge) is Direction for edge in cell.tunnel_edges),
                     "invalid visible board geometry")
        _require(reconstructed.cells == obs.board.cells, "public board geometry/history mismatch")
        _require(obs.exit_placed == saw_exit and (obs.exit_seen or not (
            saw_exit or any(card.is_exit for card in obs.hand))), "EXIT history/visibility mismatch")
        _require(obs.board.open_tunnels > 0 and not obs.won, "terminal observation is not a policy input")
        # Collection records give the action timestamps omitted from placements.
        # A live final board and no prior closed placement ensure every missing
        # collection timestamp also lies before any terminal closure.
        _require(len(used) == obs.turns + len(obs.hand), "physical public identity count mismatch")
        supply = {}
        for material, quota, total, count in ((Material.RAINCOAT, 3, 12, obs.raincoats),
                                             (Material.ROPE, 2, 8, obs.ropes)):
            own = sum(card.material is material for card in obs.hand)
            available = total - count - placed[material]
            deficit = quota - count
            _require(available >= own, "public material stock smaller than own hand")
            if deficit > 0:
                _require(available <= remaining, "needed material exceeds remaining unconsumed stock")
                if obs.set_aside_unplayable:
                    _require(available == own, "short-pile needed-material supply invariant")
            supply[material.value] = dict(quota=quota, collected=count, total=total,
                                         placed=placed[material], deficit=deficit,
                                         available=available, own_hand=own)
        _require(sum(s["available"] for s in supply.values() if s["deficit"] > 0) <= remaining,
                 "combined needed supply exceeds remaining stock")
        return supply

    def choose(self, observation: PlayerObservation, rng: Random) -> Move | None:
        return self.evaluate(observation, rng)[0]

    def evaluate(self, observation: PlayerObservation, rng: Random, *,
                 limits: OperationLimits | None = None) -> tuple[Move | None, dict, dict]:
        """Return chosen move, deterministic scientific audit, and physical costs."""
        _require(isinstance(rng, Random), "canonical Random-compatible RNG required")
        if limits is None:
            limits = OperationLimits()
        _require(type(limits) is OperationLimits, "invalid operation limits")
        with _PhysicalCalls(limits) as physical:
            supply = self._validate(observation)
            before = sha(observation_wire(observation))
            rng_before = sha(rng.getstate())
            legal = observation.legal_moves()
            weights = BoundedMergeV4Policy(setup_weight=250).weights
            scores = [strategy.score_move_no_draw(observation, move, weights) for move in legal]
            _require(all(type(score) is int for score in scores), "canonical V4 scores must be integers")
            all_indices = list(range(len(legal)))

            def maximizers(indices):
                if not indices:
                    return []
                best = max(scores[i] for i in indices)
                return [i for i in indices if scores[i] == best]

            def stock(index):
                material = observation.hand[legal[index].hand_index].material
                return supply.get(material.value) if material is not None else None

            t0 = maximizers(all_indices)
            filtered = [i for i in all_indices if not (
                legal[i].action is Action.PLACE and stock(i) is not None
                and stock(i)["deficit"] > 0 and stock(i)["available"] <= stock(i)["deficit"])]
            _require(not legal or bool(filtered), "impossible empty policy-admissible list")
            tier = maximizers(filtered)
            closure = []
            guards = [dict(eligible=False, reason="branch_not_active", after=None,
                           exit_legal_count=None) for _ in legal]
            branch = bool(tier) and all(legal[i].action is Action.COLLECT for i in tier)
            if branch:
                baseline = (observation.board.open_tunnels, observation.board.visible_water_cells,
                            observation.board.water_obstruction, observation.board.trapped_water_cells)
                admitted = set(filtered)
                for i, move in enumerate(legal):
                    guard = guards[i]
                    material_stock = stock(i)
                    if move.action is not Action.PLACE:
                        guard["reason"] = "not_place"
                    elif i not in admitted:
                        guard["reason"] = "reserve_filtered"
                    elif material_stock is None or material_stock["deficit"] <= 0:
                        guard["reason"] = "not_needed_material"
                    else:
                        _require(material_stock["available"] > material_stock["deficit"],
                                 "closure supply contradicts reserve filter")
                        board = strategy.preview_move_without_draw(observation, move).successor.board
                        after = [board.open_tunnels, board.visible_water_cells,
                                 board.water_obstruction, board.trapped_water_cells]
                        guard["after"] = after
                        if after[0] >= baseline[0]:
                            guard["reason"] = "not_reduced"
                        elif after[0] <= 0:
                            guard["reason"] = "closed_tunnels"
                        elif after[1] > baseline[1]:
                            guard["reason"] = "visible_water_increased"
                        elif after[2] > baseline[2]:
                            guard["reason"] = "water_obstruction_increased"
                        elif after[3] > baseline[3]:
                            guard["reason"] = "trapped_water_increased"
                        else:
                            if not observation.exit_placed:
                                guard["exit_legal_count"] = strategy.standalone_exit_legal_move_count(
                                    board, self._exit_card)
                            if guard["exit_legal_count"] == 0:
                                guard["reason"] = "no_exit_capacity"
                            else:
                                guard["eligible"] = True
                                guard["reason"] = "eligible"
                                closure.append(i)
            final = maximizers(closure) if closure else tier
            _require(not legal or bool(final), "impossible empty final choice tier")
            # The caller's RNG is touched exactly once, even for a singleton.
            chosen = rng.choice([legal[i] for i in final]) if final else None
            chosen_index = legal.index(chosen) if chosen is not None else None
            after = sha(observation_wire(observation))
            _require(before == after, "public observation mutated by evaluation")
            original_all_collect = bool(t0) and all(legal[i].action is Action.COLLECT for i in t0)
            flags = dict(reserve_filter_active=filtered != all_indices,
                         reserve_primary_tier_changed=tier != t0,
                         closure_branch_selected=bool(closure),
                         true_original_all_collect_crossover=bool(closure) and original_all_collect,
                         reserve_filter_mediated_change=bool(closure) and tier != t0
                         and not original_all_collect)
            audit = dict(schema="worker35-scientific-v1", input_before=before, input_after=after,
                         roots=[dict(move=move_wire(move), score=score)
                                for move, score in zip(legal, scores)], supply=supply,
                         tiers=dict(T0=t0, F=filtered, T=tier, C=closure, final=final),
                         guards=guards, flags=flags, chosen_index=chosen_index,
                         chosen=move_wire(chosen), rng_before=rng_before, rng_after=sha(rng.getstate()))
        return chosen, audit, dict(physical.counts, roots=len(legal))
