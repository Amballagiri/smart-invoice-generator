"""add shop_profiles table

Per-user shop/business details for the simplified invoice workflow.

Note: the application also auto-creates tables via ``db.create_all()`` on
startup, so this table is created automatically for new/empty databases.
This migration is provided so deployments that run ``flask db upgrade`` keep
their schema in sync without losing existing records (it only adds a new table
and never alters existing tables).
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "d45f9d1b3c20"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "shop_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("shop_name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=60), nullable=True),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column("gst_number", sa.String(length=64), nullable=True),
        sa.Column("logo", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_shop_profiles_user_id"),
        "shop_profiles",
        ["user_id"],
        unique=True,
    )


def downgrade():
    op.drop_index(op.f("ix_shop_profiles_user_id"), table_name="shop_profiles")
    op.drop_table("shop_profiles")
