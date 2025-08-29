"""add insurance coverage percentage to patients

Revision ID: 8d3ffec07429
Revises: 3fb71f142905
Create Date: 2025-08-28 21:19:23.103599

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8d3ffec07429'
down_revision = '3fb71f142905'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add insurance coverage percentage column
    op.add_column('patients', sa.Column('insurance_coverage_percentage', sa.String(length=10), nullable=True))


def downgrade() -> None:
    # Remove insurance coverage percentage column  
    op.drop_column('patients', 'insurance_coverage_percentage')