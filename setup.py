#!/usr/bin/env python
from distutils.core import setup

setup(
    name='hspy',
    version='1.0',
    description='HubSpot Marketplace Python Django Goodness',
    author='Michael Prior',
    author_email='prior@cracklabs.com',
    url='',
    packages=['marketplace'],
    install_requires=[
        'nose==1.1.2',
        'unittest2==0.5.1'
    ]
)
