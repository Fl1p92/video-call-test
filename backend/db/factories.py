from datetime import timedelta
from decimal import Decimal

import factory
import faker
from sqlalchemy.orm import scoped_session, sessionmaker

from backend import settings
from backend.db import models
from backend.utils import make_user_password_hash


Session = scoped_session(sessionmaker())
fake = faker.Faker()
USER_TEST_PASSWORD = 'testPass123'


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):

    class Meta:
        model = models.User
        sqlalchemy_session = Session

    email = factory.Faker('email')

    @factory.lazy_attribute
    def username(self):
        return fake.profile(fields=['username'])['username']

    @factory.lazy_attribute
    def password(self):
        return make_user_password_hash(USER_TEST_PASSWORD)


class BillFactory(factory.alchemy.SQLAlchemyModelFactory):

    class Meta:
        model = models.Bill
        sqlalchemy_session = Session

    user = factory.SubFactory(UserFactory)
    balance = settings.DEFAULT_BALANCE
    tariff = settings.DEFAULT_TARIFF


class PaymentFactory(factory.alchemy.SQLAlchemyModelFactory):

    class Meta:
        model = models.Payment
        sqlalchemy_session = Session

    bill = factory.SubFactory(BillFactory)
    amount = Decimal('10.00')


class CallFactory(factory.alchemy.SQLAlchemyModelFactory):

    class Meta:
        model = models.Call
        sqlalchemy_session = Session

    caller = factory.SubFactory(UserFactory)
    callee = factory.SubFactory(UserFactory)
    duration = timedelta(seconds=50)
    status = factory.Iterator([status.name for status in models.CallStatus])
