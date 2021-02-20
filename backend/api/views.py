from datetime import datetime
from http import HTTPStatus

import jwt
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web_response import Response, StreamResponse
from aiohttp.web_urldispatcher import View
from aiohttp_apispec import docs, request_schema, response_schema
from asyncpg import UniqueViolationError
from asyncpgsa import PG
from marshmallow import ValidationError
from sqlalchemy import exists, select, or_

from backend import settings
from backend.api import schema, queries
from backend.db.models import users_t, bills_t, payments_t, calls_t
from backend.utils import make_user_password_hash, check_user_password, SelectQuery


# swagger security schema
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
    URL_PATH = '/api/v1/login/'

    @docs(tags=['auth'],
          summary='Login',
          description='Login user to system')
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
    URL_PATH = '/api/v1/users/create/'

    @docs(tags=['users'],
          summary='Create new user',
          description='Add new user to database')
    @request_schema(schema.UserSchema(only=('email', 'username', 'password')))
    @response_schema(schema.UserDetailsResponseSchema(), code=HTTPStatus.CREATED.value)
    async def post(self):
        # The transaction is required in order to roll back partially added changes in case of an error
        # (or disconnection of the client without waiting for a response).
        async with self.pg.transaction() as conn:
            validated_data = self.request['validated_data']
            validated_data['password'] = make_user_password_hash(validated_data['password'])

            # Create new user
            insert_user_query = users_t.insert().returning(queries.MAIN_USER_QUERY).values(validated_data)
            try:
                new_user = await conn.fetchrow(insert_user_query)
            except UniqueViolationError as err:
                field = err.constraint_name.split('__')[-1]
                raise ValidationError({f"{field}": [f"User with this {field} already exists."]})

            # Create bill for new user
            insert_bill_data = {
                'user_id': new_user['id'],
                'balance': settings.DEFAULT_BALANCE,
                'tariff': settings.DEFAULT_TARIFF
            }
            insert_bill_query = bills_t.insert().values(insert_bill_data)
            await conn.fetch(insert_bill_query)
        return Response(body={'data': new_user}, status=HTTPStatus.CREATED)


class UsersListAPIView(BaseView):
    """
    Returns information for all users.
    """
    URL_PATH = '/api/v1/users/'

    @docs(tags=['users'],
          summary='List of users',
          description='Returns information for all users',
          security=jwt_security,
          parameters=[{
              'in': 'query',
              'name': 'search',
              'description': 'Search for a user by email or username'
          }])
    @response_schema(schema.UserListResponseSchema(), code=HTTPStatus.OK.value)
    async def get(self):
        users_query = queries.MAIN_USER_QUERY
        if search_term := self.request.query.get('search'):
            users_query = users_query.where(or_(users_t.c.email.ilike(f'%{search_term}%'),
                                                users_t.c.username.ilike(f'%{search_term}%')))
        body = SelectQuery(query=users_query, transaction_ctx=self.pg.transaction())
        return Response(body=body, status=HTTPStatus.OK)


class UserRetrieveUpdateDestroyAPIView(BaseView):
    """
    Returns, changes or delete information for a given user.
    """
    URL_PATH = r'/api/v1/users/{user_id:\d+}/'

    async def _iter(self) -> StreamResponse:
        await self.check_user_exists()
        return await super()._iter()

    @property
    def user_id(self):
        return int(self.request.match_info.get('user_id'))

    async def check_user_exists(self):
        query = select([
            exists().where(users_t.c.id == self.user_id)
        ])
        if not await self.pg.fetchval(query):
            raise HTTPNotFound()

    async def get_user(self):
        user_query = queries.MAIN_USER_QUERY.where(users_t.c.id == self.user_id)
        user = await self.pg.fetchrow(user_query)
        return user

    @docs(tags=['users'],
          summary='Retrieve user',
          description='Returns information for a given user',
          security=jwt_security)
    @response_schema(schema.UserDetailsResponseSchema(), code=HTTPStatus.OK.value)
    async def get(self):
        user = await self.get_user()
        return Response(body={'data': user}, status=HTTPStatus.OK)

    @docs(tags=['users'],
          summary='Update user',
          description='Updates information for a given user',
          security=jwt_security)
    @request_schema(schema.UserPatchSchema())
    @response_schema(schema.UserDetailsResponseSchema(), code=HTTPStatus.OK.value)
    async def patch(self):
        async with self.pg.transaction() as conn:
            validated_data = self.request['validated_data']

            # Blocking will avoid race conditions between concurrent user change requests.
            await conn.fetch('SELECT pg_advisory_xact_lock($1)', self.user_id)

            patch_query = users_t.update().values(validated_data).where(users_t.c.id == self.user_id)
            try:
                await conn.fetch(patch_query)
            except UniqueViolationError as err:
                field = err.constraint_name.split('__')[-1]
                raise ValidationError({f"{field}": [f"User with this {field} already exists."]})

        # Get up-to-date information about the user
        user = await self.get_user()
        return Response(body={'data': user}, status=HTTPStatus.OK)

    @docs(tags=['users'],
          summary='Delete user',
          description='Deletes information for a given user',
          security=jwt_security)
    @response_schema(schema.NoContentResponseSchema(), code=HTTPStatus.NO_CONTENT.value)
    async def delete(self):
        delete_query = users_t.delete().where(users_t.c.id == self.user_id)
        await self.pg.fetch(delete_query)
        return Response(body={}, status=HTTPStatus.NO_CONTENT)
