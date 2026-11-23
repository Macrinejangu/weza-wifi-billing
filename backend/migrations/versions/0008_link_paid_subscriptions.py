"""Link verified payments, subscriptions, and access sessions."""

import sqlalchemy as sa
from alembic import op

revision = "0008_link_paid_subscriptions"
down_revision = "0007_one_started_attempt"


def upgrade():
    op.add_column("subscriptions", sa.Column("payment_id", sa.Integer()))
    op.create_foreign_key("fk_subscriptions_payment", "subscriptions", "payments", ["payment_id"], ["id"])
    op.create_unique_constraint("uq_subscriptions_payment", "subscriptions", ["payment_id"])
    op.add_column("sessions", sa.Column("subscription_id", sa.Integer()))
    op.create_foreign_key("fk_sessions_subscription", "sessions", "subscriptions", ["subscription_id"], ["id"])
    op.create_unique_constraint("uq_sessions_subscription", "sessions", ["subscription_id"])


def downgrade():
    op.drop_column("sessions", "subscription_id")
    op.drop_column("subscriptions", "payment_id")
