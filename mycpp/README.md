mycpp
=====
 
This is an experimental Python-to-C++ translator based on MyPy.  It only
handles the small subset of Python that Oil uses.

It's inspired by both mypyc and Shed Skin.  

To run it, you'll need the MyPy source repository, as well as a virtualenv
containing MyPy's dependencies.

See the instructions at the top of `run.sh` for details.


### Notes on the Algorithm / Architecture

(A) One `const_pass.py`.  Collect string constants.
  
(B) Three `cppgen_pass.py` variants.  For each module, Declare and define
   classes and functions.

1. Forward Declaration Pass.

```
    class Foo;
    class Bar;
```

More work:

- Determine which methods should be declared `virtual` in their declarations
  (written in the next pass)

2. Declaration Pass.

```
    class Foo {
      void method();
    };
    class Bar {
      void method();
    };
```


More work:

- Collect member variables and write them at the end of the definition
- Collect locals for "hoisting".  Written in pass #3.
- Creates `fmtN()` functions to compile Python's `%` formatting operator.

3. Definition Pass.

```
    void Foo:method() {
      ...
    }
    void Bar:method() {
      ...
    }
```



Note: I really wish we were not using visitors, but that's inherited from MyPy.
MyPy seems to have some support for serializing the AST, so maybe we could do
that and rewrite it in Oil.

### C++ Features We Use

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
