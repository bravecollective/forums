# encoding: utf-8

from __future__ import unicode_literals, print_function

import MySQLdb
import re
import HTMLParser

from bson import ObjectId
from datetime import datetime
from itertools import groupby

from brave.forums.component.forum.model import Forum
from brave.forums.component.thread.model import Thread
from brave.forums.component.comment.model import Comment
from brave.forums.auth.model import Character, Entity
from brave.core.util.eve import APICall, populate_calls

from marrow.util.bunch import Bunch


log = __import__('logging').getLogger(__name__)


def import_evebb(old_fid, new_fid, host='mysql.bravenewbies.net', user='amcgregor', password='', database='bravenew_evebb', prefix='evebb_'):
    forum = Forum.objects(short=new_fid).first()
    
    if not forum:
        log.error("Forum not found: %s", new_fid)
        return
    
    _lookup = APICall.objects.get(name='eve.CharacterID')
    _lookup_cache = dict()
    lookup = lambda i: _lookup_cache[i] if i in _lookup_cache else _lookup_cache.setdefault(i, _lookup(names=i).row[0].characterID)
    
    db = MySQLdb.connect(host=host, user=user, passwd=password, db=database, use_unicode=True)
    
    query = """SELECT
topic.id, topic.subject, topic.last_post, topic.num_views, topic.num_replies, topic.closed, topic.sticky,
post.poster, post.message, post.posted, post.edited

FROM {prefix}posts AS post
LEFT JOIN {prefix}topics as topic ON post.topic_id = topic.id

WHERE topic.poll_type = 0
AND topic.poster NOT LIKE 'CCP %'
AND topic.forum_id = {forum_id}

ORDER BY topic.posted ASC, post.posted ASC
"""
    
    cursor = db.cursor()
    cursor.execute(query.format(prefix=prefix, forum_id=old_fid))
    
    current = None
    columns = tuple([d[0].decode('utf8') for d in cursor.description])
    
    for row in cursor:
        row = Bunch(zip(columns, row))
        
        if current != row.id:
            current = row.id
            print("Thread", row.id, row.subject, row.posted, row.poster)
            thread = Thread(forum=forum, title=row.subject, modified=datetime.fromtimestamp(row.last_post))
            thread.stat.views = row.num_views
            thread.stat.comments = row.num_replies + 1
            thread.flag.sticky = bool(row.sticky)
            thread.flag.locked = bool(row.closed)
            thread.save()
        
        print("Reply", row.posted, row.poster)
        
        try:
            poster = Character.objects.get_or_create(character=Entity(
                    id = lookup(row.poster),
                    name = row.poster
                ))[0]
        except Character.MultipleObjectsReturned:
            poster = Character.objects(character__name=row.poster).first()
        
        comment = Comment(
                id = ObjectId.from_datetime(datetime.fromtimestamp(row.posted)),
                message = row.message,
                creator = poster
            )
        
        Thread.objects(id=thread.id).update_one(push__comments=comment)
