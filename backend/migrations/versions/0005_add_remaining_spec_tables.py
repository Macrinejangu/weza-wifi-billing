
"""Add remaining Weza database tables and constraints.

Revision ID: 0005
Revises: 0004
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def timestamp_columns():
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade():
    # 1. Routers
    op.create_table(
        "routers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("host", sa.String(255), nullable=False, unique=True),
        sa.Column("identity", sa.String(100), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            server_default="offline",
            nullable=False,
        ),
        *timestamp_columns(),
    )

    # 2. Existing user and network tables
    op.add_column(
        "users",
        sa.Column(
            "registered_mac_address",
            sa.String(17),
            nullable=True,
        ),
    )
    op.create_unique_constraint(
        "uq_users_registered_mac_address",
        "users",
        ["registered_mac_address"],
    )

    op.add_column(
        "access_points",
        sa.Column("router_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "access_points",
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_access_points_router_id",
        "access_points",
        "routers",
        ["router_id"],
        ["id"],
    )
    op.create_index(
        "ix_access_points_router_id",
        "access_points",
        ["router_id"],
    )

    op.add_column(
        "sessions",
        sa.Column("router_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_sessions_router_id",
        "sessions",
        "routers",
        ["router_id"],
        ["id"],
    )
    op.create_index(
        "ix_sessions_router_id",
        "sessions",
        ["router_id"],
    )

    # 3. Usage records
    op.create_table(
        "usage_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("sessions.id"),
            nullable=False,
        ),
        sa.Column(
            "upload_bytes",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "download_bytes",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.CheckConstraint(
            "upload_bytes >= 0",
            name="ck_usage_records_upload_bytes",
        ),
        sa.CheckConstraint(
            "download_bytes >= 0",
            name="ck_usage_records_download_bytes",
        ),
    )
    op.create_index(
        "ix_usage_records_session_id",
        "usage_records",
        ["session_id"],
    )

    # 4. Notifications
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "notification_type",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "is_read",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "read_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        *timestamp_columns(),
    )
    op.create_index(
        "ix_notifications_user_id",
        "notifications",
        ["user_id"],
    )

    # 5. Support tickets
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "assigned_to",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            server_default="open",
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.String(20),
            server_default="medium",
            nullable=False,
        ),
        *timestamp_columns(),
        sa.CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved', 'closed')",
            name="ck_support_tickets_status",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'medium', 'high')",
            name="ck_support_tickets_priority",
        ),
    )
    op.create_index(
        "ix_support_tickets_user_id",
        "support_tickets",
        ["user_id"],
    )

    # 6. Administrative audit logs
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "admin_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("old_values", postgresql.JSONB(), nullable=True),
        sa.Column("new_values", postgresql.JSONB(), nullable=True),
        *timestamp_columns(),
    )
    op.create_index(
        "ix_admin_audit_logs_admin_id",
        "admin_audit_logs",
        ["admin_id"],
    )

    # 7. Payment changes
    op.add_column(
        "payments",
        sa.Column(
            "payment_method",
            sa.String(30),
            server_default="mpesa",
            nullable=False,
        ),
    )
    op.create_index(
        "uq_one_pending_payment",
        "payments",
        ["purchase_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_payments_pending_initiated_at",
        "payments",
        ["initiated_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )

    # 8. Package speed constraints
    op.create_check_constraint(
        "ck_packages_download_speed",
        "packages",
        "download_speed_mbps > 0",
    )
    op.create_check_constraint(
        "ck_packages_upload_speed",
        "packages",
        "upload_speed_mbps > 0",
    )


def downgrade():
    # Reverse package and payment changes
    op.drop_constraint(
        "ck_packages_upload_speed",
        "packages",
        type_="check",
    )
    op.drop_constraint(
        "ck_packages_download_speed",
        "packages",
        type_="check",
    )

    op.drop_index(
        "ix_payments_pending_initiated_at",
        table_name="payments",
    )
    op.drop_index(
        "uq_one_pending_payment",
        table_name="payments",
    )
    op.drop_column("payments", "payment_method")

    # Remove new tables in reverse dependency order
    op.drop_index(
        "ix_admin_audit_logs_admin_id",
        table_name="admin_audit_logs",
    )
    op.drop_table("admin_audit_logs")

    op.drop_index(
        "ix_support_tickets_user_id",
        table_name="support_tickets",
    )
    op.drop_table("support_tickets")

    op.drop_index(
        "ix_notifications_user_id",
        table_name="notifications",
    )
    op.drop_table("notifications")

    op.drop_index(
        "ix_usage_records_session_id",
        table_name="usage_records",
    )
    op.drop_table("usage_records")

    # Remove router references
    op.drop_index(
        "ix_sessions_router_id",
        table_name="sessions",
    )
    op.drop_constraint(
        "fk_sessions_router_id",
        "sessions",
        type_="foreignkey",
    )
    op.drop_column("sessions", "router_id")

    op.drop_index(
        "ix_access_points_router_id",
        table_name="access_points",
    )
    op.drop_constraint(
        "fk_access_points_router_id",
        "access_points",
        type_="foreignkey",
    )
    op.drop_column("access_points", "last_seen_at")
    op.drop_column("access_points", "router_id")

    op.drop_constraint(
        "uq_users_registered_mac_address",
        "users",
        type_="unique",
    )
    op.drop_column("users", "registered_mac_address")

    op.drop_table("routers")
