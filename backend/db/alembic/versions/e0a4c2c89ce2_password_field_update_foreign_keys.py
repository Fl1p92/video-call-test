"""Add password field to User model, update foreign keys

Revision ID: e0a4c2c89ce2
Revises: ec2b581fcb0a
Create Date: 2021-02-15 17:42:40.037609

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e0a4c2c89ce2'
down_revision = 'ec2b581fcb0a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('password', sa.String(), nullable=False))

    op.drop_constraint('fk__bills__user_id__users', 'bills', type_='foreignkey')
    op.create_foreign_key(op.f('fk__bills__user_id__users'), 'bills', 'users', ['user_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    op.drop_constraint('fk__payments__bill_id__bills', 'payments', type_='foreignkey')
    op.create_foreign_key(op.f('fk__payments__bill_id__bills'), 'payments', 'bills', ['bill_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    op.drop_constraint('fk__calls__caller_id__users', 'calls', type_='foreignkey')
    op.create_foreign_key(op.f('fk__calls__caller_id__users'), 'calls', 'users', ['caller_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
    op.drop_constraint('fk__calls__callee_id__users', 'calls', type_='foreignkey')
    op.create_foreign_key(op.f('fk__calls__callee_id__users'), 'calls', 'users', ['callee_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')


def downgrade():
    op.drop_column('users', 'password')

    op.drop_constraint(op.f('fk__bills__user_id__users'), 'bills', type_='foreignkey')
    op.create_foreign_key('fk__bills__user_id__users', 'bills', 'users', ['user_id'], ['id'])

    op.drop_constraint(op.f('fk__payments__bill_id__bills'), 'payments', type_='foreignkey')
    op.create_foreign_key('fk__payments__bill_id__bills', 'payments', 'bills', ['bill_id'], ['id'])

    op.drop_constraint(op.f('fk__calls__caller_id__users'), 'calls', type_='foreignkey')
    op.create_foreign_key('fk__calls__caller_id__users', 'calls', 'users', ['caller_id'], ['id'])
    op.drop_constraint(op.f('fk__calls__callee_id__users'), 'calls', type_='foreignkey')
    op.create_foreign_key('fk__calls__callee_id__users', 'calls', 'users', ['callee_id'], ['id'])
