from insightful import Insight


class Test:
    def __init__(self, name=""):
        self.value = 0
        self.useless = 0
        self.name = name

    def test(self):
        return 1

    def whoops(self, arg):
        raise Exception("Oh No!")

    @property
    def property(self):
        return self.test() + self.whoops(self.value)

    def __repr__(self):
        return "Test({})".format(self.name)


print("Example 1")
test = Test()
try:
    with Insight(Test):
        test.value += 1
        test.test()
        del test.useless
        test.property
except Exception:
    pass


print("\nExample 2")
testa = Test("a")
testb = Test("b")
print("All Test()s:")
with Insight(Test):
    testa.value
    testb.value
print("Only Test(a)s:")
with Insight(testa):
    testa.value
    testb.value


print("\nExample 3")
test = Test()
wont_work = test.test
with Insight(Test):
    will_work = test.test
    wont_work()
    will_work()
will_work()  # Not once outside of block.


print("\nExample 4")
test = Test()
print("Without showing method access:")
with Insight(Test):
    will_work = test.test
    test.test()
print("Showing method access:")
with Insight(Test, show_method_access=True):
    will_work = test.test
    test.test()