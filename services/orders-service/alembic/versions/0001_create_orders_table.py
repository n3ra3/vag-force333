"""create orders table

Revision ID: 0001_create_orders
Revises: 
Create Date: 2025-10-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0001_create_orders'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=255), nullable=False),
    )


def downgrade():
    op.drop_table('orders')
