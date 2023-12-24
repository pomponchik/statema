from functools import wraps
from inspect import iscoroutinefunction


def exception_escaping(function):
    """
    Декоратор для подавления любых исключений.
    """
    @wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except:
            pass
    @wraps(function)
    async def async_wrapper(*args, **kwargs):
        try:
            return await function(*args, **kwargs)
        except:
            pass
    if iscoroutinefunction(function):
        return async_wrapper
    return wrapper
