"""create content table

Revision ID: 27cf72ce4035
Revises: 1992ae5318f3
Create Date: 2020-07-31 21:34:48.775269

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from sqlalchemy import ForeignKey

revision = '27cf72ce4035'
down_revision = '1992ae5318f3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'content',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, ForeignKey('user.id')),
        sa.Column('link_id', sa.Integer, ForeignKey('link.id')),
        sa.Column('relevant', sa.Boolean, default=False),
        sa.Column('processed', sa.Boolean, default=False),
        sa.Column('create_date', sa.Date, nullable=False),
    )


def downgrade():
    op.drop_table('content')
