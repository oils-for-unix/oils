#!/usr/bin/env python2
from __future__ import print_function
"""Test functions etc, for Byterun."""

import unittest

import six

import vmtest

PY3 = six.PY3


class TestFunctions(vmtest.VmTestCase):
    def test_functions(self):
        self.assert_ok("""\
            def fn(a, b=17, c="Hello", d=[]):
                d.append(99)
                print(a, b, c, d)
            fn(1)
            fn(2, 3)
            fn(3, c="Bye")
            fn(4, d=["What?"])
            fn(5, "b", "c")
            """)

    def test_recursion(self):
        self.assert_ok("""\
            def fact(n):
                if n <= 1:
                    return 1
                else:
                    return n * fact(n-1)
            f6 = fact(6)
            print(f6)
            assert f6 == 720
            """)

    def test_nested_names(self):
        self.assert_ok("""\
            def one():
                x = 1
                def two():
                    x = 2
                    print(x)
                two()
                print(x)
            one()
            """)

    def test_calling_functions_with_args_kwargs(self):
        self.assert_ok("""\
            def fn(a, b=17, c="Hello", d=[]):
                d.append(99)
                print(a, b, c, d)
            fn(6, *[77, 88])
            fn(**{'c': 23, 'a': 7})
            fn(6, *[77], **{'c': 23, 'd': [123]})
            """)

    def test_defining_functions_with_args_kwargs(self):
        self.assert_ok("""\
            def fn(*args):
                print("args is %r" % (args,))
            fn(1, 2)
            """)
        self.assert_ok("""\
            def fn(**kwargs):
                print("kwargs is %r" % (kwargs,))
            fn(red=True, blue=False)
            """)
        self.assert_ok("""\
            def fn(*args, **kwargs):
                print("args is %r" % (args,))
                print("kwargs is %r" % (kwargs,))
            fn(1, 2, red=True, blue=False)
            """)
        self.assert_ok("""\
            def fn(x, y, *args, **kwargs):
                print("x is %r, y is %r" % (x, y))
                print("args is %r" % (args,))
                print("kwargs is %r" % (kwargs,))
            fn('a', 'b', 1, 2, red=True, blue=False)
            """)

    def test_defining_functions_with_empty_args_kwargs(self):
        self.assert_ok("""\
            def fn(*args):
                print("args is %r" % (args,))
            fn()
            """)
        self.assert_ok("""\
            def fn(**kwargs):
                print("kwargs is %r" % (kwargs,))
            fn()
            """)
        self.assert_ok("""\
            def fn(*args, **kwargs):
                print("args is %r, kwargs is %r" % (args, kwargs))
            fn()
            """)

    def test_partial(self):
        self.assert_ok("""\
            from _functools import partial

            def f(a,b):
                return a-b

            f7 = partial(f, 7)
            four = f7(3)
            assert four == 4
            """)

    def test_partial_with_kwargs(self):
        self.assert_ok("""\
            from _functools import partial

            def f(a,b,c=0,d=0):
                return (a,b,c,d)

            f7 = partial(f, b=7, c=1)
            them = f7(10)
            assert them == (10,7,1,0)
            """)

    def test_wraps(self):
        self.assert_ok("""\
            from functools import wraps
            def my_decorator(f):
                dec = wraps(f)
                def wrapper(*args, **kwds):
                    print('Calling decorated function')
                    return f(*args, **kwds)
                wrapper = dec(wrapper)
                return wrapper

            @my_decorator
            def example():
                '''Docstring'''
                return 17

            assert example() == 17
            """)


class TestClosures(vmtest.VmTestCase):
    def test_closures(self):
        self.assert_ok("""\
            def make_adder(x):
                def add(y):
                    return x+y
                return add
            a = make_adder(10)
            print(a(7))
            assert a(7) == 17
            """)

    def test_closures_store_deref(self):
        self.assert_ok("""\
            def make_adder(x):
                z = x+1
                def add(y):
                    return x+y+z
                return add
            a = make_adder(10)
            print(a(7))
            assert a(7) == 28
            """)

    def test_closures_in_loop(self):
        self.assert_ok("""\
            def make_fns(x):
                fns = []
                for i in range(x):
                    fns.append(lambda i=i: i)
                return fns
            fns = make_fns(3)
            for f in fns:
                print(f())
            assert (fns[0](), fns[1](), fns[2]()) == (0, 1, 2)
            """)

    def test_closures_with_defaults(self):
        self.assert_ok("""\
            def make_adder(x, y=13, z=43):
                def add(q, r=11):
                    return x+y+z+q+r
                return add
            a = make_adder(10, 17)
            print(a(7))
            assert a(7) == 88
            """)

    def test_deep_closures(self):
        self.assert_ok("""\
            def f1(a):
                b = 2*a
                def f2(c):
                    d = 2*c
                    def f3(e):
                        f = 2*e
                        def f4(g):
                            h = 2*g
                            return a+b+c+d+e+f+g+h
                        return f4
                    return f3
                return f2
            answer = f1(3)(4)(5)(6)
            print(answer)
            assert answer == 54
            """)


class TestGenerators(vmtest.VmTestCase):
    def test_first(self):
        self.assert_ok("""\
            def two():
                yield 1
                yield 2
            for i in two():
                print(i)
            """)

    def test_partial_generator(self):
        self.assert_ok("""\
            from _functools import partial

            def f(a,b):
                num = a+b
                while num:
                    yield num
                    num -= 1

            f2 = partial(f, 2)
            three = f2(1)
            assert list(three) == [3,2,1]
            """)

    def test_yield_multiple_values(self):
        self.assert_ok("""\
            def triples():
                yield 1, 2, 3
                yield 4, 5, 6

            for a, b, c in triples():
                print(a, b, c)
            """)

    def test_simple_generator(self):
        self.assert_ok("""\
            g = (x for x in [0,1,2])
            print(list(g))
            """)

    def test_generator_from_generator(self):
        self.assert_ok("""\
            g = (x*x for x in range(5))
            h = (y+1 for y in g)
            print(list(h))
            """)

    def test_generator_from_generator2(self):
        self.assert_ok("""\
            class Thing(object):
                RESOURCES = ('abc', 'def')
                def get_abc(self):
                    return "ABC"
                def get_def(self):
                    return "DEF"
                def resource_info(self):
                    for name in self.RESOURCES:
                        get_name = 'get_' + name
                        yield name, getattr(self, get_name)

                def boom(self):
                    #d = list((name, get()) for name, get in self.resource_info())
                    d = [(name, get()) for name, get in self.resource_info()]
                    return d

            print(Thing().boom())
            """)

    if PY3: # PY3.3+ only
        def test_yield_from(self):
            self.assert_ok("""\
                def main():
                    x = outer()
                    next(x)
                    y = x.send("Hello, World")
                    print(y)

                def outer():
                    yield from inner()

                def inner():
                    y = yield
                    yield y

                main()
                """)

        def test_yield_from_tuple(self):
            self.assert_ok("""\
                def main():
                    for x in outer():
                        print(x)

                def outer():
                    yield from (1, 2, 3, 4)

                main()
                """)

        def test_distinguish_iterators_and_generators(self):
            self.assert_ok("""\
                class Foo(object):
                    def __iter__(self):
                        return FooIter()

                class FooIter(object):
                    def __init__(self):
                        self.state = 0

                    def __next__(self):
                        if self.state >= 10:
                            raise StopIteration
                        self.state += 1
                        return self.state

                    def send(self, n):
                        print("sending")

                def outer():
                    yield from Foo()

                for x in outer():
                    print(x)
                """)

        def test_nested_yield_from(self):
            self.assert_ok("""\
                def main():
                    x = outer()
                    next(x)
                    y = x.send("Hello, World")
                    print(y)

                def outer():
                    yield from middle()

                def middle():
                    yield from inner()

                def inner():
                    y = yield
                    yield y

                main()
                """)

        def test_return_from_generator(self):
            self.assert_ok("""\
                def gen():
                    yield 1
                    return 2

                x = gen()
                while True:
                    try:
                        print(next(x))
                    except StopIteration as e:
                        print(e.value)
                        break
            """)

        def test_return_from_generator_with_yield_from(self):
            self.assert_ok("""\
                def returner():
                    if False:
                        yield
                    return 1

                def main():
                    y = yield from returner()
                    print(y)

                list(main())
            """)


if __name__ == '__main__':
    unittest.main()
