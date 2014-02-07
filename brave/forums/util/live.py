# encoding: utf-8

from __future__ import unicode_literals

import requests
import json

from hashlib import sha256
from web.auth import user

from brave.api.client import API


log = __import__('logging').getLogger(__name__)


class Channel(object):
    """A realtime broadcast channel for broadcast messaging.
    
    Primarily used to write messages to a browser-based client.
    
    Channel IDs are SHA256 hashes comprised of the browser session ID, user ID (if applicable), and a nonce.
    """
    
    url_base = b'https://forums.bravecollective.net/_push?id='
    receiver_base = b'/listen?id='
    
    def __init__(self, *tokens):
        self.id = self.hash(tokens)
    
    @property
    def url(self):
        return b'{0}{1}'.format(self.url_base, self.id)
    
    @property
    def receiver(self):
        return b'{0}{1}'.format(self.receiver_base, self.id)
    
    @classmethod
    def hash(cls, tokens):
        return sha256(b"".join(str(i) for i in tokens)).hexdigest()
    
    def send(self, handler, content):
        payload = dict(
                handler = handler,
                payload = content,
            )
        
        log.debug("push %s\n%s", self.url, json.dumps(payload))
        
        try:
            r = requests.post(self.url, data=json.dumps(payload), verify=False)
            if not r.status_code < 300:
                log.error("Error %d posting push notification.", r.status_code)
                return False
        except:
            log.exception("Error posting push notification.")
            return False
        
        return True


class UserChannel(Channel):
    @classmethod
    def hash(cls, tokens):
        return Channel.hash(session.id, session['_creation_time'], repr(user._current_obj()), *tokens)
