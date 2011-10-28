from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
import hashlib
import hmac
import base64
from marketplace import logger
from marketplace import RequestSupplement


class AuthMiddleware(object):
    """
Use this middleware to ensure requests are coming from HubSpot and that they
are intended for your app.  To use, you'll need to:

1) Place this class in your middlewares list in you settings.py

2) Let the middleware know about your secret, adding something like this to
your settings.py:

    HUBSPOT_MARKETPLACE_AUTH = { 
        'secret_key': 'hubspot-issued-secret-key-here' 
    }

This middleware assumes that you may also want to allow some non-HubSpot
Marketplace requests to pass through to your web app as well.  So, although
authentication is established at this layer, it isn't enforced unless you've
applied the @marketplace decorator on your view function.  And the code doesn't
enforce it until it executes that decorator (which happens after all the
middlewares have executed).
    """

    DEACTIVATION_NOTICE = """
HubSpot marketplace request authentication has been deactivated for all
requests!  (because there was no secret key specified in settings.py.  Gotta
specify there if you wanna turn on authentication!)
""".strip()

    SIGNATURE_KEY = 'hubspot.marketplace.signature'
            
    def __init__(self):
        super(AuthMiddleware, self).__init__()
        self.log = logger.get_log(__name__)
        auth = getattr(settings, 'HUBSPOT_MARKETPLACE_AUTH', {})
        self.secret = auth.get('secret_key')
        if not self.secret:
            self.log.warn(self.__class__.DEACTIVATION_NOTICE)
            raise MiddlewareNotUsed

    def process_request(self, request):
        """adds MarketPlaceInfo object to request at request.marketplace"""
        signature = request.REQUEST.get(self.__class__.SIGNATURE_KEY, '').strip()
        if self.is_request_authentic(signature):
            request.marketplace = RequestSupplement(request)

    def is_request_authentic(self, signature):
        """ensures this request was issued by HubSpot"""
        signature = str(signature)  # convert from unicode
        digest, payload = [
                self.base64_url_decode_for_real(s) 
                    for s in (signature+'.').split('.')[0:2]]
        return (digest and payload and 
                digest == hmac.new(self.secret, payload, hashlib.sha1).digest())


    def base64_url_decode_for_real(self, encoded_s):
        """
        base64 library decided to leave '=' chars still kicking around, and was
        still bold enough to call their method 'urlsafe' -- okaaaaay...  This
        method is urlsafe for real, and matches what the marketplace is
        expecting 
        """
        return base64.urlsafe_b64decode(encoded_s + '=' * (4 - len(encoded_s) % 4))


