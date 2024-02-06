Yaks
====

A minimal, TYPED language that compiles to the mycpp runtime.

- It uses a Lisp-ish "CST" IR, but the semantics are imperative
  - (WebAssembly also has a Lispy text format, but is imperative.)
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

Immediate goal: Delete all the "Tea" stuff in

- `frontend/syntax.asdl`
- `ysh/grammar.pgen2`
- `osh/cmd_parse.py`
- and the whole `tea/` dir I think

This is all a distraction, and it's probably a "failed attempt" at
bootstrapping.

Medium-term goals:

- Get rid of dependence on (old version of) MyPy!
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

- `pea/py2_parse.py` (written in Python 3!) exports the CST format for our
  Python 2 code in ~300-400 ms.
- `pea/pea.yaks` is compiled to C++.  We use Ninja for that.
  - How long will a non-incremental build take?  I think this should be like
    - 500 lines for the reader/front end, 
    - 1000-3000 lines for the type checker?
    - 1000-3000 lines for the C++ code generator?
  - Plus 4000 lines of the mycpp runtime
  - So I hope this will take just 1 second to compile and LINK.  Unit tests
    against mycpp seem sto take about 1 second, so it could be comparable.

Then

- `pea/py2_parse.py | _bin/pea check` type checks Oils in 1 second, and then
  you run `bin/osh`.
- `pea/py2_parse.py | _bin/pea translate` generates C++ in one second
  - then it should take 5-10 seconds to compile the output in Ninja.
- Then you run `_bin/cxx-dbg/osh`

## Implementation Strategy - It Requires Bootstrapping

Let's minimize the stuff we need to write twice.

- Write the CST reader in pure Python 3 - `yaks/{lex,read}.py`
  - Or use the existing TypeScript reader?  `yaks/{lex,parse}.ts`
  - Not sure if that will be a permanent dependency or not

- reader SYNTAX SUGAR (or macros):
  - `this.reader.ctx` becomes (attr self reader ctx) or something
  - method calls might be `(this.Parse (a b))` etc.
- STRING LITERALS may need extra work
  - do it with regexes I guess

- Write the "transformer" from CST to ASDL AST for a MINIMAL Yaks language --
  enough to write Yaks in Yaks
  - I guess use ASDL to generate Python classes?
  - `stmt`
      - `var setvar`
      - `func`, `for while`, `if switch` 
      - ASDL `data enum` I think???
  - `expr` -- function calls, arithmetic, array/dict indexing
  - `type` -- `(List T)` etc.
  - no `class`, no `try catch`, no `with`.  This can be added later, if we need
    it for `pea`.

- Also in Python 3, print C++ code from the tree?
  - we need 3 or 4 passes, like mycpp

- Does it have a type checker?  Or do you just rely on the C++ type checker?

- Rewrite this whole thing in yaks itself?
  - lex - including the regexes for string literals etc.?
  - read
  - transform
  - ==> NOW ADD the type checker?
  - print C++

- Or don't bother to rewrite it
  - Just generate C++ from Python or TypeScript, and check in a big blob to the
    Oils repo?
  - But it links against mycpp

- Now rewrite mycpp as pea.yaks ?  It's compiled to C++

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


## Direct Architecture, No Bootstrapping

- The whole program is Python 3, with no process boundary?
  - It might be fast enough?  Let's see

## NIL8 Features

- Might want multiline strings that are indented

## Line Wrapping

I do like line wrapping.  How should we support it?

- ASDL has an ad hoc function I borrowed from CPython
  - it doesn't work all the time


