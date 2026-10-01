"""Orthogonal setup dimensions; invariant game rules are not configurable."""
from dataclasses import dataclass
from enum import StrEnum

class StartSide(StrEnum):
    EASY = 'easy-5-exit'
    NORMAL = 'normal-6-exit'

@dataclass(frozen=True, slots=True)
class GameSetup:
    player_count: int = 1
    start_side: StartSide = StartSide.EASY
    hand_size: int = 6
    starting_player: int = 0

    def __post_init__(self):
        if type(self.player_count) is not int or self.player_count not in range(1,5):
            raise ValueError('player_count must be 1..4')
        if not isinstance(self.start_side, StartSide):
            raise ValueError('start_side must be StartSide')
        allowed = (3,6) if self.player_count == 1 else (3,)
        if type(self.hand_size) is not int or self.hand_size not in allowed:
            raise ValueError('solo hand must be 3 or 6; multiplayer hand must be 3')
        if type(self.starting_player) is not int or not 0 <= self.starting_player < self.player_count:
            raise ValueError('starting_player outside setup')

    @property
    def setup_id(self):
        return f'p{self.player_count}-{self.start_side.value}-hand{self.hand_size}-first{self.starting_player}-full-hand-refresh'

    def require_supported_execution(self):
        if self.player_count != 1:
            raise NotImplementedError('multiplayer execution awaits Issue27; separate hands and private observations required')

SOLO_EASY = GameSetup()
