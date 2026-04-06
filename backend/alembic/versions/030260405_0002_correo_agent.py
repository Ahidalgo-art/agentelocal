"""create_correo_agent_schema

Revision ID: 002_correo_agent
Revises: 001_base
Create Date: 2026-04-05

P0 schema for email + calendar agent:
- workspace_account
- oauth_credential_ref
- gmail_thread, gmail_message
- gmail_label_snapshot
- calendar_source, calendar_event
- sync_cursor, sync_run
- triage_decision
- draft_suggestion, approval_decision
- gmail_draft_binding
- audit_event
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002_correo_agent"
down_revision = "001_base"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Phase 1: Base tables
    op.create_table(
        "workspace_account",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default="google"),
        sa.Column("external_account_email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("oauth_subject", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_account_email"),
    )

    op.create_table(
        "oauth_credential_ref",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_mode", sa.String(32), nullable=False),
        sa.Column("encrypted_refresh_token", sa.LargeBinary(), nullable=True),
        sa.Column("encrypted_access_token", sa.LargeBinary(), nullable=True),
        sa.Column("token_expiry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes_hash", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["account_id"], ["workspace_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_oauth_account_status", "oauth_credential_ref", ["account_id", "status"])

    op.create_table(
        "gmail_label_snapshot",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gmail_label_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("label_list_visibility", sa.String(32), nullable=True),
        sa.Column("message_list_visibility", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["account_id"], ["workspace_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "gmail_label_id"),
    )

    op.create_table(
        "calendar_source",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("google_calendar_id", sa.String(255), nullable=False),
        sa.Column("summary", sa.String(255), nullable=True),
        sa.Column("primary_flag", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("selected_flag", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("timezone", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["account_id"], ["workspace_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "google_calendar_id"),
    )

    op.create_table(
        "sync_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_type", sa.String(32), nullable=False),
        sa.Column("resource_key", sa.String(255), nullable=False),
        sa.Column("mode", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("items_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_upserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("meta_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(["account_id"], ["workspace_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sync_run_account_resource", "sync_run", ["account_id", "resource_type", "started_at"], postgresql_ops={"started_at": "DESC"})
    op.create_index("ix_sync_run_status", "sync_run", ["status", "started_at"], postgresql_ops={"started_at": "DESC"})

    # Phase 2: Core aggregates
    op.create_table(
        "gmail_thread",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gmail_thread_id", sa.String(64), nullable=False),
        sa.Column("subject_normalized", sa.Text(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("participants_cache", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("labels_cache", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("has_unread", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_starred", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_important_label", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_history_id", sa.String(255), nullable=True),
        sa.Column("agent_state", sa.String(32), nullable=False, server_default="'discovered'"),
        sa.Column("requires_response", sa.Boolean(), nullable=True),
        sa.Column("last_triaged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["account_id"], ["workspace_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "gmail_thread_id"),
    )
    op.create_index("ix_gmail_thread_account_time", "gmail_thread", ["account_id", "last_message_at"], postgresql_ops={"last_message_at": "DESC"})
    op.create_index("ix_gmail_thread_account_state", "gmail_thread", ["account_id", "agent_state"])
    op.create_index("ix_gmail_thread_unread", "gmail_thread", ["account_id", "has_unread", "last_message_at"], postgresql_ops={"last_message_at": "DESC"})
    op.create_index("ix_gmail_thread_participants", "gmail_thread", ["participants_cache"], postgresql_using="gin")

    op.create_table(
        "gmail_message",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gmail_message_id", sa.String(64), nullable=False),
        sa.Column("gmail_internal_date_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sender_email", sa.String(255), nullable=True),
        sa.Column("recipient_to", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("recipient_cc", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("message_id_header", sa.String(255), nullable=True),
        sa.Column("in_reply_to_header", sa.String(255), nullable=True),
        sa.Column("references_header", sa.Text(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("headers_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("label_ids_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("payload_hash", sa.String(64), nullable=True),
        sa.Column("is_inbound", sa.Boolean(), nullable=False),
        sa.Column("is_latest_in_thread", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["thread_id"], ["gmail_thread.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id", "gmail_message_id"),
    )
    op.create_index("ix_gmail_message_thread_time", "gmail_message", ["thread_id", "gmail_internal_date_at"])
    op.create_index("ix_gmail_message_latest", "gmail_message", ["thread_id", "is_latest_in_thread"])
    op.create_index("ix_gmail_message_sender", "gmail_message", ["sender_email"])

    op.create_table(
        "calendar_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("calendar_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("google_event_id", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("summary", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("organizer_email", sa.String(255), nullable=True),
        sa.Column("attendees_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("all_day", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("meet_link", sa.String(255), nullable=True),
        sa.Column("etag", sa.String(255), nullable=True),
        sa.Column("updated_remote_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["calendar_source_id"], ["calendar_source.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("calendar_source_id", "google_event_id"),
    )
    op.create_index("ix_calendar_event_time", "calendar_event", ["calendar_source_id", "starts_at"])
    op.create_index("ix_calendar_event_updated", "calendar_event", ["calendar_source_id", "updated_remote_at"])
    op.create_index("ix_calendar_event_attendees", "calendar_event", ["attendees_json"], postgresql_using="gin")

    # Phase 3: Sync and history
    op.create_table(
        "sync_cursor",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_type", sa.String(32), nullable=False),
        sa.Column("resource_key", sa.String(255), nullable=False),
        sa.Column("cursor_value", sa.Text(), nullable=True),
        sa.Column("cursor_status", sa.String(32), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["account_id"], ["workspace_account.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_successful_run_id"], ["sync_run.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "resource_type", "resource_key"),
    )
    op.create_index("ix_sync_cursor_key", "sync_cursor", ["account_id", "resource_type", "resource_key"])
    op.create_index("ix_sync_cursor_status", "sync_cursor", ["resource_type", "cursor_status"])

    op.create_table(
        "triage_decision",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_version", sa.String(32), nullable=False),
        sa.Column("importance_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("requires_response", sa.Boolean(), nullable=False),
        sa.Column("priority_bucket", sa.String(32), nullable=False),
        sa.Column("reasons_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("signals_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("calendar_context_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["account_id"], ["workspace_account.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["thread_id"], ["gmail_thread.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_triage_thread", "triage_decision", ["thread_id", "decided_at"], postgresql_ops={"decided_at": "DESC"})
    op.create_index("ix_triage_priority", "triage_decision", ["account_id", "priority_bucket", "decided_at"], postgresql_ops={"decided_at": "DESC"})

    # Phase 4: Drafting and approval
    op.create_table(
        "draft_suggestion",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("triage_decision_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("intent", sa.String(32), nullable=False),
        sa.Column("model_name", sa.String(64), nullable=True),
        sa.Column("prompt_version", sa.String(32), nullable=False),
        sa.Column("input_context_hash", sa.String(255), nullable=False),
        sa.Column("summary_for_user", sa.Text(), nullable=False),
        sa.Column("why_this_reply", sa.Text(), nullable=False),
        sa.Column("missing_information_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("draft_subject", sa.String(255), nullable=True),
        sa.Column("draft_body_text", sa.Text(), nullable=False),
        sa.Column("draft_body_html", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["account_id"], ["workspace_account.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["thread_id"], ["gmail_thread.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triage_decision_id"], ["triage_decision.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_draft_thread", "draft_suggestion", ["thread_id", "created_at"], postgresql_ops={"created_at": "DESC"})
    op.create_index("ix_draft_status", "draft_suggestion", ["status", "created_at"], postgresql_ops={"created_at": "DESC"})
    op.create_index("ix_draft_triage", "draft_suggestion", ["triage_decision_id"])

    op.create_table(
        "approval_decision",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("draft_suggestion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("edited_body_text", sa.Text(), nullable=True),
        sa.Column("edited_body_html", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("decided_by", sa.String(255), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["draft_suggestion_id"], ["draft_suggestion.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_draft", "approval_decision", ["draft_suggestion_id", "decided_at"], postgresql_ops={"decided_at": "DESC"})

    op.create_table(
        "gmail_draft_binding",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("draft_suggestion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gmail_draft_id", sa.String(255), nullable=False),
        sa.Column("gmail_message_id", sa.String(255), nullable=True),
        sa.Column("created_remote_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_status", sa.String(32), nullable=False, server_default="'created'"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["draft_suggestion_id"], ["draft_suggestion.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draft_suggestion_id"),
        sa.UniqueConstraint("gmail_draft_id"),
    )

    op.create_table(
        "audit_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aggregate_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("trace_id", sa.String(255), nullable=False),
        sa.Column("actor_type", sa.String(32), nullable=False),
        sa.Column("actor_id", sa.String(255), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["account_id"], ["workspace_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_account", "audit_event", ["account_id", "occurred_at"], postgresql_ops={"occurred_at": "DESC"})
    op.create_index("ix_audit_aggregate", "audit_event", ["aggregate_type", "aggregate_id", "occurred_at"], postgresql_ops={"occurred_at": "DESC"})
    op.create_index("ix_audit_trace", "audit_event", ["trace_id"])


def downgrade() -> None:
    # Drop in reverse order
    op.drop_index("ix_audit_trace", table_name="audit_event")
    op.drop_index("ix_audit_aggregate", table_name="audit_event")
    op.drop_index("ix_audit_account", table_name="audit_event")
    op.drop_table("audit_event")

    op.drop_table("gmail_draft_binding")

    op.drop_index("ix_approval_draft", table_name="approval_decision")
    op.drop_table("approval_decision")

    op.drop_index("ix_draft_triage", table_name="draft_suggestion")
    op.drop_index("ix_draft_status", table_name="draft_suggestion")
    op.drop_index("ix_draft_thread", table_name="draft_suggestion")
    op.drop_table("draft_suggestion")

    op.drop_index("ix_triage_priority", table_name="triage_decision")
    op.drop_index("ix_triage_thread", table_name="triage_decision")
    op.drop_table("triage_decision")

    op.drop_index("ix_sync_cursor_status", table_name="sync_cursor")
    op.drop_index("ix_sync_cursor_key", table_name="sync_cursor")
    op.drop_table("sync_cursor")

    op.drop_index("ix_calendar_event_attendees", table_name="calendar_event")
    op.drop_index("ix_calendar_event_updated", table_name="calendar_event")
    op.drop_index("ix_calendar_event_time", table_name="calendar_event")
    op.drop_table("calendar_event")

    op.drop_index("ix_gmail_message_sender", table_name="gmail_message")
    op.drop_index("ix_gmail_message_latest", table_name="gmail_message")
    op.drop_index("ix_gmail_message_thread_time", table_name="gmail_message")
    op.drop_table("gmail_message")

    op.drop_index("ix_gmail_thread_participants", table_name="gmail_thread")
    op.drop_index("ix_gmail_thread_unread", table_name="gmail_thread")
    op.drop_index("ix_gmail_thread_account_state", table_name="gmail_thread")
    op.drop_index("ix_gmail_thread_account_time", table_name="gmail_thread")
    op.drop_table("gmail_thread")

    op.drop_index("ix_sync_run_status", table_name="sync_run")
    op.drop_index("ix_sync_run_account_resource", table_name="sync_run")
    op.drop_table("sync_run")

    op.drop_table("calendar_source")

    op.drop_table("gmail_label_snapshot")

    op.drop_index("ix_oauth_account_status", table_name="oauth_credential_ref")
    op.drop_table("oauth_credential_ref")

    op.drop_table("workspace_account")
