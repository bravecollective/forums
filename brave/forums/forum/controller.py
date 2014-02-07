# encoding: utf-8

from __future__ import unicode_literals

import bbcode

from web.auth import user
from web.core import Controller, HTTPMethod, url, request
from web.core.http import HTTPNotFound, HTTPForbidden

from brave.forums.thread.controller import ThreadController
from brave.forums.forum.model import Forum


log = __import__('logging').getLogger(__name__)



class ForumIndex(HTTPMethod):
    def __init__(self, forum):
        self.forum = forum
        super(ForumIndex, self).__init__()
    
    def get(self, page=1):
        page = int(page)
        
        if request.is_xhr:
            return 'brave.forums.template.forum', dict(page=page, forum=self.forum), dict(only='threads')
        
        return 'brave.forums.template.forum', dict(page=page, forum=self.forum)
    
    def post(self, title, message, upload=None, vote=None):
        return 'json:', ThreadController._create(self.forum, title, message)


class ForumController(Controller):
    def __init__(self, short):
        try:
            f = self.forum = Forum.objects.get(short=short)
        except Forum.DoesNotExist:
            raise HTTPNotFound()
        
        tags = user.tags if user else ()
        
        # Weird structure here.
        if f.moderate and f.moderate in tags:
            pass
        elif f.write and f.write in tags:
            pass
        elif not f.read or f.read in tags:
            pass
        else:
            raise HTTPForbidden()
        
        self.index = ForumIndex(self.forum)
        
        super(ForumController, self).__init__()
    
    def __lookup__(self, thread, *args, **kw):
        request.path_info_pop()
        return ThreadController(self.forum, thread), args
