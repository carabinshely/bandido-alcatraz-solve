from dataclasses import replace
from bandido_alcatraz.equipment_closure import EquipmentReadyClosurePolicy
from bandido_alcatraz.policies import BoundedMergeV4Policy


def test_only_closure_weight_changes() -> None:
    policy = EquipmentReadyClosurePolicy()
    baseline = BoundedMergeV4Policy(setup_weight=250).weights
    assert policy.v4_weights == baseline
    assert policy.candidate_weights == replace(baseline, delta_open_tunnels=20_000)
