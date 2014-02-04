# encoding: utf-8

from __future__ import unicode_literals

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import csv

from math import ceil

from web.core import request, Controller, HTTPMethod
from web.core.http import HTTPFound, HTTPNotFound
from web.core.locale import _

from marrow.schema.declarative import BaseAttribute, Attribute
from marrow.schema.util import DeclarativeAttributes
from marrow.util.convert import array

from mongoengine.errors import ValidationError

from brave.forums.generic.action import Action
from brave.forums.generic.column import Column
from brave.forums.generic.filter import Filter
from brave.forums.generic.util import only, serialize, context


log = __import__('logging').getLogger(__name__)


class Generic(BaseAttribute, Controller):
    """A generalized structure for the presentation and implementation of record management.
    
    HTTP    GET /object/              Full page template for the list view.
    
     XHR    GET /object/index.html    The table body fragment for a given range of results.      XHR    GET /object/index.json    The equivalent of the table body in pure JSON.     
     XHR    GET /object/form.html     The form body fragment for record creation.
     XHR    GET /object/form.json     The schema of the record creation form, also available in yaml and bencode.
    
    HTTP   POST /object/              The action of creating a new record, HTTP redirect version.
     XHR   POST /object/              The action of creating a new record, JSON version.
    
    HTTP    GET /object/id            Full page template for record detail view.
     XHR    GET /object/id.json       JSON version of the record data.  (Also available: yaml, bencode.)
    
    HTTP   POST /object/id            Update the given record, HTTP redirect version.
     XHR   POST /object/id            Update the given record, JSON version.
                                      Partial updates are supported.
    
    HTTP DELETE /object/id            Delete the record, HTTP redirect version.
     XHR DELETE /object/id            Delete the record, JSON version.
    """
    
    __model__ = Attribute()
    __key__ = Attribute(default='id')
    __form__ = Attribute()
    __order__ = Attribute(default=None)  # default order
    __search__ = Attribute(default=None)  # quick search field reference
    
    __metadata__ = Attribute(default=dict())  # area, icon, etc
    __context__ = Attribute(default=None)  # dict or callable returning a dict of vars to pass to templates
    
    # Aggregates
    
    __actions__ = DeclarativeAttributes(Action)
    __filters__ = DeclarativeAttributes(Filter)
    __columns__ = DeclarativeAttributes(Column)
    
    # Helpers.
    
    def __json__(self, record):
        """Translate a database record into valid JSON data."""
        if hasattr(record, '__json__'):
            return record.__json__()
        
        log.warning("%s instance is missing a __json__ method.", record.__class__.__name__)
        return record.to_json()
    
    @property
    def __query__(self):
        """Return a base query object.
        
        It is useful to override this if you have specific requirements, esp. security.
        """
        query = self.__model__.objects
        
        if self.__order__:
            query = query.order_by(self.__order__)
        
        return query
    
    # Default actions.
    
    @Action.method('{model.__name__} Records', False, template='brave.forums.generic.template.list')
    def list(self, q=None, s=None, p=None, l=None, o=None, omit=None):
        """Return a listing, partial listing body, or serialized results."""
        
        jsonify = request.controller.__json__
        results = request.controller.__query__
        count = results.count()
        
        page = int(p) if p else 1
        limit = min(int(l) if l else 10, 100)
        order = array(o) if o else request.controller.__order__
        omit = array(omit) if omit else []
        pages = 1 if not limit else int(ceil(count / float(limit)))
        
        if limit:
            results = results.skip((page - 1) * limit).limit(limit)
        
        if request.is_xhr or ( request.format and request.format == 'html' ):
            log.debug("action.list.rows model=%s p=%d l=%d o=%s c=%d",
                    request.controller.__model__.__name__,
                    page, limit, order, count)
            return self.action.template, context(limit=limit, count=count, pages=pages, page=page, results=results), only('rows')
        
        if request.format:
            log.debug("action.list.serialize model=%s p=%d l=%d o=%s c=%d",
                    request.controller.__model__.__name__,
                    page, limit, order, count)
            
            data = dict(success=True)
            
            if 'count' not in omit:
                data['count'] = dict(
                        results = count,
                        pages = pages,
                        limit = limit
                    )
            
            if 'query' not in omit:
                 data['query'] = dict()
                
            if 'results' not in omit:
                data['results'] = []
                for record in results:
                    data['results'].append({name: col.serialize(record) for name, col in request.controller.__columns__.iteritems() if col.condition})
            
            if request.format in ('csv', 'tab'):
                tmp = StringIO()
                cw = csv.writer(tmp, dialect='excel' if request.format == 'csv' else 'excel-tab')
                
                for record in data['results']:
                    row = []
                    
                    for name, col in request.controller.__columns__.iteritems():
                        if not col.condition: continue
                        
                        if not isinstance(record[name], dict):
                            row.append(record[name])
                            continue
                        
                        for k, v in record[name].iteritems():
                            row.append(v)
                    
                    cw.writerow(row)
                
                return tmp.getvalue().strip('\r\n')
            
            return serialize(), data
        
        log.debug("action.list.html model=%s p=%d l=%d o=%s c=%d",
                request.controller.__model__.__name__,
                page, limit, order, count)
        return self.action.template, context(limit=limit, count=count, pages=pages, page=page, results=results)
    
    @list.bind('post')
    def list(self):
        log.debug("POST Listing")
    
    @Action.method('New {model.__name__} Record', False, template='brave.forums.generic.template.form')
    def create(self):
        if request.is_xhr:
            log.debug("action.create.get.xhr")
        
        log.debug("action.create.get.html")
    
    @create.bind('post')
    def create(self):
        log.debug("POST Creation")
    
    @Action.method('{record}', False, template='brave.forums.generic.template.view')
    def read(self):
        controller = request.controller
        record = request.record
        
        if request.format:
            log.debug("action.read.get.serialize")
            return serialize(), dict(
                    success = True,
                    query = {controller.__key__: getattr(record, controller.__key__)},
                    result = record.__json__() if hasattr(record, '__json__') else controller.__json__(record)
                )
        
        if request.is_xhr:
            log.debug("action.read.get.xhr")
            return self.action.template, context(), only()
        
        log.debug("action.read.get.html")
        return self.action.template, context()
    
    @Action.method('Delete {model.__name__} Record', template='brave.forums.generic.template.delete', icon='remove')
    def delete(self):
        log.debug("action.delete.get.html")
        return self.action.template, context()
    
    @delete.bind('delete')
    def delete(self):
        if request.is_xhr or request.format:
            log.debug("action.delete.delete.serialize")
            return serialize(), dict(success=True)
        
        log.debug("action.delete.delete.html")
        raise HTTPFound(location='/')
    
    @Action.method('Modify {model.__name__} Record', template='brave.forums.generic.template.form', icon='pencil')
    def update(self):
        log.debug("GET Modification")
    
    @update.bind('post')
    def update(self, **kw):
        log.debug("action.update.post")
        
        return serialize(), dict(
                success = True,
                status = 'updated'
            )
    
    # WebCore controller methods.
    
    def index(self, *args, **kw):
        request.controller = self
        return self.list.controller()(*args, **kw)
    
    def __lookup__(self, identifier, *args, **kw):
        request.path_info_pop()
        request.controller = self
        identifier, _, ext = identifier.rpartition('.')
        if not identifier: identifier = ext
        return InstanceMethods(identifier), args


class InstanceIndex(HTTPMethod):
    def __init__(self):
        controller = request.controller
        
        self.get = controller.read.controller()
        self.post = controller.update.controller()
        self.delete = controller.delete.controller()
        
        super(InstanceIndex, self).__init__()


class InstanceMethods(Controller):
    def __init__(self, identifier):
        super(InstanceMethods, self).__init__()
        
        controller = request.controller
        
        try:
            request.record = controller.__model__.objects.get(**{controller.__key__: identifier})
        except (controller.__model__.DoesNotExist, ValidationError):
            log.exception("instance.init model=%s %s=%s", controller.__model__.__name__, controller.__key__, identifier)
            raise HTTPNotFound(_("Record with identifier {0} can not be found.").format(identifier))

        self.index = InstanceIndex()
        
        # Attach additional actions.
        for action in (i for i in controller.__actions__.itervalues() if i.instance and i.__name__ not in ('read', )):
            setattr(self, action.__name__, action.controller())
        
        log.debug("instance.init model=%s %s=%s\n\t%r", controller.__model__.__name__, controller.__key__, identifier, request.record)
