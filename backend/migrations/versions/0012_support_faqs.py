"""Store the guided Wi-Fi support answers."""

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0012_support_faqs"
down_revision = "0011_disconnection_tracking"
branch_labels = None
depends_on = None


def upgrade():
    faqs = op.create_table(
        "support_faqs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question", sa.String(160), nullable=False),
        sa.Column("steps", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    seed_faqs = [
        {
            "question": "Payment received but no internet?",
            "steps": [
                "Check for the official M-Pesa confirmation message.",
                "Reconnect to Weza Wi-Fi and check your connection status.",
                "Keep your receipt reference and avoid paying again.",
            ],
        },
        {
            "question": "Didn’t receive the M-Pesa prompt?",
            "steps": [
                "Check the phone number you entered at checkout.",
                "Check for an open M-Pesa prompt on your phone.",
                "Check the status of the first payment before trying again.",
            ],
        },
        {
            "question": "Package expired?",
            "steps": [
                "Check the expiry shown in the portal.",
                "Go to Packages to choose another plan.",
            ],
        },
        {
            "question": "Account access problems?",
            "steps": [
                "Check the email address and password you entered.",
                "Reconnect to Weza Wi-Fi and reopen the portal if you lost access.",
            ],
        },
    ]
    for faq in seed_faqs:
        op.execute(faqs.insert().values(
            question=op.inline_literal(faq["question"]),
            steps=sa.cast(op.inline_literal(json.dumps(faq["steps"])), JSONB()),
        ))


def downgrade():
    op.drop_table("support_faqs")
