from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Read-only serialiser for returning user profile data."""

    class Meta:
        model = User
        fields = ["id", "email", "name", "avatar", "is_google_user"]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    """Handles user registration with email + password."""

    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm password")

    class Meta:
        model = User
        fields = ["email", "name", "phone", "password", "password2"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            name=validated_data.get("name", ""),
            phone=validated_data.get("phone", ""),
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Extends the default JWT serialiser to include user info in the response."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token["email"] = user.email
        token["name"] = user.name
        return token

    def validate(self, attrs):
        # Use email as the login field
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class GoogleAuthSerializer(serializers.Serializer):
    """Accepts a Google id_token from the frontend and verifies it."""

    id_token = serializers.CharField(required=True)
