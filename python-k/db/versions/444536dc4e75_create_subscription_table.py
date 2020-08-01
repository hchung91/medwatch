"""create subscription table

Revision ID: 444536dc4e75
Revises: 5bfbeb229dff
Create Date: 2020-07-31 21:03:26.886414

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from sqlalchemy import ForeignKey

revision = '444536dc4e75'
down_revision = '5bfbeb229dff'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'subscription',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('company_id', sa.Integer, ForeignKey('company.id')),
        sa.Column('user_id', sa.Integer, ForeignKey('user.id')),
    )


def downgrade():
    op.drop_table('subscription')
