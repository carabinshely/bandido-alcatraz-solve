"""Independent exhaustive implementation; shares serialization only with candidate."""
from ..strategy import preview_move_without_draw
from ..rules import is_victory
from .evidence import LIMIT, BudgetExceeded, validate, observation, sha, move, leaf


def reference_key(node, depth):
    if is_victory(node.status):
        return [2, -depth, 0]
    board = node.board
    value = 10000 * node.raincoats + 10000 * node.ropes
    value -= 100 * board.open_tunnels
    value -= 20000 * board.visible_water_cells
    value -= 1000 * board.water_obstruction
    value -= 100000 * board.trapped_water_cells
    if board.open_tunnels <= 10:
        value += 250 * min(6, board.merge_opportunities)
    if node.exit_placed:
        value += 5000 if node.raincoats == 3 and node.ropes == 2 else -5000
    return [int(board.open_tunnels > 0), 0, value]


class Reference:
    def choose(self, obs, rng):
        return self.evaluate(obs, rng)[0]

    def evaluate(self, obs, rng):
        validate(obs)
        input_hash = sha(observation(obs))
        rng_hash = sha(rng.getstate())
        actions = obs.legal_moves()
        all_roots = []
        preview_count = 0
        child_count = 0
        enumerations = 1
        winners = []
        optimum = None
        for action in actions:
            if preview_count == LIMIT:
                raise BudgetExceeded('reference successor budget exhausted')
            child = preview_move_without_draw(obs, action).successor
            preview_count += 1
            next_actions = []
            if not is_victory(child.status) and child.board.open_tunnels > 0:
                next_actions = child.legal_moves()
                enumerations += 1
            ordered_leaves = []
            if len(next_actions) == 0:
                if is_victory(child.status):
                    cause = 'visible_victory'
                elif child.board.open_tunnels == 0:
                    cause = 'closed_tunnel_loss'
                else:
                    cause = 'omitted_draw_dead_end'
                ordered_leaves.append(leaf((action,), child, reference_key(child,1), cause))
            for next_action in next_actions:
                if preview_count == LIMIT:
                    raise BudgetExceeded('reference successor budget exhausted')
                end = preview_move_without_draw(child, next_action).successor
                preview_count += 1
                child_count += 1
                cause = 'horizon'
                if is_victory(end.status):
                    cause = 'visible_victory'
                elif end.board.open_tunnels == 0:
                    cause = 'closed_tunnel_loss'
                ordered_leaves.append(leaf((action,next_action),end,reference_key(end,2),cause))
            root_key = None
            root_witness = None
            for entry in ordered_leaves:
                if root_key is None or entry['key'] > root_key:
                    root_key, root_witness = entry['key'], entry['sequence']
            all_roots.append(dict(root=move(action), first_transition_sha256=sha(observation(child)),
                                  second_moves=[move(a) for a in next_actions],
                                  second_moves_sha256=sha([move(a) for a in next_actions]),
                                  leaves=ordered_leaves, leaves_sha256=sha(ordered_leaves),
                                  maximum=root_key, witness=root_witness))
            if optimum is None or root_key > optimum:
                optimum, winners = root_key, [action]
            elif root_key == optimum:
                winners.append(action)
        selected = None
        if winners:
            selected = rng.choice(winners)
        after = sha(observation(obs))
        if after != input_hash:
            raise ValueError('reference mutated observation')
        result = dict(schema='worker32-scientific-v1', input_before=input_hash,input_after=after,
                      root_moves_sha256=sha([move(a) for a in actions]), roots=all_roots,
                      maximal_roots=[move(a) for a in winners],chosen=move(selected),best=optimum,
                      rng_before=rng_hash,rng_after=sha(rng.getstate()),
                      counts=dict(roots=len(actions),children=child_count,previews=preview_count,
                                  expanded_nodes=enumerations,enumerations=enumerations,
                                  leaves=sum(len(x['leaves']) for x in all_roots)))
        return selected,result,dict(physical_legal_moves=enumerations+preview_count)
