---
default_highlighter: oil-sh
in_progress: true
---

A Tour of the Oil Language
==========================

<!-- author's note about example names

- people: alice, bob
- nouns: ale, bean
  - peanut, coconut
- 42 for integers
-->

The [FAQ][] explains that the Oil **project** has both the compatible [OSH
language]($xref:osh-language) and the new [Oil language]($xref:oil-language).

This document describes the latter from a **clean slate** perspective, i.e.
without legacy and [path dependence][].  Remember, Oil is for Python and
JavaScript programmers who avoid shell!

Knowledge of Unix shell isn't assumed, but shell users will see similarities,
simplifications, and upgrades.

[FAQ]: https://www.oilshell.org/blog/2021/01/why-a-new-shell.html
[path dependence]: https://en.wikipedia.org/wiki/Path_dependence

**Warning**: This document is **long** because it demonstrates nearly every
feature of the language.  You may want to read it in multiple sittings, or read
blog posts like [The Simplest Explanation of
Oil](https://www.oilshell.org/blog/2020/01/simplest-explanation.html) first.

To summarize:

1. Oil has interleaved *word*, *command*, and *expression* languages.
   - The command language has Ruby-like *blocks*, and the expression language
     has Python-like *data types*.
2. Oil has two kinds of *builtins* that form the "standard library".
3. Languages for *data* (like [JSON][]) are complementary to Oil code.
4. OSH and Oil share both an *interpreter data model* and a *process model*
   (provided by the Unix kernel).  Understanding these common models will make
   you both a better shell user and Oil user.

That's about it!  Keep those 4 points in mind as you read the details below.

[JSON]: https://json.org

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

In the sections below, we'll save space by showing output **in comments**, with
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

You can also type commands into a file `hello.oil`.  This is a complete Oil
program, which is identical to a shell program:

    echo 'hello world'     # => hello world

### A Taste of Oil

Unlike shell, Oil has `const` and `var` keywords:

    const name = 'world'
    echo "hello $name"     # => hello world

With rich Python-like expressions on the right:

    var x = 42             # an integer, not a string
    setvar x = min(x, 1)   # mutate with the 'setvar' keyword

    setvar x += 5          # Increment by 5
    echo $x                # => 6

It also has Ruby-like blocks:

    cd /tmp {
      echo hi > greeting.txt  # file created inside /tmp
      echo $PWD               # => /tmp
    }
    echo $PWD                 # prints the original directory

And utilities to read and write JSON:

    var d = {name: 'bob', age: 42}
    json write :d
    # =>
    # {
    #   "name": "bob",
    #   "age": 42,
    # }

## Concept: Three Sublanguages

Oil is best explained as three interleaved languages:

1. **Words** are expressions for strings, and arrays of strings.  This
   includes:
   - literals like `'mystr'`
   - substitutions like `$(hostname)`,
   - globs like `*.sh`, and more.
2. **Commands** are used for
   - I/O (pipelines, the `read` builtin),
   - control flow (`if`, `for`),
   - abstraction (`proc`), and more.
3. **Expressions** on typed data are borrowed literally from Python, with some
   JavaScript influence.
   - Lists: `['ale', 'bean']` or `%(ale bean)`
   - Dicts: `{name: 'bob', age: 42}`
   - Functions: `split('ale bean')` and `join(['pea', 'nut'])`

For example, this *command*

    write hello $name $[42 + 1]
    # =>
    # hello
    # world
    # 43

consists of **four** *words*.  The fourth word contains an expression.

*Expressions* may also have words and commands, like:

    var y = $'ale\n' ++ $(echo bean)  # concatenate two words
    write $y
    # =>
    # ale
    # bean

To say it another way: Words, commands, and expressions are mutually recursive.
If you're a conceptual person, skimming [Syntactic
Concepts](syntactic-concepts.html) may help you understand the examples that
follow.

<!--
One way to think about these sublanguages is to note that the `|` character
means something different in each context:

- In the command language, it's the pipeline operator, as in `ls | wc -l`
- In the word language, it's only valid in a literal string like `'|'`, `"|"`,
  or `\|`.  (It's also used in `${x|html}`, which formats a string.)
- In the expression language, it's the bitwise OR operator, as in Python and
  JavaScript.
-->

## Word Language: Expressions for Strings (and Arrays)

Let's review the word language first.  Words can be literals, substitutions, or
expressions that evaluate to an **array** of strings.

### Three Kinds of String Literals

You can choose the type of quote that's most convenient to write a given
string.

#### Single-Quoted, Double-Quoted, and C-Style

In single-quoted strings, all characters are **literal** (except `'`, which
can't be denoted):

    echo 'c:\Program Files\'        # => c:\Program Files\

Double-quoted strings allow **interpolation with `$`**.

    var person = 'alice'
    echo "hi $person, $(echo bye)"  # => hi bob, bye

Inside double quotes, denote operators by escaping them with `\`:

    echo "\$ \" \\ "                # => $ " \

C-style strings look like `$'foo'` and respect backslash **chararacter
escapes**:

    echo $' A is \x41 \n line two, with backslash \\'
    # =>
    #  A is A
    #  line two, with backslash \

(Note that the leading `$` does **not** mean "interpolation".  It's an
unfortunate syntax collision.)

#### Multiline Strings

Multiline strings are surrounded with triple quotes.  They have single- and
double-quoted varieties, and leading whitespace is stripped in a convenient
way.

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
    # command sub: hi
    # expression sub: 9
    # var sub: 6

(Use multiline strings instead of shell's [here docs]($xref:here-doc).)

### Five Kinds of Substitution

Oil has syntax for 5 types of substitution, all of which start with `$`.  These
constructs convert data to a **string**:

1. Variables
2. The output of commands
3. The output of builtins
4. Expressions
5. The results of functions

#### Variable Sub

The syntax `$a` or `${a}` converts a variable to a string:

    var a = 'ale'
    echo $a                          # => ale
    echo _${a}_                      # => _ale_
    echo "_ $a _"                    # => _ ale _

The shell operator `:-` is occasionally useful in Oil:

    echo ${not_defined:-'default'}   # => default

#### Command Sub

The `$(echo hi)` syntax runs a command and captures its `stdout`:

    echo $(hostname)                 # => example.com
    echo "_ $(hostname) _"           # => _ example.com _

#### Builtin Sub

The syntax `${.myproc $s arg2}` is called a *builtin sub*.  It's similar to a command
sub `$(myproc $s arg2)`, but it doesn't fork a process.  It can only capture
the output of `echo`, `printf`, and `write`.

It exists to efficiently build up long strings (like web pages) with sequences
of **commands** rather than expressions.  It can be used in config files which
can't perform I/O.

TODO: Builtin sub isn't yet implemented.

    proc p {
      echo start
      echo "_ $1 _"
      echo end
    }

    #var s = ${.p 'bean'}             # capture stdout as a variable
    #echo $s
    # =>
    # start
    # _ bean _
    # end

#### Expression Sub

The `$[myexpr]` syntax evaluates an expression and converts it to a string:

    echo $[a]                        # => ale
    echo $[1 + 2 * 3]                # => 7
    echo "_ $[1 + 2 * 3] _"          # => _ 7 _

<!-- TODO: safe substitution -->

#### Function Sub

As a shortcut for `$[f(x)]`, you can turn the result of a function into a
string with `$f(x)`:

    var foods = ['pea', 'nut']
    echo $join(foods)               # => peanut

Function subs **can't** be used in double quotes.  Use the longer expression
sub instead:

    echo "_ $[join(foods)] _"       # => _ peanut _

### Arrays of Strings: Globs, Brace Expansion, Splicing, and Splitting

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

    write {alice,bob}@example.com
    # =>
    # alice@example.com
    # bob@example.com

#### Array Splice

The `@` operator splices an array into a command:

    var myarray = %(ale bean)
    write S @myarray E
    # =>
    # S
    # ale
    # bean
    # E

#### Function Splice

You can also splice the result of a function returning an array:

    write -- @split('ale bean')
    # => 
    # ale
    # bean

Recall that *function sub* looks like `$join(mylist)`, which is consistent with
*function splice*.

#### Split Command Sub / Split Builtin Sub

There are also variants of *command sub* and *builtin sub* that split first:

    write @(seq 3)  # write gets 3 arguments
    # =>
    # 1
    # 2
    # 3

Builtin sub isn't implemented yet:

    proc digits {
      echo '4 5'
    }

    #write @{.digits}     # write gets 2 arguments
    # =>
    # 4
    # 5

## Command Language: I/O, Control Flow, Abstraction

### Simple Commands and Redirects

A simple command is a space-separated list of words, which are often unquoted.
Oil looks up the first word to determine if it's a `proc` or shell builtin.

    echo 'hello world'   # The shell builtin 'echo'

    proc greet(name) {   # A proc is a user-defined unit of code
      echo "hello $name"
    }

    # Now the first word will resolve to the proc
    greet alice            # => hello alice

If it's neither, then it's assumed to be an external command:

    ls -l /tmp           # The external 'ls' command

<!-- 
leaving off: aliases

TODO: We also need lazy arg lists: qtt | where [size > 10]
-->

You can **redirect** `stdin` and `stdout` of simple commands:

    echo hi > tmp.txt  # write to a file
    sort < tmp.txt

<!--
Here are a couple uses of `stderr`:

    ls /tmp 2> error.txt

    proc log(msg) {
      echo $msg >&2  # Write message to stderr
    }
-->

<!-- later: parse_amp fixes redirects? -->

### Pipelines

Pipelines are a powerful method manipulating text:

    ls | wc -l                       # count files in this directory
    find /bin -type f | xargs wc -l  # count files in a subtree

Pipelines may manipulate (lines of) text, binary data, JSON, TSV, etc.  More on
that below.

### Keywords for Variables

Constants can't be modified:

    const s = 'mystr'
    # setvar s = 'foo' would be an error

Modify variables with the `setvar` keyword:

    var num_beans = 12
    setvar num_beans = 13

A more complex example:

    var d = {name: 'bob', age: 42}  # dict literal
    setvar d->name = 'alice'        # d->name is a synonym for d['name']
    echo $[d->name]                 # => alice

That's most of what you need to know about assignments.  Advanced users may
want to use `setglobal` or `setref` in certain situations:

    var g = 1
    var h = 2
    proc demo(:out) {
      setglobal g = 42
      setref out = 43
    }
    demo :h  # pass a reference to h
    echo "$g $h"  # => 42 43

More details: [Variable Declaration and Mutation](variables.html).

### Conditionals: `if`, `case`

If statements use curly braces, and have optional `elif` and `else` clauses:

    if test --file foo {
      echo 'foo is a file'
      rm --verbose foo           # delete it
    } elif test --dir foo {
      echo 'foo is a directory'
    } else {
      echo 'neither'
    }

    if ! test --file README {    # The word ! inverts the exit status
      echo 'no README'
    }

When the condition is surrounded with `()`, it's a Python-like **expression**
rather than a command:

    if (num_beans > 0) {
      echo 'so many beans'
    }

    var done = false
    if (not done) {              # negate with 'not' operator
      echo "we aren't done"
    }

The case statement matches a string against **glob** patterns, and executes the
corresponding blocks:

    case $s {
      (*.py)
        echo 'python'
        rm --verbose $s
        ;;
      (*.sh)
        echo 'shell'
        ;;
      (*)
        echo 'neither'
        ;;
    }

(Shell style like `if foo; then ... fi` and `case $x in ...  esac` is also legal,
but discouraged in Oil code.)

### Loops: `for`, `while`

For loops iterate over **words**:

    for x in oil $num_beans {pea,coco}nut {
      echo $x
    }
    # =>
    # oil
    # 13
    # peanut
    # coconut

Like if statements, while loops have a **command** variant:

    while test --file lock {
      sleep 1
    }

and an **expression** variant in `()`:

    var x = 0
    while (x > 0) {
      echo "x = $x"
      # TODO: implement this
      #setvar x -= 1
    }

#### `break`, `continue`, `return`, `exit`

The `exit` **keyword** exits a process (it's not a shell builtin.)  The other 3
control flow keywords behave like they do in Python and JavaScript.

### Abstraction: `proc` and Blocks

Define units of reusable code with the `proc` keyword, and invoke them just
like any other command:

    proc mycopy(src, dest) {
      cp --verbose $src $dest
    }

    touch log.txt
    # the first word 'mycopy' is resolved as a proc
    mycopy log.txt /tmp  # runs cp --verbose

#### Ruby-like Blocks

Some builtins take blocks as arguments:

    shopt --unset errexit {  # Ignore errors
      may-fail foo
      may-fail bar
    }

    # TODO: fix crash
    #shopt --unset errexit {
    #  mycopy x y  # ignore errors
    #  mycopy y z  # ignore errors
    #}

Procs can also take blocks: TODO.

### Builtin Commands

**Shell builtins** like `cd` and `read` are the "standard library" of the
command language.  Each one takes various flags:

    cd -L .                      # follow symlinks

    echo foo | read --line       # read a line of stdin
    
Here are some categories of builtin:

- I/O: `echo  write  read`
- File system: `cd  test`
- Processes: `fork  wait  forkwait  exec`
- Interpreter settings: `shopt  shvar`
- Meta: `command  builtin  runproc  type  eval`
- Modules: `source  module`

(TODO: Make a more comprehensive list.)

## Expression Language: Python-like Types

Oil expressions are more like Python and JavaScript than the shell syntax to
perform similar operations.  For example, we write `if (x < y)` instead of `if
[ $x -lt $y ]`.

### Types and Literals: `Int`, `List`, `Dict`, ...

Let's go through Oil's Python-like data types and see the syntax for literals.

#### Null and Bool

JavaScript-like spellings are preferred for these three "atoms":

    var x = null

    var b1, b2 = true, false

    if (b1) {
      echo 'yes'
    }  # yes

For compatibility, you can also use `None`, `True`, and `False`.  But that
breaks the rule that types are spelled with capital letters (e.g. `Str`,
`Dict`).

#### Int

There are many ways to write integers:

    #var small, big = 42, 65_536         # TODO: _ not supported yet
    #echo "$small $big"                  # => 42 65536

    var hex, octal, binary = 0xFF, 0o755, 0b0101
    echo "$hex $octal $binary"           # => 255 493 5

<!--
TODO: not supported yet

Character literals can appear outside of strings, and are actually integers:

    #var newline, mu, a = \n, \u3bc, #'a'
    #echo "$newline $mu $a"
-->

#### Float

Floats are written like you'd expect, but the initial version of the Oil
language doesn't have them.  (Help wanted!)

    var small = 1.5e-10
    var big = 3.14

#### Str

The section *Three Kinds of String Literals* above describes `'single quoted'`,
`"double ${quoted}"`, and `$'c-style\n'` strings; as well as their multiline
variants.

More on strings:

- Oil has no Unicode type.  Strings in Oil are UTF-8 encoded in memory, like
  strings in Go.
- The syntax `%symbol` is used in eggex, and could be an interned string.

#### List

All lists can be expressed with Python-like literals:

    var foods = ['ale', 'bean', 'corn']
    var recursive = [1, [2, 3]]

Arrays of strings can be expressed with shell-like literals:

    var foods = %(ale bean corn)

#### Dict

Dicts have a JavaScript-like syntax with unquoted keys:

    var d = {name: 'bob', age: 42}

    echo $[d['name']]  # => bob

    var empty = {}

#### Block, Expr, and ArgList

These types are for reflection on Oil code.  Most Oil programs won't use them
directly.

- `Block`: an unevaluated code block.
  - rarely-used literal: `^(ls | wc -l)`
- `Expr`: an unevaluated expression.
  - rarely-used literal: `^[42 + a[i]]`
- `ArgList`: an argument list for procs.  It's a list of `Expr`.
  - rarely-used literal: `^{42, f(x), verbose = true}`

### Operators

Operators are generally the same as in Python:

    if (10 <= num_beans and num_beans < 20) {
      echo 'enough'
    }  # => enough

Oil has a few things that aren't in Python.  The `->` operator lets you use
unquoted keys for dicts:

    echo $[d->name]    # => bob
    echo $[d['name']]  # => bob (the same thing)

Equality can be approximate:

<!-- TODO: Implement ~== and ~~ -->

    var n = '42'
    #if (n ~== 42) {
    #  echo 'equal after type conversion'
    #}  # => equal after type conversion

Pattern matching is done with `~ !~` (regular expressions) and `~~ !~~` (glob):

    #if (s ~~ '*.py') {
    #  echo 'Python'
    #}

(See the Eggex section below for an example of `~`.)

Concatenation is `++` rather than `+` because it avoids confusion in the
presence of type conversion:

    var n = 42 + 1 
    echo $n           # => 43

    var y = $'ale\n' ++ "bean $n"
    echo $y
    # =>
    # ale
    # bean 43

<!--

#### Summary of Operators

- Arithmetic: `+ - * / // %` and `**` for exponentatiation
  - `/` always yields a float, and `//` is integer division
- Bitwise: `& | ^ ~`
- Logical: `and or not`
- Comparison: `==  <  >  <=  >=  in  'not in'` 
  - Approximate equality: `~==`
  - Eggex and glob match: `~  !~  ~~  !~~`
- Ternary: `1 if x else 0`
- Index and slice: `mylist[3]` and `mylist[1:3]`
  - `mydict->key` is a shortcut for `mydict['key']`
- Function and method call: `f(x, y)  s.startswith('prefix')`
- String and List: `++` for concatenation
  - This is a separate operator because the addition operator `+` does
    string-to-int conversion

TODO: What about list comprehensions?

- No string formatting with %
- No @ matrix multiply
-->

### Builtin Functions

These are the "standard library" for the expression language.

- For explicit word evaluation: `split()  join()  glob()  maybe()`  
- String and pattern: `find()  sub()`
- Collections: `len()  keys()  values()  items()  append()  extend()`

(TODO: Make a more comprehensive list.)

### Egg Expressions (Oil Regexes)

*Eggex* is a language for regular expressions which is technically part of Oil's
expression language.  It translates to POSIX ERE syntax, for use with tools
like `egrep`, `awk`, and `sed --regexp-extended` (GNU only).

It's designed to be readable and composable.  Short example:

    var D = / digit{1,3} /
    var ip_pattern = / D '.' D '.' D '.' D'.' /

    var z = '192.168.0.1'
    if (z ~ ip_pattern) {           # Use the ~ operator to match
      echo "$z looks like an IP address"
    }
    # =>
    # 192.168.0.1 looks like an IP address

See the [Egg Expressions doc](eggex.html) for details.

## Languages for Data (Interchange Formats)

In the sections above, we saw that Oil **code** consists of 3 interleaved
languages.  It's also useful to think of **data** as being described in a
language.

Versionless interchange formats like JSON often take the form of textual
languages.

<!-- TODO: Link to concepts and patterns -->

### Lines of Text (traditional), and QSN

Traditional Unix tools like `grep` and `awk` operate on streams of lines.  Oil
supports this style as well as any other shell.

But Oil also has [QSN: Quoted String Notation][QSN], an interchange format
which is borrowed from Rust's string literal notation.

[QSN]: qsn.html

It lets you encode arbitrary byte strings into a single (readable) line,
including those with newlines and terminal escape sequenecs.

Example:

    # A line with a tab char in the middle
    var a = $'pea\t' ++ $'42\n'

    # Print it to stdout
    write --qsn $a  # => 'pea\t42\n'

    # Write and read
    write --qsn $a | read --qsn --line
    if (_line == a) {
      echo 'serialized string to QSN and back'
    }  # => serialized string to QSN and back

### Structured: JSON, QTT

**Tree-shaped** data can be read and written as [JSON][]:

    var d = {key: 'value'}
    json write :d                 # dump variable d as JSON
    # =>
    # {
    #   "key": "value"
    # }

    echo '["ale", 42]' > example.json

    json read :d2 < example.json  # parse JSON into var d2
    pp cell d2                    # inspect the in-memory value
    # =>
    # ['ale', 42]

[JSON]: json.html
[QTT]: qtt.html

<!--
TODO:
- Fix pp cell output
- Use json write [d] syntax
-->

**Table-shaped** data can be read and written as [QTT: Quoted, Typed
Tables](qtt.html).  TODO: QTT isn't implemented yet!

<!-- Figure out the API.  Does it work like JSON?

Or I think we just implement
- basic filter/where, select, and sortby.
- QTT <=> sqlite conversion.  Are these drivers or what?
  - and then let you pipe output?

```none
    var t = {food: %(ale bean), price: [5.99, 0.40]}
    qtt write :t                  # dump variable t as QTT

    echo $'name:Str\tage:Int\nbob\t42\n' > example.qtt

    echo $'''
    name:Str\tage:Int
    bob\t42
    ''' > example.qtt

    qtt read :t2 < example.qtt    # parse QTT into var t2
    pp cell t2                    # inspect the in-memory value
    # =>
    # {name: ['bob'], age: [42]}  
```

Do we also need QTT space2tab or something?  For writing QTT inline.

More later:
- MessagePack (e.g. for shared library extension modules)
  - msgpack read, write?  I think user-defined function could be like this?
- SASH: Simple and Strict HTML?  For easy processing
- QTT: should also allow hex float representation for exactness
-->

## The Runtime Shared by OSH and Oil

Although we describe OSH and Oil as different languages, they use the **same**
interpreter under the hood.  This interpreter has various `shopt` flags that
are flipped for different behavior, e.g. with `shopt --set oil:all`.

Understanding this interpreter and its interface to the Unix kernel will help
you understand **both** languages!

### Interpreter Data Model

The [Interpreter State](interpreter-state.html) doc is **under construction**.
It will cover:

- Two separate namespaces (like Lisp 1 vs. 2):
  - **proc** namespace for procs as the first word
  - **variable** namespace
- The variable namespace has a **call stack**, for the local variables of a
  proc.
  - Each **stack frame** is a `{name -> cell}` mapping.
  - A **cell** has one of the above data types: `Null`, `Bool`, `Str`, etc.
  - A cell has `readonly`, `export`, and `nameref` **flags**.
- Boolean shell options with `shopt`: `parse_paren`, `simple_word_eval`, etc.
- String shell options with `shvar`: `IFS`, `_ESCAPE`, `_DIALECT`
- **Registers** that are silently modified by the interpreter
  - `$?` and `_status`
  - `$!` for the last PID
  - `_buffer`
  - `_this_dir`

### Process Model (the kernel)

The [Process Model](process-model.html) doc is **under construction**.  It will cover:

- Simple Commands, `exec` 
- Pipelines.  #[shell-the-good-parts](#blog-tag)
- `fork`, `forkwait`
- Command and process substitution.  (Compare with *builtin sub*).
- Related links:
  - [Oil's enhanced execution tracing](xtrace.html) (xtrace), which divides
    process-based concurrency into **synchronous** and **async** constructs.
  - [Three Comics For Understanding Unix
    Shell](http://www.oilshell.org/blog/2020/04/comics.html) (blog)


<!--
Process model additions: Capers, Headless shell 

some optimizations: See Oil starts fewer processes than other shells.
-->

## Summary

Oil is a large language that evolved from Unix shell.  But it's also simpler
than shell, so you can "forget" many of the bad parts like `[ $x -lt $y ]`.

Oil has these concepts:

- Word Language: for strings and arrays
- Command Language: for I/O, abstraction, and control flow
  - With a standard library of *shell builtins*
  - With Ruby-like blocks
- Expressions: for Python-like types
  - With a standard library of *builtin functions*
- Languages for Data
- A Runtime Shared By OSH and Oil

## Related Docs

- [Oil Language Idioms](idioms.html) - Oil side-by-side with shell.
- [Oil Language Influences](language-influences.html) - In addition to shell,
  Python, and JavaScript, Oil is influenced by Ruby, Perl, Awk, PHP, and more.
- [Oil Language Warts](warts.html) docuemnts syntax that may be surprising.
- [A Tour of the Oil Project](project-tour.html) (under construction).

## Appendix: Features Not Shown

### Advanced

These shell features are part of Oil, but aren't shown for brevity.

- The `fork` and `forkwait` builtins, for concurrent execution and subshells.
- Process Substitution: `diff <(sort left.txt) <(sort right.txt)`

### Not Yet Implemented

TODO: We need to implement these things!

- QTT parser, dumper, and builtins
- Capers: stateless coprocesses
- Defining functions in shared libraries?  What about shell builtins?

```none
# Unimplemented syntax:

qtt | filter [size > 10]  # lazy arg lists
echo ${x|html}            # formatters
echo ${x %.2f}            # statically-parsed printf

echo ${.myproc arg1}      # builtin sub

... cat file.txt          # convenient multiline syntax
  | sort
  | uniq -c
  ;
```

### Deprecated Shell Constructs

The shared interpreter supports many shell constructs that are deprecated:

- Most of what's in `${}`, like `${!indirect}`.  Use Oil functions instead.
- Assignment builtins like `local` and `declare`.  Use Oil keywords.
- Boolean expressions like `[[ x =~ $pat ]]`.  Use Oil expressions.
- Shell arithmetic like `$(( x + 1 ))` and `(( y = x ))`.  Use Oil expressions.
- The `until` loop can always be replaced with a `while` loop
- Oil code uses shell's `||` and `&&` in limited circumstances, since `errexit`
  is on by default.

## Appendix: Example of an Oil Module

Oil can be used to write simple "shell scripts" or longer programs.  It has
*procs* and *modules* to help with the latter.

(TODO: Tighten up and test this this example.)

A module is just a file, like this:

```none
#!/usr/bin/env oil
### Deploy script

module main || return 0     # declaration and "include guard"
use bin cp mkdir            # optionally declare the binaries used

source $_this_dir/util.oil  # contains helpers like "log"

const DEST = '/tmp'

proc my-sync(@files) {
  ### Sync files and show which ones

  cp --verbose @files $DEST
}

proc main {
  mkdir -p $DEST

  log "Copying source files"
  my-sync *.py {build,test}.sh

  if test --dir /tmp/logs {
    cd /tmp/logs

    log "Copying logs"
    my-sync *.log
  }
}

main @ARGV                  # The only top-level statement
```

<!--
TODO:
- Also show flags parsing?
- Show longer examples where it isn't boilerplate
-->

For something this small, you usually wouldn't bother with the boilerplate.

But this example illustrates the idea, which is that these commands appear at
the top level: `proc`, `const`, `module`, `source`, and `use`.
