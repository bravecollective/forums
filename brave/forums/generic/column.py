# encoding: utf-8

from __future__ import unicode_literals

from web.auth import always
from web.core import request, url
from web.core.locale import L_

from marrow.schema.declarative import BaseAttribute, Attribute
from marrow.tags import html5 as H


log = __import__('logging').getLogger(__name__)


class Column(BaseAttribute):
    attribute = Attribute()
    label = Attribute()
    width = Attribute()
    condition = Attribute(default=always)
    sortable = Attribute(default=False)
    default = Attribute(default=None)
    
    def resolve(self, record, name):
        value = record
        separator = True
        remainder = name
        
        while separator:
            name, separator, remainder = remainder.partition('.')
            
            try:
                value = getattr(value, name)
            except AttributeError:
                value = self.default
                break
        
        return value
    
    def render(self, record):
        if isinstance(self.attribute, (str, unicode)):
            return self.resolve(record, self.attribute)
        
        # This allows for positionally compound columns.
        return [self.resolve(record, a) for a in self.attribute]
    
    def serialize(self, record):
        if isinstance(self.attribute, (str, unicode)):
            return self.resolve(record, self.attribute)
        
        # This allows for positionally compound columns.
        return [self.resolve(record, a) for a in self.attribute]


class ReferenceColumn(Column):
    model = Attribute(default=None)
    target = Attribute(default=None)
    
    def render(self, record):
        value = super(ReferenceColumn, self).render(record)
        
        if isinstance(value, (str, unicode)):
            try:
                value = self.model.objects.get(id=value)
            except self.model.NotFound:
                return value
        
        if not self.target:
            return unicode(value)
        
        return self.resolve(value, self.target)
    
    def serialize(self, record):
        value = super(ReferenceColumn, self).serialize(record)
        
        if self.model:
            try:
                value = dict(id=unicode(value), label=self.model.objects.get(id=value))
            except self.model.NotFound:
                return None
        else:
            value = dict(id=unicode(value.id), label=value) if value else None
        
        if value:
            value['label'] = self.resolve(value['label'], self.target) if self.target else unicode(value['label'])
        
        return value


class LinkColumn(Column):
    protocol = Attribute(default=None)
    external = Attribute(default=False)
    
    def render(self, record):
        value = super(LinkColumn, self).render(record)
        protocol = self.protocol
        
        if isinstance(value, (str, unicode)):
            label = value
        else:
            value, label = value
        
        if not protocol:
            if '://' not in value and '@' not in value:
                return value
            
            if '://' not in value and '@' in value:
                protocol = 'mailto:'
        
        if self.external:
            return H.a ( target = "_blank", href = "{0}{1}".format(protocol or '', value) ) [ value ]
        
        return H.a ( href = "{0}{1}".format(protocol or '', value) ) [ value ]
        
    def serialize(self, record):
        value = super(LinkColumn, self).serialize(record)
        protocol = self.protocol
        
        if isinstance(value, (str, unicode)):
            label = value
        else:
            value, label = value
        
        if not protocol:
            if '://' not in value and '@' not in value:
                return value
            
            if '://' not in value and '@' in value:
                protocol = 'mailto:'
        
        return "{0}{1}".format(protocol or '', value)


class PrimaryColumn(Column):
    def render(self, record):
        parts = super(PrimaryColumn, self).render(record)
        if not isinstance(parts, list):
            parts = [parts]
        
        return H.div ( strip = True ) [
                [
                    H.i ( class_ = "icon-search icon-fixed-width"),
                    H.a ( target = "_blank", href = url.compose('/' + request.controller.__name__, getattr(request.record, request.controller.__key__), '') ) [ parts[0] ]
                ] + [ ( H.span ( strip = True ) [ H.br, i ] ) for i in parts[1:] ]
            ]
    
    def serialize(self, record):
        value = super(PrimaryColumn, self).serialize(record)
        
        if isinstance(value, (list, tuple)):
            return [unicode(v) for v in value]
        
        return unicode(value)
        
        


class StateColumn(Column):
    name_map = dict(
        pending=L_('pending'), expired=L_('expired'), active=L_('active'),
        verified=L_('verified'), unverified=L_('unverified'), inactive=L_('inactive'),
        idle=L_('idle'),
        incomplete=L_('review'), accepted=L_('accepted'), complete=L_('complete'), paid=L_('paid'), void=L_('void'), hidden=L_('hidden'),
        inc=L_('review'), pen=L_('pending'), acc=L_('accepted'), com=L_('complete'), pai=L_('paid'), voi=L_('void'), nul=L_('hidden'),
    )

    state_map = dict(
            pending='warning', expired='important', active='success',
            verified='success', unverified='warning', inactive='important',
            idle='info',
            incomplete='info', accepted='warning', complete='success', paid='neutral', void='neutral', hidden='neutral',
            inc='info', pen='warning', acc='warning', com='success', pai='neutral', voi='neutral', nul='neutral',
        )
    
    def render(self, record):
        value = super(StateColumn, self).render(record)
        return H.span ( class_ = 'label label-' + self.state_map[value] ) [ unicode(self.name_map[value]) ]
    
    def serialize(self, record):
        return unicode(self.name_map[super(StateColumn, self).render(record)])


class DateColumn(Column):
    def render(self, record):
        value = super(DateColumn, self).render(record)
        
        if not value: return H.em [ "Never" ]
        
        return H.time ( class_ = 'relative', datetime = value.strftime('%Y-%m-%dT%H:%M:%S%z') ) [
                value.strftime('%B %e, %G at %H:%M:%S')
            ]
    
    def serialize(self, record):
        value = super(DateColumn, self).render(record)
        return value.isoformat()


class DollarColumn(Column):
    def render(self, record):
        value = super(DollarColumn, self).render(record)
        return "${:,}".format(value)
    
    def serialize(self, record):
        value = super(DollarColumn, self).serialize(record)
        return float(value)
