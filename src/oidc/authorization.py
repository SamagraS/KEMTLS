"""Backward-compatible exports for the moved authorization endpoint module."""

from .auth_endpoints import (
    AuthorizationCodeRecord,
    AuthorizationEndpoint,
    InMemoryAuthorizationCodeStore,
    InMemoryClientRegistry,
)

__all__ = [
    "AuthorizationCodeRecord",
    "AuthorizationEndpoint",
    "InMemoryAuthorizationCodeStore",
    "InMemoryClientRegistry",
]
