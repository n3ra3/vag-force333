"""create cart_items table

Revision ID: 0001_create_cart_items
Revises: 
Create Date: 2025-10-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0001_create_cart_items'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'cart_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
    )


def downgrade():
    op.drop_table('cart_items')
