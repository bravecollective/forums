# encoding: utf-8

from __future__ import unicode_literals

from urllib import unquote

from web.auth import authenticate, deauthenticate
from web.core import config, url, request, session
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
        
        success = str(url.complete('/authorized', params=dict(redirect=redirect)))
        failure = str(url.complete('/nolove'))
        
        result = api.core.authorize(success=success, failure=failure)
        
        raise HTTPFound(location=result.location)
    
    def authorized(self, token, redirect=None):
        """Callback from Core indicating successful authentication/authorization.
        
        We pass through to the method defined in the INI file, usually:
            brave.forums.auth.model:Character.authenticate
        """

        # Prevent users from specifying their session IDs (Some user-agents were sending null ids, leading to users
        # authenticated with a session id of null
        session.regenerate_id()

        authenticate(token)
        raise HTTPFound(location=unquote(redirect).decode('utf8') if redirect else '/')
    
    def nolove(self, token):
        """User declined the authorization attempt."""
        return 'brave.forums.template.whynolove', dict()
    
    def goodbye(self):
        """User is done for this session."""
        deauthenticate(True)
        raise HTTPFound(location='/')
    
    def switch(self):
        """User wishes the re-authorize this application with a different character."""
        deauthenticate(True)
        
        api = API(config['api.endpoint'], config['api.identity'], config['api.private'], config['api.public'])
        
        success = str(url.complete('/authorized', params=dict(redirect=request.referrer)))
        failure = str(url.complete('/nolove'))
        
        result = api.core.authorize(success=success, failure=failure)
        
        raise HTTPFound(location=result.location)
