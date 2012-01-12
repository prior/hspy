#!/usr/bin/env python
from distutils.core import setup

setup(
    name='hspy',
    version='1.5.1',
    description="Python utilities to aide HubSpot Marketplace development",
    long_description = open('README.md').read(),
    author='Michael Prior',
    author_email='prior@cracklabs.com',
    url='https://github.com/prior/hspy',
    download_url='https://github.com/prior/hspy/tarball/v1.5.1',
    license='LICENSE.txt',
    packages=['marketplace'],
    install_requires=[
        'Django==1.3',
        'nose==1.1.2',
        'unittest2==0.5.1'
    ]
)
