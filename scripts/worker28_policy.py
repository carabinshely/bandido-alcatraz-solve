"""Frozen V8: width-16, at-most-three-action visible end-state beam search."""
from dataclasses import dataclass
from bandido_alcatraz.strategy import preview_move_without_draw, _bounded_merge_bank
from bandido_alcatraz.rules import is_equipment_ready

@dataclass(frozen=True)
class Node:
    state: object
    root: int
    depth: int

def potential(state):
    board=state.board
    ready=is_equipment_ready(state.raincoats,state.ropes)
    exit_term=(5000 if ready else -5000) if state.exit_placed else 0
    return (10000*(min(state.raincoats,3)+min(state.ropes,2))
            -100*board.open_tunnels-20000*board.visible_water_cells
            -1000*board.water_obstruction-100000*board.trapped_water_cells
            +250*_bounded_merge_bank(board)+exit_term)

def rank(node):
    if node.state.won:return (2,-node.depth,0)
    value=potential(node.state)
    return (0,0,value) if node.state.board.open_tunnels==0 else (1,0,value)

class VisibleEndStateBeamV8Policy:
    WIDTH=16
    HORIZON=3

    def choose(self,state,rng):
        if state.won or state.board.open_tunnels==0:return None
        first=state.legal_moves()
        if not first:return None
        beam=[Node(preview_move_without_draw(state,move).successor,i,1) for i,move in enumerate(first)]
        beam=sorted(beam,key=rank,reverse=True)[:self.WIDTH]
        for _ in range(2,self.HORIZON+1):
            expanded=[];did_expand=False
            for node in beam:
                if node.state.won or node.state.board.open_tunnels==0:
                    expanded.append(node);continue
                moves=node.state.legal_moves()
                if not moves:
                    expanded.append(node);continue
                did_expand=True
                expanded.extend(Node(preview_move_without_draw(node.state,move).successor,node.root,node.depth+1) for move in moves)
            beam=sorted(expanded,key=rank,reverse=True)[:self.WIDTH]
            if not did_expand:break
        best=max(map(rank,beam))
        roots={node.root for node in beam if rank(node)==best}
        return rng.choice([move for i,move in enumerate(first) if i in roots])
