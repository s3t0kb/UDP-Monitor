"""Background heartbeat runner driven by a pluggable Probe."""

from __future__ import annotations

from collections.abc import Callable
import logging
from queue import Queue
from threading import Event, Lock, Thread, current_thread
import time

from udpmonitor.models import NetworkMetrics
from udpmonitor.network.metrics import MetricsAccumulator
from udpmonitor.network.probes import Probe, ProbeOutcome

LOGGER = logging.getLogger(__name__)
MIN_INTERVAL_SECONDS = 0.1

MetricsListener = Callable[[NetworkMetrics], None]


class HeartbeatMonitor:
    """Run a Probe on a fixed interval from a single dedicated worker thread.

    The measurement strategy (UDP Echo, TCP connect, ICMP ping, ...) is
    fully delegated to the injected Probe, so this class only owns
    threading, timing, and rolling-metrics bookkeeping.
    """

    def __init__(
        self,
        probe: Probe,
        interval_seconds: float = 1.0,
        timeout_seconds: float = 2.0,
        window_size: int = 60,
    ) -> None:
        """Configure a monitor without starting network activity yet."""
        if interval_seconds < MIN_INTERVAL_SECONDS:
            raise ValueError(f"interval_seconds must be at least {MIN_INTERVAL_SECONDS}")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._probe = probe
        self._interval_seconds = interval_seconds
        self._timeout_seconds = timeout_seconds
        self._metrics = MetricsAccumulator(window_size)
        self._updates: Queue[NetworkMetrics] = Queue()
        self._listeners: list[MetricsListener] = []
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._lock = Lock()

    @property
    def is_running(self) -> bool:
        """Return whether the worker has been started and not yet stopped."""
        return self._thread is not None and self._thread.is_alive()

    def subscribe(self, listener: MetricsListener) -> None:
        """Register a callback; call it only from ``drain_updates``'s caller."""
        self._listeners.append(listener)

    def start(self) -> None:
        """Start heartbeat collection. Calling start while active is a no-op."""
        with self._lock:
            if self.is_running:
                return
            self._stop_event.clear()
            self._thread = Thread(target=self._run, name="heartbeat-monitor", daemon=True)
            self._thread.start()

    def stop(self, join_timeout_seconds: float = 3.0) -> None:
        """Request a clean stop and wait briefly for the worker to exit."""
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread is not current_thread():
            thread.join(timeout=join_timeout_seconds)

    def drain_updates(self) -> list[NetworkMetrics]:
        """Return queued updates and invoke listeners on the calling thread."""
        updates: list[NetworkMetrics] = []
        while not self._updates.empty():
            update = self._updates.get_nowait()
            updates.append(update)
            for listener in tuple(self._listeners):
                listener(update)
        return updates

    def _run(self) -> None:
        """Open the probe and perform periodic measurements until stopped."""
        try:
            self._probe.open()
        except OSError as error:
            self._publish(self._metrics.record_error(str(error)))
            return
        try:
            while not self._stop_event.is_set():
                started = time.monotonic()
                self._measure_once()
                remaining = self._interval_seconds - (time.monotonic() - started)
                self._stop_event.wait(max(0.0, remaining))
        finally:
            self._probe.close()

    def _measure_once(self) -> None:
        """Run one probe measurement and publish the refreshed rolling metrics."""
        try:
            result = self._probe.measure(self._timeout_seconds)
        except OSError as error:
            LOGGER.warning("Probe error: %s", error)
            self._publish(self._metrics.record_error(str(error)))
            return
        if result.outcome is ProbeOutcome.SUCCESS and result.rtt_milliseconds is not None:
            self._publish(self._metrics.record_success(result.rtt_milliseconds))
        elif result.outcome is ProbeOutcome.TIMEOUT:
            self._publish(self._metrics.record_timeout())
        else:
            self._publish(self._metrics.record_error(result.error_message or "Unknown probe error."))

    def _publish(self, metrics: NetworkMetrics) -> None:
        """Queue a worker result for safe delivery to the UI thread."""
        self._updates.put(metrics)
