# encoding: utf-8

from __future__ import unicode_literals

import bbcode

from web.core import request
from web.auth import authenticated, user
from web.core import Controller, url

from brave.forums.util import StartupMixIn
from brave.forums.live import Channel
from brave.forums.forum.model import Forum
from brave.forums.auth.controller import AuthenticationMixIn
from brave.forums.forum.controller import ForumController


log = __import__('logging').getLogger(__name__)



class RootController(Controller, StartupMixIn, AuthenticationMixIn):
    def die(self):
        """Simply explode.  Useful to get the interactive debugger up."""
        1/0
    
    def index(self):
        if authenticated:
            forum_categories = [
                    ("Management", Forum.get(('council', 'it'))),
                    ("General Discussions", Forum.get(('p', 'a', 'c'))),
                    ("EVE Discussions", Forum.get(('pvp', 'pve', 'm', 'i', 'd'))),
                    ("BRAVE Dojo", Forum.get(('dg', 'ds'))),
                    ("Other", Forum.get(('b', 'n', 'g', 'z'))),
                ]
            
            return 'brave.forums.template.index', dict(
                    announcements = Forum.get('ann'),
                    forum_categories = forum_categories
                )

        return 'brave.forums.template.welcome', dict()
    
    def listen(self, id):
        return 'json:', dict(handler="stop", payload=None)
    
    def preview(self, content):
        # If no content has been submitted to preview, show an alert box instead
        if content.strip() == '':
            return 'brave.forums.template.thread', dict(), dict(only="no_preview"),
        else:
            return bbcode.render_html(content)
    
    def __lookup__(self, forum, *args, **kw):
        request.path_info_pop()
        return ForumController(forum), args
