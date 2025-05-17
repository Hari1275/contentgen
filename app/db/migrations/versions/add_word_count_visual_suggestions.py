"""add word_count and visual_suggestions to contents table

Revision ID: add_word_count_visual
Revises: add_metadata_to_content
Create Date: 2023-07-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_word_count_visual'
down_revision = 'add_metadata_to_content'  # Make sure this matches your previous migration
branch_labels = None
depends_on = None

def upgrade():
    # Add word_count column with default value 500
    op.add_column('contents', sa.Column('word_count', sa.Integer(), nullable=True, server_default='500'))
    
    # Add visual_suggestions column
    op.add_column('contents', sa.Column('visual_suggestions', sa.Text(), nullable=True))

def downgrade():
    # Remove columns
    op.drop_column('contents', 'visual_suggestions')
    op.drop_column('contents', 'word_count')