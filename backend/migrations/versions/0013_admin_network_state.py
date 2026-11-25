"""Record access point addresses and the last verified gateway reading."""

import sqlalchemy as sa
from alembic import op

revision = "0013_admin_network_state"
down_revision = "0012_support_faqs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("access_points", sa.Column("management_ip", sa.String(45)))
    op.add_column("routers", sa.Column("hotspot_enabled", sa.Boolean()))
    op.add_column("routers", sa.Column("last_synced_at", sa.DateTime(timezone=True)))


def downgrade():
    op.drop_column("routers", "last_synced_at")
    op.drop_column("routers", "hotspot_enabled")
    op.drop_column("access_points", "management_ip")
