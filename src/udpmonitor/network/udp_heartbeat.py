"""Background UDP echo heartbeat monitor."""

from __future__ import annotations

from collections.abc import Callable
import logging
from queue import Queue
import select
import socket
import struct
from threading import Event, Lock, Thread, current_thread
import time

from udpmonitor.models import NetworkMetrics
from udpmonitor.network.metrics import MetricsAccumulator

LOGGER = logging.getLogger(__name__)
PACKET_MAGIC = b"UDPM"
PACKET_FORMAT = "!4sIQ"
PACKET_SIZE = struct.calcsize(PACKET_FORMAT)
MIN_INTERVAL_SECONDS = 0.1

MetricsListener = Callable[[NetworkMetrics], None]


class UdpHeartbeatMonitor:
    """Measure UDP echo responsiveness from a single dedicated worker thread.

    The configured endpoint must return each received UDP datagram unchanged,
    such as an RFC 862 UDP Echo service or the bundled test fixture.
    """

    def __init__(
        self,
        host: str,
        port: int,
        interval_seconds: float = 1.0,
        timeout_seconds: float = 2.0,
        window_size: int = 60,
    ) -> None:
        """Configure a monitor without starting network activity yet."""
        if not host:
            raise ValueError("host must not be empty")
        if not 1 <= port <= 65535:
            raise ValueError("port must be in the range 1-65535")
        if interval_seconds < MIN_INTERVAL_SECONDS:
            raise ValueError(f"interval_seconds must be at least {MIN_INTERVAL_SECONDS}")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._host = host
        self._port = port
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
            self._thread = Thread(target=self._run, name="udp-heartbeat", daemon=True)
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
        """Perform periodic UDP echo transactions until stopped."""
        sequence = 0
        try:
            address_info = socket.getaddrinfo(self._host, self._port, type=socket.SOCK_DGRAM)[0]
        except OSError as error:
            self._publish(self._metrics.record_error(str(error)))
            return
        family, _, _, _, address = address_info
        with socket.socket(family, socket.SOCK_DGRAM) as udp_socket:
            while not self._stop_event.is_set():
                started = time.monotonic()
                self._measure_once(udp_socket, address, sequence)
                sequence = (sequence + 1) % (2**32)
                remaining = self._interval_seconds - (time.monotonic() - started)
                self._stop_event.wait(max(0.0, remaining))

    def _measure_once(self, udp_socket: socket.socket, address: tuple[object, ...], sequence: int) -> None:
        """Send one uniquely identifiable packet and await its exact echo."""
        sent_at = time.monotonic_ns()
        payload = struct.pack(PACKET_FORMAT, PACKET_MAGIC, sequence, sent_at)
        try:
            udp_socket.sendto(payload, address)
            readable, _, _ = select.select([udp_socket], [], [], self._timeout_seconds)
            if not readable:
                self._publish(self._metrics.record_timeout())
                return
            response, _ = udp_socket.recvfrom(PACKET_SIZE)
            if response != payload:
                self._publish(self._metrics.record_error("Received an unexpected UDP response."))
                return
            rtt_milliseconds = (time.monotonic_ns() - sent_at) / 1_000_000
            self._publish(self._metrics.record_success(rtt_milliseconds))
        except OSError as error:
            LOGGER.warning("UDP heartbeat error: %s", error)
            self._publish(self._metrics.record_error(str(error)))

    def _publish(self, metrics: NetworkMetrics) -> None:
        """Queue a worker result for safe delivery to the UI thread."""
        self._updates.put(metrics)
