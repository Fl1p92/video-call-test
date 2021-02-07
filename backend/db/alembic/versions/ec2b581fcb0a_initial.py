"""Initial

Revision ID: ec2b581fcb0a
Revises: 
Create Date: 2021-02-07 13:50:47.503089

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ec2b581fcb0a'
down_revision = None
branch_labels = None
depends_on = None


StatusType = sa.Enum('successful', 'missed', 'declined', name='call_status')


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk__users')),
        sa.UniqueConstraint('email', name=op.f('uq__users__email')),
        sa.UniqueConstraint('username', name=op.f('uq__users__username'))
    )
    op.create_table(
        'bills',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('balance', sa.Numeric(), nullable=False),
        sa.Column('tariff', sa.Numeric(), nullable=False),
        sa.ForeignKeyConstraint(('user_id', ), ['users.id'], name=op.f('fk__bills__user_id__users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk__bills'))
    )
    op.create_table(
        'calls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.Column('caller_id', sa.Integer(), nullable=True),
        sa.Column('callee_id', sa.Integer(), nullable=True),
        sa.Column('duration', sa.Interval(), nullable=True),
        sa.Column('status', StatusType, nullable=False),
        sa.ForeignKeyConstraint(('caller_id', ), ['users.id'], name=op.f('fk__calls__caller_id__users')),
        sa.ForeignKeyConstraint(('callee_id', ), ['users.id'], name=op.f('fk__calls__callee_id__users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk__calls'))
    )
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.Column('bill_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Numeric(), nullable=False),
        sa.ForeignKeyConstraint(('bill_id', ), ['bills.id'], name=op.f('fk__payments__bill_id__bills')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk__payments'))
    )


def downgrade():
    op.drop_table('payments')
    op.drop_table('calls')
    op.drop_table('bills')
    op.drop_table('users')
    StatusType.drop(op.get_bind(), checkfirst=False)
