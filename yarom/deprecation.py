from __future__ import print_function
import six
import warnings
import functools


class deprecated(object):

    def __init__(self, message_or_callable=None):
        if isinstance(message_or_callable, six.string_types):
            self.message = message_or_callable
            self.func = None
        else:
            self.func = message_or_callable
            self.message = None

    def __call__(self, *args, **kwargs):
        '''This is a decorator which can be used to mark functions
        as deprecated. It will result in a warning being emitted
        when the function is used.'''
        if self.message:
            func = args[0]

            @functools.wraps(func)
            def new_func(*args, **kwargs):
                self.warn(func, self.message)
                return func(*args, **kwargs)
            return new_func
        else:
            self.warn(self.func)
            return self.func(*args, **kwargs)

    def warn(self, func, message=None):
        warnings.warn_explicit(
                    "Call to deprecated function {}{}".format(
                        func.__name__, "."
                        if message is None else ": " + str(message)),
                    category=DeprecationWarning,
                    filename=func.func_code.co_filename,
                    lineno=func.func_code.co_firstlineno + 1)


if __name__ == '__main__':
    @deprecated("The MESSAGE")
    def my_func():
        print("yelp")

    @deprecated
    def mu_func():
        print("yolp")

    my_func()
    mu_func()
