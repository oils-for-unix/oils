---
in_progress: yes
---

Oil Language Design Notes 
=========================

These informal notes may help you understand Oil.

<div id="toc">
</div> 

## It Mostly Borrows From Other Languages

Oil's design is more conservative than that of other alternative shells.  It

- **Preserves** what works best about shell (processes and files, pipelines)
- **Cleans up** the sharp edges like quoting, ad hoc parsing and splitting
- **Integrates** features from:
  - Related languages like [awk]($xref) and [xargs]($xref) (in-progress)
  - Popular dynamic languages like from Python and JavaScript.

## Influences

### POSIX Shell

For the command and word syntax:

    ls | wc -l                       # pipeline
    echo $var "${var} $(hostname)"   # variable and command sub
    echo one; echo two               # sequence of commands
    test -d /tmp && test -d /tmp/foo

Oil's own shell-like extensions:

    echo $[1 + 2*3]                  # Expression substitution
    echo $strfunc(x, y)              # Inline Function Calls

### bash and ksh

We implement many bash semantics, like "named references" for out variables:

    f() {
      local -n out=$1    # -n for named reference
      out=bar
    }

    myvar=foo
    f myvar
    echo $myvar          # prints "bar"

But clean up the syntax:   

    proc f(:out) {       # "out param" declared with :
      setref out = 1
    }

    var myvar = 'foo'
    f :myvar             # caller prefixes the var name with :
    echo $myvar          # prints "bar"

Historical note: Usenix 93.  korn shell was used for GUIs and such!

### Python

For the expression language:

    var i = 1 + 2*3
    var s = 'yes' if mybool else 'no'

And proc signatures:

    proc cp(src, dest='/tmp') {  # Python-like default value
      cp --verbose $src $dest
    }

Differences:

- Oil uses shell-like composition with "procs", not Python- or JavaScript-like
  functions.
- No classes, or operator loading.
  - `a + b` (addition) vs. `a ++ b` (concatenation)
  - `a < b` is only for integers.  `cmp()` could be for strings.
- No "accidentally quadratic"
  - Strings and `+=`
  - No `in` for array/list membership.  Only dict membership.
- `s[i]` returns an integer "rune", not a string?
- Syntax
  - `div` and `mod`
  - `xor`, because `^` is for exponentiation

### JavaScript

For dict literals:

    # Unquoted keys.  Sigil to avoid confusion with blocks.
    d = %{name: 'Bob', age: 10}

    d = %{[mystr]: 'value'}  # key expressions in []

And "structured programming" looks like C / Java / JavaScript:

    if (x > 0) {
      echo 'positive'
    } else {
      echo '0 or negative'
    }

    var x = 5
    while (x > 0) {
      echo $x
      setvar x -= 1
    }

### Ruby

For blocks:

    cd /tmp {
      echo $PWD  # prints /tmp
    }
    echo $PWD

(Julia has something like blocks too.)

And the syntax for references to variable names:

    read :line                   # populate $line variable
    push :myarray one two three  # append to array


### Perl

For the `@` character (which PowerShell also uses):

    var myarray = %(one two three)
    echo @myarray  # @ isn't a really sigil; it's the "splice" operator

    echo @arrayfunc(x, y)

Perl can be viewed as a mixture of shell, awk, and sed.  Oil is a similar
agglomeration of related languages.

<!--

TODO: autovivification from Perl/awk.  Is this setvar?
-->

### Go (library)

For the builtin flags syntax:

     mybuiltin --show=0  # turn a flag that's default true

It also uses a native UTF-8 representation of strings.

### awk and make, find and xargs

Features influenced by these languages are planned, but not implemented.

## Aside

### Tcl

Oil uses `proc` and `setvar`, which makes it look a bit like Tcl:

     proc p(x) {
       setvar y = x * 2
       echo $y
     }

     p 3  # prints 6

But this is mostly "convergent evolution", and relatively superficial.

Oil isn't homoiconic like Tcl is.  It avoids dynamic parsing.  It also has a
lot of syntax.

<!--

Config Dialect:

- nginx configs?
- hcl? 

What about JS safe string interpolation?

- r"foo"

LATER:

- R language (probably later, need help): data frames, lazy evaluation
- Honorable mention: Lua: reentrant interpreter.  However the use of Unix
  syscalls implies global process state.
- Lisp: symbol types

Tea Language:

Julia for signatures, default arguments, named arguments:

    func f(p1, p2=0 ; n2, n2=0) {
    }

Go and MyPy, for types:

    func add(x Int, y Int) Int {
      return x + y
    }
    # what about named return values?
-->

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

Oil is:

- getting rid of: ksh.  Bourne shell is good; ksh is bad because it adds bad
  string operators.
  - `${x%%a}`  `${x//}`  getting rid of all this crap.  Just use functions.
  - korn shell arrays suck.  Replaced with python-like arrays
- Add Python STRUCTURED DATA.
  - the problem with PROCESSES AND FILES is that it forces serialization everywhere.
  - Structured Data in Oil
- Add **declarative** paradigm to shell.
  - Package managers like Alpine Linux, Gentoo need declarative formats.  So do
    tools like Docker and Chef.
- Language-Oriented -- internal DSLs.


