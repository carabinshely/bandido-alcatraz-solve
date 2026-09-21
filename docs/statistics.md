# Statistical evaluation plan

The solver must separate **search** from **evaluation**. A strategy is never
reported as better merely because it was tuned on the same simulated games.

## Common random numbers

Policies are compared on the same seed set. A seed determines the shuffled
deck order, so paired results remove much of the variance caused by one policy
receiving easier random decks than another.

For two policies A and B, retain:

- both win;
- A wins / B loses;
- A loses / B wins;
- both lose.

The asymmetric cases are the most informative evidence that the policy itself
changed the outcome on the same randomized deck.

## Search vs held-out evaluation

Weight search uses a training seed range. Once weights are selected, the
candidate is evaluated on a disjoint seed range.

Training and evaluation seed ranges must never overlap.

## Win-rate uncertainty

Report a 95% Wilson interval for every retained win-rate estimate.

Approximate worst-case sample sizes for a 95% margin of error around a
proportion, before using paired comparisons:

| Desired half-width | Approximate games |
| --- | ---: |
| +/- 1.0 percentage point | 9,604 |
| +/- 0.5 percentage point | 38,416 |
| +/- 0.25 percentage point | 153,665 |
| +/- 0.2 percentage point | 240,091 |
| +/- 0.1 percentage point | 960,365 |

These are planning figures using the conservative p=0.5 case. Actual Wilson
interval width depends on the observed win rate.

## Experiment ladder

1. 500-2,000 games: smoke / reject obviously bad policies.
2. 10,000 games: coarse strategy search.
3. 40,000+ held-out games: compare plausible finalists around +/-0.5 pp.
4. Increase further only when the observed policy gap is small enough to
   justify it.

Do not spend hundreds of thousands of runs while the exact Alcatraz deck is
still incomplete; model error would dominate sampling error.
