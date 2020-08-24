import functools
import logging
import warnings
import os
import sys

# _srcfile is used when walking the stack to check when we've got the first
# caller stack frame.
#
if hasattr(sys, 'frozen'):  # support for py2exe
    _srcfile = "logging%s__init__%s" % (os.sep, __file__[-4:])
elif __file__[-4:].lower() in ['.pyc', '.pyo']:
    _srcfile = __file__[:-4] + '.py'
else:
    _srcfile = __file__
_srcfile = os.path.normcase(_srcfile)


class IceLogger(object):
    def __init__(self, **kwargs):
        self.logger = logging.getLogger('db')
        self.raise_warnings = kwargs.pop('raise_warnings', False)
        self.bot_username = kwargs.pop('username', 'no_username_provided')
        self.extras = kwargs

    def log(self, level, message, *args, **kwargs):
        extra = self.extras.copy()
        extra.update(kwargs.pop('extra', {}))
        extra.update({
            'bot_username': self.bot_username
        })
        kwargs['extra'] = extra
        self._log(level, message, args, **kwargs)

    def debug(self, message, *args, **kwargs):
        return self.log(logging.DEBUG, message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        return self.log(logging.INFO, message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        """
        Specialized warnings system. If a warning subclass is passed into
        the keyword arguments and raise_warnings is True - the warning will
        be passed to the warnings module.
        """
        warn_cls = kwargs.pop('warning', None)
        if warn_cls and self.raise_warnings:
            warnings.warn(message, warn_cls)

        return self.log(logging.WARNING, message, *args, **kwargs)

    # Alias warn to warning
    warn = warning

    def error(self, message, *args, **kwargs):
        return self.log(logging.ERROR, message, *args, **kwargs)

    def critical(self, message, *args, **kwargs):
        return self.log(logging.CRITICAL, message, *args, **kwargs)

    def _log(self, level, msg, args, exc_info=None, extra=None):
        """
        Low-level logging routine which creates a LogRecord and then calls
        all the handlers of this logger to handle the record.
        """
        # Add wrapping functionality here.
        if _srcfile:
            # IronPython doesn't track Python frames, so findCaller throws an
            # exception on some versions of IronPython. We trap it here so that
            # IronPython can use logging.
            try:
                fn, lno, func = self.findCaller()
            except ValueError:
                fn, lno, func = "(unknown file)", 0, "(unknown function)"
        else:
            fn, lno, func = "(unknown file)", 0, "(unknown function)"
        if exc_info:
            if not isinstance(exc_info, tuple):
                exc_info = sys.exc_info()
        record = self.logger.makeRecord(
            self.logger.name, level, fn, lno, msg, args, exc_info, func, extra)
        self.logger.handle(record)

    def findCaller(self):
        """
        Find the stack frame of the caller so that we can note the source
        file name, line number and function name.
        """
        f = logging.currentframe()
        # On some versions of IronPython, currentframe() returns None if
        # IronPython isn't run with -X:Frames.
        if f is not None:
            f = f.f_back
        rv = "(unknown file)", 0, "(unknown function)"
        while hasattr(f, "f_code"):
            co = f.f_code
            filename = os.path.normcase(co.co_filename)
            if filename == _srcfile:
                f = f.f_back
                continue
            rv = (co.co_filename, f.f_lineno, co.co_name)
            break
        return rv


class LogDecorator(object):
    def __init__(self):
        self.logger = logging.getLogger('decorator')

    def __call__(self, fn):
        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            try:
                self.logger.debug("{0} - {1} - {2}".format(fn.__name__, args, kwargs))
                result = fn(*args, **kwargs)
                self.logger.debug("{0} - return: {1}".format(fn.__name__, result))
                return result
            except Exception as ex:
                self.logger.debug("{0} - Exception: {1}".format(fn.__name__, ex))
                raise ex
        return decorated
