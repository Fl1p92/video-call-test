from .views import (
    LoginAPIView, UserCreateAPIView, UsersListAPIView, UserRetrieveUpdateDestroyAPIView, BillRetrieveUpdateAPIView,
    PaymentCreateAPIView, PaymentsListAPIView, CallCreateAPIView, CallsListAPIView
)


API_VIEWS = (
    LoginAPIView,  # auth
    UserCreateAPIView, UsersListAPIView, UserRetrieveUpdateDestroyAPIView,  # users
    BillRetrieveUpdateAPIView, PaymentCreateAPIView, PaymentsListAPIView,  # bills
    CallCreateAPIView, CallsListAPIView,  # calls
)
JWT_WHITE_LIST = (LoginAPIView.URL_PATH, UserCreateAPIView.URL_PATH)
