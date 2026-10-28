"""Use public card geometry to protect the least coverable open target."""

from random import Random

from bandido_alcatraz.moves import Action
from bandido_alcatraz.policies import BoundedMergeV4Policy
from bandido_alcatraz.strategy import move_features, score_features


class CatalogSupportPolicy:
    def __init__(self, ordinary_cards, exit_card) -> None:
        self.weights = BoundedMergeV4Policy(setup_weight=250).weights
        self.cards = tuple(
            tuple((rotated, tuple((cell.x, cell.y) for cell in rotated.cells))
                  for rotated in (card.rotated(turn) for turn in range(4)))
            for card in (*ordinary_cards, exit_card)
        )

    def _target_support(self, board, target) -> int:
        tx, ty = target
        support = 0
        for rotations in self.cards:
            covers = False
            for rotated, cells in rotations:
                for x, y in cells:
                    if board.can_place(rotated, (tx - x, ty - y)):
                        covers = True
                        break
                if covers:
                    break
            if covers:
                support += 1
                if support == 4:
                    break
        return support

    def _weakest_support(self, observation, move) -> int:
        if move.action is Action.COLLECT:
            return -1
        board = observation.board.clone()
        board.place(observation.hand[move.hand_index], move.origin,
                    move.quarter_turns)
        targets = board.open_tunnel_target_counts
        if not targets:
            return 0
        return min(self._target_support(board, target) for target in targets)

    def choose(self, observation, rng: Random):
        moves = observation.legal_moves()
        if not moves:
            return None
        features = [move_features(observation, move) for move in moves]
        winning = [move for move, feature in zip(moves, features) if feature.wins]
        if winning:
            return rng.choice(winning)
        scores = [score_features(feature, self.weights) for feature in features]
        best = max(scores)
        initial = rng.choice([move for move, score in zip(moves, scores)
                              if score == best])
        index = moves.index(initial)
        if initial.action is Action.COLLECT:
            return initial
        ranked = sorted(range(len(moves)), key=lambda i: (-scores[i], i))
        contenders = [index]
        for candidate in ranked:
            if len(contenders) == 3 or scores[candidate] < best - 1000:
                break
            if candidate != index and moves[candidate].action is Action.PLACE:
                contenders.append(candidate)
        winner = index
        support = self._weakest_support(observation, initial)
        for candidate in contenders[1:]:
            candidate_support = self._weakest_support(observation, moves[candidate])
            if candidate_support > support:
                winner, support = candidate, candidate_support
        return moves[winner]
