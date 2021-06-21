---
default_highlighter: oil-sh
in_progress: true
---

A Tour of the Oil Language
==========================

Recall that the Oil project has both the compatible [OSH
language]($xref:osh-language) and the new [Oil language]($xref:oil-language).

This document describes the latter from a **clean slate** perspective, i.e.
without legacy and [path dependence][].  Remember, Oil is for Python and
JavaScript programmers who avoid shell!  See the [project
FAQ](//www.oilshell.org/blog/2021/01/why-a-new-shell.html) for more background.

Knowledge of Unix shell isn't assumed, but shell users will see similarities,
simplifications, and upgrades.

[path dependence]: https://en.wikipedia.org/wiki/Path_dependence

<div id="toc">
</div>

## Preliminaries

Start Oil just like you start bash or Python:

<!-- oil-sh below skips code block extraction, since it doesn't run -->

```sh-prompt
bash$ oil                # assuming it's installed

oil$ echo 'hello world'  # command typed into Oil
hello world
```

In the sections below, we'll save space by showing output in comments, with
`=>`:

    echo 'hello world'       # => hello world

Multi-line output is shown like this:

    echo one
    echo two
    # =>
    # one
    # two


## Examples

### Hello World Script

You can also type the commands into a file `hello.oil`.  This is a complete Oil
program, which is identical to a shell program:

    echo 'hello world'     # => hello world

Unlike shell, Oil has `const` and `var` keywords:

    const name = 'world'
    echo "hello $name"     # => hello world

With rich Python-like expressions on the right:

    var x = 42             # an integer, not a string
    setvar x = min(x, 1)   # mutate with the 'setvar' keyword

    setvar x += 5          # Increment by 5
    echo $x                # => 6

### An Oil Module

TODO: Show off commands (loops, procs), words, expressions, etc.  But make it
realistic?

Single file scripts don't need this.

An Example Modules?

    #!/usr/bin/env oil

    module main || return 0
    #source $_this_dir/lib/util.oil

    proc myproc2 {
      echo hi
    }

    #runproc @ARGV

## Concept: Three Sublanguages

Oil is best explained as three interleaved languages:

1. **Words** are expressions for strings, and arrays of strings.  This
   includes:
   - literals like `'mystr'`
   - substitutions like `$(hostname)`,
   - globs like `*.sh`, and more.
2. **Commands** are used for
   - control flow (`if`, `for`),
   - abstraction (`proc`),
   - I/O (pipelines), and more.
3. **Expressions** on typed data are borrowed literally from Python, with some
   JavaScript influence.
   - Lists: `['python', 'shell']` or `%(python shell)`
   - Dicts: `{alice: 10, bob: 30}`

For example, this *command*

    write hello $name $[42 + 1]
    # =>
    # hello
    # world
    # 43

consists of four *words*.  And the fourth word contains an expression.

*Expressions* may also have words and commands, like:

    var y = $'one\n' ++ $(echo two)  # concatenate two words
    write $y
    # =>
    # one
    # two

To say it another way: Words, commands, and expressions are mutually recursive.

<!--
One way to think about these sublanguages is to note that the `|` character
means something different in each context:

- In the command language, it's the pipeline operator, as in `ls | wc -l`
- In the word language, it's only valid in a literal string like `'|'`, `"|"`,
  or `\|`.  (It's also used in `${x|html}`, which formats a string.)
- In the expression language, it's the bitwise OR operator, as in Python and
  JavaScript.
-->

## The Word Language: Expressions for Strings (and Arrays)

Let's review the word language first.  Words can be literals, substitutions, or
expressions that evaluate to an **array** of strings.

### String Literals: Three Types of Quotes

You can choose the type of quote that's more convenient to write a given
string.

#### Single-Quoted, Double-Quoted, and C-Style

In single-quoted strings, all characters are **literal** (which means such
strings can't contain single quotes.)

    echo 'c:\Program Files\'        # => c:\Program Files\

Double-quoted strings allow **interpolation with `$`**.

    var person = 'alice'
    echo "hi $person, $(echo bye)"  # => hi bob, bye

To denote operator characters, escape them with `\`:

    echo "\$ \" \\ "                # => $ " \

C-style strings look like `$'foo'` and respect backslash **chararacter
escapes**:

    echo $' A is \x41 \n line two, with backslash \\'
    # =>
    #  A is A
    #  line two, with backslash \

(The leading `$` does NOT mean "interpolation".  It's an unfortunate
collision.)

#### Multiline Strings

Multiline strings are surrounded with triple quotes.  Leading whitespace is
stripped in a convenient way, and they have single- and double-quoted
varieties, as above:

    sort <<< '''
    $2.00  # literal $, no interpolation
    $1.99
    '''
    # =>
    # $1.99
    # $2.00

    sort <<< """
    var sub: $x
    command sub: $(echo hi)
    expression sub: $[x + 3]
    """
    # =>
    # var sub: 6
    # command sub: hi
    # expression sub: 9

(Use multiline strings instead of shell's [here docs]($xref:here-doc).)

### Substitute Variables, Commands, Builtins, Expressions, or Functions

#### Variable Sub

The syntax `$a` or `${a}` converts a variable to a string:

    var a = 'AA'
    echo $a                          # => AA
    echo _${a}_                      # => _AA_
    echo "_ $a _"                    # => _ AA _
    echo ${not_defined:-'default'}   # => default

#### Command Sub

The `$()` syntax runs a command and captures its `stdout`:

    echo $(hostname)                 # => example.com
    echo "_ $(hostname) _"           # => _ example.com _

#### Builtin Sub

A builtin sub is like a command sub, but it doesn't fork a process.  It can
only capture the output of `echo`, `printf`, and `write`.

TODO: Not implemented yet.

    proc p {
      echo "_ $1 _"
    }

    #var s = ${.p ZZ}                 # capture stdout as a variable
    #echo $s                          # => _ ZZ _

#### Expression Sub

The `$[]` syntax evaluates an expression and converts it to a string:

    echo $[a]                        # => AA
    echo $[1 + 2]                    # => 3
    echo "_ $[1 + 2] _"              # => _ 3 _

<!-- TODO: safe substitution -->

#### Function Sub

You can also turn the result of a function into a word with the shortcut
`$f(x)`:

    var mylist = ['a', 'b']
    echo $join(mylist)               # => ab

Note that function subs **cannot** be used in quotes.  You may wrap them in
expression subs:

    echo "_ $[join(mylist)] _"       # => _ ab _

### Multiple Strings: Globs, Brace Expansion, and Splicing

There are four different constructs that evaluate to a **list of strings**,
rather than a single string.

#### Globs

Globs like `*.py` evaluate to a list of files.

    touch foo.py bar.py  # create the files
    write *.py
    # =>
    # foo.py
    # bar.py

If no files match, it evaluates to an empty list (option `nullglob`).

#### Brace Expansion

The brace expansion mini-language lets you write strings without duplication:

    write {andy,bob}@example.com
    # =>
    # andy@example.com
    # bob@example.com

#### Array Splice

The `@` operator splices an array into a command:

    var myarray = %(one two)  
    write S @myarray E
    # =>
    # S
    # one
    # two
    # E

#### Function Splice

You can also splice the result of a function returning an array:

    write -- @split('foo bar')
    # => 
    # foo
    # bar

Recall that *function sub* looks like `$join(mylist)`, and is complementary.

## The Command Language: Control Flow, Abstraction, I/O

### Simple Commands and Redirects

A simple command is a space-separated list of words, which are often unquoted.
Oil looks up the first word to determine if it's a `proc` or shell builtin.

    proc greet(name) {
      echo "hello $name"
    }
    greet bob            # => hello bob

    echo 'hi'            # The shell builtin 'echo' (quoting for clarity)

If not, then it's an external command:

    ls -l /tmp           # The external 'ls' command

<!-- leaving off: aliases -->

You can **redirect** `stdin` and `stdout` of simple commands:

    echo hi > tmp.txt  # write to a file
    sort < tmp.txt

Here are a couple uwses of `stderr`:

    ls /tmp 2> error.txt

    proc log(msg) {
      echo $msg >&2  # Write message to stderr
    }

<!-- later: parse_amp fixes redirects? -->

### Pipelines

Pipelines are a powerful method manipulating text:

    ls | wc -l                       # count files in this directory
    find /bin -type f | xargs wc -l  # in this subtree

TODO: You can also use JSON, CSV/TSV, HTML, etc.

### Variable Declaration and Mutation

Constants can't be modified:

    const i = 42
    # 'setvar i = 43' would be an error

But variables can:

    var mydict = {name: 'bob', age: 10}
    setvar mydict->name = 'alice'
    echo $[mydict->name]  # => alice

That's about all you need to know.  Advanced users may want `setglobal` or
`setref` in certain situations:

    var g = 1
    proc demo(:out) {
      setglobal g = 42
      setref out = 43
    }
    demo :g  # pass a reference to g
    echo $g  # => 43

### Conditionals: `if`, `case`

If statements, with `elif` and `else:

    if test --file foo {
      echo 'foo is a file'
    } elif test --dir foo {
      echo 'foo is a directory'
    } else {
      echo 'neither'
    }

With expressions

    if (x > 0) {
      echo "$x is positive"
    }

Case:

    case $x {
      (*.py)
        echo 'Python'
        ;;
      (*.sh)
        echo 'Shell'
        ;;
    }

(You can also use the shell style of `if foo; then then` and `case $x in`, but
this is discouraged.)

### Loops: `for`, `while`

    for x in one two *.py {
      echo $x
    }  # prints 'one', 'two', 'foo.py', 'bar.py'


Command:

   while test -n $foo {
     read $foo
   }

Expression:

    var x = 0
    while (x > 0) {
      echo "x = $x"
      # TODO: implement this
      #setvar x -= 1
    }

### Abstraction: `proc` and Blocks

Define units of reusable code with the `proc` keyword, and invoke them just
like any other command:

    proc mycopy(src, dest) {
      cp --verbose $src $dest
    }

    touch log.txt
    # mycopy is a proc, so shells don't run an external command
    mycopy log.txt /tmp  # runs cp --verbose

#### Ruby-like Blocks

Some builtins take blocks directly:

    cd /tmp {
      write *.py
      echo $PWD  # /tmp
    }
    echo $PWD    # back to original direcory

    # TODO: fix crash
    #shopt --unset errexit {
    #  mycopy x y  # ignore errors
    #  mycopy y z  # ignore errors
    #}


### Builtin Commands

Oil also has **shell builtins** like `cd` and `read`.  Each one has a little
"flag language":

    cd -L .                      # follow symlinks

    echo foo | read --line       # read a line of stdin
    
Some builtins and procs take Ruby-like **blocks**, like:

    cd /tmp {
      echo $PWD  # => /tmp
    }
    echo $PWD    # prints the original directory

If you're a conceptual person, skimming [Syntactic
Concepts](syntactic-concepts.html) may help you understand the examples that
follow.


## The Expression Language: Python-like Types

TODO: link docs

### Types and Literals: `Bool`, `Int`, `List`, `Dict`, ...

Types are capitalized

- Bool
- Int
- Float (deferred for first pass)
- Str
- List
- Dict

And

- Block
- Expr


These are the same:

    var x = %(one two three)
    var y = ['one', 'two', 'three']

### Operators

- arithmetic: `+ - * / // %` and `**` for exponentatiation (actually leave it out?)
- bitwise operators: `& | ^ ~`
- logical: `and or not`
- comparison: `== <= >= in 'not in'` 
  - what about `is` and `is not`?

<!--
- No string formatting with %
- No @ matrix multiply
-->

### Syntax That Isn't in Python

- `s ++ t` for concatenation of strings and arrays
  - because `+` does coercion
- `~==` for approximate equality
- `mydict->key` as a shortcut for `mydict['key']`
- Character/integer literals like `#'a'`, `\n` and `\u{3bc}` -- NOT tied to a
  string.  (used in eggex)
- `%symbol` (used in eggex)


Concat example:

    var x = 42 + 1
    var y = $'foo\n' ++ "hello $name"

### Builtin Functions

### Egg Expressions (Oil Regexes)

These are real expressions!

## Interchange Formats (Languages for Data)

### Lines of Text (traditional)

Traditional Unix

QSN too.

### JSON, QTT (structured)

For tabular data.

<!--
More later:
- MessagePack (e.g. for shared library extension modules)
- SASH: Simple and Strict HTML?  For easy processing
- QTT: should also allow hex float representation for exactness
-->

## The Runtime

### Process and Data Model

TODO: Links Docs

Kernel.

<!-- Process model additions: Capers, Headless shell -->

### `shopt`, `shvar`, and Registers

- `simple_word_eval`

#### shvars

- `IFS`
- `_ESCAPE`
- `_DIALECT`

#### Registers

- `$?` and `_status`
- `_buffer`
- `_this_dir`

## Features Not Shown

### Deprecated

- Boolean expressions like `[[ x =~ $pat ]]`
- Shell arithmetic like `$(( x + 1 ))` and `(( y = x ))`.  Use Oil expressions
  instead.
- The `until` loop can always be replaced with a `while` loop
- Oil code uses shell's `||` and `&&` in very limited circumstances, since
  `errexit` is on by default.

### Advanced

These shell features are part of Oil, but aren't shown for brevity.

- `fork` and `forkwait`
- Process Substitution: `diff <(sort left.txt) <(sort right.txt)`
- Unevaluated blocks and expressions: `^(ls | wc-l)` and `^[42 + a[i]]`

### Not Yet Implemented

TODO: We need to implement these things!

- QTT support

```none
qtt | filter [size > 10]  # lazy arg lists
echo ${x|html}            # formatters
echo ${x %.2f}            # statically-parsed printf

echo ${.myproc arg1}      # builtin sub

# convenient multiline syntax

... cat file.txt
  | sort
  | uniq -c
  ;
```

## Summary

Oil is a clean language!  With these concepts

- String Literals
- Words (substitution, splicing, globs, and brace expansion)
- Commands
- Expressions

## Related Docs

Contrast:

- [Oil Language Idioms](idioms.html) - Oil side-by-side with shell.
- [Oil Language Influences](language-influences.html)
- *A Tour of the Oil project*. TODO: Describe Oil, OSH, oven, the shell
  runtime, headless shell, etc.


