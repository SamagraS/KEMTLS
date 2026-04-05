"""
PDK (Pre-Distributed Key) Trust Store

Manages trusted ML-KEM public keys for identities. 
Enforces strict lookup and identity verification.
"""

from typing import Dict, Any, Optional, List


class PDKTrustStore:
    """
    Class for managing and resolving trusted ML-KEM public keys.
    """
    
    def __init__(self):
        """
        Initialize the PDK trust store with an empty local key repository.
        """
        # Internal storage map: { key_id: {identity, ml_kem_public_key, metadata} }
        self._store: Dict[str, Dict[str, Any]] = {}
    
    def add_entry(self, key_id: str, identity: str, ml_kem_public_key: bytes, metadata: Optional[Dict[str, Any]] = None):
        """
        Add a trusted key entry to the PDK store.
        
        Args:
            key_id: Unique identifier for the key
            identity: Name or identity associated with the key
            ml_kem_public_key: Binary ML-KEM public key
            metadata: Optional dictionary for additional context
        """
        if not isinstance(key_id, str):
            raise TypeError("key_id must be a string")
        if not isinstance(identity, str):
            raise TypeError("identity must be a string")
        if not isinstance(ml_kem_public_key, bytes):
            raise TypeError("ml_kem_public_key must be bytes")
            
        self._store[key_id] = {
            'key_id': key_id,
            'identity': identity,
            'ml_kem_public_key': ml_kem_public_key,
            'metadata': metadata or {}
        }
    
    def get_entry_by_id(self, key_id: str) -> Dict[str, Any]:
        """
        Retrieve a trusted key entry by its unique ID.
        
        Args:
            key_id: Unique identifier for the key
            
        Returns:
            Dict: Key entry summary
            
        Raises:
            KeyError: If key_id is not found in the trust store
        """
        if key_id not in self._store:
            raise KeyError(f"Key ID '{key_id}' not found in PDK trust store")
        return self._store[key_id]
    
    def get_entry_by_identity(self, identity: str) -> Dict[str, Any]:
        """
        Retrieve a trusted key entry by identity.
        
        Args:
            identity: Expected identity to search for
            
        Returns:
            Dict: The single matching key entry
            
        Raises:
            ValueError: If no key or more than one key is found for this identity
        """
        matches = [entry for entry in self._store.values() if entry['identity'] == identity]
        
        if not matches:
            raise ValueError(f"No trusted keys found for identity '{identity}'")
        if len(matches) > 1:
            raise ValueError(f"Ambiguous identity: multiple keys found for identity '{identity}'")
        
        return matches[0]
    
    def resolve_expected_identity(self, identity: str, key_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Resolve and verify a trusted key entry based on identity and optional key ID.
        
        Args:
            identity: Expected identity to verify
            key_id: Optional specific key ID to expect
            
        Returns:
            Dict: The resolved and verified key entry
            
        Raises:
            KeyError, ValueError: On lookup failure or identity mismatch
        """
        if key_id:
            # Case 1: Look up by specific ID, then verify identity
            entry = self.get_entry_by_id(key_id)
            if entry['identity'] != identity:
                raise ValueError(
                    f"Identity mismatch: Key '{key_id}' is for '{entry['identity']}', but expected '{identity}'"
                )
            return entry
        else:
            # Case 2: Look up solely by identity; ensure it is unambiguous
            return self.get_entry_by_identity(identity)
