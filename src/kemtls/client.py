"""
KEMTLS Socket Client

A socket-based client that performs a KEMTLS handshake and 
sends an encrypted HTTP request over a record layer.
"""

import socket
from typing import Dict, Any, Optional, Tuple
from .handshake import ClientHandshake
from .record_layer import for_client
from .pdk import PDKTrustStore


class KEMTLSClient:
    """
    KEMTLS client for making secure requests.
    """
    
    def __init__(
        self,
        expected_identity: str,
        ca_pk: Optional[bytes] = None,
        pdk_store: Optional[PDKTrustStore] = None,
        mode: str = "auto"
    ):
        self.expected_identity = expected_identity
        self.ca_pk = ca_pk
        self.pdk_store = pdk_store
        self.mode = mode
        self.session = None

    def request(
        self,
        host: str,
        port: int,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        body: bytes = b"",
    ) -> Tuple[bytes, Any]:
        """
        Connect to a server, perform handshake, and send an encrypted request.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        
        try:
            # 1. Perform Handshake
            handshake = ClientHandshake(
                self.expected_identity,
                self.ca_pk,
                self.pdk_store,
                self.mode
            )
            
            # Message 1: ClientHello
            ch_bytes = handshake.client_hello()
            self._send_msg(sock, ch_bytes)
            
            # Message 2: ServerHello
            sh_bytes = self._read_msg(sock)
            cke_bytes, session = handshake.process_server_hello(sh_bytes)
            self._send_msg(sock, cke_bytes)
            
            # Message 3: ServerFinished
            sf_bytes = self._read_msg(sock)
            # Finish processing on the client
            handshake.process_server_finished(sf_bytes, session)
            
            # Message 4: ClientFinished
            cf_bytes = handshake.client_finished()
            self._send_msg(sock, cf_bytes)
            
            self.session = session
            print(f"Handshake complete. Mode: {session.handshake_mode}")
            
            # 2. Record Layer
            record_layer = for_client(session, sock)
            
            # 3. Send HTTP Request
            header_lines = [f"{method} {path} HTTP/1.1", f"Host: {host}"]
            for key, value in (headers or {}).items():
                if key.lower() == "host":
                    continue
                header_lines.append(f"{key}: {value}")
            if body and not any(k.lower() == "content-length" for k in (headers or {})):
                header_lines.append(f"Content-Length: {len(body)}")
            header_lines.append("Connection: close")

            http_req = ("\r\n".join(header_lines) + "\r\n\r\n").encode('ascii') + body
            record_layer.send_record(http_req)
            
            # 4. Receive Response
            response = record_layer.recv_record()
            
            return response, session
            
        except Exception as e:
            print(f"Error in client: {e}")
            raise
        finally:
            sock.close()

    def _read_msg(self, sock: socket.socket) -> bytes:
        """Handshake length-prefix reader."""
        header = sock.recv(4)
        if not header:
            raise EOFError("Socket closed during handshake")
        length = int.from_bytes(header, "big")
        data = b""
        while len(data) < length:
            chunk = sock.recv(length - len(data))
            if not chunk:
                raise EOFError("Socket closed during handshake data read")
            data += chunk
        return data

    def _send_msg(self, sock: socket.socket, msg: bytes):
        """Handshake length-prefix sender."""
        header = len(msg).to_bytes(4, "big")
        sock.sendall(header + msg)
