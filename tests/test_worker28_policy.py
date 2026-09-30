from types import SimpleNamespace
import unittest
from unittest.mock import patch
from scripts import worker28_policy as p
from bandido_alcatraz.board import Board
from bandido_alcatraz.game import GameState
from bandido_alcatraz.model import CardDefinition,CellSpec,Direction

class Rng:
    def __init__(self):self.calls=[]
    def choice(self,values):self.calls.append(list(values));return values[0]

class Hidden:
    def fail(self,*args,**kwargs):raise AssertionError('hidden draw accessed')
    __iter__=__len__=__getitem__=__bool__=pop=copy=fail

def fake(value=0,won=False,open_count=1):
    state=SimpleNamespace(won=won,board=SimpleNamespace(open_tunnels=open_count),value=value,children={})
    state.legal_moves=lambda:list(state.children)
    return state

def preview(state,move):return SimpleNamespace(successor=state.children[move])

class Tests(unittest.TestCase):
    def test_shorter_win_dominates_longer(self):
        root=fake();root.children={'now':fake(won=True),'later':fake()};root.children['later'].children={'finish':fake(won=True)};rng=Rng()
        with patch.object(p,'preview_move_without_draw',side_effect=preview),patch.object(p,'potential',side_effect=lambda s:s.value):
            self.assertEqual(p.VisibleEndStateBeamV8Policy().choose(root,rng),'now')
        self.assertEqual(rng.calls,[['now']])

    def test_global_width_and_stable_canonical_ties(self):
        root=fake();root.children={str(i):fake() for i in range(20)};rng=Rng()
        with patch.object(p,'preview_move_without_draw',side_effect=preview),patch.object(p,'potential',side_effect=lambda s:s.value):p.VisibleEndStateBeamV8Policy().choose(root,rng)
        self.assertEqual(rng.calls,[list(root.children)[:16]])

    def test_depth_three_not_four(self):
        root=fake();a=fake();b=fake();c=fake(value=1);d=fake(won=True);a.children={'2':b};b.children={'3':c};c.children={'4':d};root.children={'chain':a,'leaf':fake(value=2)};rng=Rng()
        with patch.object(p,'preview_move_without_draw',side_effect=preview) as call,patch.object(p,'potential',side_effect=lambda s:s.value):
            self.assertEqual(p.VisibleEndStateBeamV8Policy().choose(root,rng),'leaf');self.assertFalse(any(x.args[1]=='4' for x in call.call_args_list))

    def test_deduplicate_first_action_not_leaf_count(self):
        root=fake();a=fake();a.children={'x':fake(value=3),'y':fake(value=3)};root.children={'a':a,'b':fake(value=3)};rng=Rng()
        with patch.object(p,'preview_move_without_draw',side_effect=preview),patch.object(p,'potential',side_effect=lambda s:s.value):p.VisibleEndStateBeamV8Policy().choose(root,rng)
        self.assertEqual(rng.calls,[['a','b']])

    def test_dead_terminal_loses_to_nonterminal(self):
        root=fake();root.children={'dead':fake(value=10000000,open_count=0),'alive':fake(value=-10000000)};rng=Rng()
        with patch.object(p,'preview_move_without_draw',side_effect=preview),patch.object(p,'potential',side_effect=lambda s:s.value):self.assertEqual(p.VisibleEndStateBeamV8Policy().choose(root,rng),'alive')

    def test_terminal_or_no_moves_uses_no_rng(self):
        for state in [fake(),fake(won=True),fake(open_count=0)]:
            rng=Rng();self.assertIsNone(p.VisibleEndStateBeamV8Policy().choose(state,rng));self.assertEqual(rng.calls,[])

    def test_visible_only_and_state_immutability(self):
        def card(name,edges):return CardDefinition(name,(CellSpec(0,0,frozenset(edges)),))
        board=Board();board.seed(card('start',{Direction.EAST}))
        state=GameState(board=board,draw_pile=Hidden(),hand=[card('end',{Direction.WEST}),card('a',set()),card('b',set())])
        before=(dict(board.cells),list(state.hand),state.raincoats,state.ropes,state.exit_placed,state.turns)
        rng=Rng();move=p.VisibleEndStateBeamV8Policy().choose(state,rng)
        self.assertIn(move,state.legal_moves());self.assertEqual(len(rng.calls),1);self.assertEqual(before,(dict(board.cells),list(state.hand),state.raincoats,state.ropes,state.exit_placed,state.turns))

    def test_potential_formula(self):
        state=SimpleNamespace(raincoats=5,ropes=2,exit_placed=True,board=SimpleNamespace(open_tunnels=8,visible_water_cells=1,water_obstruction=2,trapped_water_cells=1,merge_opportunities=7))
        self.assertEqual(p.potential(state),50000-800-20000-2000-100000+1500+5000)
        state.board.open_tunnels=11;self.assertEqual(p.potential(state),50000-1100-20000-2000-100000+5000)

if __name__=='__main__':unittest.main()
