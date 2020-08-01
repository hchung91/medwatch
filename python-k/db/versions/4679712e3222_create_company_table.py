"""create company table

Revision ID: 4679712e3222
Revises: 
Create Date: 2020-07-29 21:14:59.737770

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4679712e3222'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'company',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('domain_url', sa.String(100)),
        sa.Column('url', sa.String(500)),
    )


def downgrade():
    op.drop_table('company')
