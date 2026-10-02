"""Root-complete optimized adapter. No cache, pruning, draws or horizon choices."""
from .evidence import (LIMIT, BudgetExceeded, validate, sanitized, observation, sha,
                       move, leaf)
from ..rules import is_victory


def prevalidated_preview(state, action, legal):
    if action not in legal:
        raise ValueError('adapter requires node-local legal membership')
    result = sanitized(state)
    result.apply(action, validate=False)
    return result


def potential(s):
    b = s.board
    bank = min(b.merge_opportunities, 6) if b.open_tunnels <= 10 else 0
    exit_term = (5000 if (s.raincoats, s.ropes) == (3, 2) else -5000) if s.exit_placed else 0
    return (10000*(s.raincoats+s.ropes)-100*b.open_tunnels-20000*b.visible_water_cells
            -1000*b.water_obstruction-100000*b.trapped_water_cells+250*bank+exit_term)


def ranking(s, depth):
    if is_victory(s.status):
        return (2, -depth, 0)
    return (1 if s.board.open_tunnels else 0, 0, potential(s))


class Candidate:
    def choose(self, obs, rng):
        return self.evaluate(obs, rng)[0]

    def evaluate(self, obs, rng):
        validate(obs)
        before, rb = sha(observation(obs)), sha(rng.getstate())
        roots = obs.legal_moves()
        records = []
        previews = children = expanded = 0
        physical = 1
        for root in roots:
            if previews >= LIMIT:
                raise BudgetExceeded('before preview 32769')
            first = prevalidated_preview(obs, root, roots)
            previews += 1
            seconds = []
            terminal = is_victory(first.status) or first.board.open_tunnels == 0
            if not terminal:
                seconds = first.legal_moves()
                expanded += 1
                physical += 1
            leaves = []
            if not seconds:
                reason = ('visible_victory' if is_victory(first.status) else
                          'closed_tunnel_loss' if not first.board.open_tunnels else 'omitted_draw_dead_end')
                leaves.append(leaf([root], first, ranking(first, 1), reason))
            else:
                for second in seconds:
                    if previews >= LIMIT:
                        raise BudgetExceeded('before preview 32769')
                    final = prevalidated_preview(first, second, seconds)
                    previews += 1
                    children += 1
                    reason = ('visible_victory' if is_victory(final.status) else
                              'closed_tunnel_loss' if not final.board.open_tunnels else 'horizon')
                    leaves.append(leaf([root, second], final, ranking(final, 2), reason))
            best = max(x['key'] for x in leaves)
            witness = next(x['sequence'] for x in leaves if x['key'] == best)
            records.append(dict(root=move(root), first_transition_sha256=sha(observation(first)),
                                second_moves=[move(m) for m in seconds], second_moves_sha256=sha([move(m) for m in seconds]),
                                leaves=leaves, leaves_sha256=sha(leaves), maximum=best, witness=witness))
        best = max((r['maximum'] for r in records), default=None)
        tier = [m for m,r in zip(roots,records) if r['maximum'] == best]
        chosen = rng.choice(tier) if tier else None
        after = sha(observation(obs))
        if after != before:
            raise ValueError('input mutated')
        payload = dict(schema='worker32-scientific-v1', input_before=before, input_after=after,
                       root_moves_sha256=sha([move(m) for m in roots]), roots=records,
                       maximal_roots=[move(m) for m in tier], chosen=move(chosen), best=best,
                       rng_before=rb, rng_after=sha(rng.getstate()),
                       counts=dict(roots=len(roots), children=children, previews=previews,
                                   expanded_nodes=1+expanded, enumerations=1+expanded,
                                   leaves=sum(len(r['leaves']) for r in records)))
        return chosen, payload, dict(physical_legal_moves=physical)
