# encoding: utf-8

from __future__ import unicode_literals

from mongoengine import Document, StringField, ListField

from web.auth import user


log = __import__('logging').getLogger(__name__)


class Forum(Document):
    meta = dict(
            collection = 'Forums',
            allow_inheritance = False,
            indexes = [
                ],
        )
    
    short = StringField(db_field='s')
    name = StringField(db_field='n')
    summary = StringField(db_field='u')
    
    # The tag needed to read (view) or write (post to) this forum.
    read = StringField(db_field='r')
    write = StringField(db_field='w')
    moderate = StringField(db_field='m')
    
    @property
    def threads(self):
        from brave.forums.thread.model import Thread
        
        query = Thread.objects(forum=self)
        
        if 'forum.admin' not in user.tags:
            query = query.filter(flag__hidden=False)
        
        return query
    
    @classmethod
    def get(cls, short):
        return cls.objects(short__in=short) if isinstance(short, (list, tuple)) else cls.obects.get(short=short)
