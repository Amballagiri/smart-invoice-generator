"""add user profile image

Revision ID: bc42f1a8d715
Revises: ad92e55f09f7
Create Date: 2026-08-06
"""

from alembic import op
import sqlalchemy as sa


revision = "bc42f1a8d715"
down_revision = "ad92e55f09f7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("profile_image", sa.String(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("profile_image")
