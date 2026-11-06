# Weekly strategy guide maintenance

The user authorized weekly checks and publication of missing strategy pages on 2026-11-06. The recurring same-chat automation is `bandido`, scheduled Monday 10:00 Asia/Jerusalem. Keep this recurring monitor active until the user cancels it; it is not a temporary continuation timer. Do not resume the separately paused research automations.

## Evidence and coverage

Check fresh repository instructions and `origin/main`, the published `sources/site-manifest.json`, `website/content.json`, `inputs/recent-research.json`, and completed local research summaries. Read local `var/orchestrator` without mutation. Discover filenames and sizes first; avoid printing monolithic raw traces. Compare separate policy identities/source hashes and completed study results with the page inventory; a retest of an unchanged policy should update its evidence rather than create a duplicate strategy.

Every supported strategy needs a RU and EN page under `strategies/`, discoverable from all three catalog views and results. Preserve the Gaming Table style. Include an understandable player rule, real public-position walkthrough with before/catalog/chosen controls and visible hand, precise stateful agent contract, exact frozen code and standalone replay, observed win percentage plus original counts, conditions and source provenance. Keep cohorts separate; distinguish experimental status, adoption and statistical superiority. Never infer a missing result or promote a strategy from a single walkthrough.

Only allowlisted public observations, aggregate statistics, frozen policy source and hashes may be published from private evidence. Never publish hidden draws, whole traces/archives, runtime credentials, process/lock records or private storage identifiers. Import scripts are manual tools; CI builds from committed curated inputs and requires no private archive.

`import_recent_examples.py` documents the four initial public-context selections. `replay_recent.py` loads hash-verified policies, recalculates one public decision per strategy with Random(0) and explicitly recorded entry state, validates legality and unchanged input, and never draws cards. It does not claim historical RNG reconstruction or reproduce study win rates. Preserve this distinction for future additions.

## Update and verify

1. Resolve strategy identity, frozen code dependencies and study provenance. Reuse existing page identity for an unchanged policy. If a necessary source or permission is missing, finish independent work and ask one explicit question; do not invent a walkthrough or use a timer to wait for a reply.
2. Update player/agent text, public fixture, result sources, all catalog views, bilingual translations and tests. Add numerical and exact-source checks. Do not run new research games, issue seeds, touch research locks, GPU or phone.
3. Run `python -m pytest tests/test_website.py -q` and `node website/check.cjs`. Validate downloaded replay outside the repository, responsive views, keyboard controls and both languages. Request an independent code/evidence review.
4. Use a `codex/` branch and PR, wait for full CI, merge under the existing publication authorization, then verify the Pages workflow and deployed commit, RU/EN HTML, percentages, public examples and source hashes.
5. Record actual inspection/update evidence in ignored `website/.qa/weekly-maintenance-state.json`. Avoid duplicate PRs and automations. Notify only a real update, meaningful failure or decision needed; stay quiet when nothing changed.
