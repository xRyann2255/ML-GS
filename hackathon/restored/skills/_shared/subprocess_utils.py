"""Subprocess helper: kills the process tree on timeout (cross-platform).

Drop-in replacement for ``subprocess.run()`` when a *timeout* is used.
On timeout the entire process tree is killed before re-raising
``subprocess.TimeoutExpired``.
"""

import os
import signal
import subprocess
import sys


def _kill_tree(pid: int) -> None:
    """Kill an entire process tree."""
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True, timeout=10,
            )
        except Exception:
            pass
    else:
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass


def run_cmd(cmd, *, capture_output=False, text=False, timeout=None,
            input=None, **kwargs):
    """``subprocess.run`` drop-in that kills the process tree on timeout.

    On normal completion returns ``subprocess.CompletedProcess``.
    On timeout kills the tree and re-raises ``subprocess.TimeoutExpired``
    with ``.stdout`` / ``.stderr`` set from partial output.
    """
    if capture_output:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE

    if sys.platform == "win32":
        kwargs.setdefault("creationflags", subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        kwargs.setdefault("preexec_fn", os.setsid)

    stdin_arg = subprocess.PIPE if input is not None else kwargs.pop("stdin", None)
    proc = subprocess.Popen(cmd, text=text, stdin=stdin_arg, **kwargs)
    try:
        stdout, stderr = proc.communicate(input=input, timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(proc.pid)
        try:
            stdout, stderr = proc.communicate(timeout=10)
        except (subprocess.TimeoutExpired, OSError):
            proc.kill()
            stdout, stderr = proc.communicate()
        raise subprocess.TimeoutExpired(
            cmd, timeout, output=stdout, stderr=stderr
        )
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)
