pq-oidc-kemtls/
├── README.md
├── requirements.txt
├── setup.py
├── .gitignore
├── LICENSE
│
├── docs/
│   ├── TechnicalDocumentation.pdf
│   ├── BenchmarkResults.pdf
│   ├── architecture.md
│   ├── security-analysis.md
│   └── api-reference.md
│
├── src/
│   ├── __init__.py
│   │
│   ├── crypto/
│   │   ├── __init__.py
│   │   ├── kyber_kem.py           # Kyber768 KEM operations
│   │   ├── dilithium_sig.py       # Dilithium3 signatures
│   │   ├── aead.py                # ChaCha20-Poly1305 AEAD
│   │   └── kdf.py                 # HKDF key derivation
│   │
│   ├── kemtls/
│   │   ├── __init__.py
│   │   ├── handshake.py           # KEMTLS handshake protocol
│   │   ├── channel.py             # Encrypted channel
│   │   └── session.py             # Session management
│   │
│   ├── oidc/
│   │   ├── __init__.py
│   │   ├── jwt_handler.py         # PQ-JWT creation/verification
│   │   ├── authorization.py       # Authorization endpoint
│   │   ├── token.py               # Token endpoint
│   │   ├── discovery.py           # Discovery endpoint
│   │   └── claims.py              # Claims processing
│   │
│   ├── pop/
│   │   ├── __init__.py
│   │   ├── client.py              # Client-side PoP proof
│   │   └── server.py              # Server-side PoP verification
│   │
│   ├── servers/
│   │   ├── __init__.py
│   │   ├── auth_server.py         # Authorization Server
│   │   └── resource_server.py     # Resource Server
│   │
│   ├── client/
│   │   ├── __init__.py
│   │   ├── oidc_client.py         # OIDC client logic
│   │   └── kemtls_client.py       # KEMTLS client
│   │
│   └── utils/
│       ├── __init__.py
│       ├── encoding.py            # Base64url encoding/decoding
│       ├── serialization.py       # Message serialization
│       └── helpers.py             # Helper functions
│
├── benchmarks/
│   ├── __init__.py
│   ├── crypto_benchmarks.py       # Cryptographic operation benchmarks
│   ├── protocol_benchmarks.py     # Protocol-level benchmarks
│   ├── end_to_end_benchmark.py    # Full flow benchmarking
│   └── compare_reference.py       # Compare with PQ-TLS reference
│
├── tests/
│   ├── __init__.py
│   ├── test_crypto.py
│   ├── test_kemtls.py
│   ├── test_oidc.py
│   ├── test_pop.py
│   ├── test_integration.py
│   └── test_security.py
│
├── demos/
│   ├── __init__.py
│   ├── demo_full_flow.py          # Complete authentication demo
│   ├── demo_kemtls.py             # KEMTLS handshake demo
│   └── demo_pop.py                # PoP mechanism demo
│
├── config/
│   ├── auth_server_config.json
│   ├── resource_server_config.json
│   └── client_config.json
│
└── scripts/
    ├── run_auth_server.py
    ├── run_resource_server.py
    ├── run_client.py
    ├── run_benchmarks.py
    └── generate_keys.py