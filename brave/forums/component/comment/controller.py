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
    def __init__(self, thread, comment, format=None):
        self.thread = thread
        self.comment = comment
        self.channel = Channel(thread.forum.id, thread.id)
        self.format = format or 'json'
        super(CommentIndex, self).__init__()
    
    def get(self):
        if self.format == 'html':
            # This is hideously bad, but MongoEngine has yet to support .only('comments__S')
            for comment in self.thread.comments:
                if comment.id == self.comment: break
            else:
                raise HTTPNotFound()
    
            return 'brave.forums.template.thread', dict(
                    page = 1,
                    forum = self.thread.forum,
                    thread = self.thread,
                    endpoint = '',
                    comment = comment
                ), dict(only='render_push')
        
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
        
        self.channel.send('replace', str(self.comment))
        
        return 'json:', dict(
                success = True
            )
    
    def delete(self):
        """Delete the comment."""
        
        forum = self.thread.forum
        
        if 'admin' not in user.tags or (forum.moderate and forum.moderate not in user.tags)
        
        
        if self.thread.comments[0].id == self.comment:
            short = self.thread.forum.short
            self.thread.delete()
            self.channel.send('gone', str(thread.id))
            return 'json:', dict(
                    success = True,
                    location = url('/' + short)
                )
        
        Thread.objects(comments__id=self.comment).update_one(inc__stat__comments=-1, pull__comments__id=self.comment)
        self.channel.send('replace', str(thread.id))
        
        return 'json:', dict(
                success = True
            )


class CommentController(Controller):
    def __init__(self, thread, comment, format):
        self.thread = thread
        self.comment = comment
        self.index = CommentIndex(thread, comment, format)
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
            Thread.objects(comments__id=self.comment).update_one(inc__comments__S__vote_count=-1, pull__comments__S__vote_trail=user.id, inc__stat__votes=-1)
            enabled = False
            
        else:
            Thread.objects(comments__id=self.comment).update_one(inc__comments__S__vote_count=1, push__comments__S__vote_trail=user.id, inc__stat__votes=1)
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
        
        comment = Comment(
                id = comment_id,
                message = message,
                creator = user._current_obj(),
            )
        
        # Atomic operations, bitches!
        Thread.objects(id=thread.id).update_one(
                inc__stat__comments = 1,
                set__modified = datetime.utcnow(),
                push__comments = comment
            )
        
        thread.reload()
        
        self.thread.channel.send('comment', str(comment_id))
        
        return 'json:', dict(success=True)



class ThreadController(Controller):
    def __init__(self, forum, id):
        self.forum = forum
        try:
            self.thread = Thread.objects.get(id=id)
        except Thread.DoesNotExist:
            raise HTTPNotFound()
        self.channel = Channel(self.forum.id, self.thread.id)
        self.index = ThreadIndex(forum, self)
        super(ThreadController, self).__init__()
    
    @classmethod
    def _create(cls, forum, title, message):
        if forum.moderate in user.tags:
            pass
        elif not user.admin and forum.write and forum.write not in user.tags:
            return dict(success=False, message="Not allowed.")
        
        thread = Thread(forum=forum, title=title, comments=[
                Comment(
                    id = ObjectId(),
                    message = message,
                    creator = user._current_obj(),
                )
            ])
        thread.save()
        
        chan = Channel(self.forum.id)
        chan.send('thread', str(thread.id))
        
        return dict(success=True)
    
    def lock(self):
        if not (user.admin or self.forum.moderate in user.tags):
            return dict(success=False, enabled=self.thread.flag.locked, message="Not allowed.")
        
        thread = self.thread
        thread.flag.locked = not thread.flag.locked
        thread.save()
        
        self.channel.send('lock' if thread.flag.locked else 'unlock', str(thread.id))
        
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
        comment, _, format = comment.partition('.')
        request.path_info_pop()  # We consume a single path element.
        
        try:
            comment = ObjectId(comment)
        except:
            raise HTTPNotFound()
        
        return CommentController(self.thread, comment, format), args
