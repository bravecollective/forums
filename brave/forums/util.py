# encoding: utf-8

from __future__ import unicode_literals

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
        config['api.private'] = SigningKey.from_string(unhexlify(config['api.private']), curve=NIST256p, hashfunc=sha256)
        config['api.public'] = VerifyingKey.from_string(unhexlify(config['api.public']), curve=NIST256p, hashfunc=sha256)
        
        super(StartupMixIn, self).__init__()
