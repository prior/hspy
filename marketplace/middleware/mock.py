from django.conf import settings
from django.http import QueryDict
from django.core.exceptions import MiddlewareNotUsed
import base64
import hashlib
import hmac
import re
import os

import logger


class MockMiddleware(object):
    """
Use this middleware to mock exactly what the HubSpot Marketplace would do with
your requests/responses locally.  This allows you to test your app locally and
hit it just as it would be hit in production.  To use, you'll need to:

1) Make sure you've already set up your AuthMiddlware all setup -- see docs for
that guy if you don't know how.

2) Place this class in your middlewares list in your settings.py BEFORE the
AuthMiddleware.

3) Give the middleware enough information to correctly mock out how things
would go down in production, adding something like this to your settings.py:

    HUBSPOT_MARKETPLACE_MOCK = {
        'slug': 'yourappslug',
        'app': {
            'name': 'YourAppName', # override with your app name
            'callback_url': 'http://localhost:8000',
        },
        'user': {
            'id': 9999999,  # fake user_id
        }
    }

This middleware assumes that anything coming in on /market/HUBID/canvas/SLUG
should seem as a marketplace request should seem, and it appropriately adds all
the attributes to the request that would be added in production.

It also rewrites all your hsml on the response as you would expect them
rewritten in production.

NOTE-- this mock will always have to play catchup with the marketplace.  As they
add new features to the marketplace, they need to also be mocked here.  Please
feel free to contribute to this effort.
    """

    MOCK_SETTINGS_DEFAULTS = {
        'slug': 'yourslug', # override with your actual slug
        'app': {
            'name': 'MyAppName', # override with your app name
            'callback_url': 'http://localhost:8000',
        },
        'user': {
            'id': 9999999,  # fake user_id so we have something
        },
        'caller': 'Hubspot Marketplace',  # don't expect this overridden
    }


    def __init__(self):
        super(MockMiddleware,self).__init__()
        mock = getattr(settings, 'HUBSPOT_MARKETPLACE_MOCK', {})
        auth = getattr(settings, 'HUBSPOT_MARKETPLACE_AUTH', {})
        secret = auth.get('secret_key')
        self.log = logger.get_log('MockMiddleware')
        if not mock or mock and not secret:
            self.log.info('MockMiddleware has been turned off for all'
                    'requests')
            raise MiddlewareNotUsed
        payload = 'payload'
        digest = hmac.new(secret, payload, hashlib.sha1).digest()
        self.signature = '.'.join(
                [self.base64_url_encode_for_real(s) 
                    for s in [digest, payload]])

        slug = mock.get('slug')
        if not slug:
            raise KeyError("Missing slug definition in MockMiddleware")

        self.prefix_path_re = re.compile('/market/(\d+)/canvas/%s'%slug)
        self.body_re = re.compile(r'<body>(.*?)</body>',re.DOTALL)
        self.link_re = re.compile(r'<hs:link (.*?)/?>')
        self.script_re = re.compile(r'<hs:script (.*?)></hs:script>')
        self.title_re = re.compile(r'<hs:title(.*?)>(.*?)</hs:title>')
        self.form_re = re.compile(r'(<form\s.*?)action="(/.*?)"')
        self.anchor_re = re.compile(r'(<a\s.*?)href="(/.*?)"')

        path = os.path.join(os.path.dirname(__file__),'wrapper.html')
        self.wrapper = open(path).read()

        self.build_static_params()

        self.log.info('HubSpot Marketplace Mock Canvas Middleware Activated')


    def build_static_params(self):
        """
        Builds the params in a very forgiving way.  Necessary for backwared
        compatibility
        """

        mapping = {
            'caller': 'caller',
            'user_id': 'user.id',
            'user.email': 'user.email',
            'user.firstName': 'user.first_name',
            'user.lastName': 'user.last_name',
            'app.name': 'app.name',
            'app.callbackUrl': 'app.callback_url',
            'app.pageUrl': 'page.url',
        }
        base = {}
        defaults = self.__class__.MOCK_SETTINGS_DEFAULTS
        for k,v in mapping.iteritems():
            val = None
            for store in [self.mock, defaults]:
                if not val:
                    val = store.get(k) or store.get(v)
                    for l in [k,v]:
                        if not val and '.' in l:
                            parts = l.split('.')
                            temp = store.get(parts[0],{})
                            val = val or temp.get(parts[1])

            base['hubspot.marketplace.%s'%k] = str(val or '')
        base['hubspot.marketplace.signature'] = self.signature
        base['hubspot.marketplace.is_mock'] = 'true'
        self.base = base


    def process_request(self, request):
        url_match = self.prefix_path_re.match(request.path)
        if not url_match: # this isn't a url that needs marketplace mocking
            return 

        # make the relevant dictionary mutable
        params = getattr(request, request.method).copy()

        hub_id = int(url_match.group(1))

        for k,v in self.base.iteritems():
            params.appendlist(k,v)
        params.appendlist('hubspot.marketplace.portal_id', str(hub_id))
        params.appendlist('hubspot.marketplace.app.canvasUrl', 
                "http://%s/market/%s/canvas/%s" % 
                (request.get_host(), hub_id, self.slug))
        params.appendlist('hubspot.marketplace.app.pageUrl', str(request.path))

        setattr(request, request.method, QueryDict(params))

        request.path = self.prefix_path_re.sub('', request.path, 1)
        request.path_info = self.prefix_path_re.sub('', request.path_info, 1)


    def process_response(self, request, response):
        marketplace = request and getattr(request, 'marketplace', None)
        if marketplace.is_mock and response.status_code==200:
            if self.body_re.search(response.content):
                innards = self.body_re.findall(response.content)[0]
                head = ''
                for link in self.link_re.findall(innards):
                    head += "\n<link %s />"%link
                bottom = ''
                for script in self.script_re.findall(innards):
                    bottom += "\n<script %s></script>"%script
                innards = self.link_re.sub('',innards)
                innards = self.title_re.sub('',innards)
                innards = self.script_re.sub('',innards)
                innards = self.form_re.sub(r'\1action="/market/%s/canvas/%s\2"' %
                        (marketplace.hub_id,self.slug), innards)
                innards = self.anchor_re.sub(r'\1href="/market/%s/canvas/%s\2"' %
                        (marketplace.hub_id,self.slug), innards)
                content = self.wrapper
                content = content.replace('[[HEAD_CONTENTS]]',head)
                content = content.replace('[[BODY_CONTENTS]]',innards)
                content = content.replace('[[BOTTOM_BODY_CONTENTS]]',bottom)
                response.content = content
        return response


    def base64_url_encode_for_real(decoded_s):
        """
        base64 library decided to leave '=' chars still kicking around, and was
        still bold enough to call their method 'urlsafe' -- okaaaaay...  This
        method is urlsafe for real, and matches what the marketplace is
        expecting
        """
        return base64.urlsafe_b64encode(decoded_s).split('=',1)[0]




