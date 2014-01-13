# encoding: utf-8

from __future__ import unicode_literals

from datetime import datetime

from mongoengine import Document, EmbeddedDocument, ObjectIdField, StringField, DateTimeField, ReferenceField, IntField, EmbeddedDocumentField, ListField, BooleanField


log = __import__('logging').getLogger(__name__)


class Comment(EmbeddedDocument):
    meta = dict(allow_inheritance=False)
    
    id = ObjectIdField(db_field='i')
    message = StringField(db_field='m')
    
    vote_count = IntField(db_field='vc', default=0)
    vote_trail = ListField(ObjectIdField(), db_field='vt', default=[])
    
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
                    'modified', ('forum', 'flag.hidden'),
                ],
            ordering = ['-modified']
        )
    
    forum = ReferenceField('Forum', required=True)
    
    title = StringField(db_field='t')
    comments = ListField(EmbeddedDocumentField(Comment), db_field='c', default=list)
    
    flag = EmbeddedDocumentField(ThreadFlags, db_field='f', default=lambda: ThreadFlags())
    stat = EmbeddedDocumentField(ThreadStats, db_field='s', default=lambda: ThreadStats())
    
    modified = DateTimeField(db_field='m', default=datetime.utcnow)
