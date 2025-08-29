"""add metadata field to recordings for dual language support

Revision ID: e5deb8179384
Revises: 8d3ffec07429
Create Date: 2025-08-29 13:24:54.475973

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5deb8179384'
down_revision = '8d3ffec07429'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add additional_data JSON column for storing dual-language info and other metadata
    op.add_column('recordings', sa.Column('additional_data', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove additional_data column
    op.drop_column('recordings', 'additional_data')