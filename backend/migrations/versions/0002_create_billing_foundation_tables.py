"""create billing foundation tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-18 01:51:29.261206

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'access_points',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('location', sa.String(length=150), nullable=True),
        sa.Column('mac_address', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mac_address'),
    )
    op.create_index(op.f('ix_access_points_id'), 'access_points', ['id'], unique=False)
    op.create_table(
        'packages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('service_type', sa.String(), nullable=False),
        sa.Column('price', sa.Integer(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('download_speed_mbps', sa.Integer(), nullable=False),
        sa.Column('upload_speed_mbps', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('duration_minutes > 0', name='ck_packages_duration'),
        sa.CheckConstraint('price > 0', name='ck_packages_price'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_packages_id'), 'packages', ['id'], unique=False)
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=150), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_table(
        'purchases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('package_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('package_name', sa.String(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('download_speed_mbps', sa.Integer(), nullable=False),
        sa.Column('upload_speed_mbps', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('idempotency_key', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'paid', 'failed', 'expired')", name='ck_purchases_status'),
        sa.CheckConstraint('amount > 0', name='ck_purchases_amount'),
        sa.ForeignKeyConstraint(['package_id'], ['packages.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key'),
    )
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('package_id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['package_id'], ['packages.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_subscriptions_id'), 'subscriptions', ['id'], unique=False)
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('purchase_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('phone_number', sa.String(length=12), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('checkout_request_id', sa.String(length=100), nullable=True),
        sa.Column('merchant_request_id', sa.String(length=100), nullable=True),
        sa.Column('mpesa_receipt_number', sa.String(length=50), nullable=True),
        sa.Column('result_code', sa.Integer(), nullable=True),
        sa.Column('result_desc', sa.Text(), nullable=True),
        sa.Column('failure_reason', sa.String(length=255), nullable=True),
        sa.Column('raw_callback', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('callback_received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('initiated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('idempotency_key', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("phone_number ~ '^254[0-9]{9}$'", name='ck_payments_phone'),
        sa.CheckConstraint("status IN ('pending', 'successful', 'failed', 'expired')", name='ck_payments_status'),
        sa.CheckConstraint('amount > 0', name='ck_payments_amount'),
        sa.ForeignKeyConstraint(['purchase_id'], ['purchases.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('checkout_request_id'),
        sa.UniqueConstraint('idempotency_key'),
        sa.UniqueConstraint('mpesa_receipt_number'),
    )
    op.create_index('ix_payments_status', 'payments', ['status'], unique=False)
    op.create_index('uq_one_successful_payment', 'payments', ['purchase_id'], unique=True, postgresql_where=sa.text("status = 'successful'"))
    op.create_table(
        'payment_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payment_id', sa.Integer(), nullable=True),
        sa.Column('checkout_request_id', sa.String(length=100), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('result_code', sa.Integer(), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('processing_status', sa.String(length=20), nullable=False),
        sa.Column('error_message', sa.String(length=255), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("processing_status IN ('received', 'applied', 'duplicate', 'rejected', 'unmatched')", name='ck_events_processing_status'),
        sa.CheckConstraint("source IN ('callback', 'query')", name='ck_events_source'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_payment_events_checkout_request_id'), 'payment_events', ['checkout_request_id'], unique=False)
    op.create_table(
        'sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('package_id', sa.Integer(), nullable=False),
        sa.Column('access_point_id', sa.Integer(), nullable=True),
        sa.Column('payment_id', sa.Integer(), nullable=False),
        sa.Column('device_mac_address', sa.String(length=17), nullable=True),
        sa.Column('device_ip_address', sa.String(length=45), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('activation_status', sa.String(length=20), nullable=False),
        sa.Column('activation_requested_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_reason', sa.String(length=255), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("activation_status = 'succeeded' OR (started_at IS NULL AND expires_at IS NULL)", name='ck_sessions_timer_needs_activation'),
        sa.CheckConstraint("activation_status IN ('not_started', 'waiting', 'succeeded', 'failed')", name='ck_sessions_activation_status'),
        sa.CheckConstraint("status IN ('PENDING_PAYMENT', 'PAYMENT_CONFIRMED', 'ACTIVATING', 'ACTIVE', 'EXPIRED', 'FAILED', 'CANCELLED')", name='ck_sessions_status'),
        sa.ForeignKeyConstraint(['access_point_id'], ['access_points.id'], ),
        sa.ForeignKeyConstraint(['package_id'], ['packages.id'], ),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('payment_id'),
    )
    op.create_index(op.f('ix_sessions_activation_status'), 'sessions', ['activation_status'], unique=False)
    op.create_table(
        'activation_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.String(length=255), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('started', 'succeeded', 'failed')", name='ck_attempts_status'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'attempt_number', name='uq_attempt_number'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('activation_attempts')
    op.drop_index(op.f('ix_sessions_activation_status'), table_name='sessions')
    op.drop_table('sessions')
    op.drop_index(op.f('ix_payment_events_checkout_request_id'), table_name='payment_events')
    op.drop_table('payment_events')
    op.drop_index('uq_one_successful_payment', table_name='payments', postgresql_where=sa.text("status = 'successful'"))
    op.drop_index('ix_payments_status', table_name='payments')
    op.drop_table('payments')
    op.drop_index(op.f('ix_subscriptions_id'), table_name='subscriptions')
    op.drop_table('subscriptions')
    op.drop_table('purchases')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_packages_id'), table_name='packages')
    op.drop_table('packages')
    op.drop_index(op.f('ix_access_points_id'), table_name='access_points')
    op.drop_table('access_points')
