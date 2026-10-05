"""Closed shared startup runtime extracted from the accepted Worker37 leaf.

No consumer imports policy code. The two fixed consumer names select only the
shell observation prefix; resource, loader and idle-state requirements are shared.
"""
import gc
import hashlib
import os
import resource
import signal
import stat
import sys
import threading

MEMORY = 536870912
MAX_INPUT = 2097152
EXECUTABLE_SHA256 = "a15ccdaf07655a8667a3687b13171486c9a265d92273ba3ad820fbb64d2cfecc"
LIBRARY_SHA256 = "ba4450817186fbe1e3c477f6aefeee7c353cba3593cc9950382ad9d1f5e62896"
LIBRARY_SIZE = 23041360
FLAGS = {"optimize": 0, "ignore_environment": 0, "isolated": 0,
         "no_site": 0, "no_user_site": 1, "dont_write_bytecode": 1}
CONSUMERS = {"worker37-preparation-v1": "WORKER37_",
             "worker38-synthetic-profile-v1": "WORKER38_"}

class RuntimeFailure(Exception):
    """Only fixed local codes, never remote text or paths, enter diagnostics."""

    def __init__(self, classification, code):
        self.classification = classification
        self.code = code
        self.secondary_failures = []
        super().__init__(code)


def require(condition, code, classification="integrity_invalid"):
    if not condition:
        raise RuntimeFailure(classification, code)


def close_descriptor(fd, operation, record=None, *, pending=None):
    """Close once, retaining an active body/resource error if cleanup also fails."""
    failure = None
    try:
        os.close(fd)
    except MemoryError:
        failure = RuntimeFailure("resource_incomplete", "descriptor_close_memory_exhausted")
    except Exception:
        failure = RuntimeFailure("evidence_incomplete", "descriptor_close_failed")
    if record is not None:
        record["close_confirmed"] = failure is None
    if failure is not None:
        detail = {"classification": failure.classification, "code": failure.code,
                  "operation": operation}
        if record is not None:
            record["close_failure"] = detail
        if pending is None:
            raise failure from None
        previous = getattr(pending, "_bootstrap_cleanup_failures", ())
        pending._bootstrap_cleanup_failures = [*previous, detail]
        if isinstance(pending, RuntimeFailure):
            pending.secondary_failures = pending._bootstrap_cleanup_failures


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def bounded_read(path, cap):
    """No following final symlinks, unbounded read, or executable interpretation."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode), "not_regular_file")
        require(before.st_size <= cap, "local_file_cap", "resource_incomplete")
        pieces = []
        received = 0
        while True:
            part = os.read(fd, min(65536, cap + 1 - received))
            if not part:
                break
            pieces.append(part)
            received += len(part)
            require(received <= cap, "local_file_cap", "resource_incomplete")
        after = os.fstat(fd)
        require(file_tuple(before) == file_tuple(after) and received == after.st_size,
                "local_file_changed")
        return b"".join(pieces)
    finally:
        close_descriptor(fd, "bounded_read", pending=sys.exc_info()[1])


def file_tuple(value):
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)


def shell_stat(value):
    return ":".join(map(str, (value.st_dev, value.st_ino, value.st_size, int(value.st_mtime))))


def limits_snapshot():
    return {name: list(resource.getrlimit(getattr(resource, name)))
            for name in sorted(dir(resource)) if name.startswith("RLIMIT_")}


def state_snapshot():
    return {
        "limits": limits_snapshot(),
        "gc_enabled": gc.isenabled(),
        "gc_threshold": list(gc.get_threshold()),
        "profile_idle": sys.getprofile() is None,
        "trace_idle": sys.gettrace() is None,
        "threads": threading.active_count(),
        "timers": [list(signal.getitimer(timer)) for timer in
                   (signal.ITIMER_REAL, signal.ITIMER_VIRTUAL, signal.ITIMER_PROF)],
    }


def runtime_start(observation, consumer):
    """Install the one process-lifetime cap; never weaken a limit or clear hooks."""
    require(type(consumer) is str and consumer in CONSUMERS,
            "unknown_consumer", "execution_blocked")
    prefix = CONSUMERS[consumer]
    inherited = limits_snapshot()
    observation["inherited_limits"] = inherited
    observation["memory_cap"] = {"attempted": False, "confirmed": False}
    current = inherited["RLIMIT_AS"]
    require(all(value == resource.RLIM_INFINITY or value >= MEMORY for value in current),
            "inherited_address_space", "execution_blocked")
    try:
        observation["memory_cap"]["attempted"] = True
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY, MEMORY))
    except (OSError, ValueError):
        raise RuntimeFailure("execution_blocked", "memory_cap_install") from None
    observation["memory_cap"]["readback"] = list(resource.getrlimit(resource.RLIMIT_AS))
    require(observation["memory_cap"]["readback"] == [MEMORY, MEMORY],
            "memory_cap_readback", "execution_blocked")
    observation["memory_cap"]["confirmed"] = True
    observation["implementation"] = sys.implementation.name
    observation["version"] = ".".join(map(str, sys.version_info[:3]))
    require(sys.implementation.name == "cpython" and tuple(sys.version_info[:3]) == (3, 11, 16),
            "python_version", "execution_blocked")
    observation["flags"] = {name: getattr(sys.flags, name) for name in FLAGS}
    require(observation["flags"] == FLAGS,
            "python_flags", "execution_blocked")
    python_env = {key: value for key, value in os.environ.items() if key.startswith("PYTHON")}
    require(python_env == {"PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"},
            "python_environment", "execution_blocked")
    state = state_snapshot()
    observation["state"] = state
    require(state["gc_enabled"] and state["gc_threshold"] == [700, 10, 10],
            "gc_state", "execution_blocked")
    require(state["profile_idle"] and state["trace_idle"] and state["threads"] == 1
            and state["timers"] == [[0.0, 0.0]] * 3,
            "occupied_runtime_state", "execution_blocked")
    executable = os.environ.get(prefix + "EXECUTABLE", "")
    library = os.environ.get(prefix + "LIBRARY", "")
    cache = os.environ.get("RUNNER_TOOL_CACHE", "")
    require(cache.startswith("/") and os.path.realpath(cache) == cache,
            "runtime_cache_path", "execution_blocked")
    require(executable == cache + "/Python/3.11.16/x64/bin/python3.11"
            and library == cache + "/Python/3.11.16/x64/lib/libpython3.11.so.1.0",
            "runtime_fixed_paths", "execution_blocked")
    require(sys.executable == executable and os.readlink("/proc/self/exe") == executable,
            "mapped_executable")
    loader_env = {key: value for key, value in os.environ.items() if key.startswith("LD")}
    require(loader_env == {"LD_LIBRARY_PATH": os.path.dirname(library)},
            "loader_environment", "execution_blocked")
    files = {}
    observation["files"] = files
    for name, path, expected_hash, expected_size in (
        ("executable", executable, EXECUTABLE_SHA256, None),
        ("library", library, LIBRARY_SHA256, LIBRARY_SIZE),
    ):
        require(os.path.realpath(path) == path and not os.path.islink(path), "loader_symlink")
        before = os.stat(path, follow_symlinks=False)
        raw = bounded_read(path, 64 * 1024 * 1024)
        after = os.stat(path, follow_symlinks=False)
        require(file_tuple(before) == file_tuple(after), "loader_changed")
        actual_hash = sha(raw)
        files[name] = {"sha256": actual_hash, "size_bytes": len(raw),
                       "device": after.st_dev, "inode": after.st_ino,
                       "mtime_ns": after.st_mtime_ns, "mapped_identity_confirmed": False}
        require(actual_hash == expected_hash and (expected_size is None or len(raw) == expected_size),
                "loader_hash")
        require(shell_stat(after) == os.environ.get(prefix + name.upper() + "_STAT"),
                "shell_runtime_stat")
    # procfs reports zero st_size; the map is a bounded text input, not source code.
    stream = open("/proc/self/maps", "rb")
    try:
        maps = stream.read(MAX_INPUT + 1)
    finally:
        pending = sys.exc_info()[1]
        failure = None
        try:
            stream.close()
        except MemoryError:
            failure = RuntimeFailure("resource_incomplete", "mapping_close_memory_exhausted")
        except Exception:
            failure = RuntimeFailure("evidence_incomplete", "mapping_close_failed")
        if failure is not None:
            if pending is None:
                raise failure from None
            detail = {"classification": failure.classification, "code": failure.code,
                      "operation": "runtime_mapping_read"}
            pending._bootstrap_cleanup_failures = [
                *getattr(pending, "_bootstrap_cleanup_failures", ()), detail]
            if isinstance(pending, RuntimeFailure):
                pending.secondary_failures = pending._bootstrap_cleanup_failures
    require(len(maps) <= MAX_INPUT, "mapping_cap", "resource_incomplete")
    seen = {"executable": False, "library": False}
    for line in maps.decode("ascii", "strict").splitlines():
        parts = line.split(None, 5)
        if len(parts) != 6:
            continue
        path = parts[5]
        if "libpython" in path:
            require(path == library, "foreign_python_mapping")
        for name, expected_path in (("executable", executable), ("library", library)):
            if path == expected_path:
                major, minor = (int(value, 16) for value in parts[3].split(":"))
                record = files[name]
                record["observed_mapping"] = {"major": major, "minor": minor, "inode": int(parts[4])}
                require(int(parts[4]) == record["inode"]
                        and (major, minor) == (os.major(record["device"]), os.minor(record["device"])),
                        "mapped_" + name + "_identity")
                seen[name] = True
                record["mapped_identity_confirmed"] = True
    require(all(seen.values()), "missing_runtime_mapping")
    observation["memory_cap_restoration"] = "retained_until_leaf_process_exit"
    return observation

