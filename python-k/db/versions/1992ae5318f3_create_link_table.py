"""create link table

Revision ID: 1992ae5318f3
Revises: 444536dc4e75
Create Date: 2020-07-31 21:29:46.233260

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from sqlalchemy import ForeignKey

revision = '1992ae5318f3'
down_revision = '444536dc4e75'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'link',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('company_id', sa.Integer, ForeignKey('company.id')),
        sa.Column('body', sa.String(200), nullable=False),
        sa.Column('href', sa.String(200), nullable=False),
        sa.Column('processed', sa.Boolean, default=False),
        sa.Column('create_date', sa.Date, nullable=False),
    )


def downgrade():
    op.drop_table('link')
