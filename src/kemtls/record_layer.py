"""
KEMTLS Record Layer

Provides secure framing and authenticated encryption (AEAD) for KEMTLS traffic.
Wire format: seq_number(8) | length(4) | ciphertext
"""

import struct
from socket import socket
from typing import Tuple
from .session import KEMTLSSession
from crypto.aead import seal, open_, xor_iv_with_seq


class KEMTLSRecordLayer:
    """
    Manages the encryption, decryption, and framing of KEMTLS records.
    """
    
    def __init__(self, session: KEMTLSSession, sock: socket, is_client: bool):
        self.session = session
        self.sock = sock
        self.is_client = is_client
        
        # Sequence numbers
        self.send_seq = 0
        self.recv_seq = 0
        
        # Keys and IVs - depend on role
        if is_client:
            self.send_key = session.client_write_key
            self.send_iv = session.client_write_iv
            self.recv_key = session.server_write_key
            self.recv_iv = session.server_write_iv
        else:
            self.send_key = session.server_write_key
            self.send_iv = session.server_write_iv
            self.recv_key = session.client_write_key
            self.recv_iv = session.client_write_iv

    def send_record(self, plaintext: bytes):
        """Encrypt and send a record."""
        if self.send_seq >= 1 << 64:
            raise OverflowError("Sequence number overflow")
            
        nonce = xor_iv_with_seq(self.send_iv, self.send_seq)
        
        # AAD = Header (Seq + Length)
        # We'll calculate length after encryption
        # For KEMTLS records, we'll use a 4-byte length field
        
        # Encrypt first to get length
        # (Alternatively, header AAD can be just seq_num)
        # User specified: AAD = seq_number || length
        
        # We need a fixed length for AAD during encryption, 
        # so we'll use a placeholder for length.
        # Header: Seq(8) + Len(4) = 12 bytes
        dummy_header = struct.pack(">QI", self.send_seq, 0)
        ciphertext = seal(self.send_key, nonce, plaintext, dummy_header)
        
        # Update header with real length
        length = len(ciphertext)
        header = struct.pack(">QI", self.send_seq, length)
        
        # Re-seal with correct AAD?
        # Actually, let's just use Seq as AAD to avoid chicken-and-egg, 
        # but the prompt says AAD = seq_number || length.
        # This implies we must know the length.
        # In KEMTLS (like TLS 1.3), the length is not part of the AAD for the record itself, 
        # but let's follow the prompt.
        ciphertext = seal(self.send_key, nonce, plaintext, header)
        
        self.sock.sendall(header + ciphertext)
        self.send_seq += 1

    def recv_record(self) -> bytes:
        """Receive and decrypt a record."""
        # 1. Read Header
        header = self._read_n_bytes(12)
        seq, length = struct.unpack(">QI", header)
        
        if seq != self.recv_seq:
            raise ValueError(f"Sequence mismatch: expected {self.recv_seq}, got {seq}")
            
        # 2. Read Ciphertext
        ciphertext = self._read_n_bytes(length)
        
        # 3. Decrypt
        nonce = xor_iv_with_seq(self.recv_iv, self.recv_seq)
        plaintext = open_(self.recv_key, nonce, ciphertext, header)
        
        self.recv_seq += 1
        return plaintext

    def _read_n_bytes(self, n: int) -> bytes:
        """Helper to read exactly n bytes from the socket."""
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                raise EOFError("Connection closed by peer")
            data += chunk
        return data


def for_client(session: KEMTLSSession, sock: socket) -> KEMTLSRecordLayer:
    return KEMTLSRecordLayer(session, sock, True)


def for_server(session: KEMTLSSession, sock: socket) -> KEMTLSRecordLayer:
    return KEMTLSRecordLayer(session, sock, False)
