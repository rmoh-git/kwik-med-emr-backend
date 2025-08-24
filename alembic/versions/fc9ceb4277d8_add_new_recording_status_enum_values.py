"""Add new recording status enum values

Revision ID: fc9ceb4277d8
Revises: 
Create Date: 2025-08-24 18:09:13.611318

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fc9ceb4277d8'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new enum values to RecordingStatusEnum (matching existing uppercase pattern)
    op.execute("ALTER TYPE recordingstatusenum ADD VALUE 'UPLOADED'")
    op.execute("ALTER TYPE recordingstatusenum ADD VALUE 'TRANSCRIBING'")
    op.execute("ALTER TYPE recordingstatusenum ADD VALUE 'DIARIZING'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave a comment about the limitation
    pass