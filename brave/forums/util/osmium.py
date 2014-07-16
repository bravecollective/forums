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
    
    eft = StringField(db_field='f', primary_key=True, unique=True)
    clf = StringField(db_field='c')
    
    @staticmethod
    def get_fit(eft):
        # We do this little dance to guarantee we make only one request to osmium for an given fit.
        query = Fit.objects(eft=eft)
        if query:
            return query[0]
        f = Fit(eft=eft)
        try:
            f.save()
        except OperationError: # collision on unique field
            return Fit.objects(eft=eft).first()

        # Okay, we were the first to insert the fit into the DB. Go ahead and populate the CLF.

        resp = requests.post(OSMIUM_BASE+"/api/convert/eft/dna", data=dict(input=eft))
        if resp.status_code == 200:
            clf = resp.text
        else:
            clf = None
        
        f.clf=clf
        f.save()
        return f
    
    def fit_url(self):
        if not self.clf:
            return None
        return OSMIUM_BASE+"/loadout/dna/"+self.clf
