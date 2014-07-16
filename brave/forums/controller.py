# encoding: utf-8

from __future__ import unicode_literals

import sys
import bbcode

from web.auth import user, anonymous, authenticated
from web.core import Controller, session

from brave.forums.auth.controller import AuthenticationMixIn
from brave.forums.component.category.controller import CategoryController
from brave.forums.component.category.model import Category
from brave.forums.component.forum.controller import ForumController
from brave.forums.component.forum.model import Forum
from brave.forums.component.thread.model import Thread

from brave.forums.util import StartupMixIn, resume, only, require, debugging
from brave.forums.util.live import Channel
from brave.forums.util.tags import SemanticTagParser

log = __import__('logging').getLogger(__name__)


class RootController(Controller, StartupMixIn, AuthenticationMixIn):
    def __lookup__(self, first, *args, **kw):
        """Internal redirect if the first path element doesn't match a method at this level.
        
        Path elements are passed positionally, GET/POST as keyword arguments.
        Must return a new controller instance and the remaining path elements to process.
        Yes, these remaining path elements don't need to be the ones that came in originally!
        """
        if first == "category":
            return resume(CategoryController, args[0] if args else None, args[1:])
        else:
            return resume(ForumController, first, args)
    
    @require(anonymous)
    def index(self):
        """Anonymous welcome splash page."""
        return 'brave.forums.template.welcome', dict()
    
    @index.otherwise
    def index(self):
        """Authenticated forum dashboard."""
        
        allowed = list(Forum.get().scalar('id'))
        
        return 'brave.forums.template.index', dict(
                categories = Category.objects.only('id', 'title', 'members'),
                announcements = Forum.get('ann').first(),
                activity = Thread.objects.get_active(allowed, user.id, 30),
                latest = Thread.objects.get_active(allowed).order_by('-id'),
                voted = Thread.objects.get_active(allowed, days=7, stat__votes__gt=0).order_by('-stat__votes')
            )
    
    def listen(self, id):
        """Default push notification handler if not running under Nginx."""
        return 'json:', dict(handler="stop", payload=None)
    
    @require(authenticated)
    def preview(self, content):
        """Handle BBCode preview functionality."""
        
        # If no content has been submitted to preview, show an alert box instead
        if content.strip() == '':
            return only('brave.forums.template.thread', 'no_preview')
        else:
            parser = SemanticTagParser();
            return parser.format(content)
    
    @require(authenticated)
    def theme(self, theme):
        """Change the theme registered against the current user."""
        
        u = user._current_obj()
        
        u.theme = theme if theme != 'default' else None
        u.save()
        
        return 'json:', dict(success=True)

    @require(authenticated)
    def readall(self):
        for forum in Forum.objects:
            user.mark_forum_read(forum)
        return "json:", dict(success=True)
    
    @require(debugging)
    def die(self):
        """Simply explode.  Useful to get the interactive debugger up."""
        1/0
