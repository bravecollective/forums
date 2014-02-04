# encoding: utf-8

from __future__ import unicode_literals

from mongoengine import Document, StringField, ListField, Q

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
        
        u = user._current_obj()
        query = Thread.objects(forum=self)
        
        if u and u.admin:
            return query
        
        return query.filter(flag__hidden=False)
    
    @classmethod
    def get(cls, *short):
        query = cls.objects(short__in=short) if short else cls.objects
        
        if not user._current_obj():
            return query.filter(read=None)
        
        if user.admin:
            return query
        
        tags = user.tags
        
        # Limit to forums the user has some form of access to.
        query.filter(
                Q(read=None) | Q(read__in=tags) | Q(write__in=tags) | Q(moderate__in=tags)
            )
        
        return query
