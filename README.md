## Setup

```
python setup.py develop
```

Copy development.ini to local.ini and change/fill in values as appropriate.

If you want search, you'll need to
 - install Solr. Be sure to configure it so that it is not accessible from the internet!
 - configure Solr with the schema in `example-conf/solr-schema.xml`
 - configure search.server in your .ini to point to your Solr server.
