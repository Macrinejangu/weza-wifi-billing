"""Allow only one in-flight activation attempt per session."""

import sqlalchemy as sa
from alembic import op

revision = "0007_one_started_attempt"
down_revision = "0006_bind_purchase_device"


def upgrade():
    op.create_index(
        "uq_one_started_attempt",
        "activation_attempts",
        ["session_id"],
        unique=True,
        postgresql_where=sa.text("status = 'started'"),
    )


def downgrade():
    op.drop_index("uq_one_started_attempt", table_name="activation_attempts")