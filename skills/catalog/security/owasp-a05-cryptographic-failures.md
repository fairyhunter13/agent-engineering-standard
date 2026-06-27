---
name: owasp-a05-cryptographic-failures
description: Use modern cryptographic algorithms correctly for password storage, data in transit, and data at rest — and never roll your own crypto.
discipline: security
tags: [owasp, cryptography, tls, hashing, encryption]
---

# OWASP A05: Cryptographic Failures

## When to use
Apply this skill when implementing password storage, when choosing hashing algorithms, when configuring TLS, when encrypting sensitive data at rest, or when reviewing code for cryptographic misuse.

## Signal
- Passwords stored as MD5, SHA1, or SHA256 hashes (all unsuitable for passwords).
- Data transmitted over HTTP (not HTTPS) between services or to clients.
- Symmetric encryption key hardcoded in source code or stored in plaintext environment variables.
- AES-ECB cipher mode used instead of AES-GCM.
- TLS 1.0 or 1.1 enabled on web servers (deprecated; vulnerable to BEAST, POODLE).
- `testssl.sh` scan reveals weak ciphers or expired/self-signed certificates.
- Secrets embedded in Docker images (detectable via `docker history`).

## Why
A05:2025 (previously "Sensitive Data Exposure" in 2017 OWASP Top 10) covers the misuse of cryptography that exposes sensitive data even when access control is working correctly. A correctly-hashed password database cannot be cracked offline; one using MD5 can be cracked in hours on commodity hardware. TLS failures expose data in transit to network-based attackers. Hardcoded keys mean the key is effectively public — any repository access grants the ability to decrypt. The guidance is consistent: use established algorithms at correct settings, never invent your own.

## Remediate

1. **Store passwords with a memory-hard, key-stretching algorithm.** Acceptable algorithms in 2026, in order of preference:
   - **`argon2id`** — OWASP recommended (winner of Password Hashing Competition 2015). Memory parameter ≥ 19 MiB, iteration count ≥ 2, parallelism ≥ 1.
   - **`bcrypt`** — widely supported, work factor ≥ 12 (increases to ≥ 13 in 2027).
   - **`scrypt`** — good alternative when argon2 is unavailable.
   - Never: MD5, SHA1, SHA256, SHA512, unsalted hashes, PBKDF2 with low iterations.
   ```python
   # Python — argon2-cffi
   from argon2 import PasswordHasher
   ph = PasswordHasher(memory_cost=65536, time_cost=2, parallelism=1)
   hash = ph.hash(password)
   ph.verify(hash, password)  # raises VerifyMismatchError if wrong
   ```
   ```ts
   // Node.js — argon2 package
   import argon2 from 'argon2';
   const hash = await argon2.hash(password, { type: argon2.argon2id });
   await argon2.verify(hash, password);  // throws if mismatch
   ```

2. **Enforce TLS 1.3 only; disable TLS 1.0/1.1 and weak ciphers.** Configure at your reverse proxy (nginx, Caddy, HAProxy):
   ```nginx
   ssl_protocols TLSv1.3;  # TLS 1.2 only if legacy clients require it
   ssl_ciphers 'TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256';
   ssl_prefer_server_ciphers off;
   add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";
   ```
   Verify with `testssl.sh --fast hostname` or `sslyze --regular hostname`.

3. **Encrypt sensitive data at rest with AES-256-GCM.** GCM provides both confidentiality and integrity (authenticated encryption). Never use AES-ECB — it is deterministic and leaks patterns:
   ```python
   # Python — cryptography library
   from cryptography.hazmat.primitives.ciphers.aead import AESGCM
   import os

   key = AESGCM.generate_key(bit_length=256)  # 32 bytes
   aesgcm = AESGCM(key)
   nonce = os.urandom(12)  # 96-bit nonce, never reuse
   ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
   ```
   Store the nonce alongside the ciphertext — it is not a secret but must be unique per encryption.

4. **Manage keys in a secrets manager.** Never store cryptographic keys in:
   - Source code or dotfiles (`.env`, `config.py`).
   - Database columns (unless encrypted by a KMS-managed key).
   - Container environment variables without a vault.
   Use: AWS KMS, AWS Secrets Manager, HashiCorp Vault, GCP Cloud KMS, Azure Key Vault. Rotate keys annually or on compromise.

5. **Use HMAC for message authentication codes.** When verifying that a message has not been tampered with (webhook signatures, signed URLs, CSRF tokens), use HMAC-SHA256:
   ```python
   import hmac, hashlib
   def sign(payload: bytes, secret: bytes) -> str:
       return hmac.new(secret, payload, hashlib.sha256).hexdigest()

   def verify(payload: bytes, signature: str, secret: bytes) -> bool:
       expected = sign(payload, secret)
       return hmac.compare_digest(expected, signature)  # constant-time comparison
   ```
   Always use `hmac.compare_digest()` — never `==` — to prevent timing attacks.

6. **Scan for hardcoded secrets and weak crypto patterns.** Add to CI:
   ```sh
   # gitleaks — scan for secrets
   gitleaks detect --source .

   # semgrep rules for crypto misuse
   semgrep --config "p/cryptography" .
   # Catches: MD5 use, ECB mode, hardcoded keys, weak RNG
   ```

7. **Use cryptographically secure random number generation.** For tokens, session IDs, nonces, CSRF tokens — use CSPRNG, not `Math.random()` or `random.random()`:
   ```ts
   // Node.js
   import { randomBytes } from 'crypto';
   const token = randomBytes(32).toString('hex');  // 256 bits of entropy
   ```
   ```python
   import secrets
   token = secrets.token_hex(32)  # 256 bits, CSPRNG
   ```

8. **Never roll your own cryptographic primitives.** Do not implement: block ciphers, stream ciphers, hash functions, elliptic curve operations, or key exchange protocols from scratch. Cryptographic implementation errors (timing side-channels, padding oracle vulnerabilities, nonce reuse) are subtle and catastrophic. Use audited libraries: libsodium, OpenSSL (via language wrappers), the `cryptography` Python library.

## References
- OWASP A02:2021 / A05:2025 – Cryptographic Failures
- OWASP Password Storage Cheat Sheet
- NIST SP 800-175B — Guideline for Using Cryptographic Standards
- libsodium documentation (doc.libsodium.org)
- testssl.sh (drwetter/testssl.sh)
