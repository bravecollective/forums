# encoding: utf-8

from __future__ import unicode_literals

from datetime import datetime

from mongoengine import EmbeddedDocument, ObjectIdField, StringField, DateTimeField, ReferenceField, IntField, EmbeddedDocumentField, ListField, BooleanField


log = __import__('logging').getLogger(__name__)


# TODO: migration to delete the 'dc' key from all comments


class Voting(EmbeddedDocument):
    meta = dict(allow_inheritance=False)
    
    count = IntField(db_field='c', default=0)
    who = ListField(ObjectIdField(), db_field='w', default=[])
    
    def __repr__(self):
        return 'Voting({0})'.format(self.count)


class Comment(EmbeddedDocument):
    meta = dict(allow_inheritance=False)
    
    id = ObjectIdField(db_field='i')
    message = StringField(db_field='m')
    
    # TODO: migrate existing vote information into Voting instances
    vote = EmbeddedDocumentField(Voting, default=Voting)
    vote_count = IntField(db_field='vc', default=0)
    vote_trail = ListField(ObjectIdField(), db_field='vt', default=[])
    
    creator = ReferenceField('Character')
    
    created = property(lambda self: self.id.generation_time)
    modified = DateTimeField(db_field='dm')
    
    upload = None  # TODO: some day we'll allow file uploads
    
    def __repr__(self):
        return 'Comment({0.id} "{0.creator.character.name}")'.format(self)
