# encoding: utf-8

from __future__ import unicode_literals

from web.auth import user
from web.core import Controller, HTTPMethod, url, request
from web.core.http import HTTPNotFound
from bson import ObjectId
from datetime import datetime

from brave.forums.auth.model import Character
from brave.forums.component.thread.model import Thread
from brave.forums.component.comment.model import Comment
from brave.forums.util.live import Channel
from brave.forums.util import resume, only


log = __import__('logging').getLogger(__name__)


class CommentIndex(HTTPMethod):
    def __init__(self, thread, comment, format=None):
        self.thread = thread
        self.comment = comment
        self.format = format or 'json'
        super(CommentIndex, self).__init__()
    
    def get(self):
        if user:
            user.mark_thread_read(self.thread, self.comment.modified)
        
        if self.format == 'html':
            return only('brave.forums.template.thread', 'render_push',
                    page = 1,
                    forum = self.thread.forum,
                    thread = self.thread,
                    comment = self.comment,
                    post_title = self.thread.title if self.comment == self.thread.oldest() else None,
                    BASE = "/{0}/{1}".format(self.thread.forum.short, self.thread.id)
                )
        
        return 'json:', dict(
                success = True,
                character = self.comment.creator.character.id,
                comment = self.comment.message
            )
    
    def post(self, message, title=None):
        """Update the comment."""
        
        if not self.thread.user_can_edit_comment(user, self.comment):
            return 'json:', dict(success = False, message = "Not allowed.")
        
        if title:
            if self.comment.id != self.thread.oldest().id:
                return 'json:', dict(success = False, message = "Setting title on invalid comment")
            assert self.thread.update_title(title), "Couldn't update thread title?!"
        
        enabled = True
        success = self.thread.update_comment(self.comment.id, set__message = message,
                 set__modified = datetime.utcnow()
             )
        log.info("'{0}' edited comment {1} from '{2}' to '{3}'".format(user.character.name, self.comment.id, self.comment.message, message))
        if not success:
            return 'json:', dict(success = False, message = "Comment not found.")
        
        self.thread.channel.send('refresh', str(self.comment.id))
        return 'json:', dict(success=True, comment=str(self.comment.id))
    
    def delete(self):
        """Delete the comment."""
        
        forum = self.thread.forum
        
        if not self.thread.user_can_edit_comment(user, self.comment):
            return 'json:', dict(success = False, message = "Not allowed.")
        
        if self.comment.id == self.thread.oldest().id:
            forum.channel.send('gone', str(self.thread.id))
            self.thread.channel.send('gone', url('/' + forum.short))
            log.info("'{0}' deleted thread {1}/{2}".format(user.character.name, forum.short, self.thread.id))
            self.thread.delete()
            
            return 'json:', dict(success=True)
        
        self.thread.update_comment(self.comment.id, dict(dec__stat__comments=1, pull__comments__id=self.comment.id))
        log.info("'{0}' deleted comment '{1} (2)' by '{3}'  in {4}/{5}".format(user.character.name, self.comment.message, self.comment.id, self.comment.creator.character.name, forum.short, self.thread.id))
        self.thread.channel.send('remove', str(self.comment.id))
        
        return 'json:', dict(success=True)


class CommentController(Controller):
    def __init__(self, comment, format, thread):
        try:
            comment = ObjectId(comment)
        except:
            raise HTTPNotFound()
        
        self.thread = thread
        comment = self.comment = thread.get_comment(comment)
        if not self.comment:
            raise HTTPNotFound()
        
        self.index = CommentIndex(thread, comment, format)
        super(CommentController, self).__init__()
    
    def vote(self):
        if user.id in self.comment.vote_trail:
            enabled = False
            success = self.thread.update_comment(
                    self.comment.id,
                    dict(dec__stat__votes=1),
                    dec__vote_count = 1,
                    pull__vote_trail = user.id
                )
        
        else:
            enabled = True
            success = self.thread.update_comment(
                    self.comment.id,
                    dict(inc__stat__votes=1),
                    inc__vote_count = 1,
                    push__vote_trail = user.id
                )
        
        self.thread.channel.send('refresh', self.comment.id)
        
        return 'json:', dict(
                success = bool(success),
                enabled = enabled if success else not enabled
            )
