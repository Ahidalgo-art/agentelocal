"""Provides authenticated Google API credentials from persisted OAuth tokens.

Responsibilities:
- Load encrypted tokens from oauth_credential_ref.
- Build a google.oauth2.credentials.Credentials object.
- Refresh it when expired (using the refresh token).
- Propagate reauth_required when the refresh token is invalid.
- Never log tokens in clear text.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agente_local.infrastructure.persistence.models import OAuthCredentialRefModel

# Minimal scopes required for this agent.
REQUIRED_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/calendar.readonly",
]


class ReauthRequired(Exception):
    """Raised when the stored token cannot be refreshed (revoked / invalid)."""


class CredentialNotFound(Exception):
    """Raised when no credential row exists for the given account."""


class GoogleCredentialProvider:
    """Fetch and refresh Google OAuth2 credentials from the DB."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        client_id: str,
        client_secret: str,
        token_uri: str = "https://oauth2.googleapis.com/token",
    ) -> None:
        self._session_factory = session_factory
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_uri = token_uri

    async def get_credentials(self, account_id: str) -> Credentials:
        """Return valid Credentials for the given account_id.

        Refreshes automatically when the access token is expired.

        Raises:
            CredentialNotFound: no row in oauth_credential_ref.
            ReauthRequired: refresh token is revoked or invalid.
        """
        uid = uuid.UUID(account_id)

        async with self._session_factory() as session:
            result = await session.execute(
                select(OAuthCredentialRefModel).where(
                    OAuthCredentialRefModel.account_id == uid,
                    OAuthCredentialRefModel.status == "active",
                )
            )
            ref = result.scalar_one_or_none()

        if ref is None:
            raise CredentialNotFound(f"No active credential for account {account_id}")

        refresh_token = (
            ref.encrypted_refresh_token.decode() if ref.encrypted_refresh_token else None
        )
        access_token = (
            ref.encrypted_access_token.decode() if ref.encrypted_access_token else None
        )

        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=self._token_uri,
            client_id=self._client_id,
            client_secret=self._client_secret,
            scopes=REQUIRED_SCOPES,
            expiry=ref.token_expiry_at,
        )

        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                await self._persist_refreshed(account_id, creds)
            except RefreshError as exc:
                await self._mark_reauth_required(account_id)
                raise ReauthRequired(
                    f"Token refresh failed for account {account_id}: {exc}"
                ) from exc

        return creds

    async def _persist_refreshed(self, account_id: str, creds: Credentials) -> None:
        uid = uuid.UUID(account_id)
        now = datetime.now(UTC)

        async with self._session_factory() as session:
            result = await session.execute(
                select(OAuthCredentialRefModel).where(
                    OAuthCredentialRefModel.account_id == uid,
                    OAuthCredentialRefModel.status == "active",
                )
            )
            ref = result.scalar_one_or_none()
            if ref is None:
                return

            if creds.token:
                ref.encrypted_access_token = creds.token.encode()
            if creds.expiry:
                expiry = creds.expiry
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=UTC)
                ref.token_expiry_at = expiry
            ref.updated_at = now
            await session.commit()

    async def _mark_reauth_required(self, account_id: str) -> None:
        uid = uuid.UUID(account_id)
        now = datetime.now(UTC)

        async with self._session_factory() as session:
            result = await session.execute(
                select(OAuthCredentialRefModel).where(
                    OAuthCredentialRefModel.account_id == uid,
                    OAuthCredentialRefModel.status == "active",
                )
            )
            ref = result.scalar_one_or_none()
            if ref is None:
                return
            ref.status = "reauth_required"
            ref.updated_at = now
            await session.commit()
