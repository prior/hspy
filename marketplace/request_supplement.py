"""
The RequestSupplement object that will get injected on marketplace requests
"""

class RequestSupplement(object):
    # adding some duplicate fields keyed to more consistent python naming and
    # more understandable naming in some cases.  You're free to use whichever
    # you want.

    EXTRAS = { 
        'portal_id': 'hub_id',
        'app_pageUrl': 'local_url',
        'app_callbackUrl': 'local_base_url',
        'app_canvasUrl': 'base_url',
        'user_firstName': 'user_first_name',
        'user_lastName': 'user_last_name'
    }

    def __init__(self, request):
        super(RequestSupplement,self).__init__()
        self.process(request)

    def process(self, request):
        for k in request.REQUEST:
            if k.startswith('hubspot.marketplace.'):
                attr = '_'.join(k.split('.')[2:])
                val = request.REQUEST.get(k)
                if attr.endswith('_id'):
                    val = long(val)
                elif attr.startswith('is_'):
                    val = val.lower()=='true'
                setattr(self, attr, val)
        for k in self.__class__.EXTRAS:
            setattr(self,self.__class__.EXTRAS[k],getattr(self,k))


