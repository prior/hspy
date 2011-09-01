#!/usr/bin/env python
from distutils.core import setup

setup(
    name='hubspot-marketplace-django',
    version='1.0',
    description='Python WebEx Api Wrapper',
    author='Michael Prior',
    author_email='prior@cracklabs.com',
    url='',
    packages=['hubspot_marketplace.django'],
    install_requires=[
        'nose==1.1.2',
        'unittest2==0.5.1'
    ]
)
