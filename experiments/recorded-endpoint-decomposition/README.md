# Worker34: recorded endpoint component analysis

[Protocol](https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5945805807) · [Exact execution freeze](https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5946428854) · [Acceptance lifecycle](https://github.com/carabinshely/bandido-alcatraz-solve/pull/37)

## Result and meaning

`recorded_component_tradeoff_present`: **N = 69/80**, **U = 0**, overlap = 0.
Every observation had eligible two-PLACE endpoints. Both independently authored
parsers read all 160 existing Worker33 call payloads, verified all 80 source
pairs, and produced byte-identical complete scientific outputs: 383,840 leaf
rows, 80 observation rows and one summary per parser.

In 69 of the fixed observations, at least one recorded two-PLACE endpoint has a
higher value of the frozen geometric component G than every collection-containing
endpoint in the same EXIT stratum, while leaving more equipment uncollected.
G is the old weighted geometric component obtained by subtracting the exact old
inventory and endpoint EXIT terms from recorded H. No board was reconstructed,
no H was reevaluated, and no new policy, search, game or seed was executed.

This is exploratory secondary analysis motivated by Worker33's observed result.
It does not prove that placement is strategically better, validate G, isolate the
causal effect of the equipment coefficient, or identify which same-EXIT comparator
won globally. It excludes retained-hand utility and distinctions not represented
by G. No win-rate, adoption, confirmation or PROGRAM_SUCCESS claim follows.
Worker33's original `mechanism_not_exercised` classification is unchanged, and
that unchanged-H/horizon-two advancement line remains closed.

## Reproducible evidence

See `analysis-2026-10-02.manifest.json` for exact input/source/output hashes,
resource receipts, persistence and limitations. Execution was frozen at commit
`d1cb996a92b2776cd513c50a86de86e78a58b666`, tree
`4d180fb370e4ec031f08847c3a41a83aab6f1579`; a later checkpoint commit is not the
execution head. `PROTOCOL.md` is immutable and retains its prospective wording.

The original Worker33 Actions ZIP remains a separate immutable input:
19,184,749 bytes, SHA256
`18a58ec0505d81eaf4b0cfb4798b7e38b0d9555d22ad77c5d4681b5fce89492a`,
[canonical raw copy](https://drive.google.com/file/d/1WJE6WVR8bW0BSTTBoqx8GWkLWm1d7MAu/view).
The complete terminal bundle is preserved in three disjoint ZIPs listed in the
manifest: proof, parser A output and parser B output. All three canonical-folder
memberships and fresh byte-for-byte/hash readbacks are verified. Both parser output copies and all failed preflight attempts
are preserved; neither completion is discarded merely because the bytes match.

The native cloud attempt used the pinned CPython 3.12.14 interpreter and two
serial standard-library parsers. It completed with both exits zero, no failure
causes and successful cleanup. The supervisor measured 146.888 seconds before
final receipt closure; that closure remained guarded by the same 600-second
whole-workload deadline. Each parser's soft/hard RLIMIT_AS was exactly 2 GiB.
This is per-process virtual address space, not an aggregate RSS cap.

Source, tests and supervisor are isolated research scripts; they do not register
or modify a game policy. There is no active research workflow. Scripts retained
for reproducibility do not authorize a silent rerun. Any rerun or new scientific
question requires the separate recorded program decision required by the protocol.

## Validation and failed attempts

Before real-input execution, full independent exhaustive and adversarial reviews
were repeated after every source change. They repaired failure-receipt closure,
abort signaling order, administrative/schema validation, cleanup provenance,
portable test output paths and relocated-interpreter loader handling. Original
failed synthetic receipts and CI runs remain part of the proof record.

Native full suite: 794 tests and 516 subtests passed. The 37-test resource suite
had zero skips, including compiled shared-library fixtures. Exact-head runner CI
36970793740 passed 792 tests, 2 skips and 516 subtests on CPython 3.11.16. Native
analysis runtime and CI runtime are deliberately reported separately. Final PR
review, final CI, merge and post-merge acceptance are recorded in PR37 and Issue2;
this execution document does not preclaim their outcome.
