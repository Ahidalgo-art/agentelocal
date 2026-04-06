"""Unit tests for GmailSyncAdapter — all Google API calls are mocked."""
from __future__ import annotations

from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agente_local.application.ports.gmail_sync import EmailMessage, EmailThread
from agente_local.infrastructure.gmail_sync import (
    GmailSyncAdapter,
    _decode_base64_url,
    _extract_body,
    _extract_email,
    _internal_date_to_dt,
    _participants_from_headers,
)


# ---------------------------------------------------------------------------
# Helpers — pure unit tests (no I/O)
# ---------------------------------------------------------------------------


def test_internal_date_to_dt_converts_milliseconds() -> None:
    dt = _internal_date_to_dt("1743840000000")  # 2025-04-05 00:00:00 UTC
    assert dt is not None
    assert dt.tzinfo == UTC


def test_internal_date_to_dt_returns_none_for_none() -> None:
    assert _internal_date_to_dt(None) is None


def test_decode_base64_url_roundtrips() -> None:
    import base64

    original = "Hello, Agente Local!"
    encoded = base64.urlsafe_b64encode(original.encode()).decode().rstrip("=")
    assert _decode_base64_url(encoded) == original


def test_extract_body_single_part() -> None:
    import base64

    text_data = base64.urlsafe_b64encode(b"plain text body").decode()
    payload = {"mimeType": "text/plain", "body": {"data": text_data}, "parts": []}
    body_text, body_html = _extract_body(payload)
    assert body_text == "plain text body"
    assert body_html == ""


def test_extract_body_multipart() -> None:
    import base64

    text_data = base64.urlsafe_b64encode(b"text part").decode()
    html_data = base64.urlsafe_b64encode(b"<p>html part</p>").decode()
    payload = {
        "mimeType": "multipart/alternative",
        "body": {},
        "parts": [
            {"mimeType": "text/plain", "body": {"data": text_data}, "parts": []},
            {"mimeType": "text/html", "body": {"data": html_data}, "parts": []},
        ],
    }
    body_text, body_html = _extract_body(payload)
    assert body_text == "text part"
    assert body_html == "<p>html part</p>"


def test_extract_email_bare_address() -> None:
    assert _extract_email("user@example.com") == "user@example.com"


def test_extract_email_with_display_name() -> None:
    assert _extract_email("Angel Hidalgo <angel@example.com>") == "angel@example.com"


def test_participants_from_headers_aggregates_addresses() -> None:
    headers = {
        "From": "Sender One <one@example.com>",
        "To": "Recipient Two <two@example.com>, three@example.com",
        "Cc": "",
    }
    participants = _participants_from_headers(headers)
    assert "one@example.com" in participants
    assert "two@example.com" in participants
    assert "three@example.com" in participants
    assert participants["one@example.com"] == "Sender One"


# ---------------------------------------------------------------------------
# GmailSyncAdapter — integration with mocked Google API client
# ---------------------------------------------------------------------------

_FAKE_THREAD_ID = "thread_abc123"
_FAKE_MESSAGE_ID = "msg_xyz789"
_FAKE_INTERNAL_DATE = "1743840000000"  # millis
_FAKE_HISTORY_ID = "12345"


def _make_fake_thread_get() -> dict:
    """Minimal thread.get() response with one message."""
    return {
        "id": _FAKE_THREAD_ID,
        "messages": [
            {
                "id": _FAKE_MESSAGE_ID,
                "internalDate": _FAKE_INTERNAL_DATE,
                "labelIds": ["INBOX", "UNREAD"],
                "snippet": "Hello from test",
                "payload": {
                    "headers": [
                        {"name": "From", "value": "Sender <sender@example.com>"},
                        {"name": "To", "value": "me@example.com"},
                        {"name": "Subject", "value": "Test subject"},
                    ]
                },
            }
        ],
    }


def _make_fake_message_full() -> dict:
    """Minimal messages.get(format=full) response."""
    import base64

    body_text = base64.urlsafe_b64encode(b"Body text here").decode()
    return {
        "id": _FAKE_MESSAGE_ID,
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "Subject", "value": "Test subject"},
            ],
            "body": {"data": body_text},
            "parts": [],
        },
    }


def _make_mock_service(
    thread_list_resp: dict | None = None,
    thread_get_resp: dict | None = None,
    message_get_resp: dict | None = None,
    profile_resp: dict | None = None,
) -> MagicMock:
    service = MagicMock()

    # threads().list().execute()
    threads_list = MagicMock()
    threads_list.execute.return_value = thread_list_resp or {
        "threads": [{"id": _FAKE_THREAD_ID}]
    }
    service.users().threads().list.return_value = threads_list

    # threads().get().execute()
    threads_get = MagicMock()
    threads_get.execute.return_value = thread_get_resp or _make_fake_thread_get()
    service.users().threads().get.return_value = threads_get

    # messages().get().execute()
    messages_get = MagicMock()
    messages_get.execute.return_value = message_get_resp or _make_fake_message_full()
    service.users().messages().get.return_value = messages_get

    # messages().batchModify().execute()
    batch_modify = MagicMock()
    batch_modify.execute.return_value = {}
    service.users().messages().batchModify.return_value = batch_modify

    # getProfile().execute()
    profile = MagicMock()
    profile.execute.return_value = profile_resp or {"historyId": _FAKE_HISTORY_ID}
    service.users().getProfile.return_value = profile

    return service


def _make_adapter() -> tuple[GmailSyncAdapter, MagicMock]:
    """Return adapter + the underlying mock service for assertions."""
    credential_provider = MagicMock()
    credential_provider.get_credentials = AsyncMock(return_value=MagicMock())

    mock_service = _make_mock_service()

    adapter = GmailSyncAdapter(credential_provider=credential_provider)
    return adapter, mock_service


@pytest.mark.asyncio
async def test_list_threads_returns_email_thread_list() -> None:
    adapter, mock_service = _make_adapter()

    with patch("agente_local.infrastructure.gmail_sync.build", return_value=mock_service):
        threads, next_history_id = await adapter.list_threads("account-1")

    assert len(threads) == 1
    thread = threads[0]
    assert isinstance(thread, EmailThread)
    assert thread.gmail_thread_id == _FAKE_THREAD_ID
    assert thread.subject_normalized == "Test subject"
    assert thread.message_count == 1
    assert thread.has_unread is True
    assert "sender@example.com" in thread.participants_cache
    assert next_history_id == _FAKE_HISTORY_ID


@pytest.mark.asyncio
async def test_list_threads_empty_when_no_threads() -> None:
    adapter, _ = _make_adapter()
    empty_service = _make_mock_service(thread_list_resp={"threads": []})

    with patch("agente_local.infrastructure.gmail_sync.build", return_value=empty_service):
        threads, history_id = await adapter.list_threads("account-1")

    assert threads == []
    assert history_id is None


@pytest.mark.asyncio
async def test_get_thread_messages_returns_email_messages() -> None:
    adapter, mock_service = _make_adapter()

    with patch("agente_local.infrastructure.gmail_sync.build", return_value=mock_service):
        messages = await adapter.get_thread_messages("account-1", _FAKE_THREAD_ID)

    assert len(messages) == 1
    msg = messages[0]
    assert isinstance(msg, EmailMessage)
    assert msg.gmail_message_id == _FAKE_MESSAGE_ID
    assert msg.sender_email == "sender@example.com"
    assert msg.is_inbound is True
    assert "UNREAD" in msg.labels


@pytest.mark.asyncio
async def test_get_message_full_returns_body_and_headers() -> None:
    adapter, mock_service = _make_adapter()

    with patch("agente_local.infrastructure.gmail_sync.build", return_value=mock_service):
        result = await adapter.get_message_full("account-1", _FAKE_MESSAGE_ID)

    assert result["body_text"] == "Body text here"
    assert "Subject" in result["headers_json"]
    assert result["headers_json"]["Subject"] == "Test subject"


@pytest.mark.asyncio
async def test_mark_as_read_calls_batch_modify() -> None:
    adapter, mock_service = _make_adapter()

    with patch("agente_local.infrastructure.gmail_sync.build", return_value=mock_service):
        await adapter.mark_as_read("account-1", [_FAKE_MESSAGE_ID])

    mock_service.users().messages().batchModify.assert_called_once()
    call_kwargs = mock_service.users().messages().batchModify.call_args.kwargs
    assert _FAKE_MESSAGE_ID in call_kwargs["body"]["ids"]
    assert "UNREAD" in call_kwargs["body"]["removeLabelIds"]


@pytest.mark.asyncio
async def test_mark_as_read_noop_for_empty_list() -> None:
    adapter, mock_service = _make_adapter()

    with patch("agente_local.infrastructure.gmail_sync.build", return_value=mock_service):
        await adapter.mark_as_read("account-1", [])

    mock_service.users().messages().batchModify.assert_not_called()
