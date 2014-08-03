# encoding: utf-8

from __future__ import unicode_literals

from sys import exit

from binascii import unhexlify
from hashlib import sha256
from ecdsa.keys import SigningKey, VerifyingKey
from ecdsa.curves import NIST256p

from web.auth import always, Predicate
from web.core import config, request
from web.core.http import HTTPNotFound
from marrow.mailer import Mailer
from marrow.util.convert import boolean


log = __import__('logging').getLogger(__name__)



def only(template, segment, **data):
    return template, data, dict(only=segment)


class DebuggingPredicate(Predicate):
    def __nonzero__(self):
        return boolean(config.get('debug', False))

debugging = DebuggingPredicate()


class StartupMixIn(object):
    def __init__(self):
        from brave.forums import util
        
        # Configure mail delivery services.
        util.mail = Mailer(config, 'mail')
        util.mail.start()
        
        # Load our keys into a usable form.
        try:
            config['api.identity']
            config['api.private'] = SigningKey.from_string(unhexlify(config['api.private']), curve=NIST256p, hashfunc=sha256)
            config['api.public'] = VerifyingKey.from_string(unhexlify(config['api.public']), curve=NIST256p, hashfunc=sha256)
        except:
            log.critical("Core Service API identity, public, or private key missing or invalid.")
            
            private = SigningKey.generate(NIST256p, hashfunc=sha256)
            
            log.critical("Here's a new private key; update the api.private setting to reflect this.\n%s", private.to_string().encode('hex'))
            log.critical("Here's that key's public key; this is what you register with Core.\n%s",  private.get_verifying_key().to_string().encode('hex'))
            log.critical("After registering, save the server's public key to api.public and your service's ID to api.identity.")
            
            exit(-1)
        
        super(StartupMixIn, self).__init__()


def resume(Handler, element, remaining, *args, **kw):
    request.path_info_pop()
    
    if '.' in element:
        element, _, request.format = element.rpartition('.')
    else:
        request.format = None
    
    return Handler(element, *args, **kw), remaining


def require(*predicates):
    def conditional(*args, **kw):
        for predicates, handler in conditional.handlers:
            if not all(predicates):
                continue
            
            return handler(*args, **kw)
            
        else:
            raise HTTPNotFound
    
    def require(*predicates):
        def decorator(fn):
            conditional.append((predicates, fn))
            return conditional
        
        return decorator
    
    def otherwise(fn):
        conditional.handlers.append(((always, ), fn))
        return conditional
    
    conditional.handlers = []
    conditional.require = require
    conditional.otherwise = otherwise
    
    def decorator(fn):
        conditional.handlers.append((predicates, fn))
        return conditional
    
    return decorator
