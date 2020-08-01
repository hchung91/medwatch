"""create user table

Revision ID: bcd77ce27292
Revises: 4679712e3222
Create Date: 2020-07-29 21:20:40.944691

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bcd77ce27292'
down_revision = '4679712e3222'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('email', sa.String(50), nullable=False)
    )


def downgrade():
    op.drop_table('user')
