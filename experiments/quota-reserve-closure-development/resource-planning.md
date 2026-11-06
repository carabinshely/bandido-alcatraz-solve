# Worker35 preliminary resource proof and candidate audit

This is planning evidence, not execution permission or a resource freeze. The
scientific review initially examined candidate SHA256
`c660f0466ff770157d0d0eec9d520636c8359de147e1f69f817c9ad6d13ef870`.
No real observation, real-deck policy evaluation, shuffled game, cohort or
reference implementation/test was run/read by this reviewer. Static immutable
catalog metadata was inspected only to establish geometry/resource constants.
Source fixes and final exact-head independent reviews remain required.

## Candidate scientific audit

The complete original 365-line candidate and 484-line candidate-only synthetic
tests were read with the protocol/audit contract and canonical board, move,
scoring, collection/refresh and serialization code. All 48 candidate-only tests
passed under local CPython3.12.14, not the required CI3.11.16.

No additional scientific selection/guard/RNG defect was established in this
preliminary review. In particular, complete covered placement identities count
as spent; identity and geometry/counter/chronology errors fail; infeasible but
physical A<d states are accepted; short refresh requires six set-aside and exact
needed supply=own hand; terminal observations are rejected; empty live legal
lists return None without RNG; mixed T skips the closure branch; T0 is audit
only; ordered F/T/C/final and crossover flags match the contract; exactly one
choice occurs even for a singleton. Generic synthetic catalogs intentionally do
not enforce production geometry constants: the frozen runner must bind catalog
bytes and verify the constants below before using their numeric bounds.

The root separately reported P2 profile-installation/restoration findings from
an adversarial reviewer and is coordinating fixes. This report does not supersede
those findings. Resource exceptions currently need harness-owned partial
receipts: a failed evaluate has no returned cost/audit tuple, so the harness must
retain input, RNG-before, error, partial counters available from supervision,
and attempt identity rather than inventing a completed decision or game loss.

## Exact candidate physical accounting

Let P be the number of PLACE roots, G the number receiving a guard preview, and
X the number receiving the standalone EXIT guard. Then:

* legal_enumerations = 1 + P + G + X
* previews = P + G
* exit_geometry_checks = X
* 0 <= X <= G <= P

COLLECT scoring uses the no-preview fast path. Each PLACE score performs one
preview and a full legal re-enumeration for membership validation. Each guard
preview does that again. A standalone EXIT check performs a placement_moves
enumeration. Board reconstruction/place does not enter these counted functions.
The counts are candidate-only; do not relabel them as total engine/checker work.

## Static canonical constants and proof

Static sources: physical_deck.py/photo_geometry.py produce two adjacent cells
per ordinary card; deck-v1.json has 68 rows, max4 external ports,64 water_half:null,
2 top and2 bottom. Thus each of the4 water cards introduces exactly one water
cell. Static special_geometry gives two adjacent cells for easy START and EXIT,
both dry; easy START has five external tunnel ends. Ordinary IDs have maximum
JSON-encoded length15 bytes. These facts must be verified against pinned blobs.

At action count t, let n<=t be placements, s in {0,6} be set-aside and
h=min(6,69-t-s)>0. The board has at most B=2+2n cells. Every placement is
geometrically connected to the previous board. A nonoverlap placement with at
most4 external ports changes open ends by at most +2: at least one new and one
old end become connected. A water overlap adds at most one cell with three
external sides, hence at most +3. There are at most4 overlaps over the complete
game: each consumes a previously introduced visible water cell, while only four
water cells can ever be introduced. Therefore

    O <= 5 + 2n + min(n,4),      W <= 4

For one card, every nonoverlap legal placement connects at least one old open
end to one external card port. Across four rotations, each card port faces a
given old end in exactly one orientation, so there are at most4O such candidates.
An overlap can place either of two cells onto one of W water cells in four
rotations, adding at most8W candidates. Duplicates/illegal placements only reduce
the count. Consequently

    P <= h(4O+8W) <= min(6,69-t)*(52+8t+4min(t,4))

The maximum is P<=3,432 at t=63,h=6. At most6 COLLECT roots gives R<=3,438.
Sufficient candidate-only per-call bounds for every valid canonical input:

    legal <= 10,297; previews <= 6,864; EXIT checks <= 3,432; roots <= 3,438

These are mathematical ceilings, not a recommendation to change an already
frozen cap. The proof does not apply to arbitrary oversized invented catalogs.

At most69 nonempty decisions consume cards. Empty-hand-action decisions can
refresh. With u remaining cards, a full hand and ordinary refresh, the engine
checks that some draw card is playable, then rotates batches of six. All the
old draw pile is encountered within ceil((u-6)/6) refreshes. Short refresh occurs
only once and consumes six cards. Thus at most ceil(u/6) policy calls can occur
at each u; summing u=1..69 gives432 calls/game. Keeping MAX_STEPS=1000 unchanged
is required;432 is an analytic bound for this engine, not a changed step cap.

Summing the above P(t) for t=0..68 gives131,500 PLACE roots/game. Therefore:

    candidate/game: legal <=394,932; previews <=263,000; EXIT <=131,500
    candidate+replay800 games: legal <=315,945,600;
                              previews <=210,400,000; EXIT <=105,200,000

The reference is independently implemented. Its reviewer must derive its own
call graph; multiplying these counts by two is valid only if independently
proved sufficient. Checking every candidate and replay decision adds checker
work on at most345,600 observations but no extra game executions. Control's400
games, apply/refresh checks, serialization and independent final verification
are additional costs, not included in those candidate-only totals.

### Why operation counts do not prove a small wall cap

The enumerator also tries internal-facing ports that later fail legality. At
most6 tunnel edges per ordinary two-cell card gives at most h(6O+8W) trial
origins, at most5,052 on a maximal original board. At the per-call upper bound,
the 1+P+G full-hand enumerations plus X standalone EXIT enumerations may perform
up to37,551,132 trial can_place calls before accounting for all other work.
Each rotates/builds card objects and is accompanied by many Python profile
events. Counted enumerations are therefore not interchangeable constant-time
operations. Both full-root rescoring membership and profile overhead matter.

## Evidence-size bound, conditional on the specified wire

For compact worker32.evidence.canonical JSON, a conservative allowance is
300 bytes per root across root+guard+all five tier memberships, plus4KiB fixed
science overhead. This exceeds constructed maximum-field record lengths (101
bytes/root record,107 bytes/guard, plus<=25 bytes for five indices) with safe
coordinate/score/count widths. Coordinates stay within three decimal digits
because connected boards contain<=140 cells; absolute V4-250 score<2,000,000
follows from finite geometry/weights. These bounds must be rechecked if the
wire schema changes.

A public observation fits within32,768+80J bytes, where J is maximum JSON-encoded
card ID length. This conservatively allows138 visible cells,70 placement
records,6 hand cards,5 collection records and fixed setup/counters, even though
their individual maxima cannot all occur together. With J=15, this is33,968
bytes. Per candidate decision, science+one public observation is therefore
<=1,069,464 bytes (about1.02MiB). Costs/runner envelope require a separate margin.

Using432 calls/game,131,500 PLACE roots and at most414 COLLECT roots/game yields
exactly33,074,937,600 bytes (30.8034GiB) of science for800 candidate/replay games.
Public observation snapshots for all1200 passes add at most17,609,011,200 bytes
(1200*432*33,968).
Control roots/scores, checker receipts, trace metadata, conservation records,
manifests and errors are additional. Persisting duplicate full reference science
would add up to another30.8034GiB; matching independent science hash+separate
costs can avoid duplication if the frozen evidence contract permits it.

These loose bounds show why4GiB expanded/1GiB archive cannot be promised from
finite-card reasoning alone. They do not predict actual output size or require
allocating all worst-case bytes. A smaller prospectively justified hard output
cap may explicitly terminate resource-incomplete; never increase it after
outcomes. Compression ratio has no proven minimum and must not justify a raw
output promise.

For32MiB transport, use deterministic independently hashed shards with a
prospectively fixed raw payload threshold such as16MiB (or31MiB with explicit
wrapper allowance), never a nominal32MiB file plus compression/header overhead.
Check actual persisted shard size before upload. The full single-decision upper
bound fits comfortably; fail explicitly if a future record exceeds the shard
contract. Streaming write/hash/close is needed: do not accumulate all1200 traces
in RAM. Fix filename order, exact boundary algorithm, JSONL newline rules,
compression parameters/timestamps and partial-shard behavior before execution.
Retain completed shards and partial receipts on failure. Byte/hash readback is
still required; many thousands of theoretical shards also cost verification and
upload time.

## Local invented benchmarks and practical freeze requirements

The companion benchmark_candidate_synthetic.py builds only invented catalogs:
12 one-cell raincoat caps facing W,8 rope caps,48 ordinary one-cell cards, and
one invented EXIT cap. The first n ordinary cards are four-way N/E/S/W and are
manually placed at(2+i,0) from an invented two-cell five-exit START. The hand is
coat-0..coat-5. It calls evaluate once per fixture with its production profile
hook. It never constructs/shuffles/runs a game or loads real data. It requires
an exact candidate SHA and emits executable digest, mapped-library digests where
available, runtime/platform, input/science hashes, physical costs, wall/CPU,
process high-water RSS and byte counts. Use --expected-candidate-sha256 for the
reviewed final source; do not quietly replace its oldhash default.

Oldhash local CPython3.12.14 exploratory results:

* n=0:36 roots;91 legal,60 previews,30 EXIT;0.137636s profiled;7,182 science bytes
* n=4:84 roots;235 legal,156 previews,78 EXIT;0.744366s profiled;15,713 bytes
* n=8:132 roots;379 legal,252 previews,126 EXIT;1.626882s profiled;24,288 bytes
* n=40:516 roots;1,531 legal,1,020 previews,510 EXIT;24.949681s wall,
  24.940630s CPU,24,188KiB process peak RSS;93,602 science bytes

An exploratory in-memory hook-suppression comparison on n=0/4/8, with identical
complete scientific outputs/RNG, took0.036665/0.207418/0.488396s respectively:
profile overhead ratios3.754/3.589/3.331. The suppressed mode is not present in
the benchmark script or permitted in the execution harness. These local values
are not pinned-CI caps, worst-case performance proofs or real-cohort timings.

Run the hook-enabled script under the actual pinned3.11.16 CI runtime, preserving
its raw JSONL. Add independently authored checker benchmarks on exactly the same
invented inputs without importing candidate helpers; record checker cost/time
separately. Include sequential candidate+checker timing and synthetic sharding,
compression, verifier, output overflow, timeout/RSS kill and partial-retention
tests. A process RSS high-water mark is cumulative, not precise per-call live
memory; supervise the complete process group/cgroup as well.

No defensible small numeric wall-time/memory/archive freeze can be derived solely
from these local timings or historical Worker31's35m43s. The latter used a
different candidate/call graph and did not establish this profiler+checker cost.
Choose practical protections only after pinned synthetic measurements with
headroom, retain a hard overall runner/job timeout, and explicitly accept that
an extreme valid state can still produce a resource-incomplete attempt. This is
a practical abort boundary, distinct from mathematically sufficient physical
operation ceilings and from scientific validity. No outcomes, policy weights,
seed population or scientific selection rules may inform cap changes.


## Status at publication

These bounds and local synthetic timings are prospective planning evidence only.
The source/runtime/resource execution freeze remains pending. Two profiler
restoration failure paths found by the independent adversarial review were
repaired and independently rechecked on candidate f7e61f41 and reference 4a27004f.
Pinned-runtime CI and complete harness reviews remain pending. The scientific selection rule and
permanently spent three-pass population remain unchanged.
