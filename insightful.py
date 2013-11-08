#

"""Insightful is designed to be a debugging patch - slap it onto a
malfunctioning class or instance and it will spew out every interaction with
it. Gain some insight."""

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
        self.target = target
        self.function_calls = function_calls
        self.attribute_access = attribute_access
        self.attribute_assignment = attribute_assignment
        self.attribute_deletion = attribute_deletion
        self.show_method_access = show_method_access
        self.prefix = prefix
        self.original_getattribute = None
        self.original_setattr = None
        self.original_delattr = None
        self.stack = []
        self.done = False

    def _print(self, message):
        print("{}{}".format(self.prefix, message))

    def __enter__(self):
        self.original_getattribute = self.target.__getattribute__
        self.original_setattr = self.target.__setattr__
        self.original_delattr = self.target.__delattr__

        if self.function_calls or self.attribute_access:
            @wraps(self.original_getattribute)
            def getattribute_wrapper(instance_self, name):
                description = "{}.{}".format(instance_self, name)
                self.stack.append(description)
                value = self.original_getattribute(instance_self, name)
                self.stack.pop()
                if (hasattr(value, "__self__") and
                        value.__self__ is instance_self):
                    if self.show_method_access:
                        self._print("{} -> {}".format(description, value))
                    if self.function_calls:
                        return self.call_decorator(instance_self, value)
                else:
                    if self.attribute_access:
                        self._print("{} -> {}".format(description, value))
                return value
            self.target.__getattribute__ = getattribute_wrapper

        if self.attribute_assignment:
            @wraps(self.original_setattr)
            def setattr_wrapper(instance_self, name, value):
                description = "{}.{} = {}".format(instance_self, name, value)
                self.stack.append(description)
                self.original_setattr(instance_self, name, value)
                self.stack.pop()
                self._print(description)
            self.target.__setattr__ = setattr_wrapper

        if self.attribute_deletion:
            @wraps(self.original_delattr)
            def delattr_wrapper(instance_self, name):
                description = "del {}.{}".format(instance_self, name)
                self.stack.append(description)
                self.original_delattr(instance_self, name)
                self.stack.pop()
                self._print(description)
            self.target.__delattr__ = delattr_wrapper

    def call_decorator(self, instance_self, function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            if self.done:
                return function(*args, **kwargs)
            arguments = inspect.getcallargs(function, *args, **kwargs)
            names, varargs, keywords, defaults = inspect.getargspec(
                function.__func__)
            description = "{}.{}{}".format(
                instance_self, function.__name__,
                inspect.formatargvalues(names, varargs, keywords, arguments))
            self.stack.append(description)
            value = function(*args, **kwargs)
            self.stack.pop()
            self._print("{} -> {}".format(description, value))
            return value
        return wrapper

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            stack = iter(self.stack)
            first = next(stack)
            self._print("{}: {}".format(exc_type.__name__, exc_val))
            self._print("  during: {}".format(first))
            for frame in stack:
                self._print("  during: {}".format(frame))
        self.done = True
        self.target.__getattribute__ = self.original_getattribute
        self.target.__setattr__ = self.original_setattr
        self.target.__delattr__ = self.original_delattr