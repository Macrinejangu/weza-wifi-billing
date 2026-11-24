"""Add RouterOS session identity and disconnection metadata.

Revision ID: b4e82b0da84f
Revises: 0005
"""

from alembic import op
import sqlalchemy as sa


revision = "b4e82b0da84f"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "sessions",
        sa.Column("router_identity", sa.String(255), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column("router_session_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column("router_server_name", sa.String(255), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "disconnection_status",
            sa.String(20),
            server_default="not_started",
            nullable=False,
        ),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "disconnection_requested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "sessions",
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column("disconnection_error", sa.String(255), nullable=True),
    )
    op.create_check_constraint(
        "ck_sessions_disconnection_status",
        "sessions",
        "disconnection_status IN ('not_started', 'waiting', 'succeeded', 'failed')",
    )


def downgrade():
    op.drop_constraint(
        "ck_sessions_disconnection_status",
        "sessions",
        type_="check",
    )
    op.drop_column("sessions", "disconnection_error")
    op.drop_column("sessions", "disconnected_at")
    op.drop_column("sessions", "disconnection_requested_at")
    op.drop_column("sessions", "disconnection_status")
    op.drop_column("sessions", "router_server_name")
    op.drop_column("sessions", "router_session_id")
    op.drop_column("sessions", "router_identity")
