"""create products table

Revision ID: 0001_create_products
Revises: 
Create Date: 2025-10-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0001_create_products'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('price', sa.Numeric(), nullable=False),
    )


def downgrade():
    op.drop_table('products')
