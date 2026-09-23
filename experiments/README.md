# Experiment artifacts

Git stores experiment definitions plus compact manifests/summaries only.

Large raw per-seed, per-turn, and diagnostic payloads must be uploaded to the durable Google Drive raw-artifact store documented in [../docs/persistence.md](../docs/persistence.md).

Do not commit generated raw JSON merely to preserve it. Local runners should write raw output under `artifacts/raw/` or `artifacts/tmp/`, both ignored by Git.

Human-readable experiment conclusions and orchestration decisions are recorded in Issue #2.
