"""Track hotspot disconnection attempts and outcomes."""

import sqlalchemy as sa
from alembic import op

revision = "0011_disconnection_tracking"
down_revision = "0010_router_grant"
branch_labels = None
depends_on = None


def upgrade():
    for name in ("router_identity", "router_session_id", "router_server_name", "disconnection_error"):
        op.add_column("sessions", sa.Column(name, sa.String(255)))
    for name in ("disconnection_requested_at", "disconnected_at"):
        op.add_column("sessions", sa.Column(name, sa.DateTime(timezone=True)))
    op.add_column(
        "sessions",
        sa.Column("disconnection_status", sa.String(20), nullable=False, server_default="not_started"),
    )
    op.create_check_constraint(
        "ck_sessions_disconnection_status",
        "sessions",
        "disconnection_status IN ('not_started', 'waiting', 'succeeded', 'failed')",
    )


def downgrade():
    op.drop_constraint("ck_sessions_disconnection_status", "sessions", type_="check")
    for name in (
        "disconnection_status", "disconnected_at", "disconnection_requested_at",
        "disconnection_error", "router_server_name", "router_session_id", "router_identity",
    ):
        op.drop_column("sessions", name)
