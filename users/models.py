from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class CustomUserManager(BaseUserManager):
    def create_user(self,username, password=None, **extra_fields):
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(unique=True, max_length=150)
    email = models.EmailField(unique=True, blank=True, null=True)
    mobile = models.CharField(max_length=15, blank=True, null=True)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ('username', )

    def __str__(self):
        return self.username

# Create your models here.

class Points(models.Model):
    host = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    total_points = models.IntegerField(default=0)

    def __str__(self):
        if self.host:
            return self.host.username
        else:
            return "No Host"

class Product(models.Model):
    name = models.CharField(max_length=100)
    point_value = models.IntegerField()

    def __str__(self) -> str:
        return self.name