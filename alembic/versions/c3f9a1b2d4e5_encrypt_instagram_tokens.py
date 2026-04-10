"""Encrypt Instagram access and refresh tokens at rest

Revision ID: c3f9a1b2d4e5
Revises: 85beb1ac062d
Create date: 2026-04-03

This is a data migration. The schema (column types) does not change —
both access_token and refresh_token remain TEXT columns. This migration
encrypts any existing plaintext values using Fernet (TOKEN_ENCRYPTION_KEY).

Running this migration on a table with no rows is a safe no-op.
Running it twice on already-encrypted data will fail (as intended —
double-encrypting would corrupt tokens). Guard against this by only
running it once, immediately after deploying the EncryptedText column change.
"""
import os
import logging
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# revision identifiers
revision = 'c3f9a1b2d4e5'
down_revision = '85beb1ac062d'
branch_labels = None
depends_on = None


def _get_fernet():
    """Load Fernet key from environment."""
    from cryptography.fernet import Fernet
    key = os.getenv("TOKEN_ENCRYPTION_KEY")
    if not key:
        raise ValueError(
            "TOKEN_ENCRYPTION_KEY must be set before running this migration. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def upgrade() -> None:
    """Encrypt all existing plaintext tokens in instagram_accounts."""
    bind = op.get_bind()
    session = Session(bind=bind)

    try:
        fernet = _get_fernet()

        rows = bind.execute(
            sa.text("SELECT id, access_token, refresh_token FROM instagram_accounts")
        ).fetchall()

        if not rows:
            logger.info("No instagram_accounts rows to migrate — skipping encryption pass.")
            return

        logger.info(f"Encrypting tokens for {len(rows)} Instagram account(s)...")

        for row in rows:
            account_id, access_token, refresh_token = row

            encrypted_access = fernet.encrypt(access_token.encode("utf-8")).decode("ascii")
            encrypted_refresh = (
                fernet.encrypt(refresh_token.encode("utf-8")).decode("ascii")
                if refresh_token else None
            )

            bind.execute(
                sa.text(
                    "UPDATE instagram_accounts "
                    "SET access_token = :access_token, refresh_token = :refresh_token "
                    "WHERE id = :id"
                ),
                {
                    "access_token": encrypted_access,
                    "refresh_token": encrypted_refresh,
                    "id": account_id,
                }
            )

        logger.info("Token encryption migration complete.")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def downgrade() -> None:
    """Decrypt tokens back to plaintext (requires the same TOKEN_ENCRYPTION_KEY)."""
    bind = op.get_bind()
    session = Session(bind=bind)

    try:
        fernet = _get_fernet()

        rows = bind.execute(
            sa.text("SELECT id, access_token, refresh_token FROM instagram_accounts")
        ).fetchall()

        if not rows:
            return

        logger.info(f"Decrypting tokens for {len(rows)} Instagram account(s)...")

        for row in rows:
            account_id, access_token, refresh_token = row

            decrypted_access = fernet.decrypt(access_token.encode("ascii")).decode("utf-8")
            decrypted_refresh = (
                fernet.decrypt(refresh_token.encode("ascii")).decode("utf-8")
                if refresh_token else None
            )

            bind.execute(
                sa.text(
                    "UPDATE instagram_accounts "
                    "SET access_token = :access_token, refresh_token = :refresh_token "
                    "WHERE id = :id"
                ),
                {
                    "access_token": decrypted_access,
                    "refresh_token": decrypted_refresh,
                    "id": account_id,
                }
            )

        logger.info("Token decryption (downgrade) complete.")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
