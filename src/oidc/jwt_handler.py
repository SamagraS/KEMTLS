"""JWT/JWS handling for the updated OIDC layer."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

from crypto.ml_dsa import MLDSA65
from utils.encoding import base64url_decode, base64url_encode
from utils.serialization import deserialize_message, serialize_message


ID_TOKEN_TYPE = "JWT"
ACCESS_TOKEN_TYPE = "at+jwt"
DEFAULT_KID = "signing-key-1"


class PQJWT:
    """Signs and validates standard-shaped JWTs with ML-DSA-65."""

    def sign_jwt(
        self,
        claims: Dict[str, Any],
        issuer_sk: bytes,
        kid: str = DEFAULT_KID,
        token_type: str = ID_TOKEN_TYPE,
        extra_headers: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not isinstance(claims, dict):
            raise TypeError("claims must be a dictionary")
        if not isinstance(kid, str) or not kid:
            raise ValueError("kid must be a non-empty string")
        if not isinstance(token_type, str) or not token_type:
            raise ValueError("token_type must be a non-empty string")

        header = {
            "alg": MLDSA65.ALGORITHM,
            "typ": token_type,
            "kid": kid,
        }
        if extra_headers:
            if not isinstance(extra_headers, dict):
                raise TypeError("extra_headers must be a dictionary when provided")
            if any(name in extra_headers for name in ("alg", "typ", "kid")):
                raise ValueError("extra_headers must not override alg, typ, or kid")
            header.update(extra_headers)

        header_b64 = base64url_encode(serialize_message(header))
        payload_b64 = base64url_encode(serialize_message(claims))
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        signature = MLDSA65.sign(issuer_sk, signing_input)
        return f"{header_b64}.{payload_b64}.{base64url_encode(signature)}"

    def verify_jwt(
        self,
        token: str,
        issuer_pk: bytes,
        expected_type: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if not isinstance(token, str):
            raise TypeError("token must be a string")

        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("invalid JWT format")

        header_b64, payload_b64, signature_b64 = parts
        header = deserialize_message(base64url_decode(header_b64))
        payload = deserialize_message(base64url_decode(payload_b64))
        if not isinstance(header, dict):
            raise ValueError("JWT header must decode to an object")
        if not isinstance(payload, dict):
            raise ValueError("JWT payload must decode to an object")

        if header.get("alg") != MLDSA65.ALGORITHM:
            raise ValueError(f"unsupported JWT algorithm: {header.get('alg')}")
        if expected_type and header.get("typ") != expected_type:
            raise ValueError(
                f"unexpected JWT type: expected {expected_type}, got {header.get('typ')}"
            )

        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        signature = base64url_decode(signature_b64)
        if not MLDSA65.verify(issuer_pk, signing_input, signature):
            raise ValueError("invalid JWT signature")

        return header, payload

    def create_id_token(
        self,
        claims: Dict[str, Any],
        issuer_sk: bytes,
        issuer_pk: Optional[bytes] = None,
        kid: str = DEFAULT_KID,
        **_: Any,
    ) -> str:
        return self.sign_jwt(claims, issuer_sk, kid=kid, token_type=ID_TOKEN_TYPE)

    def create_access_token(
        self,
        claims: Dict[str, Any],
        issuer_sk: bytes,
        kid: str = DEFAULT_KID,
        cnf_claim: Optional[Dict[str, Any]] = None,
    ) -> str:
        token_claims = dict(claims)
        if cnf_claim is not None:
            if not isinstance(cnf_claim, dict):
                raise TypeError("cnf_claim must be a dictionary when provided")
            if set(cnf_claim) != {"cnf"}:
                raise ValueError("cnf_claim must only contain the 'cnf' field")
            token_claims.update(cnf_claim)
        return self.sign_jwt(token_claims, issuer_sk, kid=kid, token_type=ACCESS_TOKEN_TYPE)

    def validate_id_token(
        self,
        token: str,
        issuer_pk: bytes,
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
        nonce: Optional[str] = None,
    ) -> Dict[str, Any]:
        _, claims = self.verify_jwt(token, issuer_pk, expected_type=ID_TOKEN_TYPE)
        self._validate_registered_claims(claims, issuer=issuer, audience=audience)
        if nonce is not None and claims.get("nonce") != nonce:
            raise ValueError("nonce mismatch")
        return claims

    def validate_access_token(
        self,
        token: str,
        issuer_pk: bytes,
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
    ) -> Dict[str, Any]:
        _, claims = self.verify_jwt(token, issuer_pk, expected_type=ACCESS_TOKEN_TYPE)
        self._validate_registered_claims(claims, issuer=issuer, audience=audience)
        return claims

    def verify_id_token(
        self,
        token: str,
        issuer_pk: bytes,
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
        nonce: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.validate_id_token(
            token,
            issuer_pk,
            issuer=issuer,
            audience=audience,
            nonce=nonce,
        )

    def extract_confirmation_claim(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            payload = deserialize_message(base64url_decode(parts[1]))
            cnf = payload.get("cnf")
            return cnf if isinstance(cnf, dict) else None
        except Exception:
            return None

    def _validate_registered_claims(
        self,
        claims: Dict[str, Any],
        issuer: Optional[str],
        audience: Optional[str],
    ) -> None:
        now = int(time.time())
        if "exp" in claims and now >= int(claims["exp"]):
            raise ValueError("token expired")
        if "nbf" in claims and now < int(claims["nbf"]):
            raise ValueError("token not yet valid")
        if issuer is not None and claims.get("iss") != issuer:
            raise ValueError("issuer mismatch")
        if audience is not None and claims.get("aud") != audience:
            raise ValueError("audience mismatch")


__all__ = ["ACCESS_TOKEN_TYPE", "DEFAULT_KID", "ID_TOKEN_TYPE", "PQJWT"]
