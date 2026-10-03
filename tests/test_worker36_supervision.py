"""PROPOSED ONLY: finite S01-S16 helper tests; do not infer execution approval.

Imports only the standalone supervision helper and the Python standard library.
Every spawned program below is an invented stub, never an evaluator or fixture.
"""
from __future__ import annotations

import importlib.util
from contextlib import contextmanager
import json
import os
from pathlib import Path
import resource
import signal
import sys
import tempfile
import time
import unittest
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "worker36" / "supervision.py"
SPEC = importlib.util.spec_from_file_location("worker36_supervision_standalone", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
supervision = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = supervision
SPEC.loader.exec_module(supervision)

STUB_PROCESS_STARTS = 0
STUB_SUPERVISOR_INVOCATIONS = 0

STUB_PRELUDE = '''
import json, os, resource, signal, sys, time
from pathlib import Path
state_path = Path(sys.argv[1])
def mark(value):
    temporary = state_path.with_suffix(".pending")
    with temporary.open("w") as stream:
        json.dump(value, stream, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, state_path)
def activate(scope="candidate"):
    mark({"active": True, "scope": scope, "cpu_started": time.process_time(), "wall_started": time.monotonic()})
'''


@unittest.skipUnless(sys.platform == "linux", "Linux-only independent supervision")
class SupervisionStubTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="worker36-supervision-stub-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.counter = 0

    def run_stub(self, code, *, phase=None, before=None, **overrides):
        global STUB_PROCESS_STARTS, STUB_SUPERVISOR_INVOCATIONS
        STUB_SUPERVISOR_INVOCATIONS += 1
        self.counter += 1
        cell = self.root / f"stub-{self.counter}"
        cell.mkdir()
        script = cell / "stub.py"
        script.write_text(STUB_PRELUDE + "\n" + code, encoding="utf-8")
        state = cell / "call-state.json"
        log = cell / "child.log"
        if before:
            before(cell, state, log)
        env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
        env.update(PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1")
        arguments = dict(command=[sys.executable, "-B", "-s", str(script), str(state)],
                         env=env, cwd=cell, output_log=log, call_state=state,
                         phase=phase or supervision.PhaseBudget(wall_seconds=10, cpu_seconds=10),
                         wall_seconds=3, cpu_seconds=2, call_wall_seconds=2, call_cpu_seconds=1,
                         address_space_bytes=512 * 1024 * 1024)
        arguments.update(overrides)
        result = supervision.run_child(**arguments)
        STUB_PROCESS_STARTS += int(result["spawned"])
        return result, cell, log

    def assert_clean(self, result):
        self.assertTrue(result["cleanup"]["complete"], result)
        self.assertEqual(result["cleanup"]["remaining_pids"], [], result)
        self.assertFalse(result["scientific_returns_inferred"])
        if result["pid"] is not None:
            self.assertFalse(Path(f"/proc/{result['pid']}").exists(), result)

    def assert_resource(self, result, reason):
        self.assertEqual(result["status"], "resource_incomplete", result)
        self.assertEqual(result["reason"], reason, result)
        self.assert_clean(result)

    def test_S01_zero_exit_records_process_only(self):
        result, _, log = self.run_stub("print('invented stdout', flush=True)\nprint('invented stderr', file=sys.stderr, flush=True)")
        self.assertEqual(result["status"], "completed", result)
        self.assertEqual(result["exit_code"], 0)
        self.assertIsNone(result["signal"])
        self.assertIn(b"invented stdout", log.read_bytes())
        self.assertIn(b"invented stderr", log.read_bytes())
        self.assertTrue(result["output_durable"])
        self.assertGreater(result["child_cpu_seconds"], 0)
        self.assertGreater(result["child_high_water_rss_kib"], 0)
        self.assert_clean(result)

    def test_S02_nonzero_and_signal_are_explicit(self):
        cases = [("print('prefix', flush=True)\nsys.exit(7)", 7, None),
                 ("print('prefix', flush=True)\nos.kill(os.getpid(), signal.SIGKILL)", None, signal.SIGKILL)]
        for code, exit_code, sig in cases:
            with self.subTest(exit_code=exit_code, signal=sig):
                result, _, log = self.run_stub(code)
                self.assertEqual(result["status"], "execution_incomplete", result)
                self.assertEqual(result["exit_code"], exit_code)
                self.assertEqual(result["signal"], sig)
                self.assertEqual(log.read_bytes(), b"prefix\n")
                self.assert_clean(result)

    def test_S03_whole_cell_wall_works_without_state(self):
        result, _, _ = self.run_stub("time.sleep(30)", wall_seconds=0.2)
        self.assert_resource(result, "cell_wall_limit")
        self.assertLess(result["wall_seconds"], 2)

    def test_S04_active_hang_with_profiles_suppressed(self):
        result, _, _ = self.run_stub("activate()\nsys.setprofile = lambda hook: None\ntime.sleep(30)", call_wall_seconds=0.2)
        self.assert_resource(result, "call_wall_limit")
        self.assertEqual(result["active_call_at_stop"]["scope"], "candidate")

    def test_S05_live_cpu_not_just_reaped_children(self):
        result, _, _ = self.run_stub("activate()\nsys.setprofile = lambda hook: None\nwhile True: pass", call_cpu_seconds=0.15)
        self.assert_resource(result, "call_cpu_limit")
        self.assertGreaterEqual(result["child_cpu_seconds"], 0.15)
        self.assertGreater(result["phase"]["reaped_child_cpu_seconds"], 0)

    def test_S06_whole_cell_cpu_without_state(self):
        result, _, _ = self.run_stub("while True: pass", cpu_seconds=0.15)
        self.assert_resource(result, "cell_cpu_limit")

    def test_S07_phase_wall_blocks_or_terminates(self):
        phase = supervision.PhaseBudget(wall_seconds=1)
        phase.wall_started -= 2
        result, _, _ = self.run_stub("raise AssertionError('must not spawn')", phase=phase)
        self.assertEqual(result["status"], "execution_blocked", result)
        self.assertFalse(result["spawned"])
        self.assertIn("phase_wall_limit_before_spawn", " ".join(result["errors"]))
        phase = supervision.PhaseBudget(wall_seconds=0.2)
        result, _, _ = self.run_stub("time.sleep(30)", phase=phase)
        self.assert_resource(result, "phase_wall_limit")

    def test_S08_phase_parent_reaped_live_terms(self):
        with mock.patch.object(supervision, "_usage", side_effect=[10.0, 20.0, 11.0, 22.0]):
            phase = supervision.PhaseBudget()
            snapshot = phase.snapshot(3.0)
        self.assertEqual(snapshot["parent_cpu_seconds"], 1.0)
        self.assertEqual(snapshot["reaped_child_cpu_seconds"], 2.0)
        self.assertEqual(snapshot["live_child_cpu_seconds"], 3.0)
        self.assertEqual(snapshot["cpu_seconds"], 6.0)
        phase = supervision.PhaseBudget(cpu_seconds=0.01)
        stop = time.process_time() + 0.02
        while time.process_time() < stop:
            pass
        result, _, _ = self.run_stub("pass", phase=phase)
        self.assertFalse(result["spawned"], result)
        phase = supervision.PhaseBudget(cpu_seconds=0.5)
        result, _, _ = self.run_stub("stop = time.process_time() + 0.08\nwhile time.process_time() < stop: pass", phase=phase)
        self.assertEqual(result["status"], "completed", result)
        prior = result["phase"]["reaped_child_cpu_seconds"]
        self.assertGreater(prior, 0.05)
        result, _, _ = self.run_stub("while True: pass", phase=phase)
        self.assert_resource(result, "phase_cpu_limit")
        self.assertGreater(result["phase"]["reaped_child_cpu_seconds"], prior)

    def test_S09_term_ignoring_escaped_descendant_is_killed(self):
        code = '''
pid = os.fork()
if pid == 0:
    os.setsid()
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    Path("descendant.pid").write_text(str(os.getpid()))
    while True: time.sleep(1)
else:
    while True: time.sleep(1)
'''
        result, cell, _ = self.run_stub(code, wall_seconds=0.3)
        self.assert_resource(result, "cell_wall_limit")
        self.assertTrue(result["cleanup"]["sigkill_used"], result)
        pid = int((cell / "descendant.pid").read_text())
        self.assertFalse(Path(f"/proc/{pid}").exists())

    def test_S10_child_exit_leaving_descendant_is_incomplete(self):
        code = '''
pid = os.fork()
if pid == 0:
    Path("descendant.pid").write_text(str(os.getpid()))
    while True: time.sleep(1)
else:
    while not Path("descendant.pid").exists(): time.sleep(0.005)
    os._exit(0)
'''
        result, cell, _ = self.run_stub(code)
        self.assertEqual(result["status"], "execution_incomplete", result)
        self.assertEqual(result["reason"], "descendants_survived_child", result)
        self.assertEqual(result["exit_code"], 0)
        self.assert_clean(result)
        self.assertFalse(Path(f"/proc/{int((cell / 'descendant.pid').read_text())}").exists())

    def test_S11_exact_address_space_and_inherited_limits(self):
        result, _, log = self.run_stub("print(json.dumps({'as': resource.getrlimit(resource.RLIMIT_AS), 'pid': os.getpid(), 'pgid': os.getpgrp(), 'sid': os.getsid(0)}))")
        self.assertEqual(result["status"], "completed", result)
        data = json.loads(log.read_text())
        self.assertEqual(data["as"], [512 * 1024 * 1024] * 2)
        self.assertEqual(data["pid"], data["pgid"])
        self.assertEqual(data["pid"], data["sid"])
        real_getrlimit = resource.getrlimit
        def altered(which):
            if which == resource.RLIMIT_AS:
                return (64 * 1024 * 1024, 64 * 1024 * 1024)
            return real_getrlimit(which)
        with mock.patch.object(supervision.resource, "getrlimit", side_effect=altered):
            result, _, _ = self.run_stub("pass")
        self.assertFalse(result["spawned"], result)
        self.assertIn("unexpected inherited RLIMIT_AS", " ".join(result["errors"]))
        def frozen_parent(which):
            if which == resource.RLIMIT_AS:
                return (512 * 1024 * 1024, 512 * 1024 * 1024)
            return real_getrlimit(which)
        with mock.patch.object(supervision.resource, "getrlimit", side_effect=frozen_parent):
            self.assertEqual(supervision.inherited_limits_snapshot()["RLIMIT_AS"], [512 * 1024 * 1024] * 2)
        baseline = supervision.inherited_limits_snapshot()
        baseline["RLIMIT_NOFILE"][0] += 1
        result, _, _ = self.run_stub("pass", expected_inherited_limits=baseline)
        self.assertFalse(result["spawned"], result)
        self.assertIn("exact admission baseline", " ".join(result["errors"]))

    def test_S12_proc_or_subreaper_unavailable_blocks_spawn(self):
        for name in ("_scan_processes", "_subreaper"):
            with self.subTest(helper=name):
                with mock.patch.object(supervision, name, side_effect=supervision.SupervisionError("injected prerequisite failure")):
                    result, _, _ = self.run_stub("pass")
                self.assertEqual(result["status"], "execution_blocked", result)
                self.assertFalse(result["spawned"])

    def test_S13_output_overflow_preserves_bounded_prefix(self):
        result, _, log = self.run_stub("os.write(1, b'x' * 8192)\ntime.sleep(30)", output_log_limit_bytes=257)
        self.assert_resource(result, "output_log_limit")
        self.assertEqual(log.read_bytes(), b"x" * 257)
        self.assertEqual(result["output_bytes_preserved"], 257)
        self.assertTrue(result["output_durable"])
        self.assertTrue(result["output_overflow"])
        def denied(path, incoming):
            raise supervision.OutputBudgetExceeded("invented shared raw cap")
        result, _, log = self.run_stub("print('bytes', flush=True)\ntime.sleep(30)", output_budget_check=denied)
        self.assert_resource(result, "shared_output_budget_limit")
        self.assertEqual(log.read_bytes(), b"")
        held = False
        entries = []
        @contextmanager
        def guard(path, incoming):
            nonlocal held
            self.assertFalse(held)
            held = True
            entries.append((path, incoming))
            try:
                yield
            finally:
                held = False
        real_write = supervision.os.write
        def guarded_write(fd, data):
            self.assertTrue(held, "shared-budget guard must surround the actual write")
            return real_write(fd, data)
        with mock.patch.object(supervision.os, "write", side_effect=guarded_write):
            result, _, log = self.run_stub("print('guarded prefix', flush=True)", output_budget_check=guard)
        self.assertEqual(result["status"], "completed", result)
        self.assertTrue(entries)
        self.assertFalse(held)
        self.assertEqual(log.read_bytes(), b"guarded prefix\n")

    def test_S14_malformed_state_variants_fail_closed(self):
        variants = [
            "state_path.write_text('{')",
            "state_path.write_text('x' * 17000)",
            "state_path.write_text('{\"active\": true, \"scope\": \"candidate\", \"wall_started\": NaN, \"cpu_started\": 0}')",
            "mark({'active': True, 'scope': 'candidate', 'wall_started': time.monotonic() + 100, 'cpu_started': 0})",
            "mark({'active': True, 'scope': 'candidate', 'wall_started': time.monotonic(), 'cpu_started': 1000000})",
            "Path('target').write_text('{}'); state_path.symlink_to('target')",
            "activate(); time.sleep(0.1); activate()",
        ]
        for index, code in enumerate(variants):
            with self.subTest(variant=index):
                result, _, _ = self.run_stub(code + "\ntime.sleep(30)")
                self.assertEqual(result["status"], "integrity_invalid", result)
                self.assertEqual(result["primary_outcome"]["exception_type"], "CallStateIntegrityError", result)
                self.assertTrue(result["errors"], result)
                self.assert_clean(result)

    def test_S15_valid_transition_and_admission_rejections(self):
        result, _, _ = self.run_stub("activate()\ntime.sleep(0.06)\nmark({'active': False})\ntime.sleep(0.06)")
        self.assertEqual(result["status"], "completed", result)
        self.assertIsNone(result["active_call_at_stop"])
        for filename in ("state", "log"):
            def existing(cell, state, log):
                (state if filename == "state" else log).write_text("preserve")
            result, cell, log = self.run_stub("pass", before=existing)
            self.assertFalse(result["spawned"], result)
            self.assertEqual((cell / "call-state.json" if filename == "state" else log).read_text(), "preserve")
        for arguments in ({"wall_seconds": float("nan")}, {"call_cpu_seconds": 0},
                          {"address_space_bytes": 1024}, {"output_log_limit_bytes": 0}):
            result, _, _ = self.run_stub("pass", **arguments)
            self.assertFalse(result["spawned"], result)
        real_scan = supervision._scan_processes
        def with_existing_child(ticks):
            processes = real_scan(ticks)
            processes[999999999] = supervision._Process(999999999, os.getpid(), 999999999, 999999999, "S", 1, 0, 0)
            return processes
        with mock.patch.object(supervision, "_scan_processes", side_effect=with_existing_child):
            result, _, _ = self.run_stub("pass")
        self.assertFalse(result["spawned"], result)

    def test_S16_injected_io_spawn_observation_and_cleanup_failures(self):
        with mock.patch.object(supervision.subprocess, "Popen", side_effect=OSError("injected spawn failure")):
            result, _, _ = self.run_stub("pass")
        self.assertEqual(result["status"], "execution_blocked", result)
        self.assertFalse(result["spawned"])
        for name in ("_call_state",):
            with mock.patch.object(supervision, name, side_effect=OSError("injected state read failure")):
                result, _, _ = self.run_stub("time.sleep(30)")
            self.assertEqual(result["status"], "execution_incomplete", result)
            self.assert_clean(result)
        with mock.patch.object(supervision.os, "write", side_effect=OSError("injected log write failure")):
            result, _, _ = self.run_stub("print('prefix', flush=True)")
        self.assertEqual(result["status"], "execution_incomplete", result)
        self.assert_clean(result)
        real_scan = supervision._scan_processes
        scans = 0
        def transient_proc_failure(ticks):
            nonlocal scans
            scans += 1
            if scans == 2:
                raise OSError("injected running proc failure")
            return real_scan(ticks)
        with mock.patch.object(supervision, "_scan_processes", side_effect=transient_proc_failure):
            result, _, _ = self.run_stub("time.sleep(30)")
        self.assertEqual(result["status"], "execution_incomplete", result)
        self.assert_clean(result)
        real_signal = supervision._signal_owned
        calls = 0
        def transient_signal_failure(*args):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError("injected cleanup signal failure")
            return real_signal(*args)
        with mock.patch.object(supervision, "_signal_owned", side_effect=transient_signal_failure):
            result, _, _ = self.run_stub("time.sleep(30)", wall_seconds=0.1)
        # P2-01: a later cleanup problem cannot erase the observed wall cap.
        self.assertEqual(result["status"], "resource_incomplete", result)
        self.assertEqual(result["reason"], "cell_wall_limit", result)
        self.assertEqual(result["primary_outcome"], {"status": "resource_incomplete", "reason": "cell_wall_limit"})
        self.assertTrue(any(failure["phase"] == "cleanup" and
                            failure["reason"] == "process_cleanup_unconfirmed"
                            for failure in result["secondary_failures"]), result)
        self.assertFalse(result["cleanup"]["complete"])
        self.assertTrue(result["cleanup"]["errors"])
        self.assertEqual(result["cleanup"]["remaining_pids"], [])
        self.assertFalse(Path(f"/proc/{result['pid']}").exists())


    def _subreaper_restoration_fault(self):
        real_subreaper = supervision._subreaper
        setter_calls = 0
        def injected(get, value=0):
            nonlocal setter_calls
            if not get:
                setter_calls += 1
            observed = real_subreaper(get, value)
            if not get and setter_calls == 2:
                # Restore the real setting first; inject only the reported fault.
                raise supervision.SupervisionError("invented restoration failure after actual restore")
            return observed
        return injected

    def test_P2_02_resource_survives_subreaper_restoration_failure(self):
        with mock.patch.object(supervision, "_subreaper", side_effect=self._subreaper_restoration_fault()):
            result, _, _ = self.run_stub("time.sleep(30)", wall_seconds=0.2)
        self.assert_resource(result, "cell_wall_limit")
        self.assertEqual(result["primary_outcome"], {"status": "resource_incomplete", "reason": "cell_wall_limit"})
        failures = result["secondary_failures"]
        self.assertEqual(len(failures), 1, result)
        self.assertEqual(failures[0]["phase"], "subreaper_restoration")
        self.assertEqual(failures[0]["status"], "execution_incomplete")
        self.assertEqual(failures[0]["reason"], "subreaper_restoration_failed")
        self.assertEqual(failures[0]["exception_type"], "SupervisionError")
        self.assertIsInstance(failures[0]["message"], str)

    def test_P2_03_resource_survives_deferred_log_failure(self):
        with mock.patch.object(supervision.os, "write", side_effect=OSError("invented deferred log failure")):
            result, _, log = self.run_stub("print('retained in memory', flush=True)\ntime.sleep(30)", wall_seconds=0.2)
        self.assert_resource(result, "cell_wall_limit")
        self.assertEqual(result["primary_outcome"], {"status": "resource_incomplete", "reason": "cell_wall_limit"})
        self.assertGreater(result["output_bytes_observed"], 0, result)
        self.assertEqual(log.read_bytes(), b"")
        self.assertFalse(result["output_durable"])
        self.assertTrue(result["output_prefix_gap"])
        self.assertIsNotNone(result["returncode"])
        self.assertEqual(result["signal"], -result["returncode"])
        self.assertIsNone(result["exit_code"])
        self.assertTrue(any(failure["phase"] == "log_persistence" and
                            failure["reason"] == "output_log_preservation_failed" and
                            failure["status"] == "execution_incomplete"
                            for failure in result["secondary_failures"]), result)

    def test_P2_04_zero_exit_with_restoration_failure_is_not_completed(self):
        with mock.patch.object(supervision, "_subreaper", side_effect=self._subreaper_restoration_fault()):
            result, _, _ = self.run_stub("pass")
        self.assertEqual(result["primary_outcome"], {"status": "completed", "reason": "child_exit_zero"})
        self.assertEqual(result["status"], "execution_incomplete", result)
        self.assertEqual(result["reason"], "subreaper_restoration_failed")
        self.assertEqual(result["exit_code"], 0)
        self.assertIsNone(result["signal"])
        self.assertEqual(result["secondary_failures"][0]["reason"], "subreaper_restoration_failed")
        self.assert_clean(result)

    def test_P2_05_final_output_budget_keeps_primary_zero_exit(self):
        cleaned = False
        real_cleanup = supervision._cleanup
        def cleanup_then_flag(*args):
            nonlocal cleaned
            evidence = real_cleanup(*args)
            cleaned = True
            return evidence
        def budget_check(path, incoming):
            if cleaned and incoming > 0:
                raise supervision.OutputBudgetExceeded("invented final raw allowance exhausted")
        with mock.patch.object(supervision, "_cleanup", side_effect=cleanup_then_flag):
            result, _, log = self.run_stub("print('invented raw prefix', flush=True)", output_budget_check=budget_check)
        self.assert_resource(result, "shared_output_budget_limit")
        self.assertEqual(result["primary_outcome"], {"status": "completed", "reason": "child_exit_zero"})
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(log.read_bytes(), b"")
        self.assertGreater(result["output_bytes_observed"], 0)
        self.assertEqual(result["output_bytes_preserved"], 0)
        self.assertTrue(result["output_prefix_gap"])
        self.assertTrue(result["output_durable"])
        self.assertTrue(any(failure["phase"] == "log_persistence" and
                            failure["status"] == "resource_incomplete" and
                            failure["reason"] == "shared_output_budget_limit"
                            for failure in result["secondary_failures"]), result)

    def test_P2_06_secondary_failure_precedence_is_lossless(self):
        cases = [
            ("integrity_invalid", ["resource_incomplete", "execution_incomplete"], "integrity_invalid", "original"),
            ("resource_incomplete", ["execution_incomplete", "resource_incomplete"], "resource_incomplete", "original"),
            ("execution_incomplete", ["execution_incomplete", "resource_incomplete"], "resource_incomplete", "later-1"),
            ("completed", ["execution_incomplete"], "execution_incomplete", "later-0"),
            ("completed", ["resource_incomplete", "integrity_invalid", "execution_incomplete"], "integrity_invalid", "later-1"),
        ]
        for initial, following, expected_status, expected_reason in cases:
            with self.subTest(primary=initial, secondary=following):
                primary = {"status": initial, "reason": "original"}
                result = {**primary, "primary_outcome": dict(primary), "secondary_failures": []}
                for index, status in enumerate(following):
                    supervision._record_secondary_failure(
                        result, phase="invented-preservation-phase", status=status,
                        reason=f"later-{index}", error=OSError("invented secondary failure"))
                self.assertEqual(result["primary_outcome"], primary)
                self.assertEqual(result["status"], expected_status)
                self.assertEqual(result["reason"], expected_reason)
                self.assertEqual(len(result["secondary_failures"]), len(following))
                for failure in result["secondary_failures"]:
                    self.assertEqual(set(failure), {"phase", "status", "reason", "exception_type", "message"})
                    self.assertTrue(all(isinstance(value, str) for value in failure.values()))


    def test_F4_01_postspawn_memory_is_resource(self):
        with mock.patch.object(supervision, "_call_state", side_effect=MemoryError("invented postspawn allocation failure")):
            result, _, _ = self.run_stub("time.sleep(30)")
        self.assertEqual(result["status"], "resource_incomplete", result)
        self.assertEqual(result["primary_outcome"]["status"], "resource_incomplete")
        self.assertEqual(result["primary_outcome"]["exception_type"], "MemoryError")
        self.assert_clean(result)

    def test_F4_02_secondary_memory_phases_preserve_exit(self):
        for stage in ("cleanup", "log", "restoration", "final_accounting"):
            with self.subTest(stage=stage):
                phase = supervision.PhaseBudget(wall_seconds=10, cpu_seconds=10)
                real_cleanup = supervision._cleanup
                real_write = supervision.os.write
                real_subreaper = supervision._subreaper
                real_snapshot = phase.snapshot
                cleaned = triggered = False
                setters = 0
                def cleanup(*args):
                    nonlocal cleaned, triggered
                    result = real_cleanup(*args)
                    cleaned = True
                    if stage == "cleanup" and not triggered:
                        triggered = True
                        raise MemoryError("invented cleanup allocation failure")
                    return result
                def write(fd, data):
                    nonlocal triggered
                    if stage == "log" and not triggered:
                        triggered = True
                        raise MemoryError("invented log allocation failure")
                    return real_write(fd, data)
                def subreaper(get, value=0):
                    nonlocal setters, triggered
                    outcome = real_subreaper(get, value)
                    if not get:
                        setters += 1
                    if stage == "restoration" and not get and setters == 2:
                        triggered = True
                        raise MemoryError("invented error after actual restoration")
                    return outcome
                def snapshot(live_child_cpu_seconds=0.0):
                    nonlocal triggered
                    if stage == "final_accounting" and cleaned and not triggered:
                        triggered = True
                        raise MemoryError("invented final accounting allocation failure")
                    return real_snapshot(live_child_cpu_seconds)
                with mock.patch.object(supervision, "_cleanup", side_effect=cleanup), \
                     mock.patch.object(supervision.os, "write", side_effect=write), \
                     mock.patch.object(supervision, "_subreaper", side_effect=subreaper), \
                     mock.patch.object(phase, "snapshot", side_effect=snapshot):
                    result, _, _ = self.run_stub("print('invented prefix', flush=True)", phase=phase)
                self.assertTrue(triggered, stage)
                self.assertEqual(result["status"], "resource_incomplete", result)
                self.assertEqual(result["primary_outcome"], {"status": "completed", "reason": "child_exit_zero"})
                self.assertEqual(result["exit_code"], 0)
                self.assertEqual(result["returncode"], 0)
                self.assertIsNone(result["signal"])
                self.assertTrue(any(failure.get("exception_type") == "MemoryError" and
                                    failure["status"] == "resource_incomplete"
                                    for failure in result["secondary_failures"]), result)
                self.assertEqual(setters, 2, "real subreaper restoration must still be attempted")
                self.assertFalse(phase._running)
                if stage == "final_accounting":
                    self.assertFalse(result["phase_accounting_complete"])
                self.assert_clean(result)

    def test_F4_03_exit65_survives_resource_accounting_faults(self):
        class ResourceExceeded(RuntimeError):
            pass
        for stage in ("postpoll_scan", "child_usage", "phase_snapshot"):
            with self.subTest(stage=stage):
                phase = supervision.PhaseBudget(wall_seconds=10, cpu_seconds=10)
                real_poll, real_scan = supervision._poll, supervision._scan_processes
                real_cleanup, real_usage = supervision._cleanup, supervision._usage
                real_snapshot = phase.snapshot
                prior_subreaper = supervision._subreaper(True)
                observed = cleaned = triggered = False
                def poll(child):
                    nonlocal observed
                    real_poll(child)
                    observed = observed or child.returncode == 65
                def scan(ticks):
                    nonlocal triggered
                    if stage == "postpoll_scan" and observed and not triggered:
                        triggered = True
                        raise ResourceExceeded("invented resource fault after observed exit65")
                    return real_scan(ticks)
                def cleanup(*args):
                    nonlocal cleaned
                    evidence = real_cleanup(*args)
                    cleaned = True
                    return evidence
                def usage(who):
                    nonlocal triggered
                    if stage == "child_usage" and cleaned and who == resource.RUSAGE_CHILDREN and not triggered:
                        triggered = True
                        raise ResourceExceeded("invented final child accounting fault")
                    return real_usage(who)
                def snapshot(live_child_cpu_seconds=0.0):
                    nonlocal triggered
                    if stage == "phase_snapshot" and cleaned and not triggered:
                        triggered = True
                        raise ResourceExceeded("invented final phase accounting fault")
                    return real_snapshot(live_child_cpu_seconds)
                with mock.patch.object(supervision, "_poll", side_effect=poll), \
                     mock.patch.object(supervision, "_scan_processes", side_effect=scan), \
                     mock.patch.object(supervision, "_cleanup", side_effect=cleanup), \
                     mock.patch.object(supervision, "_usage", side_effect=usage), \
                     mock.patch.object(phase, "snapshot", side_effect=snapshot):
                    result, _, _ = self.run_stub("sys.exit(65)", phase=phase,
                                                 output_budget_exceptions=(ResourceExceeded,))
                self.assertTrue(triggered, stage)
                self.assertEqual(result["returncode"], 65)
                self.assertEqual(result["exit_code"], 65)
                self.assertIsNone(result["signal"])
                self.assertEqual(result["primary_outcome"], {"status": "execution_incomplete", "reason": "child_nonzero_exit"})
                self.assertEqual(result["status"], "resource_incomplete", result)
                self.assertTrue(any(failure.get("exception_type") == "ResourceExceeded" and
                                    failure["status"] == "resource_incomplete"
                                    for failure in result["secondary_failures"]), result)
                self.assertFalse(phase._running)
                self.assertEqual(supervision._subreaper(True), prior_subreaper)
                self.assert_clean(result)

    def test_F4_04_committed_marker_integrity_matrix(self):
        now = time.monotonic()
        valid = {"active": True, "scope": "candidate", "wall_started": now, "cpu_started": 0.1}
        raw_variants = [
            b"{",
            b'{"active":false,"active":true}',
            b"[]",
            b'{"active":1}',
            json.dumps({"active": True, "wall_started": now, "cpu_started": 0.1}).encode(),
            b'{"active":true,"scope":"candidate","wall_started":NaN,"cpu_started":0}',
            json.dumps({**valid, "wall_started": now - 10}).encode(),
            json.dumps({**valid, "wall_started": now + 100}).encode(),
            json.dumps({**valid, "cpu_started": -1}).encode(),
            json.dumps({**valid, "unexpected": True}).encode(),
        ]
        self.assertEqual(len(raw_variants), 10)
        for index, raw in enumerate(raw_variants):
            with self.subTest(variant=index):
                path = self.root / f"committed-marker-{index}.json"
                path.write_bytes(raw)
                with self.assertRaises(supervision.CallStateIntegrityError):
                    supervision._call_state(path, now, 1.0, now - 1, 100)

    def test_F4_05_unavailable_observations_are_not_corruption(self):
        with mock.patch.object(supervision, "_call_state", side_effect=PermissionError("invented unreadable marker")):
            result, _, _ = self.run_stub("time.sleep(30)")
        self.assertEqual(result["status"], "execution_incomplete", result)
        self.assertEqual(result["primary_outcome"]["exception_type"], "PermissionError")
        self.assert_clean(result)
        real_scan = supervision._scan_processes
        scans = 0
        def unavailable(ticks):
            nonlocal scans
            scans += 1
            if scans == 2:
                raise supervision.SupervisionError("invented process observation unavailable")
            return real_scan(ticks)
        with mock.patch.object(supervision, "_scan_processes", side_effect=unavailable):
            result, _, _ = self.run_stub("time.sleep(30)")
        self.assertEqual(result["status"], "execution_incomplete", result)
        self.assertEqual(result["primary_outcome"]["exception_type"], "SupervisionError")
        self.assert_clean(result)

    def test_F4_06_marker_corruption_dominates_cleanup_memory(self):
        real_cleanup = supervision._cleanup
        triggered = False
        def cleanup(*args):
            nonlocal triggered
            result = real_cleanup(*args)
            if not triggered:
                triggered = True
                raise MemoryError("invented memory failure after real cleanup")
            return result
        with mock.patch.object(supervision, "_cleanup", side_effect=cleanup):
            result, _, _ = self.run_stub("mark({'active': 'invalid'})\ntime.sleep(30)")
        self.assertTrue(triggered)
        self.assertEqual(result["status"], "integrity_invalid", result)
        self.assertEqual(result["primary_outcome"]["status"], "integrity_invalid")
        self.assertEqual(result["primary_outcome"]["exception_type"], "CallStateIntegrityError")
        self.assertTrue(any(failure.get("exception_type") == "MemoryError" and
                            failure["status"] == "resource_incomplete"
                            for failure in result["secondary_failures"]), result)
        self.assertIsNotNone(result["returncode"])
        self.assert_clean(result)


    def test_F5_01_oversized_integer_clocks_are_integrity_failures(self):
        now = time.monotonic()
        valid = {"active": True, "scope": "candidate", "wall_started": now, "cpu_started": 0.1}
        huge = 10 ** 400  # Exactly 401 decimal digits; far below marker byte cap.
        for name in ("wall_started", "cpu_started"):
            for sign in (1, -1):
                with self.subTest(clock=name, sign=sign):
                    path = self.root / f"oversized-clock-{name}-{sign}.json"
                    raw = json.dumps({**valid, name: sign * huge}).encode()
                    self.assertLess(len(raw), supervision.CALL_STATE_LIMIT)
                    path.write_bytes(raw)
                    with self.assertRaises(supervision.CallStateIntegrityError) as caught:
                        supervision._call_state(path, now, 1.0, now - 1, 100)
                    self.assertIsInstance(caught.exception.__cause__, OverflowError)
                    self.assertEqual(supervision._exception_status(caught.exception), "integrity_invalid")

    def test_F5_02_constructed_recursion_errors_are_resource_failures(self):
        for before_spawn in (False, True):
            with self.subTest(before_spawn=before_spawn):
                error = RecursionError("invented typed error; no recursive execution")
                self.assertEqual(supervision._exception_status(error, before_spawn=before_spawn),
                                 "resource_incomplete")
        for initial, expected in (("completed", "resource_incomplete"),
                                  ("integrity_invalid", "integrity_invalid")):
            with self.subTest(primary=initial):
                primary = {"status": initial, "reason": "original"}
                result = {**primary, "primary_outcome": dict(primary), "secondary_failures": []}
                supervision._record_secondary_failure(
                    result, phase="invented-final-accounting", status="execution_incomplete",
                    reason="invented-recursion-failure", error=RecursionError("constructed only"))
                self.assertEqual(result["status"], expected)
                self.assertEqual(result["primary_outcome"], primary)
                self.assertEqual(result["secondary_failures"][0]["status"], "resource_incomplete")
                self.assertEqual(result["secondary_failures"][0]["exception_type"], "RecursionError")
                if initial == "integrity_invalid":
                    self.assertEqual(result["reason"], "original")


    def test_S30_timeout_handler_diagnostic_is_preserved(self):
        code = """
def on_term(signum, frame):
    os.write(1, b'SIGTERM diagnostic\\n')
    os._exit(0)
signal.signal(signal.SIGTERM, on_term)
os.write(1, b'start\\n')
while True:
    time.sleep(1)
"""
        result, _, log = self.run_stub(code, wall_seconds=0.3)
        expected = b"start\nSIGTERM diagnostic\n"
        self.assert_resource(result, "cell_wall_limit")
        self.assertEqual(result["primary_outcome"], {"status": "resource_incomplete", "reason": "cell_wall_limit"})
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(log.read_bytes(), expected)
        self.assertEqual(result["output_bytes_observed"], len(expected))
        self.assertEqual(result["output_bytes_preserved"], len(expected))
        self.assertEqual(result["output_pipe_tail"], "eof_observed")
        self.assertFalse(result["output_prefix_gap"])
        self.assertFalse(result["output_overflow"])
        self.assertTrue(result["output_durable"])

    def test_S31_timeout_handler_respects_original_output_cap(self):
        code = """
def on_term(signum, frame):
    os.write(1, b'terminated:' + b'x' * 128 + b'\\n')
    os._exit(0)
signal.signal(signal.SIGTERM, on_term)
os.write(1, b'start\\n')
while True:
    time.sleep(1)
"""
        cap = 32
        result, _, log = self.run_stub(code, wall_seconds=0.3, output_log_limit_bytes=cap)
        full = b"start\nterminated:" + b"x" * 128 + b"\n"
        self.assert_resource(result, "cell_wall_limit")
        self.assertEqual(result["primary_outcome"], {"status": "resource_incomplete", "reason": "cell_wall_limit"})
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(log.read_bytes(), full[:cap])
        self.assertEqual(result["output_bytes_preserved"], cap)
        self.assertEqual(result["output_bytes_observed"], cap + 1)
        self.assertTrue(result["output_overflow"])
        self.assertTrue(result["output_prefix_gap"])
        self.assertTrue(result["output_durable"])
        self.assertEqual(result["output_pipe_tail"], "output_cap_reached")
        self.assertTrue(any(failure["phase"] == "post_cleanup_output" and
                            failure["status"] == "resource_incomplete" and
                            failure["reason"] == "output_log_limit"
                            for failure in result["secondary_failures"]), result)


if __name__ == "__main__":
    unittest.main()
