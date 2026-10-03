"""add provider payment models and invoice payment detail fields

Adds provider-level payment tracking alongside the existing invoice payment
summary fields, plus a deduplicated raw event log for idempotent webhook
processing. The secure mock flow is unaffected.

Revision ID: b2c3d4e5f6a7
Revises: f1a2b3c4d5e6
Create Date: 2026-10-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.add_column(sa.Column('payment_order_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('payment_provider_status', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('amount_paid', sa.Numeric(precision=12, scale=2), nullable=True))
        batch_op.create_index('ix_invoices_payment_order_id', ['payment_order_id'], unique=False)

    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=30), nullable=False),
        sa.Column('provider_order_id', sa.String(length=100), nullable=True),
        sa.Column('provider_payment_id', sa.String(length=100), nullable=True),
        sa.Column('provider_link_id', sa.String(length=100), nullable=True),
        sa.Column('provider_qr_id', sa.String(length=100), nullable=True),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=True),
        sa.Column('method', sa.String(length=30), nullable=True),
        sa.Column('vpa', sa.String(length=100), nullable=True),
        sa.Column('signature_verified', sa.Boolean(), nullable=False),
        sa.Column('amount_refunded', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('raw_payload', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ['invoice_id'],
            ['invoices.id'],
            name='fk_payments_invoice_id',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_order_id', name='uq_payments_provider_order_id'),
        sa.UniqueConstraint('provider_payment_id', name='uq_payments_provider_payment_id'),
    )
    op.create_index('ix_payments_invoice_id', 'payments', ['invoice_id'], unique=False)

    op.create_table(
        'payment_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=30), nullable=False),
        sa.Column('event_id', sa.String(length=120), nullable=False),
        sa.Column('event_type', sa.String(length=80), nullable=True),
        sa.Column('invoice_id', sa.Integer(), nullable=True),
        sa.Column('payment_id', sa.Integer(), nullable=True),
        sa.Column('payload', sa.Text(), nullable=True),
        sa.Column('signature_valid', sa.Boolean(), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ['invoice_id'],
            ['invoices.id'],
            name='fk_payment_events_invoice_id',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['payment_id'],
            ['payments.id'],
            name='fk_payment_events_payment_id',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id', name='uq_payment_events_event_id'),
    )
    op.create_index('ix_payment_events_invoice_id', 'payment_events', ['invoice_id'], unique=False)
    op.create_index('ix_payment_events_payment_id', 'payment_events', ['payment_id'], unique=False)


def downgrade():
    op.drop_index('ix_payment_events_payment_id', table_name='payment_events')
    op.drop_index('ix_payment_events_invoice_id', table_name='payment_events')
    op.drop_table('payment_events')

    op.drop_index('ix_payments_invoice_id', table_name='payments')
    op.drop_table('payments')

    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.drop_index('ix_invoices_payment_order_id')
        batch_op.drop_column('amount_paid')
        batch_op.drop_column('payment_provider_status')
        batch_op.drop_column('payment_order_id')
