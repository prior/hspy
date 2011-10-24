from django.conf import settings
from django.http import HttpResponse
import logger

"""
View method decorators relevant to the hubspot marketplace
"""


AUTH_ERROR = """
This request did not have a proper HubSpot Marketplace authentication
signature!

This particular view was decorated so as to expect a valid HubSpot Marketplace
signature, however, the signature on this request was either missing,
malformed, or wrong.

Perhaps you incorrectly decorated this view as a marketplace view?  Or, perhaps
this request did not originate from HubSpot!?

If you're running locally, use the MockMiddleware to mock out all the
interactions you would be having with the marketplace in Production.  This will
give you the closest experience to riding the marketplace during your local
development.
""".strip()


def marketplace(function=None):
    """
    Use this decorator when you want to ensure marketplace authentication
    """

    def _dec(view_func):
        def _view(request, *args, **kwargs):
            authenticate = getattr(settings, 'HUBSPOT_MARKETPLACE_AUTH', {}).get('SECRET_KEY', False)
            if authenticate and not getattr(request, 'marketplace', None):
                logger.get_log('marketplace_decorator').error(AUTH_ERROR)
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

