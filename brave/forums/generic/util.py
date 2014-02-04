# encoding: utf-8

from __future__ import unicode_literals

from web.core import request
from web.core.http import HTTPNotFound


log = __import__('logging').getLogger(__name__)


def only(fn):
    return dict(only=fn)


def serialize():
    if request.format and request.format not in ('json', 'yaml', 'bencode'):
        raise HTTPNotFound()
    
    return (request.format or 'json') + ':'


def context(**kw):
    ctx = getattr(request.controller, '__context__', None)
    
    kw['controller'] = request.controller
    
    if hasattr(request, 'record'):
        kw['record'] = request.record
    
    if not ctx: return kw
    return dict(ctx() if callable(ctx) else ctx, **kw)
