# encoding: utf-8

from __future__ import unicode_literals

import sys
import bbcode

from datetime import datetime, timedelta
from traceback import extract_tb, extract_stack, format_list
from web.auth import authenticated, user
from web.core import Controller, url, request, session

from brave.forums.util import StartupMixIn
from brave.forums.live import Channel
from brave.forums.forum.model import Forum
from brave.forums.thread.model import Thread
from brave.forums.auth.controller import AuthenticationMixIn
from brave.forums.forum.controller import ForumController
from brave.forums.admin.controller import AdministrationController


log = __import__('logging').getLogger(__name__)


class RootController(Controller, StartupMixIn, AuthenticationMixIn):
    admin = AdministrationController()
    
    def die(self):
        """Simply explode.  Useful to get the interactive debugger up."""
        1/0
    
    def index(self):
        if authenticated:
            forum_categories = [
                    ("Management", Forum.get('council', 'it')),
                    ("General Discussions", Forum.get('p', 'a', 'c')),
                    ("EVE Discussions", Forum.get('pvp', 'pve', 'm', 'i', 'd')),
                    ("BRAVE Dojo", Forum.get('dg', 'ds')),
                    ("Other", Forum.get('b', 'n', 'g', 'z')),
                ]
            
            allowed = Forum.get().scalar('id')
            announcements = Forum.get('ann').first()
            
            return 'brave.forums.template.index', dict(
                    forum_categories = forum_categories,
                    
                    announcements = announcements.threads if announcements else None,
                    
                    activity = Thread.objects(
                            forum__in = allowed,
                            modified__gt = datetime.utcnow() - timedelta(days=30),
                            comments__creator = user._current_obj()
                        ).order_by('-modified'),
                    
                    latest = Thread.objects(forum__in=allowed).order_by('-id'),
                    
                    voted = Thread.objects(
                            forum__in = allowed,
                            modified__gt = datetime.utcnow() - timedelta(days=7),
                            stat__votes__gt = 0
                        ).order_by('-stat__votes'),
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
    
    def theme(self, theme):
        u = user._current_obj()
        
        if not u:
            session['theme'] = theme if theme != 'default' else None
            session.save()
            return 'json:', dict(success=True)
        
        u.theme = theme if theme != 'default' else None
        u.save()
        
        return 'json:', dict(success=True)
    
    def __lookup__(self, forum, *args, **kw):
        request.path_info_pop()
        return ForumController(forum), args





    def trace(self):
        exception = None
        trace = None
        
        try:
            1/0
        except Exception as e:
            exception = e
            trace = extract_stack()
        
        data = dict(
                foo = "Bar",
                baz = "Diz",
                daz = dict(
                        sub = 2,
                        mul = 4,
                        div = 8,
                    ),
                forums = Forum.objects.all()
            )
        
        return 'brave.forums.template.traceback', dict(
                request = request,
                exception = e,
                traceback = trace,
                traceback2 = format_list(trace),
                data = data
            )