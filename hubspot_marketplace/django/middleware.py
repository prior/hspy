from django.conf import settings
from django.http import HttpResponse
from django.core.exceptions import MiddlewareNotUsed
import base64
import hashlib
import hmac

import logging
logger = logging.getLogger(__name__)


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
        self.secret = auth_settings.get('SECRET_KEY', None) or ''
        logger.info('HubSpot Marketplace Request Authentication Activated')
        if not self.secret:
            raise MissingSecretError

    def process_request(self, request):
        signature = request.REQUEST.get('hubspot.marketplace.signature', None) or ''
        if not self.is_request_authentic(signature):
            logger.error("\n  This request did not have a proper HubSpot Marketplace authentication signature!\n  It was either missing, malformed, or wrong.\n  Perhaps your SECRET_KEY is set to an incorrect value?\n  Or, perhaps this request did not originate from HubSpot!?\n  Returning a 401 for this request.")
            return HttpResponse(status=401)

    def is_request_authentic(self, signature):
        signature = str(signature) or ''  # convert from unicode
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

