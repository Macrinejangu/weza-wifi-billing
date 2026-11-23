"""Bind the verified hotspot device to its purchase."""

import sqlalchemy as sa
from alembic import op

revision = "0006_bind_purchase_device"
down_revision = "0005"


def upgrade():
    op.add_column("purchases", sa.Column("device_mac_address", sa.String(17)))
    op.add_column("purchases", sa.Column("device_ip_address", sa.String(45)))


def downgrade():
    op.drop_column("purchases", "device_ip_address")
    op.drop_column("purchases", "device_mac_address")
