#==========================================================================================\\\
#=================================== tests/sample_module.py =============================\\\
#==========================================================================================\\\

"""Sample module for testing linkcode_resolve edge cases."""

import functools


def test_decorator_no_wraps(func):
    """Decorator that doesn't use functools.wraps."""
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def test_decorator_with_wraps(func):
    """Decorator that uses functools.wraps."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


@test_decorator_no_wraps
def decorated_no_wraps():
    """Function decorated without functools.wraps."""
    return "no_wraps"


@test_decorator_with_wraps
def decorated_with_wraps():
    """Function decorated with functools.wraps."""
    return "with_wraps"


class Klass:
    """Sample class for testing property and method resolution."""

    @property
    def prop(self):
        """A test property."""
        return 42

    @classmethod
    def class_m(cls):
        """A test classmethod."""
        return cls.__name__

    @staticmethod
    def static_m():
        """A test staticmethod."""
        return "static"


def simple_function():
    """A simple function for basic testing."""
    return "simple"