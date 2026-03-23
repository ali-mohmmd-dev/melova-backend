import os

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Max
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    CustomTokenObtainPairSerializer,
    GoogleAuthSerializer,
    RegisterSerializer,
    UserSerializer,
    CustomerListSerializer,
)

User = get_user_model()    


def get_tokens_for_user(user):
    """Generate JWT access + refresh token pair for a user."""
    refresh = RefreshToken.for_user(user)
    
    # Add custom claims to the access token
    access_token = refresh.access_token
    access_token["email"] = user.email
    access_token["name"] = user.name
    access_token["is_staff"] = user.is_staff
    access_token["is_superuser"] = user.is_superuser
    
    return {
        "refresh": str(refresh),
        "access": str(access_token),
    }


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Register a new user with email and password.
    Returns JWT tokens on success.
    """

    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = get_tokens_for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                **tokens,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Login with email + password. Returns JWT access + refresh tokens and user info.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Blacklist the provided refresh token to log the user out.
    Requires: { "refresh": "<token>" }
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response(
                {"detail": "Invalid or already blacklisted token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_205_RESET_CONTENT)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/auth/me/   — Return current user's profile.
    PATCH /api/auth/me/  — Update current user's profile (name, avatar).
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            from .serializers import UserSerializer as S

            class UpdatableUserSerializer(S):
                class Meta(S.Meta):
                    read_only_fields = ["id", "email", "is_google_user"]

            return UpdatableUserSerializer
        return UserSerializer


class GoogleLoginView(APIView):
    """
    POST /api/auth/google/
    Exchange a Google id_token (obtained on the frontend via Google Sign-In) for
    Django JWT tokens.

    Request body: { "id_token": "<google_id_token>" }
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["id_token"]
        google_client_id = os.environ.get("GOOGLE_CLIENT_ID", "")

        # Verify the token with Google
        try:
            idinfo = google_id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                google_client_id,
            )
        except ValueError as e:
            return Response(
                {"detail": f"Invalid Google token: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        google_id = idinfo.get("sub")
        email = idinfo.get("email")
        name = idinfo.get("name", "")
        avatar = idinfo.get("picture", "")

        if not email:
            return Response(
                {"detail": "Google account has no email address."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get or create the user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "name": name,
                "avatar": avatar,
                "google_id": google_id,
                "is_google_user": True,
            },
        )

        # If user exists but hasn't linked their Google account yet, link it
        if not created and not user.google_id:
            user.google_id = google_id
            user.is_google_user = True
            if not user.avatar and avatar:
                user.avatar = avatar
            if not user.name and name:
                user.name = name
            user.save()

        tokens = get_tokens_for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "created": created,
                **tokens,
            },
            status=status.HTTP_200_OK,
        )


class CustomerListView(generics.ListAPIView):
    """
    GET /api/auth/customers/
    Admin only: List all customers (non-staff users) with order stats.
    """

    permission_classes = [permissions.IsAdminUser]
    serializer_class = CustomerListSerializer

    def get_queryset(self):
        return (
            User.objects.filter(is_staff=False)
            .annotate(
                order_count=Count("orders", distinct=True),
                total_spent=Sum("orders__total"),
                last_order_date=Max("orders__created_at"),
            )
            .order_by("-date_joined")
        )
