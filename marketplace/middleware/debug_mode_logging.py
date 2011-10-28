import traceback
from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from marketplace import logger


class DebugModeLoggingMiddleware(object):
    """
Use this middleware to force logging of errors even when Debug = True.  You'll
find this useful in the case that you have QA in DEBUG mode, and you'd still
like to log exceptions that show up there (not just to the screen, which is the
default behavior in DEBUG mode)

If you don't want to fiddle with your middlewares list in different
environments, you can just add this permanently, and then easily turn it off by
using this setting: 
DEBUG_MODE_LOGGING = False

You might find it useful to do that for local development, since it may get
annoying to wade through exception logs on your console when you're already
seeing every error on the screen.
    """

    def __init__(self):
        super(DebugModeLoggingMiddleware,self).__init__()
        self.log = logger.get_log(__name__)
        if not getattr(settings, 'DEBUG', False):
            self.log.info('DebugModeLoggingMiddleware has been turned off for all requests cuz we\'re not in debug mode')
            raise MiddlewareNotUsed
        if not getattr(settings, 'DEBUG_MODE_LOGGING', True):
            self.log.info('DebugModeLoggingMiddleware has been explicitly turned off for all requests')
            raise MiddlewareNotUsed
        self.log.info('DebugModeLoggingMiddleware has been activated')

    def process_exception(self, request, exception):
        if settings.DEBUG:
            self.log.error(traceback.format_exc(exception))

