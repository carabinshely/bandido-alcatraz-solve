"""One admitted disposable cell; preparation tests inject only literal stubs."""
from __future__ import annotations
import copy
import gc
import os
from pathlib import Path
from random import Random
import resource
import signal
import sys
from .common import (Budget, CALL_CAPS, IntegrityError, OP_CAPS, RESOURCES, SCHEDULE, TimingDelegate,
                     U_FLAGS, canonical, digest, error_record, fsync_directory, loader_pin, require, runtime_check, strict_json,
                     suppress_profile, write_failure_receipt)
from .sources import construct_fixture, isolated_imports, read_manifest, verify_files, verify_modules


def equality(first, second):
    for key in ('chosen', 'scientific', 'rng_initial', 'rng_final'):
        require(canonical(first[key]) == canonical(second[key]), 'candidate/reference mismatch: ' + key)


def check_boundary(payload, public_hash):
    science = payload['scientific']
    require(science['input_before'] == science['input_after'] == public_hash,
            'returned science observation boundary mismatch')
    require(science['rng_before'] == digest(payload['rng_initial']) == payload['initial_rng_sha256']
            and science['rng_after'] == digest(payload['rng_final']) == payload['final_rng_sha256'],
            'returned science RNG boundary mismatch')
    require(canonical(science['chosen']) == canonical(payload['chosen']), 'chosen boundary mismatch')


def run_cell(attempt, index):
    attempt = Path(attempt).resolve(); budget = Budget(attempt)
    receipt = strict_json((attempt / 'receipt.json').read_bytes())
    require(receipt['admission_verified'] is True and receipt['status'] == 'measuring'
            and receipt['current_cell'] == index and receipt['supervisor_pid'] == os.getppid(),
            'cell requires live admitted supervisor')
    require(type(index) is int and 1 <= index <= 20, 'unknown allocated cell')
    cell = SCHEDULE[index - 1]; folder = attempt / 'cells' / f'{index:02d}'
    # The supervisor creates this exclusive cell directory and no child retries.
    require(folder.is_dir() and not list(folder.iterdir()), 'cell directory occupied')
    captures = {}; guard = folder / 'active-call.json'; error = None; failure = None; whole = None
    harness = None; resource_types = (); secondary_errors = []
    phase = 'cell_source_runtime_preflight'
    restoration_checks_active = False

    def retain_failure(caught, failed_phase, *, observed_drift=False):
        nonlocal error, failure
        detail = getattr(caught, 'worker36_failure', None)
        if not isinstance(detail, dict):
            detail = error_record(caught, failed_phase, observed_drift=observed_drift,
                                  resource_types=resource_types)
        if error is None:
            error, failure = caught, detail
        elif ((failure['status'] != 'integrity_invalid' and detail['status'] == 'integrity_invalid') or
              (failure['status'] not in ('integrity_invalid', 'resource_incomplete') and
               detail['status'] == 'resource_incomplete')):
            # Integrity remains dominant; established resource exhaustion also
            # survives infrastructure/persistence uncertainty in either order.
            secondary_errors.append(failure)
            error, failure = caught, detail
        else:
            secondary_errors.append(detail)
        try:
            error.worker36_failure = failure
        except (AttributeError, TypeError):
            pass

    try:
        runtime = runtime_check(child=True)
        # A trusted parent is necessary but does not substitute for the child's
        # own actual mapped-loader identity. Bind it before historical file
        # access, imports, fixture construction or either evaluator can occur.
        admitted = strict_json((attempt / 'external-admission.json').read_bytes())
        require(type(admitted) is dict and 'loader_pin' in admitted and
                type(runtime) is dict and 'loader' in runtime,
                'cell requires an external admitted and observed loader pin')
        admitted_pin = loader_pin(admitted['loader_pin'])
        require(admitted['loader_pin'] == admitted_pin and
                loader_pin(runtime['loader']) == admitted_pin,
                'cell mapped loader differs from admitted freeze')
        # Runtime preflight must establish idle hooks/timers before this cell
        # owns any restoration obligation. An already occupied countdown may
        # naturally decrease while being rejected; that is not cell drift.
        before_hook, before_trace, setter = sys.getprofile(), sys.gettrace(), sys.setprofile
        timers = {str(k): {'handler': signal.getsignal(sig), 'timer': signal.getitimer(k)}
                  for k, sig in ((signal.ITIMER_REAL, signal.SIGALRM), (signal.ITIMER_PROF, signal.SIGPROF))}
        restoration_checks_active = True
        restored = attempt / 'restored'; manifest = read_manifest(attempt / 'source-manifest.json')
        verify_files(restored, manifest)
        modules = isolated_imports(restored, manifest)
        bounded = modules['worker35_resources']
        harness = modules['run_quota_reserve_closure_development']
        benchmark = modules['benchmark_worker35_synthetic']
        candidate = modules['bandido_alcatraz.quota_reserve_closure']
        reference = modules['bandido_alcatraz.quota_reserve_closure_reference']
        resource_types = tuple(module.ResourceExceeded for module in (bounded, candidate, reference))
        require(all(isinstance(kind, type) and issubclass(kind, Exception) for kind in resource_types),
                'frozen resource exception classes unavailable')
        wire = modules['bandido_alcatraz.worker32.evidence']
        def check_sources():
            try:
                require(gc.isenabled() and gc.get_threshold() == (700, 10, 10), 'default GC policy drift')
                verify_files(restored, manifest)
                return verify_modules(restored, manifest)
            except BaseException as caught:
                caught.worker36_failure = error_record(caught, 'evaluator_source_check',
                    observed_drift=isinstance(caught, IntegrityError), resource_types=resource_types)
                raise
        expected_modules = admitted['cell_preflight_modules']
        module_records = verify_modules(restored, manifest)
        require(type(expected_modules) is list and all(type(name) is str for name in expected_modules)
                and len(set(expected_modules)) == len(expected_modules)
                and set(module_records) == set(expected_modules),
                'cell preflight module population differs from admitted freeze')
        budget.write(folder / 'source-runtime-preflight.json', {'phase': 'source_runtime_preflight',
            'evaluator_starts': 0, 'runtime': runtime, 'modules': module_records})
        phase = 'fixture_construction'
        # Exact AST nodes from the frozen constructor; its main is never called.
        state, catalog, inputs, public = construct_fixture(cell['size'], restored)
        initial_rng = Random(11).getstate()
        before_public = wire.observation(public)
        engine_before, conservation_before = harness.state_witness(state, catalog)
        require(conservation_before['inventory_count'] == 69, 'invented identities not conserved')
        budget.write(folder / 'cell-start.json', {**cell, 'observation_sha256': digest(before_public),
                     'initial_rng_sha256': digest(initial_rng), 'rng_initial': initial_rng,
                     'public_before': before_public, 'engine_before': engine_before,
                     'conservation_before': conservation_before})
        def delegate(policy, scope):
            return TimingDelegate(policy.evaluate, scope=scope, condition=cell['condition'], budget=budget,
                folder=folder, cell=cell, observation_wire=wire.observation, move_wire=wire.move,
                captures=captures, guard_path=guard, verify_sources=check_sources)
        first = delegate(candidate.QuotaReserveClosurePolicy(**inputs), 'candidate')
        other = delegate(reference.QuotaReserveClosureReference(**inputs), 'reference')
        candidate_limits = candidate.OperationLimits(**OP_CAPS)
        reference_limits = reference.OperationLimits(**OP_CAPS)
        harness.FREEZE = {'resources': RESOURCES}
        harness.BUDGET = budget
        phase = 'cell_measurement'
        if cell['condition'] == 'P':
            # Original harness writers use ordinary mkdir; pre-create and fsync
            # their exact ancestry without changing the historical source.
            budget.mkdir(folder / 'call-results' / 'pass-2')
            budget.mkdir(folder / 'decision-traces' / 'pass-2')
            audited = harness.AuditPolicy(first, reference=other, catalog=catalog, output=folder,
                pass_number=2, seed=11, limits=RESOURCES['per_call'],
                candidate_limits=candidate_limits, reference_limits=reference_limits,
                state_provider=lambda: state)
            # AuditPolicy exclusively creates/fsyncs its original journal files.
            # Persist those directory entries without changing its source.
            fsync_directory(folder / 'call-results' / 'pass-2')
            fsync_directory(folder / 'decision-traces' / 'pass-2')
            # P retains its original full wrapper, decision and policy meters,
            # original check order, production journals and disagreement path.
            with bounded.cpu_deadline(720, 'Worker36 complete P cell'):
                whole = benchmark.measure_wrapper(audited, state, RESOURCES['whole_wrapper_operations'], 720)
            budget.write(guard, {'active': False}, replace=True)
            budget.write(folder / 'whole-wrapper-resources.json', whole)
        else:
            detached_reference = copy.deepcopy(public)  # before candidate evaluation
            rng = Random(11); reference_rng = Random(); reference_rng.setstate(rng.getstate())
            require(rng is not reference_rng, 'RNG objects must be distinct')
            with suppress_profile() as real_getprofile:
                for policy, observation, random, limits in (
                    (first, public, rng, candidate_limits),
                    (other, detached_reference, reference_rng, reference_limits)):
                    # Independent supervisor watches guard through capture;
                    # original signal protections are additional defenses.
                    with bounded.deadline(360, 'Worker36 U call'), bounded.cpu_deadline(360, 'Worker36 U call'):
                        result = policy.evaluate(observation, random, limits=limits)
                        require(real_getprofile() is None, 'U evaluator installed profile hook')
                        if len(result[1]['roots']) > CALL_CAPS['roots']:
                            raise bounded.ResourceExceeded('U returned roots exceed frozen ceiling')
                    budget.write(guard, {'active': False}, replace=True)
            require(canonical(wire.observation(detached_reference)) == canonical(before_public),
                    'reference mutated detached observation')
            budget.write(folder / 'unmeasured-accounting.json', U_FLAGS)
        first_payload = strict_json((folder / 'candidate-return.json').read_bytes())
        second_payload = strict_json((folder / 'reference-return.json').read_bytes())
        equality(first_payload, second_payload)
        for payload in (first_payload, second_payload):
            check_boundary(payload, digest(before_public))
            require(canonical(payload['rng_initial']) == canonical(initial_rng), 'fixture RNG initialization')
        engine_after, conservation_after = harness.state_witness(state, catalog)
        after_public = wire.observation(public)
        require(canonical(before_public) == canonical(after_public), 'public observation mutated')
        require(engine_before == engine_after and canonical(conservation_before) == canonical(conservation_after),
                'invented real-state/conservation witness mismatch')
        if cell['condition'] == 'P':
            metrics = list(harness.iter_jsonl(folder / 'resource-metrics.jsonl'))
            require([m['scope'] for m in metrics] == ['candidate', 'reference'], 'P decision scopes')
            for payload, metric in zip((first_payload, second_payload), metrics):
                cost = payload['physical_cost']
                require(canonical(cost) == canonical(metric['cost']) and metric['status'] == 'returned',
                        'P policy/decision physical meter mismatch')
                require(cost['legal_enumerations'] == 1 + cost['previews'] + cost['exit_geometry_checks'],
                        'P independent operation identity mismatch')
                require(cost['roots'] == len(payload['scientific']['roots']) <= 16384, 'P returned roots')
                require(all(cost[k] <= OP_CAPS[k] for k in OP_CAPS), 'P physical cap mismatch')
            require(whole['operations'] == {k: first_payload['physical_cost'][k] + second_payload['physical_cost'][k]
                                           for k in OP_CAPS}, 'P whole-wrapper meter reconciliation')
        check_sources()
        budget.write(folder / 'cell-boundaries.json', {'public_after': after_public, 'engine_after': engine_after,
                     'conservation_after': conservation_after, 'equality': True})
    except BaseException as caught:
        retain_failure(caught, phase)
    finally:
        restored_hooks = restored_timers = None
        peak_rss = None
        try:
            if harness is not None:
                harness.BUDGET = None
            if restoration_checks_active:
                restored_hooks = sys.getprofile() is before_hook and sys.gettrace() is before_trace and sys.setprofile is setter
                restored_timers = all(signal.getsignal(sig) == timers[str(k)]['handler'] and
                                      signal.getitimer(k) == timers[str(k)]['timer']
                                      for k, sig in ((signal.ITIMER_REAL, signal.SIGALRM), (signal.ITIMER_PROF, signal.SIGPROF)))
                if not restored_hooks or not restored_timers:
                    retain_failure(IntegrityError('hook/timer restoration failed'), 'cell_restoration', observed_drift=True)
        except BaseException as restoration_error:
            retain_failure(restoration_error, 'cell_restoration_observation')
        try:
            peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        except BaseException as accounting_error:
            retain_failure(accounting_error, 'cell_terminal_accounting')
        result = {**cell, 'schema': 'worker36-cell-receipt-v1',
                  'status': 'complete' if error is None else failure['status'], 'classification': None,
                  'actual_starts': sum(v['method_entered'] is True for v in captures.values()),
                  'actual_starts_upper_bound': sum(v['invocation_attempted'] for v in captures.values()),
                  'actual_starts_semantics': 'observed method-entry lower bound; pre-call markers do not prove entry',
                  'pre_call_markers': sum(v['start_marker_durable'] for v in captures.values()),
                  'invocation_attempts': sum(v['invocation_attempted'] for v in captures.values()),
                  'actual_returns': sum(v['returned'] for v in captures.values()),
                  'confirmed_captures': sum(v['durable_capture_confirmed'] for v in captures.values()),
                  'calls': captures, 'hook_restored': restored_hooks, 'timer_restored': restored_timers,
                  'peak_rss_kib': peak_rss,
                  'peak_rss_description': 'fresh child process high-water RSS, not evaluator live memory',
                  'failure': failure, 'secondary_errors': secondary_errors,
                  'error_type': failure['error_type'] if failure else None,
                  'error': failure['error'] if failure else None,
                  'phase': failure['phase'] if failure else 'cell_complete'}
        try:
            budget.write(folder / 'cell-receipt.json', result)
        except BaseException as receipt_error:
            retain_failure(receipt_error, 'cell_receipt_persistence')
            result.update(status=failure['status'], failure=failure, secondary_errors=secondary_errors,
                          error_type=failure['error_type'], error=failure['error'], phase=failure['phase'],
                          receipt_write_confirmed=False)
            try:
                write_failure_receipt(attempt, result, name=f'failure-receipt-cell-{index:02d}.json')
            except BaseException as sidecar_error:
                retain_failure(sidecar_error, 'cell_failure_sidecar_persistence')
    if error is not None:
        raise error
    return result
