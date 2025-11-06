"""add amount/currency/created_at/idempotency_key to orders

Revision ID: 0002_add_order_fields
Revises: 0001_create_orders_table
Create Date: 2025-11-03 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_add_order_fields'
down_revision = '0001_create_orders'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('orders', sa.Column('amount', sa.Float(), nullable=True))
    op.add_column('orders', sa.Column('currency', sa.String(length=10), nullable=True))
    op.add_column('orders', sa.Column('idempotency_key', sa.String(length=128), nullable=True))
    # Use server default now() for Postgres to populate created_at for new rows
    op.add_column('orders', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))


def downgrade():
    op.drop_column('orders', 'created_at')
    op.drop_column('orders', 'idempotency_key')
    op.drop_column('orders', 'currency')
    op.drop_column('orders', 'amount')
