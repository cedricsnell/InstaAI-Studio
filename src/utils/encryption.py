"""
Token encryption utilities for InstaAI Studio.

Instagram access tokens are encrypted at rest using Fernet symmetric encryption.
The encryption key is loaded from the TOKEN_ENCRYPTION_KEY environment variable.

To generate a key:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Store the output as TOKEN_ENCRYPTION_KEY in your .env file.
"""
import os
import logging
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """Load and return a Fernet instance from the TOKEN_ENCRYPTION_KEY env var."""
    key = os.getenv("TOKEN_ENCRYPTION_KEY")
    if not key:
        raise ValueError(
            "TOKEN_ENCRYPTION_KEY environment variable is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


class EncryptedText(TypeDecorator):
    """
    SQLAlchemy column type that transparently encrypts and decrypts text values.

    Encryption uses Fernet (AES-128-CBC + HMAC-SHA256).
    The plaintext is encrypted before writing and decrypted after reading,
    so all existing code that accesses the column value works unchanged.
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Encrypt plaintext before writing to the database."""
        if value is None:
            return None
        fernet = _get_fernet()
        return fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def process_result_value(self, value, dialect):
        """Decrypt ciphertext after reading from the database."""
        if value is None:
            return None
        fernet = _get_fernet()
        try:
            return fernet.decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, Exception) as e:
            # Log and re-raise — a decryption failure indicates a key mismatch
            # or data corruption and should not be silently swallowed.
            logger.error("Failed to decrypt token — possible key mismatch or corrupted data: %s", e)
            raise ValueError("Token decryption failed. Check TOKEN_ENCRYPTION_KEY.") from e
