from django.db import models
import uuid
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    img = models.ImageField(upload_to='img/', null=True, blank=True)

    def __str__(self):
        return self.username