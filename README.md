insightful
==========

A debugging patch - slap it into a malfunctioning class or instance and it will
spew out every interaction with it. It's not elegant, but it might help you
gain some insight.

```python
from insightful import Insight

class Test:
    def __init__(self):
        self.value = 0
        self.useless = 0

    def test(self):
        return 1

    def whoops(self, arg):
        raise Exception("Oh No!")

    @property
    def property(self):
        return self.test() + self.whoops(self.value)

    def __repr__(self):
        return "Test()"

test = Test()
with Insight(Test):
    test.value += 1
    test.test()
    del test.useless
    test.property

Insight: Test().value -> 0
Insight: Test().value = value
Insight: Test().test(self=Test()) -> 1
Insight: del Test().useless
Insight: Test().test(self=Test()) -> 1
Insight: Test().value -> 1
Insight: Exception: Oh No!
Insight:   during: Test().property
Insight:   during: Test().whoops(self=Test(), arg=1)
Traceback (most recent call last):
  File "/home/gareth/Development/insightful/insightful.py", line 150, in <module>
    test.property
  File "/home/gareth/Development/insightful/insightful.py", line 65, in getattribute_wrapper
    value = self.original_getattribute(instance_self, name)
  File "/home/gareth/Development/insightful/insightful.py", line 143, in property
    return self.test() + self.whoops(self.value)
  File "/home/gareth/Development/insightful/insightful.py", line 111, in wrapper
    value = function(*args, **kwargs)
  File "/home/gareth/Development/insightful/insightful.py", line 139, in whoops
    raise Exception("Oh No!")
Exception: Oh No!
```

You can customise what is reported when you construct the context manager:

```python
Insight(target, function_calls=True, attribute_access=True,
        attribute_assignment=True, attribute_deletion=True,
        show_method_access=False, prefix="Insight: ")
```

 * target: The class or instance to provide insight into.
 * function_calls: Whether to log function calls.
 * attribute_access: Whether to log attribute access.
 * attribute_assignment: Whether to log attribute assignment.
 * attribute_deletion: Whether to log attribute deletion.
 * show_method_access: Whether to log method access - it is
   impossible to determine if the accessor means to call the method or not, so
   it is assumed they do and the access itself doesn't need to be logged. If you
   need to know about method accesses, rather than just calls, set to True.
 * prefix: The prefix for all output.

This all works by injecting `__getattribute__()`, `__setattr__()` and
`__delattr__()` methods, and decorating functions. This means that it will not
notify you about certain magic methods that bypass normal lookup - most notably
`__init__()`.
