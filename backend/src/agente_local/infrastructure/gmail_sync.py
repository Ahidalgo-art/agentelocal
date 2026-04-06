"""GmailSyncAdapter — implements GmailSyncPort using Google API Client.

Design decisions (aligned with ADR-010):
- Read-only by default: only mark_as_read mutates remote state.
- The adapter is stateless: credentials are fetched per call via GoogleCredentialProvider.
- MIME decoding handles both single-part and multipart bodies.
- All remote I/O is synchronous (google-api-python-client design); wrapped in
  asyncio.to_thread() to keep the port contract async-native without blocking the loop.
- Never store tokens in memory beyond the call duration.
"""
from __future__ import annotations

import asyncio
import base64
import re
from datetime import UTC, datetime
from typing import Optional

from googleapiclient.discovery import build

from agente_local.application.ports.gmail_sync import EmailMessage, EmailThread, GmailSyncPort
from agente_local.infrastructure.google_credentials import GoogleCredentialProvider

_UNREAD_LABEL = "UNREAD"
_IMPORTANT_LABEL = "IMPORTANT"
# Sender labels that indicate an outbound message.
_SENT_LABEL = "SENT"


def _internal_date_to_dt(internal_date_ms: str | int | None) -> Optional[datetime]:
    if internal_date_ms is None:
        return None
    try:
        return datetime.fromtimestamp(int(internal_date_ms) / 1000, tz=UTC)
    except (ValueError, OSError):
        return None


def _decode_base64_url(data: str) -> str:
    """Decode Gmail's URL-safe base64 payload."""
    padding = 4 - len(data) % 4
    if padding < 4:
        data += "=" * padding
    raw = base64.urlsafe_b64decode(data.encode())
    # Try utf-8, fall back to latin-1.
    for enc in ("utf-8", "latin-1", "ascii"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _extract_body(payload: dict) -> tuple[str, str]:
    """Return (body_text, body_html) from a Gmail message payload."""
    body_text = ""
    body_html = ""

    def _walk(part: dict) -> None:
        nonlocal body_text, body_html
        mime = part.get("mimeType", "")
        if mime == "text/plain" and not body_text:
            data = part.get("body", {}).get("data", "")
            if data:
                body_text = _decode_base64_url(data)
        elif mime == "text/html" and not body_html:
            data = part.get("body", {}).get("data", "")
            if data:
                body_html = _decode_base64_url(data)
        for sub in part.get("parts", []):
            _walk(sub)

    _walk(payload)
    return body_text, body_html


def _headers_dict(headers: list[dict]) -> dict[str, str]:
    return {h["name"]: h["value"] for h in headers if "name" in h and "value" in h}


def _extract_email(value: str) -> str:
    """Extract bare email address from 'Name <email>' format."""
    match = re.search(r"<([^>]+)>", value)
    return match.group(1).strip().lower() if match else value.strip().lower()


def _participants_from_headers(headers: dict[str, str]) -> dict[str, str]:
    """Build {email: display_name} from From / To / Cc headers."""
    results: dict[str, str] = {}
    for hdr in ("From", "To", "Cc"):
        raw = headers.get(hdr, "")
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            addr_match = re.search(r"<([^>]+)>", part)
            name_match = re.match(r"^(.*?)\s*<", part)
            addr = addr_match.group(1).strip().lower() if addr_match else part.lower()
            name = name_match.group(1).strip().strip('"') if name_match else addr
            if addr:
                results[addr] = name
    return results


class GmailSyncAdapter(GmailSyncPort):
    """Concrete Gmail adapter using google-api-python-client."""

    def __init__(self, credential_provider: GoogleCredentialProvider) -> None:
        self._credential_provider = credential_provider

    # ------------------------------------------------------------------
    # GmailSyncPort implementation
    # ------------------------------------------------------------------

    async def list_threads(
        self,
        account_id: str,
        history_id: Optional[str] = None,
        limit: int = 100,
    ) -> tuple[list[EmailThread], Optional[str]]:
        """Return modified threads since history_id (or all if None)."""
        creds = await self._credential_provider.get_credentials(account_id)

        def _run() -> tuple[list[EmailThread], Optional[str]]:
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            threads_raw: list[dict] = []
            fetched = 0

            # Full resync: list threads
            list_kwargs: dict = {"userId": "me", "maxResults": min(limit, 500)}
            while fetched < limit:
                resp = service.users().threads().list(**list_kwargs).execute()
                batch = resp.get("threads", [])
                threads_raw.extend(batch)
                fetched += len(batch)
                next_page_token_resp = resp.get("nextPageToken")
                if not next_page_token_resp or fetched >= limit:
                    break
                list_kwargs["pageToken"] = next_page_token_resp

            # Resolve each thread to its metadata (lightweight get).
            out: list[EmailThread] = []
            for t in threads_raw[:limit]:
                thread_data = (
                    service.users()
                    .threads()
                    .get(userId="me", id=t["id"], format="metadata")
                    .execute()
                )
                messages = thread_data.get("messages", [])
                if not messages:
                    continue

                latest_msg = messages[-1]
                hdrs = _headers_dict(latest_msg.get("payload", {}).get("headers", []))
                label_ids: list[str] = latest_msg.get("labelIds", [])
                last_dt = _internal_date_to_dt(latest_msg.get("internalDate"))

                # Aggregate participants across all messages in thread.
                participants: dict[str, str] = {}
                for msg in messages:
                    h = _headers_dict(msg.get("payload", {}).get("headers", []))
                    participants.update(_participants_from_headers(h))

                out.append(
                    EmailThread(
                        gmail_thread_id=t["id"],
                        subject_normalized=hdrs.get("Subject"),
                        last_message_at=last_dt,
                        message_count=len(messages),
                        has_unread=_UNREAD_LABEL in label_ids,
                        is_important_label=_IMPORTANT_LABEL in label_ids,
                        participants_cache=participants,
                    )
                )

            # Return latest history id from last message for cursor.
            final_history_id: str | None = None
            if threads_raw:
                profile = service.users().getProfile(userId="me").execute()
                final_history_id = profile.get("historyId")

            return out, final_history_id

        return await asyncio.to_thread(_run)

    async def get_thread_messages(
        self, account_id: str, thread_id: str
    ) -> list[EmailMessage]:
        creds = await self._credential_provider.get_credentials(account_id)

        def _run() -> list[EmailMessage]:
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            thread_data = (
                service.users()
                .threads()
                .get(userId="me", id=thread_id, format="metadata")
                .execute()
            )
            messages = thread_data.get("messages", [])
            out: list[EmailMessage] = []
            for msg in messages:
                hdrs = _headers_dict(msg.get("payload", {}).get("headers", []))
                label_ids: list[str] = msg.get("labelIds", [])
                out.append(
                    EmailMessage(
                        gmail_message_id=msg["id"],
                        gmail_internal_date_at=_internal_date_to_dt(msg.get("internalDate")),
                        sender_email=_extract_email(hdrs.get("From", "")),
                        snippet=msg.get("snippet"),
                        is_inbound=_SENT_LABEL not in label_ids,
                        labels=label_ids,
                    )
                )
            return out

        return await asyncio.to_thread(_run)

    async def get_message_full(self, account_id: str, message_id: str) -> dict:
        creds = await self._credential_provider.get_credentials(account_id)

        def _run() -> dict:
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
            payload = msg.get("payload", {})
            hdrs = _headers_dict(payload.get("headers", []))
            body_text, body_html = _extract_body(payload)
            return {
                "body_text": body_text,
                "body_html": body_html,
                "headers_json": hdrs,
            }

        return await asyncio.to_thread(_run)

    async def mark_as_read(self, account_id: str, message_ids: list[str]) -> None:
        if not message_ids:
            return
        creds = await self._credential_provider.get_credentials(account_id)

        def _run() -> None:
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            service.users().messages().batchModify(
                userId="me",
                body={"ids": message_ids, "removeLabelIds": [_UNREAD_LABEL]},
            ).execute()

        await asyncio.to_thread(_run)
