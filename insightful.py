#

"""Insightful is designed to be a debugging patch - slap it onto a
malfunctioning class or instance and it will spew out every interaction with
it. Gain some insight."""

from contextlib import contextmanager
from functools import wraps
import inspect


class Insight:
    """A context manager that prints any interactions with a given instance or
    any instance of a given class within the enclosed code.

    This works by injecting `__getattribute__()`, `__setattr__()` and
    `__delattr__()` methods, and decorating functions. This means that it will
     not notify you about certain magic methods that bypass normal lookup."""
    def __init__(self, target,
                 function_calls=True,
                 attribute_access=True,
                 attribute_assignment=True,
                 attribute_deletion=True,
                 show_method_access=False,
                 prefix="Insight: "):
        """
        :param target: The class or instance to provide insight into.
        :param function_calls: Whether to log function calls.
        :param attribute_access: Whether to log attribute access.
        :param attribute_assignment: Whether to log attribute assignment.
        :param attribute_deletion: Whether to log attribute deletion.
        :param show_method_access: Whether to log method access - it is
                                   impossible to determine if the accessor means
                                   to call the method or not, so it is assumed
                                   they do and the access itself doesn't need to
                                   be logged. If you need to know about method
                                   accesses, rather than just calls, set to
                                   True.
        :param prefix: The prefix for all output.
        """
        if isinstance(target, type):
            self.target = target
            self.instance = None
        else:
            self.target = type(target)
            self.instance = target
        self.function_calls = function_calls
        self.attribute_access = attribute_access
        self.attribute_assignment = attribute_assignment
        self.attribute_deletion = attribute_deletion
        self.show_method_access = show_method_access
        self.prefix = prefix
        self.original_getattribute = None
        self.original_setattr = None
        self.original_delattr = None
        self._stack = []
        self._done = False
        self._guarded = False

    def _print(self, message):
        print("{}{}".format(self.prefix, message))

    def _fast_track(self, instance_self):
        return self._guarded or (self.instance is not None
                                 and self.instance is not instance_self)

    @contextmanager
    def _recursion_guard(self):
        self._guarded = True
        yield
        self._guarded = False

    def __enter__(self):
        self.original_getattribute = self.target.__getattribute__
        self.original_setattr = self.target.__setattr__
        self.original_delattr = self.target.__delattr__

        if self.function_calls or self.attribute_access:
            @wraps(self.original_getattribute)
            def getattribute_wrapper(instance, name):
                if self._fast_track(instance):
                    return self.original_getattribute(instance, name)
                with self._recursion_guard():
                    instance_repr = self.target.__repr__(instance)
                    description = "{}.{}".format(instance_repr, name)
                    self._stack.append(description)
                value = self.original_getattribute(instance, name)
                with self._recursion_guard():
                    self._stack.pop()
                    if (hasattr(value, "__self__") and
                            value.__self__ is instance):
                        if self.show_method_access:
                            self._print("{} -> {}".format(description, value))
                        if self.function_calls:
                            return self.call_decorator(instance_repr, value)
                    else:
                        if self.attribute_access:
                            self._print("{} -> {}".format(description, value))
                    return value
            self.target.__getattribute__ = getattribute_wrapper

        if self.attribute_assignment:
            @wraps(self.original_setattr)
            def setattr_wrapper(instance, name, value):
                if self._fast_track(instance):
                    return self.original_setattr(instance, name)
                with self._recursion_guard():
                    instance_repr = self.target.__repr__(instance)
                    description = "{}.{} = {}".format(instance_repr, name, value)
                    self._stack.append(description)
                self.original_setattr(instance, name, value)
                with self._recursion_guard():
                    self._stack.pop()
                    self._print(description)
            self.target.__setattr__ = setattr_wrapper

        if self.attribute_deletion:
            @wraps(self.original_delattr)
            def delattr_wrapper(instance, name):
                if self._fast_track(instance):
                    return self.original_delattr(instance, name)
                with self._recursion_guard():
                    instance_repr = self.target.__repr__(instance)
                    description = "del {}.{}".format(instance_repr, name)
                    self._stack.append(description)
                self.original_delattr(instance, name)
                with self._recursion_guard():
                    self._stack.pop()
                    self._print(description)
            self.target.__delattr__ = delattr_wrapper

    def call_decorator(self, instance_repr, function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            if self._done:
                return function(*args, **kwargs)
            with self._recursion_guard():
                arguments = inspect.getcallargs(function, *args, **kwargs)
                names, varargs, keywords, defaults = inspect.getargspec(
                    function.__func__)
                description = "{}.{}{}".format(
                    instance_repr, function.__name__,
                    inspect.formatargvalues(names, varargs, keywords, arguments))
                self._stack.append(description)
            value = function(*args, **kwargs)
            with self._recursion_guard():
                self._stack.pop()
                self._print("{} -> {}".format(description, value))
                return value
        return wrapper

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            stack = iter(self._stack)
            first = next(stack)
            self._print("{}: {}".format(exc_type.__name__, exc_val))
            self._print("  during: {}".format(first))
            for frame in stack:
                self._print("  during: {}".format(frame))
        self._done = True
        self.target.__getattribute__ = self.original_getattribute
        self.target.__setattr__ = self.original_setattr
        self.target.__delattr__ = self.original_delattr