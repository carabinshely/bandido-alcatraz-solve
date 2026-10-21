# Paired35 bounded capacity (source proposal, not execution GO)

The single fixed 100-pair CI run has 200 games. The preceding paired34 run actually emitted 700,784,017 decoded bytes and 38,568 framed records across its 100 pairs; its original artifact was 23,711,548 bytes. Those measurements describe a different policy and are planning evidence, not an upper proof for this candidate.

The prospective driver hard-vetoes before every call/write at 1 GiB decoded JSON, 64 MiB compressed evidence, 65,536 framed records, 1,200 per-pair journal rows, 4 MiB terminal reserve, 32,768 physical counted operations per call, 512 MiB address space, and 14,400 seconds whole-run. The workflow timeout must exceed the bounded driver by 20 minutes. Evidence is always lossless; a cap hit yields an incomplete run, not a favorable 100-pair verdict or truncated game. At most one first issue; no retry, replacement, suffix resume, or outcome-selected stopping.

The 5 GB owner ceiling needs a separately measured prospective reservation and retained copies before GO. This file does not reserve disk, issue seeds, or prove actual runtime fit.
