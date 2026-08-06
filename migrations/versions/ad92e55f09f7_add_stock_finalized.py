"""add stock finalized

Revision ID: ad92e55f09f7
Revises: eeb66ae6c333
Create Date: 2026-08-06 10:33:56.469898

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "ad92e55f09f7"
down_revision = "eeb66ae6c333"
branch_labels = None
depends_on = None


def upgrade():
    # Create inventory_history table
    op.create_table(
        "inventory_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=True),
        sa.Column("quantity_change", sa.Numeric(12, 3), nullable=False),
        sa.Column("stock_after", sa.Numeric(12, 3), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("inventory_history") as batch_op:
        batch_op.create_index("ix_inventory_history_invoice_id", ["invoice_id"])
        batch_op.create_index("ix_inventory_history_product_id", ["product_id"])
        batch_op.create_index("ix_inventory_history_user_id", ["user_id"])

    # Add stock_finalized column
    with op.batch_alter_table("invoices") as batch_op:
        batch_op.add_column(
            sa.Column(
                "stock_finalized",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade():
    # Remove stock_finalized column
    with op.batch_alter_table("invoices") as batch_op:
        batch_op.drop_column("stock_finalized")

    # Drop indexes
    with op.batch_alter_table("inventory_history") as batch_op:
        batch_op.drop_index("ix_inventory_history_user_id")
        batch_op.drop_index("ix_inventory_history_product_id")
        batch_op.drop_index("ix_inventory_history_invoice_id")

    # Drop table
    op.drop_table("inventory_history")