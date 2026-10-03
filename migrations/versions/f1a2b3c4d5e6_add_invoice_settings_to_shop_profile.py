"""add invoice settings to shop_profile

Revision ID: f1a2b3c4d5e6
Revises: 0e3064c9a873
Create Date: 2026-10-02 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = '0e3064c9a873'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('shop_profiles', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'invoice_prefix',
            sa.String(length=20),
            nullable=False,
            server_default='INV',
        ))
        batch_op.add_column(sa.Column(
            'default_gst',
            sa.Numeric(5, 2),
            nullable=False,
            server_default='18.00',
        ))
        batch_op.add_column(sa.Column(
            'currency',
            sa.String(length=3),
            nullable=False,
            server_default='INR',
        ))
        batch_op.add_column(sa.Column(
            'payment_terms',
            sa.String(length=100),
            nullable=False,
            server_default='Due on Receipt',
        ))
        batch_op.add_column(sa.Column(
            'footer_note',
            sa.Text(),
            nullable=True,
        ))


def downgrade():
    with op.batch_alter_table('shop_profiles', schema=None) as batch_op:
        batch_op.drop_column('footer_note')
        batch_op.drop_column('payment_terms')
        batch_op.drop_column('currency')
        batch_op.drop_column('default_gst')
        batch_op.drop_column('invoice_prefix')
