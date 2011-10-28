import re
import os
from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from marketplace import logger


class ErrorGogglesMiddleware(object):
    """
Use this middleware to make django error stack traces show up properly inside
the marketplace wrapper.  If you've ever had to deal with a stack trace
without this middleware, you know it can get very hard to decipiher what the
issue is.

This middleware will only attempt to reformat for the marketplace when the
django app is in DEBUG mode.  Otherwise it won't attempt anything
    """


    def __init__(self):
        super(ErrorGogglesMiddleware,self).__init__()
        self.log = logger.get_log(__name__)
        debug_mode = getattr(settings, 'DEBUG', False)
        if not debug_mode:
            self.log.info('ErrorGogglesMiddleware has been turned off for all requests because we are not in DEBUG mode')
            raise MiddlewareNotUsed
        self.head_re = re.compile(r'<head>(.*?)</head>',re.DOTALL)
        self.body_re = re.compile(r'<body>(.*?)</body>',re.DOTALL)
        self.style_re = re.compile(r'<style type="text/css">(.*?)</style>', re.DOTALL)
        self.script_re = re.compile(r'<script type="text/javascript">(.*?)</script>', re.DOTALL)
        self.reset_styles = open(os.path.join(os.path.dirname(__file__),'error_goggles_reset.css')).read()
        self.log.info('ErrorGogglesMiddleware has been activated')

    def process_response(self, request, response):
        marketplace = request and getattr(request, 'marketplace', None)
        if marketplace and response.status_code >= 400:
            if self.head_re.search(response.content) and self.body_re.search(response.content):
                head = self.head_re.findall(response.content)[0]
                body = self.body_re.findall(response.content)[0]
                body = '<div class="hsmpdjerr">%s</div>' % body
                for style in self.style_re.findall(head):
                    body = '<style type="text/css">%s</style>'%style + body
                body = '<style type="text/css">%s</style>'%self.reset_styles + body
                for script in self.script_re.findall(head):
                    body = '<script type="text/javascript">%s</script>' % script + body
                response.content = self.body_re.sub('<body>%s</body>'%body, response.content)
        return response


