#!/usr/bin/env python
from setuptools import setup, find_packages

VERSION = '1.6.3'

setup(
    name='hspy',
    version=VERSION,
    author='prior',
    author_email='mprior@hubspot.com',
    packages=find_packages(),
    url='https://github.com/HubSpot/hspy',
    download_url='https://github.com/HubSpot/hspy/tarball/v%s'%VERSION,
    license='LICENSE.txt',
    description='Utilities to aide HubSpot Marketplace development',
    long_description=open('README.rst').read(),
    install_requires=[
        'Django==1.3'
    ],
    platforms=['any']
)

