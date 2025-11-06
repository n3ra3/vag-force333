"""add unique index on idempotency_key

Revision ID: 0003_unique_idempotency
Revises: 0002_add_order_fields
Create Date: 2025-11-03 00:00:00.000001
"""
from alembic import op
import sqlalchemy as sa

revision = '0003_unique_idempotency'
down_revision = '0002_add_order_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Add unique index on idempotency_key to prevent duplicates
    op.create_index('ux_orders_idempotency_key', 'orders', ['idempotency_key'], unique=True)


def downgrade():
    op.drop_index('ux_orders_idempotency_key', table_name='orders')
