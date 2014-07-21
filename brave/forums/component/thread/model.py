# encoding: utf-8

from __future__ import unicode_literals

from datetime import datetime, timedelta

from bson import ObjectId
from mongoengine.queryset import queryset_manager
from mongoengine.queryset.field_list import QueryFieldList
from mongoengine import QuerySet, Document, EmbeddedDocument, ObjectIdField, StringField, DateTimeField, ReferenceField, EmbeddedDocumentField, ListField, BooleanField

from brave.forums.model import Statistics
from brave.forums.component.comment.model import Comment
from brave.forums.util.live import Channel


log = __import__('logging').getLogger(__name__)


class ThreadQuerySet(QuerySet):
    def __init__(self, *args, **kw):
        super(ThreadQuerySet, self).__init__(*args, **kw)
        
        # Exclude certain fields.  Must use in-db name here.
        self._loaded_fields += QueryFieldList(['c', 'b'], value=QueryFieldList.EXCLUDE, _only_called=False)
    
    def get_active(self, forum=None, user=None, days=None, **kw):
        """Return filtered postings.
        
        Implements the most common filtering operations used across Thread objects.
        """
        
        query = self.order_by('-modified')
        
        if forum: query = query(forum__in=forum if isinstance(forum, (list, tuple)) else [forum])
        if user: query = query(comments__creator=user)
        if days: query = query(modified__gt=datetime.utcnow() - timedelta(days=days))
        if kw: query = query(**kw)
        
        return query


class ThreadFlags(EmbeddedDocument):
    meta = dict(allow_inheritance=False)
    
    locked = BooleanField(db_field='l', default=False)
    sticky = BooleanField(db_field='s', default=False)
    hidden = BooleanField(db_field='h', default=False)
    uploads = BooleanField(db_field='u', default=False)
    
    def __repr__(self):
        return 'ThreadFlags({0})'.format([
                flag for flag in ('locked', 'sticky', 'hidden', 'uploads') if getattr(self, flag)
            ])


class Thread(Document):
    meta = dict(
            collection = 'Threads',
            allow_inheritance = False,
            queryset_class = ThreadQuerySet,
            indexes = [
                    'modified',
                    ('forum', 'flag.hidden'),
                ],
            ordering = ['-modified']
        )
    
    forum = ReferenceField('Forum', required=True)
    
    title = StringField(db_field='t')
    comments = ListField(EmbeddedDocumentField(Comment), db_field='c', default=list)
    
    flag = EmbeddedDocumentField(ThreadFlags, db_field='f', default=lambda: ThreadFlags())
    stat = EmbeddedDocumentField(Statistics, db_field='s', default=lambda: Statistics())
    subs = ListField(ObjectIdField(), db_field='b', default=list)
    
    created = property(lambda self: self.id.generation_time)
    modified = DateTimeField(db_field='m', default=datetime.utcnow)
    
    def __repr__(self):
        return 'Thread({0.id} in {0.forum.id}, "{0.title}")'.format(self)
    
    @property
    def channel(self):
        if not hasattr(self, '_channel'):
            self._channel = Channel(self.forum.id, self.id)
        
        return self._channel
    
    def add_comment(self, user, message):
        comment = Comment(
                id = ObjectId(),
                message = message,
                creator = user,
            )
        
        Thread.objects(id=self.id).update_one(
                inc__stat__comments = 1,
                set__modified = datetime.utcnow(),
                push__comments = comment
            )
        
        log.info("{0.character.name} added comment '{1}' to {2.forum.short}/{2.id}".format(user, message, self))

        self.channel.send('comment', str(comment.id))
        
        return comment
    
    def get_comment(self, id):
        """Return a specific Comment instance."""
        
        try:
            data = Thread._get_collection().find(
                    {'c': {'$elemMatch': {'i': id}}},
                    {'c.$': 1}
                ).next()
        
        except StopIteration:
            return None
        
        # Return a proper Comment instance.  We like to live in MongoEngine-land.
        return Comment._from_son(data['c'][0])
    
    def update_comment(self, id, raw=None, **kw):
        """Perform an update operation across a specific comment."""
        
        ops = ('set', 'unset', 'inc', 'dec', 'push', 'push_all', 'pop', 'pull', 'pull_all', 'add_to_set')
        
        update = dict()
        
        # Inject the appropriate dereference to the matched comment.
        for key, value in kw.iteritems():
            parts = key.split('__')
            parts.insert(1 if parts[0] in ops else 0, 'comments__$')
            update['__'.join(parts)] = value
        
        if raw:
            update.update(raw)
        
        return Thread.objects(comments__id=id).update_one(**update)
    
    def update_title(self, title):
        return Thread.objects(id=self.id).update_one(set__title=title)
    
    def oldest(self, cache=True):
        """Return the first (oldest) comment in this thread.
        
        This always refers to the comment that started the thread; the original post.
        
        To force re-querying in the event of a cached result, pass False as the first argument.
        """
        
        if not hasattr(self, '_oldest') or not cache:
            rec = Thread.objects(id=self.id).all_fields().only('comments').fields(slice__comments=[0, 1]).first()
            if not rec: return None  # we don't cache empty sets to force re-get
            self._oldest = rec.comments[0]
        
        return self._oldest
    
    def latest(self, cache=True):
        """Return the latest (most recent) comment in this thread.
        
        To force re-querying in the event of a cached result, pass False as the first argument.
        """
        
        if not hasattr(self, '_latest') or not cache:
            rec = Thread.objects(id=self.id).all_fields().only('comments').fields(slice__comments=-1).first()
            if not rec: return None  # we don't cache empty sets to force re-get
            self._latest = rec.comments[0]
        
        return self._latest

    def user_can_edit_comment(self, u, c):
        return self.forum.user_can_moderate(u) or (u and u._current_obj() == c.creator)
