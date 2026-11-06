# Numeric strategy results

User request: a linked summary table with wins/total games for every strategy,
and the same concrete numbers prominently on each strategy page, in both locales.
Existing authorization covers continued publication through the Pages workflow.

- [x] Recover recorded results without new simulations. Keep cohort, model,
  hand size and source for every numerator/denominator; do not pool cohorts.
- [x] Build one source-backed result registry. Use it for the All algorithms
  tab, the Results page and each strategy's visible result block.
- [x] Translate labels and conditions; verify numeric consistency, links and
  responsive tables. Run website/engine tests and independent review.
- [ ] Publish through a reviewed PR and verify the deployed pages.

Current-rule routine smoke (already run in CI #42177440648) supplies results
for RandomLegal, MinOpen, V0 and V1. It is a 20-game smoke, not confirmation.
Historical V1–V3 receipts recovered from recorded GitHub source refs; V5–V7
and current V4 use existing repository manifests. CatalogSupport retains its
two distinct 240-pair cohorts. No new seeds or research runs are authorized.
