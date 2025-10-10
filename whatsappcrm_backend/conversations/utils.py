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
        try:
            # If an event loop is already running (e.g., in Celery with eventlet),
            # schedule the async function on it.
            loop = asyncio.get_running_loop()
            loop.create_task(func(*args, **kwargs))
        except RuntimeError: # 'RuntimeError: There is no current event loop...'
            # If no event loop is running (e.g., in a standard Django sync view),
            # start a new one to run the async function.
            asyncio.run(func(*args, **kwargs))
    return wrapper