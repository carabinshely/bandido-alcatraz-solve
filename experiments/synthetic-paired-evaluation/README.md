# Synthetic paired evaluation

This is a framework validation experiment, **not** a Bandido: Alcatraz
strategy result.

Every policy receives the same seed range, which means it receives the same
randomized deck order for a given seed. The receipt records both per-policy
win rates with 95% Wilson intervals and paired outcomes.

This experiment exists to prove that the evaluation machinery can distinguish
policy effects from random-deck effects before the exact Alcatraz deck is
available.
