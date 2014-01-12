# encoding: utf-8

from __future__ import unicode_literals

import requests
import json
import bbcode

from binascii import hexlify, unhexlify
from hashlib import sha256
from web.auth import authenticate, user
from web.core import config, Controller, url, request, response
from web.core.http import HTTPFound, HTTPNotFound
from web.auth import authenticated
from marrow.mailer import Mailer
from ecdsa.keys import SigningKey, VerifyingKey
from ecdsa.curves import NIST256p


from brave.core.api.client import API
from brave.forums import util
from brave.forums.model import Forum, Thread, Comment


log = __import__('logging').getLogger(__name__)


class Channel(object):
    """A realtime broadcast channel for broadcast messaging.
    
    Primarily used to write messages to a browser-based client.
    
    Channel IDs are SHA256 hashes comprised of the browser session ID, user ID (if applicable), and a nonce.
    """
    
    url_base = b'http://forum.bravecollective.net/_push?id='
    receiver_base = b'/_live?id='
    
    def __init__(self, *tokens):
        self.id = self.hash(tokens)
    
    @property
    def url(self):
        return b'{0}{1}'.format(self.url_base, sha256(self.id).hexdigest())
    
    @property
    def receiver(self):
        return b'{0}{1}'.format(self.url, sha256(self.id).hexdigest())
    
    @classmethod
    def hash(cls, tokens):
        return sha256(b"".join(str(i) for i in tokens)
    
    def send(self, cls, content):
        payload = dict(
                class = cls,
                payload = content,
            )
        
        try:
            r = requests.post(self.url, data=json.dumps(payload))
            if not r.status_code == requests.codes.ok:
                log.error("Error %d posting push notification.", r.status_code)
                return False
        except:
            log.exception("Error posting push notification.")
        
        return True


class UserChannel(Channel):
    @classmethod
    def hash(cls, tokens):
        return Channel.hash(session.id, session['_creation_time'], repr(user._current_obj(), *tokens)
