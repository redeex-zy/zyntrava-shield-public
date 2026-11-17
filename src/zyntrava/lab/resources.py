"""Sample only the owned research runner process, never unrelated processes."""

import threading
import time

import psutil


class ResourceMeter:
    def __init__(self) -> None:
        self.process = psutil.Process()
        self.stop_event = threading.Event()
        self.peak_rss = self.process.memory_info().rss
        self.started_rss = self.peak_rss
        self.cpu_start = sum(self.process.cpu_times()[:2])
        self.started = time.perf_counter()
        self.thread = threading.Thread(target=self.sample, daemon=True)
        self.thread.start()

    def sample(self) -> None:
        while not self.stop_event.wait(0.01):
            self.peak_rss = max(self.peak_rss, self.process.memory_info().rss)

    def finish(self) -> dict[str, float | int]:
        self.stop_event.set()
        self.thread.join(timeout=1)
        return {
            "sampled_peak_process_rss_bytes": self.peak_rss,
            "rss_at_arm_start_bytes": self.started_rss,
            "runner_cpu_seconds": sum(self.process.cpu_times()[:2]) - self.cpu_start,
            "arm_wall_seconds": time.perf_counter() - self.started,
            "sampling_interval_ms": 10,
        }
