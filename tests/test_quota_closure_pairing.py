"""Cross-implementation integration on invented fixtures, never cohort states."""
from random import Random

import pytest

from test_quota_reserve_closure import fixture, card, E, W
from bandido_alcatraz.model import Material
from bandido_alcatraz.quota_reserve_closure_reference import QuotaReserveClosureReference


@pytest.mark.parametrize('case', ['initial', 'rope', 'wet', 'unplayable', 'met', 'spare', 'exact', 'infeasible', 'covered'])
@pytest.mark.parametrize('rng_seed', [0, 1, 17])
def test_candidate_reference_complete_science_on_invented_inputs(case, rng_seed):
    kwargs = {}
    if case == 'rope':
        kwargs['hand_ids'] = ('rope-0',)
    elif case == 'wet':
        kwargs['wet_coat'] = True
    elif case == 'unplayable':
        kwargs['hand_ids'] = ()
    elif case == 'met':
        kwargs.update(hand_ids=('coat-3',), collected=(('coat-0', 1), ('coat-1', 2), ('coat-2', 3)))
    elif case in ('spare', 'exact', 'infeasible', 'covered'):
        spent = {'spare': 8, 'exact': 9, 'infeasible': 10, 'covered': 9}[case]
        overrides = [card(f'coat-{i}', (E, W), Material.RAINCOAT, water=(case == 'covered' and i == 0)) for i in range(spent)]
        placements = [(f'coat-{i}', (i+2, 0), 0) for i in range(spent)]
        if case == 'covered':
            overrides.append(card('ordinary-47', (E, W)))
            placements.insert(1, ('ordinary-47', (2, 0), 0))
        kwargs.update(hand_ids=(f'coat-{spent}',), overrides=overrides, placements=placements)
    candidate, obs, cards = fixture(**kwargs)
    reference = QuotaReserveClosureReference(catalog=tuple(cards.values()), start_card=candidate._start_card, exit_card=candidate._exit_card)
    crng, rrng = Random(rng_seed), Random(rng_seed)
    cmove, cscience, ccost = candidate.evaluate(obs, crng)
    rmove, rscience, rcost = reference.evaluate(obs, rrng)
    assert cmove == rmove
    assert cscience == rscience
    assert crng.getstate() == rrng.getstate()
    assert ccost == rcost
