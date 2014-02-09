# encoding: utf-8

"""Category data definition.

Sample population:

me = Character.objects.get(character__name='Draleth')

Category( id=0, title="Management", members=['council', 'it']).save()
Category( id=5, title="General Discussions", members=['p', 'a', 'c']).save()
Category(id=10, title="EVE Discussions", members=['pvp', 'pve', 'm', 'i', 'd']).save()
Category(id=15, title="BRAVE Dojo", members=['dg', 'ds']).save()
Category(id=20, title="Other", members=['b', 'n', 'g', 'z']).save()

"""

from __future__ import unicode_literals

from mongoengine import Document, ObjectIdField, StringField, ReferenceField, IntField, ListField


log = __import__('logging').getLogger(__name__)


class Category(Document):
    meta = dict(
            collection = 'Categories',
            allow_inheritance = False,
            indexes = [('id', 'title')],
            ordering = ['id', 'title']
        )
    
    id = IntField(primary_key=True)
    title = StringField(db_field='t')
    members = ListField(StringField(), db_field='b')
    owner = ReferenceField('Character', db_field='o')
    
    def __repr__(self):
        return 'Category({0.id}, "{0.title}", [{1}])'.format(self, ', '.join(self.members))
    
    @property
    def forums(self):
        from brave.forums.component.forum.model import Forum
        return Forum.get(*self.members)
