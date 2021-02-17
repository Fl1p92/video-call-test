from datetime import datetime
from http import HTTPStatus

import jwt
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web_response import Response
from aiohttp.web_urldispatcher import View
from aiohttp_apispec import docs, request_schema, response_schema
from asyncpg import UniqueViolationError
from asyncpgsa import PG
from marshmallow import ValidationError
from sqlalchemy import exists, select, and_, func

from backend import settings
from backend.api import schema
from backend.db.models import User, Bill
from backend.utils import make_user_password_hash, check_user_password, SelectQuery


# sql alchemy tables
users_t = User.__table__
bills_t = Bill.__table__

jwt_security = [{'JWT Authorization': []}]


class BaseView(View):
    URL_PATH: str

    @property
    def pg(self) -> PG:
        return self.request.app['pg']


class LoginAPIView(BaseView):
    """
    Check the credentials and return the JWT Token
    if the credentials are valid and authenticated.
    """
    URL_PATH = r'/api/v1/login/'

    @docs(tags=['auth'], summary='Login', description='Login user to system')
    @request_schema(schema.UserSchema(only=('email', 'password')))
    @response_schema(schema.JWTTokenResponseSchema(), code=HTTPStatus.OK.value)
    async def post(self):
        validated_data = self.request['validated_data']
        get_user_query = users_t.select().where(users_t.c.email == validated_data['email'])
        user = await self.pg.fetchrow(get_user_query)
        if user is not None:
            if check_user_password(validated_data['password'], user['password']):
                payload_data = {
                    'id': user['id'],
                    'email': user['email'],
                    'username': user['username'],
                    'exp': datetime.utcnow() + settings.JWT_EXPIRATION_DELTA
                }
                token = jwt.encode(payload=payload_data, key=settings.JWT_SECRET)
                response_data = {
                    'token': f'Bearer {token}',
                    'user': {k: v for k, v in payload_data.items() if k != 'exp'}
                }
                return Response(body={'data': response_data}, status=HTTPStatus.OK)
        raise ValidationError({f'non_field_errors': ['Unable to log in with provided credentials.']})


class UserCreateAPIView(BaseView):
    URL_PATH = r'/api/v1/users/create/'

    @docs(tags=['users'], summary='Create new user', description='Add new user to database')
    @request_schema(schema.UserSchema(only=('email', 'username', 'password')))
    @response_schema(schema.UserCreateResponseSchema(), code=HTTPStatus.CREATED.value)
    async def post(self):
        # The transaction is required in order to roll back partially added changes in case of an error
        # (or disconnection of the client without waiting for a response).
        async with self.pg.transaction() as conn:
            validated_data = self.request['validated_data']
            validated_data['password'] = make_user_password_hash(validated_data['password'])

            # Create new user
            insert_user_query = users_t.insert().returning(users_t).values(validated_data)
            try:
                new_user = dict(await conn.fetchrow(insert_user_query))
            except UniqueViolationError as err:
                field = err.constraint_name.split('__')[-1]
                raise ValidationError({f"{field}": [f"User with this {field} already exists."]})

            # Create bill for new user
            insert_bill_data = {
                'user_id': new_user['id'],
                'balance': settings.DEFAULT_BALANCE,
                'tariff': settings.DEFAULT_TARIFF
            }
            insert_bill_query = bills_t.insert().returning(bills_t).values(insert_bill_data)
            new_user_bill = await conn.fetchrow(insert_bill_query)
            new_user.pop('password', None)  # remove password from response
            response_data = {**new_user, 'bill': new_user_bill}
        return Response(body={'data': response_data}, status=HTTPStatus.CREATED)


class UsersListAPIView(BaseView):
    URL_PATH = r'/api/v1/users/'

