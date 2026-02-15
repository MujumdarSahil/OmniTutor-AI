# =============================================================================
# app/adaptive/metrics.py — Provider metrics and global registry
# =============================================================================

import time

EMA_ALPHA = 0.2  # new sample weight; prev weight = 0.8


class ProviderMetrics:
    def __init__(self) -> None:
        self.total_requests: int = 0
        self.success_count: int = 0
        self.failure_count: int = 0
        self._avg_latency: float | None = None  # rolling EMA
        self.last_failure_timestamp: float | None = None
        self.circuit_open_until: float | None = None
        self._failure_timestamps: list[float] = []  # for 3-in-60s rule

    @property
    def failure_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.failure_count / self.total_requests

    @property
    def avg_latency(self) -> float:
        return self._avg_latency if self._avg_latency is not None else 0.0

    def record_success(self, latency_ms: float) -> None:
        self.total_requests += 1
        self.success_count += 1
        if self._avg_latency is None:
            self._avg_latency = latency_ms
        else:
            self._avg_latency = (self._avg_latency * (1 - EMA_ALPHA)) + (latency_ms * EMA_ALPHA)

    def record_failure(self) -> None:
        self.total_requests += 1
        self.failure_count += 1
        now = time.monotonic()
        self.last_failure_timestamp = now
        self._failure_timestamps.append(now)
        # keep only last 60 seconds
        cutoff = now - 60.0
        self._failure_timestamps = [t for t in self._failure_timestamps if t >= cutoff]
        if len(self._failure_timestamps) >= 3:
            self.open_circuit(duration_sec=60)

    def is_circuit_open(self) -> bool:
        if self.circuit_open_until is None:
            return False
        if time.monotonic() >= self.circuit_open_until:
            self.circuit_open_until = None
            return False
        return True

    def open_circuit(self, duration_sec: int = 60) -> None:
        self.circuit_open_until = time.monotonic() + duration_sec

    def to_dict(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "success": self.success_count,
            "failure": self.failure_count,
            "failure_rate": round(self.failure_rate, 4),
            "avg_latency": round(self.avg_latency, 2),
            "circuit_open": self.is_circuit_open(),
        }


PROVIDER_STATS: dict[str, ProviderMetrics] = {
    "openai": ProviderMetrics(),
    "groq": ProviderMetrics(),
    "gemini": ProviderMetrics(),
    "ollama": ProviderMetrics(),
}


def get_provider_metrics(provider: str) -> ProviderMetrics:
    return PROVIDER_STATS[provider]
