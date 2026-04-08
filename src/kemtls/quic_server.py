"""QUIC-style UDP server transport for KEMTLS + HTTP/1.1 bridge."""

from __future__ import annotations

import socket
import threading
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from flask import Flask

from ._http_bridge import call_flask_app, parse_http_request
from .handshake import ServerHandshake
from .quic_crypto import QUICPacketProtector, build_packet_aad
from .quic_packets import ACK, APP_DATA, CONNECTION_CLOSE, HANDSHAKE, INITIAL, decode_packet, encode_packet
from .quic_state import QUICConnectionState
from utils.serialization import deserialize_message


_RETRY_TIMEOUT_S = 0.25
_MAX_RETRIES = 4


@dataclass
class _ServerConnection:
    state: QUICConnectionState
    peer_address: Tuple[str, int]
    handshake: ServerHandshake
    phase: str = "await_initial"
    session: Any = None
    sender: Optional[QUICPacketProtector] = None
    receiver: Optional[QUICPacketProtector] = None
    sent_packets: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    processed_app_packets: set[int] = field(default_factory=set)
    cached_server_hello: Optional[bytes] = None
    cached_server_finished: Optional[bytes] = None


class KEMTLSQUICServer:
    """UDP-based QUIC-style server that keeps KEMTLS application semantics intact."""

    def __init__(
        self,
        app: Flask,
        server_identity: str,
        server_lt_sk: bytes,
        cert: Optional[Dict[str, Any]] = None,
        pdk_key_id: Optional[str] = None,
        host: str = "0.0.0.0",
        port: int = 4433,
    ):
        self.app = app
        self.server_identity = server_identity
        self.server_lt_sk = server_lt_sk
        self.cert = cert
        self.pdk_key_id = pdk_key_id
        self.host = host
        self.port = port

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(0.1)

        self._stop_event = threading.Event()
        self._connections: Dict[bytes, _ServerConnection] = {}

    def stop(self) -> None:
        self._stop_event.set()
        try:
            self.sock.close()
        except OSError:
            pass

    def start(self) -> None:
        self.sock.bind((self.host, self.port))
        print(f"KEMTLS QUIC Server listening on {self.host}:{self.port} (udp)")

        while not self._stop_event.is_set():
            try:
                raw, addr = self.sock.recvfrom(65535)
            except socket.timeout:
                self._retransmit_expired_packets()
                continue
            except OSError:
                if self._stop_event.is_set():
                    break
                raise

            try:
                packet = decode_packet(raw)
            except Exception:
                continue

            try:
                self._handle_packet(packet, addr)
            except EOFError:
                continue
            except Exception as exc:
                print(f"Error handling QUIC packet: {exc!r}")
                traceback.print_exc()

            self._retransmit_expired_packets()

    def _new_connection(self, connection_id: bytes, addr: Tuple[str, int]) -> _ServerConnection:
        collector = None
        if hasattr(self, "get_collector") and callable(self.get_collector):
            collector = self.get_collector()

        handshake = ServerHandshake(
            self.server_identity,
            self.server_lt_sk,
            self.cert,
            self.pdk_key_id,
            collector=collector,
        )
        return _ServerConnection(
            state=QUICConnectionState(connection_id=connection_id, peer_address=addr),
            peer_address=addr,
            handshake=handshake,
        )

    def _handle_packet(self, packet, addr: Tuple[str, int]) -> None:
        connection = self._connections.get(packet.connection_id)
        if connection is None:
            if packet.packet_type != INITIAL:
                return
            connection = self._new_connection(packet.connection_id, addr)
            self._connections[packet.connection_id] = connection

        if packet.packet_type == CONNECTION_CLOSE:
            connection.state.mark_closed()
            self._connections.pop(packet.connection_id, None)
            return

        if packet.packet_type == ACK:
            self._process_ack(connection, packet.payload)
            return

        connection.state.note_received_packet(packet.packet_number)

        if connection.phase == "await_initial":
            if packet.packet_type != INITIAL:
                return
            self._send_ack(connection, packet.packet_number, epoch=packet.epoch)
            server_hello = connection.handshake.process_client_hello(packet.payload)
            connection.cached_server_hello = server_hello
            self._send_packet(connection, HANDSHAKE, server_hello, epoch=0, reliable=True)
            connection.phase = "await_cke"
            return

        if connection.phase == "await_cke":
            if packet.packet_type != HANDSHAKE:
                if packet.packet_type == INITIAL and connection.cached_server_hello is not None:
                    self._send_ack(connection, packet.packet_number, epoch=packet.epoch)
                    self._send_packet(connection, HANDSHAKE, connection.cached_server_hello, epoch=0, reliable=True)
                return
            self._send_ack(connection, packet.packet_number, epoch=packet.epoch)
            server_finished = connection.handshake.process_client_key_exchange(packet.payload)
            connection.cached_server_finished = server_finished
            self._send_packet(connection, HANDSHAKE, server_finished, epoch=0, reliable=True)
            connection.phase = "await_cf"
            return

        if connection.phase == "await_cf":
            if packet.packet_type != HANDSHAKE:
                if packet.packet_type == INITIAL and connection.cached_server_hello is not None:
                    self._send_ack(connection, packet.packet_number, epoch=packet.epoch)
                    self._send_packet(connection, HANDSHAKE, connection.cached_server_hello, epoch=0, reliable=True)
                return

            message_type = None
            try:
                message = deserialize_message(packet.payload)
                if isinstance(message, dict):
                    message_type = message.get("type")
            except Exception:
                message_type = None

            if message_type == "ClientKeyExchange" and connection.cached_server_finished is not None:
                self._send_ack(connection, packet.packet_number, epoch=packet.epoch)
                self._send_packet(connection, HANDSHAKE, connection.cached_server_finished, epoch=0, reliable=True)
                return

            self._send_ack(connection, packet.packet_number, epoch=packet.epoch)
            session = connection.handshake.verify_client_finished(packet.payload)
            session.transport = "quic"
            connection.session = session
            connection.sender = QUICPacketProtector(session.server_write_key, session.server_write_iv)
            connection.receiver = QUICPacketProtector(session.client_write_key, session.client_write_iv)
            connection.phase = "established"
            print(f"Handshake complete. Mode: {session.handshake_mode}")
            if hasattr(self, "on_handshake_complete") and callable(self.on_handshake_complete):
                collector = getattr(connection.handshake, "collector", None)
                if collector is not None:
                    self.on_handshake_complete(collector.get_metrics())
            return

        if connection.phase != "established" or packet.packet_type != APP_DATA:
            return

        if connection.receiver is None:
            return

        self._send_ack(connection, packet.packet_number, epoch=packet.epoch)

        aad = build_packet_aad(
            packet_type=APP_DATA,
            connection_id=connection.state.connection_id,
            packet_number=packet.packet_number,
            epoch=packet.epoch,
            payload_length=0,
        )
        if packet.packet_number in connection.processed_app_packets:
            return
        plaintext = connection.receiver.unprotect_packet(packet.packet_number, packet.payload, aad)
        connection.processed_app_packets.add(packet.packet_number)

        parse_http_request(plaintext)
        response_bytes = call_flask_app(self.app, connection.session, plaintext)
        self._send_packet(connection, APP_DATA, response_bytes, epoch=1, reliable=True)

    def _send_packet(self, connection: _ServerConnection, packet_type: int, payload: bytes, *, epoch: int, reliable: bool) -> int:
        packet_number = connection.state.next_packet_number()
        packet_payload = payload

        if packet_type == APP_DATA:
            if connection.sender is None:
                raise RuntimeError("QUIC sender context not established")
            aad = build_packet_aad(
                packet_type=APP_DATA,
                connection_id=connection.state.connection_id,
                packet_number=packet_number,
                epoch=epoch,
                payload_length=0,
            )
            packet_payload = connection.sender.protect_packet(packet_number, payload, aad)

        packet_bytes = encode_packet(
            packet_type=packet_type,
            connection_id=connection.state.connection_id,
            packet_number=packet_number,
            payload=packet_payload,
            epoch=epoch,
        )
        self.sock.sendto(packet_bytes, connection.peer_address)

        if reliable:
            deadline = time.monotonic() + _RETRY_TIMEOUT_S
            connection.state.schedule_retransmission(packet_number, deadline)
            connection.sent_packets[packet_number] = {
                "bytes": packet_bytes,
                "deadline": deadline,
                "attempts": 0,
            }

        return packet_number

    def _send_ack(self, connection: _ServerConnection, packet_number: int, *, epoch: int) -> None:
        ack_payload = packet_number.to_bytes(8, "big")
        ack_packet = encode_packet(
            packet_type=ACK,
            connection_id=connection.state.connection_id,
            packet_number=connection.state.next_packet_number(),
            payload=ack_payload,
            epoch=epoch,
        )
        self.sock.sendto(ack_packet, connection.peer_address)

    def _process_ack(self, connection: _ServerConnection, payload: bytes) -> None:
        if len(payload) != 8:
            return
        acked_packet_number = int.from_bytes(payload, "big")
        connection.state.acknowledge_packet(acked_packet_number)
        connection.sent_packets.pop(acked_packet_number, None)

    def _retransmit_expired_packets(self) -> None:
        now = time.monotonic()
        for connection_id, connection in list(self._connections.items()):
            if connection.state.close_state == "closed":
                self._connections.pop(connection_id, None)
                continue

            for entry in list(connection.state.expired_retransmissions(now)):
                packet_state = connection.sent_packets.get(entry.packet_number)
                if packet_state is None:
                    continue
                if packet_state["attempts"] >= _MAX_RETRIES:
                    continue
                self.sock.sendto(packet_state["bytes"], connection.peer_address)
                packet_state["attempts"] += 1
                packet_state["deadline"] = now + _RETRY_TIMEOUT_S
                connection.state.schedule_retransmission(entry.packet_number, packet_state["deadline"])
