"""add invoice builder fields"""
from alembic import op
import sqlalchemy as sa

revision = "d45f9d1b3c20"
down_revision = "c8fd1b7e42aa"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("invoices") as batch:
        batch.add_column(sa.Column("terms", sa.Text(), nullable=True))
        batch.add_column(sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"))
        batch.add_column(sa.Column("payment_method", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("template_name", sa.String(length=30), nullable=False, server_default="Modern Blue"))
        batch.add_column(sa.Column("round_off", sa.Numeric(12, 2), nullable=False, server_default="0.00"))
    with op.batch_alter_table("invoice_items") as batch:
        batch.add_column(sa.Column("discount_percentage", sa.Numeric(5, 2), nullable=False, server_default="0.00"))
        batch.add_column(sa.Column("description", sa.String(length=500), nullable=True))

def downgrade():
    with op.batch_alter_table("invoice_items") as batch:
        batch.drop_column("description")
        batch.drop_column("discount_percentage")
    with op.batch_alter_table("invoices") as batch:
        batch.drop_column("round_off")
        batch.drop_column("template_name")
        batch.drop_column("payment_method")
        batch.drop_column("currency")
        batch.drop_column("terms")
