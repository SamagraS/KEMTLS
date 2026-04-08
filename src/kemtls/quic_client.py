"""QUIC-style UDP client transport for KEMTLS.

This module keeps KEMTLS and HTTP/1.1 semantics unchanged while swapping the
underlying transport from TCP to a UDP packet protocol with acknowledgements
and retransmissions.
"""

from __future__ import annotations

import os
import socket
import time
from typing import Any, Callable, Dict, Optional, Tuple

from .handshake import ClientHandshake
from .quic_crypto import QUICPacketProtector, build_packet_aad
from .quic_packets import ACK, APP_DATA, CONNECTION_CLOSE, HANDSHAKE, INITIAL, decode_packet, encode_packet
from .quic_state import QUICConnectionState
from .tcp_transport import build_http_request
from .transport import KEMTLSTransport


_HANDSHAKE_RETRY_TIMEOUT_S = 0.35
_APP_RETRY_TIMEOUT_S = 0.25
_MAX_RETRIES = 4


class KEMTLSQUICClientTransport(KEMTLSTransport):
    """Client-side QUIC-style transport using UDP datagrams."""

    def __init__(
        self,
        expected_identity: str,
        ca_pk: Optional[bytes] = None,
        pdk_store=None,
        mode: str = "auto",
        collector: Optional[Any] = None,
    ):
        super().__init__()
        self.expected_identity = expected_identity
        self.ca_pk = ca_pk
        self.pdk_store = pdk_store
        self.mode = mode
        self.collector = collector

        self.sock: Optional[socket.socket] = None
        self.connected_host: Optional[str] = None
        self.connected_port: Optional[int] = None
        self.connection_id = os.urandom(8)
        self.state = QUICConnectionState(connection_id=self.connection_id)

        self.sender: Optional[QUICPacketProtector] = None
        self.receiver: Optional[QUICPacketProtector] = None
        self.pending_packets: Dict[int, Dict[str, Any]] = {}
        self.processed_app_packets: set[int] = set()

    def connect(self, host: str, port: int) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect((host, port))
        sock.settimeout(_HANDSHAKE_RETRY_TIMEOUT_S)
        self.sock = sock
        self.connected_host = host
        self.connected_port = port

        if self.collector:
            self.collector.start_hct()

        handshake = ClientHandshake(
            self.expected_identity,
            self.ca_pk,
            self.pdk_store,
            self.mode,
            collector=self.collector,
        )

        client_hello = handshake.client_hello()
        server_hello_packet = self._transmit_with_retry(
            packet_type=INITIAL,
            payload=client_hello,
            epoch=0,
            expect_packet_type=HANDSHAKE,
        )
        server_hello = server_hello_packet.payload

        if self.collector and hasattr(self.collector, "record_ttfb"):
            self.collector.record_ttfb()

        client_key_exchange, session = handshake.process_server_hello(server_hello)
        server_finished_packet = self._transmit_with_retry(
            packet_type=HANDSHAKE,
            payload=client_key_exchange,
            epoch=0,
            expect_packet_type=HANDSHAKE,
        )
        server_finished = server_finished_packet.payload

        session = handshake.process_server_finished(server_finished, session)
        client_finished = handshake.client_finished()
        self._send_packet(packet_type=HANDSHAKE, payload=client_finished, epoch=0, reliable=False)

        session.transport = "quic"
        self.session = session
        self.sender = QUICPacketProtector(session.client_write_key, session.client_write_iv)
        self.receiver = QUICPacketProtector(session.server_write_key, session.server_write_iv)

        if self.collector:
            self.collector.end_hct()

        print(f"Handshake complete. Mode: {session.handshake_mode}")

    def accept(self, *args, **kwargs):
        raise NotImplementedError("QUIC client transport cannot accept inbound connections")

    def send_handshake(self, payload: bytes) -> None:
        self._send_packet(packet_type=HANDSHAKE, payload=payload, epoch=0, reliable=True)

    def recv_handshake(self) -> bytes:
        packet = self._recv_loop(expect_packet_type=HANDSHAKE)
        return packet.payload

    def send_application(self, payload: bytes) -> None:
        if self.sender is None or self.session is None:
            raise RuntimeError("No active QUIC session")
        self._send_packet(packet_type=APP_DATA, payload=payload, epoch=1, reliable=True)

    def recv_application(self) -> bytes:
        if self.receiver is None:
            raise RuntimeError("No active QUIC session")

        overall_deadline = time.monotonic() + (_APP_RETRY_TIMEOUT_S * (_MAX_RETRIES + 3))
        while True:
            try:
                packet = self._recv_loop(expect_packet_type=APP_DATA)
            except TimeoutError:
                if time.monotonic() >= overall_deadline:
                    raise
                continue
            self._send_ack(packet.packet_number, epoch=packet.epoch)

            if packet.packet_number in self.processed_app_packets:
                continue

            aad = build_packet_aad(
                packet_type=APP_DATA,
                connection_id=self.connection_id,
                packet_number=packet.packet_number,
                epoch=packet.epoch,
                payload_length=0,
            )
            plaintext = self.receiver.unprotect_packet(packet.packet_number, packet.payload, aad)
            self.processed_app_packets.add(packet.packet_number)
            return plaintext

    def close(self) -> None:
        if self.sock is not None:
            try:
                close_packet = encode_packet(
                    packet_type=CONNECTION_CLOSE,
                    connection_id=self.connection_id,
                    packet_number=self.state.next_packet_number(),
                    payload=b"close",
                    epoch=0,
                )
                self.sock.send(close_packet)
            except Exception:
                pass
            try:
                self.sock.close()
            except OSError:
                pass

        self.sock = None
        self.session = None
        self.sender = None
        self.receiver = None
        self.connected_host = None
        self.connected_port = None
        self.pending_packets.clear()
        self.processed_app_packets.clear()

    def matches_endpoint(self, host: str, port: int) -> bool:
        return (
            self.sock is not None
            and self.session is not None
            and self.connected_host == host
            and self.connected_port == port
        )

    def _send_packet(self, *, packet_type: int, payload: bytes, epoch: int, reliable: bool) -> int:
        if self.sock is None:
            raise RuntimeError("QUIC transport is not connected")

        packet_number = self.state.next_packet_number()
        packet_payload = payload

        if packet_type == APP_DATA:
            if self.sender is None:
                raise RuntimeError("No active QUIC sender context")
            aad = build_packet_aad(
                packet_type=APP_DATA,
                connection_id=self.connection_id,
                packet_number=packet_number,
                epoch=epoch,
                payload_length=0,
            )
            packet_payload = self.sender.protect_packet(packet_number, payload, aad)

        packet_bytes = encode_packet(
            packet_type=packet_type,
            connection_id=self.connection_id,
            packet_number=packet_number,
            payload=packet_payload,
            epoch=epoch,
        )
        self.sock.send(packet_bytes)

        if reliable:
            deadline = time.monotonic() + (_APP_RETRY_TIMEOUT_S if packet_type == APP_DATA else _HANDSHAKE_RETRY_TIMEOUT_S)
            self.state.schedule_retransmission(packet_number, deadline)
            self.pending_packets[packet_number] = {
                "bytes": packet_bytes,
                "deadline": deadline,
                "attempts": 0,
                "timeout": _APP_RETRY_TIMEOUT_S if packet_type == APP_DATA else _HANDSHAKE_RETRY_TIMEOUT_S,
            }

        return packet_number

    def _transmit_with_retry(self, *, packet_type: int, payload: bytes, epoch: int, expect_packet_type: int):
        packet_number = self._send_packet(packet_type=packet_type, payload=payload, epoch=epoch, reliable=True)

        while True:
            try:
                packet = self._recv_loop(expect_packet_type=expect_packet_type)
                self.pending_packets.pop(packet_number, None)
                self.state.acknowledge_packet(packet_number)
                self._send_ack(packet.packet_number, epoch=packet.epoch)
                return packet
            except TimeoutError:
                entry = self.pending_packets.get(packet_number)
                if entry is None:
                    continue
                if entry["attempts"] >= _MAX_RETRIES:
                    raise TimeoutError("handshake retransmission budget exhausted")
                self.sock.send(entry["bytes"])
                entry["attempts"] += 1
                entry["deadline"] = time.monotonic() + entry["timeout"]

    def _recv_loop(self, *, expect_packet_type: int):
        if self.sock is None:
            raise RuntimeError("QUIC transport is not connected")

        deadline = time.monotonic() + _HANDSHAKE_RETRY_TIMEOUT_S
        while True:
            timeout_remaining = max(0.01, deadline - time.monotonic())
            self.sock.settimeout(timeout_remaining)
            try:
                raw_packet = self.sock.recv(65535)
            except socket.timeout:
                self._process_expired_retransmissions()
                raise TimeoutError("timed out waiting for QUIC packet")

            packet = decode_packet(raw_packet)
            if packet.connection_id != self.connection_id:
                continue

            if packet.packet_type == ACK:
                if len(packet.payload) == 8:
                    acked_number = int.from_bytes(packet.payload, "big")
                    self.pending_packets.pop(acked_number, None)
                    self.state.acknowledge_packet(acked_number)
                continue

            if packet.packet_type != expect_packet_type:
                if packet.packet_type == CONNECTION_CLOSE:
                    raise EOFError("QUIC peer closed connection")
                continue

            self.state.note_received_packet(packet.packet_number)
            return packet

    def _process_expired_retransmissions(self) -> None:
        if self.sock is None:
            return

        now = time.monotonic()
        for entry in list(self.state.expired_retransmissions(now)):
            packet_state = self.pending_packets.get(entry.packet_number)
            if packet_state is None:
                continue
            if packet_state["attempts"] >= _MAX_RETRIES:
                continue
            self.sock.send(packet_state["bytes"])
            packet_state["attempts"] += 1
            packet_state["deadline"] = now + packet_state["timeout"]
            self.state.schedule_retransmission(entry.packet_number, packet_state["deadline"])

    def _send_ack(self, packet_number: int, *, epoch: int) -> None:
        if self.sock is None:
            return
        ack_packet = encode_packet(
            packet_type=ACK,
            connection_id=self.connection_id,
            packet_number=self.state.next_packet_number(),
            payload=packet_number.to_bytes(8, "big"),
            epoch=epoch,
        )
        self.sock.send(ack_packet)


def request_over_transport(
    transport: KEMTLSQUICClientTransport,
    *,
    host: str,
    port: int,
    method: str,
    path: str,
    headers: Optional[Dict[str, str]] = None,
    body: bytes = b"",
    keep_alive: bool = False,
    header_mutator: Optional[Callable[[Dict[str, str], Any], None]] = None,
) -> Tuple[bytes, Any]:
    reuse = keep_alive and transport.matches_endpoint(host, port)
    if not reuse:
        transport.close()
        transport.connect(host, port)

    effective_headers = dict(headers or {})
    if header_mutator is not None:
        header_mutator(effective_headers, transport.session)

    request_bytes = build_http_request(
        host,
        method,
        path,
        headers=effective_headers,
        body=body,
        keep_alive=keep_alive,
    )
    transport.send_application(request_bytes)
    response = transport.recv_application()
    return response, transport.session
