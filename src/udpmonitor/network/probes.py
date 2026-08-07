"""Pluggable single-measurement strategies used by HeartbeatMonitor.

UDP Echo (RFC 862) gives the most accurate RTT/loss/jitter numbers, but it
only works when the target actually runs an Echo service. Most real
diagnostic targets -- a home router, a Discord voice server, a VRChat
world server -- do not. TcpConnectProbe and IcmpPingProbe trade some
accuracy for the ability to measure targets that were never designed to
be measured, so a single interval/timeout-driven HeartbeatMonitor can
point at whichever target is actually reachable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
import logging
import platform
import re
import select
import socket
import struct
import subprocess
import time

LOGGER = logging.getLogger(__name__)


class ProbeOutcome(StrEnum):
    """Result category of a single probe attempt."""

    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """Outcome of one measurement attempt."""

    outcome: ProbeOutcome
    rtt_milliseconds: float | None = None
    error_message: str | None = None


class Probe(ABC):
    """A strategy that measures round-trip responsiveness to one target."""

    def open(self) -> None:
        """Acquire resources shared by repeated measurements. Optional to override."""

    def close(self) -> None:
        """Release resources acquired by ``open``. Optional to override."""

    @abstractmethod
    def measure(self, timeout_seconds: float) -> ProbeResult:
        """Perform exactly one measurement and return its outcome."""


class UdpEchoProbe(Probe):
    """Measure RTT via RFC 862 UDP Echo.

    Requires the target to return each datagram unchanged, such as a
    self-hosted Echo Test Server. Not suitable for arbitrary hosts like
    game or voice servers.
    """

    PACKET_MAGIC = b"UDPM"
    PACKET_FORMAT = "!4sIQ"
    PACKET_SIZE = struct.calcsize(PACKET_FORMAT)

    def __init__(self, host: str, port: int) -> None:
        """Configure the Echo target without opening a socket yet."""
        if not host:
            raise ValueError("host must not be empty")
        if not 1 <= port <= 65535:
            raise ValueError("port must be in the range 1-65535")
        self._host = host
        self._port = port
        self._socket: socket.socket | None = None
        self._address: tuple[object, ...] | None = None
        self._sequence = 0

    def open(self) -> None:
        """Resolve the target and open a UDP socket for reuse across measurements."""
        family, _, _, _, address = socket.getaddrinfo(self._host, self._port, type=socket.SOCK_DGRAM)[0]
        self._socket = socket.socket(family, socket.SOCK_DGRAM)
        self._address = address

    def close(self) -> None:
        """Close the underlying UDP socket."""
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def measure(self, timeout_seconds: float) -> ProbeResult:
        """Send one uniquely identifiable packet and await its exact echo."""
        if self._socket is None or self._address is None:
            return ProbeResult(ProbeOutcome.ERROR, error_message="Probe is not open.")
        sequence, self._sequence = self._sequence, (self._sequence + 1) % (2**32)
        sent_at = time.monotonic_ns()
        payload = struct.pack(self.PACKET_FORMAT, self.PACKET_MAGIC, sequence, sent_at)
        try:
            self._socket.sendto(payload, self._address)
            readable, _, _ = select.select([self._socket], [], [], timeout_seconds)
            if not readable:
                return ProbeResult(ProbeOutcome.TIMEOUT)
            response, _ = self._socket.recvfrom(self.PACKET_SIZE)
            if response != payload:
                return ProbeResult(ProbeOutcome.ERROR, error_message="Received an unexpected UDP response.")
            rtt_milliseconds = (time.monotonic_ns() - sent_at) / 1_000_000
            return ProbeResult(ProbeOutcome.SUCCESS, rtt_milliseconds=rtt_milliseconds)
        except OSError as error:
            return ProbeResult(ProbeOutcome.ERROR, error_message=str(error))


class TcpConnectProbe(Probe):
    """Measure handshake latency by opening and closing a TCP connection.

    Does not exercise the UDP path, but works against almost any reachable
    host/port pair without needing special cooperation from the target.
    Useful as a coarse "is the server alive" signal when nothing at the
    target speaks UDP Echo -- for example a game server's web/API port.
    """

    def __init__(self, host: str, port: int) -> None:
        """Configure the TCP target."""
        if not host:
            raise ValueError("host must not be empty")
        if not 1 <= port <= 65535:
            raise ValueError("port must be in the range 1-65535")
        self._host = host
        self._port = port

    def measure(self, timeout_seconds: float) -> ProbeResult:
        """Open a TCP connection, time the handshake, then close it."""
        started_at = time.monotonic_ns()
        try:
            with socket.create_connection((self._host, self._port), timeout=timeout_seconds):
                rtt_milliseconds = (time.monotonic_ns() - started_at) / 1_000_000
                return ProbeResult(ProbeOutcome.SUCCESS, rtt_milliseconds=rtt_milliseconds)
        except TimeoutError:
            return ProbeResult(ProbeOutcome.TIMEOUT)
        except OSError as error:
            return ProbeResult(ProbeOutcome.ERROR, error_message=str(error))


class IcmpPingProbe(Probe):
    """Measure RTT via the operating system's ping utility.

    Shells out to the platform ping command instead of opening a raw ICMP
    socket, because raw sockets require administrator privileges on
    Windows while the bundled ping.exe does not.
    """

    _WINDOWS_RTT_PATTERN = re.compile(r"(?:time|時間)[=<]\s*(\d+)\s*ms", re.IGNORECASE)
    _POSIX_RTT_PATTERN = re.compile(r"time[=<]\s*([\d.]+)\s*ms", re.IGNORECASE)

    def __init__(self, host: str) -> None:
        """Configure the ping target."""
        if not host:
            raise ValueError("host must not be empty")
        self._host = host
        self._is_windows = platform.system() == "Windows"

    def measure(self, timeout_seconds: float) -> ProbeResult:
        """Run a single ping and parse its reported round-trip time."""
        timeout_milliseconds = max(1, round(timeout_seconds * 1000))
        command = (
            ["ping", "-n", "1", "-w", str(timeout_milliseconds), self._host]
            if self._is_windows
            else ["ping", "-c", "1", "-W", str(max(1, round(timeout_seconds))), self._host]
        )
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout_seconds + 1.0,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if self._is_windows else 0,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return ProbeResult(ProbeOutcome.ERROR, error_message=str(error))
        pattern = self._WINDOWS_RTT_PATTERN if self._is_windows else self._POSIX_RTT_PATTERN
        match = pattern.search(completed.stdout)
        if match:
            return ProbeResult(ProbeOutcome.SUCCESS, rtt_milliseconds=float(match.group(1)))
        if completed.returncode == 0:
            return ProbeResult(ProbeOutcome.ERROR, error_message="Could not parse ping output.")
        return ProbeResult(ProbeOutcome.TIMEOUT)
