# encoding: utf-8

from __future__ import unicode_literals

from sys import exit
from binascii import unhexlify
from hashlib import sha256
from web.core import config
from marrow.mailer import Mailer
from ecdsa.keys import SigningKey, VerifyingKey
from ecdsa.curves import NIST256p


log = __import__('logging').getLogger(__name__)


class StartupMixIn(object):
    def __init__(self):
        from brave.forums import util
        
        # Configure mail delivery services.
        util.mail = Mailer(config, 'mail')
        util.mail.start()
        
        # Load our keys into a usable form.
        try:
            config['api.private'] = SigningKey.from_string(unhexlify(config['api.private']), curve=NIST256p, hashfunc=sha256)
            config['api.public'] = VerifyingKey.from_string(unhexlify(config['api.public']), curve=NIST256p, hashfunc=sha256)
        except:
            log.critical("Core Service API identity, public, or private key missing.")
            
            private = SigningKey.generate(NIST256p, hashfunc=sha256)
            
            log.critical("Here's a new private key; update the api.private setting to reflect this.\n%s", private.to_string().encode('hex'))
            log.critical("Here's that key's public key; this is what you register with Core.\n%s",  private.get_verifying_key().to_string().encode('hex'))
            log.critical("After registering, save the server's public key to api.public and your service's ID to api.identity.")
            
            exit(-1)
        
        super(StartupMixIn, self).__init__()
