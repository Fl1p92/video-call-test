from .views import UserCreateAPIView, LoginAPIView


API_VIEWS = (LoginAPIView, UserCreateAPIView)
JWT_WHITE_LIST = (LoginAPIView.URL_PATH, UserCreateAPIView.URL_PATH)
