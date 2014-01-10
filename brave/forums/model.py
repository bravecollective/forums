# encoding: utf-8

from __future__ import unicode_literals

from datetime import datetime

from web.core import config
from mongoengine import Document, EmbeddedDocument, StringField, DateTimeField, ReferenceField, IntField, EmbeddedDocumentField, ListField, BooleanField
from brave.core.api.client import API


log = __import__('logging').getLogger(__name__)


class Entity(EmbeddedDocument):
    meta = dict(allow_inheritance=False)
    
    id = IntField(db_field='i')
    name = StringField(db_field='n')


class Ticket(Document):
    meta = dict(
            collection = 'Tickets',
            allow_inheritance = False,
            indexes = [
                    'character.id'
                ],
        )
    
    token = StringField(db_field='t')
    
    character = EmbeddedDocumentField(Entity, db_field='c', default=lambda: Entity())
    corporation = EmbeddedDocumentField(Entity, db_field='o', default=lambda: Entity())
    alliance = EmbeddedDocumentField(Entity, db_field='a', default=lambda: Entity())
    tags = ListField(StringField(), db_field='t', default=list)
    
    expires = DateTimeField(db_field='e')
    seen = DateTimeField(db_field='s')
    
    @classmethod
    def authenticate(cls, identifier, password=None):
        """Validate the given identifier; password is ignored."""
        
        api = API(config['api.endpoint'], config['api.identity'], config['api.private'], config['api.public'])
        result = api.core.info(identifier)
        
        user = cls.objects(character__id=result.character.id).first()
        
        if not user:
            user = cls(token=identifier, expires=result.expires, seen=datetime.utcnow())
            user.character.id = result.character.id
            user.character.name = result.character.name
            user.corporation.id = result.corporation.id
            user.corporation.name = result.corporation.name
            
            if result.alliance:
                user.alliance.id = result.alliance.id
                user.alliance.name = result.alliance.name
            
            user.tags = result.tags if 'tags' in result else []
            
            user.save()
        
        else:
            # TODO: Also update the corporate details, if appropriate.
            user.update(set__token=identifier, set__seen=datetime.utcnow(), set__tags=result.get('tags', []))
        
        return user.id, user
    
    @classmethod
    def lookup(cls, identifier):
        """Thaw current user data based on session-stored user ID."""
        
        user = cls.objects(id=identifier).first()
        
        if user:
            user.update(set__seen=datetime.utcnow())
        
        return user


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
    
    # The tag needed to read (view) or wrie (post to) this forum.
    read = StringField(db_field='r')
    write = StringField(db_field='w')
    
    @property
    def threads(self):
        return Thread.objects(forum=self)


class Comment(EmbeddedDocument):
    meta = dict(allow_inheritance=False)
    
    message = StringField(db_field='m')
    
    creator = ReferenceField('Ticket')
    created = DateTimeField(db_field='dc', default=datetime.utcnow)
    modified = DateTimeField(db_field='dm')
    
    upload = None  # TODO: some day we'll allow file uploads


class ThreadFlags(EmbeddedDocument):
    meta = dict(allow_inheritance=False)
    
    locked = BooleanField(db_field='l', default=False)
    sticky = BooleanField(db_field='s', default=False)
    hidden = BooleanField(db_field='h', default=False)
    uploads = BooleanField(db_field='u', default=False)


class ThreadStats(EmbeddedDocument):
    meta = dict(allow_inheritance=False)
    
    comments = IntField(db_field='c', default=0)
    uploads = IntField(db_field='u', default=0)
    votes = IntField(db_field='v', default=0)
    views = IntField(db_field='i', default=0)


class Thread(Document):
    meta = dict(
            collection = 'Threads',
            allow_inheritance = False,
            indexes = [
                ],
            ordering = ['-id']
        )
    
    forum = ReferenceField(Forum, required=True)
    
    title = StringField(db_field='t')
    comments = ListField(EmbeddedDocumentField(Comment), db_field='c', default=list)
    
    flag = EmbeddedDocumentField(ThreadFlags, db_field='f', default=lambda: ThreadFlags())
    stat = EmbeddedDocumentField(ThreadStats, db_field='s', default=lambda: ThreadStats())

