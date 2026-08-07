"""Tests for pluggable measurement strategies."""

from __future__ import annotations

import socket
import subprocess

import pytest

from udpmonitor.network.probes import IcmpPingProbe, ProbeOutcome, TcpConnectProbe


def test_tcp_connect_probe_reports_success_against_a_listening_socket() -> None:
    """A reachable TCP endpoint should measure a positive RTT."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    try:
        probe = TcpConnectProbe("127.0.0.1", listener.getsockname()[1])
        result = probe.measure(timeout_seconds=1.0)
    finally:
        listener.close()

    assert result.outcome is ProbeOutcome.SUCCESS
    assert result.rtt_milliseconds is not None
    assert result.rtt_milliseconds >= 0.0


def test_tcp_connect_probe_reports_error_when_port_is_closed() -> None:
    """A closed port should be reported as an error rather than crash."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    listener.close()  # Free the port immediately so the connection is refused.

    result = TcpConnectProbe("127.0.0.1", port).measure(timeout_seconds=1.0)

    assert result.outcome is ProbeOutcome.ERROR


def test_tcp_connect_probe_rejects_invalid_port() -> None:
    """Out-of-range ports should fail fast rather than reach the network."""
    with pytest.raises(ValueError):
        TcpConnectProbe("127.0.0.1", 0)


def test_icmp_ping_probe_parses_windows_style_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """A Windows ping reply line should be parsed into a millisecond RTT."""
    probe = IcmpPingProbe("example.invalid")
    probe._is_windows = True
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(args=[], returncode=0, stdout="Reply from 127.0.0.1: bytes=32 time=12ms TTL=64"),
    )

    result = probe.measure(timeout_seconds=1.0)

    assert result.outcome is ProbeOutcome.SUCCESS
    assert result.rtt_milliseconds == 12.0


def test_icmp_ping_probe_reports_timeout_when_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    """A nonzero exit with no parsable reply should be treated as a timeout."""
    probe = IcmpPingProbe("example.invalid")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(args=[], returncode=1, stdout="Request timed out."),
    )

    result = probe.measure(timeout_seconds=1.0)

    assert result.outcome is ProbeOutcome.TIMEOUT
