# Recent strategy pages implementation plan

**Goal:** Give all four recent experimental strategies the same player explanation, real move walkthrough and agent specification as the existing guide, in RU and EN. Keep the approved Gaming Table design and existing numerical results.

**Architecture:** Reuse the existing static generator, board renderer and public-observation format. Import only a selected public decision from saved completed evidence, with source hashes and policy-state provenance. Verify a single decision without drawing cards or restarting research. Each experiment gets a stable strategies/research-N.html address, linked from all three catalog views and results.

**Tech stack:** Python standard library, existing JavaScript/CSS, pytest and existing Chrome checks.

## Tasks

- [ ] Inspect saved evidence and extract one relevant public position per policy; retain exact source and state provenance, exclude hidden draws and private operations.
- [ ] Add failing tests for four complete bilingual strategy pages, legal examples, unchanged input, exact policy sources and standalone reproduction.
- [ ] Implement dedicated pages and integrate their links and percentages into the catalog and result sections.
- [ ] Translate all new player and agent text; verify narrow/mobile layouts, keyboard controls and exact replay.
- [ ] Create one weekly same-chat automation that checks completed research and site coverage, updates/publishes missing pages, and never resumes research.
- [ ] Independently review, run CI, publish through existing Pages workflow and verify public pages.

## Decisions

The user explicitly requested matching the existing pages, so reuse their agreed design and structure without a new design-choice round. Publish verified updates under the existing publication authorization. Weekly check: Monday 10:00 Asia/Jerusalem; notify only changes, failures or decisions needed. Existing research automations stay paused.
