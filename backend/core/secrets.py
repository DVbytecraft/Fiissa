"""
Chiffrement authentifié AES-256-GCM pour les secrets applicatifs.
Remplace l'ancien XOR homebrew — AESGCM offre confidentialité + intégrité.
"""

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from core.config import settings

_NONCE_SIZE = 12  # 96-bit nonce standard GCM


def _derive_key() -> bytes:
    """Dérive une clé 256-bit depuis SECRET_KEY via SHA-256."""
    return hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()


def encrypt_secret(value: str) -> str:
    """
    Chiffre une valeur avec AES-256-GCM.
    Format du token : base64url(nonce[12] + ciphertext+tag)
    """
    key = _derive_key()
    nonce = os.urandom(_NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, value.encode("utf-8"), None)
    token = nonce + ciphertext
    return base64.urlsafe_b64encode(token).decode("ascii")


def decrypt_secret(token: str) -> str:
    """
    Déchiffre un token produit par encrypt_secret.
    Lève ValueError si le token est corrompu ou falsifié (authentification échouée).
    """
    key = _derive_key()
    decoded = base64.urlsafe_b64decode(token.encode("ascii"))
    if len(decoded) < _NONCE_SIZE + 16:  # nonce + min GCM tag
        raise ValueError("Token de chiffrement invalide ou tronqué")
    nonce, ciphertext = decoded[:_NONCE_SIZE], decoded[_NONCE_SIZE:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def mask_secret(value: str) -> str:
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}***{value[-2:]}"
