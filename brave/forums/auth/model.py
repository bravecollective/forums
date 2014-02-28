# encoding: utf-8

from __future__ import unicode_literals

from datetime import datetime

from web.core import config
from mongoengine import Document, EmbeddedDocument, StringField, DateTimeField, IntField, EmbeddedDocumentField, ListField, MapField, queryset_manager
from brave.api.client import API


log = __import__('logging').getLogger(__name__)


def log_date_condition(message, *args):
    args = [arg.strftime("%Y/%m/%d-%H:%m:%S") if isinstance(arg, datetime) else arg for arg in args]
    log.debug(message, *args)


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
    
    # Map Forum IDs to mappings of Thread IDs to "last viewed" DateTimes.
    # Child mappings may contain a "read" key indicating the last time the forum was marked as read.
    read = MapField(MapField(DateTimeField()), db_field='r', default=dict)
    
    def __repr__(self):
        return "<Character {0.id} \"{0.character.name}\">".format(self)
    
    @queryset_manager
    def objects(doc_cls, queryset):
        return queryset.exclude('read')
    
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
        return Character.objects(id=self.id).update_one(**{
                'set__read__{0}__{1}'.format(thread.forum.id, thread.id): time or datetime.utcnow()
            })
    
    def mark_forum_read(self, forum, time=None):
        return Character.objects(id=self.id).update_one(**{
                'set__read__{0}'.format(forum.id): {'read': time or datetime.utcnow()}
            })
    
    def is_thread_read(self, thread):
        forum_id = unicode(thread.forum.id)
        thread_id = unicode(thread.id)
        
        # We don't, by default, pull the read information from the DB, so we'll need to fetch this.
        # Even better, we only really need two values out of the result.
        query = Character.objects(id=self.id, **{'read__' + forum_id + '__exists': True})
        query = query.only('read__' + forum_id + '__read', 'read__' + forum_id + '__' + thread_id)
        
        read = query.first()
        if not read:
            log.debug("thread %s unread notfound", thread_id)
            return False
        
        read = read.read[forum_id]
        forum_read = read.get('read', None)
        modified = thread.modified
        
        if forum_read and forum_read >= modified:
            log_date_condition("thread %s read forum %s >= %s", thread_id, forum_read, modified)
            return True
        else:
            log_date_condition("%s >= %s == False", forum_read, modified)
        
        if thread_id in read and read[thread_id] >= modified:
            log_date_condition("thread %s read %s >= %s", thread_id, read.get(thread_id, None), modified)
            return True
        else:
            log_date_condition("%s >= %s == False", read.get(thread_id, None), modified)
        
        log.debug("thread %s unread", thread_id)
        return False
    
    def is_forum_read(self, forum):
        # We special-case empty forums to prevent explosions.
        if not forum.threads:
            log.debug("forum %s read empty", forum.id)
            return True
        
        forum_id = unicode(forum.id)
        query = Character.objects(id=self.id, **{'read__' + forum_id + '__exists': True}).only('read__' + forum_id)
        
        read = query.first()
        
        if not read:
            log.debug("%s unread notfound", forum_id)
            return False
        
        read = read.read[forum_id]
        forum_read = read.get('read', None)
        newest_modified = forum.threads.scalar('modified').first()
        
        if forum_read and forum_read >= newest_modified:
            log_date_condition("forum %s read %s >= %s",
                forum_id, forum_read, newest_modified)
            return True
        
        # This is potentially HIDEOUSLY EXPENSIVE, so we restrict the fields being returned.
        for thread_id, modified in forum.threads.scalar('id', 'modified'):
            thread_id = unicode(thread_id)
            
            if forum_read and forum_read >= modified:
                log_date_condition("forum %s skip %s\n\t%s >= %s == True",
                    forum_id, thread_id, forum_read, modified)
                continue
            
            if thread_id not in read or read[thread_id] < modified:
                log_date_condition("forum %s unread %s\n\t%s < %s == True",
                    forum_id, thread_id, read.get(thread_id, None), modified)
                return False
            
            log_date_condition("forum %s reject %s read", forum_id, thread_id)
        
        log.info("forum %s cleanup %s", forum_id, modified.strftime("%Y/%m/%d-%H:%m:%S"))
        
        # All threads were read or examined; mark the forum read so we don't need to scan so many threads next time.
        self.mark_forum_read(forum, newest_modified)
        return True
