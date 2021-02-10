from http import HTTPStatus

from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web_response import Response
from aiohttp.web_urldispatcher import View
from aiohttp_apispec import docs, request_schema, response_schema
from asyncpg import UniqueViolationError
from asyncpgsa import PG
from marshmallow import ValidationError
from sqlalchemy import exists, select, and_, func

from backend import settings
from backend.api.schema import UserSchema, UserCreateResponseSchema
from backend.db.models import User, Bill
from backend.utils import SelectQuery

users_t = User.__table__
bills_t = Bill.__table__


class BaseView(View):
    URL_PATH: str

    @property
    def pg(self) -> PG:
        return self.request.app['pg']


class UserCreateAPIView(BaseView):
    URL_PATH = r'/api/v1/users/create/'

    @docs(tags=['users'], summary='Create new user', description='Add new user to database')
    @request_schema(UserSchema(only=('email', 'username')))
    @response_schema(UserCreateResponseSchema(), code=HTTPStatus.CREATED.value)
    async def post(self):
        # The transaction is required in order to roll back partially added changes in case of an error
        # (or disconnection of the client without waiting for a response).
        async with self.pg.transaction() as conn:
            validated_data = self.request['validated_data']

            # create new user
            insert_user_query = users_t.insert().returning(users_t).values(validated_data)
            try:
                new_user = await conn.fetchrow(insert_user_query)
            except UniqueViolationError as err:
                field = err.constraint_name.split('__')[-1]
                raise ValidationError({f"{field}": [f"User with this {field} already exists."]})

            # create bill for new user
            insert_bill_data = {
                'user_id': new_user['id'],
                'balance': settings.DEFAULT_BALANCE,
                'tariff': settings.DEFAULT_TARIFF
            }
            insert_bill_query = bills_t.insert().returning(bills_t).values(insert_bill_data)
            new_user_bill = await conn.fetchrow(insert_bill_query)
            response_data = {**new_user, 'bill': new_user_bill}
        return Response(body={'data': response_data}, status=HTTPStatus.CREATED)


class UsersListAPIView(BaseView):
    URL_PATH = r'/api/v1/users/'

