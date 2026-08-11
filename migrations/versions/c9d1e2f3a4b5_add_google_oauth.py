"""add google oauth identity

Revision ID: c9d1e2f3a4b5
Revises: a32570deb37a
Create Date: 2026-08-11 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c9d1e2f3a4b5"
down_revision = "a32570deb37a"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("google_sub", sa.String(length=255), nullable=True))
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=256),
            nullable=True,
        )
    with op.batch_alter_table("users") as batch_op:
        batch_op.create_index("ix_users_google_sub", ["google_sub"], unique=True)


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_google_sub")
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=256),
            nullable=False,
        )
        batch_op.drop_column("google_sub")
