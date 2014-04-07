# encoding: utf-8

from __future__ import unicode_literals

import requests

from mongoengine import Q, Document, StringField, EmbeddedDocumentField, DateTimeField

OSMIUM_BASE = "http://o.smium.org"

class Fit(Document):
    meta = dict(
            collection = 'Fits',
            allow_inheritance = False,
            indexes = [
                ],
        )
    
    eft = StringField(db_field='f', primary_key=True)
    clf = StringField(db_field='c')
    
    @staticmethod
    def get_fit(eft):
        query = Fit.objects(eft=eft)
        if query:
            print "hello"
            return query[0]
        
        resp = requests.post(OSMIUM_BASE+"/api/convert/eft/dna", data=dict(input=eft))
        if resp.status_code == 200:
            clf = resp.text
        else:
            clf = None
        
        return Fit(eft=eft, clf=clf).save()
    
    def fit_url(self):
        if not self.clf:
            return None
        return OSMIUM_BASE+"/loadout/dna/"+self.clf
