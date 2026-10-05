# Worker38 prospective native preparation budget gate amendment

Status: review candidate only. This changes no implementation, registered scientific allocation, scientific fixture, runtime version, timing rule, scientific resource limit, or execution authority. No preparation test has been run. Both independent full amendment reviews and a separately recorded adoption are required before implementing this candidate; the later exact source/fixture/command map still requires its own execution gate.

## Reason and exact clause

The registered FINITE-PREPARATION-PLAN.json, fixture_and_execution_gate[2] (line64), says:

> The map must contain a deterministic expected-output bound within8MiB log and24MiB case prefix; do not claim fit from an estimate, raise caps or discard evidence if a bound is exceeded.

Replace only that condition with:

> The map must disclose the deterministic expected-output bounds for all397 fixed selectors, including whether their sum exceeds the unchanged8MiB log and24MiB case-prefix ceilings. A sum above the ceiling does not authorize exceeding it or imply successful completion. Before entering each selector, reserve a reviewed worst-case bound for every reachable known output sink, surviving partial/staged write and required observation of that selector, in addition to the still-unused global failure reserve. Refuse entry when a reservation is unproved or does not fit the remaining allowance. Keep every already-written prefix and all executed-case outcomes, distinguish insufficient allowance (resource_incomplete) from an unproved reservation (execution_blocked before any case, otherwise execution_incomplete), preserve any established stronger failure, and mark all remaining selectors unexecuted. Do not raise caps, discard evidence, count unexecuted cases as passes, reorder cases in response to observations, resume, or retry this batch.

The existing exact-cap H05/H08 output_gate remains binding: those outputs are charged at their actual retained sizes if their selectors are reached. Neither those selectors nor any other selector gains an entitlement to run after the budget closes. This is a prospective preparation admission change made before outcomes exist.

## Disclosed arithmetic

ARITHMETIC.json binds all source proofs and the complete397-method partition:177 retained core/cell/supervisor/transport/verifier,72 driver,84 Worker37,64 Worker38 integration. S01's legacy-produced artifacts are counted once. There are1,078 declared observation units.

The present expected-path ceiling is29,035,551 bytes:28,756,513 produced-file bytes plus279,038 compact method/observation bytes. It exceeds24MiB (25,165,824) by3,869,727 before remaining inventories, mutation witnesses and global terminal records. It is not an estimate of future observed bytes. The certified partial lower bound is13,435,712, below the ceiling; therefore the existing arithmetic does not prove actual completion impossible. A successful397-case result is not promised.

The largest single term is F07 at6,406,556 produced bytes, including the actual production package, sealed part, provider wrapper, fresh readback, original manifest and observed verification/custody reports. All four archive payload occurrences remain charged. The34 observed custody JSON versions remain produced outputs. No expected report is generated from candidate output and retrospectively called an input. The previously reviewed input lineage and all43 verifier intents remain unchanged.

## Finite reservation mechanism

The implementation remains one fixed native runner, fixed selector order and the existing finite native-only capture hooks. No generic filesystem interceptor, mount/quota configuration, new process, watchdog, alternate interpreter, production API or scientific test switch is introduced.

1. Freeze each selector's literal input hashes, exact mutation lineage, all reachable produced names, maximum occurrence/version counts, sink mechanisms, per-sink maximum bytes, stdout/stderr source, and retention/capture records. Include the expected success path and existing injected failures, plus the ordinary partial/staged-write possibilities of those same sinks. Pin the source spans that establish each bound. Mere source-wide64MiB production limits or an after-the-case scan are not a24MiB native guarantee.
2. The map has separate expected_output_upper_bytes and reservation_upper_bytes. The latter includes every retained physical copy/version, possible simultaneous old/new atomic stage, per-case inventories and all native observations. It may exceed the expected positive-path bound. An unresolved sink has reservation_certified=false; this is an explicit pre-entry stop, never a zero-byte allowance. Root and reviewers can judge the resulting potentially shorter batch's utility before authorizing it.
3. Reserve65,536 bytes inside the24MiB prefix cap at batch entry for global start/terminal/index evidence: start record at most4,096, terminal record at most16,384, and compact index at most45,056. The index uses at most397 compact rows [ordinal, inventory_SHA256, inventory_size_bytes] plus at most4,096 bytes of fixed framing; it references per-case inventories already charged to their cases and does not duplicate payload rows. Any ordinary writer is excluded from this reserve. Unused reserve is not converted into authority for another case.
4. Maintain used_actual_bytes plus active_reservation_bytes plus unused_global_reserve <=25,165,824, and the separate cumulative log budget <=8,388,608. Before the case's setup, require a certified complete reservation and enough headroom. Mark its exact selector as started durably before invoking it. Native fixed-record writers check their byte request before writing. Reserved bytes are not counted as actually produced; final receipts report both separately.
5. During the selector, the fixed known producers must stay within their proven reservations. Existing bounded production emitters retain their own semantics. The actual Bash stub paths and45 generic literal roots use their fixed finite source/command bounds and existing stdout/pipe limits. Any narrow native-only capture adapter needed for a known in-memory report or observation validates size before its own exclusive write. Such an adapter may not truncate a scientific stub result, alter a test's expected error, intercept arbitrary production writes, add a test, or claim an untested production path. If a sink cannot be protected by existing finite bounds or such a fixed capture boundary, that selector is unstartable until a separately reviewed remedy exists.
6. After test cleanups restore their mocks, inspect retained roots using captured real observation functions. No-follow inventory, exact input checks, produced-path classification and per-case byte totals must agree with the reservation. Release only its unused reservation after all mandatory observations are durably retained. Replacements and same-byte production writes remain outputs; explicit retained versions and witnesses remain charged. No case cleanup deletes roots or failure prefixes. Hash equality does not discount a second physical copy.
7. If the next case cannot be reserved, do not construct its fixture, import a new case dependency, launch its child, or emit its expected output. Write a bounded terminal record from the reserve with the distinct cause above and first unexecuted selector and counts for started/completed/passed/failed/unexecuted methods and observed subcases/processes. The full397 roster remains in the immutable map; unexecuted selectors can be represented by a fixed suffix index. This is not397 passes or full preparation validation.
8. An unexpected write path, size/domain mismatch, failed observation or violated reservation is a failed enforcement/validation result, never evidence of a successful capped batch. The original bytes remain. The reviewed pre-entry proof must make an actual cap overrun unreachable for the fixed admitted sources; the post-case scan detects violations but is not described as prevention. A map whose claimed proof cannot support that guarantee is not executable under this amendment.

## Failure preservation and time

No new time allowance is added. Original600-second wall enforcement, exact512MiB per process,8MiB logs,24MiB prefixes and32MiB combined remain. The independent10-second literal descendant lifetime remains clipped to the original batch deadline. Mandatory child cleanup remains inside the case's source-bound deadline; no child is launched without its existing time reserve.

On a stopped case, keep partial files and staged bytes. Attempt one bounded terminal/index publication using the unused reserve and original remaining time. Do not repeat a full reconciliation after the original deadline or start a fresh timer. On hard kill or failed terminal publication, surviving start/partial records and external exit status establish incomplete/unknown coverage; a missing terminal record is never inferred success. Later read-only custody may preserve those bytes under the standing evidence workflow, but cannot resume tests, regenerate missing test output, or repair the batch into success.

Log writes through the fixed Python/native capture sinks stop before the8MiB allowance is exceeded; already written log prefixes remain. A proposed command/call site with an unaccounted direct stdout/stderr writer is unstartable. The final exact command and finite sink inventory must demonstrate this; the current draft runner does not yet provide that proof.

## Current implementation limitation and next gate

The current new64 Bash helper checks its131,072-byte envelope only after subprocess completion and file creation; that assertion is not preventive enforcement. The frozen command-stub source must provide the reservation bound before entry, or that selector remains unstartable.

The preserved native runner draft presently reserves expected_output_upper_bytes and scans roots after a case. It does not yet implement the certified sink/reservation distinction, global reserve, complete version witnesses or final inventories. This amendment does not certify those missing features and does not permit running the draft. It authorizes no implementation until adopted.

After adoption, the only implementation work contemplated here is those bounded native-runner/map accounting changes and existing fixed capture-hook completion. The exact397 cases, their logical assertions, fixtures,45 generic roots plus2 existing descendants,25 Bash cases and existing mock-call tables remain. No additional runtime test campaign is authorized. Two independent static reviews must inspect the complete immutable source/fixture/command map and all sink inequalities before root may authorize one batch. Its outcome may legitimately be resource_incomplete with a preserved executed prefix; no automatic retry follows.

## Review questions

- Does the amended gate preserve the hard output caps before writes, rather than merely detecting an overrun afterward?
- Does each proposed reservation cover partial/staged versions and capture metadata without input/output relabeling or content deduplication?
- Is the potentially early incomplete prefix useful enough to justify the one bounded preparation batch, with every unexecuted case disclosed?
- Is the accounting change smaller and safer than further fixture redesign or broad write interception?
