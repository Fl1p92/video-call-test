from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from http import HTTPStatus

import jwt
from aiohttp import hdrs
from aiohttp.web_exceptions import HTTPNotFound, HTTPForbidden
from aiohttp.web_response import Response, StreamResponse
from aiohttp.web_urldispatcher import View
from aiohttp_apispec import docs, request_schema, response_schema
from asyncpg import UniqueViolationError
from asyncpgsa import PG
from marshmallow import ValidationError
from sqlalchemy import exists, select, or_, Table

from backend import settings
from backend.api import schema, queries
from backend.api.permissions import IsAuthenticatedForObject
from backend.db.models import users_t, bills_t, payments_t, calls_t, CallStatus
from backend.utils import make_user_password_hash, check_user_password, SelectQuery


# swagger security schema
jwt_security = [{'JWT Authorization': []}]


class BaseView(View):
    URL_PATH: str

    @property
    def pg(self) -> PG:
        return self.request.app['pg']


class CheckObjectsExistsMixin:
    object_id_path: str
    check_exists_table: Table

    async def _iter(self) -> StreamResponse:
        await self.check_object_exists()
        return await super()._iter()

    @property
    def object_id(self):
        return int(self.request.match_info.get(self.object_id_path))

    async def check_object_exists(self):
        query = select([
            exists().where(self.check_exists_table.c.id == self.object_id)
        ])
        if not await self.pg.fetchval(query):
            raise HTTPNotFound()


class CheckUserPermissionMixin:
    skip_methods: list = []
    permissions_classes: list = []

    async def _iter(self) -> StreamResponse:
        if self.request.method not in self.skip_methods:
            await self.check_permissions()
        return await super()._iter()

    async def check_permissions(self):
        permissions_objects = [permission() for permission in self.permissions_classes]
        for permission in permissions_objects:
            if not permission.has_permission(self.request, self):
                raise HTTPForbidden(reason='You do not have permission to perform this action.')


class LoginAPIView(BaseView):
    """
    Checks the credentials and return the JWT Token
    if the credentials are valid and authenticated.
    """
    URL_PATH = '/api/v1/auth/login/'

    @docs(tags=['auth'],
          summary='Login',
          description='Login user to system')
    @request_schema(schema.UserSchema(only=('email', 'password')))
    @response_schema(schema.JWTTokenResponseSchema(), code=HTTPStatus.OK.value)
    async def post(self):
        validated_data = self.request['validated_data']
        get_user_query = users_t.select(users_t.c.email == validated_data['email'])
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
        raise ValidationError({'non_field_errors': ['Unable to log in with provided credentials.']})


class UserCreateAPIView(BaseView):
    """
    Creates new user.
    """
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
    URL_PATH = '/api/v1/users/list/'

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


class UserRetrieveUpdateDestroyAPIView(CheckObjectsExistsMixin, CheckUserPermissionMixin, BaseView):
    """
    Returns, changes or delete information for a user.
    """
    URL_PATH = r'/api/v1/users/{user_id:\d+}/'
    object_id_path = 'user_id'
    check_exists_table = users_t
    skip_methods = [hdrs.METH_GET]
    permissions_classes = [IsAuthenticatedForObject]

    async def get_user(self):
        user_query = queries.MAIN_USER_QUERY.where(users_t.c.id == self.object_id)
        user = await self.pg.fetchrow(user_query)
        return user

    @docs(tags=['users'],
          summary='Retrieve user',
          description='Returns information for a user',
          security=jwt_security)
    @response_schema(schema.UserDetailsResponseSchema(), code=HTTPStatus.OK.value)
    async def get(self):
        user = await self.get_user()
        return Response(body={'data': user}, status=HTTPStatus.OK)

    @docs(tags=['users'],
          summary='Update user',
          description='Updates information for a user',
          security=jwt_security)
    @request_schema(schema.UserPatchSchema())
    @response_schema(schema.UserDetailsResponseSchema(), code=HTTPStatus.OK.value)
    async def patch(self):
        async with self.pg.transaction() as conn:
            validated_data = self.request['validated_data']

            # Blocking will avoid race conditions between concurrent user change requests
            await conn.fetch('SELECT pg_advisory_xact_lock($1)', self.object_id)

            patch_query = users_t.update().values(validated_data).where(users_t.c.id == self.object_id)
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
          description='Deletes information for a user',
          security=jwt_security)
    @response_schema(schema.NoContentResponseSchema(), code=HTTPStatus.NO_CONTENT.value)
    async def delete(self):
        delete_query = users_t.delete().where(users_t.c.id == self.object_id)
        await self.pg.fetch(delete_query)
        return Response(body={}, status=HTTPStatus.NO_CONTENT)


class BillRetrieveUpdateAPIView(CheckObjectsExistsMixin, CheckUserPermissionMixin, BaseView):
    """
    Returns or changes bill information for a user.
    """
    URL_PATH = r'/api/v1/bills/{user_id:\d+}/'
    object_id_path = 'user_id'
    check_exists_table = users_t
    permissions_classes = [IsAuthenticatedForObject]

    async def get_bill(self):
        bill_query = bills_t.select(bills_t.c.user_id == self.object_id)
        bill = dict(await self.pg.fetchrow(bill_query))
        max_call_duration_minutes = bill['balance'] // bill['tariff']
        bill['max_call_duration_minutes'] = max_call_duration_minutes if max_call_duration_minutes > 0 else 0
        return bill

    @docs(tags=['bills'],
          summary='Retrieve bill',
          description='Returns bill information for a user',
          security=jwt_security)
    @response_schema(schema.BillDetailsResponseSchema(), code=HTTPStatus.OK.value)
    async def get(self):
        bill = await self.get_bill()
        return Response(body={'data': bill}, status=HTTPStatus.OK)

    @docs(tags=['bills'],
          summary='Update bill',
          description='Updates bill information for a user',
          security=jwt_security)
    @request_schema(schema.BillSchema(only=('tariff', )))
    @response_schema(schema.BillDetailsResponseSchema(), code=HTTPStatus.OK.value)
    async def patch(self):
        async with self.pg.transaction() as conn:
            validated_data = self.request['validated_data']

            # Blocking will avoid race conditions between concurrent bill change requests
            await conn.fetch('SELECT pg_advisory_xact_lock($1)', self.object_id)

            patch_query = bills_t.update().values(validated_data).where(bills_t.c.user_id == self.object_id)
            await conn.fetch(patch_query)

        # Get up-to-date bill information
        bill = await self.get_bill()
        return Response(body={'data': bill}, status=HTTPStatus.OK)


class PaymentCreateAPIView(BaseView):
    """
    Creates new payment for a bill.
    """
    URL_PATH = '/api/v1/payments/create/'

    async def check_bill_exists(self, bill_id):
        query = select([
            exists().where(bills_t.c.id == bill_id)
        ])
        if not await self.pg.fetchval(query):
            raise HTTPNotFound()

    async def update_bill_balance(self, bill_id):
        async with self.pg.transaction() as conn:
            amount = self.request['validated_data'].get('amount')
            # Blocking will avoid race conditions between concurrent bill change requests
            await conn.fetch('SELECT pg_advisory_xact_lock($1)', bill_id)
            query = bills_t.update().values(balance=bills_t.c.balance + amount).where(bills_t.c.id == bill_id)
            await conn.fetch(query)

    @docs(tags=['bills'],
          summary='Create payment',
          description='Creates new payment for a user',
          security=jwt_security)
    @request_schema(schema.PaymentSchema())
    @response_schema(schema.PaymentDetailsResponseSchema(), code=HTTPStatus.CREATED.value)
    async def post(self):
        async with self.pg.transaction() as conn:
            validated_data = self.request['validated_data']
            bill_id = validated_data.get('bill_id')

            # Check bill id exists
            await self.check_bill_exists(bill_id)

            # Create new payment
            insert_payment_query = payments_t.insert().returning(payments_t).values(validated_data)
            new_payment = await conn.fetchrow(insert_payment_query)

        # Update bill balance by the amount of the new payment
        await self.update_bill_balance(bill_id)

        return Response(body={'data': new_payment}, status=HTTPStatus.CREATED)


class PaymentsListAPIView(CheckObjectsExistsMixin, CheckUserPermissionMixin, BaseView):
    """
    Returns payments information for user bill.
    """
    URL_PATH = r'/api/v1/payments/{user_id:\d+}/list/'
    object_id_path = 'user_id'
    check_exists_table = users_t
    permissions_classes = [IsAuthenticatedForObject]

    @docs(tags=['bills'],
          summary='List of payments',
          description='Returns information for all payments',
          security=jwt_security)
    @response_schema(schema.PaymentListResponseSchema(), code=HTTPStatus.OK.value)
    async def get(self):
        payments_query = payments_t.select(bills_t.c.user_id == self.object_id).select_from(payments_t.join(bills_t))
        body = SelectQuery(query=payments_query, transaction_ctx=self.pg.transaction())
        return Response(body=body, status=HTTPStatus.OK)


class CallCreateAPIView(BaseView):
    """
    Creates new call for a user.
    """
    URL_PATH = '/api/v1/calls/create/'

    async def check_users_exists(self, caller_id, callee_id, conn):
        if caller_id == callee_id:
            raise ValidationError({"non_field_errors": [f"User {caller_id} cannot call himself."]})
        query = users_t.select(users_t.c.id.in_([caller_id, callee_id]))
        if len(await conn.fetch(query)) != 2:
            raise HTTPNotFound()

    async def check_user_balance(self, caller_id, conn):
        query = bills_t.select(bills_t.c.user_id == caller_id)
        user_bill = await conn.fetchrow(query)
        if user_bill['balance'] <= 0 or not user_bill['balance'] // user_bill['tariff']:
            raise ValidationError({"non_field_errors": [f"User {caller_id} doesn't have enough money to call."]})
        return user_bill

    async def update_user_balance(self, caller_bill, conn):
        duration = self.request['validated_data'].get('duration')
        duration_delta = relativedelta(seconds=duration.total_seconds())
        # Rounding duration to minutes
        duration_minutes = duration_delta.minutes + 1 if duration_delta.seconds else duration_delta.minutes
        call_cost = int(duration_minutes) * caller_bill['tariff']
        # Blocking will avoid race conditions between concurrent bill change requests
        await conn.fetch('SELECT pg_advisory_xact_lock($1)', caller_bill['id'])
        query = bills_t.update().values(balance=bills_t.c.balance - call_cost).where(bills_t.c.id == caller_bill['id'])
        await conn.fetch(query)

    @docs(tags=['calls'],
          summary='Create call',
          description='Creates new call for a user',
          security=jwt_security)
    @request_schema(schema.CallSchema())
    @response_schema(schema.CallDetailsResponseSchema(), code=HTTPStatus.CREATED.value)
    async def post(self):
        async with self.pg.transaction() as conn:
            validated_data = self.request['validated_data']
            validated_data['duration'] = timedelta(seconds=validated_data['duration'])

            # Check users availability
            await self.check_users_exists(caller_id=validated_data.get('caller_id'),
                                          callee_id=validated_data.get('callee_id'),
                                          conn=conn)

            # Check user balance
            user_bill = await self.check_user_balance(caller_id=validated_data.get('caller_id'), conn=conn)

            # Create new call
            insert_call_query = calls_t.insert().returning(calls_t).values(validated_data)
            new_call = await conn.fetchrow(insert_call_query)

            # Update user balance
            await self.update_user_balance(caller_bill=user_bill, conn=conn)

        return Response(body={'data': new_call}, status=HTTPStatus.CREATED)


class CallsListAPIView(CheckObjectsExistsMixin, CheckUserPermissionMixin, BaseView):
    """
    Returns information about calls for user.
    """
    URL_PATH = r'/api/v1/calls/{user_id:\d+}/list/'
    object_id_path = 'user_id'
    check_exists_table = users_t
    permissions_classes = [IsAuthenticatedForObject]

    @property
    def correct_statuses(self):
        return {status.name for status in CallStatus}

    @docs(tags=['calls'],
          summary='List of calls',
          description='Returns information about calls for user',
          security=jwt_security,
          parameters=[{
              'in': 'query',
              'name': 'type',
              'description': 'Filter calls by call status'
          }])
    @response_schema(schema.CallListResponseSchema(), code=HTTPStatus.OK.value)
    async def get(self):
        calls_query = calls_t.select(or_(calls_t.c.caller_id == self.object_id, calls_t.c.callee_id == self.object_id))
        if (filter_term := self.request.query.get('type')) and (filter_term in self.correct_statuses):
            calls_query = calls_query.where(calls_t.c.status == filter_term)
        body = SelectQuery(query=calls_query, transaction_ctx=self.pg.transaction())
        return Response(body=body, status=HTTPStatus.OK)
