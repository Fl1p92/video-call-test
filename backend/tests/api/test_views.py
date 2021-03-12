from http import HTTPStatus

from backend import settings
from backend.db.factories import USER_TEST_PASSWORD, UserFactory, BillFactory, PaymentFactory
from backend.db.models import User, Bill, Payment
from backend.api import views, schema
from backend.utils import url_for


async def test_create_user(authorized_api_client, db_session):
    api_client, _ = authorized_api_client
    # Try to create user without all required fields
    partial_data = {
        'username': 'test_user',
    }
    # Response checks
    response = await api_client.post(url_for(views.UserCreateAPIView.URL_PATH), data=partial_data)
    assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    assert len(response_data['error']['fields'].keys()) == 2
    assert response_data['error']['fields'].keys() == {'email', 'password'}

    # Try to create user with invalid data
    invalid_data = {
        'username': 'test_user',
        'email': 'invalid_email.com',
        'password': USER_TEST_PASSWORD[:5],
    }
    # Response checks
    response = await api_client.post(url_for(views.UserCreateAPIView.URL_PATH), data=invalid_data)
    assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    assert len(response_data['error']['fields'].keys()) == 2
    assert response_data['error']['fields']['email'][0] == 'Not a valid email address.'
    assert response_data['error']['fields']['password'][0] == 'Shorter than minimum length 7.'

    # Creates a new user
    user_data = {
        'username': 'test_user',
        'email': 'test_user@email.com',
        'password': USER_TEST_PASSWORD,
    }
    assert db_session.query(User).filter(User.email == user_data['email']).count() == 0
    # Response checks
    response = await api_client.post(url_for(views.UserCreateAPIView.URL_PATH), data=user_data)
    assert response.status == HTTPStatus.CREATED
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    errors = schema.UserDetailsResponseSchema().validate(response_data)
    assert not errors
    assert response_data['data']['username'] == user_data['username']
    assert response_data['data']['email'] == user_data['email']
    # DB user checks
    user_from_db = db_session.query(User).filter(User.email == user_data['email']).first()
    assert user_from_db
    assert user_from_db.username == user_data['username']
    # Bill creation check
    user_bill = db_session.query(Bill).filter(Bill.user_id == user_from_db.id).first()
    assert user_bill
    assert user_bill.balance == settings.DEFAULT_BALANCE
    assert user_bill.tariff == settings.DEFAULT_TARIFF

    # Try to create user with same data
    duplicate_user_data = {
        'username': 'test_user',  # same username
        'email': 'test_user2@email.com',
        'password': USER_TEST_PASSWORD,
    }
    # Check user exists
    assert db_session.query(User).filter(User.username == duplicate_user_data['username']).first()
    # Response checks
    response = await api_client.post(url_for(views.UserCreateAPIView.URL_PATH), data=duplicate_user_data)
    assert response.status == HTTPStatus.BAD_REQUEST
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    assert len(response_data['error']['fields'].keys()) == 1
    assert response_data['error']['fields']['username'][0] == 'User with this username already exists.'


async def test_login_user(authorized_api_client, db_session):
    api_client, _ = authorized_api_client
    # Create user object without commit the current transaction (checks invalid data)
    user = UserFactory()
    request_data = {'email': user.email, 'password': USER_TEST_PASSWORD}
    response = await api_client.post(url_for(views.LoginAPIView.URL_PATH), data=request_data)
    # Response checks
    assert response.status == HTTPStatus.BAD_REQUEST
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    assert response_data['error']['fields']['non_field_errors'][0] == 'Unable to log in with provided credentials.'

    # Then commit the current transaction
    db_session.commit()

    # Check invalid password
    invalid_password_data = {'email': user.email, 'password': 'invalid_password'}
    response = await api_client.post(url_for(views.LoginAPIView.URL_PATH), data=invalid_password_data)
    # Response checks
    assert response.status == HTTPStatus.BAD_REQUEST
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    assert response_data['error']['fields']['non_field_errors'][0] == 'Unable to log in with provided credentials.'

    # Check valid data
    response = await api_client.post(url_for(views.LoginAPIView.URL_PATH), data=request_data)
    # Response checks
    assert response.status == HTTPStatus.OK
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    errors = schema.JWTTokenResponseSchema().validate(response_data)
    assert not errors
    assert response_data['data']['user']['username'] == user.username
    assert response_data['data']['user']['email'] == user.email


async def test_get_user_list(authorized_api_client, db_session):
    api_client, user = authorized_api_client
    # Creates users pool
    initial_users_quantity = db_session.query(User).count()
    n = 5
    for _ in range(n):
        UserFactory()
    db_session.commit()

    # Get all users
    response = await api_client.get(url_for(views.UsersListAPIView.URL_PATH))
    # Response checks
    assert response.status == HTTPStatus.OK
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    errors = schema.UserListResponseSchema().validate(response_data)
    assert not errors
    assert len(response_data['data']) == initial_users_quantity + n

    # Filter by username
    response = await api_client.get(url_for(views.UsersListAPIView.URL_PATH), params={'search': user.username})
    # Response checks
    assert response.status == HTTPStatus.OK
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    errors = schema.UserListResponseSchema().validate(response_data)
    assert not errors
    assert len(response_data['data']) == 1
    assert response_data['data'][0]['id'] == user.id
    assert response_data['data'][0]['username'] == user.username
    assert response_data['data'][0]['email'] == user.email


async def test_retrieve_update_destroy_user(authorized_api_client, db_session):
    api_client, user = authorized_api_client
    other_user = UserFactory()
    db_session.commit()

    # # Get methods
    # Get info about authorized user
    response = await api_client.get(url_for(views.UserRetrieveUpdateDestroyAPIView.URL_PATH, user_id=user.id))
    # Response checks
    assert response.status == HTTPStatus.OK
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    errors = schema.UserDetailsResponseSchema().validate(response_data)
    assert not errors
    assert response_data['data']['id'] == user.id
    assert response_data['data']['username'] == user.username
    assert response_data['data']['email'] == user.email

    # Get info about other_user
    response = await api_client.get(url_for(views.UserRetrieveUpdateDestroyAPIView.URL_PATH, user_id=other_user.id))
    # Response checks
    assert response.status == HTTPStatus.OK
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    errors = schema.UserDetailsResponseSchema().validate(response_data)
    assert not errors
    assert response_data['data']['id'] == other_user.id
    assert response_data['data']['username'] == other_user.username
    assert response_data['data']['email'] == other_user.email

    # Get info about not exists user
    last_id = db_session.query(User).order_by(User.id.desc()).first().id
    response = await api_client.get(url_for(views.UserRetrieveUpdateDestroyAPIView.URL_PATH, user_id=last_id + 100))
    # Response checks
    assert response.status == HTTPStatus.NOT_FOUND
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    assert response_data['error']['code'] == 'not_found'
    assert response_data['error']['message'] == '404: Not Found'

    # # Patch methods
    # Attempt to update authorized user info with not unique username
    invalid_patch_data = {'username': other_user.username}
    response = await api_client.patch(url_for(views.UserRetrieveUpdateDestroyAPIView.URL_PATH, user_id=user.id),
                                      data=invalid_patch_data)
    # Response checks
    assert response.status == HTTPStatus.BAD_REQUEST
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    assert len(response_data['error']['fields'].keys()) == 1
    assert response_data['error']['fields']['username'][0] == 'User with this username already exists.'

    # Update authorized user info
    new_username = user.username + '_patched'
    valid_patch_data = {'username': new_username}
    response = await api_client.patch(url_for(views.UserRetrieveUpdateDestroyAPIView.URL_PATH, user_id=user.id),
                                      data=valid_patch_data)
    # Response checks
    assert response.status == HTTPStatus.OK
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    errors = schema.UserDetailsResponseSchema().validate(response_data)
    assert not errors
    assert response_data['data']['id'] == user.id
    assert response_data['data']['username'] == new_username
    assert response_data['data']['email'] == user.email
    # DB check
    db_session.refresh(user)  # get updates from db
    assert db_session.query(User).filter(User.id == user.id).first().username == new_username

    # Attempt to update other_user with authorized user
    old_username = other_user.username
    invalid_patch_data = {'username': other_user.username + '_patched'}
    response = await api_client.patch(url_for(views.UserRetrieveUpdateDestroyAPIView.URL_PATH, user_id=other_user.id),
                                      data=invalid_patch_data)
    # Response checks
    assert response.status == HTTPStatus.FORBIDDEN
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    assert response_data['error']['code'] == 'forbidden'
    assert response_data['error']['message'] == '403: You do not have permission to perform this action.'
    # DB check
    db_session.refresh(other_user)  # get updates from db
    assert db_session.query(User).filter(User.id == other_user.id).first().username == old_username

    # # Delete methods
    # Attempt to delete other_user with authorized user
    response = await api_client.delete(url_for(views.UserRetrieveUpdateDestroyAPIView.URL_PATH, user_id=other_user.id))
    # Response checks
    assert response.status == HTTPStatus.FORBIDDEN
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    assert response_data['error']['code'] == 'forbidden'
    assert response_data['error']['message'] == '403: You do not have permission to perform this action.'
    # DB check
    db_session.refresh(other_user)  # get updates from db
    assert db_session.query(User).filter(User.id == other_user.id).count() == 1

    # Delete authorized user
    response = await api_client.delete(url_for(views.UserRetrieveUpdateDestroyAPIView.URL_PATH, user_id=user.id))
    # Response checks
    assert response.status == HTTPStatus.NO_CONTENT
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    assert response_data is None
    # DB check
    assert db_session.query(User).filter(User.id == user.id).count() == 0


async def test_retrieve_update_bill(authorized_api_client, db_session):
    api_client, user = authorized_api_client
    user_bill = BillFactory(user=user)
    other_user = BillFactory().user
    db_session.commit()

    # # Get methods
    # Retrieve bill info for authorized user
    response = await api_client.get(url_for(views.BillRetrieveUpdateAPIView.URL_PATH, user_id=user.id))
    # Response checks
    assert response.status == HTTPStatus.OK
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    errors = schema.BillDetailsResponseSchema().validate(response_data)
    assert not errors
    assert response_data['data']['id'] == user_bill.id
    assert response_data['data']['user_id'] == user.id
    assert response_data['data']['balance'] == user_bill.balance
    assert response_data['data']['tariff'] == user_bill.tariff

    # Attempt to retrieve bill info for other_user
    response = await api_client.get(url_for(views.BillRetrieveUpdateAPIView.URL_PATH, user_id=other_user.id))
    # Response checks
    assert response.status == HTTPStatus.FORBIDDEN
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    assert response_data['error']['code'] == 'forbidden'
    assert response_data['error']['message'] == '403: You do not have permission to perform this action.'

    # Get bill info about not exists user
    last_id = db_session.query(User).order_by(User.id.desc()).first().id
    response = await api_client.get(url_for(views.BillRetrieveUpdateAPIView.URL_PATH, user_id=last_id + 100))
    # Response checks
    assert response.status == HTTPStatus.NOT_FOUND
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    assert response_data['error']['code'] == 'not_found'
    assert response_data['error']['message'] == '404: Not Found'

    # # Patch methods
    # Update authorized user bill info
    new_tariff = user_bill.tariff + 1
    patch_data = {'tariff': new_tariff}
    response = await api_client.patch(url_for(views.BillRetrieveUpdateAPIView.URL_PATH, user_id=user.id),
                                      data=patch_data)
    # Response checks
    assert response.status == HTTPStatus.OK
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    errors = schema.BillDetailsResponseSchema().validate(response_data)
    assert not errors
    assert response_data['data']['id'] == user_bill.id
    assert response_data['data']['user_id'] == user.id
    assert response_data['data']['balance'] == user_bill.balance
    assert response_data['data']['tariff'] == new_tariff
    # DB check
    db_session.refresh(user_bill)  # get updates from db
    assert db_session.query(Bill).filter(Bill.user_id == user.id).first().tariff == new_tariff


async def test_create_payment(authorized_api_client, db_session):
    api_client, user = authorized_api_client
    user_bill = BillFactory(user=user)
    db_session.commit()

    # Try to create payment without all required fields
    partial_data = {
        'amount': 10,
    }
    # Response checks
    response = await api_client.post(url_for(views.PaymentCreateAPIView.URL_PATH), data=partial_data)
    assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    assert len(response_data['error']['fields'].keys()) == 1
    assert response_data['error']['fields'].keys() == {'bill_id'}

    # Try to create payment with invalid data
    invalid_data = {
        'bill_id': '123',
        'amount': -123,
    }
    # Response checks
    response = await api_client.post(url_for(views.PaymentCreateAPIView.URL_PATH), data=invalid_data)
    assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    assert len(response_data['error']['fields'].keys()) == 2
    assert response_data['error']['fields']['bill_id'][0] == 'Not a valid integer.'
    assert response_data['error']['fields']['amount'][0] == 'Must be greater than 0.'

    # Try to create payment with invalid bill_id
    last_id = db_session.query(Bill).order_by(Bill.id.desc()).first().id
    invalid_bill_id_data = {
        'bill_id': last_id + 100,
        'amount': 10,
    }
    # Response checks
    response = await api_client.post(url_for(views.PaymentCreateAPIView.URL_PATH), data=invalid_bill_id_data)
    assert response.status == HTTPStatus.NOT_FOUND
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    assert response_data['error']['code'] == 'not_found'
    assert response_data['error']['message'] == '404: Not Found'

    # Creates a new payment
    old_balance = user_bill.balance
    payment_data = {
        'bill_id': user_bill.id,
        'amount': 10,
    }
    assert db_session.query(Payment).filter(Payment.bill_id == payment_data['bill_id']).count() == 0
    # Response checks
    response = await api_client.post(url_for(views.PaymentCreateAPIView.URL_PATH), data=payment_data)
    assert response.status == HTTPStatus.CREATED
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    errors = schema.PaymentDetailsResponseSchema().validate(response_data)
    assert not errors
    assert response_data['data']['bill_id'] == payment_data['bill_id']
    assert response_data['data']['amount'] == payment_data['amount']
    # DB checks
    assert db_session.query(Payment).filter(Payment.bill_id == payment_data['bill_id']).count() == 1
    payment_from_db = db_session.query(Payment).filter(Payment.bill_id == payment_data['bill_id']).first()
    assert payment_from_db.amount == payment_data['amount']
    # Bill balance updates check
    db_session.refresh(user_bill)  # get updates from db
    assert user_bill.balance == old_balance + payment_data['amount']


async def test_get_payment_list(authorized_api_client, db_session):
    api_client, user = authorized_api_client
    user_bill = BillFactory(user=user)
    other_user = UserFactory()
    # Creates payments pool
    n = 5
    for _ in range(n):
        PaymentFactory(bill=user_bill)
    db_session.commit()

    # Retrieve payments list for authorized user
    response = await api_client.get(url_for(views.PaymentsListAPIView.URL_PATH, user_id=user.id))
    # Response checks
    assert response.status == HTTPStatus.OK
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    errors = schema.PaymentListResponseSchema().validate(response_data)
    assert not errors
    assert len(response_data['data']) == n

    # Attempt to retrieve payments list for other_user
    response = await api_client.get(url_for(views.PaymentsListAPIView.URL_PATH, user_id=other_user.id))
    # Response checks
    assert response.status == HTTPStatus.FORBIDDEN
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    assert response_data['error']['code'] == 'forbidden'
    assert response_data['error']['message'] == '403: You do not have permission to perform this action.'

    # Attempt to retrieve payments list for not exists user
    last_id = db_session.query(User).order_by(User.id.desc()).first().id
    response = await api_client.get(url_for(views.PaymentsListAPIView.URL_PATH, user_id=last_id + 100))
    # Response checks
    assert response.status == HTTPStatus.NOT_FOUND
    assert response.content_type == 'application/json'
    # Response data checks
    response_data = await response.json()
    assert response_data['error']['code'] == 'not_found'
    assert response_data['error']['message'] == '404: Not Found'
