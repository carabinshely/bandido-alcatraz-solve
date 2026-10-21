# Paired33 bounded capacity (source proposal, not execution GO)

The single fixed 100-pair CI run has 200 games. The previous twelve-pair run actually emitted 74,956,163 decoded bytes, 4,214 records, and a 2,584,275-byte ZIP in 955.18 seconds. Linear extrapolation gives about 625 MB decoded, 35,117 records, and 2.21 hours; it is a planning estimate, not an upper proof for the new policy.

The prospective driver hard-vetoes before every call/write at 1 GiB decoded JSON, 64 MiB compressed evidence, 65,536 framed records, 1,200 per-pair journal rows, 4 MiB terminal reserve, 32,768 physical counted operations per call, 512 MiB address space, and 14,400 seconds whole-run. The workflow timeout must exceed the bounded driver by 20 minutes. Evidence is always lossless; a cap hit yields an incomplete run, not a favorable 100-pair verdict or truncated game. At most one first issue; no retry, replacement, suffix resume, or outcome-selected stopping.

The 5 GB owner ceiling needs a separately measured prospective reservation and retained copies before GO. This file does not reserve disk, issue seeds, or prove actual runtime fit.
