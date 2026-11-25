from alembic import op
import sqlalchemy as sa

revision = "0010_router_grant"
down_revision = "0009_system_settings"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("sessions", sa.Column("router_grant_id", sa.String(32)))
    op.create_unique_constraint("uq_sessions_router_grant_id", "sessions", ["router_grant_id"])


def downgrade():
    op.drop_constraint("uq_sessions_router_grant_id", "sessions", type_="unique")
    op.drop_column("sessions", "router_grant_id")
