mycpp
=====
 
This is a Python-to-C++ translator based on MyPy.  It only
handles the small subset of Python that we use in Oils.

It's inspired by both mypyc and Shed Skin.  These posts give background:

- [Brief Descriptions of a Python to C++ Translator](https://www.oilshell.org/blog/2022/05/mycpp.html)
- [Oil Is Being Implemented "Middle Out"](https://www.oilshell.org/blog/2022/03/middle-out.html)

As of March 2024, the translation to C++ is **done**.  So it's no longer
experimental!

However, it's still pretty **hacky**.  This doc exists mainly to explain the
hacks.  (We may want to rewrite mycpp as "yaks", although it's low priority
right now.)

---

Source for this doc: [mycpp/README.md]($oils-src).  The code is all in
[mycpp/]($oils-src).


<div id="toc">
</div>

## Instructions

### Translating and Compiling `oils-cpp`

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

## mycpp Idioms / "Creative Hacks"

Oils is written in typed Python 2.  It will run under a stock Python 2
interpreter, and it will typecheck with stock MyPy.

However, there are a few language features that don't map cleanly from typed
Python to C++:

- switch statements (unfortunately we don't have the Python 3 match statement)
- C++ destructors - the RAII ptatern
- casting - MyPy has one kind of cast; C++ has `static_cast` and
  `reinterpret_cast`.  (We don't use C-style casting.)

So this describes the idioms we use.  There are some hacks in
[mycpp/cppgen_pass.py]($oils-src) to handle these cases, and also Python
runtime equivalents in `mycpp/mylib.py`.

### `with {,tag,str_}switch` &rarr; Switch statement

We have three constructs that translate to a C++ switch statement.  They use a
Python context manager `with Xswitch(obj) ...` as a little hack.

Here are examples like the ones in [mycpp/examples/test_switch.py]($oils-src).
(`ninja mycpp-logs-equal` translates, compiles, and tests all the examples.)

Simple switch:

    myint = 99
    with switch(myint) as case:
        if case(42, 43):
            print('forties')
        else:
            print('other')

Switch on **object type**, which goes well with ASDL sum types:

    val = value.Str('foo)  # type: value_t
    with tagswitch(val) as case:
        if case(value_e.Str, value_e.Int):
            print('string or int')
        else:
            print('other')

We usually need to apply the `UP_val` pattern here, described in the next
section.

Switch on **string**, which generates a fast **two-level dispatch** -- first on
length, and then with `str_equals_c()`:

    s = 'foo'
    with str_switch(s) as case:
        if case("foo")
            print('FOO')
        else:
            print('other')

### `val` &rarr; `UP_val` &rarr; `val` Downcasting pattern

Summary: variable names like `UP_*` are **special** in our Python code.

Consider the downcasts marked BAD:

    val = value.Str('foo)  # type: value_t

    with tagswitch(obj) as case:
        if case(value_e.Str):
            val = cast(value.Str, val)  # BAD: conflicts with first declaration
            print('s = %s' % val.s)

        elif case(value_e.Int):
            val = cast(value.Int, val)  # BAD: conflicts with both
            print('i = %d' % val.i)

        else:
            print('other')

MyPy allows this, but it translates to invalid C++ code.  C++ can't have a
variable named `val`, with 2 related types `value_t` and `value::Str`.

So we use this idiom instead, which takes advantage of **local vars in case
blocks** in C++:

    val = value.Str('foo')  # type: value_t

    UP_val = val  # temporary variable that will be casted

    with tagswitch(val) as case:
        if case(value_e.Str):
            val = cast(value.Str, UP_val)  # this works
            print('s = %s' % val.s)

        elif case(value_e.Int):
            val = cast(value.Int, UP_val)  # also works
            print('i = %d' % val.i)

        else:
            print('other')

This translates to something like:

    value_t* val = Alloc<value::Str>(str42);
    value_t* UP_val = val;

    switch (val->tag()) {
        case value_e::Str: {
            // DIFFERENT local var
            value::Str* val = static_cast<value::Str>(UP_val);
            print(StrFormat(str43, val->s))
        }
            break;
        case value_e::Int: {
            // ANOTHER DIFFERENT local var
            value::Int* val = static_cast<value::Int>(UP_val);
            print(StrFormat(str44, val->i))
        }
            break;
        default:
            print(str45);
    }

This works because there's no problem having **different** variables with the
same name within each `case { }` block.

Again, the names `UP_*` are **special**.  If the name doesn't start with `UP_`,
the inner blocks will look like:

        case value_e::Str: {
            val = static_cast<value::Str>(val);  // BAD: val reused
            print(StrFormat(str43, val->s))
        }

And they will fail to compile.  It's not valid C++ because the superclass
`value_t` doesn't have a field `val->s`.  Only the subclass `value::Str` has
it.

(Note that Python has a single flat scope per function, while C++ has nested
scopes.)

### Python context manager &rarr; C++ constructor and destructor (RAII)

This Python code:

    with ctx_Foo(42):
      f()

translates to this C++ code:

    {
      ctx_Foo tmp(42);
      f()

      // destructor ~ctx_Foo implicitly called
    }

## MyPy "Shimming" Technique

We have an interesting way of "writing Python and C++ at the same time":

1. First, all Python code must pass the MyPy type checker, and run with a stock
   Python 2 interpreter.
   - This is the source of truth &mdash; the source of our semantics.
1. We translate most `.py` files to C++, **except** some files, in particular
   [mycpp/mylib.py]($oils-src) and files starting with `py` like
   `core/{pyos.pyutil}.py`.
1. In C++, we can substitute custom implementations with the properties we
   want, like `Dict<K, V>` being ordered, `BigInt` being distinct from C `int`,
   `BufWriter` being efficient, etc.

The MyPy type system is very powerful!  It lets us do all this.

### NewDict() for ordered dicts

Dicts in Python 2 aren't ordered, but we make them ordered at **runtime** by
using `mylib.NewDict()`, which returns `collections_.OrderedDict`.

The **static type** is still `Dict[K, V]`, but change the "spec" to be an
ordered dict.

In C++, `Dict<K, V>` is implemented as an ordered dict.  (Note: we don't
implement preserving order on deletion, which seems OK.)

- TODO: `iteritems()` could go away

### StackArray[T]

TODO: describe this when it works.

### BigInt

- In Python, it's simply defined a a class with an integer, in
  [mylib/mops.py]($oils-src).
- In C++, it's currently `typedef int64_t BigInt`, but we want to make it a big
  integer.

### ByteAt(), ByteEquals(), ...

Hand optimization to reduce 1-byte strings.  For IFS algorithm,
`LooksLikeGlob()`, `GlobUnescape()`.

### File / LineReader / BufWriter

TODO: describe how this works.

Can it be more type safe?  I think we can cast `File` to both `LineReader` and
`BufWriter`.

Or can we invert the relationship, so `File` derives from **both** LineReader
and BufWriter?

### Fast JSON - avoid intermediate allocations

- `pyj8.WriteString()` is shimmed so we don't create encoded J8 string objects,
  only to throw them away and write to `mylib.BufWriter`.  Instead, we append
  an encoded strings **directly** to the `BufWriter`.
- Likewise, we have `BufWriter::write_spaces` to avoid temporary allocations
  when writing indents.
  - This could be generalized to `BufWriter::write_repeated(' ', 42)`.
- We may also want `BufWriter::write_slice()`

## Limitations Requiring Source Rewrites

mycpp itself may cause limitations on expressiveness, or the C++ language may
be able express what we want.

- C++ doesn't have `try / except / else`, or `finally`
  - Use the `with ctx_Foo` pattern instead.
- `if mylist` tests if the pointer is non-NULL; use `if len(mylist)` for
  non-empty test
- Functions can have at most one keyword / optional argument.
  - We generate two methods: `f(x)` which calls `f(x, y)` with the default
    value of `y`
  - If there are two or more optional arguments:
    - For classes, you can use the "builder pattern", i.e. add an
      `Init_MyMember()` method
    - If the arguments are booleans, translate it to a single bitfield argument
- C++ has nested scope and Python has flat function scope.  This can cause name
  collisions.
  - Could enforce this if it becomes a problem

Also see `mycpp/examples/invalid_*` for Python code that fails to translate.

## WARNING: Assumptions Not Checked

### Global Constants Can't Be Mutated

We translate top level constants to statically initialized C data structures
(zero startup cost):

    gStr = 'foo'   
    gList = [1, 2]  # type: List[int]
    gDict = {'bar': 42}  # type: Dict[str, int]

Even though `List` and `Dict` are mutable in general, you should **NOT** mutate
these global instances!  The C++ code will break at runtime.

### Gotcha about Returning Variants (Subclasses) of a Type

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

### Hacky Heuristics

- `callable(arg)` to either:
  - function call `f(arg)`
  - instantiation `Alloc<T>(arg)`
- `name.attr` to either:
  - `obj->member`
  - `module::Func`
- `cast(MyType, obj)` to either
  - `static_cast<MyType*>(obj)`
  - `reinterpret_cast<MyType*>(obj)`

### Hacky Hard-Coded Names

These are signs of coupling between mycpp and Oils, which ideally shouldn't
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

### Major Features

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
  - TODO: mycpp need real modules, because our `oils_for_unix.mycpp.cc`
    translation unit is getting big.
  - And `cpp/preamble.h` is a hack to work around the lack of modules.

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

## C++ Notes

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
