"""create workflow audit tables

Revision ID: 0001_workflow_audit
Revises:
Create Date: 2026-09-10
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_workflow_audit"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workflow_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("triggered_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("cooldown_days", sa.Float(), nullable=False),
        sa.Column("total_employees", sa.Integer(), nullable=False),
        sa.Column("sent_count", sa.Integer(), nullable=False),
        sa.Column("pending_review_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_runs_status_completed_at", "workflow_runs", ["status", "completed_at"])
    op.create_index("ix_workflow_runs_triggered_at", "workflow_runs", ["triggered_at"])

    op.create_table(
        "workflow_email_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=False),
        sa.Column("employee_id", sa.String(length=255), nullable=False),
        sa.Column("employee_name", sa.String(length=255), nullable=False),
        sa.Column("employee_email", sa.String(length=320), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("allocated_leave", sa.Float(), nullable=False),
        sa.Column("used_leave", sa.Float(), nullable=False),
        sa.Column("remaining_leave", sa.Float(), nullable=False),
        sa.Column("risk_category", sa.String(length=30), nullable=False),
        sa.Column("delivery_status", sa.String(length=30), nullable=False),
        sa.Column("provider_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_email_events_workflow_run_id", "workflow_email_events", ["workflow_run_id"])
    op.create_index("ix_workflow_email_events_employee_id", "workflow_email_events", ["employee_id"])
    op.create_index("ix_workflow_email_events_status", "workflow_email_events", ["delivery_status"])


def downgrade() -> None:
    op.drop_index("ix_workflow_email_events_status", table_name="workflow_email_events")
    op.drop_index("ix_workflow_email_events_employee_id", table_name="workflow_email_events")
    op.drop_index("ix_workflow_email_events_workflow_run_id", table_name="workflow_email_events")
    op.drop_table("workflow_email_events")
    op.drop_index("ix_workflow_runs_triggered_at", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_status_completed_at", table_name="workflow_runs")
    op.drop_table("workflow_runs")
