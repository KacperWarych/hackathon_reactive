"""Serialize the one-process demo's import, index, entry and query operations.

Reentrant for service composition; this is deliberately not a multi-process lock.
"""
from functools import wraps
from threading import RLock

_OPERATION_LOCK = RLock()


def serialized_operation(function):
    @wraps(function)
    def guarded(*args, **kwargs):
        with _OPERATION_LOCK:
            return function(*args, **kwargs)
    return guarded
