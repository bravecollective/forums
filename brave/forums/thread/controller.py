# encoding: utf-8

from __future__ import unicode_literals

import bbcode

from web.auth import user
from web.core import Controller, HTTPMethod, url, request
from web.core.http import HTTPNotFound
from bson import ObjectId
from datetime import datetime

from brave.forums.live import Channel
from brave.forums.auth.model import Ticket
from brave.forums.thread.model import Thread, Comment


log = __import__('logging').getLogger(__name__)


class CommentIndex(HTTPMethod):
    def __init__(self, thread, comment):
        self.thread = thread
        self.comment = comment
        super(CommentIndex, self).__init__()
    
    def get(self):
        # We fall back to raw pymongo in order to be as efficient as possible.
        
        try:
            comment = Thread._get_collection().find({'c': {'$elemMatch': {'i': self.comment}}}, {'c.$': 1}).next()
        except StopIteration:
            raise HTTPNotFound()
        
        try:
            comment = comment['c'][0]
        except:
            raise HTTPNotFound()

        return 'json:', dict(
                success = True,
                character = Ticket.objects(id=comment['creator']).only('character__id').first().character.id,
                comment = comment['m']
            )
    
    def post(self, message):
        """Update the comment."""
        
        return 'json:', dict(
                success = True
            )
    
    def delete(self):
        """Delete the comment."""
        
        # TODO: Security!  Woo!  (Check admin or owner.)
        
        if self.thread.comments[0].id == self.comment:
            short = self.thread.forum.short
            self.thread.delete()
            return 'json:', dict(
                    success = True,
                    location = url('/' + short)
                )
        
        Thread.objects(comments__id=self.comment).update_one(inc__stat__comments=-1, pull__comments__id=self.comment)
        
        return 'json:', dict(
                success = True
            )


class CommentController(Controller):
    def __init__(self, thread, comment):
        self.thread = thread
        self.comment = comment
        self.index = CommentIndex(thread, comment)
        super(CommentController, self).__init__()
    
    def vote(self):
        try:
            comment = Thread._get_collection().find({'c': {'$elemMatch': {'i': self.comment}}}, {'c.$': 1}).next()
        except StopIteration:
            raise HTTPNotFound()
        
        try:
            comment = comment['c'][0]
        except:
            raise HTTPNotFound()
        
        if user.id in comment.get('vt', []):
            Thread.objects(comments__id=self.comment).update_one(inc__comments__S__vote_count=-1, pull__comments__S__vote_trail=user.id)
            enabled = False
            
        else:
            Thread.objects(comments__id=self.comment).update_one(inc__comments__S__vote_count=1, push__comments__S__vote_trail=user.id)
            enabled = True
        
        return 'json:', dict(
                success = True,
                enabled = enabled
            )
    


class ThreadIndex(HTTPMethod):
    def __init__(self, forum, thread):
        self.forum = forum
        self.thread = thread
        super(ThreadIndex, self).__init__()
    
    def get(self, page=1):
        thread = self.thread.thread
        Thread.objects(id=thread.id).update_one(inc__stat__views=1)
        return 'brave.forums.template.thread', dict(page=page, forum=self.forum, thread=thread, endpoint=self.thread.channel.receiver)
    
    def post(self, message, upload=None, vote=None):
        if self.forum.moderate in user.tags:
            pass
        elif not user.admin and self.forum.write and self.forum.write not in user.tags:
            return 'json:', dict(success=False, message="Not allowed.")
        
        if not message or not message.strip():
            return 'json:', dict(success=False, message="Empty message.")
        
        comment_id = ObjectId()
        
        thread = self.thread.thread
        
        # Atomic operations, bitches!
        Thread.objects(id=thread.id).update_one(
                inc__stat__comments = 1,
                set__modified = datetime.utcnow(),
                push__comments = Comment(
                        id = comment_id,
                        message = message,
                        creator = user._current_obj(),
                    )
            )
        
        thread.reload()
        
        payload = dict(
                identifier = str(comment_id),
                character = dict(id=unicode(user.id), nid=user.character.id, name=user.character.name),
                when = dict(
                        iso = comment_id.generation_time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                        pretty = comment_id.generation_time.strftime('%B %e, %G at %H:%M:%S')
                    ),
                message = bbcode.render_html(message)
            )
        
        self.thread.channel.send('comment', payload)
        
        return 'json:', dict(success=True)



class ThreadController(Controller):
    def __init__(self, forum, id):
        self.forum = forum
        self.thread = Thread.objects.get(id=id)
        self.channel = Channel(self.forum.id, self.thread.id)
        self.index = ThreadIndex(forum, self)
        super(ThreadController, self).__init__()
    
    @classmethod
    def _create(cls, forum, title, message):
        if self.forum.moderate in user.tags:
            pass
        elif self.forum.write and self.forum.write not in user.tags:
            return dict(success=False, message="Not allowed.")
        
        thread = Thread(forum=forum, title=title, comments=[
                Comment(
                    id = ObjectId(),
                    message = message,
                    creator = user._current_obj(),
                )
            ])
        thread.save()
        
        return dict(success=True)
    
    def lock(self):
        if not (user.admin or self.forum.moderate in user.tags):
            return dict(success=False, enabled=self.thread.flag.locked, message="Not allowed.")
        
        thread = self.thread
        thread.flag.locked = not thread.flag.locked
        thread.save()
        
        return 'json:', dict(success=True, enabled=thread.flag.locked)
    
    def sticky(self):
        if not (user.admin or self.forum.moderate in user.tags):
            return dict(success=False, enabled=self.thread.flag.sticky, message="Not allowed.")
        
        thread = self.thread
        thread.flag.sticky = not thread.flag.sticky
        thread.save()
        
        return 'json:', dict(success=True, enabled=thread.flag.sticky)
    
    def hide(self):
        if not (user.admin or self.forum.moderate in user.tags):
            return dict(success=False, enabled=self.thread.flag.hidden, message="Not allowed.")
        
        thread = self.thread
        thread.flag.hidden = not thread.flag.hidden
        thread.save()
        
        return 'json:', dict(success=True, enabled=thread.flag.hidden)
    
    def __lookup__(self, comment, *args, **data):
        try:
            comment = ObjectId(comment)
        except:
            raise HTTPNotFound()
        
        return CommentController(self.thread, comment), args
