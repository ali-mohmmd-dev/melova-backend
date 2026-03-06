from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Custom manager that uses email as the unique identifier instead of username."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set.")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom User model that supports both email/password and Google OAuth."""

    username = None  # Remove username field; email is the unique identifier
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=255, blank=True)
    
    objects = UserManager()
    name = models.CharField(max_length=255, blank=True)
    avatar = models.URLField(blank=True, null=True)
    google_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    is_google_user = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # no extra required fields beyond email

    def __str__(self):
        return self.email
