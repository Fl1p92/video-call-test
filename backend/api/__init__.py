from .views import (
    LoginAPIView,  # auth
    UserCreateAPIView, UsersListAPIView, UserRetrieveUpdateDestroyAPIView,  # users
)


API_VIEWS = (LoginAPIView, UserCreateAPIView, UsersListAPIView, UserRetrieveUpdateDestroyAPIView)
JWT_WHITE_LIST = (LoginAPIView.URL_PATH, UserCreateAPIView.URL_PATH)
