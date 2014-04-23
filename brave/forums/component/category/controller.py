# encoding: utf-8

from __future__ import unicode_literals

from web.auth import user, authenticated
from web.core import Controller
from web.core.http import HTTPNotFound

from brave.forums.component.category.model import Category
from brave.forums.util import require


log = __import__('logging').getLogger(__name__)

class CategoryController(Controller):
    def __init__(self, id):
        try:
            self.category = Category.objects.get(id=id)
        except Category.DoesNotExist:
            raise HTTPNotFound()

    @require(authenticated)
    def read(self):
        for forum in self.category.forums():
            user.mark_forum_read(forum)
        return "json:", dict(success=True)
