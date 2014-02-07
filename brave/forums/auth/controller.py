# encoding: utf-8

from __future__ import unicode_literals

from web.auth import authenticate, deauthenticate
from web.core import config, url
from web.core.http import HTTPFound

from brave.api.client import API


log = __import__('logging').getLogger(__name__)



class AuthenticationMixIn(object):
    def authorize(self, redirect=None):
        # Perform the initial API call and direct the user.
        
        if redirect is None:
            redirect = request.referrer
            redirect = '/' if not redirect or redirect.endswith(request.script_name) else redirect
        
        api = API(config['api.endpoint'], config['api.identity'], config['api.private'], config['api.public'])
        
        success = str(url.complete('/authorized', redirect=redirect))
        failure = str(url.complete('/nolove'))
        
        result = api.core.authorize(success=success, failure=failure)
        
        raise HTTPFound(location=result.location)
    
    def authorized(self, token, redirect=None):
        # Capture the returned token and use it to look up the user details.
        # If we don't have this character, create them.
        # Store the token against this user account.
        # Note that our own 'sessions' may not last beyond the UTC date returned as 'expires'.
        # (Though they can be shorter!)
        
        # We request an authenticated session from the server.
        
        authenticate(token)
        
        raise HTTPFound(location=redirect or '/')
    
    def nolove(self, token):
        return 'brave.forums.template.whynolove', dict()
    
    def goodbye(self):
        deauthenticate(True)
        raise HTTPFound(location='/')
