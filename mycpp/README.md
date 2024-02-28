mycpp
=====
 
This is an experimental Python-to-C++ translator based on MyPy.  It only
handles the small subset of Python that Oil uses.

It's inspired by both mypyc and Shed Skin.  These posts give background:

- [Brief Descriptions of a Python to C++ Translator](https://www.oilshell.org/blog/2022/05/mycpp.html)
- [Oil Is Being Implemented "Middle Out"](https://www.oilshell.org/blog/2022/03/middle-out.html)

## Instructions

### Translating and Compiling `oil-native`

Running `mycpp` is best done on a Debian / Ubuntu-ish machine.  Follow the
instructions at <https://github.com/oilshell/oil/wiki/Contributing> to create
the "dev build" first, which is DISTINCT from the C++ build.  Make sure you can
run:

    oil$ build/py.sh all

This will give you a working shell:

    oil$ bin/osh -c 'echo hi'  # running interpreted Python
    hi

To run mycpp, we will build Python 3.10, clone MyPy, and install MyPy's
dependencies.  First install packages:

    # We need libssl-dev, libffi-dev, zlib1g-dev to bootstrap Python
    oil$ build/deps.sh install-ubuntu-packages

Then fetch data, like the Python 3.10 tarball and MyPy repo:

    oil$ build/deps.sh fetch

Then build from source:

    oil$ build/deps.sh install-wedges

To build oil-native, use:

    oil$ ./NINJA-config.sh
    oil$ ninja              # translate and compile, may take 30 seconds

    oil$ _bin/cxx-asan/osh -c 'echo hi'  # running compiled C++ !
    hi

To run the tests and benchmarks:

    oil$ mycpp/TEST.sh test-translator
    ... 200+ tasks run ...

If you have problems, post a message on `#oil-dev` at
`https://oilshell.zulipchat.com`.  Not many people have contributed to `mycpp`,
so I can use your feedback!

Related:

- [Oil Native Quick
Start](https://github.com/oilshell/oil/wiki/Oil-Native-Quick-Start) on the
wiki.
- [Oil Dev Cheat Sheet](https://github.com/oilshell/oil/wiki/Oil-Native-Quick-Start)

## Notes on the Algorithm / Architecture

There are four passes over the MyPy AST.

(1) `const_pass.py`: Collect string constants 

Turn turn the constant in `myfunc("foo")` into top-level `GLOBAL_STR(str1,
"foo")`.
  
(2) Three passes in `cppgen_pass.py`.

(a) Forward Declaration Pass.

    class Foo;
    class Bar;

This pass also determines which methods should be declared `virtual` in their
declarations.  The `virtual` keyword is written in the next pass.

(b) Declaration Pass.

    class Foo {
      void method();
    };
    class Bar {
      void method();
    };

More work in this pass:

- Collect member variables and write them at the end of the definition
- Collect locals for "hoisting".  Written in the next pass.
- Creates `fmtN()` functions to compile Python's `%` formatting operator.

(c) Definition Pass.

    void Foo:method() {
      ...
    }
    void Bar:method() {
      ...
    }

Note: I really wish we were not using visitors, but that's inherited from MyPy.

## WARNING: Assumptions Not Checked

### Global Constants Can't Be Mutated

We translate top level constants to statically initialized C data structures
(zero startup cost):

    gStr = 'foo'   
    gList = [1, 2]  # type: List[int]
    gDict = {'bar': 42}  # type: Dict[str, int]

Even though `List` and `Dict` are mutable in general, you should **NOT** mutate
these global instances!  The C++ code will break at runtime.

### Gotcha about Returning Variants (Subclasses) of a type

MyPy will accept this code:

```
if cond:
  sig = proc_sig.Open  # type: proc_sig_t
                       # bad because mycpp HOISTS this
else:
  sig = proc_sig.Closed.CreateNull()
  sig.words = words    # assignment fails
return sig
```

It will translate to C++, but fail to compile.  Instead, rewrite it like this:

```
sig = None  # type: proc_sig_t
if cond:
  sig = proc_sig.Open  # type: proc_sig_t
                       # bad because mycpp HOISTS this
else:
  closed = proc_sig.Closed.CreateNull()
  closed.words = words    # assignment fails
  sig = closed
return sig
```

### Exceptions Can't Leave Destructors / Python `__exit__`

Context managers like `with ctx_Foo():` translate to C++ constructors and
destructors.

In C++, a destructor can't "leave" an exception.  It results in a runtime error.

You can throw and CATCH an exception WITHIN a destructor, but you can't let it
propagate outside.

This means you must be careful when coding the `__exit__` method.  For example,
in `vm::ctx_Redirect`, we had this bug due to `IOError` being thrown and not
caught when restoring/popping redirects.

To fix the bug, we rewrote the code to use an out param
`List[IOError_OSError]`.

Related:

- <https://akrzemi1.wordpress.com/2011/09/21/destructors-that-throw/>

## More Translation Notes

### "Creative Hacks"

- `with tagswitch(d) as case` &rarr; `switch / case`
  - We don't have Python 3 pattern matching
- Scope-based resource management
  - `with ctx_Foo(...)` &rarr; C++ constructors and destructors

### Major Features

- `callable(arg)` to either &rarr;
  - function call `f(arg)`
  - instantiation `Alloc<T>(arg)`
- `name.attr` to either &rarr;
  - `obj->member`
  - `module::Func`
- Python `int` and `bool` &rarr; C++ `int` and `bool`
  - `None` &rarr; `nullptr`
- Statically Typed Python Collections
  - `str` &rarr; `Str*`
  - `List[T]` &rarr; `List<T>*`
  - `Dict[K, V]` &rarr; `Dict<K, V>*`
  - tuples &rarr; `Tuple2<A, B>`, `Tuple3<A, B, C>`, etc.
- Collection literals turn into initializer lists
  - And there is a C++ type inference issue which requires an explicit
    `std::initializer_list<int>{1, 2, 3}`, not just `{1, 2, 3}`
- Python's polymorphic iteration &rarr; `StrIter`, `ListIter<T>`, `DictIter<K,
  V`
  - `d.iteritems()` is rewritten `mylib.iteritems()` &rarr; `DictIter`
    - TODO: can we be smarter about this?
  - `reversed(mylist)` &rarr; `ReverseListIter`
- Python's `in` operator:
  - `s in mystr` &rarr; `str_contains(mystr, s)`
  - `x in mylist` &rarr; `list_contains(mylist, x)`
- Classes and inheritance
  - `__init__` method becomes a constructor.  Note: initializer lists aren't
    used.
  - Detect `virtual` methods
  - TODO: could we detect `abstract` methods? (`NotImplementedError`)
- Python generators `Iterator[T]` &rarr; eager `List<T>` accumulators
- Python Exceptions &rarr; C++ exceptions
- Python Modules &rarr; C++ namespace (we assume a 2-level hierarchy)

### Minor Translations

- `s1 == s2` &rarr; `str_equals(s1, s2)`
- `'x' * 3` &rarr; `str_repeat(globalStr, 3)`
- `[None] * 3` &rarr; `list_repeat(nullptr, 3)`
- Omitted:
  - If the LHS of an assignment is `_`, then the statement is omitted
    - This is for `_ = log`, which shuts up Python lint warnings for 'unused
      import'
  - Code under `if __name__ == '__main__'`

### Optimizations

- Returning Tuples by value.  To reduce GC pressure, we we return
  `Tuple2<A, B>` instead of `Tuple2<A, B>*`, and likewise for `Tuple3` and `Tuple4`.

### Rooting Policy

The translated code roots local variables in every function

    StackRoots _r({&var1, &var2});

We have two kinds of hand-written code:

1. Methods like `Str::strip()` in `mycpp/` 
2. OS bindings like `stat()` in `cpp/` 

Neither of them needs any rooting!  This is because we use **manual collection
points** in the interpreter, and these functions don't call any functions that
can collect.  They are "leaves" in the call tree.

### Hard-Coded Names

These are signs of coupling between mycpp and Oil, which ideally shouldn't
exist.

- `mycpp_main.py`
  - `ModulesToCompile()` -- some files have to be ordered first, like the ASDL
    runtime.
    - TODO: Pea can respect parameter order?  So we do that outside the project?
    - Another ordering constraint comes from **inheritance**.  The forward
      declaration is NOT sufficient in that case.
- `cppgen_pass.py`
  - `_GetCastKind()` has some hard-coded names
  - `AsdlType::Create()` is special cased to `::`, not `->`
  - Default arguments e.g. `scope_e::Local` need a repeated `using`.

Issue on mycpp improvements: <https://github.com/oilshell/oil/issues/568>

## Limitations Requiring Source Rewrites

### Due to the Translation or C++ language

- C++ doesn't have `try / except / else`, or `finally`
  - This usually requires some rewriting
- `if mylist` tests if the pointer is non-NULL; use `if len(mylist)` for
  non-empty test
- Functions can have at most one keyword / optional argument.
  - We generate two methods: `f(x)` which calls `f(x, y)` with the default
    value of `y`
  - If there are two or more optional arguments:
    - For classes, you can use the "builder pattern", i.e. add an
      `Init_MyMember()` method
    - If the arguments are booleans, translate it to a single bitfield argument
- C++ has nested scope and Python has flat function scope.  Can cause name
  collisions.
  - Could enforce this if it becomes a problem

## C++

### Gotchas

- C++ classes can have 2 member variables of the same name!  From the base
  class and derived class.
- Failing to declare methods `virtual` can involve the wrong one being called
  at runtime

### Minor Features Used

In addition to classes, templates, exceptions, etc. mentioned above, we use:

- `static_cast` and `reinterpret_cast`
- `enum class` for ASDL
- Function overloading
  - For equality and hashing?
- `offsetof` for introspection of field positions for garbage collection
- `std::initializer_list` for `StackRoots()`
  - Should we get rid of this?

### Not Used

- I/O Streams, RTTI, etc.
- `const`
- Smart pointers

## Notes on the Runtime (`mylib`)

- A `Str` is immutable, and can be used as a key to a `Dict` (at the Python
  level), and thus an `AssocArray` (at the Oil level).
- A `BufWriter` is mutable.  It's an alias for `cStringIO.StringIO()`.  You
  build it with repeated calls to`write()`, and then call `getvalue()` at the
  end.
