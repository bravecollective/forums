# encoding: utf-8

from __future__ import unicode_literals

from web.auth import user
from web.core import Controller, HTTPMethod, url, request
from web.core.http import HTTPNotFound, HTTPForbidden

from brave.forums.component.forum.model import Forum
from brave.forums.component.thread.controller import ThreadController
from brave.forums.util import resume, only


log = __import__('logging').getLogger(__name__)


class ForumIndex(HTTPMethod):
    def __init__(self, forum):
        self.forum = forum
        super(ForumIndex, self).__init__()
    
    def get(self, page=1):
        page = int(page)
        data = dict(page=int(page), forum=self.forum)
        
        if request.is_xhr or request.format == 'html':
            return only('brave.forums.template.forum', 'threads',
                    results = self.forum.threads.filter(flag__sticky=False),
                    limit = 5,
                    **data
                )
        
        return 'brave.forums.template.forum', data
    
    def post(self, title, message, upload=None, vote=None):
        if not self.forum.user_can_write(user):
            log.debug("deny post to %r: w=%r t=%r", self.forum, self.forum.write, user.tags)
            raise HTTPNotFound()
        
        if not title.strip() or not message.strip():
            return 'json:', dict(success=False, message="Must supply both a title and a message for a new thread.")
        
        thread = self.forum.create_thread(user._current_obj(), title, message)
        
        return 'json:', dict(success=True, id=str(thread.id))


class ForumController(Controller):
    def __init__(self, short):
        try:
            f = self.forum = Forum.objects.get(short=short)
        except Forum.DoesNotExist:
            raise HTTPNotFound()
        
        if not f.user_can_read(user):
            log.debug("conditions failed")
            if user:
                raise HTTPNotFound()
            raise HTTPForbidden()
        
        self.index = ForumIndex(f)
        
        super(ForumController, self).__init__()

    def read(self):
        user.mark_forum_read(self.forum)
        return "json:", dict(success=True)
    
    def __lookup__(self, thread, *args, **kw):
        log.debug("Continuing from %r to thread %s.", self.forum, thread)
        return resume(ThreadController, thread, args, self.forum)
