from pysolr import Solr

from marrow.util.futures import ScalingPoolExecutor
from web.core import config

if not config.get('search.enabled'):
    def index_comment(*args, **kw):
        pass
    def unindex_comment(*args, **kw):
        pass
    def index_comment_async(*args, **kw):
        pass
    def unindex_comment_async(*args, **kw):
        pass
    def reindex(*args, **kw):
        pass
    def search(*args, **kw):
        pass
else:

    solr = Solr(config['search.server'])
    index_thread_pool = ScalingPoolExecutor(5, 10, 60)

    def index_comment(thread, comment):
        """Add a single comment to Solr. If the comment is already indexed,
        this will replace the old one."""
        solr.add([{
            'comment_id': comment.id,
            'thread_id': thread.id,
            'title': thread.title,
            'forum': thread.forum.name,
            'forum_short': thread.forum.short,
            'author': comment.creator.character.name,
            'modified': comment.modified,
            'comment': comment.message,
        }])

    def unindex_comment(comment_id):
        """Remove a comment from the search index by id."""
        solr.delete(q='comment_id:{}'.format(comment_id))

    def index_comment_async(thread, comment):
        index_thread_pool.submit(index_comment, thread, comment)

    def unindex_comment_async(comment_id):
        index_thread_pool.submit(unindex_comment, comment_id)

    def reindex(clear=False):
        """Index every comment."""
        from brave.forums.component.thread.model import Thread
        if clear:
            solr.delete(q='*:*')
        for thread in Thread.objects():
            for comment in thread.reload().comments:
                index_comment(thread, comment)

    def search(query, forums):
        """Run a search, filtering to the given forums"""
        fq = "forum_short:(" + " OR ".join(forums) + ")"
        return solr.search(query, **{
            'fq': fq,
            'hl': 'true', # Rreturn highlighted hit snippets...
            'hl.fl': "*", # ...on all fields...
            'hl.requireMatch': 'true', # ...that match.
            'defType': 'edismax', # Use the extended DisMax query parser.
            'qf': 'title^10 text', # Weight titles more heavily than other fields.
        })
