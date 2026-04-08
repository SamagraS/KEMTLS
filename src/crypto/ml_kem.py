"""ML-KEM-768 wrapper with liboqs and pqcrypto backends."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Tuple


def _has_oqs_shared_library() -> bool:
    install_root = Path(os.environ.get("OQS_INSTALL_PATH", Path.home() / "_oqs"))
    search_dirs = [install_root / "lib", install_root / "lib64", install_root / "bin"]
    library_names = ("liboqs.so", "liboqs.so.0", "liboqs.dylib", "oqs.dll", "liboqs.dll")
    for directory in search_dirs:
        if not directory.exists():
            continue
        for library_name in library_names:
            if (directory / library_name).exists():
                return True
    return False


def _load_oqs_backend():
    if os.name != "nt" and not _has_oqs_shared_library():
        return None
    try:
        import oqs  # type: ignore
    except Exception:
        return None
    try:
        with oqs.KeyEncapsulation("ML-KEM-768"):
            return oqs
    except Exception:
        return None


def _load_pqcrypto_backend():
    try:
        from pqcrypto.kem import ml_kem_768  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "ML-KEM-768 operations require either a working 'oqs/liboqs' runtime "
            "or 'pqcrypto.kem.ml_kem_768'."
        ) from exc
    return ml_kem_768


def _with_backend(
    oqs_op: Callable[[Any], Tuple[bytes, ...] | bytes],
    pqcrypto_op: Callable[[Any], Tuple[bytes, ...] | bytes],
):
    oqs = _load_oqs_backend()
    if oqs is not None:
        return oqs_op(oqs)
    return pqcrypto_op(_load_pqcrypto_backend())


class MLKEM768:
    """Stateless ML-KEM-768 operations with strict input validation."""

    ALGORITHM = "ML-KEM-768"
    PUBLIC_KEY_SIZE = 1184
    SECRET_KEY_SIZE = 2400
    CIPHERTEXT_SIZE = 1088
    SHARED_SECRET_SIZE = 32

    @classmethod
    def generate_keypair(cls) -> Tuple[bytes, bytes]:
        """Generate a fresh ML-KEM-768 keypair."""

        def _oqs_generate(oqs_module):
            with oqs_module.KeyEncapsulation(cls.ALGORITHM) as kem:
                public_key = kem.generate_keypair()
                secret_key = kem.export_secret_key()
            return public_key, secret_key

        def _pq_generate(backend):
            return backend.generate_keypair()

        public_key, secret_key = _with_backend(_oqs_generate, _pq_generate)
        cls._validate_public_key(public_key)
        cls._validate_secret_key(secret_key)
        return public_key, secret_key

    @classmethod
    def encapsulate(cls, public_key: bytes) -> Tuple[bytes, bytes]:
        """Encapsulate to an ML-KEM-768 public key."""
        cls._validate_public_key(public_key)

        def _oqs_encap(oqs_module):
            with oqs_module.KeyEncapsulation(cls.ALGORITHM) as kem:
                return kem.encap_secret(public_key)

        def _pq_encap(backend):
            return backend.encrypt(public_key)

        ciphertext, shared_secret = _with_backend(_oqs_encap, _pq_encap)
        cls._validate_ciphertext(ciphertext)
        cls._validate_shared_secret(shared_secret)
        return ciphertext, shared_secret

    @classmethod
    def decapsulate(cls, secret_key: bytes, ciphertext: bytes) -> bytes:
        """Decapsulate an ML-KEM-768 ciphertext."""
        cls._validate_secret_key(secret_key)
        cls._validate_ciphertext(ciphertext)

        def _oqs_decap(oqs_module):
            with oqs_module.KeyEncapsulation(cls.ALGORITHM, secret_key) as kem:
                return kem.decap_secret(ciphertext)

        def _pq_decap(backend):
            return backend.decrypt(secret_key, ciphertext)

        shared_secret = _with_backend(_oqs_decap, _pq_decap)
        cls._validate_shared_secret(shared_secret)
        return shared_secret

    @classmethod
    def _validate_public_key(cls, public_key: bytes) -> None:
        cls._validate_bytes("public_key", public_key, cls.PUBLIC_KEY_SIZE)

    @classmethod
    def _validate_secret_key(cls, secret_key: bytes) -> None:
        cls._validate_bytes("secret_key", secret_key, cls.SECRET_KEY_SIZE)

    @classmethod
    def _validate_ciphertext(cls, ciphertext: bytes) -> None:
        cls._validate_bytes("ciphertext", ciphertext, cls.CIPHERTEXT_SIZE)

    @classmethod
    def _validate_shared_secret(cls, shared_secret: bytes) -> None:
        cls._validate_bytes("shared_secret", shared_secret, cls.SHARED_SECRET_SIZE)

    @staticmethod
    def _validate_bytes(name: str, value: bytes, expected_length: int) -> None:
        if not isinstance(value, bytes):
            raise TypeError(f"{name} must be bytes")
        if len(value) != expected_length:
            raise ValueError(
                f"Invalid {name} size: expected {expected_length} bytes, got {len(value)}"
            )


class KyberKEM(MLKEM768):
    """Backward-compatible alias for the renamed ML-KEM implementation."""


__all__ = ["KyberKEM", "MLKEM768"]
