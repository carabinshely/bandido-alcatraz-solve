# Bilingual guide and Pages publication

**Goal:** Keep complete Russian and English versions of all 27 guide pages and
publish the verified site on GitHub Pages. The user explicitly authorized
enabling Pages and publication in this chat on 2026-11-06; this supersedes the
earlier local-only scope.

**Architecture:** One renderer, shared numerical data and source packages.
`website/locales/en.json` translates complete text nodes and accessible labels
at build time; a missing Russian message fails the build. `website/localize.py`
adds English counterparts under `en/` and rewrites only shared-resource paths.
Language links point to equivalent documents and retain query/fragment context.
Browser-generated labels use the document language.

**Publication:** `.github/workflows/pages.yml`, on trusted `main` changes or
manual dispatch, uses the existing self-hosted Linux `bandido-alcatraz-tests`
runner and Python 3.14.10. Build verifies the site before uploading its artifact;
deploy has Pages/OIDC permissions and the `github-pages` environment. No
GitHub-hosted fallback or simulator changes.

- [x] Add failing page-parity and equivalent-language-link tests.
- [x] Translate all page text, metadata, accessibility labels and browser states.
- [x] Build 54 pages; check every relative URL and source contract.
- [x] Check both locales in Chrome, including storage failure, context, keyboard,
  themes, all strategy examples and A/B walkthrough.
- [x] Enable Pages in repository settings; UI confirmed “GitHub Pages source saved.”
- [x] Fast-forward the feature branch to current `origin/main` (03b9899), retaining
  the repository's updated Python 3.14 baseline and runner configuration.
- [ ] Commit and push the reviewed feature, merge via PR after checks.
- [ ] Verify successful Pages deployment and live Russian/English pages.

## Review and verification

Independent reviewer found no blocking translation/URL/workflow issue. One
language-link freshness edge case was reproduced in Chrome (first tab selection
on a bare URL), fixed by updating contextual links after pushState, and covered
by a regression check. Earlier initial-history-tab fix is retained.

176 website/related-engine tests passed locally. Chrome covers 192 states,
including all 27 English documents, no untranslated Russian UI except the
intentional native-language “Русский” switch, no horizontal overflow, JS errors
or resource failures. Download packages remain shared and executable separately.
