"""Add unique constraint to Bill User FK

Revision ID: b76fb3e5ffa5
Revises: e0a4c2c89ce2
Create Date: 2021-02-19 16:19:15.296323

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b76fb3e5ffa5'
down_revision = 'e0a4c2c89ce2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(op.f('uq__bills__user_id'), 'bills', ['user_id'])


def downgrade():
    op.drop_constraint(op.f('uq__bills__user_id'), 'bills', type_='unique')
