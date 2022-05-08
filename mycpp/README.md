mycpp
=====
 
This is an experimental Python-to-C++ translator based on MyPy.  It only
handles the small subset of Python that Oil uses.

It's inspired by both mypyc and Shed Skin.  These posts give background:

- [Brief Descriptions of a Python to C++ Translator](https://www.oilshell.org/blog/2022/05/mycpp.html)
- [Oil Is Being Implemented "Middle Out"](https://www.oilshell.org/blog/2022/03/middle-out.html)

## Running It

To run it, it helps to have a Debian / Ubuntu-ish machine.  Follow the
instructions at

    https://github.com/oilshell/oil/wiki/Contributing

to create the "dev build" first, which is DISTINCT from oil-native.  Make sure
you can run:

    oil$ build/dev.sh all

This will give you a working shell in Python:

    oil$ bin/osh -c 'echo hi'
    hi

To run mycpp, you'll need the MyPy source repository, as well as a virtualenv
containing MyPy's dependencies.  The instructions at the top of `deps.sh` give
details:

    oil$ mycpp/deps.sh git-clone
    oil$ mycpp/deps.sh pip-install

To build oil-native, use:

    oil$ build/dev.sh oil-cpp  # translate and compile, may take 30 seconds

    oil$ _bin/osh_eval.dbg -c 'echo hi'
    hi

To run the tests and benchmarks, follow the instructions at the top of `deps.sh`.

If you have problems, post a message on `#oil-dev` at
`https://oilshell.zulipchat.com`.  Not many people have contributed to `mycpp`,
so I can use your feedback!

## Notes on the Algorithm / Architecture

(A) One `const_pass.py`.  Collect string constants.
  
(B) Three `cppgen_pass.py` variants.  For each module, Declare and define
   classes and functions.

1. Forward Declaration Pass.


    class Foo;
    class Bar;

More work:

- Determine which methods should be declared `virtual` in their declarations
  (written in the next pass)

2. Declaration Pass.


    class Foo {
      void method();
    };
    class Bar {
      void method();
    };


More work:

- Collect member variables and write them at the end of the definition
- Collect locals for "hoisting".  Written in pass #3.
- Creates `fmtN()` functions to compile Python's `%` formatting operator.

3. Definition Pass.

    void Foo:method() {
      ...
    }
    void Bar:method() {
      ...
    }


Note: I really wish we were not using visitors, but that's inherited from MyPy.
MyPy seems to have some support for serializing the AST, so maybe we could do
that and rewrite it in Oil.

## C++ Features We Use

It would be nice to generate plain C, but it would also be significantly more
work because we use several C++ features.

And IMO the generated code is more readable in C++.  For example, classes and
methods preserve the structure of the source.  And if we didn't have
namespaces, we'd have to use long generated function names.

- Templates for `List`, `Dict`, `Tuple`, etc.
- Inheritance (for "modules")
  - Virtual Methods
  - Abstract Methods
  - Initializer lists in constructors
- namespaces for modules
- A little bit of operator overloading, for Dict []
  - TODO: could get rid of this.
- Some Function Overloading for `format_r` ?
  - Do we need this for equality and hashing?
- `new` (but not `delete`!)
- Exceptions
- ASDL: type-safe enums, i.e. `enum class`
- Minor:
  - `nullptr`
  - `static_cast` and `reinterpret_cast`

Later:

- Destructors, for scoped-based cleanup.
- References for non-nullable values?

Not using:

- I/O Streams, RTTI, etc.
- `const`

## Notes on mylib

- A `Str` is immutable, and can be used as a key to a `Dict` (at the Python
  level), and thus an `AssocArray` (at the Oil level).
  - TODO: It can share underlying storage of `data_`?
- A `BufWriter` is mutable.  It's an alias for `cStringIO.StringIO()`.  You
  build it with repeated calls to`write()`, and then call `getvalue()` at the
  end.

## Limitations 

### Due to Garbage Collection

- Instead of `Tuple[str, int]`, use an ASDL record `(str s, int i)`
- `for x in [1, 2, 3]` is not allowed.  Assign it to a temporary variable
  first, so it can be picked up in StackRoots().




