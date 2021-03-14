from enum import Enum, unique, auto

from sqlalchemy import Column, Integer, MetaData, String, DateTime, Numeric, ForeignKey, Interval, Enum as EnumCol
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import text


# Default naming convention for all indexes and constraints
# See why this is important and how it would save your time:
# https://alembic.sqlalchemy.org/en/latest/naming.html
convention = {
    'all_column_names': lambda constraint, table: '_'.join([
        column.name for column in constraint.columns.values()
    ]),
    'ix': 'ix__%(table_name)s__%(all_column_names)s',
    'uq': 'uq__%(table_name)s__%(all_column_names)s',
    'ck': 'ck__%(table_name)s__%(constraint_name)s',
    'fk': (
        'fk__%(table_name)s__'
        '%(all_column_names)s__'
        '%(referred_table_name)s'
    ),
    'pk': 'pk__%(table_name)s'
}

# Registry for all tables
metadata = MetaData(naming_convention=convention)


@unique
class CallStatus(Enum):
    successful = auto()
    missed = auto()
    declined = auto()


@as_declarative(metadata=metadata)
class Base:
    """Base model class"""
    id = Column(Integer, primary_key=True)
    created = Column(DateTime(timezone=True), server_default=text('clock_timestamp()'), nullable=False)

    @declared_attr
    def __tablename__(cls):
        return f"{cls.__name__.lower()}s"

    def __repr__(self):
        return f"[{self.id}] {self.__class__.__name__}"


class User(Base):
    email = Column(String, nullable=False, unique=True)
    username = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    bill = relationship('Bill', uselist=False, back_populates='user')


class Bill(Base):
    user_id = Column(Integer, ForeignKey('users.id', onupdate='CASCADE', ondelete='CASCADE'), unique=True)
    user = relationship('User', back_populates='bill')
    balance = Column(Numeric, nullable=False)
    tariff = Column(Numeric, nullable=False)
    payments = relationship('Payment', back_populates='bill')


class Payment(Base):
    bill_id = Column(Integer, ForeignKey('bills.id', onupdate='CASCADE', ondelete='CASCADE'))
    bill = relationship('Bill', back_populates='payments')
    amount = Column(Numeric, nullable=False)


class Call(Base):
    caller_id = Column(Integer, ForeignKey('users.id', onupdate='CASCADE', ondelete='CASCADE'))
    caller = relationship('User', foreign_keys=[caller_id])
    callee_id = Column(Integer, ForeignKey('users.id', onupdate='CASCADE', ondelete='CASCADE'))
    callee = relationship('User', foreign_keys=[callee_id])
    duration = Column(Interval)
    status = Column(EnumCol(CallStatus, name='call_status'), nullable=False)


# sql alchemy tables
users_t = User.__table__
bills_t = Bill.__table__
payments_t = Payment.__table__
calls_t = Call.__table__
