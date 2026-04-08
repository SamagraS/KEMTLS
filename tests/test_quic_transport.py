from types import SimpleNamespace

from kemtls.quic_packets import HANDSHAKE, QUICPacket
from kemtls.quic_state import QUICConnectionState
from kemtls.quic_client import KEMTLSQUICClientTransport


def test_quic_connection_state_tracks_out_of_order_packets():
    state = QUICConnectionState(connection_id=b"conn-1")

    state.note_received_packet(5)
    state.note_received_packet(3)
    state.note_received_packet(4)

    assert state.recv_packet_number == 5
    assert state.pending_acks == {3, 4, 5}
    assert state.received_packets == {3, 4, 5}


def test_quic_handshake_retransmits_after_timeout(monkeypatch):
    transport = KEMTLSQUICClientTransport(expected_identity="server-1")
    transport.connection_id = b"conn-1"

    sends = []

    class DummySocket:
        def send(self, payload):
            sends.append(payload)

    transport.sock = DummySocket()

    packet_number = 11
    transport.pending_packets[packet_number] = {
        "bytes": b"retransmit-me",
        "deadline": 0.0,
        "attempts": 0,
        "timeout": 0.1,
    }

    call_count = {"n": 0}

    def fake_send_packet(**_kwargs):
        return packet_number

    def fake_recv_loop(*, expect_packet_type):
        assert expect_packet_type == HANDSHAKE
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise TimeoutError("forced timeout")
        return SimpleNamespace(
            packet_number=7,
            packet_type=HANDSHAKE,
            payload=b"server-hello",
            epoch=0,
        )

    monkeypatch.setattr(transport, "_send_packet", fake_send_packet)
    monkeypatch.setattr(transport, "_recv_loop", fake_recv_loop)
    monkeypatch.setattr(transport, "_send_ack", lambda *_args, **_kwargs: None)

    packet = transport._transmit_with_retry(
        packet_type=HANDSHAKE,
        payload=b"client-hello",
        epoch=0,
        expect_packet_type=HANDSHAKE,
    )

    assert packet.payload == b"server-hello"
    assert sends == [b"retransmit-me"]
    assert packet_number not in transport.pending_packets
