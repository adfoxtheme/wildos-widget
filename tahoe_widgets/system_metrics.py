"""Đọc thông số tài nguyên hệ thống (CPU, GPU, RAM, SSD, Mạng, Uptime)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CpuMetrics:
    percent: int = 0
    model: str = "Intel / AMD"
    temp: int | None = None


@dataclass
class GpuMetrics:
    has_gpu: bool = False
    util: int = 0
    temp: int | None = None
    used: int = 0
    total: int = 0
    model: str = ""


@dataclass
class StorageMetrics:
    percent: int = 0
    text: str = "-- / --"
    swap_percent: int = 0


@dataclass
class NetworkMetrics:
    interface: str = "mạng"
    down_text: str = "0 KB/s"
    up_text: str = "0 KB/s"


@dataclass
class SystemMetrics:
    uptime: str = "00:00:00"
    uptime_seconds: float = 0.0
    cpu: CpuMetrics = field(default_factory=CpuMetrics)
    gpu: GpuMetrics = field(default_factory=GpuMetrics)
    ram: StorageMetrics = field(default_factory=StorageMetrics)
    disk: StorageMetrics = field(default_factory=StorageMetrics)
    net: NetworkMetrics = field(default_factory=NetworkMetrics)


def _read_text(path: str | Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def read_uptime_seconds() -> float:
    raw = _read_text("/proc/uptime").split()
    if not raw:
        return 0.0
    try:
        return float(raw[0])
    except ValueError:
        return 0.0


class SystemMetricsReader:
    """Đọc các chỉ số phần cứng định kỳ, có cache model và đọc NVIDIA không chặn UI."""

    def __init__(self) -> None:
        self._prev_cpu: tuple[int, int] | None = None
        self._prev_net: tuple[int, int, float] | None = None
        self._cpu_model_cache: str | None = None
        self._gpu_type: str | None = None
        self._amd_path: Path | None = None
        self._gpu_model_cache: str | None = None
        self._gpu_lock = threading.Lock()
        self._gpu_cache = GpuMetrics()
        self._nvidia_pending = False

    def _get_cpu_model(self) -> str:
        if self._cpu_model_cache:
            return self._cpu_model_cache
        for line in _read_text("/proc/cpuinfo").splitlines():
            if line.startswith("model name"):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    name = parts[1].strip()
                    name = re.sub(r"CPU\s+@.*$", "", name).strip()
                    name = re.sub(r"Intel\(R\)\s+Core\(TM\)\s+", "", name)
                    name = re.sub(r"Intel\(R\)\s+Xeon\(R\)\s+CPU\s+", "Xeon ", name)
                    self._cpu_model_cache = name
                    return name
        self._cpu_model_cache = "Intel / AMD"
        return self._cpu_model_cache

    def _get_cpu_temp(self) -> int | None:
        raw = _read_text("/sys/class/thermal/thermal_zone0/temp").strip()
        if raw.isdigit():
            return round(int(raw) / 1000)
        for hwmon in sorted(Path("/sys/class/hwmon").glob("hwmon*")):
            name = _read_text(hwmon / "name").strip().lower()
            if name in {"coretemp", "k10temp", "zenpower", "acpitz"}:
                temp_raw = _read_text(hwmon / "temp1_input").strip()
                if temp_raw.isdigit():
                    return round(int(temp_raw) / 1000)
        return None

    def _read_cpu_percent(self) -> int:
        first_line = _read_text("/proc/stat").splitlines()[:1]
        if not first_line or not first_line[0].startswith("cpu "):
            return 0
        parts = [int(x) for x in first_line[0].split()[1:]]
        if len(parts) < 4:
            return 0
        idle = parts[3] + (parts[4] if len(parts) > 4 else 0)
        total = sum(parts)
        percent = 0
        if self._prev_cpu is not None:
            prev_idle, prev_total = self._prev_cpu
            delta_idle = idle - prev_idle
            delta_total = total - prev_total
            if delta_total > 0:
                percent = max(0, min(100, round(((delta_total - delta_idle) / delta_total) * 100)))
        self._prev_cpu = (idle, total)
        return percent

    def _read_mem(self) -> StorageMetrics:
        total = avail = swap_total = swap_free = 0
        for line in _read_text("/proc/meminfo").splitlines():
            digits = re.sub(r"\D+", "", line)
            if not digits:
                continue
            val = int(digits)
            if line.startswith("MemTotal:"):
                total = val
            elif line.startswith("MemAvailable:"):
                avail = val
            elif line.startswith("SwapTotal:"):
                swap_total = val
            elif line.startswith("SwapFree:"):
                swap_free = val
        used = max(0, total - avail)
        percent = round((used / total) * 100) if total > 0 else 0
        swap_used = max(0, swap_total - swap_free)
        swap_percent = round((swap_used / swap_total) * 100) if swap_total > 0 else 0
        used_gib = used / 1024 / 1024
        total_gib = total / 1024 / 1024
        return StorageMetrics(
            percent=percent,
            text=f"{used_gib:.1f} / {total_gib:.1f} GiB",
            swap_percent=swap_percent,
        )

    def _read_disk(self) -> StorageMetrics:
        try:
            st = os.statvfs("/")
            total = st.f_blocks * st.f_frsize
            free = st.f_bfree * st.f_frsize
            used = max(0, total - free)
            percent = round((used / total) * 100) if total > 0 else 0
            used_gib = used / (1024 ** 3)
            total_gib = total / (1024 ** 3)
            return StorageMetrics(percent=percent, text=f"{used_gib:.1f} / {total_gib:.1f} GiB")
        except OSError:
            return StorageMetrics(percent=0, text="-- / --")

    def _read_net(self) -> NetworkMetrics:
        rx_bytes = tx_bytes = 0
        main_if = "mạng"
        for line in _read_text("/proc/net/dev").splitlines():
            trimmed = line.strip()
            if not trimmed or trimmed.startswith("Inter-") or trimmed.startswith("face"):
                continue
            if ":" not in trimmed:
                continue
            if_name, rest = trimmed.split(":", 1)
            if_name = if_name.strip()
            if if_name == "lo":
                continue
            nums = [int(x) for x in rest.split()]
            if len(nums) >= 9:
                rx_bytes += nums[0]
                tx_bytes += nums[8]
                if main_if == "mạng":
                    main_if = if_name

        now = time.monotonic()
        down_speed = up_speed = 0.0
        if self._prev_net is not None:
            prev_rx, prev_tx, prev_t = self._prev_net
            dt = now - prev_t
            if dt > 0.3:
                down_speed = max(0.0, (rx_bytes - prev_rx) / dt / 1024.0)
                up_speed = max(0.0, (tx_bytes - prev_tx) / dt / 1024.0)
        self._prev_net = (rx_bytes, tx_bytes, now)

        def fmt(val: float) -> str:
            if val >= 1024:
                return f"{val / 1024:.1f} MB/s"
            return f"{round(val)} KB/s"

        return NetworkMetrics(interface=main_if, down_text=fmt(down_speed), up_text=fmt(up_speed))

    def _get_amd_model(self) -> str:
        if self._gpu_model_cache:
            return self._gpu_model_cache
        try:
            out = subprocess.check_output(["lspci"], text=True, stderr=subprocess.DEVNULL, timeout=2)
            for line in out.splitlines():
                if re.search(r"vga|3d|display", line, re.I) and re.search(r"amd|radeon|advanced micro", line, re.I):
                    brackets = re.findall(r"\[(.*?)\]", line)
                    for inner in brackets:
                        if re.search(r"radeon", inner, re.I):
                            model = re.sub(r"^Radeon\s+", "RX ", inner.strip(), flags=re.I)
                            model = re.sub(r"Radeon\s+", "", model, flags=re.I).strip()
                            self._gpu_model_cache = model
                            return model
                    parts = line.split(":", 2)
                    if len(parts) > 2:
                        model = re.sub(r"Advanced Micro Devices, Inc\.\s*", "", parts[2], flags=re.I)
                        model = re.sub(r"\[AMD/ATI\]\s*", "", model, flags=re.I)
                        model = re.sub(r"\s*\(rev.*$", "", model).strip()
                        if model:
                            self._gpu_model_cache = model
                            return model
        except Exception:
            pass
        self._gpu_model_cache = "Radeon GPU"
        return self._gpu_model_cache

    def _detect_gpu_device(self) -> None:
        if self._gpu_type is not None:
            return
        if shutil.which("nvidia-smi"):
            self._gpu_type = "nvidia"
            with self._gpu_lock:
                self._gpu_cache.has_gpu = True
            return

        for i in range(8):
            base = Path(f"/sys/class/drm/card{i}/device")
            vendor = _read_text(base / "vendor").strip().lower()
            if vendor == "0x1002":
                vram_raw = _read_text(base / "mem_info_vram_total").strip()
                vram_bytes = int(vram_raw) if vram_raw.isdigit() else 0
                if vram_bytes >= 1024 * 1024 * 1024:
                    self._gpu_type = "amd"
                    self._amd_path = base
                    with self._gpu_lock:
                        self._gpu_cache.has_gpu = True
                        self._gpu_cache.total = round(vram_bytes / (1024 * 1024))
                        self._gpu_cache.model = self._get_amd_model()
                    return

        self._gpu_type = "none"

    def _update_amd_gpu(self) -> None:
        if not self._amd_path:
            return
        busy_raw = _read_text(self._amd_path / "gpu_busy_percent").strip()
        used_raw = _read_text(self._amd_path / "mem_info_vram_used").strip()
        temp: int | None = None
        for hwmon in (self._amd_path / "hwmon").glob("hwmon*"):
            temp_raw = _read_text(hwmon / "temp1_input").strip()
            if temp_raw.isdigit():
                temp = round(int(temp_raw) / 1000)
                break
        with self._gpu_lock:
            if busy_raw.isdigit():
                self._gpu_cache.util = max(0, min(100, int(busy_raw)))
            if used_raw.isdigit():
                self._gpu_cache.used = round(int(used_raw) / (1024 * 1024))
            self._gpu_cache.temp = temp

    def _update_nvidia_async(self) -> None:
        if self._nvidia_pending:
            return
        self._nvidia_pending = True

        def worker() -> None:
            try:
                out = subprocess.check_output(
                    [
                        "nvidia-smi",
                        "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,name",
                        "--format=csv,noheader,nounits",
                    ],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=3,
                )
                parts = [p.strip() for p in out.strip().splitlines()[0].split(",")]
                if len(parts) >= 4:
                    model = parts[4] if len(parts) > 4 else "GPU"
                    model = re.sub(r"NVIDIA\s+GeForce\s+", "", model)
                    model = re.sub(r"NVIDIA\s+", "", model)
                    with self._gpu_lock:
                        self._gpu_cache = GpuMetrics(
                            has_gpu=True,
                            util=int(parts[0]) if parts[0].isdigit() else 0,
                            used=int(parts[1]) if parts[1].isdigit() else 0,
                            total=int(parts[2]) if parts[2].isdigit() else 0,
                            temp=int(parts[3]) if parts[3].isdigit() else None,
                            model=model,
                        )
            except Exception:
                pass
            finally:
                self._nvidia_pending = False

        threading.Thread(target=worker, daemon=True).start()

    def read(self) -> SystemMetrics:
        uptime_sec = read_uptime_seconds()
        total_sec = int(uptime_sec)
        hours = total_sec // 3600
        minutes = (total_sec % 3600) // 60
        seconds = total_sec % 60

        self._detect_gpu_device()
        if self._gpu_type == "nvidia":
            self._update_nvidia_async()
        elif self._gpu_type == "amd":
            self._update_amd_gpu()

        with self._gpu_lock:
            gpu_snapshot = GpuMetrics(
                has_gpu=self._gpu_cache.has_gpu,
                util=self._gpu_cache.util,
                temp=self._gpu_cache.temp,
                used=self._gpu_cache.used,
                total=self._gpu_cache.total,
                model=self._gpu_cache.model,
            )

        return SystemMetrics(
            uptime=f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            uptime_seconds=uptime_sec,
            cpu=CpuMetrics(
                percent=self._read_cpu_percent(),
                model=self._get_cpu_model(),
                temp=self._get_cpu_temp(),
            ),
            gpu=gpu_snapshot,
            ram=self._read_mem(),
            disk=self._read_disk(),
            net=self._read_net(),
        )
