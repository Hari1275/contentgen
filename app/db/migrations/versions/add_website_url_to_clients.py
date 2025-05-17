"""add website_url and social_profiles to clients table

Revision ID: add_website_social
Revises: add_word_count_visual
Create Date: 2023-07-15 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite

# revision identifiers, used by Alembic.
revision = 'add_website_social'
down_revision = 'add_word_count_visual'  # Make sure this matches your previous migration
branch_labels = None
depends_on = None

def upgrade():
    # Add website_url column
    op.add_column('clients', sa.Column('website_url', sa.String(255), nullable=True))
    
    # Add social_profiles column - JSON type handling for SQLite vs PostgreSQL
    if op.get_context().dialect.name == 'sqlite':
        op.add_column('clients', sa.Column('social_profiles', sa.Text(), nullable=True))
    else:
        op.add_column('clients', sa.Column('social_profiles', postgresql.JSON(astext_type=sa.Text()), nullable=True))

def downgrade():
    # Remove columns
    op.drop_column('clients', 'social_profiles')
    op.drop_column('clients', 'website_url')