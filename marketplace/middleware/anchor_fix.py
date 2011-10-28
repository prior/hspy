import re
#from marketplace import logger


class AnchorFixMiddleware(object):
    """
Use this middleware to make absolute paths in anchor tags be prepended with a
protocol relative url.  This can be used as a fix for the current marketplace
wonkiness where it doesn't rewrite absolute urls in an anchor tag

look here for more info:
http://docs.hubapi.com/wiki/Link_Rewriting

This middleware essentially turns the box pointed to by <a> and by "Absolute
Url" into something useful.
    """

    def __init__(self):
        super(AnchorFixMiddleware,self).__init__()
        self.anchor_re = re.compile(r'(<a\s.*?)href="(/.*?)"')

    def process_response(self, request, response):
        marketplace = request and getattr(request, 'marketplace', None)
        if marketplace and response.status_code==200:
            response.content = self.anchor_re.sub(r'\1href="%s\2"' %
                    marketplace.base_url[0:-1], response.content)
        return response



