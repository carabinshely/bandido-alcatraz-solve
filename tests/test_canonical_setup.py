from random import Random
from pathlib import Path
import pytest
from bandido_alcatraz.game import GameState, PlayerObservation
from bandido_alcatraz.setup import GameSetup, StartSide
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.strategy import clone_state, preview_move_without_draw
from bandido_alcatraz.moves import Action, Move
from bandido_alcatraz.simulate import play_game
from test_game import card, board_with_east_exit
from bandido_alcatraz.model import Direction, Material


def test_four_orthogonal_solo_setups_select_real_start_without_play():
    deck=load_real_deck(Path(__file__).parents[1]/'data')
    ids=set()
    for side in StartSide:
        for size in (3,6):
            setup=GameSetup(start_side=side,hand_size=size)
            ids.add(setup.setup_id)
            start=deck.start_for_setup(setup)
            state=GameState.new(start_card=start,deck=deck.draw_deck(),hand_size=size,setup=setup,rng=Random(9))
            assert len(state.hand)==size
            assert state.board.open_tunnels==(5 if side is StartSide.EASY else 6)
    assert len(ids)==4


def test_setup_validation_and_no_fake_multiplayer():
    for kwargs in ({'player_count':0},{'player_count':True},{'hand_size':4},{'player_count':2,'hand_size':6},{'start_side':'easy'},{'starting_player':1}):
        with pytest.raises(ValueError):GameSetup(**kwargs)
    setup=GameSetup(player_count=2,hand_size=3)
    with pytest.raises(NotImplementedError):setup.require_supported_execution()


def test_six_card_refresh_long_short_empty_and_no_action_counter():
    blocked=card('blocked',set());playable=card('playable',{Direction.WEST})
    for n in (2,6,7):
        state=GameState(board_with_east_exit(),[playable]*n,[blocked]*6,setup=GameSetup())
        assert state.refresh_unplayable_hand()
        assert len(state.hand)==min(6,n) and state.turns==0
        assert state.set_aside_unplayable==(6 if n<=6 else 0)
        assert len(state.draw_pile)==(0 if n<=6 else n)
    state=GameState(board_with_east_exit(),[],[blocked]*6,setup=GameSetup())
    assert not state.refresh_unplayable_hand()


def test_refresh_order_keeps_existing_deterministic_convention():
    blocked=card('blocked',set())
    cards=[card(str(i),{Direction.WEST}) for i in range(7)]
    state=GameState(board_with_east_exit(),list(cards),[blocked]*6,setup=GameSetup())
    assert state.refresh_unplayable_hand()
    assert state.hand==list(reversed(cards[1:]))
    assert state.draw_pile==[blocked]*6+[cards[0]]
    short=GameState(board_with_east_exit(),cards[:2],[blocked]*6,setup=GameSetup())
    assert short.refresh_unplayable_hand() and short.hand==cards[:2]


def test_overcollection_rejected_but_legal_placement_prevents_refresh():
    coat=card('coat',{Direction.WEST},material=Material.RAINCOAT)
    replacement=card('replacement',{Direction.WEST})
    state=GameState(board_with_east_exit(),[replacement],[coat],raincoats=3,ropes=2)
    # The historic excess COLLECT is now illegal; its card still has normal PLACE moves.
    moves=state.legal_moves()
    assert moves and all(move.action is Action.PLACE for move in moves)
    assert not state.refresh_unplayable_hand()
    with pytest.raises(ValueError, match='illegal collect'):
        state.apply(Move(Action.COLLECT,0))
    assert state.raincoats==3 and state.ropes==2 and state.turns==0
    assert state.hand==[coat] and state.draw_pile==[replacement]
    assert not state.collected_equipment
    state.apply(moves[0])
    assert state.raincoats==3 and not state.won
    assert state.board.open_tunnels==0 and state.turns==1
    assert not state.collected_equipment


def test_history_is_clone_safe_and_visible_without_hidden_draw():
    coat=card('coat',{Direction.WEST},material=Material.RAINCOAT)
    rope=card('rope',{Direction.WEST,Direction.EAST},material=Material.ROPE)
    state=GameState(board_with_east_exit(),[card('hidden',{Direction.WEST})],[coat,rope])
    move=next(m for m in state.legal_moves() if m.action is Action.COLLECT)
    preview=preview_move_without_draw(state,move).successor
    assert not state.collected_equipment and preview.collected_equipment[0].card is coat
    state.apply(move)
    observation=state.observation()
    assert isinstance(observation,PlayerObservation) and not hasattr(observation,'draw_pile')
    assert observation.collected_equipment==state.collected_equipment
    clone=clone_state(observation)
    assert not clone.draw_pile and clone.collected_equipment==state.collected_equipment
    observation.board._cells.clear()
    assert state.board.cells


def test_synthetic_simulator_exposes_only_observation_and_final_hook():
    class Policy:
        def choose(self,state,rng):
            assert isinstance(state,PlayerObservation)
            assert not hasattr(state,'draw_pile')
            moves=state.legal_moves()
            return moves[0] if moves else None
        def on_game_finished(self,state):self.final=state
    p=Policy()
    result=play_game(start_card=card('start',{Direction.EAST}),deck=[card('coat',{Direction.WEST},material=Material.RAINCOAT)],hand_size=6,setup=GameSetup(),policy=p,seed=0)
    assert p.final.turns==result.turns
    assert p.final.collected_equipment or p.final.board.open_tunnels==0


def test_physical_start_cannot_disagree_with_reported_setup():
    deck=load_real_deck(Path(__file__).parents[1]/'data')
    with pytest.raises(ValueError, match='START'):
        GameState.new(start_card=deck.start_normal,deck=deck.draw_deck(),hand_size=6,setup=GameSetup(),rng=Random(9))


def test_private_hands_and_face_down_zone_do_not_leak():
    own=card('own',{Direction.WEST})
    secret=card('secret-exit',{Direction.WEST},is_exit=True)
    hidden=card('hidden-discard',set())
    state=GameState(board_with_east_exit(),[],[],setup=GameSetup(player_count=2,hand_size=3),private_hands=[[own],[secret]],face_down_set_aside=(hidden,),exit_seen=True)
    a=state.observation(0);b=state.observation(1)
    assert a.hand==(own,) and not a.exit_seen
    assert b.hand==(secret,) and b.exit_seen
    for observation in (a,b):
        assert not hasattr(observation,'private_hands')
        assert not hasattr(observation,'face_down_set_aside')
        assert not hasattr(observation,'draw_pile')
    with pytest.raises(NotImplementedError):state.apply(state.legal_moves()[0])


def test_refresh_preserves_physical_identities_across_zones():
    old=[card('blocked'+str(i),set()) for i in range(6)]
    new=[card('draw'+str(i),{Direction.WEST}) for i in range(2)]
    state=GameState(board_with_east_exit(),list(new),list(old),setup=GameSetup())
    before=sorted(c.card_id for c in state.hand+state.draw_pile)
    assert state.refresh_unplayable_hand()
    after=sorted(c.card_id for c in state.hand+state.draw_pile+list(state.face_down_set_aside))
    assert before==after and len(state.face_down_set_aside)==6
    assert state.private_hands[0] is state.hand
    assert not hasattr(state.observation(),'face_down_set_aside')


def test_rejected_setup_preserves_caller_rng():
    rng=Random(17);before=rng.getstate()
    start=card('start_normal',{Direction.EAST})
    deck=[card(str(i),{Direction.WEST}) for i in range(10)]
    with pytest.raises(ValueError, match='START'):
        GameState.new(start_card=start,deck=deck,hand_size=6,setup=GameSetup(),rng=rng)
    assert rng.getstate()==before


def test_terminal_capture_isolated_from_inner_callback_and_checks_result():
    from dataclasses import replace
    from bandido_alcatraz.export_svg import FinalStateCapturePolicy, FinalBoardExport
    class Policy:
        def choose(self,state,rng):return None
        def on_game_finished(self,state):
            state.board.place(card('hypothetical',{Direction.WEST}),(1,0))
    capture=FinalStateCapturePolicy(Policy())
    result=play_game(start_card=card('start',{Direction.EAST}),deck=[],hand_size=6,setup=GameSetup(),policy=capture,seed=0)
    exported=FinalBoardExport.from_capture(game_index=1,capture=capture,result=result)
    assert result.open_tunnels==exported.board.open_tunnels==1
    assert len(exported.board.placements)==1
    with pytest.raises(ValueError, match='mismatch'):
        FinalBoardExport.from_capture(game_index=1,capture=capture,result=replace(result,open_tunnels=0))
