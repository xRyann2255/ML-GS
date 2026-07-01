"""Kill orphaned processes left behind by VS Code terminals.

Cleans up orphaned processes that accumulate from VS Code terminal usage:
- powershell.exe / bash: all except the current process tree
- conhost.exe: those whose parent process is dead (Windows only)
- python / python.exe: orphans with dead parents
- secexpr.exe / perl.exe: orphans with dead parents (Windows only)
- Code.exe / code: those not part of any active VS Code window tree
- node: orphans with dead parents (Linux only)

Uses wmic (stdlib) + ctypes (stdlib) on Windows, /proc on Linux — zero external dependencies.

Usage: cleanup.py [--dry-run]
"""

import argparse
import os
import signal
import subprocess
import sys


# ---------------------------------------------------------------------------
# Platform-specific imports and helpers
# ---------------------------------------------------------------------------

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import csv
    import ctypes
    import io
    from ctypes import wintypes


# ---------------------------------------------------------------------------
# Process enumeration via wmic (Windows) or /proc (Linux)
# ---------------------------------------------------------------------------

def get_process_map():
    """Build {pid: (parent_pid, name, mem_bytes)} from OS process list."""
    if _IS_WINDOWS:
        return _get_process_map_windows()
    return _get_process_map_linux()


def _get_process_map_windows():
    """Build {pid: (parent_pid, name, mem_bytes)} from wmic.

    Returns dict mapping PID -> (PPID, process name, working set bytes).
    """
    result = subprocess.run(
        ["wmic", "process", "get",
         "Name,ProcessId,ParentProcessId,WorkingSetSize", "/format:csv"],
        capture_output=True, text=True, timeout=15,
    )
    pm = {}
    reader = csv.reader(io.StringIO(result.stdout.strip()))
    header = None
    for row in reader:
        if not row or all(c == "" for c in row):
            continue
        # First non-empty row is header: Node,Name,ParentProcessId,ProcessId,WorkingSetSize
        if header is None:
            header = [h.strip() for h in row]
            continue
        try:
            d = dict(zip(header, [c.strip() for c in row]))
            pid = int(d["ProcessId"])
            ppid = int(d.get("ParentProcessId", 0) or 0)
            name = d.get("Name", "")
            mem = int(d.get("WorkingSetSize", 0) or 0)
            pm[pid] = (ppid, name, mem)
        except (ValueError, KeyError):
            continue
    return pm


def _get_process_map_linux():
    """Build {pid: (parent_pid, name, mem_bytes)} from /proc.

    Reads /proc/[pid]/stat for PPID and comm, /proc/[pid]/statm for RSS.
    """
    pm = {}
    proc_dir = "/proc"
    page_size = os.sysconf("SC_PAGE_SIZE")
    for entry in os.listdir(proc_dir):
        if not entry.isdigit():
            continue
        pid = int(entry)
        try:
            with open(f"{proc_dir}/{pid}/stat") as f:
                stat_line = f.read()
            # Parse: pid (comm) state ppid ...
            # comm can contain spaces/parens, so find last ')' to delimit
            comm_start = stat_line.index("(") + 1
            comm_end = stat_line.rindex(")")
            name = stat_line[comm_start:comm_end]
            fields = stat_line[comm_end + 2 :].split()
            # fields[0] = state, fields[1] = ppid
            ppid = int(fields[1])

            # RSS from statm (field 1, in pages)
            mem = 0
            try:
                with open(f"{proc_dir}/{pid}/statm") as f:
                    statm = f.read().split()
                mem = int(statm[1]) * page_size  # RSS in bytes
            except (OSError, IndexError, ValueError):
                pass

            pm[pid] = (ppid, name, mem)
        except (OSError, ValueError, IndexError):
            continue
    return pm


def is_parent_alive(pid, proc_map):
    """Check if the parent of *pid* is still running."""
    info = proc_map.get(pid)
    if not info:
        return False
    ppid = info[0]
    return ppid != 0 and ppid in proc_map


# ---------------------------------------------------------------------------
# Window detection via ctypes (Windows) or heuristic (Linux)
# ---------------------------------------------------------------------------

if _IS_WINDOWS:
    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def get_window_pids():
    """Get PIDs of all processes that have visible top-level windows."""
    if not _IS_WINDOWS:
        # On Linux, protect processes that have a controlling terminal
        # as a proxy for "visible window" (desktop sessions use X11/Wayland
        # but in headless Coder workspaces, tty ownership is the best heuristic).
        pids = set()
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                fd_dir = f"/proc/{entry}/fd/0"
                if os.path.exists(fd_dir) and os.readlink(fd_dir).startswith("/dev/pts/"):
                    pids.add(int(entry))
            except (OSError, ValueError):
                continue
        return pids

    pids = set()

    @EnumWindowsProc
    def callback(hwnd, lparam):
        if ctypes.windll.user32.IsWindowVisible(hwnd):
            pid = wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(
                hwnd, ctypes.byref(pid))
            if pid.value:
                pids.add(pid.value)
        return True

    ctypes.windll.user32.EnumWindows(callback, 0)
    return pids


# ---------------------------------------------------------------------------
# Kill helpers
# ---------------------------------------------------------------------------

def kill_pid(pid):
    """Kill a single process by PID."""
    if _IS_WINDOWS:
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                           capture_output=True, timeout=5)
        except Exception:
            pass
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass


def find_by_name(proc_map, *names):
    """Find all PIDs with a matching process name (case-insensitive).

    On Linux, also matches without .exe suffix (e.g., 'python' matches 'python3').
    """
    names_lower = {n.lower() for n in names}
    # On Linux, also match prefix (e.g. "python" matches "python3", "python3.11")
    if not _IS_WINDOWS:
        results = []
        for pid, info in proc_map.items():
            proc_name = info[1].lower()
            if proc_name in names_lower:
                results.append((pid, info))
            elif any(proc_name.startswith(n.replace(".exe", "")) for n in names_lower):
                results.append((pid, info))
        return results
    return [(pid, info) for pid, info in proc_map.items()
            if info[1].lower() in names_lower]


def mb(bytes_val):
    return round(bytes_val / (1024 * 1024), 1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Kill orphaned processes")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview what would be killed")
    args = parser.parse_args()
    dry = args.dry_run

    current_pid = os.getpid()
    proc_map = get_process_map()

    # Protect parent PID (defense-in-depth)
    current_info = proc_map.get(current_pid)
    parent_pid = current_info[0] if current_info else 0

    print("\n=== Orphan Process Cleanup ===")
    if dry:
        print("[DRY RUN] No processes will be killed.\n")

    # Build VS Code / editor protected PID set
    code_names = ("Code.exe",) if _IS_WINDOWS else ("code",)
    code_procs = find_by_name(proc_map, *code_names)
    window_pids = get_window_pids()
    protected = set()

    # Protect Code processes with visible windows / active terminals
    for pid, _ in code_procs:
        if pid in window_pids:
            protected.add(pid)

    # Propagate protection to children
    changed = True
    while changed:
        changed = False
        for pid, info in code_procs:
            if pid not in protected and info[0] in protected:
                protected.add(pid)
                changed = True

    total_killed = 0
    total_mem = 0

    # --- Shell orphans (PowerShell on Windows, bash/zsh on Linux) ---
    if _IS_WINDOWS:
        shell_names = ("powershell.exe",)
        shell_label = "PowerShell"
    else:
        shell_names = ("bash", "zsh", "sh")
        shell_label = "Shell (bash/zsh/sh)"

    ps_procs = [(pid, info) for pid, info in find_by_name(proc_map, *shell_names)
                if pid != current_pid and pid != parent_pid]
    # On Linux, only kill orphans (dead parent), not all shell instances
    if not _IS_WINDOWS:
        ps_procs = [(pid, info) for pid, info in ps_procs
                    if not is_parent_alive(pid, proc_map)]
    ps_mem = sum(info[2] for _, info in ps_procs)

    print(f"{shell_label} processes (excluding current PID {current_pid}): {len(ps_procs)}")
    if ps_procs:
        if dry:
            print(f"  Would kill {len(ps_procs)} {shell_label} processes (~{mb(ps_mem)} MB)")
        else:
            for pid, _ in ps_procs:
                kill_pid(pid)
            print(f"  Killed {len(ps_procs)} {shell_label} processes (~{mb(ps_mem)} MB freed)")
        total_killed += len(ps_procs)
        total_mem += ps_mem
    else:
        print("  None found.")

    # --- Conhost orphans (Windows only) ---
    if _IS_WINDOWS:
        conhost_procs = find_by_name(proc_map, "conhost.exe")
        orphan_conhosts = [(pid, info) for pid, info in conhost_procs
                           if not is_parent_alive(pid, proc_map)]
        oc_mem = sum(info[2] for _, info in orphan_conhosts)

        live_c = len(conhost_procs) - len(orphan_conhosts)
        print(f"\nConhost processes: {len(conhost_procs)} total, "
              f"{len(orphan_conhosts)} orphaned, {live_c} live")
        if orphan_conhosts:
            if dry:
                print(f"  Would kill {len(orphan_conhosts)} conhost processes "
                      f"(~{mb(oc_mem)} MB)")
            else:
                for pid, _ in orphan_conhosts:
                    kill_pid(pid)
                print(f"  Killed {len(orphan_conhosts)} conhost processes "
                      f"(~{mb(oc_mem)} MB freed)")
            total_killed += len(orphan_conhosts)
            total_mem += oc_mem
        else:
            print("  No orphans found.")

    # --- Python orphans ---
    py_names = ("python.exe", "pythonw.exe") if _IS_WINDOWS else ("python", "python3")
    py_procs = find_by_name(proc_map, *py_names)
    orphan_pys = [(pid, info) for pid, info in py_procs
                  if not is_parent_alive(pid, proc_map)
                  and pid != current_pid and pid != parent_pid]
    op_mem = sum(info[2] for _, info in orphan_pys)

    live_py = len(py_procs) - len(orphan_pys)
    print(f"\nPython processes: {len(py_procs)} total, "
          f"{len(orphan_pys)} orphaned, {live_py} live")
    if orphan_pys:
        if dry:
            print(f"  Would kill {len(orphan_pys)} Python processes "
                  f"(~{mb(op_mem)} MB)")
        else:
            for pid, _ in orphan_pys:
                kill_pid(pid)
            print(f"  Killed {len(orphan_pys)} Python processes "
                  f"(~{mb(op_mem)} MB freed)")
        total_killed += len(orphan_pys)
        total_mem += op_mem
    else:
        print("  No orphans found.")

    # --- Secexpr + Perl orphans (Windows) / Node orphans (Linux) ---
    if _IS_WINDOWS:
        se_procs = find_by_name(proc_map, "secexpr.exe")
        orphan_se = [(pid, info) for pid, info in se_procs
                     if not is_parent_alive(pid, proc_map)]

        perl_procs = find_by_name(proc_map, "perl.exe")
        orphan_perl = [(pid, info) for pid, info in perl_procs
                       if not is_parent_alive(pid, proc_map)]

        all_se = orphan_se + orphan_perl
        se_mem = sum(info[2] for _, info in all_se)

        live_se = len(se_procs) - len(orphan_se)
        live_pl = len(perl_procs) - len(orphan_perl)
        print(f"\nSecexpr processes: {len(se_procs)} total, "
              f"{len(orphan_se)} orphaned, {live_se} live")
        print(f"Perl processes: {len(perl_procs)} total, "
              f"{len(orphan_perl)} orphaned, {live_pl} live")
        if all_se:
            if dry:
                print(f"  Would kill {len(orphan_se)} secexpr + "
                      f"{len(orphan_perl)} perl processes (~{mb(se_mem)} MB)")
            else:
                for pid, _ in all_se:
                    kill_pid(pid)
                print(f"  Killed {len(orphan_se)} secexpr + "
                      f"{len(orphan_perl)} perl processes (~{mb(se_mem)} MB freed)")
            total_killed += len(all_se)
            total_mem += se_mem
        else:
            print("  No orphans found.")
    else:
        # Linux: look for orphaned node processes (VS Code extensions, language servers)
        node_procs = find_by_name(proc_map, "node")
        orphan_nodes = [(pid, info) for pid, info in node_procs
                        if not is_parent_alive(pid, proc_map)]
        node_mem = sum(info[2] for _, info in orphan_nodes)

        live_n = len(node_procs) - len(orphan_nodes)
        print(f"\nNode processes: {len(node_procs)} total, "
              f"{len(orphan_nodes)} orphaned, {live_n} live")
        if orphan_nodes:
            if dry:
                print(f"  Would kill {len(orphan_nodes)} node processes "
                      f"(~{mb(node_mem)} MB)")
            else:
                for pid, _ in orphan_nodes:
                    kill_pid(pid)
                print(f"  Killed {len(orphan_nodes)} node processes "
                      f"(~{mb(node_mem)} MB freed)")
            total_killed += len(orphan_nodes)
            total_mem += node_mem
        else:
            print("  No orphans found.")

    # --- Code/Editor orphans ---
    orphan_codes = [(pid, info) for pid, info in code_procs
                    if pid not in protected
                    and not is_parent_alive(pid, proc_map)]
    code_mem = sum(info[2] for _, info in orphan_codes)
    live_codes = len(code_procs) - len(orphan_codes)
    code_label = "Code" if _IS_WINDOWS else "code/code-server"

    print(f"\n{code_label} processes: {len(code_procs)} total, "
          f"{len(orphan_codes)} orphaned, {live_codes} live")
    if orphan_codes:
        if dry:
            print(f"  Would kill {len(orphan_codes)} {code_label} processes "
                  f"(~{mb(code_mem)} MB)")
        else:
            for pid, _ in orphan_codes:
                kill_pid(pid)
            print(f"  Killed {len(orphan_codes)} {code_label} processes "
                  f"(~{mb(code_mem)} MB freed)")
        total_killed += len(orphan_codes)
        total_mem += code_mem
    else:
        print("  No orphans found.")

    # --- Summary ---
    print("\n--- Summary ---")
    if dry:
        print(f"Would kill {total_killed} processes (~{mb(total_mem)} MB)")
    else:
        print(f"Killed {total_killed} processes (~{mb(total_mem)} MB freed)")
    print()


if __name__ == "__main__":
    main()
