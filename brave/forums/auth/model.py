# encoding: utf-8

from __future__ import unicode_literals

from datetime import datetime

from web.core import config
from mongoengine import Document, EmbeddedDocument, StringField, DateTimeField, IntField, EmbeddedDocumentField, ListField, MapField
from brave.api.client import API


log = __import__('logging').getLogger(__name__)


class Entity(EmbeddedDocument):
    meta = dict(allow_inheritance=False)
    
    id = IntField(db_field='i')
    name = StringField(db_field='n')


class Character(Document):
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
    tags = ListField(StringField(), db_field='g', default=list)
    
    theme = StringField(db_field='h')
    
    expires = DateTimeField(db_field='e')
    seen = DateTimeField(db_field='s')
    
    # { forum1: {
    #       'read': forum1_read_ts,
    #   },
    #   forum2: {
    #       'read': forum2_read_ts,
    #       thread2: thread2_read_ts,
    #   }
    # }
    read = MapField(MapField(DateTimeField()), db_field='r', default=dict)

    def __repr__(self):
        return "<Ticket {0.id} \"{0.character.name}\">".format(self)
    
    @property
    def admin(self):
        return 'admin' in self.tags or 'forum.admin' in self.tags
    
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

    def mark_thread_read(self, thread, time=None):
        if time is None:
            time = datetime.utcnow()
        update_op = 'set__read__'+str(thread.forum.id)+'__'+str(thread.id)
        Character.objects(id=self.id).update_one(**{update_op: datetime.utcnow()})

    def mark_forum_read(self, forum, time=None):
        if time is None:
            time = datetime.utcnow()
        update_op = 'set__read__'+str(forum.id)
        Character.objects(id=self.id).update_one(**{update_op: {'read': datetime.utcnow()}})

    def is_thread_read(self, thread):
        if str(thread.forum.id) not in self.read:
            return False
        d = self.read[str(thread.forum.id)]
        return ('read' in d and d['read'] > thread.modified or
                str(thread.id) in d and d[str(thread.id)] > thread.modified)

    def is_forum_read(self, forum):
        if not forum.threads:
            return True
        if str(forum.id) not in self.read:
            return False
        d = self.read[str(forum.id)]

        last_modified = forum.threads[0].modified
        for thread in forum.threads:
            modified = thread.modified
            last_modified = max(last_modified, modified)
            if 'read' in d and d['read'] >= modified:
                # all unchecked threads were modified earlier than this one
                break
            if str(thread.id) not in d or d[str(thread.id)] < modified:
                return False

        # All threads were read; mark the whole forum read so we don't need to
        # scan so many threads next time.
        self.mark_forum_read(forum, last_modified)
        return True
