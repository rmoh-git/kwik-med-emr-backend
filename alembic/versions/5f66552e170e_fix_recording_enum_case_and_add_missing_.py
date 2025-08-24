"""Fix recording enum case and add missing values

Revision ID: 5f66552e170e
Revises: fc9ceb4277d8
Create Date: 2025-08-24 18:10:15.508154

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5f66552e170e'
down_revision = 'fc9ceb4277d8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing uppercase enum values to match existing pattern
    op.execute("ALTER TYPE recordingstatusenum ADD VALUE IF NOT EXISTS 'UPLOADED'")
    op.execute("ALTER TYPE recordingstatusenum ADD VALUE IF NOT EXISTS 'TRANSCRIBING'") 
    op.execute("ALTER TYPE recordingstatusenum ADD VALUE IF NOT EXISTS 'DIARIZING'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values easily
    pass