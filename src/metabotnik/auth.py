from django.shortcuts import render, resolve_url, redirect
from django.core.urlresolvers import reverse
import dropbox
from dropbox import DropboxOAuth2Flow, Dropbox
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.conf import settings
from django.http.response import HttpResponseBadRequest, HttpResponseForbidden
from django.core.mail import send_mail
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
        oauth_result = get_dropbox_auth_flow(request).finish(request.GET)
        account_id = oauth_result.account_id
        access_token = oauth_result.access_token
        user = authenticate(account_id=account_id, access_token=access_token)
        if user.is_active:
            login(request, user)
            return redirect('/')
        else:
            return redirect(reverse('help', args=['await']))
    except dropbox.oauth.BadRequestException, e:
        return HttpResponseBadRequest()
    except dropbox.oauth.BadStateException, e:
        # Start the auth flow again.
        return redirect("login")
    except dropbox.oauth.CsrfException, e:
        return HttpResponseForbidden()
    except dropbox.oauth.NotApprovedException, e:
        return redirect("home")
    except dropbox.oauth.ProviderException, e:
        return HttpResponseForbidden()


class DropboxAuthBackend(object):
    def authenticate(self, **credentials):
        #TODO user_id comes in here?
        account_id, access_token = credentials.get('account_id'), credentials.get('access_token')
        client = Dropbox(access_token)
        info = client.users_get_current_account()
        try:
            user = User.objects.get(username=account_id)
        except User.DoesNotExist:
            user = User.objects.create(username=account_id, 
                                       password='bogus',
                                       last_name=info.name.display_name,
                                       email=info.email,
                                       is_active=False)
            DropBoxInfo.objects.create(user=user, access_token=access_token)
            send_mail('A new Metabotnik user has registered', 
                      'And the user %s is https://metabotnik.com/admin/auth/user/%s/' % (user.last_name, user.pk), 
                          'info@metabotnik.com', ['eposthumus@gmail.com'], fail_silently=True)

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None