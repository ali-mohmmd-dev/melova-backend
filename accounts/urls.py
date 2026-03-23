from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import GoogleLoginView, LoginView, LogoutView, RegisterView, UserProfileView, CustomerListView

urlpatterns = [
    # Standard JWT auth
    path("register/", RegisterView.as_view(), name="auth_register"),
    path("login/", LoginView.as_view(), name="auth_login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="auth_logout"),
    # Current user profile
    path("me/", UserProfileView.as_view(), name="auth_me"),
    # Google OAuth
    path("google/", GoogleLoginView.as_view(), name="auth_google"),
    # Admin
    path("customers/", CustomerListView.as_view(), name="admin_customers"),
]
