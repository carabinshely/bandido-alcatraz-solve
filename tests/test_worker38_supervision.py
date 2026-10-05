"""PROPOSED ONLY: finite S01-S16 helper tests; do not infer execution approval.

Imports only the standalone supervision helper and the Python standard library.
Every spawned program below is an invented stub, never an evaluator or fixture.
"""
from __future__ import annotations

import importlib.util
from contextlib import ExitStack, contextmanager
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "worker38" / "supervision.py"
SPEC = importlib.util.spec_from_file_location("worker38_supervision_standalone", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
supervision = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = supervision
SPEC.loader.exec_module(supervision)

STUB_PROCESS_STARTS = 0
STUB_SUPERVISOR_INVOCATIONS = 0
STUB_MOCKED_PROCESS_STARTS = 0
NATIVE_BATCH_DEADLINE_MONOTONIC = None
_NATIVE_BATCH_ORIGINAL_DEADLINE = None
_ROUTINE_CI_ORIGINAL_DEADLINE = None
STUB_DEADLINE_CONTEXT = None

STUB_PRELUDE = '''
import json, os, resource, signal, sys, time
from pathlib import Path
_stub_entry = time.monotonic()
_stub_cutoff = min(_stub_entry + 10.0, float(sys.argv[2]), float(sys.argv[3]) - 1.0)
def arm_same_lifetime():
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGALRM})
    remaining = _stub_cutoff - time.monotonic()
    if remaining <= 0:
        os._exit(124)
    signal.setitimer(signal.ITIMER_REAL, remaining, 0.0)
def within_lifetime():
    if time.monotonic() >= _stub_cutoff:
        os._exit(124)
    return True
def bounded_sleep(seconds):
    end = min(time.monotonic() + seconds, _stub_cutoff)
    while time.monotonic() < end:
        within_lifetime()
        time.sleep(min(0.01, max(0.0, end - time.monotonic())))
    within_lifetime()
arm_same_lifetime()
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


class LiteralBoundaryResourceError(RuntimeError):
    pass


class LiteralPreservationExpired(BaseException):
    def __init__(self, cutoff):
        super().__init__("invented preservation cutoff exhausted")
        self.worker38_preservation_deadline = cutoff
        self.worker38_failure = {"status": "resource_incomplete", "category": "resource",
            "phase": "preservation_boundary", "error_type": type(self).__name__, "error": str(self)}


class LiteralSupervisorBoundaryHarness:
    """Actual private supervisor with literal process/clock/alarm mocks; no OS child."""
    def __init__(self, root, scenario):
        self.root, self.scenario = Path(root), scenario
        self.root.mkdir(parents=True, exist_ok=True)
        self.now = 1000.0
        self.events, self.observed, self.cleanup_deadlines, self.log_fds = [], [], [], []
        self.post_cleanup_fsyncs = self.setter_count = self.subreaper_value = 0
        self.call_fault = False
        self.started = False
        self.pidfd_refs = {}
        self.next_pidfd = 987000000
        self.error_factory = LiteralBoundaryResourceError
        self.child = SimpleNamespace(pid=987654321, returncode=None, stdout=None)

    def __enter__(self):
        self.stack = ExitStack()
        self.stack.__enter__()
        read_fd, write_fd = os.pipe()
        os.write(write_fd, b"literal diagnostic prefix\n")
        os.close(write_fd)
        self.child.stdout = os.fdopen(read_fd, "rb", buffering=0)
        self.stack.callback(lambda: self.child.stdout.close() if not self.child.stdout.closed else None)
        harness = self
        class Selector:
            def __init__(self): self.registered = False
            def register(self, fileobj, flags): self.registered = True
            def unregister(self, fileobj): self.registered = False
            def select(self, timeout=0):
                return [(SimpleNamespace(fd=harness.child.stdout.fileno(), fileobj=harness.child.stdout), 1)] if self.registered else []
            def close(self): harness.events.append(("selector_close", harness.now))
        def inventory(ticks):
            self.events.append(("cleanup_proc_scan" if self.cleanup_deadlines else "proc_scan", self.now))
            pid = os.getpid()
            values = {pid: supervision._Process(pid, 0, pid, pid, "S", 1, 0.0, 0.0)}
            if self.started and self.child.returncode is None:
                values[self.child.pid] = self.pidfd_read(self.child.pid, ticks)
            return values
        def read_process(pid, ticks):
            if self.started and pid == self.child.pid and self.child.returncode is None:
                return supervision._Process(pid, os.getpid(), pid, pid, "S", 10, 0.0, 0.0)
            raise ProcessLookupError(pid)
        self.pidfd_read = read_process
        self.pidfd_signal = lambda pid, sig: self.events.append(("pid_signal", self.now, pid, sig))
        def initialize(child, *args, **kwargs):
            global STUB_MOCKED_PROCESS_STARTS
            STUB_MOCKED_PROCESS_STARTS += 1
            self.events.append(("mock_spawn", self.now))
            self.started = True
        def poll(child):
            if self.scenario == "arm_unconfirmed_exit65": child.returncode = 65
            elif self.scenario in ("success", "first_fsync_failure"): child.returncode = 0
        def call_state(*args, **kwargs):
            if self.scenario in ("resource_late_fsync", "cleanup_expiry") and not self.call_fault:
                self.call_fault, self.now = True, 1900.0
                self.events.append(("first_resource_failure", self.now))
                raise self.error_factory("invented first measurement resource failure")
            return None
        def cleanup(child, ticks, tracked, resource_exceptions=(), deadline=None, on_failure=None):
            self.cleanup_deadlines.append(deadline)
            self.events.append(("cleanup", self.now, deadline))
            if self.scenario == "cleanup_expiry" and len(self.cleanup_deadlines) == 1:
                self.now = 2601.0
                raise LiteralPreservationExpired(2500.0)
            if child.returncode is None:
                child.returncode = -signal.SIGKILL if self.scenario == "cleanup_expiry" else -signal.SIGTERM
            return {"complete": True, "sigkill_used": self.scenario == "cleanup_expiry",
                    "remaining_pids": [], "errors": [], "failure_details": []}
        def subreaper(get, value=0):
            if get: return self.subreaper_value
            self.setter_count += 1
            self.subreaper_value = value
            self.events.append(("subreaper_set", self.now, value))
            return value
        real_open, real_close = os.open, os.close
        def pidfd_open(pid, flags=0):
            proc = self.pidfd_read(pid, 100)
            self.next_pidfd += 1
            self.pidfd_refs[self.next_pidfd] = proc.identity
            self.events.append(("pidfd_open", self.now, proc.identity, self.next_pidfd))
            return self.next_pidfd
        def pidfd_send(descriptor, sig, siginfo=None, flags=0):
            identity = self.pidfd_refs[descriptor]
            self.events.append(("pidfd_signal", self.now, identity, sig))
            self.pidfd_signal(identity[0], sig)
        def close_descriptor(descriptor):
            if descriptor in self.pidfd_refs:
                self.events.append(("pidfd_close", self.now, self.pidfd_refs.pop(descriptor)))
            else:
                real_close(descriptor)
        def tracked_open(path, *args, **kwargs):
            fd = real_open(path, *args, **kwargs)
            if Path(path) == self.root / "literal-supervisor.log": self.log_fds.append(fd)
            return fd
        def fsync(fd):
            if self.cleanup_deadlines:
                self.post_cleanup_fsyncs += 1
                self.events.append(("post_cleanup_fsync", self.now))
                if self.scenario == "resource_late_fsync": self.now = 2601.0
                elif self.scenario == "first_fsync_failure":
                    if self.post_cleanup_fsyncs == 1:
                        self.now = 1900.0
                        raise OSError("invented first log-fsync failure")
                    self.now = 2601.0
                    raise LiteralPreservationExpired(2500.0)
        def usage(who):
            self.events.append(("usage", self.now, who))
            return 0.0
        def budget(path, incoming): self.events.append(("budget", self.now, incoming))
        patches = [mock.patch.object(supervision.time, "monotonic", side_effect=lambda: self.now),
            mock.patch.object(supervision, "_scan_processes", side_effect=inventory),
            mock.patch.object(supervision, "_inherited_limits", return_value={}),
            mock.patch.object(supervision, "_require_pidfd_support"),
            mock.patch.object(supervision, "_read_process", side_effect=lambda pid, ticks: self.pidfd_read(pid, ticks)),
            mock.patch.object(supervision.os, "pidfd_open", side_effect=pidfd_open),
            mock.patch.object(supervision.signal, "pidfd_send_signal", side_effect=pidfd_send),
            mock.patch.object(supervision.os, "close", side_effect=close_descriptor),
            mock.patch.object(supervision, "_subreaper", side_effect=subreaper),
            mock.patch.object(supervision, "_usage", side_effect=usage),
            mock.patch.object(supervision, "_poll", side_effect=poll),
            mock.patch.object(supervision, "_call_state", side_effect=call_state),
            mock.patch.object(supervision, "_cleanup", side_effect=cleanup),
            mock.patch.object(supervision, "_allocate_popen", return_value=self.child),
            mock.patch.object(supervision, "_initialize_popen", side_effect=initialize),
            mock.patch.object(supervision.selectors, "DefaultSelector", Selector),
            mock.patch.object(supervision.os, "fsync", side_effect=fsync),
            mock.patch.object(supervision.os, "open", side_effect=tracked_open),
            mock.patch.object(supervision.os, "killpg", side_effect=lambda *args: self.events.append(("killpg", self.now, args))),
            mock.patch.object(signal, "setitimer", side_effect=lambda *args: self.events.append(("alarm", self.now, args)))]
        for patch in patches: self.stack.enter_context(patch)
        self.phase = supervision.PhaseBudget(wall_seconds=1800, cpu_seconds=1800)
        self.kwargs = dict(command=["literal-never-executed"], env={}, cwd=self.root,
            output_log=self.root / "literal-supervisor.log", call_state=self.root / "literal-call-state.json",
            phase=self.phase, wall_seconds=720, cpu_seconds=720, call_wall_seconds=360, call_cpu_seconds=360,
            address_space_bytes=supervision.FROZEN_ADDRESS_SPACE, output_budget_check=budget,
            output_budget_exceptions=(LiteralBoundaryResourceError,))
        return self

    def callback(self, observed):
        self.observed.append(dict(observed))
        self.events.append(("transition", self.now, dict(observed)))
        cutoff = observed["first_failure_monotonic"] + 600
        signal.setitimer(signal.ITIMER_REAL, cutoff - self.now)
        if self.scenario == "arm_unconfirmed_exit65":
            error = OSError("invented alarm installation unconfirmed")
            error.worker38_preservation_deadline = cutoff
            raise error
        return cutoff

    def run(self, on_terminal_failure=None):
        global STUB_SUPERVISOR_INVOCATIONS
        STUB_SUPERVISOR_INVOCATIONS += 1
        return supervision._run_child(**self.kwargs,
            on_terminal_failure=self.callback if on_terminal_failure is None else on_terminal_failure)

    def __exit__(self, *args): return self.stack.__exit__(*args)


class LiteralPartialSpawnHarness(LiteralSupervisorBoundaryHarness):
    ROOT_PID, ADOPTED_PID, DESCENDANT_PID = 987654310, 987654311, 987654309
    OLD_PRODUCER_PID, UNRELATED_PID = 987654320, 987654321

    def __enter__(self):
        real_cleanup, real_poll = supervision._cleanup, supervision._poll
        super().__enter__()
        self.child.pid = None
        self.live, self.terminated = {}, {}
        self.signals, self.waited = [], []
        self.initialized = self.expiry_injected = False
        parent = os.getpid()
        parent_proc = supervision._Process(parent, 0, parent, parent, "S", 1, 0.0, 0.0)
        old_producer = supervision._Process(self.OLD_PRODUCER_PID, 77, 77, 77, "S", 2, 0.0, 0.0)
        unrelated = supervision._Process(self.UNRELATED_PID, 77, 77, 77, "S", 3, 0.0, 0.0)
        used = SimpleNamespace(ru_utime=0.0, ru_stime=0.0, ru_maxrss=1)
        def process(pid, ppid, start):
            return supervision._Process(pid, ppid, parent, parent, "S", start, 0.0, 0.0)
        def initialize(child, *args, **kwargs):
            global STUB_MOCKED_PROCESS_STARTS
            STUB_MOCKED_PROCESS_STARTS += 1
            self.initialized, self.now = True, 1900.0
            self.events.append(("partial_init", self.now))
            if self.scenario != "no_fork": self.live[self.ROOT_PID] = process(self.ROOT_PID, parent, 10)
            if self.scenario == "recover_direct":
                self.live[self.ADOPTED_PID] = process(self.ADOPTED_PID, parent, 11)
                self.live[self.DESCENDANT_PID] = process(self.DESCENDANT_PID, self.ROOT_PID, 12)
            if self.scenario in ("retained_pid", "targeted_available", "targeted_unavailable", "emergency_memory"):
                child.pid = self.ROOT_PID
                child.stdout.close()
                raise MemoryError("invented allocation failure after PID publication")
            if self.scenario == "no_fork": raise OSError("invented initializer failure before fork")
            raise LiteralBoundaryResourceError("invented constructor failure before PID publication")
        def inventory(ticks):
            self.events.append(("partial_proc_scan", self.now))
            if self.initialized and self.scenario in ("unavailable", "targeted_available", "targeted_unavailable", "emergency_memory"):
                raise OSError("invented unavailable post-fork inventory")
            old = process(old_producer.pid, parent, old_producer.start_ticks) if self.initialized else old_producer
            values = {parent: parent_proc, old.pid: old}
            if self.initialized: values[unrelated.pid] = unrelated
            values.update(self.live)
            if self.initialized and self.scenario == "expired_recovery": self.now = 2601.0
            return values
        def read_process(pid, ticks):
            self.events.append(("targeted_identity", self.now, pid))
            if self.scenario == "emergency_memory": raise MemoryError("invented targeted identity allocation failure")
            if self.scenario == "targeted_unavailable": raise OSError("invented unavailable targeted identity")
            if pid in self.live: return self.live[pid]
            raise ProcessLookupError(pid)
        def kill(pid, sig):
            self.signals.append((pid, sig))
            self.events.append(("pid_signal", self.now, pid, sig))
            if pid not in self.live: raise ProcessLookupError(pid)
            self.terminated[pid] = sig
            if pid == self.ROOT_PID and self.DESCENDANT_PID in self.live:
                old = self.live[self.DESCENDANT_PID]
                self.live[old.pid] = process(old.pid, parent, old.start_ticks)
        def wait4(pid, flags):
            self.waited.append(("wait4", pid))
            if pid in self.terminated:
                sig = self.terminated.pop(pid)
                self.live.pop(pid, None)
                return pid, sig, used
            if pid in self.live: return 0, 0, used
            raise ChildProcessError(pid)
        def waitpid(pid, flags):
            self.waited.append(("waitpid", pid))
            if pid in self.terminated:
                sig = self.terminated.pop(pid)
                self.live.pop(pid, None)
                return pid, sig
            if pid in self.live: return 0, 0
            raise ChildProcessError(pid)
        def cleanup(child, ticks, tracked, resource_exceptions=(), deadline=None, on_failure=None):
            self.cleanup_deadlines.append(deadline)
            self.events.append(("partial_cleanup", self.now, deadline))
            if self.scenario == "emergency_memory" and len(self.cleanup_deadlines) == 1:
                # The one-shot interruption follows the first retained identity;
                # later emergency reads then inject the distinct typed failure.
                with mock.patch.object(supervision, "_read_process", return_value=self.live[child.pid]):
                    supervision._remember_root(child, ticks)
                raise OSError("invented first cleanup interruption")
            if self.scenario == "expired_recovery" and not self.expiry_injected:
                self.expiry_injected = True
                raise LiteralPreservationExpired(2500.0)
            return real_cleanup(child, ticks, tracked, resource_exceptions, deadline, on_failure)
        self.pidfd_read = read_process
        self.pidfd_signal = kill
        patches = [mock.patch.object(supervision, "_initialize_popen", side_effect=initialize),
            mock.patch.object(supervision, "_scan_processes", side_effect=inventory),
            mock.patch.object(supervision, "_read_process", side_effect=read_process),
            mock.patch.object(supervision, "_poll", side_effect=real_poll),
            mock.patch.object(supervision, "_cleanup", side_effect=cleanup),
            mock.patch.object(supervision.os, "kill", side_effect=kill),
            mock.patch.object(supervision.os, "wait4", side_effect=wait4),
            mock.patch.object(supervision.os, "waitpid", side_effect=waitpid),
            mock.patch.object(supervision.time, "sleep", side_effect=lambda seconds: setattr(self, "now", self.now + seconds))]
        for patch in patches: self.stack.enter_context(patch)
        return self


@unittest.skipUnless(sys.platform == "linux", "Linux-only independent supervision")
class SupervisionStubTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="worker38-supervision-stub-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.counter = 0

    def run_stub(self, code, *, phase=None, before=None, **overrides):
        global STUB_PROCESS_STARTS, STUB_SUPERVISOR_INVOCATIONS, _NATIVE_BATCH_ORIGINAL_DEADLINE
        global _ROUTINE_CI_ORIGINAL_DEADLINE, STUB_DEADLINE_CONTEXT
        batch_deadline = NATIVE_BATCH_DEADLINE_MONOTONIC
        context = 'native_frozen_batch'
        if batch_deadline is None:
            self.assertTrue(os.environ.get('GITHUB_ACTIONS') == 'true' and
                            os.environ.get('GITHUB_WORKFLOW') == 'tests' and
                            os.environ.get('RUNNER_NAME') == 'bandido-alcatraz-ci' and
                            os.environ.get('GITHUB_REPOSITORY') == 'carabinshely/bandido-alcatraz-solve',
                            'only separately authorized fixed routine CI may establish its own test-module clock')
            if _ROUTINE_CI_ORIGINAL_DEADLINE is None:
                _ROUTINE_CI_ORIGINAL_DEADLINE = time.monotonic() + 600.0
            batch_deadline = _ROUTINE_CI_ORIGINAL_DEADLINE
            context = 'routine_ci_tests'
        if STUB_DEADLINE_CONTEXT is None:
            STUB_DEADLINE_CONTEXT = context
        self.assertEqual(STUB_DEADLINE_CONTEXT, context, 'test execution context cannot change mid-module')
        self.assertTrue(type(batch_deadline) in (float, int) and math.isfinite(batch_deadline),
                        'frozen native batch must supply its original absolute deadline')
        if _NATIVE_BATCH_ORIGINAL_DEADLINE is None:
            _NATIVE_BATCH_ORIGINAL_DEADLINE = batch_deadline
        self.assertEqual(batch_deadline, _NATIVE_BATCH_ORIGINAL_DEADLINE,
                         'native batch deadline cannot be renewed')
        launch_observed = time.monotonic()
        self.assertGreaterEqual(batch_deadline - launch_observed, 11.0,
                                'generic root requires at least11 seconds of original batch remainder')
        cutoff = min(launch_observed + 10.0, batch_deadline - 1.0)
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
        arguments = dict(command=[sys.executable, "-B", "-s", str(script), str(state),
                                  repr(cutoff), repr(batch_deadline)],
                         env=env, cwd=cell, output_log=log, call_state=state,
                         phase=phase or supervision.PhaseBudget(wall_seconds=10, cpu_seconds=10),
                         wall_seconds=3, cpu_seconds=2, call_wall_seconds=2, call_cpu_seconds=1,
                         address_space_bytes=512 * 1024 * 1024)
        arguments.update(overrides)
        self.assertGreaterEqual(batch_deadline - time.monotonic(), 11.0,
                                'literal setup left too little original batch time to launch')
        original_initialize = supervision._initialize_popen
        def initialize_before_original_deadlines(child, *args, **kwargs):
            now = time.monotonic()
            self.assertGreaterEqual(batch_deadline - now, 11.0,
                                    'actual root launch has less than11 seconds of original batch time')
            self.assertLess(now, cutoff, 'independent original root lifetime already expired')
            return original_initialize(child, *args, **kwargs)
        with mock.patch.object(supervision, '_initialize_popen', side_effect=initialize_before_original_deadlines):
            result = supervision._run_child(**arguments)
        STUB_PROCESS_STARTS += int(result["spawned"])
        if result['spawned']:
            self.assertIsNotNone(result['returncode'], 'unknown reap is not successful stub containment')
            self.assertNotIn(result['returncode'], (124, -signal.SIGALRM),
                             'independent stub self-expiry is a failed preparation case')
            self.assertLess(time.monotonic(), cutoff,
                            'supervisor cleanup must finish before independent stub cutoff')
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
        result, _, _ = self.run_stub("bounded_sleep(30)", wall_seconds=0.2)
        self.assert_resource(result, "cell_wall_limit")
        self.assertLess(result["wall_seconds"], 2)

    def test_S04_active_hang_with_profiles_suppressed(self):
        result, _, _ = self.run_stub("activate()\nsys.setprofile = lambda hook: None\nbounded_sleep(30)", call_wall_seconds=0.2)
        self.assert_resource(result, "call_wall_limit")
        self.assertEqual(result["active_call_at_stop"]["scope"], "candidate")

    def test_S05_live_cpu_not_just_reaped_children(self):
        result, _, _ = self.run_stub("activate()\nsys.setprofile = lambda hook: None\nwhile within_lifetime(): pass", call_cpu_seconds=0.15)
        self.assert_resource(result, "call_cpu_limit")
        self.assertGreaterEqual(result["child_cpu_seconds"], 0.15)
        self.assertGreater(result["phase"]["reaped_child_cpu_seconds"], 0)

    def test_S06_whole_cell_cpu_without_state(self):
        result, _, _ = self.run_stub("while within_lifetime(): pass", cpu_seconds=0.15)
        self.assert_resource(result, "cell_cpu_limit")

    def test_S07_phase_wall_blocks_or_terminates(self):
        phase = supervision.PhaseBudget(wall_seconds=1)
        phase.wall_started -= 2
        result, _, _ = self.run_stub("raise AssertionError('must not spawn')", phase=phase)
        self.assertEqual(result["status"], "execution_blocked", result)
        self.assertFalse(result["spawned"])
        self.assertIn("phase_wall_limit_before_spawn", " ".join(result["errors"]))
        phase = supervision.PhaseBudget(wall_seconds=0.2)
        result, _, _ = self.run_stub("bounded_sleep(30)", phase=phase)
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
        result, _, _ = self.run_stub("stop = time.process_time() + 0.08\nwhile time.process_time() < stop and within_lifetime(): pass", phase=phase)
        self.assertEqual(result["status"], "completed", result)
        prior = result["phase"]["reaped_child_cpu_seconds"]
        self.assertGreater(prior, 0.05)
        result, _, _ = self.run_stub("while within_lifetime(): pass", phase=phase)
        self.assert_resource(result, "phase_cpu_limit")
        self.assertGreater(result["phase"]["reaped_child_cpu_seconds"], prior)

    def test_S09_term_ignoring_escaped_descendant_is_killed(self):
        code = '''
pid = os.fork()
if pid == 0:
    arm_same_lifetime()
    os.setsid()
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    Path("descendant.pid").write_text(str(os.getpid()))
    while within_lifetime(): bounded_sleep(1)
else:
    while within_lifetime(): bounded_sleep(1)
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
    arm_same_lifetime()
    Path("descendant.pid").write_text(str(os.getpid()))
    while within_lifetime(): bounded_sleep(1)
else:
    while not Path("descendant.pid").exists(): bounded_sleep(0.005)
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
        result, _, log = self.run_stub("os.write(1, b'x' * 8192)\nbounded_sleep(30)", output_log_limit_bytes=257)
        self.assert_resource(result, "output_log_limit")
        self.assertEqual(log.read_bytes(), b"x" * 257)
        self.assertEqual(result["output_bytes_preserved"], 257)
        self.assertTrue(result["output_durable"])
        self.assertTrue(result["output_overflow"])
        def denied(path, incoming):
            raise supervision.OutputBudgetExceeded("invented shared raw cap")
        result, _, log = self.run_stub("print('bytes', flush=True)\nbounded_sleep(30)", output_budget_check=denied)
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
                result, _, _ = self.run_stub(code + "\nbounded_sleep(30)")
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
        with mock.patch.object(supervision, "_allocate_popen", side_effect=OSError("injected spawn failure")):
            result, _, _ = self.run_stub("pass")
        self.assertEqual(result["status"], "execution_blocked", result)
        self.assertFalse(result["spawned"])
        for name in ("_call_state",):
            with mock.patch.object(supervision, name, side_effect=OSError("injected state read failure")):
                result, _, _ = self.run_stub("bounded_sleep(30)")
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
            result, _, _ = self.run_stub("bounded_sleep(30)")
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
            result, _, _ = self.run_stub("bounded_sleep(30)", wall_seconds=0.1)
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
            result, _, _ = self.run_stub("bounded_sleep(30)", wall_seconds=0.2)
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
            result, _, log = self.run_stub("print('retained in memory', flush=True)\nbounded_sleep(30)", wall_seconds=0.2)
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
            result, _, _ = self.run_stub("bounded_sleep(30)")
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
            result, _, _ = self.run_stub("bounded_sleep(30)")
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
            result, _, _ = self.run_stub("bounded_sleep(30)")
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
            result, _, _ = self.run_stub("mark({'active': 'invalid'})\nbounded_sleep(30)")
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
while within_lifetime():
    bounded_sleep(1)
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
while within_lifetime():
    bounded_sleep(1)
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

    def assert_boundary_teardown(self, h, result):
        self.assertTrue(result["cleanup"]["complete"], result)
        self.assertTrue(h.child.stdout.closed)
        self.assertTrue(any(event[0] == "selector_close" for event in h.events))
        self.assertEqual(len(h.log_fds), 1)
        with self.assertRaises(OSError): os.fstat(h.log_fds[0])
        self.assertEqual(h.setter_count, 2)
        self.assertEqual(h.subreaper_value, 0)
        self.assertFalse(h.phase._running)

    def assert_no_expired_bulk(self, h):
        self.assertFalse(any(event[0] in ("usage", "budget", "proc_scan", "post_cleanup_fsync")
                             and event[1] >= 2500 for event in h.events))

    def test_S32_first_resource_failure_precedes_cleanup_and_late_fsync(self):
        with LiteralSupervisorBoundaryHarness(self.root / "S32", "resource_late_fsync") as h:
            result = h.run()
            self.assert_boundary_teardown(h, result)
            self.assertEqual(h.cleanup_deadlines, [1905.0])
            self.assertEqual(h.post_cleanup_fsyncs, 1)
            transition = next(i for i, e in enumerate(h.events) if e[0] == "transition")
            cleanup = next(i for i, e in enumerate(h.events) if e[0] == "cleanup")
            self.assertLess(transition, cleanup)
            self.assertEqual(len(h.observed), 1)
            self.assert_no_expired_bulk(h)
        self.assertEqual(result["primary_outcome"]["status"], "resource_incomplete")
        self.assertEqual(result["preservation_deadline_monotonic"], 2500.0)
        self.assertTrue(result["preservation_expired"])
        self.assertFalse(result["output_durable"])
        self.assertFalse(result["phase_accounting_complete"])

    def test_S33_expiry_inside_cleanup_keeps_original_deadline(self):
        with LiteralSupervisorBoundaryHarness(self.root / "S33", "cleanup_expiry") as h:
            result = h.run()
            self.assert_boundary_teardown(h, result)
            self.assertEqual(h.cleanup_deadlines, [1905.0, 1905.0])
            self.assertEqual(h.post_cleanup_fsyncs, 0)
            self.assertTrue(any(e[0] == "pidfd_signal" and e[3] == signal.SIGKILL for e in h.events))
            self.assertFalse(any(e[0] == "killpg" for e in h.events))
            self.assert_no_expired_bulk(h)
        self.assertEqual(result["preservation_deadline_monotonic"], 2500.0)
        self.assertTrue(result["preservation_expired"])
        self.assertFalse(result["child_accounting_complete"])
        self.assertFalse(result["phase_accounting_complete"])

    def test_S34_observed_exit65_survives_unconfirmed_callback(self):
        with LiteralSupervisorBoundaryHarness(self.root / "S34", "arm_unconfirmed_exit65") as h:
            result = h.run()
            self.assert_boundary_teardown(h, result)
            self.assertEqual(len(h.observed), 1)
            self.assertEqual(h.observed[0]["exit_code"], 65)
            self.assertEqual(h.cleanup_deadlines, [1005.0])
            self.assertEqual(h.post_cleanup_fsyncs, 0)
        self.assertEqual(result["exit_code"], 65)
        self.assertEqual(result["primary_outcome"], {"status": "execution_incomplete", "reason": "child_nonzero_exit"})
        self.assertEqual(result["preservation_deadline_monotonic"], 1600.0)
        self.assertTrue(result["preservation_transition_attempted"])
        self.assertFalse(result["preservation_transition_complete"])
        self.assertTrue(result["preservation_blocked"])
        self.assertFalse(result["child_accounting_complete"])

    def test_S35_success_has_clean_boundary_spawn_and_accounting(self):
        with LiteralSupervisorBoundaryHarness(self.root / "S35", "success") as h:
            result = h.run()
            self.assert_boundary_teardown(h, result)
            self.assertEqual(h.observed, [])
            self.assertFalse(any(e[0] == "alarm" for e in h.events))
        self.assertEqual(result["status"], "completed", result)
        self.assertIsNone(result["preservation_deadline_monotonic"])
        for field in ("preservation_transition_attempted", "preservation_transition_complete", "preservation_expired", "preservation_blocked", "spawn_ownership_uncertain"):
            self.assertIs(result[field], False)
        for field in ("spawn_attempted", "spawn_initialization_complete", "child_accounting_complete", "phase_accounting_complete", "output_durable"):
            self.assertIs(result[field], True)
        self.assertEqual(result["spawn_discovery"], "not_required")
        self.assertEqual(result["spawn_recovered_pids"], [])
        self.assertNotIn("first_terminal_failure", result)
        self.assertNotIn("preservation_boundary_failure", result)

    def test_S36_first_fsync_failure_has_only_preexpiry_fallback(self):
        with LiteralSupervisorBoundaryHarness(self.root / "S36", "first_fsync_failure") as h:
            result = h.run()
            self.assert_boundary_teardown(h, result)
            self.assertEqual(len(h.observed), 1)
            self.assertEqual(h.observed[0]["first_failure_monotonic"], 1900.0)
            self.assertEqual(h.post_cleanup_fsyncs, 2)
            transition = next(i for i, e in enumerate(h.events) if e[0] == "transition")
            fsyncs = [i for i, e in enumerate(h.events) if e[0] == "post_cleanup_fsync"]
            self.assertLess(fsyncs[0], transition)
            self.assertLess(transition, fsyncs[1])
        self.assertEqual(result["primary_outcome"], {"status": "completed", "reason": "child_exit_zero"})
        self.assertEqual(result["status"], "resource_incomplete")
        self.assertEqual(result["preservation_deadline_monotonic"], 2500.0)
        self.assertTrue(result["preservation_expired"])
        self.assertFalse(result["output_durable"])

    def test_S37_finally_entry_sentinel_cannot_bypass_teardown(self):
        with LiteralSupervisorBoundaryHarness(self.root / "S37", "resource_late_fsync") as h:
            real = supervision._FailureBoundary.start
            injected = False
            def faulty(boundary, **kwargs):
                nonlocal injected
                if boundary.attempted and kwargs.get("error") is None and not h.cleanup_deadlines and not injected:
                    injected, h.now = True, 2601.0
                    raise LiteralPreservationExpired(2500.0)
                return real(boundary, **kwargs)
            with mock.patch.object(supervision._FailureBoundary, "start", new=faulty): result = h.run()
            self.assertTrue(injected)
            self.assert_boundary_teardown(h, result)
            self.assertEqual(h.cleanup_deadlines, [1905.0])
            self.assertEqual(h.post_cleanup_fsyncs, 0)
            self.assert_no_expired_bulk(h)
        self.assertTrue(result["preservation_expired"])
        self.assertTrue(result["preservation_blocked"])
        self.assertEqual(result["preservation_deadline_monotonic"], 2500.0)

    def test_S38_first_boundary_bookkeeping_never_grants_late_authority(self):
        for stage, method in (("note", "note_exception"), ("clock", "_first_failure_time"), ("observation", "_observation")):
            with self.subTest(stage=stage):
                with LiteralSupervisorBoundaryHarness(self.root / ("S38-" + stage), "resource_late_fsync") as h:
                    real = getattr(supervision._FailureBoundary, method)
                    injected, flags = False, []
                    def faulty(boundary, *args, **kwargs):
                        nonlocal injected
                        if not injected:
                            injected = True
                            flags.append((boundary.attempted, boundary.confirmed, boundary.blocked,
                                boundary.result["preservation_transition_attempted"], boundary.result["preservation_transition_complete"], boundary.result["preservation_blocked"]))
                            if stage == "clock": raise LiteralPreservationExpired(None)
                            raise MemoryError("invented boundary " + stage + " allocation failure")
                        return real(boundary, *args, **kwargs)
                    with mock.patch.object(supervision._FailureBoundary, method, new=faulty): result = h.run()
                    self.assert_boundary_teardown(h, result)
                    self.assertEqual(flags, [(True, False, True, True, False, True)])
                    self.assertEqual(h.observed, [])
                    self.assertFalse(any(e[0] == "alarm" for e in h.events))
                    self.assertEqual(h.cleanup_deadlines, [1905.0 if stage == "observation" else 1000.0])
                    self.assertEqual(h.post_cleanup_fsyncs, 0)
                self.assertTrue(result["preservation_transition_attempted"])
                self.assertFalse(result["preservation_transition_complete"])
                self.assertTrue(result["preservation_blocked"])
                self.assertIsNone(result["preservation_deadline_monotonic"])

    def test_S39_postcleanup_bookkeeping_cannot_skip_remaining_teardown(self):
        for stage in ("observed_exit", "permit"):
            with self.subTest(stage=stage):
                with LiteralSupervisorBoundaryHarness(self.root / ("S39-" + stage), "resource_late_fsync") as h:
                    injected = False
                    if stage == "observed_exit":
                        real = supervision._retain_child_exit
                        def faulty(child, result):
                            nonlocal injected
                            if h.cleanup_deadlines and not injected:
                                injected, h.now = True, 2601.0
                                raise LiteralPreservationExpired(2500.0)
                            return real(child, result)
                        patch = mock.patch.object(supervision, "_retain_child_exit", new=faulty)
                    else:
                        real = supervision._FailureBoundary.permit
                        def faulty(boundary):
                            nonlocal injected
                            if h.cleanup_deadlines and not injected:
                                injected, h.now = True, 2601.0
                                raise LiteralPreservationExpired(2500.0)
                            return real(boundary)
                        patch = mock.patch.object(supervision._FailureBoundary, "permit", new=faulty)
                    with patch: result = h.run()
                    self.assertTrue(injected)
                    self.assert_boundary_teardown(h, result)
                    self.assertEqual(h.cleanup_deadlines, [1905.0])
                    self.assertEqual(h.post_cleanup_fsyncs, 0)
                    self.assert_no_expired_bulk(h)
                self.assertTrue(result["preservation_expired"])
                self.assertEqual(result["preservation_deadline_monotonic"], 2500.0)

    def assert_partial_spawn_restored(self, h, result):
        self.assertTrue(result["spawn_attempted"])
        self.assertFalse(result["spawn_initialization_complete"])
        self.assertTrue(h.child.stdout.closed)
        self.assertEqual(h.setter_count, 2)
        self.assertEqual(h.subreaper_value, 0)
        self.assertFalse(h.phase._running)
        with self.assertRaises(OSError): os.fstat(h.log_fds[0])
        self.assertEqual(result["preservation_deadline_monotonic"], 2500.0)
        self.assertEqual(len(h.observed), 1)
        self.assertEqual(sum(e[0] == "alarm" for e in h.events), 1)
        self.assertFalse(any(e[0] == "killpg" for e in h.events))
        excluded = {h.OLD_PRODUCER_PID, h.UNRELATED_PID, os.getpid()}
        self.assertFalse(any(pid in excluded for pid, _ in h.signals))
        self.assertFalse(any(pid in excluded for _, pid in h.waited))

    def test_S40_partial_initializer_retains_published_pid(self):
        with LiteralPartialSpawnHarness(self.root / "S40", "retained_pid") as h:
            result = h.run()
            self.assert_partial_spawn_restored(h, result)
            self.assertEqual(h.cleanup_deadlines, [1905.0])
            self.assertEqual(h.live, {})
            self.assertEqual(h.signals, [(h.ROOT_PID, signal.SIGTERM)])
        self.assertTrue(result["spawned"])
        self.assertEqual(result["pid"], h.ROOT_PID)
        self.assertFalse(result["spawn_ownership_uncertain"])
        self.assertEqual(result["spawn_discovery"], "retained_pid")
        self.assertTrue(result["cleanup"]["complete"], result)
        self.assertEqual(result["primary_outcome"]["exception_type"], "MemoryError")
        self.assertEqual(result["signal"], signal.SIGTERM)
        self.assertTrue(result["output_prefix_gap"])
        self.assertEqual(result["output_pipe_tail"], "closed_during_initialization")
        self.assertTrue(result["child_accounting_complete"])
        self.assertTrue(result["phase_accounting_complete"])

    def test_S41_missing_pid_selects_direct_wait_root_and_stable_identities(self):
        with LiteralPartialSpawnHarness(self.root / "S41", "recover_direct") as h:
            result = h.run()
            self.assert_partial_spawn_restored(h, result)
            self.assertEqual(h.cleanup_deadlines, [1905.0])
            self.assertEqual(h.live, {})
            owned = {h.ROOT_PID, h.ADOPTED_PID, h.DESCENDANT_PID}
            self.assertEqual({pid for pid, _ in h.signals}, owned)
            self.assertTrue(all(sig == signal.SIGTERM for _, sig in h.signals))
            stale = supervision._Process(h.ROOT_PID, os.getpid(), 1, 1, "S", 10, 0.0, 0.0)
            replacement = supervision._Process(h.ROOT_PID, 77, 1, 1, "S", 99, 0.0, 0.0)
            prior = list(h.signals)
            with mock.patch.object(supervision, "_read_process", return_value=replacement):
                supervision._cleanup_signal(h.child, {stale.pid: stale}, signal.SIGKILL, 100)
            self.assertEqual(h.signals, prior)
        self.assertEqual(result["spawn_discovery"], "recovered_direct_child")
        self.assertEqual(result["pid"], h.ROOT_PID)
        self.assertLess(h.DESCENDANT_PID, h.ROOT_PID)
        self.assertEqual(set(result["spawn_recovered_pids"]), owned)
        self.assertTrue(result["cleanup"]["complete"])
        self.assertTrue(result["child_accounting_complete"])
        self.assertTrue(result["phase_accounting_complete"])

    def test_S42_missing_pid_unavailable_inventory_stays_unknown(self):
        with LiteralPartialSpawnHarness(self.root / "S42", "unavailable") as h:
            result = h.run()
            self.assert_partial_spawn_restored(h, result)
            self.assertEqual(h.signals, [])
            self.assertEqual(h.waited, [])
            self.assertEqual(h.cleanup_deadlines, [])
            self.assertIn(h.ROOT_PID, h.live)
        self.assertIsNone(result["spawned"])
        self.assertIsNone(result["pid"])
        self.assertTrue(result["spawn_ownership_uncertain"])
        self.assertFalse(result["cleanup"]["complete"])
        self.assertFalse(result["output_durable"])
        self.assertTrue(result["output_prefix_gap"])
        self.assertTrue(any(x["reason"] == "partial_spawn_discovery_failed" for x in result["secondary_failures"]))
        self.assertTrue(any(x["reason"] == "process_cleanup_unconfirmed" for x in result["secondary_failures"]))
        self.assertFalse(result["child_accounting_complete"])
        self.assertFalse(result["phase_accounting_complete"])
        self.assertEqual(result["child_cpu_seconds"], 0.0)
        self.assertEqual(result["phase"]["cpu_seconds"], 0.0)

    def test_S43_empty_current_inventory_does_not_infer_never_created(self):
        with LiteralPartialSpawnHarness(self.root / "S43", "no_fork") as h:
            result = h.run()
            self.assert_partial_spawn_restored(h, result)
            self.assertEqual(h.signals, [])
            self.assertEqual(h.waited, [])
            self.assertEqual(h.cleanup_deadlines, [])
            self.assertEqual(h.live, {})
        self.assertIsNone(result["spawned"])
        self.assertFalse(result["spawn_ownership_uncertain"])
        self.assertEqual(result["spawn_discovery"], "no_owned_child_observed")
        self.assertTrue(result["cleanup"]["complete"])
        self.assertIsNone(result["returncode"])
        self.assertIsNone(result["exit_code"])
        self.assertIsNone(result["signal"])

    def test_S44_partial_spawn_expiry_keeps_original_cleanup_cutoff(self):
        with LiteralPartialSpawnHarness(self.root / "S44", "expired_recovery") as h:
            result = h.run()
            self.assert_partial_spawn_restored(h, result)
            self.assertTrue(h.expiry_injected)
            self.assertEqual(h.cleanup_deadlines, [1905.0, 1905.0])
            self.assertEqual(h.live, {})
            self.assertEqual(h.signals, [(h.ROOT_PID, signal.SIGKILL)])
            self.assertEqual(h.post_cleanup_fsyncs, 0)
            self.assert_no_expired_bulk(h)
        self.assertTrue(result["cleanup"]["complete"])
        self.assertTrue(result["cleanup"]["sigkill_used"])
        self.assertTrue(result["preservation_expired"])
        self.assertFalse(result["output_durable"])
        self.assertFalse(result["phase_accounting_complete"])

    def test_S45_retained_identity_fallback_keeps_typed_causes_and_lower_bounds(self):
        for variant in ("targeted_available", "targeted_unavailable", "emergency_memory"):
            with self.subTest(variant=variant):
                with LiteralPartialSpawnHarness(self.root / ("S45-" + variant), variant) as h:
                    result = h.run()
                    self.assert_partial_spawn_restored(h, result)
                    self.assertEqual(h.cleanup_deadlines, [1905.0, 1905.0] if variant == "emergency_memory" else [1905.0])
                    transition = next(i for i, e in enumerate(h.events) if e[0] == "transition")
                    targeted = [i for i, e in enumerate(h.events) if e[0] == "targeted_identity"]
                    self.assertTrue(targeted)
                    self.assertGreater(min(targeted), transition)
                    if variant == "targeted_available":
                        self.assertEqual(h.live, {})
                        self.assertEqual(h.signals, [(h.ROOT_PID, signal.SIGKILL)])
                        self.assertTrue(result["cleanup"]["sigkill_used"])
                    else:
                        self.assertIn(h.ROOT_PID, h.live)
                        self.assertEqual(h.signals, [])
                        self.assertFalse(result["cleanup"]["sigkill_used"])
                        self.assertIn(h.ROOT_PID, result["cleanup"]["remaining_pids"])
                        self.assertIsNone(result["returncode"])
                if variant == "emergency_memory":
                    self.assertTrue(any(x["reason"] == "emergency_cleanup_inventory_failed" and x.get("exception_type") == "OSError" for x in result["secondary_failures"]))
                    self.assertTrue(any(x["reason"] == "emergency_group_kill_failed" and x.get("exception_type") == "MemoryError" and x["status"] == "resource_incomplete" for x in result["secondary_failures"]))
                self.assertFalse(result["cleanup"]["complete"])
                self.assertEqual(result["primary_outcome"]["status"], "resource_incomplete")
                self.assertFalse(result["child_accounting_complete"])
                self.assertFalse(result["phase_accounting_complete"])
                self.assertEqual(result["child_cpu_seconds"], 0.0)
                self.assertEqual(result["phase"]["cpu_seconds"], 0.0)


    def literal_owned_child(self, pid=987650001, start=10, *, reaped=False):
        tracked = {(pid, start)} if reaped else set()
        return SimpleNamespace(pid=pid, returncode=0 if reaped else None,
            _worker38_ticks=100, _worker38_spawn_baseline=frozenset(),
            _worker38_tracked=tracked, _worker38_root_identity=(pid, start) if reaped else None,
            _worker38_ownership_uncertain=not reaped)

    def test_S46_root_identity_precedes_first_wait_even_for_fast_exit(self):
        for variant in ('running', 'zombie', 'unavailable'):
            with self.subTest(variant=variant):
                child = self.literal_owned_child()
                events = []
                proc = supervision._Process(child.pid, os.getpid(), child.pid, child.pid,
                    'Z' if variant == 'zombie' else 'S', 10, 0.0, 0.0)
                def read(pid, ticks):
                    events.append('identity')
                    if variant == 'unavailable': raise OSError('literal identity unavailable')
                    return proc
                def wait(pid, flags):
                    events.append('wait4')
                    self.assertEqual(child._worker38_root_identity, proc.identity)
                    return (pid if variant == 'zombie' else 0, 0, SimpleNamespace(ru_utime=0.0, ru_stime=0.0))
                with mock.patch.object(supervision, '_read_process', side_effect=read), \
                     mock.patch.object(supervision.os, 'wait4', side_effect=wait):
                    if variant == 'unavailable':
                        with self.assertRaises(OSError): supervision._poll(child)
                        self.assertEqual(events, ['identity'])
                        self.assertIsNone(child._worker38_root_identity)
                        self.assertTrue(child._worker38_ownership_uncertain)
                    else:
                        supervision._poll(child)
                        self.assertEqual(events, ['identity', 'wait4'])
                        self.assertEqual(child._worker38_root_identity, proc.identity)
                        self.assertIn(proc.identity, child._worker38_tracked)
                        if variant == 'zombie':
                            with mock.patch.object(supervision, '_read_process', side_effect=AssertionError('must not replace root after reap')):
                                supervision._poll(child)
                            self.assertEqual(events, ['identity', 'wait4'])

    def test_S47_reused_root_group_and_baseline_do_not_confer_ownership(self):
        root, descendant, producer, unrelated, replacement_child = 987651001, 987651002, 987651003, 987651004, 987651005
        frozen = (root, 10)
        tracked = {frozen, (descendant, 20)}
        baseline = {(producer, 30)}
        rows = {
            root: supervision._Process(root, 77, root, root, 'S', 99, 0.0, 0.0),
            descendant: supervision._Process(descendant, 77, descendant, descendant, 'S', 20, 0.0, 0.0),
            producer: supervision._Process(producer, os.getpid(), root, root, 'S', 30, 0.0, 0.0),
            unrelated: supervision._Process(unrelated, 77, root, root, 'S', 40, 0.0, 0.0),
            replacement_child: supervision._Process(replacement_child, root, root, root, 'S', 50, 0.0, 0.0),
        }
        with mock.patch.object(supervision, '_read_process', side_effect=AssertionError('no numeric-group lineage')):
            owned = supervision._owned_processes(rows, frozen, tracked, baseline, 100)
        self.assertEqual(set(owned), {descendant})
        self.assertEqual(tracked, {frozen, (descendant, 20)})
        class Replacement:
            identity = (root, 99)
            @property
            def own_cpu(self): raise AssertionError('replacement CPU must not enter original call accounting')
        marker = self.root / 'S47-call.json'
        value = {'active': True, 'scope': 'candidate', 'wall_started': 110.0, 'cpu_started': 0.0}
        marker.write_text(json.dumps(value), encoding='utf-8')
        with mock.patch.object(supervision, '_read_process', return_value=Replacement()), \
             mock.patch.object(supervision.time, 'monotonic', return_value=123.0):
            self.assertEqual(supervision._call_state(marker, 123.0, 0.0, 100.0, 100, root, frozen), value)

    def test_S48_descendant_requires_current_original_parent_identity(self):
        root, descendant = 987652001, 987652002
        original = supervision._Process(root, os.getpid(), root, root, 'S', 10, 0.0, 0.0)
        descendant_row = supervision._Process(descendant, root, root, root, 'S', 20, 0.0, 0.0)
        for variant in ('matching_parent', 'replaced_parent'):
            with self.subTest(variant=variant):
                tracked = {original.identity}
                current = original if variant == 'matching_parent' else supervision._Process(root, 77, root, root, 'S', 99, 0.0, 0.0)
                with mock.patch.object(supervision, '_read_process', return_value=current):
                    if variant == 'matching_parent':
                        owned = supervision._owned_processes({root: original, descendant: descendant_row}, original.identity, tracked, set(), 100)
                        self.assertEqual(set(owned), {root, descendant})
                    else:
                        with self.assertRaises(supervision.SupervisionError):
                            supervision._owned_processes({root: original, descendant: descendant_row}, original.identity, tracked, set(), 100)
                        self.assertNotIn(descendant_row.identity, tracked)

    def test_S49_pidfd_pins_target_across_fixed_reuse_windows(self):
        pid, descriptor = 987653001, 7654321
        original = supervision._Process(pid, os.getpid(), pid, pid, 'S', 10, 0.0, 0.0)
        replacement = supervision._Process(pid, 77, pid, pid, 'S', 99, 0.0, 0.0)
        for variant in ('before_acquisition', 'after_acquisition', 'after_recheck'):
            with self.subTest(variant=variant):
                bound, signaled = [], []
                def acquire(got_pid, flags):
                    self.assertEqual(got_pid, pid)
                    bound.append(replacement.identity if variant == 'before_acquisition' else original.identity)
                    return descriptor
                def send(fd, sig, siginfo, flags):
                    self.assertEqual(fd, descriptor)
                    signaled.append(bound[0])
                    # Original exits and the numeric PID is reused at this point;
                    # the descriptor remains bound to the departed original.
                    raise ProcessLookupError('literal original exited')
                with mock.patch.object(supervision.os, 'pidfd_open', side_effect=acquire), \
                     mock.patch.object(supervision, '_read_process', return_value=original if variant == 'after_recheck' else replacement), \
                     mock.patch.object(supervision.signal, 'pidfd_send_signal', side_effect=send), \
                     mock.patch.object(supervision.os, 'close') as close, \
                     mock.patch.object(supervision.os, 'kill', side_effect=AssertionError('numeric signal forbidden')), \
                     mock.patch.object(supervision.os, 'killpg', side_effect=AssertionError('group signal forbidden')):
                    supervision._signal_owned({pid: original}, pid, signal.SIGKILL, 100)
                close.assert_called_once_with(descriptor)
                self.assertNotIn(replacement.identity, signaled)
                self.assertEqual(signaled, [original.identity] if variant == 'after_recheck' else [])

    def test_S50_normal_and_emergency_inventory_failure_keep_retained_targets(self):
        for variant in ('normal_cleanup', 'emergency_cleanup'):
            with self.subTest(variant=variant):
                child = self.literal_owned_child(reaped=True)
                root = child.pid
                descendant = root + 1
                child._worker38_tracked.add((descendant, 20))
                replacement = supervision._Process(root, 77, root, root, 'S', 99, 0.0, 0.0)
                escaped = supervision._Process(descendant, 77, descendant, descendant, 'S', 20, 0.0, 0.0)
                clock = [1900.0]
                alive = {descendant: escaped}
                signaled, failures, closed = [], [], []
                def read(pid, ticks):
                    if pid == root: return replacement
                    if pid in alive: return alive[pid]
                    raise ProcessLookupError(pid)
                def acquire(pid, flags):
                    if pid not in alive: raise ProcessLookupError(pid)
                    return pid + 100
                def send(fd, sig, siginfo, flags):
                    pid = fd - 100
                    signaled.append((pid, sig))
                    alive.pop(pid, None)
                def failed(error, reason): failures.append((type(error).__name__, reason))
                with mock.patch.object(supervision, '_scan_processes', side_effect=OSError('literal inventory unavailable')), \
                     mock.patch.object(supervision, '_read_process', side_effect=read), \
                     mock.patch.object(supervision.os, 'pidfd_open', side_effect=acquire), \
                     mock.patch.object(supervision.signal, 'pidfd_send_signal', side_effect=send), \
                     mock.patch.object(supervision.os, 'close', side_effect=lambda fd: closed.append(fd)), \
                     mock.patch.object(supervision.os, 'kill', side_effect=AssertionError('numeric signal forbidden')), \
                     mock.patch.object(supervision.os, 'killpg', side_effect=AssertionError('group signal forbidden')), \
                     mock.patch.object(supervision.time, 'monotonic', side_effect=lambda: clock[0]), \
                     mock.patch.object(supervision.time, 'sleep', side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)):
                    if variant == 'normal_cleanup':
                        result = supervision._cleanup(child, 100, child._worker38_tracked, (), 1905.0, failed)
                        self.assertFalse(result['complete'])
                        self.assertTrue(result['sigkill_used'])
                        self.assertGreaterEqual(clock[0], 1905.0)
                        self.assertLess(clock[0], 1905.0 + supervision.POLL_SECONDS * 1.1)
                    else:
                        with self.assertRaises(OSError):
                            supervision._emergency_cleanup_kill(child, 100, child._worker38_tracked, failed)
                        self.assertEqual(clock[0], 1900.0)
                self.assertEqual(signaled, [(descendant, signal.SIGKILL)])
                self.assertEqual(closed, [descendant + 100])
                self.assertTrue(failures)
                self.assertTrue(all(kind == 'OSError' for kind, _ in failures))
                self.assertEqual(child._worker38_root_identity, (root, 10))

    def test_S51_normal_spawn_missing_root_proof_is_incomplete(self):
        real_cleanup, real_poll = supervision._cleanup, supervision._poll
        with LiteralSupervisorBoundaryHarness(self.root / 'S51', 'success') as h:
            first = True
            def unavailable(pid, ticks):
                nonlocal first
                if first:
                    h.now, first = 1900.0, False
                raise OSError('literal root identity unavailable')
            def cleanup(child, ticks, tracked, resource_exceptions=(), deadline=None, on_failure=None):
                h.cleanup_deadlines.append(deadline)
                return real_cleanup(child, ticks, tracked, resource_exceptions, deadline, on_failure)
            with mock.patch.object(supervision, '_read_process', side_effect=unavailable), \
                 mock.patch.object(supervision, '_poll', side_effect=real_poll), \
                 mock.patch.object(supervision, '_cleanup', side_effect=cleanup), \
                 mock.patch.object(supervision.os, 'wait4', side_effect=AssertionError('unproven root must not be reaped')), \
                 mock.patch.object(supervision.time, 'sleep', side_effect=lambda seconds: setattr(h, 'now', h.now + seconds)):
                result = h.run()
            self.assertEqual(h.cleanup_deadlines, [1905.0])
            self.assertEqual(h.setter_count, 2)
            self.assertEqual(h.subreaper_value, 0)
            self.assertFalse(h.phase._running)
            self.assertTrue(h.child.stdout.closed)
            with self.assertRaises(OSError): os.fstat(h.log_fds[0])
            self.assertFalse(any(e[0] in ('pid_signal', 'pidfd_signal', 'killpg') for e in h.events))
        self.assertTrue(result['spawned'])
        self.assertTrue(result['spawn_ownership_uncertain'])
        self.assertFalse(result['cleanup']['complete'])
        self.assertFalse(result['child_accounting_complete'])
        self.assertFalse(result['phase_accounting_complete'])
        self.assertEqual(result['preservation_deadline_monotonic'], 2500.0)
        self.assertEqual(result['primary_outcome']['exception_type'], 'OSError')

    def test_S52_pidfd_prerequisite_and_close_fail_closed(self):
        for variant in ('missing_open', 'missing_send', 'unsupported_kernel', 'typed_close_failure'):
            with self.subTest(variant=variant):
                acquire = mock.Mock(return_value=123)
                send, close = mock.Mock(), mock.Mock()
                if variant == 'unsupported_kernel': acquire.side_effect = OSError(38, 'literal ENOSYS')
                if variant == 'typed_close_failure': close.side_effect = MemoryError('literal pidfd close failure')
                expected = (supervision.SupervisionError if variant.startswith('missing_') else
                            MemoryError if variant == 'typed_close_failure' else OSError)
                with mock.patch.object(supervision.os, 'pidfd_open', None if variant == 'missing_open' else acquire), \
                     mock.patch.object(supervision.signal, 'pidfd_send_signal', None if variant == 'missing_send' else send), \
                     mock.patch.object(supervision.os, 'close', close), \
                     mock.patch.object(supervision.os, 'kill', side_effect=AssertionError('numeric fallback forbidden')), \
                     mock.patch.object(supervision.os, 'killpg', side_effect=AssertionError('group fallback forbidden')):
                    with self.assertRaises(expected) as caught: supervision._require_pidfd_support()
                if variant == 'typed_close_failure':
                    send.assert_called_once_with(123, 0, None, 0)
                    close.assert_called_once_with(123)
                    self.assertEqual(supervision._exception_status(caught.exception), 'resource_incomplete')
                else:
                    close.assert_not_called()
                    send.assert_not_called()



if __name__ == "__main__":
    unittest.main()
