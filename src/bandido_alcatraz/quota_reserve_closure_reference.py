"""Independently authored Worker35 decision reference, not a second game engine.

The frozen protocol is experiments/quota-reserve-closure-development/PROTOCOL.md.
Only canonical Board geometry, move enumeration, V4 scoring/preview/EXIT capacity
and existing wire serialization are shared. Public validation, supply accounting,
reserve selection, closure guards and tier selection are implemented here without
importing the candidate or any candidate decision helper. The caller freezes the
physical catalog; START is a separate definition, never an ordinary deck identity.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from random import Random
from typing import Iterable
from contextlib import contextmanager
import sys

from . import moves, strategy
from .board import Board, CardPlacement, PlacementKind
from .game import CollectedEquipment, PlayerObservation
from .model import CardDefinition, CellSpec, Direction, Material
from .moves import Action, Move
from .setup import GameSetup, SOLO_EASY
from .worker32.evidence import canonical, card as card_wire, move as move_wire, observation as observation_wire, sha


class IntegrityError(RuntimeError):
    """An invalid input or internal invariant is never a game result."""


class ReferenceInputError(IntegrityError, ValueError):
    """The supplied public state is outside the frozen live-input contract."""


class ReferenceIntegrityError(IntegrityError):
    """An internal invariant failed; never convert this into refresh or loss."""


class ResourceExceeded(RuntimeError):
    """An explicitly supplied physical-operation ceiling was exceeded."""


@dataclass(frozen=True, slots=True)
class OperationLimits:
    legal_enumerations: int | None = None
    previews: int | None = None
    exit_geometry_checks: int | None = None

    def __post_init__(self):
        for value in (self.legal_enumerations, self.previews, self.exit_geometry_checks):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError('operation ceilings must be nonnegative integers or None')


@contextmanager
def _physical_operations(limits: OperationLimits):
    # Observe the actual frozen Python calls, including nested membership checks.
    # This does not patch the canonical engine or cache/eliminate any work.
    targets = {moves.legal_moves.__code__: 'legal_enumerations',
               moves.placement_moves.__code__: 'legal_enumerations',
               strategy.preview_move_without_draw.__code__: 'previews',
               strategy.standalone_exit_legal_move_count.__code__: 'exit_geometry_checks'}
    counts = dict(legal_enumerations=0, previews=0, exit_geometry_checks=0, roots=0)
    prior = sys.getprofile()
    # CPython can expose an active native profiler as a non-callable object.
    # setprofile cannot forward or reinstall that object. Reject before touching
    # the active hook rather than losing it during attempted cleanup.
    if prior is not None and not callable(prior):
        raise ReferenceIntegrityError('cannot preserve a non-callable existing profile hook')

    def count(frame, event, arg):
        if prior is not None:
            prior(frame, event, arg)
        if event == 'call' and frame.f_code in targets:
            name = targets[frame.f_code]
            counts[name] += 1
            ceiling = getattr(limits, name)
            if ceiling is not None and counts[name] > ceiling:
                raise ResourceExceeded(f'{name} exceeded {ceiling}')

    try:
        sys.setprofile(count)
        yield counts
    finally:
        sys.setprofile(prior)


_QUOTAS = {Material.RAINCOAT: 3, Material.ROPE: 2}
_TOTALS = {Material.RAINCOAT: 12, Material.ROPE: 8}


def _integer(value: object, *, minimum: int = 0, maximum: int | None = None) -> bool:
    return type(value) is int and value >= minimum and (maximum is None or value <= maximum)


def _typed_card(card: object) -> bool:
    return (type(card) is CardDefinition and type(card.card_id) is str and bool(card.card_id)
            and type(card.is_exit) is bool
            and (card.material is None or type(card.material) is Material)
            and type(card.cells) is tuple and bool(card.cells)
            and all(type(cell) is CellSpec and type(cell.x) is int and type(cell.y) is int
                    and type(cell.water) is bool and type(cell.tunnel_edges) is frozenset
                    and all(type(edge) is Direction for edge in cell.tunnel_edges)
                    for cell in card.cells))


class QuotaReserveClosureReference:
    """Stateless cleanroom checker over a caller-frozen public physical catalog."""

    def __init__(self, *, catalog: Iterable[CardDefinition], start_card: CardDefinition,
                 exit_card: CardDefinition) -> None:
        cards = tuple(catalog)
        if len(cards) != 69 or any(not _typed_card(card) for card in cards):
            raise ReferenceInputError('catalog requires the 69 physical draw-deck cards')
        if any(type(card.card_id) is not str or not card.card_id for card in cards):
            raise ReferenceInputError('catalog card identity must be a nonempty string')
        mapping = {card.card_id: card for card in cards}
        if len(mapping) != len(cards):
            raise ReferenceInputError('catalog has duplicate physical identities')
        if Counter(card.material for card in cards if card.material is not None) != _TOTALS:
            raise ReferenceInputError('catalog must contain 12 raincoats and 8 ropes')
        if not _typed_card(exit_card) or not exit_card.is_exit:
            raise ReferenceInputError('a fixed EXIT definition is required')
        if [card for card in cards if card.is_exit] != [exit_card]:
            raise ReferenceInputError('catalog must contain the unique fixed EXIT')
        if (not _typed_card(start_card) or start_card.is_exit
                or start_card.material is not None or start_card.card_id in mapping):
            raise ReferenceInputError('START must have its own non-equipment identity')
        start = Board()
        start.seed(start_card)
        if start.open_tunnels != 5:
            raise ReferenceInputError('easy START must have exactly five open tunnels')
        self._catalog = mapping
        self._start = start_card
        self._exit = exit_card
        # Spell the frozen V4-250 weights locally rather than inheriting a policy.
        self._weights = strategy.PolicyWeights(
            collect_excess=0, delta_visible_water=20_000,
            delta_water_obstruction=1_000, new_trapped_water=-100_000,
            bounded_merge_setup_gain=250,
        )

    def _public_validation(self, obs: PlayerObservation) -> dict:
        if type(obs) is not PlayerObservation:
            raise ReferenceInputError('an exact detached PlayerObservation is required')
        if type(obs.board) is not Board:
            raise ReferenceInputError('public board must be a canonical Board')
        if type(obs.setup) is not GameSetup or obs.setup != SOLO_EASY or obs.player_index != 0:
            raise ReferenceInputError('solo easy5 hand6 setup is required')
        if not _integer(obs.player_index, maximum=0):
            raise ReferenceInputError('invalid player index')
        if type(obs.hand) is not tuple or not 1 <= len(obs.hand) <= 6:
            raise ReferenceInputError('a live canonical hand contains one through six cards')
        if not _integer(obs.raincoats, maximum=3) or not _integer(obs.ropes, maximum=2):
            raise ReferenceInputError('invalid exact equipment counters')
        if (not _integer(obs.turns, maximum=69)
                or not _integer(obs.set_aside_unplayable, maximum=6)
                or obs.set_aside_unplayable not in (0, 6)):
            raise ReferenceInputError('invalid public physical count')
        if type(obs.exit_seen) is not bool or type(obs.exit_placed) is not bool:
            raise ReferenceInputError('EXIT knowledge and placement flags must be Boolean')
        if type(obs.collected_equipment) is not tuple:
            raise ReferenceInputError('complete collection history must be a tuple')

        used: set[str] = set()

        def claim(card: CardDefinition) -> None:
            if (not _typed_card(card) or self._catalog.get(card.card_id) != card
                    or card.material is not self._catalog[card.card_id].material
                    or type(card.is_exit) is not bool
                    or canonical(card_wire(card)) != canonical(card_wire(self._catalog[card.card_id]))):
                raise ReferenceInputError('unknown card or catalog material/geometry mismatch')
            if card.card_id in used:
                raise ReferenceInputError('duplicate identity or cross-zone physical reuse')
            used.add(card.card_id)

        placed = Counter()
        records = obs.board.placements
        if not records or type(records[0]) is not CardPlacement:
            raise ReferenceInputError('complete placement history must start with START')
        rebuilt = Board()
        for index, record in enumerate(records):
            if type(record) is not CardPlacement:
                raise ReferenceInputError('invalid placement-history record')
            if (not _integer(record.placement_index, maximum=69)
                    or record.placement_index != index
                    or type(record.origin) is not tuple or len(record.origin) != 2
                    or any(type(coordinate) is not int for coordinate in record.origin)
                    or not _integer(record.quarter_turns, maximum=3)):
                raise ReferenceInputError('invalid placement index, origin or rotation')
            try:
                if index == 0:
                    if (record.card_id != self._start.card_id or record.kind is not PlacementKind.START
                            or record.origin != (0, 0) or record.quarter_turns != 0):
                        raise ReferenceInputError('noncanonical START placement')
                    rebuilt.seed(self._start)
                else:
                    if rebuilt.open_tunnels == 0:
                        raise ReferenceInputError('placement history continued after terminal closure')
                    card = self._catalog.get(record.card_id)
                    if card is None:
                        raise ReferenceInputError('unknown physical placement identity')
                    claim(card)
                    rebuilt.place(card, record.origin, record.quarter_turns)
                    if card.material is not None:
                        placed[card.material] += 1
            except (TypeError, IndexError, KeyError, ValueError) as exc:
                raise ReferenceInputError('invalid physical placement history') from exc
            if canonical(asdict(rebuilt.placements[-1])) != canonical(asdict(record)):
                raise ReferenceInputError('placement geometry, kind or covered-history mismatch')
        if (rebuilt.cells != obs.board.cells or rebuilt.placements != records
                or any(type(value.water) is not bool or type(x) is not int or type(y) is not int
                       for (x, y), value in obs.board.cells.items())):
            raise ReferenceInputError('public geometry does not match complete history')
        if obs.board._placement_count != len(records):
            raise ReferenceInputError('public placement count does not match history')

        collected = Counter()
        previous_turn = 0
        for entry in obs.collected_equipment:
            if type(entry) is not CollectedEquipment:
                raise ReferenceInputError('invalid collection-history entry')
            claim(entry.card)
            if (entry.material not in _QUOTAS or not _integer(entry.turn, minimum=1, maximum=obs.turns)
                    or entry.turn <= previous_turn or not _integer(entry.player_index, maximum=0)):
                raise ReferenceInputError('invalid material, collection turn or collector')
            previous_turn = entry.turn
            collected[entry.material] += 1
        if collected[Material.RAINCOAT] != obs.raincoats or collected[Material.ROPE] != obs.ropes:
            raise ReferenceInputError('collected counters disagree with physical history')
        if len(records) - 1 + len(obs.collected_equipment) != obs.turns:
            raise ReferenceInputError('turn count disagrees with placement and collection history')
        for card in obs.hand:
            claim(card)
        has_placed_exit = any(record.card_id == self._exit.card_id for record in records[1:])
        if obs.exit_placed != has_placed_exit:
            raise ReferenceInputError('EXIT flag disagrees with placement history')
        if (obs.exit_placed or self._exit in obs.hand) and not obs.exit_seen:
            raise ReferenceInputError('visible EXIT must have been seen')
        if rebuilt.open_tunnels == 0 or obs.won:
            raise ReferenceInputError('terminal observations are outside the policy domain')
        remaining = 69 - obs.turns - obs.set_aside_unplayable
        if remaining <= 0 or len(obs.hand) != min(6, remaining):
            raise ReferenceInputError('own hand violates exact live physical conservation')
        remaining_count = 69 - len(used) - obs.set_aside_unplayable
        if remaining_count < 0 or (obs.set_aside_unplayable and remaining_count != 0):
            raise ReferenceInputError('public physical counts cannot describe a canonical live state')
        supply = {}
        for material, quota in _QUOTAS.items():
            count = collected[material]
            available = _TOTALS[material] - count - placed[material]
            own_count = sum(card.material is material for card in obs.hand)
            if count < quota:
                if available < own_count or available > own_count + remaining_count:
                    raise ReferenceInputError('needed supply disagrees with public physical accounting')
                if obs.set_aside_unplayable and available != own_count:
                    raise ReferenceInputError('short-pile refresh violates the needed-supply invariant')
            supply[material.value] = dict(quota=quota, collected=count,
                total=_TOTALS[material], placed=placed[material],
                deficit=quota-count, available=available, own_hand=own_count)
        return supply

    def _compute(self, obs: PlayerObservation) -> tuple[list[Move], dict]:
        supply = self._public_validation(obs)
        legal = obs.legal_moves()
        if len(legal) != len(set(legal)):
            raise ReferenceIntegrityError('canonical enumeration repeated a legal root')
        scores = [strategy.score_move_no_draw(obs, action, self._weights) for action in legal]
        if any(type(score) is not int for score in scores):
            raise ReferenceIntegrityError('canonical immediate scores must be integers')

        def best(indices: list[int]) -> list[int]:
            if not indices:
                raise ReferenceIntegrityError('a nonempty selection tier is required')
            top = max(scores[index] for index in indices)
            return [index for index in indices if scores[index] == top]

        def material_info(action: Move) -> dict | None:
            material = obs.hand[action.hand_index].material
            return supply[material.value] if material is not None else None

        original = best(list(range(len(legal)))) if legal else []
        admissible = []
        for index, action in enumerate(legal):
            info = material_info(action)
            protected_place = (action.action is Action.PLACE and info is not None
                               and info['deficit'] > 0 and info['available'] <= info['deficit'])
            if not protected_place:
                admissible.append(index)
        if legal and not admissible:
            raise ReferenceIntegrityError('reserve filter emptied a nonempty legal list')
        primary = best(admissible) if legal else []
        all_collect = bool(primary) and all(legal[index].action is Action.COLLECT for index in primary)
        closure: list[int] = []
        classifications: list[dict] = []
        before = [obs.board.open_tunnels, obs.board.visible_water_cells,
                  obs.board.water_obstruction, obs.board.trapped_water_cells]
        for index, action in enumerate(legal):
            info = material_info(action)
            row = dict(eligible=False, reason='branch_not_active', after=None,
                       exit_legal_count=None)
            if all_collect:
                if action.action is not Action.PLACE:
                    row['reason'] = 'not_place'
                elif index not in admissible:
                    row['reason'] = 'reserve_filtered'
                elif info is None or info['deficit'] <= 0:
                    row['reason'] = 'not_needed_material'
                else:
                    board = strategy.preview_move_without_draw(obs, action).successor.board
                    after = [board.open_tunnels, board.visible_water_cells,
                             board.water_obstruction, board.trapped_water_cells]
                    row['after'] = after
                    failures = (
                        (after[0] >= before[0], 'not_reduced'),
                        (after[0] <= 0, 'closed_tunnels'),
                        (after[1] > before[1], 'visible_water_increased'),
                        (after[2] > before[2], 'water_obstruction_increased'),
                        (after[3] > before[3], 'trapped_water_increased'),
                    )
                    row['reason'] = next((reason for failed, reason in failures if failed), 'eligible')
                    if row['reason'] == 'eligible' and not obs.exit_placed:
                        capacity = strategy.standalone_exit_legal_move_count(board, self._exit)
                        row['exit_legal_count'] = capacity
                        if capacity == 0:
                            row['reason'] = 'no_exit_capacity'
                    row['eligible'] = row['reason'] == 'eligible'
                    if row['eligible']:
                        closure.append(index)
            classifications.append(row)
        final = best(closure) if closure else primary
        if legal and not final:
            raise ReferenceIntegrityError('nonempty legal list produced an empty final tier')
        science = dict(schema='worker35-scientific-v1',
            roots=[dict(move=move_wire(action), score=score) for action, score in zip(legal, scores)],
            supply=supply,
            tiers=dict(T0=original, F=admissible, T=primary, C=closure, final=final),
            guards=classifications,
            flags=dict(reserve_filter_active=admissible != list(range(len(legal))),
                reserve_primary_tier_changed=primary != original,
                closure_branch_selected=bool(closure),
                true_original_all_collect_crossover=bool(closure) and bool(original) and all(
                    legal[index].action is Action.COLLECT for index in original),
                reserve_filter_mediated_change=bool(closure) and primary != original and any(
                    legal[index].action is Action.PLACE for index in original)))
        return [legal[index] for index in final], science

    def evaluate(self, observation: PlayerObservation, rng: Random, *,
                 limits: OperationLimits | None = None) -> tuple[Move | None, dict, dict]:
        if limits is None:
            limits = OperationLimits()
        if type(limits) is not OperationLimits:
            raise ValueError('reference OperationLimits required')
        # Validate type before using the serializer; no private-state adapter exists.
        if type(observation) is not PlayerObservation:
            raise ReferenceInputError('an exact detached PlayerObservation is required')
        before = sha(observation_wire(observation))
        rng_before = sha(rng.getstate())
        meter = _physical_operations(limits)
        try:
            # A forwarded prior hook may raise on contextlib.__enter__'s return,
            # after the generator yielded but before a with statement registers
            # its __exit__. Close explicitly even if that entry never completes;
            # traceback retention must not defer restoration until garbage collection.
            cost = meter.__enter__()
            final, science = self._compute(observation)
            cost['roots'] = len(science['roots'])
        finally:
            meter.gen.close()
        if sha(observation_wire(observation)) != before:
            raise ReferenceIntegrityError('decision computation mutated the public observation')
        if sha(rng.getstate()) != rng_before:
            raise ReferenceIntegrityError('scoring or guards mutated RNG state')
        selected = rng.choice(final) if final else None
        if final and selected not in final:
            raise ReferenceIntegrityError('RNG returned a move outside the final tier')
        selected_wire = move_wire(selected)
        index = None
        if selected is not None:
            index = next(i for i, root in enumerate(science['roots']) if root['move'] == selected_wire)
        science.update(input_before=before, input_after=sha(observation_wire(observation)),
                       chosen_index=index, chosen=selected_wire,
                       rng_before=rng_before, rng_after=sha(rng.getstate()))
        if science['input_after'] != before:
            raise ReferenceIntegrityError('RNG choice mutated the public observation')
        return selected, science, dict(cost)

    def choose(self, observation: PlayerObservation, rng: Random) -> Move | None:
        return self.evaluate(observation, rng)[0]
