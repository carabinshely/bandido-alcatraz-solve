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

## Download names and complete outer verification

The original proof README expects the following sidecars beside the ZIPs. Their
exact original bytes are now tracked here:

- [Package catalog](worker34-package-catalog.json)
- [Outer checksums](worker34-packages-SHA256SUMS)
- [Independent archive readback receipt](worker34-readback-verification.json)

Use this repository directory as the working directory, or copy those three
sidecars into a fresh verification directory. Download each authenticated Drive
file and explicitly save or rename it to the filename below. Drive's stored
`bandido-` prefix is a descriptive upload name and is not part of these local
checksum filenames:

- [Proof ZIP](https://drive.google.com/file/d/1lMcrgzUg67Ngnk2ujcGuPyMi7hb90_Hj/view): `worker34-terminal-proof-2026-10-02.zip`
- [Parser A ZIP](https://drive.google.com/file/d/1pxHJjEh42y1AdKKeVfeZSkj-5CbfQqSQ/view): `worker34-output-a-2026-10-02.zip`
- [Parser B ZIP](https://drive.google.com/file/d/1eAiNYDABIGsR7Vq6DT6R8EXkth6r06Pf/view): `worker34-output-b-2026-10-02.zip`
- [Original external Worker33 ZIP](https://drive.google.com/file/d/1WJE6WVR8bW0BSTTBoqx8GWkLWm1d7MAu/view): `bandido-worker33-original-actions-36961069413-1.zip`

After downloading these exact files, run from that directory:

```sh
set -eu
sha256sum -c worker34-packages-SHA256SUMS
mkdir worker34-unpacked
unzip -q worker34-terminal-proof-2026-10-02.zip -d worker34-unpacked
unzip -q worker34-output-a-2026-10-02.zip -d worker34-unpacked
unzip -q worker34-output-b-2026-10-02.zip -d worker34-unpacked
cd worker34-unpacked/worker34-terminal-proof
sha256sum -c SHA256SUMS
python3 -B verify_output_integrity.py \
  --artifact ../../bandido-worker33-original-actions-36961069413-1.zip \
  --receipt ../reproduced-integrity.json
(cd accepted-worker33-proof && sha256sum -c SHA256SUMS)
```

This verifies preserved evidence only. It does not rerun either analysis parser,
recompute G/dominance, evaluate a policy or execute games. The checker validates
the original external archive's pinned bytes as well. Keep the separately
supplied readback receipt as historical verification evidence; a new local
verification writes a new receipt and must not overwrite that original.

The sidecar publication and filename clarification repair packaging instructions
only. All three previously persisted ZIPs, scientific outputs and execution
sources remain byte-identical; no analysis rerun occurred.
