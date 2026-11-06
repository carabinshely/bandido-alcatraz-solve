# Local strategy site implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan in this session. The user approved the design and requested implementation; no additional design approval is pending.

**Goal:** A locally served Russian guide with all 15 existing policies and three catalogue views in the approved «Игровой стол» design.

**Architecture:** Build ordinary HTML pages from one content JSON using Python's standard library. Keep browser JavaScript limited to catalogue tabs, remembered navigation, theme and recorded-position interactions. Relative URLs work under a GitHub Pages project prefix.

**Tech Stack:** Python 3.11+, HTML, CSS, browser JavaScript; no npm dependencies.

**Spec:** Approved «Игровой стол» mockup and three catalogue views from this chat. Prioritize understandable player advice, with exact agent contracts and source provenance.

## Global constraints

- Local only; no publication, external writes or new research cohorts.
- Fifteen policies, seven player-task families, V0–V7 history plus the separate catalogue branch.
- Current canonical model: v2-exact-equipment-quota-limited-collect-full-hand-refresh.
- Historical evidence must not be ranked against current-model results.
- Preserve the verified seed 1000263, decision 8 example; any new policy replay of that observation is explicitly a recalculation with fixed RNG, not the recorded historical action.
- Existing physical geometry and embedded fonts only; no new generated assets.

## Review focus

- Direct strategy URLs and refresh work below a project subdirectory.
- All three views contain the same policies; detail pages retain return context.
- Unavailable browser storage must not prevent navigation.
- Mobile text, cards, source paths and controls reflow at 320px.
- Agent parameters must match source, notably explicit V4 setup_weight=250 rather than the constructor default 500.

### Task 1: Content and static pages

**Files:** `website/content.json`, `website/build.py`, `website/templates/`, `website/assets/`, `tests/test_website.py`.

- [x] Write and run failing integrity tests for the generated site, complete inventory, local links, source contracts and static-prefix compatibility.
- [x] Import the approved content and verified example. Add exact source/weight data and provenance for all policies.
- [x] Generate the catalogue, individual strategy pages, rules and evidence pages, and downloadable reproduction materials into `website/dist/`.
- [x] Run the integrity tests to green.

### Task 2: Browser experience and verification

**Files:** `website/assets/site.css`, `website/assets/site.js`, `website/check.cjs`, `website/README.md`.

- [x] Implement three accessible catalogue tabs, persistent return context, stable links and position controls.
- [x] Check navigation, reload/back/forward, disabled storage, download links and the board example in Chrome.
- [x] Inspect screenshots at mobile and desktop widths in both themes; fix observed functional defects.
- [x] Run repository tests and record the actual results.
- [x] Serve locally, request opening the preview, and provide launch instructions. Do not publish.

## Verification and review

- 27 HTML pages, all local links and anchors checked; relative URLs tested below `/project/`.
- 174 targeted website/engine tests passed; both reproduction ZIPs run outside the checkout.
- Chrome: 84 catalogue/strategy width/theme states, all 15 policy pages, six cards per hand, correct before/after geometry, no JS exceptions or HTTP failures.
- Storage disabled, theme cycling, tab keyboard navigation, deep link expansion, return/reload and history checked.
- Independent reviewer found initially remembered tab lost on Back. Added a failing Chrome regression check, fixed history entry state, reran successfully.
- Complete repository pytest collection has nine existing Windows blockers: eight Linux `resource` imports and a byte-pinned Worker31 helper checked out with CRLF. Confirmed committed LF bytes match its expected pin. No simulator or historical verifier changes made.
- Server on 127.0.0.1:8765 returned HTTP 200. Codex panel open request returned `queued`; direct local link provided in handoff.
