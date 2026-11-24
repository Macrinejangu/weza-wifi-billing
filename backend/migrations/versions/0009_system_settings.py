"""Store operator console preferences."""

import sqlalchemy as sa
from alembic import op

revision = "0009_system_settings"
down_revision = "0008_link_paid_subscriptions"


def upgrade():
    settings = op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("maintenance_start", sa.Time()),
        sa.Column("maintenance_end", sa.Time()),
        sa.CheckConstraint("id = 1", name="ck_system_settings_singleton"),
    )
    op.bulk_insert(settings, [{"id": 1, "name": "Weza Wi-Fi Core"}])


def downgrade():
    op.drop_table("system_settings")
