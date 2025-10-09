# conversations/utils.py

import asyncio
from functools import wraps

def async_signal_handler(func):
    """
    Decorator to run an async signal handler from a sync context.
    This is useful for Django signals that need to call async functions.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        asyncio.run(func(*args, **kwargs))
    return wrapper