# encoding: utf-8

from __future__ import unicode_literals

from operator import __or__
from web.auth import user
from mongoengine import Q, Document, StringField, EmbeddedDocumentField, DateTimeField

from brave.forums.model import Statistics
from brave.forums.util.live import Channel
from brave.forums.component.thread.model import Thread


log = __import__('logging').getLogger(__name__)


class Forum(Document):
    meta = dict(
            collection = 'Forums',
            allow_inheritance = False,
            indexes = [
                ],
        )
    
    short = StringField(db_field='s')  # , primary_key=True) TODO: Migrate this into _id.
    name = StringField(db_field='n')
    summary = StringField(db_field='u')
    
    # The tag needed to read (view) or write (post to) this forum.
    read = StringField(db_field='r')
    write = StringField(db_field='w')
    moderate = StringField(db_field='m')
    
    stat = EmbeddedDocumentField(Statistics, db_field='t', default=Statistics)
    modified = DateTimeField(db_field='o')
    
    def __repr__(self):
        return 'Forum({0.short} "{0.name}" r={0.read} w={0.write} m={0.moderate})'.format(self)
    
    @property
    def channel(self):
        if not hasattr(self, '_channel'):
            self._channel = Channel(self.id)
        
        return self._channel
    
    @property
    def threads(self):
        u = user._current_obj()
        query = Thread.objects(forum=self)
        
        if u and u.admin:
            return query
        
        return query.filter(flag__hidden=False)
    
    @classmethod
    def get(cls, *short):
        query = cls.objects(short__in=short) if short else cls.objects
        
        u = user._current_obj()
        if u and u.admin: return query
        
        components = [Q(read=None)]
        if not u or not u.tags: return query.filter(*components)
        
        components.append(Q(read__in=u.tags))
        components.append(Q(write__in=u.tags))
        components.append(Q(moderate__in=u.tags))
        
        # Limit to forums the user has some form of access to.
        return query.filter(reduce(__or__, components))
    
    def create_thread(self, user, title, message):
        thread = Thread(forum=self, title=title).save()
        thread.add_comment(user, message)
        
        self.channel.send('thread', str(thread.id))
        
        return thread

    def user_can_admin(self, u):
        return u and u.admin

    def user_can_moderate(self, u):
        return self.user_can_admin(u) or (u and self.moderate in u.tags)

    def user_can_write(self, u):
        return self.user_can_moderate(u) or (u and (not self.write or self.write in u.tags))

    def user_can_read(self, u):
        return self.user_can_write(u) or not self.read or (u and self.read in u.tags)
