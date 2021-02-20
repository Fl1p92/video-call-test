from .views import (
    LoginAPIView, UserCreateAPIView, UsersListAPIView, UserRetrieveUpdateDestroyAPIView, BillRetrieveUpdateAPIView,
    PaymentCreateAPIView, PaymentsListAPIView,
)


API_VIEWS = (
    LoginAPIView,  # auth
    UserCreateAPIView, UsersListAPIView, UserRetrieveUpdateDestroyAPIView,  # users
    BillRetrieveUpdateAPIView, PaymentCreateAPIView, PaymentsListAPIView,  # bills
)
JWT_WHITE_LIST = (LoginAPIView.URL_PATH, UserCreateAPIView.URL_PATH)
