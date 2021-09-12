---
default_highlighter: oil-sh
---

A Tour of the Oil Language
==========================

<!-- author's note about example names

- people: alice, bob
- nouns: ale, bean
  - peanut, coconut
- 42 for integers
-->

This document describes the [Oil language]($xref:oil-language) from **clean
slate** perspective.  Knowledge of Unix shell or the compatible [OSH
language]($xref:osh-language) isn't assumed.  But shell users will see
similarities, simplifications, and upgrades.

Remember, Oil is for Python and JavaScript users who avoid shell!  See the
[project FAQ][FAQ] for more color on that.

[FAQ]: https://www.oilshell.org/blog/2021/01/why-a-new-shell.html
[path dependence]: https://en.wikipedia.org/wiki/Path_dependence

This document is **long** because it demonstrates nearly every feature of the
language.  You may want to read it in multiple sittings, or read [The Simplest
Explanation of
Oil](https://www.oilshell.org/blog/2020/01/simplest-explanation.html) first.

A summary of what follows:

1. Oil has interleaved *word*, *command*, and *expression* languages.
   - The command language has Ruby-like *blocks*, and the expression language
     has Python-like *data types*.
2. Oil has two kinds of *builtins* that form the "standard library".
3. Languages for *data* (like [JSON][]) are complementary to Oil code.
4. OSH and Oil share both an *interpreter data model* and a *process model*
   (provided by the Unix kernel).  Understanding these common models will make
   you both a better shell user and Oil user.

Keep those 4 points in mind as you read the details below.

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
    json write :d  # :d refers to the variable d
    # =>
    # {
    #   "name": "bob",
    #   "age": 42,
    # }

## Word Language: Expressions for Strings (and Arrays)

Let's describe the word language first, and then talk about commands and
expressions.  Words are a rich language because **strings** are a central
concept in shell.

### Three Kinds of String Literals

You can choose the type of quote that's most convenient to write a given
string.

#### Single-Quoted, Double-Quoted, and C-Style

Double-quoted strings allow **interpolation with `$`**:

    var person = 'alice'
    echo "hi $person, $(echo bye)"  # => hi bob, bye

Denote operators by escaping them with `\`:

    echo "\$ \" \\ "                # => $ " \

In single-quoted strings, all characters are **literal** (except `'`, which
can't be denoted):

    echo 'c:\Program Files\'        # => c:\Program Files\

C-style strings look like `$'foo'` and respect backslash **character escapes**:

    echo $' A is \x41 \n line two, with backslash \\'
    # =>
    #  A is A
    #  line two, with backslash \

(Note that the `$` before the quote does **not** mean "interpolation".  It's an
unfortunate syntax collision.)

#### Multiline Strings

Multiline strings are surrounded with triple quotes.  They come in the same
three varieties, and leading whitespace is stripped in a convenient way.

    sort <<< """
    var sub: $x
    command sub: $(echo hi)
    expression sub: $[x + 3]
    """
    # =>
    # command sub: hi
    # expression sub: 9
    # var sub: 6

    sort <<< '''
    $2.00  # literal $, no interpolation
    $1.99
    '''
    # =>
    # $1.99
    # $2.00

    sort <<< $'''
    C\tD
    A\tB
    '''
    # =>
    # A        B
    # C        D


(Use multiline strings instead of shell's [here docs]($xref:here-doc).)

### Five Kinds of Substitution

Oil has syntax for 5 types of substitution, all of which start with `$`.  These
constructs convert data to a **string**:

1. Variables
2. The output of commands
3. The output of builtins (a performance optimization)
4. Expressions
5. The results of functions (syntactic sugar, since functions are expressions)

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

    proc p(x) {
      echo start
      echo "_ $x _"
      echo end
    }

    # var s = ${.p 'bean'}             # capture stdout as a variable
    # echo $s
    # =>
    # start
    # _ bean _
    # end

#### Expression Sub

The `$[myexpr]` syntax evaluates an expression and converts it to a string:

    echo $[a]                        # => ale
    echo $[1 + 2 * 3]                # => 7
    echo "_ $[1 + 2 * 3] _"          # => _ 7 _

<!-- TODO: safe substitution with $[a] -->

#### Function Sub

As a shortcut for `$[f(x)]`, you can turn the result of a function into a
string with `$f(x)`:

    var foods = ['pea', 'nut']
    echo $join(foods)               # => peanut

Function subs **can't** be used in double quotes, so `echo "_ $join(foods) _"`
is invalid.  Use the longer *expression sub* instead:

    echo "_ $[join(foods)] _"       # => _ peanut _

### Arrays of Strings: Globs, Brace Expansion, Splicing, and Splitting

There are four constructs that evaluate to an **list of strings**, rather than
a single string.

#### Globs

Globs like `*.py` evaluate to a list of files.

    touch foo.py bar.py  # create the files
    write *.py
    # =>
    # foo.py
    # bar.py

If no files match, it evaluates to an empty list (`[]`).

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

    # write @{.digits}     # write gets 2 arguments
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
    greet alice          # => hello alice

If it's neither, then it's assumed to be an external command:

    ls -l /tmp           # The external 'ls' command

<!-- 
TODO: We also need lazy arg lists: qtt | where (size > 10)
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

Pipelines are a powerful method manipulating data streams:

    ls | wc -l                       # count files in this directory
    find /bin -type f | xargs wc -l  # count files in a subtree

The stream may contain (lines of) text, binary data, JSON, TSV, and more.
Details below.

### Keywords for Using Variables

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
want to use `setglobal` or `setref` in certain situations.

<!--
    var g = 1
    var h = 2
    proc demo(:out) {
      setglobal g = 42
      setref out = 43
    }
    demo :h  # pass a reference to h
    echo "$g $h"  # => 42 43
-->

More details: [Variable Declaration and Mutation](variables.html).

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

While loops can use a **command** as the termination condition:

    while test --file lock {
      sleep 1
    }

Or an **expression**, which is surrounded in `()`:

    var i = 3
    while (i < 6) {
      echo "i = $i"
      setvar i += 1
    }
    # =>
    # i = 3
    # i = 4
    # i = 5

### Conditionals: `if`, `case`

If statements test the exit code of a command, and have optional `elif` and
`else` clauses:

    if test --file foo {
      echo 'foo is a file'
      rm --verbose foo     # delete it
    } elif test --dir foo {
      echo 'foo is a directory'
    } else {
      echo 'neither'
    }

Invert with the exit with `!`:

    if ! grep alice /etc/passwd { 
      echo 'alice is not a user'
    }

As with `while` loops, the condition can also be an **expression** wrapped in
`()`:

    if (num_beans > 0) {
      echo 'so many beans'
    }

    var done = false
    if (not done) {        # negate with 'not' operator (contrast with !)
      echo "we aren't done"
    }

The case statement matches a string against **glob** patterns, and executes the
corresponding block:

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

### Error Handling

If statements are also used for **error handling**:

    if ! cp foo /tmp {
      echo 'error copying'
    }

When invoking a `proc` in the condition, wrap it with the `try` builtin:

    if ! try myproc {
      echo 'failed'
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

    shopt --unset errexit {  # ignore errors
      mycopy ale /tmp
      mycopy bean /bin
    }

For more details, see [Procs, Blocks, and Funcs](proc-block-func.html)
(under construction).

<!-- TODO: Procs can also take blocks. -->

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

<!-- TODO: Link to a comprehensive list of builtins -->

Syntax quirk: builtins like `read` use the colon as a "pseudo-sigil":

    var x = ''
    whoami | read :x  # mutate variable x

It's just a visual indication that the string arg is a variable name.

## Expression Language: Python-like Types

Oil expressions are more like Python and JavaScript than traditional shell
syntax.  For example, we write `if (x < y)` instead of `if [ $x -lt $y ]`.

### Types and Literals: `Int`, `List`, `Dict`, ...

Let's go through Oil's Python-like data types and see the syntax for literals.

#### Null and Bool

Oil uses JavaScript-like spellings these three "atoms":

    var x = null

    var b1, b2 = true, false

    if (b1) {
      echo 'yes'
    }  # => yes

#### Int

There are many ways to write integers:

    var small, big = 42, 65_536
    echo "$small $big"                  # => 42 65536

    var hex, octal, binary = 0x0001_0000, 0o755, 0b0001_0101
    echo "$hex $octal $binary"           # => 65536 493 21

"Runes" are integers that represent Unicode code points.  The'yre not common in
Oil code, but can make certain string algorithms more readable.

    # Pound rune literals are similar to ord('A')
    const a = #'A'

    # Backslash rune literals can appear outside of quotes
    const newline = \n  # Remember this is an integer
    const backslash = \\  # ditto

    # Unicode rune literal is syntactic sugar for 0x3bc
    const mu = \u{3bc}

    echo "chars $a $newline $backslash $mu"  # => chars 65 10 92 956

#### Float

Floats are written like you'd expect, but the initial version of the Oil
language doesn't have them.  (Help wanted!)

    var small = 1.5e-10
    var big = 3.14

#### Str

See the section above called *Three Kinds of String Literals*.  It described
`'single quoted'`, `"double ${quoted}"`, and `$'c-style\n'` strings; as well as
their multiline variants.

More on strings:

- Oil has no Unicode type.  Strings in Oil are UTF-8 encoded in memory, like
  strings in Go.

<!--
- The syntax `%symbol` is used in eggex, and could be an interned string.
-->

#### List (and Arrays)

All lists can be expressed with Python-like literals:

    var foods = ['ale', 'bean', 'corn']
    var recursive = [1, [2, 3]]

As a special case, list of strings are called **arrays**.  They can be be
expressed with shell-like literals:

    var foods = %(ale bean corn)

#### Dict

Dicts have a JavaScript-like syntax with unquoted keys:

    var d = {name: 'bob', age: 42, 'key with spaces': 'val'}

    # These are synonyms.  Fatal exception if the key doesn't exist.
    var v1 = d['name']
    var v2 = d->name 

    # Using them in a command (with expression sub):
    echo $[d['name']]             # => bob
    echo $[d->name]               # => bob

    echo $[d['key with spaces']]  # => val

    var empty = {}

#### Block, Expr, and ArgList

These types are for reflection on Oil code.  Most Oil programs won't use them
directly.

- `Block`: an unevaluated code block.
  - rarely-used literal: `^(ls | wc -l)`
- `Expr`: an unevaluated expression.
  - rarely-used literal: `^[42 + a[i]]`
- `ArgList`: an argument list for procs.  It's a list of lazily evaluated
  `Expr`.
  - rarely-used literal: `^{42, f(x), verbose = true}`

<!-- TODO: implement Block, Expr, ArgList types (variants of value) -->

### Operators

Operators are generally the same as in Python:

    if (10 <= num_beans and num_beans < 20) {
      echo 'enough'
    }  # => enough

Oil has a few operators that aren't in Python.  The `->` operator lets you use
unquoted keys for dicts:

    echo $[d->name]    # => bob
    echo $[d['name']]  # => bob (the same thing)

Equality can be approximate or exact:

    var n = ' 42 '
    if (n ~== 42) {
      echo 'equal after type conversion'
    }  # => equal after type conversion

    if (n === 42) {
      echo "not reached because strings and ints aren't equal"
    }

<!-- TODO: is n === 42 a type error? -->

Pattern matching can be done with globs (`~~` and `!~~`):

    const filename = 'foo.py'
    if (filename ~~ '*.py') {
      echo 'Python'
    }  # => Python

    if (filename !~~ '*.sh') {
      echo 'not shell'
    }  # => not shell

or regular expressions (`~` and `!~`).  See the Eggex section below for an
example of the latter.

Concatenation is `++` rather than `+` because it avoids confusion in the
presence of type conversion:

    var n = 42 + 1    # string plus int does implicit conversion
    echo $n           # => 43

    var y = 'ale ' ++ "bean $n"  # concatenation
    echo $y  # => ale bean 43

<!--
TODO: change example above
    var n = '42' + 1    # string plus int does implicit conversion
-->

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
-->

### Builtin Functions

In addition to shell-like builtins, Oil also has builtin **functions**.  These
are like the "standard library" for the expression language.  Examples:

- Explicit word evaluation: `split()  join()  glob()  maybe()`  
- String and pattern: `find()  sub()`
- Collections: `len()  keys()  values()  items()  append()  extend()`

<!-- TODO: Make a comprehensive list of func builtins. -->

### Egg Expressions (Oil Regexes)

*Eggex* is a language for regular expressions which is part of Oil's expression
language.  It translates to POSIX ERE syntax, for use with tools like `egrep`,
`awk`, and `sed --regexp-extended` (GNU only).

It's designed to be readable and composable.  Example:

    var D = / digit{1,3} /
    var ip_pattern = / D '.' D '.' D '.' D'.' /

    var z = '192.168.0.1'
    if (z ~ ip_pattern) {           # Use the ~ operator to match
      echo "$z looks like an IP address"
    }  # => 192.168.0.1 looks like an IP address

    if (z !~ / '.255' %end /) {
      echo "doesn't end with .255"
    }  # => doesn't end with .255"

See the [Egg Expressions doc](eggex.html) for details.

## Interlude

### Summary

Here are the 3 languages we saw in the last 3 sections:

1. **Words** evaluate to a string, or list of strings.  This includes:
   - literals like `'mystr'`
   - substitutions like `${x}` and `$(hostname)`
   - globs like `*.sh`
2. **Commands** are used for
   - I/O: pipelines, builtins like `read`
   - control flow: `if`, `for`
   - abstraction: `proc`
3. **Expressions** on typed data are borrowed from Python, with some JavaScript
   influence.
   - Lists: `['ale', 'bean']` or `%(ale bean)`
   - Dicts: `{name: 'bob', age: 42}`
   - Functions: `split('ale bean')` and `join(['pea', 'nut'])`

### More Examples

How does these languages work together?  Here are two examples.

(1) This *command*:

    write hello $name $[d['age'] + 1]
    # =>
    # hello
    # world
    # 43

consists of **four** *words*.  The fourth word is an *expression sub* `$[]`.

(2) The *expression* on the right hand side of `=` concatenates two strings:

    var food = 'ale ' ++ $(echo bean | tr a-z A-Z)
    write $food  # => ale BEAN

The second string is a *command sub*, which captures `stdout` as a string.

So words, commands, and expressions are **mutually recursive**.  If you're a
conceptual person, skimming [Syntactic Concepts](syntactic-concepts.html) may
help you understand this on a deeper level.

<!--
One way to think about these sublanguages is to note that the `|` character
means something different in each context:

- In the command language, it's the pipeline operator, as in `ls | wc -l`
- In the word language, it's only valid in a literal string like `'|'`, `"|"`,
  or `\|`.  (It's also used in `${x|html}`, which formats a string.)
- In the expression language, it's the bitwise OR operator, as in Python and
  JavaScript.
-->

## Languages for Data (Interchange Formats)

In addition to languages for **code**, Oil also deals with languages for
**data**.  [JSON]($xref) is a prominent example of the latter.

<!-- TODO: Link to slogans, fallacies, and concepts -->

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
    var mystr = $'pea\t' ++ $'42\n'

    # Print it to stdout
    write --qsn $mystr  # => 'pea\t42\n'

    # Write and read
    write --qsn $mystr h| read --qsn --line
    if (_line === mystr) {
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
- Use json write (d) syntax
-->

**Table-shaped** data can be read and written as [QTT: Quoted, Typed
Tables](qtt.html).  (TODO: not yet implemented.)

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

Oil is a large language that evolved from Unix shell.  It has Python-like
expressions on typed data, and Ruby-like command blocks.

Even though it's large, you can "forget" the bad parts of shell like `[ $x -lt
$y ]`.

These concepts are central to Oil:

1. Interleaved *word*, *command*, and *expression* languages.
2. A standard library of *shell builtins*, as well as *builtin functions*
3. Languages for *data*
4. A *runtime* shared by OSH and Oil


## Related Docs

- [Oil Language Idioms](idioms.html) - Oil side-by-side with shell.
- [Oil Language Influences](language-influences.html) - In addition to shell,
  Python, and JavaScript, Oil is influenced by Ruby, Perl, Awk, PHP, and more.
- [A Feel For Oil's Syntax](syntax-feelings.html) - Some thoughts that may help
  you remember the syntax.
- [Oil Language Warts](warts.html) docuemnts syntax that may be surprising.
- [A Tour of the Oil Project](project-tour.html) (under construction).

## Appendix: Features Not Shown

### Advanced

These shell features are part of Oil, but aren't shown for brevity.

- The `fork` and `forkwait` builtins, for concurrent execution and subshells.
- Process Substitution: `diff <(sort left.txt) <(sort right.txt)`

### Deprecated Shell Constructs

The shared interpreter supports many shell constructs that are deprecated:

- Oil code uses shell's `||` and `&&` in limited circumstances, since `errexit`
  is on by default.
- Most of what's in `${}`, like `${!indirect}`.  Use Oil functions instead.
- Assignment builtins like `local` and `declare`.  Use Oil keywords.
- Boolean expressions like `[[ x =~ $pat ]]`.  Use Oil expressions.
- Shell arithmetic like `$(( x + 1 ))` and `(( y = x ))`.  Use Oil expressions.
- The `until` loop can always be replaced with a `while` loop

### Not Yet Implemented

This document mentions a few constructs that aren't yet implemented.  Here's a
summary:

```none
# Unimplemented syntax:

my-qtt | filter [size > 10]  # lazy arg lists
qtt read :x < input.qtt      # qtt builtin
echo ${x|html}               # formatters
echo ${x %.2f}               # statically-parsed printf

echo ${.myproc arg1}         # builtin sub

... cat file.txt             # convenient multiline syntax
  | sort
  | uniq -c
  ;
```

<!--

- Capers: stateless coprocesses
- Functions
  - Unifying with procs and builtin sub
  - Defining in Oil and JavaScript
-->

## Appendix: Example of an Oil Module

Oil can be used to write simple "shell scripts" or longer programs.  It has
*procs* and *modules* to help with the latter.

A module is just a file, like this:

```
#!/usr/bin/env oil
### Deploy script

module main || return 0         # declaration, "include guard"
use bin cp mkdir                # optionally declare binaries used

source $_this_dir/lib/util.oil  # defines 'log' helper

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

main @ARGV                      # The only top-level statement
```

<!--
TODO:
- Also show flags parsing?
- Show longer examples where it isn't boilerplate
-->

You wouldn't bother with the boilerplate for something this small.  But this
example illustrates the idea, which is that the top level often contains these
words: `proc`, `const`, `module`, `source`, and `use`.

