"""Linux process-group ownership, cleanup, and fail-closed residual verification.

Keep the leader unreaped until group cleanup: its PID cannot be reused while we
signal its group. A durable random token identifies residual descendants after a
supervisor crash. Residual signals use pidfds, never an unverified numeric PID.
"""
import ctypes
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import time

TOKEN_ENV = 'WORKER32_PROCESS_GROUP_TOKEN'


class SupervisorInterrupted(TimeoutError):
    pass


def _stat(pid):
    try:
        raw = (Path('/proc')/str(pid)/'stat').read_text()
    except FileNotFoundError:
        return None
    fields = raw.rsplit(') ', 1)[1].split()
    return dict(state=fields[0], group=int(fields[2]), session=int(fields[3]),
                start=int(fields[19]))


def _boot():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def _members(group):
    deadline = time.monotonic() + 5
    live = []
    for p in Path('/proc').iterdir():
        if time.monotonic() > deadline:
            raise TimeoutError('process inventory deadline')
        if p.name.isdecimal():
            s = _stat(int(p.name))
            if s and s['group'] == group and s['state'] != 'Z':
                live.append(int(p.name))
    return live


def _kill_group(group, sig):
    try:
        os.killpg(group, sig)
    except ProcessLookupError:
        pass


def _cleanup(process, grace):
    # Caller has not reaped the leader, so the PGID is still owned, even if its
    # process has already exited. Always KILL and attempt reaping on scan errors.
    problem = None
    try:
        _kill_group(process.pid, signal.SIGTERM)
        until = time.monotonic() + grace
        while _members(process.pid) and time.monotonic() < until:
            time.sleep(min(.02, max(0, until-time.monotonic())))
    except BaseException as exc:
        problem = exc
    finally:
        _kill_group(process.pid, signal.SIGKILL)
    try:
        until = time.monotonic() + 5
        while _members(process.pid):
            if time.monotonic() >= until:
                raise TimeoutError('compute group still active after KILL; finalization forbidden')
            time.sleep(.02)
    except BaseException as exc:
        problem = problem or exc
    finally:
        process.wait(timeout=5)
        # PR_SET_CHILD_SUBREAPER adopts orphan descendants. Only reap our group.
        while True:
            try:
                pid, _ = os.waitpid(-process.pid, os.WNOHANG)
            except ChildProcessError:
                break
            if pid == 0:
                problem = problem or TimeoutError('unreaped live compute descendant')
                break
    if problem is not None:
        raise problem


# The child refuses execution if its spawning supervisor has already died.
# PDEATHSIG kills the leader on an unhandleable supervisor death. Descendants
# remain identifiable by TOKEN_ENV for the finalizer. This also closes the gap
# between fork and durable PID recording without Python preexec_fn callbacks.
_BOOTSTRAP = '''import ctypes,json,os,signal,sys
libc=ctypes.CDLL(None,use_errno=True)
if libc.prctl(1,9,0,0,0) != 0:
    raise OSError(ctypes.get_errno(), 'PR_SET_PDEATHSIG')
if os.getppid() != int(sys.argv[1]):
    sys.exit(125)
signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
# Registration is durable before any compute code or descendants can execute.
with open('/proc/self/stat') as f:
    start=int(f.read().rsplit(') ',1)[1].split()[19])
with open(sys.argv[2],'x') as f:
    json.dump(dict(pid=os.getpid(),start=start,token=os.environ['WORKER32_PROCESS_GROUP_TOKEN']),f)
    f.flush();os.fsync(f.fileno())
fd=os.open(os.path.dirname(sys.argv[2]),os.O_RDONLY)
os.fsync(fd);os.close(fd)
if os.getppid() != int(sys.argv[1]):
    sys.exit(125)
os.execvpe(sys.argv[3],sys.argv[3:],os.environ)
'''


def run_group(command, log, timeout=1800, grace=30):
    from .runtime import durable
    log = Path(log)
    token = secrets.token_hex(32)
    owner = _stat(os.getpid())
    plan = dict(schema='worker32-process-group-v1', token=token, boot=_boot(),
                uid=os.getuid(), supervisor_pid=os.getpid(), supervisor_start=owner['start'])
    # Durable before spawning. Finalization can find orphaned children even if
    # the supervisor dies before Popen returns.
    durable(log.with_name(log.name+'.group.json'), plan)
    libc = ctypes.CDLL(None, use_errno=True)
    previous_subreaper = ctypes.c_int()
    if libc.prctl(37, ctypes.byref(previous_subreaper), 0, 0, 0) != 0 or libc.prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'subreaper setup')
    handlers = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGINT)}
    received_signal = None
    def interrupted(signum, frame):
        nonlocal received_signal
        # Poll this at a safe boundary: raising asynchronously during Popen or
        # cleanup could abandon a child before its handle was assigned.
        received_signal = signum
    process = None
    try:
        for sig in handlers:
            signal.signal(sig, interrupted)
        with log.open('xb') as stream:
            try:
                process = subprocess.Popen([sys.executable, '-c', _BOOTSTRAP,
                    str(os.getpid()), str(log.with_name(log.name+'.group-leader.json').absolute()), *command], stdout=stream, stderr=subprocess.STDOUT,
                    start_new_session=True, env={**os.environ, TOKEN_ENV:token})
                until = time.monotonic() + timeout
                while True:
                    if received_signal is not None:
                        raise SupervisorInterrupted(f'supervisor received signal {received_signal}')
                    status = os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                    if status is not None:
                        break
                    if time.monotonic() >= until:
                        raise TimeoutError('whole-compute process group exceeded deadline')
                    time.sleep(min(.02, max(0, until-time.monotonic())))
            finally:
                # Repeated handled signals cannot interrupt containment. SIGKILL
                # is covered by the durable token and finalization residual gate.
                for sig in handlers:
                    signal.signal(sig, signal.SIG_IGN)
                if process is not None:
                    _cleanup(process, grace)
                stream.flush()
                os.fsync(stream.fileno())
                durable(log.with_name(log.name+'.group-closed.json'), {'token':token,'cleaned':True})
        if received_signal is not None:
            raise SupervisorInterrupted(f'supervisor received signal {received_signal}')
        return process.returncode
    finally:
        for sig, handler in handlers.items():
            signal.signal(sig, handler)
        libc.prctl(36, previous_subreaper.value, 0, 0, 0)


def _residuals(plan, leader):
    """Return identity-pinned live members, or fail closed if inspection is unsafe."""
    found = []
    deadline = time.monotonic()+5
    marker = (TOKEN_ENV+'='+plan['token']).encode()
    try:
        for p in Path('/proc').iterdir():
            if time.monotonic() >= deadline:
                raise TimeoutError('residual inventory deadline')
            if not p.name.isdecimal():
                continue
            try:
                if p.stat().st_uid != plan['uid']:
                    continue
                before = _stat(int(p.name))
                if before is None or before['state'] == 'Z' or before['start'] < plan['supervisor_start'] or int(p.name) == plan['supervisor_pid']:
                    continue
                with (p/'environ').open('rb') as f:
                    environment = f.read(1024*1024+1)
                if len(environment) > 1024*1024:
                    raise ValueError('uninspectable oversized process environment')
                if marker not in environment.split(b'\0'):
                    continue
                fd = os.pidfd_open(int(p.name))
                after = _stat(int(p.name))
                try:
                    with (p/'environ').open('rb') as f:
                        still_owned = marker in f.read(1024*1024+1).split(b'\0')
                except BaseException:
                    os.close(fd)
                    raise
                if after is None or before['start'] != after['start'] or not still_owned:
                    os.close(fd)
                    continue
                found.append(fd)
            except (FileNotFoundError, ProcessLookupError):
                continue
            except PermissionError:
                # Same-uid processes must be inspectable on the authorized runner.
                raise ValueError('cannot safely inspect same-uid residual process')
        return found
    except BaseException:
        for fd in found:
            os.close(fd)
        raise


def residual_gate(directory, grace=30):
    """Before *any* finalization, settle known groups after abnormal supervisor death.

    A live unclosed supervisor blocks finalization. Stale manifests from another
    boot cannot name live processes. Token matching + start-time recheck + pidfd
    signaling prevents signaling an unrelated process after PID reuse.
    """
    for path in sorted(Path(directory).glob('*.group.json')):
        if path.is_symlink() or path.stat().st_size > 8192:
            raise ValueError('unsafe process ownership record')
        plan = json.loads(path.read_bytes())
        if (set(plan) != {'schema','token','boot','uid','supervisor_pid','supervisor_start'}
            or plan['schema'] != 'worker32-process-group-v1'
            or type(plan['token']) is not str or len(plan['token']) != 64
            or any(c not in '0123456789abcdef' for c in plan['token'])
            or type(plan['uid']) is not int or plan['uid'] != os.getuid()
            or any(type(plan[k]) is not int or plan[k] < 1 for k in ('supervisor_pid','supervisor_start'))):
            raise ValueError('invalid process ownership record')
        if plan['boot'] != _boot():
            continue
        owner = _stat(plan['supervisor_pid'])
        closed = path.with_name(path.name.replace('.group.json','.group-closed.json'))
        if owner and owner['start'] == plan['supervisor_start'] and owner['state'] != 'Z':
            # A separate supervisor can still be writing terminal metadata even
            # after group cleanup. Only a synchronous self-finalizer may use its
            # own closed receipt while the owner process is alive.
            if plan['supervisor_pid'] != os.getpid():
                raise RuntimeError('supervisor still active; finalization forbidden')
            if not closed.is_file() or closed.is_symlink() or json.loads(closed.read_bytes()) != {'token':plan['token'],'cleaned':True}:
                raise RuntimeError('supervisor still active; finalization forbidden')
        registration = path.with_name(path.name.replace('.group.json','.group-leader.json'))
        if not registration.exists():
            # The bootstrap cannot start compute before durable registration.
            # With its parent gone it either exits or is killed by PDEATHSIG.
            continue
        if registration.is_symlink() or registration.stat().st_size > 8192:
            raise ValueError('unsafe leader registration')
        leader = json.loads(registration.read_bytes())
        if (set(leader) != {'pid','start','token'} or leader['token'] != plan['token']
            or type(leader['pid']) is not int or leader['pid'] < 1
            or type(leader['start']) is not int or leader['start'] < plan['supervisor_start']):
            raise ValueError('invalid leader registration')
        until = time.monotonic()+grace
        while True:
            fds = _residuals(plan, leader)
            if not fds:
                break
            try:
                for fd in fds:
                    try:
                        signal.pidfd_send_signal(fd, signal.SIGTERM if time.monotonic()<until else signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            finally:
                for fd in fds:
                    os.close(fd)
            if time.monotonic() > until+5:
                raise TimeoutError('residual compute remains active; finalization forbidden')
            time.sleep(.02)
