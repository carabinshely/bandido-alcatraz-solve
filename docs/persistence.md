# Persistence model

## Canonical Git state

Commit these:

- formalized rules and modeling decisions;
- abstract deck specification and validation checks;
- simulator and policy code;
- experiment definitions and compact manifests;
- compact aggregate summaries needed to reproduce and compare experiments.

Do **not** commit large per-seed, per-turn, or diagnostic raw payloads.

## Durable raw experiment storage

Google Drive is the durable store for raw experiment artifacts.

Project folder:

- Bandido Alcatraz Solver / Experiment Artifacts / Raw
- Drive folder ID: `1sQhQY3aKuHvQfyOTUIQjJGANCKOwKgEd`
- Drive URL: https://drive.google.com/drive/folders/1sQhQY3aKuHvQfyOTUIQjJGANCKOwKgEd

Prefer compressed `.json.gz` for large JSON payloads.

A Git manifest that references a Drive artifact should record at least:

- experiment identifier and schema version;
- simulator Git commit SHA;
- workflow run URL / ID;
- ruleset and deck identifiers;
- policy identifier and complete parameters;
- deterministic seed set or range;
- aggregate result summary;
- Drive file ID / URL;
- raw artifact byte size;
- SHA-256 checksum of the uploaded raw bytes.

The Drive raw artifact and its Git manifest form one durable experiment record. Human interpretation and orchestration decisions remain in Issue #2.

## Local/generated state

Local runners may write temporary raw outputs under `artifacts/raw/`, `artifacts/tmp/`, and `var/`. Those paths are ignored by Git.

Other non-Git state includes SQLite execution caches, temporary profiling output, and physical card photographs/scans.

## GitHub Actions artifacts

GitHub Actions artifacts may be used as temporary transport from a self-hosted run to durable storage, but they are not the sole durable experiment store.

## Change flow

Research workers must not accumulate indefinitely on one implementation PR. At a stable implementation checkpoint:

1. persist raw artifacts outside Git;
2. keep only compact manifests/summaries in Git;
3. run CI and review;
4. merge the bounded PR;
5. start the next research slice from fresh `main`.
