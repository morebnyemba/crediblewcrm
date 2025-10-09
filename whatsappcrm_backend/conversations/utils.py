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
        # FIX: asyncio.run() cannot be called from a running event loop (like eventlet's).
        # Instead, get the current loop and schedule the task on it.
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(func(*args, **kwargs))
        except RuntimeError: # 'RuntimeError: There is no current event loop...'
            # If no loop is running, we can safely start one.
            asyncio.run(func(*args, **kwargs))
    return wrapper