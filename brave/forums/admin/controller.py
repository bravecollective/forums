# encoding: utf-8

from __future__ import unicode_literals

from web.auth import user
from web.core import Controller, HTTPMethod, url, request
from web.core.http import HTTPNotFound

from marrow.schema.declarative import BaseAttribute

from brave.forums.admin.forums import Forums
from brave.forums.thread.model import Thread


log = __import__('logging').getLogger(__name__)


class AdministrationController(BaseAttribute, Controller):
    forum = Forums()
    
    def index(self):
        return 'brave.forums.admin.template.index', dict(
                latest = Thread.objects.order_by('-modified'),
                commented = Thread.objects(stat__comments__gt=0).order_by('-stat__comments'),
                visible = Thread.objects(stat__views__gt=1).order_by('-stat__views'),
                voted = Thread.objects(stat__votes__gt=0).order_by('-stat__votes'),
            )
