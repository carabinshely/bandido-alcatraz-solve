# Worker35 prospective resource decision

This document selects protections before any Worker35 real observation or game.
It is not execution permission. The exact final source/tree/configuration,
independent reviews, required CI and one admitted attempt must still be bound by
a separate Issue #2 execution-go. The scientific protocol and population are
unchanged: 400 control, 400 candidate, 400 replay on permanently spent seeds
1000000–1000399, with the preregistered conditional net +8 development screen.

## Measured preflight

The actual production AuditPolicy path, all three profiling layers, independent
reference, public/engine checks, serialization and durable journal writes were
measured only on five invented fixtures on the existing runner:

- Source head: `2aeb8825f3d784d9c4385579d10e8543e9d957a6`
- Run: https://github.com/carabinshely/bandido-alcatraz-solve/actions/runs/36985323612
- Synthetic job: `110768927991`; research jobs skipped
- Artifact: `11217148461`, 2614 ZIP bytes,
  SHA256 `9b545289465eb4075e13a20d2ad01d3ee55b82a27bc9b12ce620c17edd6a8fbe`
- Retained JSONL: `synthetic-preflight-2aeb8825.jsonl`,
  SHA256 `c8d555cd0288f7e2341a2788217360cd0530ad33c28f3c4536bf30b3d0ae0c3e`
- CPython 3.11.16, executable SHA256
  `a15ccdaf07655a8667a3687b13171486c9a265d92273ba3ad820fbb64d2cfecc`

All five complete candidate/reference science and cost pairs agreed. Whole
wrapper times for 0/4/8/40/48 invented placements were approximately
0.547/2.587/5.934/86.214/122.323 seconds. Largest fixture: 612 roots, candidate
61.922 seconds, reference 60.337 seconds, peak process RSS 28,792 KiB and
208,917 durable journal bytes. These fixtures are not a random sample of the
real cohort and cannot establish its runtime distribution or likely completion.
Final configuration-head CI repeats the same synthetic benchmark. The retained
measurement is a prospective design input, not a claim that an older clean
review applies to a changed head.

## Fixed protection limits

The machine-readable `execution-freeze.json` is the authoritative configuration.
The same per-call values apply separately to control, candidate and reference:

| Bound | Value |
| --- | ---: |
| Roots per decision | 16,384 |
| Actual legal enumerations per decision | 32,768 |
| Actual previews per decision | 32,768 |
| Actual standalone EXIT checks per decision | 16,384 |
| Wall time per decision implementation | 360 seconds |
| CPU time per decision implementation | 360 seconds |
| Whole-cohort count of each physical operation | 1,000,000,000 |
| Complete three-pass cohort wall time | 64,800 seconds (18 hours) |
| Producer finalization wall time | 7,200 seconds (2 hours) |
| Packaging wall time, separately | 7,200 seconds (2 hours) |
| Process address space | 2 GiB |
| Raw evidence | 16 GiB |
| One decision trace | 128 MiB |
| One JSONL line | 8 MiB |
| One receipt | 8 MiB |
| Complete compressed transport stream | 4 GiB |
| One split compressed-stream payload | 30 MiB |
| Development job hard backstop | 1,380 minutes (23 hours) |

The operation limits exceed the static canonical bounds in resource-planning.md;
the complete immutable model remains separately pinned. Time, memory and output
limits are practical abort boundaries, not proofs every possible valid state
will fit. In particular, no completion forecast is inferred from the old
Worker31 timing or the invented fixture sample. The longer whole-cohort ceiling
avoids an unnecessarily short cutoff while leaving all scientific choices fixed.
Resource overflow remains explicit resource-incomplete; it never becomes a
valid negative screen, a V4 fallback, a dropped seed or a post-result cap increase.

The job backstop leaves one hour beyond the separately bounded cohort,
finalization and packaging phases for setup and preservation. GitHub currently
allows self-hosted jobs up to five days, but its job token can expire after
24 hours. The 23-hour backstop stays below that token lifetime; artifact-shard
uploads run in separate jobs. This uses the existing runner, with no new paid
service or credential. Sources:
https://docs.github.com/en/actions/reference/limits
https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idtimeout-minutes

## Storage and verification boundaries

Before any research seed, check available runner disk against the complete raw
plus compressed budgets and a further 2 GiB safety margin. Recheck native disk
before download/reassembly/extraction. Avoid retaining duplicate complete
archives: keep at most one reassembled archive, the extracted raw tree and a
bounded transient part/wrapper. The cloud verification workspace is not the
research executor.

At most 137 payload parts are needed for a 4 GiB stream with 30 MiB parts, below
the workflow matrix limit. Independently verify actual provider ZIP wrappers
are below the 32 MiB transfer limit, every part's identity/hash/size/order, the
reassembled stream hash, ZIP membership and raw inventory before interpretation.
Each part is uploaded separately. Temporary GitHub artifacts use seven-day
retention; durable canonical Drive persistence and fresh byte/hash readback are
mandatory before acceptance. No failed/superseded evidence is discarded.

Run the independent raw verifier under a separately supervised 7,200-second
wall bound and 2 GiB address-space bound, preserving its logs on failure. This
is independent of producer finalization. The verifier establishes raw scientific
and provenance gates; root separately establishes transport and Drive custody.
A storage/transport or verification blocker never grants acceptance and must
not be relabeled as a valid negative result. Catastrophic OS/filesystem failures
may leave only a durable prefix and external job logs; never claim a receipt or
upload exists without verifying it.

## Source and approval binding

The source inventory covers every tracked execution blob except the freeze
JSON itself. The external execution-go binds the final commit, tree and raw
freeze SHA256, avoiding a self-reference. Review fields declare required clean
roles; they are not approvals. Actual exact-final-head reviews and CI evidence
belong in that external go record. Existing preflight results do not authorize
an altered head automatically. No PR body admission is present at this stage.
