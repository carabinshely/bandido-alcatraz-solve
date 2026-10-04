"""Fail-closed, standard-library-only Linux child resource supervision.

This helper never imports policy/game code or infers scientific returns. A
``completed`` result means only a zero process exit with confirmed cleanup.
The admission driver owns exact frozen arguments, source/runtime checks, raw
attempt size limits, call-state instrumentation, and scientific acceptance.

The atomic call-state channel is trusted instrumentation, not a defense against
a malicious child lying about entering a call. Enforcement runs outside child
profile hooks, using /proc live CPU and monotonic wall time. Linux accounting is
clock-tick quantized; checks have bounded polling latency. A kernel CPU ceiling
is an additional whole-child backstop. Use a dedicated single-threaded parent
with no unrelated children. Linux pidfd support is checked on the supervisor
itself before spawn; every cleanup signal uses a revalidated pidfd, never a
numeric PID or process-group fallback. No replacement child runs occur here.
"""
from __future__ import annotations

import ctypes
import errno
from contextlib import contextmanager, nullcontext
import json
import math
import os
from pathlib import Path
import resource
import selectors
import signal
import stat
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Callable, Mapping, Sequence

FROZEN_ADDRESS_SPACE = 512 * 1024 * 1024
DEFAULT_LOG_LIMIT = 1024 * 1024
CALL_STATE_LIMIT = 16 * 1024
POLL_SECONDS = 0.02
TERM_GRACE_SECONDS = 0.10
CLEANUP_SECONDS = 5.0


class SupervisionError(RuntimeError):
    """A failed supervision prerequisite or independent observation."""


class CallStateIntegrityError(SupervisionError):
    """Committed call-state bytes violate the trusted instrumentation contract."""


class OutputBudgetExceeded(RuntimeError):
    """The caller reports its prospective shared raw output limit was reached."""


def _positive(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise SupervisionError(f"{name} must be a finite positive number")
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise SupervisionError(f"{name} must be a finite positive number")
    return value


def _usage(who: int) -> float:
    used = resource.getrusage(who)
    return used.ru_utime + used.ru_stime


@dataclass
class PhaseBudget:
    """Starts before startup, accounting parent + reaped + live child CPU."""
    wall_seconds: float = 1800
    cpu_seconds: float = 1800
    wall_started: float = field(init=False)
    parent_cpu_started: float = field(init=False)
    reaped_child_cpu_started: float = field(init=False)
    _cpu_high_water: float = field(init=False, default=0.0)
    _running: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        self.wall_seconds = _positive(self.wall_seconds, "phase.wall_seconds")
        self.cpu_seconds = _positive(self.cpu_seconds, "phase.cpu_seconds")
        self.wall_started = time.monotonic()
        self.parent_cpu_started = _usage(resource.RUSAGE_SELF)
        self.reaped_child_cpu_started = _usage(resource.RUSAGE_CHILDREN)

    def snapshot(self, live_child_cpu_seconds: float = 0.0) -> dict:
        parent = max(0.0, _usage(resource.RUSAGE_SELF) - self.parent_cpu_started)
        reaped = max(0.0, _usage(resource.RUSAGE_CHILDREN) - self.reaped_child_cpu_started)
        live = max(0.0, float(live_child_cpu_seconds))
        self._cpu_high_water = max(self._cpu_high_water, parent + reaped + live)
        return {"wall_seconds": max(0.0, time.monotonic() - self.wall_started),
                "parent_cpu_seconds": parent, "reaped_child_cpu_seconds": reaped,
                "live_child_cpu_seconds": live, "cpu_seconds": self._cpu_high_water,
                "wall_limit_seconds": self.wall_seconds, "cpu_limit_seconds": self.cpu_seconds}

    def exhausted(self, snapshot: dict) -> str | None:
        if snapshot["wall_seconds"] >= self.wall_seconds:
            return "phase_wall_limit"
        if snapshot["cpu_seconds"] >= self.cpu_seconds:
            return "phase_cpu_limit"
        return None


@dataclass(frozen=True)
class _Process:
    pid: int
    ppid: int
    pgrp: int
    session: int
    state: str
    start_ticks: int
    own_cpu: float
    waited_cpu: float

    @property
    def identity(self) -> tuple[int, int]:
        return (self.pid, self.start_ticks)


def _read_process(pid: int, ticks: int) -> _Process:
    raw = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    close = raw.rfind(")")  # comm itself may contain spaces or parentheses.
    fields = raw[close + 2:].split()
    if close < 0 or len(fields) < 22:
        raise SupervisionError(f"malformed proc stat for pid {pid}")
    try:
        return _Process(pid, int(fields[1]), int(fields[2]), int(fields[3]),
                        fields[0], int(fields[19]),
                        (int(fields[11]) + int(fields[12])) / ticks,
                        (int(fields[13]) + int(fields[14])) / ticks)
    except (ValueError, IndexError) as exc:
        raise SupervisionError(f"invalid proc stat for pid {pid}") from exc


def _scan_processes(ticks: int) -> dict[int, _Process]:
    result = {}
    for entry in Path("/proc").iterdir():
        if entry.name.isdecimal():
            try:
                proc = _read_process(int(entry.name), ticks)
            except (FileNotFoundError, ProcessLookupError):
                continue
            except PermissionError:
                try:
                    owned = entry.stat().st_uid == os.getuid()
                except FileNotFoundError:
                    continue
                if owned:
                    raise SupervisionError(f"owned proc stat unreadable: {entry.name}")
                continue
            result[proc.pid] = proc
    return result


def _subreaper(get: bool, value: int = 0) -> int:
    libc = ctypes.CDLL(None, use_errno=True)
    if not hasattr(libc, "prctl"):
        raise SupervisionError("Linux child subreaper unavailable")
    current = ctypes.c_int()
    status = (libc.prctl(37, ctypes.byref(current), 0, 0, 0) if get
              else libc.prctl(36, int(value), 0, 0, 0))
    if status != 0:
        raise SupervisionError(f"Linux child subreaper failed: errno {ctypes.get_errno()}")
    return current.value if get else value


def _arm_parent_death_signal(expected_parent_pid: int) -> None:
    """Kill the direct child if its coordinator dies, including coordinator KILL.

    Linux clears PDEATHSIG in forked descendants; ordinary failure cleanup still
    owns all descendants. This is not a cgroup-wide hard-kill guarantee, nor can
    it make a process in uninterruptible kernel I/O disappear immediately.
    """
    libc = ctypes.CDLL(None, use_errno=True)
    if not hasattr(libc, "prctl"):
        raise SupervisionError("Linux parent-death signal unavailable")
    if libc.prctl(1, int(signal.SIGKILL), 0, 0, 0) != 0:  # PR_SET_PDEATHSIG
        raise SupervisionError(f"parent-death signal setup failed: errno {ctypes.get_errno()}")
    installed = ctypes.c_int()
    if libc.prctl(2, ctypes.byref(installed), 0, 0, 0) != 0 or installed.value != signal.SIGKILL:
        raise SupervisionError("parent-death signal verification failed")
    # Close the fork/prctl race: the parent may already have died before arming.
    if os.getppid() != expected_parent_pid:
        os.kill(os.getpid(), signal.SIGKILL)
        os._exit(127)  # Defensive fallback; never continue with a different parent.


def _inherited_limits() -> dict[str, list[int]]:
    unlimited = (resource.RLIM_INFINITY, resource.RLIM_INFINITY)
    watched = ("RLIMIT_AS", "RLIMIT_CPU", "RLIMIT_DATA", "RLIMIT_RSS", "RLIMIT_FSIZE")
    result = {}
    for name in watched:
        if not hasattr(resource, name):
            raise SupervisionError(f"missing Linux {name}")
        pair = resource.getrlimit(getattr(resource, name))
        result[name] = list(pair)
        allowed = (unlimited, (FROZEN_ADDRESS_SPACE, FROZEN_ADDRESS_SPACE)) if name == "RLIMIT_AS" else (unlimited,)
        if pair not in allowed:
            raise SupervisionError(f"unexpected inherited {name}: {pair!r}")
    # Capture every platform-dependent limit for an explicit admission baseline.
    for name in sorted(name for name in dir(resource) if name.startswith("RLIMIT_")):
        result[name] = list(resource.getrlimit(getattr(resource, name)))
    return result


def inherited_limits_snapshot() -> dict[str, list[int]]:
    """Read-only exact baseline for a later admission; never changes limits."""
    return _inherited_limits()


def _owned_processes(processes, root_identity, tracked, baseline, ticks):
    """Stable observed identities and lineage, never numeric group/session IDs."""
    known = set(tracked)
    if root_identity is not None:
        known.add(root_identity)
    known_pids = {pid for pid, _ in known}
    fresh = {pid: proc for pid, proc in processes.items() if proc.identity not in baseline}
    owned = {}
    for pid, proc in fresh.items():
        if proc.identity in known:
            owned[pid] = proc
        elif pid in known_pids:
            if proc.ppid == os.getpid():
                raise SupervisionError("new direct child reuses an already observed PID")
            # A replacement of an observed process never inherits ownership.
            continue
        elif proc.ppid == os.getpid():
            owned[pid] = proc
    changed = True
    while changed:
        changed = False
        for pid, proc in fresh.items():
            if pid in owned or pid in known_pids or proc.ppid not in owned:
                continue
            parent = owned[proc.ppid]
            # The scan is not atomic. Recheck the parent AFTER observing the
            # child's parentage, so a reused parent PID cannot confer ownership.
            try:
                current_parent = _read_process(parent.pid, ticks)
            except (FileNotFoundError, ProcessLookupError) as exc:
                raise SupervisionError("descendant parent identity became unavailable") from exc
            if current_parent.identity != parent.identity:
                raise SupervisionError("descendant parent identity changed")
            owned[pid] = proc
            changed = True
    tracked.update(proc.identity for proc in owned.values())
    return owned


def _require_pidfd_support():
    """Harmless self-only capability gate before creating a cell process."""
    if not callable(getattr(os, "pidfd_open", None)) or not callable(getattr(signal, "pidfd_send_signal", None)):
        raise SupervisionError("Linux pidfd APIs are required for identity-safe signaling")
    descriptor = os.pidfd_open(os.getpid(), 0)
    try:
        signal.pidfd_send_signal(descriptor, 0, None, 0)
    finally:
        os.close(descriptor)


def _remember_root(child, ticks):
    """Freeze the original direct-child identity before any wait can reap it."""
    identity = getattr(child, "_worker36_root_identity", None)
    if identity is not None:
        if identity[0] != child.pid:
            raise SupervisionError("retained root PID changed")
        return identity
    child._worker36_ownership_uncertain = True
    if child.returncode is not None:
        raise SupervisionError("root was reaped before its identity was retained")
    proc = _read_process(child.pid, ticks)
    baseline = child._worker36_spawn_baseline
    if proc.ppid != os.getpid() or proc.identity in baseline:
        raise SupervisionError("original root direct-child identity unavailable")
    child._worker36_root_identity = proc.identity
    child._worker36_tracked.add(proc.identity)
    child._worker36_ownership_uncertain = False
    return proc.identity


def _call_state(path: Path, now: float, root_cpu: float, started: float, ticks: int, root_pid: int | None = None, root_identity: tuple[int, int] | None = None) -> dict | None:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise CallStateIntegrityError("committed call_state may not be a symlink") from exc
        raise
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > CALL_STATE_LIMIT:
            raise CallStateIntegrityError("call_state must be a bounded regular file")
        raw = os.read(fd, CALL_STATE_LIMIT + 1)
        if len(raw) > CALL_STATE_LIMIT:
            raise CallStateIntegrityError("call_state exceeds limit")
    finally:
        os.close(fd)
    try:
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError("duplicate JSON key")
                result[key] = value
            return result
        def constant(value):
            raise ValueError("nonfinite JSON constant")
        state = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeDecodeError) as exc:
        raise CallStateIntegrityError("invalid atomic call_state JSON") from exc
    if not isinstance(state, dict) or type(state.get("active")) is not bool:
        raise CallStateIntegrityError("call_state requires boolean active")
    if not state["active"]:
        if set(state) != {"active"}:
            raise CallStateIntegrityError("inactive call_state has unexpected schema fields")
        return state
    if set(state) != {"active", "scope", "wall_started", "cpu_started"}:
        raise CallStateIntegrityError("active call_state has missing or unexpected schema fields")
    scope = state.get("scope")
    if not isinstance(scope, str) or not scope or len(scope) > 256:
        raise CallStateIntegrityError("active call_state requires a bounded scope")
    for name in ("wall_started", "cpu_started"):
        number = state.get(name)
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            raise CallStateIntegrityError(f"invalid active call_state {name}")
        try:
            finite = math.isfinite(number)
        except (OverflowError, TypeError, ValueError) as exc:
            # JSON integers can be valid bounded bytes yet exceed float range.
            # That is invalid committed clock evidence, not unavailable IO.
            raise CallStateIntegrityError(f"invalid active call_state {name}") from exc
        if not finite:
            raise CallStateIntegrityError(f"invalid active call_state {name}")
    # Read clocks after the atomic record: the child can replace it after the
    # preceding process scan. A vanished child is classified by its wait status.
    now = max(now, time.monotonic())
    if root_pid is not None:
        try:
            proc = _read_process(root_pid, ticks)
            root_cpu = (max(root_cpu, proc.own_cpu) if root_identity is None or proc.identity == root_identity
                        else math.inf)
        except (FileNotFoundError, ProcessLookupError):
            root_cpu = math.inf
    if state["wall_started"] < started or state["wall_started"] > now:
        raise CallStateIntegrityError("call_state wall clock outside child lifetime")
    if state["cpu_started"] < 0 or state["cpu_started"] > root_cpu + POLL_SECONDS + 2.0 / ticks:
        raise CallStateIntegrityError("call_state CPU clock outside observed child lifetime")
    return state


def _poll(child: subprocess.Popen) -> None:
    """Own wait4 so resource usage is from this fresh child, not lifetime max."""
    _remember_root(child, child._worker36_ticks)
    if child.returncode is not None:
        return
    try:
        pid, status, used = os.wait4(child.pid, os.WNOHANG)
    except ChildProcessError as exc:
        raise SupervisionError("child was unexpectedly reaped elsewhere") from exc
    if pid:
        child.returncode = os.waitstatus_to_exitcode(status)
        child._worker36_usage = used


def _signal_owned(owned, root_pid, sig, ticks, on_attempt=None):
    """Pin the kernel target before revalidation; no numeric signal fallback."""
    for proc in owned.values():
        try:
            descriptor = os.pidfd_open(proc.pid, 0)
        except ProcessLookupError:
            continue
        try:
            try:
                current = _read_process(proc.pid, ticks)
            except (FileNotFoundError, ProcessLookupError):
                continue
            if current.identity != proc.identity:
                continue
            if on_attempt is not None:
                on_attempt()
            try:
                signal.pidfd_send_signal(descriptor, sig, None, 0)
            except ProcessLookupError:
                # The pinned process exited; its numeric replacement is untouched.
                pass
        finally:
            os.close(descriptor)


def _reap_adopted(root_pid: int, owned: dict[int, _Process]) -> None:
    for pid, proc in owned.items():
        if pid != root_pid and proc.ppid == os.getpid():
            try:
                os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                pass


def _exception_status(error: BaseException, resource_exceptions: tuple = (), *, before_spawn: bool = False) -> str:
    if isinstance(error, CallStateIntegrityError):
        return "integrity_invalid"
    attached = getattr(error, "worker36_failure", None)
    if isinstance(attached, dict) and attached.get("status") in ("execution_blocked", "execution_incomplete", "resource_incomplete", "integrity_invalid"):
        return attached["status"]
    if isinstance(error, (MemoryError, RecursionError, OutputBudgetExceeded) + resource_exceptions):
        return "resource_incomplete"
    return "execution_blocked" if before_spawn else "execution_incomplete"


def _retain_child_exit(child: subprocess.Popen, result: dict) -> dict | None:
    """Copy already observed wait evidence before any fallible resource work."""
    code = getattr(child, "returncode", None)
    if code is None:
        return None
    result.update(returncode=code, exit_code=code if code >= 0 else None,
                  signal=-code if code < 0 else None)
    if code == 0:
        return {"status": "completed", "reason": "child_exit_zero"}
    if code == -signal.SIGXCPU:
        return {"status": "resource_incomplete", "reason": "kernel_cpu_limit"}
    return {"status": "execution_incomplete",
            "reason": "child_nonzero_exit" if code > 0 else "child_signal"}


def _cleanup(child: subprocess.Popen, ticks: int, tracked: set[tuple[int, int]],
             resource_exceptions: tuple = (), deadline: float | None = None, on_failure: Callable | None = None) -> dict:
    if deadline is None:
        deadline = time.monotonic() + CLEANUP_SECONDS
    escalation = min(time.monotonic() + TERM_GRACE_SECONDS, deadline)
    used_kill = sent_term = False
    errors: list[str] = []
    last_owned: dict[int, _Process] = {}
    failure_details = []

    def remember(error, reason):
        if on_failure is not None:
            on_failure(error, reason)
        if len(failure_details) < 16:
            failure_details.append({"phase": "cleanup", "status": _exception_status(error, resource_exceptions),
                                    "reason": reason, "exception_type": type(error).__name__, "message": str(error)})

    while True:
        try:
            _poll(child)
        except BaseException as exc:
            remember(exc, "cleanup_root_observation_failed")
            errors.append(f"cleanup root: {type(exc).__name__}: {exc}")
        try:
            owned = _cleanup_inventory(child, ticks, tracked)
            last_owned = owned
        except BaseException as exc:
            remember(exc, "cleanup_inventory_failed")
            errors.append(f"cleanup inventory: {type(exc).__name__}: {exc}")
            owned = last_owned
            try:
                if not owned:
                    owned = _retained_partial_identity(child, ticks, tracked)
                    last_owned = owned
                _cleanup_signal(child, owned, signal.SIGKILL, ticks)
            except (ProcessLookupError, FileNotFoundError):
                pass
            except BaseException as targeted_error:
                remember(targeted_error, "cleanup_retained_identity_failed")
                errors.append(f"retained identity: {type(targeted_error).__name__}: {targeted_error}")
        _reap_adopted(child.pid, owned)
        try:
            _poll(child)
        except BaseException as exc:
            remember(exc, "cleanup_root_observation_failed")
            errors.append(f"cleanup root: {type(exc).__name__}: {exc}")
        if not owned and child.returncode is not None:
            return {"complete": not errors, "sigkill_used": used_kill or bool(getattr(child, "_worker36_sigkill_attempted", False)), "remaining_pids": [], "errors": errors, "failure_details": failure_details}
        try:
            if time.monotonic() >= escalation:
                _cleanup_signal(child, owned, signal.SIGKILL, ticks)
                used_kill = used_kill or bool(getattr(child, "_worker36_sigkill_attempted", False))
            elif not sent_term:
                _cleanup_signal(child, owned, signal.SIGTERM, ticks)
                sent_term = True
        except BaseException as exc:
            remember(exc, "cleanup_signal_failed")
            errors.append(f"cleanup signal: {type(exc).__name__}: {exc}")
        if time.monotonic() >= deadline:
            return {"complete": False, "sigkill_used": used_kill or bool(getattr(child, "_worker36_sigkill_attempted", False)),
                    "remaining_pids": sorted(set(owned) | ({child.pid} if child.returncode is None else set())), "errors": errors + ["cleanup deadline exceeded"], "failure_details": failure_details}
        time.sleep(POLL_SECONDS)


def _record_secondary_failure(
    result: dict, *, phase: str, status: str, reason: str,
    error: BaseException | None = None, message: str | None = None, exception_type: str | None = None,
) -> None:
    """Retain a later failure without erasing the primary execution evidence.

    Integrity dominates resource; either dominates infrastructure. Equal-priority
    observations retain the earlier terminal cause. The pre-cleanup primary
    outcome is never changed, including when later preservation prevents success.
    """
    priority = {"completed": 0, "execution_blocked": 1, "execution_incomplete": 1,
                "resource_incomplete": 2, "integrity_invalid": 3}
    if status not in priority or status == "completed":
        raise ValueError("invalid secondary failure status")
    if not isinstance(phase, str) or not phase or not isinstance(reason, str) or not reason:
        raise ValueError("secondary failure phase and reason must be nonempty strings")
    if error is not None:
        inferred = _exception_status(error, before_spawn=status == "execution_blocked")
        if priority[inferred] > priority[status]:
            status = inferred
    failure = {"phase": phase, "status": status, "reason": reason}
    if error is not None:
        failure.update(exception_type=type(error).__name__, message=str(error))
    elif message is not None:
        if not isinstance(message, str):
            raise ValueError("secondary failure message must be a string")
        failure["message"] = message
    if error is None and exception_type is not None:
        if not isinstance(exception_type, str):
            raise ValueError("secondary exception type must be a string")
        failure["exception_type"] = exception_type
    result["secondary_failures"].append(failure)
    if priority[status] > priority[result["status"]]:
        result.update(status=status, reason=reason)



def _allocate_popen():
    """Retain the stdlib instance before its fallible, potentially forking init."""
    child = subprocess.Popen.__new__(subprocess.Popen)
    child.pid = child.returncode = child.stdin = child.stdout = child.stderr = None
    return child


def _initialize_popen(child, *args, **kwargs):
    subprocess.Popen.__init__(child, *args, **kwargs)


def _partial_spawn_owned(processes, baseline, tracked, ticks):
    """Use the same baseline-excluded lineage rules during construction."""
    return _owned_processes(processes, None, tracked, baseline, ticks)


def _cleanup_inventory(child, ticks, tracked):
    identity = _remember_root(child, ticks)
    return _owned_processes(_scan_processes(ticks), identity, tracked,
                            child._worker36_spawn_baseline, ticks)


def _cleanup_signal(child, owned, sig, ticks):
    def attempted():
        if sig == signal.SIGKILL:
            child._worker36_sigkill_attempted = True
    _signal_owned(owned, child.pid, sig, ticks, attempted)


def _retained_partial_identity(child, ticks, tracked):
    """Shared fallback using only retained identities, including known descendants."""
    pid = getattr(child, "pid", None)
    if type(pid) is not int or pid <= 1 or pid == os.getpid():
        return {}
    identity = _remember_root(child, ticks)
    known = set(tracked)
    known.add(identity)
    owned = {}
    for known_pid, start_ticks in known:
        try:
            proc = _read_process(known_pid, ticks)
        except (FileNotFoundError, ProcessLookupError):
            continue
        if proc.identity == (known_pid, start_ticks) and proc.identity not in child._worker36_spawn_baseline:
            owned[known_pid] = proc
    return owned


def _emergency_cleanup_kill(child, ticks, tracked, on_failure=None):
    try:
        owned = _cleanup_inventory(child, ticks, tracked)
    except BaseException as inventory_error:
        try:
            if on_failure is not None:
                on_failure(inventory_error, "emergency_cleanup_inventory_failed")
        finally:
            # Mandatory targeting survives failed bookkeeping. Later typed errors
            # propagate independently of the already retained inventory error.
            owned = {}
            for pid, start_ticks in tracked:
                try:
                    proc = _read_process(pid, ticks)
                except (FileNotFoundError, ProcessLookupError):
                    continue
                if proc.identity == (pid, start_ticks) and proc.identity not in child._worker36_spawn_baseline:
                    owned[pid] = proc
            if not owned:
                try:
                    owned = _retained_partial_identity(child, ticks, tracked)
                except (FileNotFoundError, ProcessLookupError):
                    pass
            _cleanup_signal(child, owned, signal.SIGKILL, ticks)
        raise inventory_error
    _cleanup_signal(child, owned, signal.SIGKILL, ticks)


class _PreservationStopped(BaseException):
    def __init__(self, *, expired, deadline):
        message = "original preservation deadline exhausted" if expired else "preservation transition unconfirmed"
        super().__init__(message)
        self.worker36_preservation_deadline = deadline
        self.worker36_failure = {"status": "resource_incomplete" if expired else "execution_incomplete",
            "category": "resource" if expired else "infrastructure", "phase": "preservation_boundary",
            "error_type": type(self).__name__, "error": message}


class _FailureBoundary:
    """One driver-owned cutoff; unconfirmed attempts never regain authority."""
    def __init__(self, result, callback):
        self.result, self.callback = result, callback
        self.attempted = self.confirmed = self.expired = self.blocked = False
        self.deadline = self.first_failure_monotonic = self.cleanup_deadline = None
        self.resource_exceptions = ()

    def _flags(self):
        self.result.update(preservation_deadline_monotonic=self.deadline,
            preservation_transition_attempted=self.attempted,
            preservation_transition_complete=self.confirmed,
            preservation_expired=self.expired, preservation_blocked=self.blocked)

    def _adopt_exception(self, error):
        attached = getattr(error, "worker36_failure", None)
        supplied = getattr(error, "worker36_preservation_deadline", None)
        if type(supplied) in (int, float) and math.isfinite(supplied) and supplied > 0:
            if self.deadline is None:
                self.deadline = supplied
            elif supplied != self.deadline:
                self.blocked = True
        if isinstance(attached, dict):
            self.result["preservation_boundary_failure"] = dict(attached)
            if not isinstance(error, Exception) and attached.get("status") == "resource_incomplete":
                self.expired = self.blocked = True

    def note_exception(self, error):
        self._adopt_exception(error)
        self._flags()

    def fail_closed(self, error, *, phase="preservation_transition", reason="preservation_bookkeeping_failed"):
        if self.callback is not None:
            self.attempted = True
        self.blocked = True
        try:
            self._adopt_exception(error)
        except BaseException:
            pass
        try:
            self._flags()
        except BaseException:
            self.result["preservation_transition_attempted"] = self.attempted
            self.result["preservation_transition_complete"] = self.confirmed
            self.result["preservation_blocked"] = True
            self.result["preservation_expired"] = self.expired
            self.result["preservation_deadline_monotonic"] = self.deadline
        if self.result.get("reason") is None:
            self.result.update(status=_exception_status(error, self.resource_exceptions), reason=reason)
        self.result.setdefault("primary_outcome", {"status": self.result["status"], "reason": self.result["reason"]})
        try:
            _record_secondary_failure(self.result, phase=phase,
                status=_exception_status(error, self.resource_exceptions), reason=reason, error=error)
        except BaseException:
            if self.result["status"] not in ("integrity_invalid", "resource_incomplete", "execution_blocked"):
                self.result.update(status="execution_incomplete", reason=reason)

    def _first_failure_time(self):
        return time.monotonic()

    def _observation(self, *, phase, status, reason, error):
        observed = {"status": status, "reason": reason, "phase": phase,
            "first_failure_monotonic": self.first_failure_monotonic,
            "returncode": self.result["returncode"], "exit_code": self.result["exit_code"], "signal": self.result["signal"]}
        if "primary_outcome" in self.result:
            observed["primary_outcome"] = dict(self.result["primary_outcome"])
        if error is not None:
            observed.update(exception_type=type(error).__name__, message=str(error))
        return observed

    def start(self, *, phase, status, reason, error=None):
        if self.callback is None:
            return
        if self.attempted:
            if error is not None:
                try:
                    self.note_exception(error)
                except BaseException as exc:
                    self.fail_closed(exc)
            return
        # Publish denial before any fallible clock, note, allocation or callback.
        self.attempted, self.confirmed, self.blocked = True, False, True
        try:
            self._flags()
            if error is not None:
                self.note_exception(error)
            self.first_failure_monotonic = self._first_failure_time()
            self.cleanup_deadline = self.first_failure_monotonic + CLEANUP_SECONDS
            observed = self._observation(phase=phase, status=status, reason=reason, error=error)
            self.result["first_terminal_failure"] = observed
            cutoff = self.callback(dict(observed))
            if type(cutoff) not in (int, float) or not math.isfinite(cutoff) or cutoff <= 0:
                raise SupervisionError("invalid original preservation cutoff")
            if self.deadline is not None and self.deadline != cutoff:
                raise SupervisionError("preservation cutoff changed")
            self.deadline = cutoff
            self.confirmed = True
            self.blocked = self.expired
            self._flags()
            self.permit()
        except BaseException as exc:
            self.fail_closed(exc)

    def permit(self):
        if self.blocked:
            return False
        if self.callback is None or not self.attempted:
            return True
        try:
            if self.deadline is None or not self.confirmed:
                self.blocked = True
            elif time.monotonic() >= self.deadline:
                self.expired = self.blocked = True
            self._flags()
            return self.confirmed and not self.expired and not self.blocked
        except BaseException as exc:
            self.fail_closed(exc)
            return False

    def require(self):
        if not self.permit():
            raise _PreservationStopped(expired=self.expired, deadline=self.deadline)


def run_child(
    command: Sequence[str], env: Mapping[str, str], cwd: Path | str,
    output_log: Path, call_state: Path, phase: PhaseBudget,
    wall_seconds: float = 720, cpu_seconds: float = 720,
    address_space_bytes: int = FROZEN_ADDRESS_SPACE, *,
    call_wall_seconds: float = 360, call_cpu_seconds: float = 360,
    output_log_limit_bytes: int = DEFAULT_LOG_LIMIT,
    expected_inherited_limits: Mapping[str, Sequence[int]] | None = None,
    output_budget_check: Callable | None = None,
    output_budget_exceptions: tuple[type[Exception], ...] = (OutputBudgetExceeded,),
    on_terminal_failure: Callable[[dict], float] | None = None,
) -> dict:
    """Run one fresh serial child, retaining a bounded combined output prefix.

    Smaller time/log budgets are solely for separately authorized helper tests.
    The measurement driver must explicitly supply the exact frozen parameters.
    ``call_state`` must not exist before spawn. Child instrumentation atomically
    replaces it before a call protection scope and deactivates it after capture.
    The default 1 MiB log prefix is a helper default, not a protocol amendment;
    measurement must pass its remaining raw allowance plus a shared-budget guard.
    Output is bounded in parent memory while the child owns raw evidence writes,
    then persisted only after confirmed group cleanup. A parent hard kill can
    lose this buffered log; no durable output is claimed before final fsync.
    output_budget_check(path, bytes) checks buffered growth during execution and
    checks it again after cleanup, when the parent is the sole raw writer. It may
    return a context manager to surround final writes. On a shared-budget cap,
    only the largest fitting raw-log prefix is persisted; its gap is explicit.
    Only declared output_budget_exceptions classify callback failure as a cap.
    primary_outcome retains the pre-cleanup status/reason; secondary_failures
    records later problems without downgrading resource/integrity causes.
    Cleanup output is drained nonblockingly under the original cleanup deadline
    and existing output cap. output_durable describes only the retained prefix;
    output_prefix_gap also flags an unconfirmed pipe tail, not just lost bytes.
    Production supplies on_terminal_failure to arm the one original preservation
    cutoff before failure work. Unconfirmed/expired authority permits only bounded
    mandatory cleanup/restoration. Construction ownership is retained before init;
    narrow recovery excludes every pre-spawn process identity. Counters remain
    lower bounds while ownership or cleanup is unconfirmed.
    """
    began = time.monotonic()
    result = {
        "schema": "worker36.supervision.v1", "status": "execution_blocked",
        "reason": None, "spawned": False, "pid": None, "returncode": None,
        "spawn_attempted": False, "spawn_initialization_complete": False,
        "spawn_ownership_uncertain": False, "spawn_discovery": "not_attempted", "spawn_recovered_pids": [],
        "exit_code": None, "signal": None, "wall_seconds": 0.0,
        "child_cpu_seconds": 0.0, "child_high_water_rss_kib": None,
        "scientific_returns_inferred": False, "output_log": str(output_log),
        "output_bytes_preserved": 0, "output_bytes_observed": 0, "output_overflow": False,
        "output_capture_mode": "bounded_memory_then_post_cleanup_fsync",
        "output_prefix_gap": False, "output_pipe_tail": "unobserved",
        "output_durable": False, "active_call_at_stop": None,
        "cleanup": {"complete": True, "sigkill_used": False, "remaining_pids": [], "errors": []},
        "poll_seconds": POLL_SECONDS, "errors": [], "secondary_failures": [],
        "child_accounting_complete": False, "phase_accounting_complete": False,
    }
    boundary = _FailureBoundary(result, on_terminal_failure)
    boundary._flags()
    child = log_fd = selector = old_subreaper = None
    tracked: set[tuple[int, int]] = set()
    ticks = 0
    child_reaped_baseline = None
    declared_resource_types = ()
    seen_scopes: dict[str, tuple[float, float]] = {}
    phase_claimed = pipe_eof = False
    state_seen = False
    root_cpu_last = 0.0
    output_buffer = bytearray()

    cleanup_deadline = None
    spawn_baseline = frozenset()

    def valid_child_pid():
        pid = getattr(child, "pid", None)
        return pid if type(pid) is int and pid > 1 and pid != os.getpid() else None

    def observe_spawn():
        pid = valid_child_pid()
        if pid is not None:
            result.update(spawned=True, pid=pid)
            if not result["spawn_initialization_complete"] and result["spawn_discovery"] != "recovered_direct_child":
                result["spawn_discovery"] = "retained_pid"
            result["spawn_ownership_uncertain"] = (
                getattr(child, "_worker36_root_identity", None) is None
                or getattr(child, "_worker36_ownership_uncertain", True))
        return pid

    def record_secondary(*args, **kwargs):
        try:
            boundary.start(phase=kwargs["phase"], status=kwargs["status"], reason=kwargs["reason"], error=kwargs.get("error"))
        except BaseException as exc:
            boundary.fail_closed(exc)
        try:
            _record_secondary_failure(*args, **kwargs)
        except BaseException as exc:
            boundary.fail_closed(exc, phase="failure_recording", reason="secondary_recording_failed")

    def cleanup_failure(error, reason):
        try:
            boundary.start(phase="cleanup", status=_exception_status(error, declared_resource_types), reason=reason, error=error)
        except BaseException as exc:
            boundary.fail_closed(exc)

    def recover_partial_spawn():
        if result["spawn_initialization_complete"]:
            return True
        if not result["spawn_attempted"]:
            return False
        result["cleanup"] = {"complete": False, "sigkill_used": False, "remaining_pids": [],
            "errors": ["partial spawn ownership is unconfirmed"], "failure_details": []}
        if observe_spawn() is not None:
            return True
        result.update(spawn_ownership_uncertain=True, spawn_discovery="unavailable",
                      output_prefix_gap=True, output_pipe_tail="spawn_ownership_unconfirmed")
        try:
            owned = _partial_spawn_owned(_scan_processes(ticks), spawn_baseline, tracked, ticks)
            if not owned:
                result.update(spawn_ownership_uncertain=False, spawn_discovery="no_owned_child_observed",
                              output_pipe_tail="no_owned_child_observed")
                result["cleanup"] = {"complete": True, "sigkill_used": False, "remaining_pids": [], "errors": [], "failure_details": []}
                return False
            recovered = sorted(owned)
            direct = sorted(pid for pid, proc in owned.items() if proc.ppid == os.getpid())
            if not direct:
                _cleanup_signal(child, owned, signal.SIGKILL, ticks)
                raise SupervisionError("partial spawn has no currently waitable direct child")
            child.pid, child.returncode = direct[0], None
            child._worker36_root_identity = owned[child.pid].identity
            child._worker36_ownership_uncertain = False
            result.update(spawned=True, pid=child.pid, spawn_ownership_uncertain=False,
                          spawn_discovery="recovered_direct_child", spawn_recovered_pids=recovered)
            return True
        except BaseException as exc:
            record_secondary(result, phase="cleanup", status=_exception_status(exc, declared_resource_types),
                             reason="partial_spawn_discovery_failed", error=exc)
            record_secondary(result, phase="cleanup", status="execution_incomplete",
                             reason="process_cleanup_unconfirmed", message="partial spawn ownership is unknown")
            result["cleanup"]["errors"].append(f"ownership discovery: {type(exc).__name__}: {exc}")
            return False

    @contextmanager
    def budget_guard(size):
        boundary.require()
        guard = output_budget_check(output_log, size) if output_budget_check is not None else None
        boundary.require()
        with guard if guard is not None else nullcontext():
            boundary.require()
            yield
            boundary.require()

    def check_buffer_budget(size):
        with budget_guard(size):
            pass

    def drain_after_cleanup(deadline):
        nonlocal pipe_eof
        if pipe_eof:
            return
        if not boundary.permit():
            result.update(output_pipe_tail="preservation_stopped", output_prefix_gap=True)
            return
        if not result["cleanup"]["complete"]:
            result["output_pipe_tail"] = "cleanup_unconfirmed"
            result["output_prefix_gap"] = True
            return
        try:
            if deadline is None or time.monotonic() >= deadline:
                result["output_pipe_tail"] = "cleanup_deadline_exhausted"
                result["output_prefix_gap"] = True
                record_secondary(result, phase="post_cleanup_output", status="execution_incomplete",
                                          reason="output_tail_cleanup_deadline")
                return
            # Setup can fail before the running-loop nonblocking configuration.
            os.set_blocking(child.stdout.fileno(), False)
            while True:
                boundary.require()
                if time.monotonic() >= deadline:
                    result["output_pipe_tail"] = "cleanup_deadline_exhausted"
                    result["output_prefix_gap"] = True
                    record_secondary(result, phase="post_cleanup_output", status="execution_incomplete",
                                              reason="output_tail_cleanup_deadline")
                    return
                remaining = output_log_limit_bytes - len(output_buffer)
                try:
                    # One byte beyond capacity is sufficient overflow evidence;
                    # never drain/discard an unbounded tail or allocate a new cap.
                    data = os.read(child.stdout.fileno(), min(65536, remaining + 1))
                except BlockingIOError:
                    result["output_pipe_tail"] = "read_unavailable"
                    result["output_prefix_gap"] = True
                    record_secondary(result, phase="post_cleanup_output", status="execution_incomplete",
                                              reason="output_tail_unconfirmed")
                    return
                if not data:
                    pipe_eof = True
                    result["output_pipe_tail"] = "eof_observed"
                    return
                result["output_bytes_observed"] += len(data)
                output_buffer.extend(data[:remaining])
                if len(data) > remaining:
                    result["output_overflow"] = True
                    result["output_prefix_gap"] = True
                    result["output_pipe_tail"] = "output_cap_reached"
                    record_secondary(result, phase="post_cleanup_output", status="resource_incomplete",
                                              reason="output_log_limit")
                    return
                check_buffer_budget(len(output_buffer))
        except output_budget_exceptions as exc:
            result["output_overflow"] = True
            result["output_prefix_gap"] = True
            result["output_pipe_tail"] = "shared_output_budget_limit"
            record_secondary(result, phase="post_cleanup_output", status="resource_incomplete",
                                      reason="shared_output_budget_limit", error=exc)
        except BaseException as exc:
            result["output_prefix_gap"] = True
            result["output_pipe_tail"] = "drain_failed"
            record_secondary(result, phase="post_cleanup_output", status=_exception_status(exc, declared_resource_types),
                                      reason="output_tail_drain_failed", error=exc)

    def guarded_stage(phase_name, reason, action):
        try:
            return action()
        except BaseException as exc:
            try:
                boundary.fail_closed(exc, phase=phase_name, reason=reason)
            except BaseException:
                # Nested finally ownership below reaches all remaining mandatory
                # stages even if failure bookkeeping itself fails.
                boundary.attempted = on_terminal_failure is not None or boundary.attempted
                boundary.blocked = True
                result["preservation_transition_attempted"] = boundary.attempted
                result["preservation_transition_complete"] = boundary.confirmed
                result["preservation_blocked"] = True
                if result["status"] not in ("integrity_invalid", "resource_incomplete", "execution_blocked"):
                    result.update(status="execution_incomplete", reason=reason)

    def prepare_teardown():
        pending = sys.exc_info()[1]
        if pending is not None:
            boundary.fail_closed(pending, phase="teardown", reason="failure_bookkeeping_interrupted")
        result.setdefault("primary_outcome", {"status": result["status"], "reason": result["reason"]})
        if result["status"] != "completed" and result["reason"] is not None:
            boundary.start(phase="supervision", status=result["status"], reason=result["reason"])

    def cleanup_child():
        nonlocal cleanup_deadline
        if child is None or not result["spawn_attempted"]:
            return
        try:
            if cleanup_deadline is None:
                if boundary.cleanup_deadline is not None:
                    cleanup_deadline = boundary.cleanup_deadline
                elif boundary.blocked or (boundary.attempted and not boundary.confirmed):
                    cleanup_deadline = began
                else:
                    cleanup_deadline = time.monotonic() + CLEANUP_SECONDS
        except BaseException as exc:
            cleanup_deadline = began
            boundary.fail_closed(exc, phase="cleanup", reason="cleanup_deadline_unavailable")
        finally:
            if cleanup_deadline is None:
                cleanup_deadline = began
            try:
                if not recover_partial_spawn():
                    return
                result["cleanup"] = _cleanup(child, ticks, tracked, declared_resource_types, cleanup_deadline, cleanup_failure)
            except BaseException as exc:
                try:
                    result["cleanup"] = {"complete": False, "sigkill_used": False,
                        "remaining_pids": [child.pid] if valid_child_pid() is not None else [],
                        "errors": [f"{type(exc).__name__}: {exc}"]}
                    record_secondary(result, phase="cleanup", status=_exception_status(exc, declared_resource_types),
                                     reason="cleanup_exception", error=exc)
                finally:
                    try:
                        try:
                            _emergency_cleanup_kill(child, ticks, tracked,
                                lambda error, reason: record_secondary(result, phase="cleanup",
                                    status=_exception_status(error, declared_resource_types), reason=reason, error=error))
                        except ProcessLookupError:
                            pass
                        except BaseException as kill_error:
                            result["cleanup"]["errors"].append(f"emergency owned kill: {type(kill_error).__name__}: {kill_error}")
                            record_secondary(result, phase="cleanup", status=_exception_status(kill_error, declared_resource_types),
                                             reason="emergency_group_kill_failed", error=kill_error)
                    finally:
                        try:
                            if valid_child_pid() is not None or recover_partial_spawn():
                                result["cleanup"] = _cleanup(child, ticks, tracked, declared_resource_types, cleanup_deadline, cleanup_failure)
                        except BaseException as retry_error:
                            result["cleanup"]["errors"].append(f"cleanup recovery: {type(retry_error).__name__}: {retry_error}")
                            record_secondary(result, phase="cleanup", status=_exception_status(retry_error, declared_resource_types),
                                             reason="cleanup_recovery_failed", error=retry_error)

    def after_child_cleanup():
        if child is None or valid_child_pid() is None:
            return
        observe_spawn()
        _retain_child_exit(child, result)
        if boundary.permit():
            try:
                boundary.require()
                result["wall_seconds"] = time.monotonic() - began
                if child_reaped_baseline is not None:
                    result["child_cpu_seconds"] = max(result["child_cpu_seconds"], max(0.0, _usage(resource.RUSAGE_CHILDREN) - child_reaped_baseline))
                if hasattr(child, "_worker36_usage"):
                    result["child_high_water_rss_kib"] = child._worker36_usage.ru_maxrss
                boundary.require()
                result["child_accounting_complete"] = (result["cleanup"].get("complete") is True
                    and result["spawn_ownership_uncertain"] is False and result["returncode"] is not None)
            except BaseException as exc:
                record_secondary(result, phase="final_accounting", status=_exception_status(exc, declared_resource_types),
                                 reason="child_accounting_failed", error=exc)
        for failure in result["cleanup"].get("failure_details", []):
            record_secondary(result, **failure)
        if not result["cleanup"]["complete"]:
            record_secondary(result, phase="cleanup", status="execution_incomplete", reason="process_cleanup_unconfirmed",
                             message="; ".join(result["cleanup"]["errors"]))
        if child.stdout is not None and not child.stdout.closed:
            drain_after_cleanup(cleanup_deadline)
        elif result["spawned"] and not pipe_eof:
            result.update(output_prefix_gap=True, output_pipe_tail="closed_during_initialization")

    def close_stdout():
        if child is not None and getattr(child, "stdout", None) is not None:
            try:
                child.stdout.close()
            except BaseException as exc:
                record_secondary(result, phase="cleanup", status=_exception_status(exc, declared_resource_types),
                                 reason="stdout_close_failed", error=exc)
                result["errors"].append(f"stdout close: {type(exc).__name__}: {exc}")

    def close_selector():
        if selector is not None:
            try:
                selector.close()
            except BaseException as exc:
                record_secondary(result, phase="cleanup", status=_exception_status(exc, declared_resource_types),
                                 reason="selector_close_failed", error=exc)
                result["errors"].append(f"selector close: {type(exc).__name__}: {exc}")

    def persist_log():
        if log_fd is None:
            return
        try:
            if result["cleanup"]["complete"] and boundary.permit():
                boundary.require()
                fitting = len(output_buffer)
                try:
                    check_buffer_budget(fitting)
                except output_budget_exceptions as exc:
                    result["output_overflow"] = True
                    record_secondary(result, phase="log_persistence", status="resource_incomplete",
                                     reason="shared_output_budget_limit", error=exc)
                    result["errors"].append(f"final shared output budget: {type(exc).__name__}: {exc}")
                    low, high = 0, fitting
                    while low < high:
                        boundary.require()
                        middle = (low + high + 1) // 2
                        try:
                            check_buffer_budget(middle)
                        except output_budget_exceptions:
                            high = middle - 1
                        else:
                            low = middle
                    fitting = low
                if fitting:
                    with budget_guard(fitting):
                        view = memoryview(output_buffer)[:fitting]
                        while view:
                            boundary.require()
                            wrote = os.write(log_fd, view)
                            if wrote <= 0:
                                raise OSError("output log write made no progress")
                            result["output_bytes_preserved"] += wrote
                            boundary.require()
                            view = view[wrote:]
                boundary.require()
                os.fsync(log_fd)
                boundary.require()
                result["output_durable"] = True
            result["output_prefix_gap"] = (result["output_prefix_gap"] or
                result["output_bytes_preserved"] < result["output_bytes_observed"] or
                (result["spawned"] and not pipe_eof))
        except BaseException as exc:
            result["output_prefix_gap"] = True
            record_secondary(result, phase="log_persistence", status=_exception_status(exc, declared_resource_types),
                             reason="output_log_preservation_failed", error=exc)
            result["errors"].append(f"log preservation: {type(exc).__name__}: {exc}")
            if boundary.permit():
                try:
                    boundary.require()
                    os.fsync(log_fd)
                    boundary.require()
                except BaseException as fsync_error:
                    record_secondary(result, phase="log_persistence", status=_exception_status(fsync_error, declared_resource_types),
                                     reason="output_log_fsync_failed", error=fsync_error)

    def close_log():
        if log_fd is not None:
            try:
                os.close(log_fd)
            except BaseException as exc:
                record_secondary(result, phase="log_persistence", status=_exception_status(exc, declared_resource_types),
                                 reason="output_log_close_failed", error=exc)

    def restore_subreaper():
        if old_subreaper is not None:
            try:
                _subreaper(False, old_subreaper)
            except BaseException as exc:
                record_secondary(result, phase="subreaper_restoration", status=_exception_status(exc, declared_resource_types),
                                 reason="subreaper_restoration_failed", error=exc)
                result["errors"].append(f"subreaper restoration: {type(exc).__name__}: {exc}")

    def final_accounting():
        if isinstance(phase, PhaseBudget) and boundary.permit():
            try:
                boundary.require()
                result["phase"] = phase.snapshot()
                final_limit = phase.exhausted(result["phase"])
                boundary.require()
                result["phase_accounting_complete"] = (result["cleanup"].get("complete") is True
                    and result["spawn_ownership_uncertain"] is False)
                if result["status"] == "completed" and final_limit:
                    record_secondary(result, phase="final_budget", status="resource_incomplete", reason=final_limit)
            except BaseException as exc:
                record_secondary(result, phase="final_accounting", status=_exception_status(exc, declared_resource_types),
                                 reason="phase_accounting_failed", error=exc)
        if child is not None and boundary.permit():
            try:
                result["wall_seconds"] = time.monotonic() - began
                if result["status"] == "completed" and result["wall_seconds"] >= wall_seconds:
                    record_secondary(result, phase="final_budget", status="resource_incomplete", reason="cell_wall_limit")
            except BaseException as exc:
                record_secondary(result, phase="final_accounting", status=_exception_status(exc, declared_resource_types),
                                 reason="wall_accounting_failed", error=exc)

    def reset_phase():
        if phase_claimed:
            phase._running = False

    try:
        try:
            if on_terminal_failure is not None and not callable(on_terminal_failure):
                raise SupervisionError("on_terminal_failure must be callable")
            wall_seconds = _positive(wall_seconds, "wall_seconds")
            cpu_seconds = _positive(cpu_seconds, "cpu_seconds")
            call_wall_seconds = _positive(call_wall_seconds, "call_wall_seconds")
            call_cpu_seconds = _positive(call_cpu_seconds, "call_cpu_seconds")
            if type(address_space_bytes) is not int or address_space_bytes != FROZEN_ADDRESS_SPACE:
                raise SupervisionError("address_space_bytes must be exactly 512 MiB")
            if type(output_log_limit_bytes) is not int or not 0 < output_log_limit_bytes <= 64 * 1024 * 1024:
                raise SupervisionError("output log limit must be a positive integer at most 64 MiB")
            if output_budget_check is not None and not callable(output_budget_check):
                raise SupervisionError("output_budget_check must be callable")
            if (not isinstance(output_budget_exceptions, tuple) or
                    any(not isinstance(cls, type) or not issubclass(cls, Exception) for cls in output_budget_exceptions)):
                raise SupervisionError("output_budget_exceptions must contain exception classes")
            declared_resource_types = output_budget_exceptions
            boundary.resource_exceptions = declared_resource_types
            if not isinstance(phase, PhaseBudget) or phase._running:
                raise SupervisionError("a dedicated, inactive PhaseBudget is required")
            if not command or isinstance(command, (str, bytes)) or any(not isinstance(x, str) or not x for x in command):
                raise SupervisionError("command must contain executable and string arguments")
            if not isinstance(env, Mapping) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in env.items()):
                raise SupervisionError("an explicit string environment is required")
            if sys.platform != "linux":
                raise SupervisionError("independent supervision requires Linux")
            _require_pidfd_support()
            ticks = os.sysconf("SC_CLK_TCK")
            if not isinstance(ticks, int) or ticks <= 0:
                raise SupervisionError("Linux process CPU tick frequency unavailable")
            if len(list(Path("/proc/self/task").iterdir())) != 1:
                raise SupervisionError("supervisor must be single-threaded")
            processes = _scan_processes(ticks)
            if os.getpid() not in processes:
                raise SupervisionError("supervisor proc accounting unavailable")
            if any(proc.ppid == os.getpid() for proc in processes.values()):
                raise SupervisionError("serial supervisor has pre-existing children")
            spawn_baseline = frozenset(proc.identity for proc in processes.values())
            result["inherited_limits"] = _inherited_limits()
            if expected_inherited_limits is not None:
                expected = {name: list(pair) for name, pair in expected_inherited_limits.items()}
                if expected != result["inherited_limits"]:
                    raise SupervisionError("inherited limits differ from exact admission baseline")
            result["cpu_tick_seconds"] = 1.0 / ticks
            output_log = Path(output_log).absolute()
            call_state = Path(call_state).absolute()
            cwd = Path(cwd).resolve(strict=True)
            if not cwd.is_dir():
                raise SupervisionError("cwd is not a directory")
            for path in (output_log, call_state):
                if path.exists() or path.is_symlink():
                    raise SupervisionError(f"pre-existing evidence path: {path}")
                if path.parent.resolve(strict=True) != path.parent:
                    raise SupervisionError("evidence parent path may not contain symlinks")
            if output_log == call_state:
                raise SupervisionError("output_log and call_state must be distinct")
            result["phase"] = phase.snapshot()
            reason = phase.exhausted(result["phase"])
            if reason:
                raise SupervisionError(f"{reason}_before_spawn")
            old_subreaper = _subreaper(True)
            _subreaper(False, 1)
            if _subreaper(True) != 1:
                raise SupervisionError("Linux child subreaper verification failed")
            phase._running = True
            phase_claimed = True
            log_fd = os.open(output_log, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            os.fsync(log_fd)
            parent_fd = os.open(output_log.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)

            coordinator_pid = os.getpid()

            def set_limits() -> None:
                _arm_parent_death_signal(coordinator_pid)
                if _inherited_limits() != result["inherited_limits"]:
                    raise SupervisionError("inherited limits changed before child setup")
                resource.setrlimit(resource.RLIMIT_AS, (address_space_bytes, address_space_bytes))
                kernel_cpu = math.ceil(cpu_seconds)
                resource.setrlimit(resource.RLIMIT_CPU, (kernel_cpu, kernel_cpu))
                if resource.getrlimit(resource.RLIMIT_AS) != (address_space_bytes, address_space_bytes):
                    raise SupervisionError("exact child RLIMIT_AS was not installed")
                if resource.getrlimit(resource.RLIMIT_CPU) != (kernel_cpu, kernel_cpu):
                    raise SupervisionError("child CPU backstop was not installed")

            child_reaped_baseline = _usage(resource.RUSAGE_CHILDREN)
            began = time.monotonic()
            child = _allocate_popen()
            child._worker36_spawn_baseline = spawn_baseline
            child._worker36_tracked = tracked
            child._worker36_ticks = ticks
            child._worker36_root_identity = None
            child._worker36_ownership_uncertain = True
            child._worker36_partial_spawn = True
            result.update(spawn_attempted=True, spawned=None, spawn_ownership_uncertain=True, spawn_discovery="initializing")
            _initialize_popen(child,
                list(command), cwd=cwd, env=dict(env), stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True,
                start_new_session=True, preexec_fn=set_limits,
            )
            result.update(spawn_initialization_complete=True, spawn_discovery="not_required")
            _remember_root(child, ticks)
            result["spawn_ownership_uncertain"] = False
            child._worker36_partial_spawn = False
            result.update(status="execution_incomplete", spawned=True, pid=child.pid,
                          parent_death_signal=int(signal.SIGKILL), parent_pid=coordinator_pid)
            assert child.stdout is not None
            os.set_blocking(child.stdout.fileno(), False)
            selector = selectors.DefaultSelector()
            selector.register(child.stdout, selectors.EVENT_READ)
            while True:
                _poll(child)
                observed_exit = _retain_child_exit(child, result)
                if observed_exit is not None and child.returncode != 0 and result["reason"] is None:
                    result.update(observed_exit)
                    result.setdefault("primary_outcome", dict(observed_exit))
                    boundary.start(phase="child_exit", **observed_exit)
                boundary.require()
                processes = _scan_processes(ticks)
                owned = _owned_processes(processes, child._worker36_root_identity, tracked, spawn_baseline, ticks)
                live_cpu = sum(proc.own_cpu + proc.waited_cpu for proc in owned.values())
                reaped = max(0.0, _usage(resource.RUSAGE_CHILDREN) - child_reaped_baseline)
                total_cpu = live_cpu + reaped
                result["child_cpu_seconds"] = max(result["child_cpu_seconds"], total_cpu)
                root = owned.get(child.pid)
                if root is not None:
                    root_cpu_last = max(root_cpu_last, root.own_cpu)
                elif hasattr(child, "_worker36_usage"):
                    used = child._worker36_usage
                    root_cpu_last = max(root_cpu_last, used.ru_utime + used.ru_stime)
                result["wall_seconds"] = time.monotonic() - began
                result["phase"] = phase.snapshot(live_cpu)
                boundary.require()
                state = _call_state(call_state, time.monotonic(), root_cpu_last, began, ticks, child.pid,
                                    child._worker36_root_identity)
                if state is None and state_seen:
                    raise SupervisionError("call_state disappeared after first atomic record")
                state_seen = state_seen or state is not None
                if state and state["active"]:
                    stamp = (state["wall_started"], state["cpu_started"])
                    previous = seen_scopes.setdefault(state["scope"], stamp)
                    if previous != stamp:
                        raise CallStateIntegrityError("active scope start clocks changed")
                    result["active_call_at_stop"] = dict(state)
                else:
                    result["active_call_at_stop"] = None
                try:
                    if output_buffer:
                        check_buffer_budget(len(output_buffer))
                except output_budget_exceptions as exc:
                    result["errors"].append(f"shared output budget: {type(exc).__name__}: {exc}")
                    result.update(status="resource_incomplete", reason="shared_output_budget_limit", output_overflow=True)
                    break
                reason = phase.exhausted(result["phase"])
                if reason is None and result["wall_seconds"] >= wall_seconds:
                    reason = "cell_wall_limit"
                if reason is None and total_cpu >= cpu_seconds:
                    reason = "cell_cpu_limit"
                if reason is None and state and state["active"]:
                    if time.monotonic() - state["wall_started"] >= call_wall_seconds:
                        reason = "call_wall_limit"
                    elif total_cpu - state["cpu_started"] >= call_cpu_seconds:
                        reason = "call_cpu_limit"
                if reason:
                    result.update(status="resource_incomplete", reason=reason)
                    break
                # A bounded drain pass prevents flooding from starving limit checks.
                for key, _ in selector.select(POLL_SECONDS if child.returncode is None else 0):
                    try:
                        data = os.read(key.fd, 65536)
                    except BlockingIOError:
                        continue
                    if not data:
                        selector.unregister(key.fileobj)
                        pipe_eof = True
                        result["output_pipe_tail"] = "eof_observed"
                        continue
                    result["output_bytes_observed"] += len(data)
                    remaining = output_log_limit_bytes - len(output_buffer)
                    output_buffer.extend(data[:remaining])
                    try:
                        check_buffer_budget(len(output_buffer))
                    except output_budget_exceptions as exc:
                        result["errors"].append(f"shared output budget: {type(exc).__name__}: {exc}")
                        result.update(status="resource_incomplete", reason="shared_output_budget_limit", output_overflow=True)
                        break
                    if len(data) > remaining:
                        result.update(status="resource_incomplete", reason="output_log_limit", output_overflow=True)
                        break
                if result["reason"] in ("output_log_limit", "shared_output_budget_limit"):
                    break
                if child.returncode is not None:
                    descendants = [proc.pid for proc in owned.values() if proc.pid != child.pid]
                    if descendants:
                        result.update(status="execution_incomplete", reason="descendants_survived_child")
                        break
                    if pipe_eof:
                        if child.returncode == 0:
                            if state and state["active"]:
                                result.update(status="execution_incomplete", reason="child_exited_with_active_call")
                            else:
                                result.update(status="completed", reason="child_exit_zero")
                        elif child.returncode == -signal.SIGXCPU:
                            result.update(status="resource_incomplete", reason="kernel_cpu_limit")
                        else:
                            result.update(status="execution_incomplete", reason="child_nonzero_exit" if child.returncode > 0 else "child_signal")
                        break
        except BaseException as exc:
            observe_spawn()
            observed_exit = _retain_child_exit(child, result) if child is not None else None
            failure_status = _exception_status(exc, declared_resource_types, before_spawn=not result["spawn_attempted"])
            if result["reason"] is not None or observed_exit is not None:
                if result["reason"] is None:
                    result.update(observed_exit)
                result.setdefault("primary_outcome", {"status": result["status"], "reason": result["reason"]})
                record_secondary(result, phase="supervision", status=failure_status, reason=f"supervision_{type(exc).__name__}", error=exc)
            else:
                result.update(status=failure_status, reason=f"supervision_{type(exc).__name__}")
                result["primary_outcome"] = {"status": failure_status, "reason": result["reason"],
                    "exception_type": type(exc).__name__, "message": str(exc)}
                boundary.start(phase="supervision", status=failure_status, reason=result["reason"], error=exc)
            result["errors"].append(f"{type(exc).__name__}: {exc}")
        finally:
            try:
                guarded_stage("teardown", "teardown_entry_failed", prepare_teardown)
            finally:
                try:
                    guarded_stage("cleanup", "cleanup_stage_failed", cleanup_child)
                finally:
                    try:
                        guarded_stage("final_accounting", "post_cleanup_bookkeeping_failed", after_child_cleanup)
                    finally:
                        try:
                            guarded_stage("cleanup", "stdout_close_stage_failed", close_stdout)
                        finally:
                            try:
                                guarded_stage("cleanup", "selector_close_stage_failed", close_selector)
                            finally:
                                try:
                                    guarded_stage("log_persistence", "log_persistence_stage_failed", persist_log)
                                finally:
                                    try:
                                        guarded_stage("log_persistence", "log_close_stage_failed", close_log)
                                    finally:
                                        try:
                                            guarded_stage("subreaper_restoration", "subreaper_stage_failed", restore_subreaper)
                                        finally:
                                            guarded_stage("cleanup", "phase_reset_failed", reset_phase)
            guarded_stage("final_accounting", "final_accounting_stage_failed", final_accounting)
    except BaseException as exc:
        guarded_stage("teardown", "supervisor_teardown_interrupted",
                      lambda: boundary.fail_closed(exc, phase="teardown", reason="supervisor_teardown_interrupted"))
    finally:
        if phase_claimed:
            phase._running = False
    return result
