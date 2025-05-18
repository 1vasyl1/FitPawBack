from django.contrib import admin
from django.contrib.auth.decorators import login_required

from accounts.models import User


admin.site.register(User)