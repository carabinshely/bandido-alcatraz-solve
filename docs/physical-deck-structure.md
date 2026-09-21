# Physical deck structure — v1

Derived from the complete owner-photo transcription in `data/deck-v1.json`.

## Inventory

- 68 ordinary cards
- 30 rotationally canonical external-geometry families
- 12 raincoat cards
- 8 rope cards
- 4 water cards
- 1 separate EXIT card
- 1 double-sided START card

## External-port distribution

| External tunnel ports | Cards | Raincoat | Rope | Water | Gate-marked |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 9 | 1 | 4 | 0 | 9 |
| 2 | 22 | 5 | 2 | 0 | 8 |
| 3 | 20 | 5 | 0 | 2 | 3 |
| 4 | 17 | 1 | 2 | 2 | 0 |

For a placement that consumes exactly one existing open end, the immediate
open-end change is:

`delta_open = external_ports - 2`

Therefore:

- 1-port card: -1 open end;
- 2-port card: 0;
- 3-port card: +1;
- 4-port card: +2.

Connecting a card to two existing open ends improves this by another two.

## Strategy implication to test

Equipment collection has an opportunity cost: the selected equipment card is
removed from tunnel play.

This cost is especially visible for ropes: 4 of the 8 rope cards are 1-port
closure cards. A policy that blindly collects every still-needed rope may
discard scarce closure capacity.

Do not turn this observation into a strategy conclusion without paired
real-deck simulation. The first test should compare:

1. current `greedy_v0`: collect needed equipment unconditionally;
2. geometry-aware collection: prefer collecting equipment on higher-degree
   cards and preserve 1-port closure cards when another route to the required
   equipment remains plausible.

The comparison must use identical deck seeds.
