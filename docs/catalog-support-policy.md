# Catalog-support policy

`CatalogSupportPolicy` in `src/bandido_alcatraz/catalog_support.py` is the exact
source tested in two independent local paired cohorts (SHA-256
`6b668193a5a763561ca0c91fd15be3e3dbbaa38b2283b9085b84365ca3718b4a`).
Construct it with the photographed deck's `ordinary_cards` and `exit_card`.
It uses only public board geometry and the visible hand; the physical card
catalog is fixed before play. Its base scoring is `BoundedMergeV4Policy` with
`setup_weight=250`.

Both cohorts used simulator snapshot commit
`e0ea569ba4cbdfad1c7cc4fdd1cbc1998de101aa` (38-file source/data manifest
SHA-256 `c44acf56b6ef9561c542f7f7914b56ec2bef5f3ff10a8a939c78a6c1257df7a8`),
ruleset `v2-exact-equipment-quota-limited-collect-full-hand-refresh`, and setup
`p1-easy-5-exit-hand6-first0-full-hand-refresh`. The photographed deck files
were `data/deck-v1.json` SHA-256
`ed399db69ee50b82fe3ccbe1d6b2f7ab642dc3384f01eb3236100439bfc0fdfb`
and `data/deck-observations-v0.json` SHA-256
`1c246d4c978fae76d898d0beb33e629fca71790b04ec439fe0681bf1d3cdaf25`.
The simulator `src/bandido_alcatraz/simulate.py` SHA-256 was
`4d9ea62bbb92e30e6ba82b0a6e7443b113438da09b0af8a19f17069263443ceb`.

The policy keeps an immediate winning move. Otherwise it considers up to three
near-best V4 placements and prefers the one that leaves the weakest open target
coverable by more catalog cards. Collection follows the V4 choice.

| Fresh paired cohort | Candidate wins | V4-250 wins | Discordant wins (candidate/control) | Exact two-sided paired p |
| --- | ---: | ---: | ---: | ---: |
| 1001729–1001968 (240 pairs) | 37 | 28 | 9 / 0 | 0.00390625 |
| 1001969–1002208 (240 pairs) | 34 | 21 | 14 / 1 | 0.0009765625 |

The second cohort was fixed before its seeds were issued and used the unchanged
candidate and control. Its paired win-rate difference was +5.42 percentage
points; a conservative 95% interval was +0.32 to +10.17 points. Both cohorts
support a positive direction, while the second interval does not establish a
gain of at least five points. The earlier 30-pair screens selected the policy,
so their outcomes are development data, not additional confirmation.

The raw traces, first-dispatch receipts, frozen source/runtime pins, validation,
and complete packets were read back from the owner-only private Drive Raw folder.
Packet SHA-256 values: first cohort
`8155eeeaf63ae5ca7005564fc251b0602fee123ef096bfea917c1a19bd8c10b7`;
independent cohort
`280a4e5f4a1f5ab7c3df2c5ab0338ea9570dbc57c0d9dc0f959e1279e13ad45e`.
This page records the tested policy and results; future policy changes require
new evaluation rather than inheriting these results.
