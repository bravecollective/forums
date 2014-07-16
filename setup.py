#!/usr/bin/env python

import sys, os
from setuptools import setup, find_packages

setup(
        name = "Brave Forums",
        version = "0.1",
        description = "Online forums software designed for the Brave Collective Alliance of EVE Online.",
        author = "Alice Bevan-McGregor",
        author_email = "alice@gothcandy.com",
        license = "MIT",
        
        packages = find_packages(),
        include_package_data = True,
        zip_safe = False,
        paster_plugins = ['PasteScript', 'WebCore'],
        namespace_packages = ['brave'],
        
        tests_require = ['nose', 'webtest', 'coverage'],
        test_suite = 'nose.collector',
        
        dependency_links = [
            'https://github.com/marrow/marrow.tags/archive/develop.zip#egg=marrow.tags',
            'https://github.com/marrow/marrow.templating/archive/develop.zip#egg=marrow.templating',
            'https://github.com/marrow/WebCore/archive/develop.zip#egg=WebCore'
            'https://github.com/bravecollective/api/archive/develop.zip#egg=brave.api',
        ],
        
        install_requires = [
                'marrow.tags',
                'marrow.templating',
                'brave.api',
                'WebCore>=1.1.2',
                'MongoEngine>=0.7.999',
                'Mako>=0.4.1',
                'beaker>=1.5',
                'requests==1.1.0',
                'blinker',
                'ecdsa',
                'xmltodict',
                'ipython',
                'pudb',
                'babel',
                'marrow.mailer',
                'futures',
                'bbcode'
            ],
        
    )
