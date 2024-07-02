---
default_highlighter: oils-sh
---

YSH Language Influences
=======================

Almost all syntax in YSH comes from another language.  This doc lists some of
these influences.

Reading this page isn't essential for all users, but it may help some users
remember the syntax.

<div id="toc">
</div> 

## General Philosophy

At a high level, YSH is a bash-compatible shell language that adds features
from popular dynamic languages.

Its design is more conservative than that of other alternative shells.  Our
goals are to:

- **Preserve** what works best about shell: processes, pipelines, and files.
- **Clean up** the sharp edges like quoting, ad hoc parsing and splitting
- **Integrate** features from Python, JavaScript, Ruby, and other languages
  listed below.

## Major Influences

### POSIX Shell

The command and word syntax comes from shell:

    ls | wc -l                        # pipeline
    echo $var "${var} $(hostname)"    # variable and command sub
    echo one; echo two                # sequence of commands
    test -d /tmp && test -d /tmp/foo  # builtins and operators

Shell-like extensions in YSH:

    echo $[42 + a[i]]                 # Expression substitution
    cd /tmp { echo hi }               # Block arguments

### bash and ksh

We implement many bash semantics, like "named references" for out variables:

    f() {
      local -n out=$1    # -n for named reference
      out=bar
    }

    x=foo
    f x
    echo x=$x            # => x=bar

Though we discourage dynamic scope.  YSH provides a better mechanism called
`value.Place`.

    proc f(; out) {
      call out->setValue('bar')
    }

    var x = 'foo'
    f (&x)               # pass a place
    echo x=$x            # => x=bar

<!--
Historical note: Usenix 93.  korn shell was used for GUIs and such!
-->

### Python

The YSH expression language is mostly Python compatible.  Expressions occur on
the right-hand side of `=`:

    var a = 42 + a[i]
    var b = fib(10)
    var c = 'yes' if mybool else 'no'

Proc signatures take influence from Python:

    proc mycopy(src, dest='/tmp') {  # Python-like default value
      cp --verbose $src $dest
    }

Related: differences documented in [YSH Expressions vs.
Python](ysh-vs-python.html).

### JavaScript

YSH uses JavaScript's dict literals:

    var d1 = {name: 'Alice', age: 10}  # Keys aren't quoted

    var d2 = {[mystr]: 'value'}        # Key expressions in []

    var name = 'Bob'
    var age = 15
    var d3 = {name, age}  # Omitted values taken from surrounding scope

Blocks use curly braces, so most code resembles C / Java / JavaScript:

    if (x > 0) {
      echo 'positive'
    } else {
      echo 'zero or negative'
    }

    var i = 5
    while (i > 0) {
      echo $i
      setvar i -= 1
    }

### Ruby

YSH has Ruby-like blocks:

    cd /tmp {
      echo $PWD  # prints /tmp
    }
    echo $PWD

### Perl

The `@` character comes from Perl (and PowerShell):

    var myarray = :| one two three |
    echo @myarray          # @ is the "splice" operator

    echo @[arrayfunc(x, y)]

    for i in @(seq 3) {    # split command sub
      echo $i
    }

The unbuffered `for` loop is similar to Perl's `while (<>) { ...`:

    for line in <> {
      echo $line
    }

Perl can be viewed as a mixture of shell, awk, and sed.  YSH is a similar
agglomeration of languages, but it's statically parsed.

### Julia

The semicolon in `proc` and `func` definitions comes from Julia:

    func f(x, y; invert=false) {
      if (invert) {
        return (-x - y)
      } else {
        return (x + y)
      }
    }

Multiline strings in YSH strip leading whitespace, similar to Julia:

    proc p {
      # Because leading and trailing space are stripped, this is 2 lines long
      var foods = '''
      peanut
      coconut
      '''
    }


(Julia has something like blocks too.)

### Go

Like Go, Oils is UTF-8-centric.  (Go blog: [Strings, bytes, runes and
characters in Go](https://go.dev/blog/strings).)

The design of for loops is roughly influenced by Go:

    for i, item in (mylist) {  # ask for index and value
      echo "$i $item"
    }

    for i, k, v in (mydict) {  # ask for index, key, and value
      echo "$i $k $v"
    }

### Awk

YSH gets its regex match operator from Awk:

    if (mystr ~ /digit+/) {
      echo 'Number'
    }

(We don't use Perl's `=~` operator.)

### Lisp

YSH has "quotation types" that represent unevaluated code.  Like Lisp, they
give you control over evaluation:

    var my_cmd = ^(ls /tmp | wc -l)
    eval (my_cmd)

    var my_expr = ^[42 + a[i]]
    var v = evalExpr(my_expr)

    var my_template = ^"hi $name"  # unimplemented

### Haskell

YSH also uses `++` to concatenate strings and lists:

    var mystr = a ++ b    
    var mystr = "$a$b"       # very similar

    var mylist = c ++ d
    var mylist = :| @c @d |  # also converts every element to a string

YSH has a `value.IO` type that makes functions pure:

    func renderPrompt(io) {
      return (io->promptVal('$') ++ " ")
    }

## Minor Influences

### make, find and xargs

Our design for Ruby-like blocks was influenced by these mini-languages.

### Tcl

YSH uses `proc` and `setvar`, which makes it look something like Tcl:

     proc p(x) {
       setvar y = x * 2
       echo $y
     }

     p 3  # prints 6

But this is mostly superficial: YSH isn't homoiconic like Tcl is, and has a
detailed syntax.  It intentionally avoids dynamic parsing.

However, [Data Definition and Code Generation in Tcl (PDF)][config-tcl] shows
how Tcl can be used a configuration language:

    change 6/11/2003 {
      author "Will Duquette"
      description {
        Added the SATl component to UCLO.
      }
    }

Hay blocks in YSH allow this to be expressed very similarly:

    hay define Change

    Change 6/11/2003 {
      author = "Will Duquette"
      description = '''
        Added the SATl component to UCLO.
      '''
    }


[config-tcl]: https://trs.jpl.nasa.gov/bitstream/handle/2014/7660/03-1728.pdf

### PHP

PHP has global variables like `_REQUEST` and `_POST`.

YSH has `_error`, `_group()`, `_start()`, etc.  These are global variables that
are "silently" mutated by the interpreter (and functions to access such global
data).

### Lua

YSH also uses a leading `=` to print expressions in the REPL.

    = 1 + 2

Lua's implementation as a pure ANSI C core without I/O was also influential.

### C

Most of our C-like syntax can be attributed to JavaScript or Python.  But the
`value.Place` type is created with the `&` operator, and should be familiar to
C users:

    $ echo hi | read --all (&myvar)
    $ echo "myvar=$myvar"
    => myvar=hi

So a `value.Place` behaves like a pointer in some ways.

The `&` syntax may also feel familiar to Rust users.

## Related

- [Novelties in OSH and YSH](novelties.html)

<!--

Config Dialect:

- nginx configs?
- HCL? 

What about JS safe string interpolation?

- r"foo"

LATER:

- R language (probably later, need help): data frames
	- lazy evaluation like  mutate (ms = secs * 100)

Go for type signatures:

    func add(x Int, y Int) Int {
      return x + y
    }
    # what about named return values?

and MyPy for types like List[Int], Dict[Str, Str]

(Swift and Perl 6 also capitalize all types)

Rust:

    0..n and 1..=n ?
    enum
    |x| x+1 

Clojure:

\n and \newline for character literals, but YSH uses #'n' and \n

maybe set literals with #{a b c} vs. #{a, b, c}

## Paradigms and Style

Shell is already mix of: 

- dataflow: concurrent processes and files, pipelines
  - instead of Clojure's "functions and data", we have "processes and files".
    Simple.  Functional.  Transforming file system trees is a big part of
    containers.
- imperative: the original Bourne shell added this.  
  - "functions" are really procedures; return
  - iteration constructs: while / for / break / continue
  - conditional constructs: if / case

YSH is:

- getting rid of: ksh.  Bourne shell is good; ksh is bad because it adds bad
  string operators.
  - `${x%%a}`  `${x//}`  getting rid of all this crap.  Just use functions.
  - korn shell arrays suck.  Replaced with python-like arrays
- Add Python STRUCTURED DATA.
  - the problem with PROCESSES AND FILES is that it forces serialization everywhere.
  - Structured Data in YSH
- Add **declarative** paradigm to shell.
  - Package managers like Alpine Linux, Gentoo need declarative formats.  So do
    tools like Docker and Chef.
- Language-Oriented -- internal DSLs.
--> 
