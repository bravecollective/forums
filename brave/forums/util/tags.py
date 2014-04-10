# encoding: utf-8

from __future__ import unicode_literals

from bbcode import Parser
from urllib import quote
from marrow.tags import html5 as H
from brave.forums.util.osmium import Fit


log = __import__('logging').getLogger(__name__)


class SemanticTagParser(object):
    def __init__(self):
        self.parser = Parser()
        self.standalone_available_tags = dict(
                System = self.format_dotlan,
                Region = self.format_dotlan,
                Character = self.format_evewho,
                Corporation = self.format_evewho,
                Alliance = self.format_evewho,
                DebugTag = self.format_logging
            )
        
        for tag, parser in self.standalone_available_tags.iteritems():
            self.parser.add_formatter(tag, parser, standalone=True)
        
        self.parser.add_formatter('Spoiler', self.format_spoilers, standalone=False, strip=True)
        self.parser.add_formatter('h', self.format_heading, standalone=False, strip=True)
        self.parser.add_formatter('img', self.format_image, standalone=False, strip=True)
        self.parser.add_formatter('fit', self.format_fit, standalone=False, strip=True,
                  transform_newlines=False, escape_html=False)
    
    def format(self, text):
        try:
            return self.parser.format(text)
        except Exception as e:
            log.debug("bbcode fail", exc_info=True)
            
            return unicode(H.div ( strip = True ) [
                    text,
                    H.div ( class_ = 'error-message' ) [ "There was an error processing this bbcode: ", unicode(e) ]
                ])
    
    dotlan_template = '<a href="http://evemaps.dotlan.net/{0}/{1}" target="dotlan">{2}</a>'
    
    def format_dotlan(self, tag_name, value, options, parent, context):
        label = options[tag_name]
        
        return self.dotlan_template.format(
                tag_name.lower(),
                label.replace(' ', '_'),
                label
            )
    
    evewho_alias = dict(corporation='corp', alliance='ali', character='pilot')
    evewho_template = '<a href="http://evewho.com/{0}/{1}" target="evewho">{2}</a>'
    
    def format_evewho(self, tag_name, value, options, parent, context):
        label = options[tag_name]
        return self.evewho_template.format(self.evewho_alias[tag_name.lower()], quote(label), label)
    
    def format_logging(self, tag_name, value, options, parent, context):
        return unicode(H.pre [[
                "{0}={1!r}\n".format(k, v) for k, v in locals().iteritems() if k[0] != '_'
            ]])
    
    def format_spoilers(self, tag_name, value, options, parent, context):
        if tag_name not in options:
            options[tag_name] = "Spoilers..."
        
        return unicode(H.div ( class_ = 'spoiler-container' ) [
                H.a ( href = '#', class_ = 'target fa fa-plus-square fa-fw fa-lg' ),
                H.span ( class_ = 'description' ) [ options[tag_name] ],
                H.div ( class_ = 'spoilers' ) [ H.Text(value, escape=False) ]
            ])
    
    def format_heading(self, tag_name, value, options, parent, context):
        return unicode(H.h4 [ H.Text(value, escape=False) ])
    
    def format_image(self, tag_name, value, options, parent, context):
        return value.replace('">', '" target="_blank"><img src="').replace('</a>', '"></a>')
        return unicode(H.img ( src = value ))
    
    def format_fit(self, tag_name, value, options, parent, contex):
        title = None
        url = None
        
        if value:
            title = value.split("\n")[0]
            url = Fit.get_fit(value).fit_url()
        
        if url:
            description_contents = (title, " - ", H.a ( href = url ) [ "Osmium" ])
        else:
            description_contents = title
        
        value = value.replace('\n', "<br />")
        
        return unicode(H.div ( class_ = 'spoiler-container' ) [
                H.a ( href = '#', class_ = 'target fa fa-plus-square fa-fw fa-lg' ),
                H.span ( class_ = 'description' ) [ description_contents ],
                H.div ( class_ = 'spoilers' ) [ value ]
            ])
