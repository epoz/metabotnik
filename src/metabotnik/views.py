from django.shortcuts import render, resolve_url, redirect
from django.conf import settings
from django.contrib.auth.models import User

def home(request):
    return render(request, 'index.html')

