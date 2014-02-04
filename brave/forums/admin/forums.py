# encoding: utf-8

from __future__ import unicode_literals

from web.auth import user, Predicate
from web.core import Controller, HTTPMethod, url, request
from web.core.http import HTTPNotFound

from brave.forums.generic.controller import Generic, BaseAttribute, Action
from brave.forums.generic.column import Column, PrimaryColumn, DateColumn

from brave.forums.forum.model import Forum


log = __import__('logging').getLogger(__name__)


class Forums(Generic):
    __model__ = Forum
    __order__ = 'name'
    __key__ = 'short'
    
    __metadata__ = dict(
            icon = 'comments',
            singular = "Forum",
            plural = "Forums",
            subtitle = "Primary organizational unit."
        )
    
    # Column Definitions
    
    name = PrimaryColumn(('name', 'summary'), "Forum")
    ro = Column('read', "Read")
    rw = Column('write', "Write")
    moderate = Column('moderate', "Moderate")
    created = DateColumn('id.generation_time', "Created")
    
    # Security Configuraiton of Existing Views
    
    #list = Generic.list.clone(condition=authenticated)
    #create = Generic.create.clone(condition=is_administrator)
    #read = Generic.read.clone(condition=authenticated)
    #update = Generic.update.clone(condition=is_alice)
    #delete = Generic.delete.clone(condition=is_alice)
    
    # Custom Actions
    
    #@Action.method("Void Invoice {record.id}", template='rita.template.invoice.void', icon='minus',
    #        condition=has_state('inc', 'pen', 'acc', 'com', 'pai', chain=is_administrator))
    #def void(self):
    #    pass  # confirm voiding
    
    #@void.bind('post')
    #def void(self):
    #    pass  # actually void the invoice
