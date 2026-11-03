"""Records the machine and software state alongside every run."""
from __future__ import annotations

import platform
import subprocess
import sys
from datetime import datetime, timezone

try:
    import psutil
except ImportError:
    psutil = None


def _cpu_name() -> str:
    try:
        if sys.platform == "darwin":
            return subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
        if sys.platform.startswith("linux"):
            for line in open("/proc/cpuinfo"):
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
        if sys.platform == "win32":
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"], text=True)
            return out.strip()
    except Exception:
        pass
    return platform.processor() or "unknown"


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def _git_dirty() -> bool | None:
    try:
        return bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    except Exception:
        return None


def collect(client=None, models=()) -> dict:
    info = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "os": platform.platform(),
        "machine_arch": platform.machine(),
        "cpu": _cpu_name(),
        "python": sys.version.split()[0],
        "git_commit": _git_commit(),
        "git_dirty": _git_dirty(),
    }
    if psutil:
        info["cores_physical"] = psutil.cpu_count(logical=False)
        info["cores_logical"] = psutil.cpu_count(logical=True)
        info["ram_total_gb"] = round(psutil.virtual_memory().total / 1024 ** 3, 1)
    if client is not None:
        info["ollama_version"] = client.version()
        info["models"] = {m: {"digest": client.digest(m), **client.show(m)} for m in models}
    return info
