"""create keyword table

Revision ID: 5bfbeb229dff
Revises: bcd77ce27292
Create Date: 2020-07-29 21:24:11.055119

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from sqlalchemy import ForeignKey

revision = '5bfbeb229dff'
down_revision = 'bcd77ce27292'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'keyword',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('company_id', sa.Integer, ForeignKey('company.id')),
        sa.Column('user_id', sa.Integer, ForeignKey('user.id')),
        sa.Column('keyword', sa.String(50), nullable=False),
        sa.Column('exclude', sa.Boolean, default=False),
    )


def downgrade():
    op.drop_table('keyword')
