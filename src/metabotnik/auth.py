from django.shortcuts import render, resolve_url, redirect
from dropbox.client import DropboxOAuth2Flow, DropboxClient
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.conf import settings
from django.http.response import HttpResponseBadRequest, HttpResponseForbidden
from metabotnik.models import DropBoxInfo

def get_dropbox_auth_flow(request):
    proto = 'https://' if request.is_secure() else 'http://'
    redirect_uri = proto + request.META['HTTP_HOST'] + resolve_url('dropboxauthredirect')
    return DropboxOAuth2Flow(settings.DROPBOX_APP_KEY, settings.DROPBOX_APP_SECRET, 
                                     redirect_uri, request.session, "dropbox-auth-csrf-token")

def logoutview(request):
    logout(request)
    return render(request, 'index.html')    

def loginview(request):
    # Check to see if user is logged in already
    if request.user.is_authenticated():
        raise Exception()
    return redirect(get_dropbox_auth_flow(request).start())    

def dropboxauthredirect(request):
    try:
        access_token, user_id, url_state = \
                get_dropbox_auth_flow(request).finish(request.REQUEST)        
        user = authenticate(user_id=user_id, access_token=access_token)
        login(request, user)
        return redirect('/')
    except DropboxOAuth2Flow.BadRequestException, e:
        return HttpResponseBadRequest()
    except DropboxOAuth2Flow.BadStateException, e:
        # Start the auth flow again.
        return redirect("login")
    except DropboxOAuth2Flow.CsrfException, e:
        return HttpResponseForbidden()
    except DropboxOAuth2Flow.NotApprovedException, e:
        return redirect("home")
    except DropboxOAuth2Flow.ProviderException, e:
        return HttpResponseForbidden()

class DropboxAuthBackend(object):
    def authenticate(self, **credentials):
        user_id, access_token = credentials.get('user_id'), credentials.get('access_token')
        client = DropboxClient(access_token)
        info = client.account_info()
        try:
            user = User.objects.get(username=user_id)
        except User.DoesNotExist:
            user = User.objects.create(username=user_id, 
                                       password='bogus',
                                       last_name=info.get('display_name'),
                                       email=info.get('email'))
            DropBoxInfo.objects.create(user=user, access_token=access_token)
        
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None