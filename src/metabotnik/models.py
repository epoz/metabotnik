from django.db import models
from django.contrib.auth.models import User


class DropBoxInfo(models.Model):
    user = models.OneToOneField(User, primary_key=True)
    access_token = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now=True)