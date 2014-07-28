# encoding: utf-8

from __future__ import unicode_literals

from bson import ObjectId
from datetime import datetime

from web.auth import user
from web.core import Controller, HTTPMethod, url, request
from web.core.http import HTTPNotFound

from brave.forums.auth.model import Character
from brave.forums.component.thread.model import Thread
from brave.forums.component.comment.controller import CommentController
from brave.forums.component.comment.model import Comment
from brave.forums.util import resume, only


log = __import__('logging').getLogger(__name__)


class ThreadIndex(HTTPMethod):
    def __init__(self, forum, thread):
        self.forum = forum
        self.thread = thread
        super(ThreadIndex, self).__init__()
    
    def get(self, page=1):
        Thread.objects(id=self.thread.id).update_one(inc__stat__views=1)
        
        if user:
            user.mark_thread_read(self.thread)
        
        return 'brave.forums.template.thread', dict(page=page, forum=self.forum, thread=self.thread)
    
    def post(self, message, upload=None, vote=None):
        forum = self.forum
        
        if not forum.user_can_write(user):
            return 'json:', dict(success=False, message="Not allowed.")
        
        if not message or not message.strip():
            return 'json:', dict(success=False, message="Empty message.")
        
        new_comment = self.thread.add_comment(user._current_obj(), message)
        
        return 'json:', dict(success=True, comment=str(new_comment.id))



class ThreadController(Controller):
    def __init__(self, id, forum):
        self.forum = forum
        
        try:
            t = self.thread = Thread.objects.get(id=id)
        except Thread.DoesNotExist:
            raise HTTPNotFound()
            
        if self.forum.short != self.thread.forum.short:
            raise HTTPNotFound()
        
        self.index = ThreadIndex(forum, t)
        
        log.debug("%r", t)
        
        super(ThreadController, self).__init__()
    
    def __lookup__(self, comment, *args, **data):
        log.debug("Continuing from %r to thread %s.", self.thread, comment)
        comment, _, format = comment.partition('.')
        return resume(CommentController, comment, args, format, self.thread)
    
    def lock(self):
        if not self.forum.user_can_moderate(user):
            return dict(success=False, enabled=self.thread.flag.locked, message="Not allowed.")
        
        thread = self.thread
        thread.flag.locked = not thread.flag.locked
        thread.save()
        
        self.forum.channel.send('lock' if thread.flag.locked else 'unlock', str(thread.id))
        self.thread.channel.send('lock' if thread.flag.locked else 'unlock', str(thread.id))
        
        return 'json:', dict(success=True, enabled=thread.flag.locked)
    
    def sticky(self):
        if not self.forum.user_can_moderate(user):
            return dict(success=False, enabled=self.thread.flag.sticky, message="Not allowed.")
        
        thread = self.thread
        thread.flag.sticky = not thread.flag.sticky
        thread.save()
        
        self.forum.channel.send('sticky' if thread.flag.sticky else 'unsticky', str(thread.id))
        self.thread.channel.send('sticky' if thread.flag.sticky else 'unsticky', str(thread.id))
        
        return 'json:', dict(success=True, enabled=thread.flag.sticky)
    
    def hide(self):
        if not self.forum.user_can_moderate(user):
            return dict(success=False, enabled=self.thread.flag.hidden, message="Not allowed.")
        
        thread = self.thread
        thread.flag.hidden = not thread.flag.hidden
        thread.save()
        
        self.forum.channel.send('hidden' if thread.flag.hidden else 'visible', str(thread.id))
        self.thread.channel.send('hidden' if thread.flag.hidden else 'visible', str(thread.id))
        
        return 'json:', dict(success=True, enabled=thread.flag.hidden)
