"""add metadata to content

Revision ID: add_metadata_to_content
Revises: your_previous_revision
Create Date: 2023-07-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_metadata_to_content'
down_revision = 'your_previous_revision'  # Replace with your actual previous revision
branch_labels = None
depends_on = None

def upgrade():
    # Add metadata column
    op.add_column('contents', sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    
    # Add new content types
    op.execute("ALTER TYPE contenttype ADD VALUE IF NOT EXISTS 'website'")
    op.execute("ALTER TYPE contenttype ADD VALUE IF NOT EXISTS 'content_plan'")
    op.execute("ALTER TYPE contenttype ADD VALUE IF NOT EXISTS 'instagram'")
    op.execute("ALTER TYPE contenttype ADD VALUE IF NOT EXISTS 'twitter'")
    op.execute("ALTER TYPE contenttype ADD VALUE IF NOT EXISTS 'linkedin'")
    op.execute("ALTER TYPE contenttype ADD VALUE IF NOT EXISTS 'facebook'")

def downgrade():
    # Remove metadata column
    op.drop_column('contents', 'metadata')
    
    # Note: We can't easily remove enum values in PostgreSQL