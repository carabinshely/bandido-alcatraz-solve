# Persistence model

## Canonical Git state

Commit these:

- formalized rules and modeling decisions;
- abstract deck specification and its validation checks;
- simulator and policy code;
- experiment manifests;
- compact aggregate results sufficient to reproduce and compare experiments.

## Non-canonical local/generated state

Do not commit these:

- raw per-game traces from large runs;
- SQLite databases used as execution caches;
- temporary search state;
- physical card photographs or scans;
- generated profiling output.

Local execution state belongs under `var/` and is ignored by Git.

## Reproducible experiment receipt

Every retained aggregate result should record:

- simulator Git commit SHA;
- ruleset identifier/version;
- deck identifier and content hash;
- policy identifier and complete parameters;
- player count/difficulty/hand size;
- random-number-generator seed definition;
- number of games;
- wins/losses and win rate;
- loss-reason counts where available;
- runtime metadata that can affect determinism.

The raw trace is disposable; the experiment definition and aggregate receipt are durable.

## Change flow

After the empty-repository bootstrap, substantive changes use a branch and pull request. Results are never silently overwritten: a changed ruleset, deck, policy, or experiment definition produces a new versioned result.
