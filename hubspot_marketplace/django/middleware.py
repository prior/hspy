from django.conf import settings
from django.http import HttpResponse
from django.core.exceptions import MiddlewareNotUsed
import base64
import hashlib
import hmac
import re
import pprint
import os

import logging
logger = logging.getLogger(__name__)


def marketplace(function=None):
    def _dec(view_func):
        def _view(request, *args, **kwargs):
            authenticate = getattr(settings, 'HUBSPOT_MARKETPLACE', {}).get('AUTH', {}).get('ACTIVATE', True)
            if authenticate and not (request.marketplace or {}).get('authenticated', False):
                logger.error("\nThis request did not have a proper HubSpot Marketplace authentication signature!\n  This particular view was decorated so as to expect a valid HubSpot Marketplace signature, however, the signature on this request was either missing, malformed, or wrong.  Perhaps you incorrectly decorated this view as a marketplace view?  Or, perhaps this request did not originate from HubSpot!?  Returning a 401 for this request.")
                return HttpResponse(status=401)
            else:
                return view_func(request, *args, **kwargs)
        _view.__name__ = view_func.__name__
        _view.__dict__ = view_func.__dict__
        _view.__doc__ = view_func.__doc__
        return _view
    
    if function is None:
        return _dec
    else:
        return _dec(function)


class AuthMiddleware(object):
    """
Use this to ensure requests are coming from HubSpot and that they are intended for your app.

To install, simply place this class in your middlewares list, and set up this setting:
    HUBSPOT_MARKETPLACE = { 
        'AUTH': { 'SECRET_KEY': 'hubspot-issued-secret-key-here' } 
    }

If you want to easily toggle request validation on and off you can do so from the settings as well:
    HUBSPOT_MARKETPLACE = { 
        'ACTIVATE': False  # it will be on by default unless turned off like so
    }  """

    def __init__(self):
        marketplace_settings = getattr(settings, 'HUBSPOT_MARKETPLACE', {})
        if not marketplace_settings.get('ACTIVATE', True) or not marketplace_settings.get('ACTIVATE_AUTH', True):
            logger.info('HubSpot Marketplace Request Authentication Deactivated')
            raise MiddlewareNotUsed
        self.secret = marketplace_settings.get('SECRET_KEY', None)
        logger.info('HubSpot Marketplace Request Authentication Activated')
        if not self.secret:
            raise MissingSecretError

    def process_request(self, request):
        request.marketplace = getattr(request, 'marketplace', {})
        request.marketplace['authenticated']= False
        signature = request.REQUEST.get('hubspot.marketplace.signature', None) or ''
        if self.is_request_authentic(signature):
            #TODO: could make this more general and flexible as new things are added and maybe other things are removed, but would still like to force common capitalization/underscore rules
            request.marketplace['authenticated'] = True
            request.marketplace['caller'] = request.REQUEST.get('hubspot.marketplace.caller', None)
            request.marketplace['portal'] = {'id': request.REQUEST.get('hubspot.marketplace.portal_id', None)}
            request.marketplace['app'] = {}
            request.marketplace['app']['name'] = request.REQUEST.get('hubspot.marketplace.app.name', None)
            request.marketplace['app']['callback_url'] = request.REQUEST.get('hubspot.marketplace.app.callbackUrl', None)
            request.marketplace['app']['page_url'] = request.REQUEST.get('hubspot.marketplace.app.pageUrl', None)
            request.marketplace['app']['canvas_url'] = request.REQUEST.get('hubspot.marketplace.app.canvasUrl', None)
            request.marketplace['user'] = {'id': request.REQUEST.get('hubspot.marketplace.user_id', None)}
            request.marketplace['user']['first_name'] = request.REQUEST.get('hubspot.marketplace.app.firstName', None)
            request.marketplace['user']['last_name'] = request.REQUEST.get('hubspot.marketplace.app.lastName', None)
            request.marketplace['user']['email'] = request.REQUEST.get('hubspot.marketplace.app.email', None)

    def is_request_authentic(self, signature):
        signature = str(signature)  # convert from unicode
        digest, payload = [base64_url_decode_for_real(item) for item in (signature+'.').split('.')[0:2]]
        return digest and payload and digest == hmac.new(self.secret, payload, hashlib.sha1).digest()


class MissingSecretError(NameError):
    """
HubSpot Marketplace Secret hasn't been defined!

If you intend to use the AuthMiddleware and/or MockMiddleware, then you need to 
specify a secret in your settings:
    HUBSPOT_MARKETPLACE = { 
        'SECRET_KEY': 'hubspot-issued-secret-key-here',
    }

Or you can temporarily turn off the middleware's in your settings:
    HUBSPOT_MARKETPLACE = { 
        'ACTIVATE': False 
    }

Or, if you plan to never use it, then you need to remove 
'AuthMiddleware' and 'MockMiddleware' from your list of middlewares """

    def __init__(self, *args):
        NameError.__init__(self, self.__doc__)


MOCK_SETTINGS_DEFAULTS = {
    'SLUG': 'yourslug', # override with your actual slug
    'CALLER': 'Hubspot Marketplace',  # don't expect this overridden
    'APP': {
        'NAME': 'MyAppName', # override with your app name
        'CALLBACK_URL': 'http://localhost:8000',
    },
    'USER': {
        'ID': 9999999,  # fake user_id
    }
}


class MockMiddleware(object):
    def __init__(self):
        marketplace_settings = getattr(settings, 'HUBSPOT_MARKETPLACE', {})
        if not marketplace_settings.get('ACTIVATE', True) or not marketplace_settings.get('ACTIVATE_MOCK', True):
            logger.info('HubSpot Marketplace Request Authentication Deactivated')
            raise MiddlewareNotUsed
        secret = marketplace_settings.get('SECRET_KEY', None)
        if secret:
            payload = 'payload'
            digest = hmac.new(secret, payload, hashlib.sha1).digest()
            self.signature = '.'.join([base64_url_encode_for_real(s) for s in [digest, payload]])
        else:
            logger.info('Unable to generate a mock signature without a SECRET_KEY specified!')

        self.mock_settings = marketplace_settings.get('MOCK', {})
        self.slug = self.mock_settings.get('SLUG', None)
        if not self.slug:
            raise MissingSlugError
        self.prefix_path_re = re.compile('/market/(\d+)/canvas/%s'%self.slug)

        self.mock_settings.setdefault('CALLER', MOCK_SETTINGS_DEFAULTS['CALLER'])
        for k in MOCK_SETTINGS_DEFAULTS['APP']:
            self.mock_settings.setdefault(k, MOCK_SETTINGS_DEFAULTS['APP'][k])
        for k in MOCK_SETTINGS_DEFAULTS['USER']:
            self.mock_settings.setdefault(k, MOCK_SETTINGS_DEFAULTS['USER'][k])
        
        self.rebody = re.compile('<body>(.*?)</body>',re.DOTALL)
        self.relink = re.compile('<hs:link (.*?)/?>')
        self.rescript = re.compile('<hs:script (.*?)/?>')
        self.retitle = re.compile('<hs:title(.*?)>(.*?)</hs:title>')
        self.reform = re.compile('(<form\s.*?)action="(/.*?)"')
        self.reanchor = re.compile('(<a\s.*?)href="(/.*?)"')

        self.wrapper = open(os.path.join(os.path.dirname(__file__),'wrapper.html')).read()

        logger.info('HubSpot Marketplace Mock Canvas Middleware Activated')

    def process_request(self, request):
        # make the relevant dictionary mutable
        if request.method == 'GET':
            h = request.GET = request.GET.copy()
        else:
            h = request.POST = request.POST.copy()

        # rewrite path url and path_info urls
        m = self.prefix_path_re.match(request.path)
        if m:
            request.path = self.prefix_path_re.sub('', request.path, 1)
            portal_id = m.group(1)
            request.path_info = self.prefix_path_re.sub('', request.path_info, 1)

            #if we're here, then we need to be mocking out a marketplace request
            h.appendlist('hubspot.marketplace.caller', self.mock_settings['CALLER'])
            h.appendlist('hubspot.marketplace.user_id', str(self.mock_settings['USER']['ID']))
            h.appendlist('hubspot.marketplace.portal_id', str(portal_id))
            h.appendlist('hubspot.marketplace.app.name', self.mock_settings['APP']['NAME'])
            h.appendlist('hubspot.marketplace.app.callbackUrl', self.mock_settings['APP']['CALLBACK_URL'])
            h.appendlist('hubspot.marketplace.app.pageUrl', "TODO")
            h.appendlist('hubspot.marketplace.app.canvasUrl', "TODO")
            if self.signature:
                h.appendlist('hubspot.marketplace.signature', self.signature)

            request.marketplace = getattr(request, 'marketplace', {})
            request.marketplace['mock']= True


    def process_response(self, request, response):
        if request and request.marketplace and request.marketplace.get('mock',False) and response.status_code==200:
            if self.rebody.search(response.content):
                innards = self.rebody.findall(response.content)[0]
                head = ''
                for link in self.relink.findall(innards):
                    head += "\n<link %s />"%link
                bottom = ''
                for script in self.rescript.findall(innards):
                    bottom += "\n<script %s />"%script
                innards = self.relink.sub('',innards)
                innards = self.retitle.sub('',innards)
                innards = self.reform.sub(r'\1action="/market/%s/canvas/%s\2"'%(request.marketplace['portal']['id'],self.slug), innards)
                innards = self.reanchor.sub(r'\1href="/market/%s/canvas/%s\2"'%(request.marketplace['portal']['id'],self.slug), innards)
                content = self.wrapper
                content = content.replace('[[HEAD_CONTENTS]]',head)
                content = content.replace('[[BODY_CONTENTS]]',innards)
                content = content.replace('[[BOTTOM_BODY_CONTENTS]]',bottom)
                response.content = content
        return response


class MissingSlugError(NameError):
    """
HubSpot Marketplace Mock Canvas Slug hasn't been defined!

If you intend to use the MockCanvasMiddleware to aide your local development,
then you need to specify your slug in your settings:
    HUBSPOT_MARKETPLACE = { 
        'MOCK': { 'SLUG': 'your-hubspot-marketplace-app-slug' } 
    }

Or you can temporarily turn off the mocking middleware by deactivating this 
middleware in your settings:
    HUBSPOT_MARKETPLACE = { 
        'MOCK': { 'ACTIVATE': False } 
    }

Or, if you plan to never use it, then you need to remove 
'MockCanvasMiddleware' from your list of middlewares """

    def __init__(self, *args):
        NameError.__init__(self, self.__doc__)
        


def base64_url_decode_for_real(encoded_s):
    """ base64 library decided to leave '=' chars still kicking around, and was still bold enough to call their method 'urlsafe' -- okaaaaay...  This method is urlsafe for real, and matches what the marketplace is expecting """
    return base64.urlsafe_b64decode(encoded_s + '=' * (4 - len(encoded_s) % 4))

def base64_url_encode_for_real(decoded_s):
    """ base64 library decided to leave '=' chars still kicking around, and was still bold enough to call their method 'urlsafe' -- okaaaaay...  This method is urlsafe for real, and matches what the marketplace is expecting """
    return base64.urlsafe_b64encode(decoded_s).split('=',1)[0]

