# encoding: utf-8

from __future__ import unicode_literals

from mongoengine import EmbeddedDocument, IntField


class Statistics(EmbeddedDocument):
    meta = dict(allow_inheritance=False)
    
    comments = IntField(db_field='c', default=0)
    uploads = IntField(db_field='u', default=0)
    votes = IntField(db_field='v', default=0)
    views = IntField(db_field='i', default=0)
