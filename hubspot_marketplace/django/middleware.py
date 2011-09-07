from django.conf import settings
from django.http import HttpResponse
from django.core.exceptions import MiddlewareNotUsed
import base64
import hashlib
import hmac

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
        auth_settings = getattr(settings, 'HUBSPOT_MARKETPLACE', {}).get('AUTH', {})
        if not auth_settings.get('ACTIVATE', True):
            logger.info('HubSpot Marketplace Request Authentication Deactivated')
            raise MiddlewareNotUsed
        self.secret = auth_settings.get('SECRET_KEY', None)
        logger.info('HubSpot Marketplace Request Authentication Activated')
        if not self.secret:
            raise MissingSecretError

    def process_request(self, request):
        request.marketplace = {'authenticated': False}
        signature = request.REQUEST.get('hubspot.marketplace.signature', None) or ''
        if self.is_request_authentic(signature):
            #TODO: could make this more general and flexible as new things are added and maybe other things are removed, but would still like to force common capitalization/underscore rules
            request.marketplace['authenticated'] = True
            request.marketplace['caller'] = request.REQUEST.get('hubspot.marketplace.caller', None)
            request.marketplace['portal_id'] = request.REQUEST.get('hubspot.marketplace.portal_id', None)
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
        digest, payload = [b64_url_decode(item) for item in (signature+'.').split('.')[0:2]]
        return digest and payload and digest == hmac.new(self.secret, payload, hashlib.sha1).digest()


class MissingSecretError(NameError):
    """
HubSpot Marketplace Secret hasn't been defined!

If you intend to use the AuthenticateRequestMiddleware, then you need to 
specify a secret in your settings:
    HUBSPOT_MARKETPLACE = { 
        'AUTH': { 'SECRET_KEY': 'hubspot-issued-secret-key-here' } 
    }

Or you can temporarily turn it off by deactivating this middleware in your
settings:
    HUBSPOT_MARKETPLACE = { 
        'AUTH': { 'ACTIVATE': False } 
    }

Or, if you plan to never use it, then you need to remove 
'AuthenticateRequestMiddleware' from your list of middlewares """

    def __init__(self, *args):
        NameError.__init__(self, self.__doc__)


def b64_url_decode(encoded_s):
    return base64.urlsafe_b64decode(encoded_s + '=' * (4 - len(encoded_s) % 4))

