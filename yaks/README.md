Yaks
====

A minimal, TYPED language that compiles to the mycpp runtime.

- It uses NIL8 for its syntax
   - It's a Lisp-ish IR, but the semantics are imperative.  (WebAssembly also
     has a Lispy text format, but is imperative.)
- It can be written by hand, and easily read by humans.
  - `(func f [] (var [x Int] 42))` etc.
  - See `oilshell/yaks` experiment in TypeScript.
- It can also be generated in a LOSSLESS way from other languages, like Python
  - So that we can generate precise type errors that point back to Python source code
  - File, Line, Column 
  - We will probably split files into spans/Tokens like
    `doctools/micro-syntax.md`.  And then the tree can refer to this linear
    list.

## Goals

Medium-term goals:

- Get rid of dependence on (old version of) MyPy!
  - this is causing build problems, e.g. on Fedora
- Type check and run bin/{osh,ysh} in less than **one second**.
  - Similar to my `deno check && deno run` experience (which was on a tiny
    codebase; maybe it wasn't that fast.)

Non-Goal: change the source language of Oils.

- For the immediate future, it will still be in Python 2 with type comments.
  - Contributors will be able to see a familiar language.
  - We just got the yapf formatter working, etc.

### Why Compile to C++?

To be fast.  Language processors should be written in AOT -compiled languages:

- <https://news.ycombinator.com/item?id=35045520>

`pea/TEST.sh` shows that 

- parsing all of Oils serially (wiht Python 3 ast.parse()) takes 410 ms.
- Pickling also takes some time.
- Unpickling takes time

### More Issues with mycpp I want to address

- speed of Python dev build
  - type check and run Python in 1 second
- speed of C++ build
  - type check, generate multiple C++ MODULES, compile the whole program in
    say 5-10 seconds.  I think it's more like 30 seconds now.
- rooting: can be optimize it, not generate 480 KB of StackRoots or wahtever
  - this requires analyzing the call graph
- MODULES and dependencies -- may require re-organizing the Oils codebase
itself.
  - cpp/preamble.h is a hack.
  - This includes things like "system" deps like ENOENT and fork(), etc.

## End Goal

- `pea/pea_main.py` (written in Python 3!) exports Yaks for the ~40-50K lines
  of Python 2 code in ~300-400 ms.
- I think ASDL also needs to exports Yaks.
  - so we can build a symbol table
- `pea/pea.yaks` is compiled to C++.  We use Ninja for that.
  - How long will a non-incremental build take?  I think this should be like
    - 500 lines for the reader/front end, 
    - 1000-3000 lines for the type checker?
    - 1000-3000 lines for the C++ code generator?
  - Plus 4000 lines of the mycpp runtime
  - So I hope this will take just 1 second to compile and LINK.  Unit tests
    against mycpp seem sto take about 1 second, so it could be comparable.

Then

- `pea/pea_main.py | yaks check` type checks Oils in 1 second, and then you run
  `bin/osh`.
- `pea/pea_main.py | yaks cpp` generates C++ in one second
  - then it should take 5-10 seconds to compile the output in Ninja.
- Then you run `_bin/cxx-dbg/osh`

## Implementation Strategy - It Requires Bootstrapping

Let's minimize the stuff we need to write twice.

- Write the first pass "yaks0" in Python 2 with re2c and ASDL.
  - uses the NIL8 parser
  - custom transformer from nil8.asdl -> yaks.asdl
  - then print C++ directly with no type checking

- Then I think you can write "myyaks" ?
  - It's a single mycpp pass that outputs Yaks, with all the type information?

OLDER

- then rewrite all of that in Yaks itself???
  - lexer - does it invoke re2c directly?  No Python
  - parser - with infix rule
  - transform
  - print

- then translate Python 2 to Yaks, and type check that
  - first use MyPy?  does that make sense?  I think so.
    - you preserve all the hacks
    - REDUCE MYCPP TO A SINGLE PASS TO YAKS
    - all passes go over yaks, not over MyPy
      - const pass, forward decl pass, etc.

- then run it on itself!
- then run it on Oils

- then add your own type checker
  - go from `pea/pea_main.py` with the Python 2 AST to Yaks directly, without MyPy

So you could have:

- `yaks/{yaks_main.py,yaks.asdl}` -> generates mycpp C++ from `test.yaks`
  - copy mycpp/examples
  - {lex,read,transform,cppgen}.py
- `yaks/yaks_main.yaks` -> generates mycpp C++ from `oils-for-unix.yaks`, which
  is the CST dump of Python 2 !!!  
  - {lex,read,transform,check,cppgen}.yaks -- add type checker here
- `pea/py2_to_yaks.py`?
  - I guess this dumps yaks directly?  Or is there another step?
  - So we can use that type checker.  We're only writing a single type checker?
  - Yaks will have to be expanded with `class with` and all that.

OK that's a little weird.  Why not just stick with all Python?  Because:

- `pea.yaks` has to be FAST!
- Python has some weaknesses, like you need this extra ASDL

Although I suppose you could consider typed Python 3 or something?

That has proper declarations.  But you would still need ASDL.

## Notes

### NIL8 Features

- Might want multiline strings that are indented
  - for printing blocks of C++

### Line Wrapping

How do we make the output wrapped to 80 columns?  We need some kind of limit

- ASDL has an ad hoc function I borrowed from CPython
  - it doesn't work all the time

## First Words

Operators for names:

    (obj.field)
    (obj..method)      # not -> because it conflicts with C syntax?  
                       # We might want values and methods
    (namespace::func)

Arithmetic:

    (+ 1 2) et.c

    # + - / * %
    # ^ & |
    # unary ~

    a,42   is a[42]

    (== 3 4)
    (<  3 4)
    (<= 3 4)
    (>  3 4)
    (>= 3 4)

Boolean:

    (not true)
    (and true true)
    (or false false)

Only 1 top level keyword:

    # Everything lives in a module.
    (module osh
      ...
    )
    (module ysh
      ...
    )


How do we do import and export?  Do we have a require/provide kind of things?

Does this replace Ninja?  Info is duplicated in C++ and Ninja.

Module-level keywords:

    (global [s Str] "123")

    (func main [x Int] ...)

    (class Foo
      (construct Foo [x Int] ...)  
      (method main [x Str] ...)

      (member x Int)
      # Or you could do this I suppose

      [x Int]
      [y Int]
    )

    # Do we need something special for
    # There could be a macro that desugars this

    (class ctx_Foo
      (construct ctx_Foo)
      (method __enter__  # no-op
        ...
        )
      (method __exit__
    )

Within functions:

    (var [x Str] "123")

    # function call
    (print "hi")

    # or maybe
    (call print "hi")

    (if true (print "true") (print "false"))

    (while true
      (print "hi")
    )

    (foreach  # not like for in C, that could be separate

    (switch x
      (case [1 2 3]
        (call print "num")
        (call print "hi")
      )
      (case [4 5 6]
        (call print "num")
        (call print "hi")
      )
    )

    (break)
    (continue)
    (return 42)

Special within functions:

    (tagswitch (call obj..tag)  # method call I guess
      (case command_e.Simple
        (call print "simple")
      )
      (case command_e::Pipeline  # maybe use ::
        (call print "pipe")
      )
    )

    (with (call ctx_Foo a b) 
      (call print "hi")
    )

Not used in mycpp, but could be in other C++ code generators:

    (& i)  # address of
    (* pi)  # pointer dereference


### `PY_foo` for mycpp ambiguities

I think there can be a separate pass that resolves this?

Export

    t(x)
    (PY_call t x)

Then this gets turned into EITHER:

    (call t x)
    (call [Alloc t] x)

I think it depends on the symbol table.

Likewise if you have

    x.y()

That has to be

    (call (PY_attr x y))

Turn it into either

    (call x->y)  # obj->member
    (call x::y)  # namespace::func


More

- `PY_cast` -> `reinterpret_cast` or `static_cast`


### Other Issues

- C++ nested scope vs. flat function scope


