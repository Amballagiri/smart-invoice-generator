"""add AI conversations

Revision ID: c8fd1b7e42aa
Revises: bc42f1a8d715
Create Date: 2026-08-06 18:25:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c8fd1b7e42aa"
down_revision = "bc42f1a8d715"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("ai_conversations") as batch_op:
        batch_op.create_index("ix_ai_conversations_user_id", ["user_id"])
        batch_op.create_index("ix_ai_conversations_created_at", ["created_at"])


def downgrade():
    with op.batch_alter_table("ai_conversations") as batch_op:
        batch_op.drop_index("ix_ai_conversations_created_at")
        batch_op.drop_index("ix_ai_conversations_user_id")
    op.drop_table("ai_conversations")
