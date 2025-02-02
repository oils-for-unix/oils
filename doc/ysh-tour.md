---
default_highlighter: oils-sh
---

A Tour of YSH
=============

<!-- author's note about example names

- people: alice, bob
- nouns: ale, bean
  - peanut, coconut
- 42 for integers
-->

This doc describes the [YSH]($xref) language from **clean slate**
perspective.  We don't assume you know Unix shell, or the compatible
[OSH]($xref).  But shell users will see the similarity, with simplifications
and upgrades.

Remember, YSH is for Python and JavaScript users who avoid shell!  See the
[project FAQ][FAQ] for more color on that.

[FAQ]: https://www.oilshell.org/blog/2021/01/why-a-new-shell.html

This document is **long** because it demonstrates nearly every feature of the
language.  You may want to read it in multiple sittings, or read [The Simplest
Explanation of
Oil](https://www.oilshell.org/blog/2020/01/simplest-explanation.html) first.
(Until 2023, YSH was called the "Oil language".)


Here's a summary of what follows:

1. YSH has interleaved *word*, *command*, and *expression* languages.
   - The command language has Ruby-like *blocks*, and the expression language
     has Python-like *data types*.
2. YSH has both builtin *commands* like `cd /tmp`, and builtin *functions* like
   `join()`.
3. Languages for *data*, like [JSON][], are complementary to YSH code.
4. OSH and YSH share both an *interpreter data model* and a *process model*
   (provided by the Unix kernel).  Understanding these common models will make
   you both a better shell user and YSH user.

Keep these points in mind as you read the details below.

[JSON]: https://json.org

<div id="toc">
</div>

## Preliminaries

Start YSH just like you start bash or Python:

<!-- oils-sh below skips code block extraction, since it doesn't run -->

```sh-prompt
bash$ ysh                # assuming it's installed

ysh$ echo 'hello world'  # command typed into YSH
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

You can also type commands into a file like `hello.ysh`.  This is a complete
YSH program, which is identical to a shell program:

    echo 'hello world'     # => hello world

### A Taste of YSH

Unlike shell, YSH has `var` and `const` keywords:

    const name = 'world'   # const is rarer, used the top-level
    echo "hello $name"     # => hello world

They take rich Python-like expressions on the right:

    var x = 42             # an integer, not a string
    setvar x = x * 2 + 1   # mutate with the 'setvar' keyword

    setvar x += 5          # Increment by 5
    echo $x                # => 6

    var mylist = [x, 7]    # two integers [6, 7]

Expressions are often surrounded by `()`:

    if (x > 0) {
      echo 'positive'
    }  # => positive

    for i, item in (mylist) {  # 'mylist' is a variable, not a string
      echo "[$i] item $item"
    }
    # =>
    # [0] item 6
    # [1] item 7

YSH has Ruby-like blocks:

    cd /tmp {
      echo hi > greeting.txt  # file created inside /tmp
      echo $PWD               # => /tmp
    }
    echo $PWD                 # prints the original directory

And utilities to read and write JSON:

    var person = {name: 'bob', age: 42}
    json write (person)
    # =>
    # {
    #   "name": "bob",
    #   "age": 42,
    # }

    echo '["str", 42]' | json read  # sets '_reply' variable by default

The `=` keyword evaluates and prints an expression:

    = _reply
    # => (List)   ["str", 42]

(Think of it like `var x = _reply`, without the `var`.)

## Word Language: Expressions for Strings (and Arrays)

Let's describe the word language first, and then talk about commands and
expressions.  Words are a rich language because **strings** are a central
concept in shell.

### Unquoted Words

Words denote strings, but you often don't need to quote them:

    echo hi  # => hi

Quotes are useful when a string has spaces, or punctuation characters like `( )
;`.

### Three Kinds of String Literals

You can choose the style that's most convenient to write a given string.

#### Double-Quoted, Single-Quoted, and J8 strings (like JSON)

Double-quoted strings allow **interpolation**, with `$`:

    var person = 'alice'
    echo "hi $person, $(echo bye)"  # => hi alice, bye

Write operators by escaping them with `\`:

    echo "\$ \" \\ "                # => $ " \

In single-quoted strings, all characters are **literal** (except `'`, which
can't be expressed):

    echo 'c:\Program Files\'        # => c:\Program Files\

If you want C-style backslash **character escapes**, use a J8 string, which is
like JSON, but with single quotes:

    echo u' A is \u{41} \n line two, with backslash \\'
    # =>
    #  A is A
    #  line two, with backslash \

The `u''` strings are guaranteed to be valid Unicode (unlike JSON).  You can
also use `b''` strings:

    echo b'byte \yff'  # Byte that's not valid unicode, like \xff in C.
                       # Don't confuse it with \u{ff}.

#### Multi-line Strings

Multi-line strings are surrounded with triple quotes.  They come in the same
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

    sort <<< u'''
    C\tD
    A\tB
    '''  # b''' strings also supported
    # =>
    # A        B
    # C        D

(Use multiline strings instead of shell's [here docs]($xref:here-doc).)

### Three Kinds of Substitution

YSH has syntax for 3 types of substitution, all of which start with `$`.  That
is, you can convert any of these things to a **string**:

1. Variables
2. The output of commands
3. The value of expressions

#### Variable Sub

The syntax `$a` or `${a}` converts a variable to a string:

    var a = 'ale'
    echo $a                          # => ale
    echo _${a}_                      # => _ale_
    echo "_ $a _"                    # => _ ale _

The shell operator `:-` is occasionally useful in YSH:

    echo ${not_defined:-'default'}   # => default

#### Command Sub

The `$(echo hi)` syntax runs a command and captures its `stdout`:

    echo $(hostname)                 # => example.com
    echo "_ $(hostname) _"           # => _ example.com _

#### Expression Sub

The `$[myexpr]` syntax evaluates an expression and converts it to a string:

    echo $[a]                        # => ale
    echo $[1 + 2 * 3]                # => 7
    echo "_ $[1 + 2 * 3] _"          # => _ 7 _

<!-- TODO: safe substitution with "$[a]"html -->

### Arrays of Strings: Globs, Brace Expansion, Splicing, and Splitting

There are four constructs that evaluate to a **list of strings**, rather than a
single string.

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

#### Splicing

The `@` operator splices an array into a command:

    var myarray = :| ale bean |
    write S @myarray E
    # =>
    # S
    # ale
    # bean
    # E

You also have `@[]` to splice an expression that evaluates to a list:

    write -- @[split('ale bean')]
    # => 
    # ale
    # bean

Each item will be converted to a string.

#### Split Command Sub / Split Builtin Sub

There's also a variant of *command sub* that decodes J8 lines into a sequence
of strings:

    write @(seq 3)  # write is passed 3 args
    # =>
    # 1
    # 2
    # 3

## Command Language: I/O, Control Flow, Abstraction

### Simple Commands

A simple command is a space-separated list of words.  YSH looks up the first
word to determine if it's a builtin command, or a user-defined `proc`.

    echo 'hello world'   # The shell builtin 'echo'

    proc greet (name) {  # Define a unit of code
      echo "hello $name"
    }

    # The first word now resolves to the proc you defined
    greet alice          # => hello alice

If it's neither, then it's assumed to be an external command:

    ls -l /tmp           # The external 'ls' command

Commands accept traditional string arguments, as well as typed arguments in
parentheses:

    # 'write' is a string arg; 'x' is a typed expression arg
    json write (x)

<!--
Block args are a special kind of typed arg:

    cd /tmp { 
      echo $PWD
    }
-->

### Redirects

You can **redirect** `stdin` and `stdout` of simple commands:

    echo hi > tmp.txt  # write to a file
    sort < tmp.txt

Here are the most common idioms for using `stderr` (identical to shell):

    ls /tmp 2>errors.txt
    echo 'fatal error' >&2

### ARGV and ENV

The `ARGV` list holds the arguments passed to the shell:

    var num_args = len(ARGV)
    ls /tmp @ARGV            # pass shell's arguments through

---

You can add to the environment of a new process with a *prefix binding*:

    PYTHONPATH=vendor ./demo.py

The `ENV` object reflects the current environment:

    echo $[ENV.PYTHONPATH]   # => vendor

### Pipelines

Pipelines are a powerful method manipulating data streams:

    ls | wc -l                       # count files in this directory
    find /bin -type f | xargs wc -l  # count files in a subtree

The stream may contain (lines of) text, binary data, JSON, TSV, and more.
Details below.

### Multi-line Commands

The `...` prefix lets you write long commands, pipelines, and `&&` chains
without `\` line continuations.

    ... find /bin               # traverse this directory and
        -type f -a -executable  # print executable files
      | sort -r                 # reverse sort
      | head -n 30              # limit to 30 files
      ;

When this mode is active:

- A single newline behaves like a space
- A blank line (two newlines in a row) is illegal, but a line that has only a
  comment is allowed.  This prevents confusion if you forget the `;`
  terminator.

### `var`, `setvar`, `const` to Declare and Mutate

Constants can't be modified:

    const myconst = 'mystr'
    # setvar myconst = 'foo' would be an error

Modify variables with the `setvar` keyword:

    var num_beans = 12
    setvar num_beans = 13

A more complex example:

    var d = {name: 'bob', age: 42}  # dict literal
    setvar d.name = 'alice'         # d.name is a synonym for d['name']
    echo $[d.name]                  # => alice

That's most of what you need to know about assignments.  Advanced users may
want to use `setglobal` or `call myplace->setValue(42)` in certain situations.

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

More info: [Variable Declaration and Mutation](variables.html).

### `for` Loop

#### Words

Shell-style for loops iterate over **words**:

    for word in 'oils' $num_beans {pea,coco}nut {
      echo $word
    }
    # =>
    # oils
    # 13
    # peanut
    # coconut

You can ask for the loop index with `i,`:

    for i, word in README.md *.py {
      echo "$i - $word"
    }
    # =>
    # 0 - README.md
    # 1 - __init__.py

#### Typed Data

To iterate over a typed data, use parentheses around an **expression**.  The
expression should evaluate to an integer `Range`, `List`, `Dict`, or `io.stdin`.

Range:

    for i in (3 ..< 5) {  # range operator ..<
      echo "i = $i"
    }
    # =>
    # i = 3
    # i = 4

List:

    var foods = ['ale', 'bean']
    for item in (foods) {
      echo $item
    }
    # =>
    # ale
    # bean

Again, you can request the index with `for i, item in ...`.

---

There are **three** ways of iterating over a `Dict`:

    var mydict = {pea: 42, nut: 10}
    for key in (mydict) {
      echo $key
    }
    # =>
    # pea
    # nut

    for key, value in (mydict) {
      echo "$key $value"
    }
    # =>
    # pea - 42
    # nut - 10

    for i, key, value in (mydict) {
      echo "$i $key $value"
    }
    # =>
    # 0 - pea - 42
    # 1 - nut - 10

That is, if you ask for two things, you'll get the key and value.  If you ask
for three, you'll also get the index.

(One way to think of it: `for` loops in YSH have the functionality Python's
`enumerate()`, `items()`, `keys()`, and `values()`.)

---

The `io.stdin` object iterates over lines:

    for line in (io.stdin) {
      echo $line
    }
    # lines are buffered, so it's much faster than `while read --raw-line`

<!--
TODO: Str loop should give you the (UTF-8 offset, rune)
Or maybe just UTF-8 offset?  Decoding errors could be exceptions, or Unicode
replacement.
-->

### `while` Loop

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

### Conditionals

#### `if elif` 

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

Invert the exit code with `!`:

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

#### `case` 

The case statement is a series of conditionals and executable blocks.  The
condition can be either an unquoted glob pattern like `*.py`, an eggex pattern
like `/d+/`, or a typed expression like `(42)`:

    var s = 'README.md'
    case (s) {
      *.py           { echo 'Python' }
      *.cc | *.h     { echo 'C++' }
      *              { echo 'Other' }
    }
    # => Other

    case (s) {
      / dot* '.md' / { echo 'Markdown' }
      (30 + 12)      { echo 'the integer 42' }
      (else)         { echo 'neither' }
    }
    # => Markdown


<!--
(Shell style like `if foo; then ... fi` and `case $x in ...  esac` is also
legal, but discouraged in YSH code.)
-->

### Error Handling

If statements are also used for **error handling**.  Builtins and external
commands use this style:

    if ! test -d /bin {
      echo 'not a directory'
    }

    if ! cp foo /tmp {
      echo 'error copying'  # any non-zero status
    }

Procs use this style (because of shell's *disabled `errexit` quirk*):

    try {
      myproc
    }
    if failed {
      echo 'failed'
    }

For a complete list of examples, see [YSH Error
Handling](ysh-error.html).  For design goals and a reference, see [YSH
Fixes Shell's Error Handling](error-handling.html).

#### exit, break, continue, return

The `exit` **keyword** exits a process.  (It's not a shell builtin.)

The other 3 control flow keywords behave like they do in Python and JavaScript.

### Shell-like `proc`

You can define units of code with the `proc` keyword.  A `proc` is like a
*procedure* or *process*.

    proc mycopy (src, dest) {
      ### Copy verbosely

      mkdir -p $dest
      cp --verbose $src $dest
    }

The `###` line is a "doc comment".  Simple procs like this are invoked like a
shell command:

    touch log.txt
    mycopy log.txt /tmp   # first word 'mycopy' is a proc

Procs have many features, including **four** kinds of arguments:

1. Word args (which are always strings)
1. Typed, positional args
1. Typed, named args
1. A final block argument, which may be written with `{ }`.

At the call site, they can look like any of these forms:

    ls /tmp                      # word arg

    json write (d)               # word arg, then positional arg

    try {
      error 'failed' (status=9)  # word arg, then named arg
    }

    cd /tmp { echo $PWD }        # word arg, then block arg

    pp value ([1, 2])            # positional, typed arg 

<!-- TODO: lazy arg list: ls8 | where [age > 10] -->

At the definition site, the kinds of parameters are separated with `;`, similar
to the Julia language:

    proc p2 (word1, word2; pos1, pos2, ...rest_pos) {
      echo "$word1 $word2 $[pos1 + pos2]"
      json write (rest_pos)
    }

    proc p3 (w ; ; named1, named2, ...rest_named; block) {
      echo "$w $[named1 + named2]"
      call io->eval(block)
      json write (rest_named)
    }

    proc p4 (; ; ; block) {
      call io->eval(block)
    }

YSH also has Python-like functions defined with `func`.  These are part of the
expression language, which we'll see later.

For more info, see the [Guide to Procs and Funcs](proc-func.html).

### Ruby-like Block Arguments

A block is a value of type `Command`.  For example, `shopt` is a builtin
command that takes a block argument:

    shopt --unset errexit {  # ignore errors
      cp ale /tmp
      cp bean /bin
    }

In this case, the block doesn't form a new scope.

#### Block Scope / Closures

However, by default, block arguments capture the frame they're defined in.
This means they obey *lexical scope*.

Consider this proc, which accepts a block, and runs it:

    proc do-it (; ; ; block) {
      call io->eval(block)
    }

When the block arg is passed, the enclosing stack frame is captured.  This
means that code inside the block can use variables in the captured frame:

    var x = 42
    do-it {         
      echo "x = $x"  # outer x is visible LATER, when the block is run    
    }

- [Feature Index: Closures](ref/feature-index.html#Closures)

### Builtin Commands

**Shell builtins** like `cd` and `read` are the "standard library" of the
command language.  Each one takes various flags:

    cd -L .                      # follow symlinks

    echo foo | read --all        # read all of stdin
    
Here are some categories of builtin:

- I/O: `echo  write  read`
- File system: `cd  test`
- Processes: `fork  wait  forkwait  exec`
- Interpreter settings: `shopt  shvar`
- Meta: `command  builtin  runproc  type  eval`

<!-- TODO: Link to a comprehensive list of builtins -->

## Expression Language: Python-like Types

YSH expressions look and behave more like Python or JavaScript than shell.  For
example, we write `if (x < y)` instead of `if [ $x -lt $y ]`.  Expressions are
usually surrounded by `( )`.  

At runtime, variables like `x` and `y` are bounded to **typed data**, like
integers, floats, strings, lists, and dicts.

<!--
[Command vs. Expression Mode](command-vs-expression-mode.html) may help you
understand how YSH is parsed.
-->

### Python-like `func`

At the end of the *Command Language*, we saw that procs are shell-like units of
code.  YSH also has Python-like **functions**, which are different than
`procs`:

- They're defined with the `func` keyword.
- They're called in expressions, not in commands.
- They're **pure**, and live in the **interior** of a process.
  - In contrast, procs usually perform I/O, and have **exterior** boundaries.

The simplest function is:

    func identity(x) {
      return (x)  # parens required for typed return
    }

A more complex pure function:

    func myRepeat(s, n; special=false) {  # positional; named params
      var parts = []
      for i in (0 ..< n) {
        append $s (parts)
      }
      var result = join(parts)

      if (special) {
        return ("$result !!")
      } else {
        return (result)
      }
    }

    echo $[myRepeat('z', 3)]  # => zzz

    echo $[myRepeat('z', 3, special=true)]  # => zzz !!

A function that mutates its argument:

    func popTwice(mylist) {
      call mylist->pop()
      call mylist->pop()
    }

    var mylist = [3, 4]

    # The call keyword is an "adapter" between commands and expressions,
    # like the = keyword.
    call popTwice(mylist)


Funcs are named using `camelCase`, while procs use `kebab-case`.  See the
[Style Guide](style-guide.html) for more conventions.

#### Builtin Functions

In addition, to builtin commands, YSH has Python-like builtin **functions**.
These are like the "standard library" for the expression language.  Examples:

- Functions that take multiple types: `len()  type()`
- Conversions: `bool()   int()   float()   str()  list()   ...`
- Explicit word evaluation: `split()  join()  glob()  maybe()`  

<!-- TODO: Make a comprehensive list of func builtins. -->


### Data Types: `Int`, `Str`, `List`, `Dict`, `Obj`, ...

YSH has data types, each with an expression syntax and associated methods.

### Methods

Non-mutating methods are looked up with the `.` operator:

    var line = ' ale bean '
    var caps = line.trim().upper()  # 'ALE BEAN'

Mutating methods are looked up with a thin arrow `->`:

    var foods = ['ale', 'bean']
    var last = foods->pop()  # bean
    write @foods  # => ale

You can ignore the return value with the `call` keyword:

    call foods->pop()

That is, YSH adds mutable data structures to shell, so we have a special syntax
for mutation.

---

You can also chain functions with a fat arrow `=>`:

    var trimmed = line.trim() => upper()  # 'ALE BEAN'

The `=>` operator allows functions to appear in a natural left-to-right order,
like methods.

    # list() is a free function taking one arg
    # join() is a free function taking two args
    var x = {k1: 42, k2: 43} => list() => join('/')  # 'K1/K2'

---

Now let's go through the data types in YSH.  We'll show the syntax for
literals, and what **methods** they have.

#### Null and Bool

YSH uses JavaScript-like spellings these three "atoms":

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

<!--
"Runes" are integers that represent Unicode code points.  They're not common in
YSH code, but can make certain string algorithms more readable.

    # Pound rune literals are similar to ord('A')
    const a = #'A'

    # Backslash rune literals can appear outside of quotes
    const newline = \n  # Remember this is an integer
    const backslash = \\  # ditto

    # Unicode rune literal is syntactic sugar for 0x3bc
    const mu = \u{3bc}

    echo "chars $a $newline $backslash $mu"  # => chars 65 10 92 956
-->

#### Float

Floats are written with a decimal point:

    var big = 3.14

You can use scientific notation, as in Python:

    var small = 1.5e-10

#### Str

See the section above on *Three Kinds of String Literals*.  It described
`'single quoted'`, `"double ${quoted}"`, and `u'J8-style\n'` strings; as well
as their multiline variants.

Strings are UTF-8 encoded in memory, like strings in the [Go
language](https://golang.org).  There isn't a separate string and unicode type,
as in Python.

Strings are **immutable**, as in Python and JavaScript.  This means they only
have **transforming** methods:

    var x = s.trim()

Other methods:

- `trimLeft()   trimRight()`
- `trimPrefix()   trimSuffix()`
- `upper()   lower()`
- `search()  leftMatch()` - pattern matching
- `replace()   split()`

#### List (and Arrays)

All lists can be expressed with Python-like literals:

    var foods = ['ale', 'bean', 'corn']
    var recursive = [1, [2, 3]]

As a special case, list of strings are called **arrays**.  It's often more
convenient to write them with shell-like literals:

    # No quotes or commas
    var foods = :| ale bean corn |

    # You can use the word language here
    var other = :| foo $s *.py {alice,bob}@example.com |

Lists are **mutable**, as in Python and JavaScript.  So they mainly have
mutating methods:

    call foods->reverse()
    write -- @foods
    # =>
    # corn
    # bean
    # ale

#### Dict

Dicts use syntax that's like JavaScript.  Here's a dict literal:

    var d = {
      name: 'bob',  # unquoted keys are allowed
      age: 42,
      'key with spaces': 'val'
    }

You can use either `[]` or `.` to retrieve a value, given a key:

    var v1 = d['name']
    var v2 = d.name                # shorthand for the above
    var v3 = d['key with spaces']  # no shorthand for this

(If the key doesn't exist, an error is raised.)

You can change Dict values with the same 2 syntaxes:

    set d['name'] = 'other'
    set d.name = 'fun'

---

If you want to compute a key name, use an expression inside `[]`:

    var key = 'alice'
    var d2 = {[key ++ '_z']: 'ZZZ'}  # Computed key name
    echo $[d2.alice_z]   # => ZZZ

If you omit the value, its taken from a variable of the same name:

    var d3 = {key}             # like {key: key}
    echo "name is $[d3.key]"   # => name is alice

More examples:

    var empty = {}
    echo $[len(empty)]  # => 0

The `keys()` and `values()` methods return new `List` objects:

    var keys = keys(d2)      # => alice_z
    var vals = values(d3)    # => alice

#### Obj

YSH has an `Obj` type that bundles **code** and **data**.  (In contrast, JSON
messages are pure data, not objects.)

The main purpose of objects is **polymorphism**:

    var obj = makeMyObject(42)  # I don't know what it looks like inside

    echo $[obj.myMethod()]      # But I can perform abstract operations

    call obj->mutatingMethod()  # Mutation is considered special, with ->

YSH objects are similar to Lua and JavaScript objects.  They can be thought of
as a linked list of `Dict` instances.

Or you can say they have a `Dict` of properties, and a recursive "prototype
chain" that is also an `Obj`.

- [Feature Index: Objects](ref/feature-index.html#Objects)

### `Place` type / "out params"

The `read` builtin can set an implicit variable `_reply`:

    whoami | read --all  # sets _reply

Or you can pass a `value.Place`, created with `&`

    var x                      # implicitly initialized to null
    whoami | read --all (&x)   # mutate this "place"
    echo who=$x  # => who=andy

<!--
#### Quotation Types: value.Command (Block) and value.Expr

These types are for reflection on YSH code.  Most YSH programs won't use them
directly.

- `Command`: an unevaluated code block.
  - rarely-used literal: `^(ls | wc -l)`
- `Expr`: an unevaluated expression.
  - rarely-used literal: `^[42 + a[i]]`
-->

### Operators

YSH operators are generally the same as in Python:

    if (10 <= num_beans and num_beans < 20) {
      echo 'enough'
    }  # => enough

YSH has a few operators that aren't in Python.  Equality can be approximate or
exact:

    var n = ' 42 '
    if (n ~== 42) {
      echo 'equal after stripping whitespace and type conversion'
    }  # => equal after stripping whitespace type conversion

    if (n === 42) {
      echo "not reached because strings and ints aren't equal"
    }

<!-- TODO: is n === 42 a type error? -->

Pattern matching can be done with globs (`~~` and `!~~`)

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
- Function calls
  - free: `f(x, y)`
  - transformations and chaining: `s => startWith('prefix')`
  - mutating methods: `mylist->pop()`
- String and List: `++` for concatenation
  - This is a separate operator because the addition operator `+` does
    string-to-int conversion

TODO: What about list comprehensions?
-->

### Egg Expressions (YSH Regexes)

An *Eggex* is a YSH expression that denotes a regular expression.  Eggexes
translate to POSIX ERE syntax, for use with tools like `egrep`, `awk`, and `sed
--regexp-extended` (GNU only).

They're designed to be readable and composable.  Example:

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

Before moving onto other YSH features, let's review what we've seen.

### Three Interleaved Languages

Here are the languages we saw in the last 3 sections:

1. **Words** evaluate to a string, or list of strings.  This includes:
   - literals like `'mystr'`
   - substitutions like `${x}` and `$(hostname)`
   - globs like `*.sh`
2. **Commands** are used for
   - I/O: pipelines, builtins like `read`
   - control flow: `if`, `for`
   - abstraction: `proc`
3. **Expressions** on typed data are borrowed from Python, with influence from
   JavaScript:
   - Lists: `['ale', 'bean']` or `:| ale bean |`
   - Dicts: `{name: 'bob', age: 42}`
   - Functions: `split('ale bean')` and `join(['pea', 'nut'])`

### How Do They Work Together?

Here are two examples:

(1) In this this *command*, there are **four** *words*.  The fourth word is an
*expression sub* `$[]`.

    write hello $name $[d['age'] + 1]
    # =>
    # hello
    # world
    # 43

(2) In this assignment, the *expression* on the right hand side of `=`
concatenates two strings.  The first string is a literal, and the second is a
*command sub*.

    var food = 'ale ' ++ $(echo bean | tr a-z A-Z)
    write $food  # => ale BEAN

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

---

Let's move on from talking about **code**, and talk about **data**.

## Data Notation / Interchange Formats

In YSH, you can read and write data languages based on [JSON]($xref).  This is
a primary way to exchange messages between Unix processes.

Instead of being **executed**, like our command/word/expression languages,
these languages **parsed** as data structures.

<!-- TODO: Link to slogans, fallacies, and concepts -->

### UTF-8

UTF-8 is the foundation of our data notation.  It's the most common Unicode
encoding, and the most consistent:

    var x = u'hello \u{1f642}'  # store a UTF-8 string in memory
    echo $x                     # send UTF-8 to stdout

hello &#x1f642;

<!-- TODO: there's a runes() iterator which gives integer offsets, usable for
slicing -->

### JSON

JSON messages are UTF-8 text.  You can encode and decode JSON with functions
(`func` style):

    var message = toJson({x: 42})       # => (Str)   '{"x": 42}'
    var mydict = fromJson('{"x": 42}')  # => (Dict)  {x: 42}

Or with commands (`proc` style):

    json write ({x: 42}) > foo.json     # writes '{"x": 42}'

    json read (&mydict) < foo.json      # create var
    = mydict                            # => (Dict)  {x: 42}

### J8 Notation

But JSON isn't quite enough for a principled shell.

- Traditional Unix tools like `grep` and `awk` operate on streams of **lines**.
  In YSH, to avoid data-dependent bugs, we want a reliable way of **quoting**
  lines.
- In YSH, we also want to represent **binary** data, not just text.  When you
  read a Unix file, it may or may not be text.

So we borrow JSON-style strings, and create [J8 Notation][].  Slogans:

- *Deconstructing and Augmenting JSON*
- *Fixing the JSON-Unix Mismatch*

[J8 Notation]: $xref:j8-notation

#### J8 Lines

*J8 Lines* are a building block of J8 Notation.  If you have a file
`lines.txt`:

<pre>
  doc/hello.md
 "doc/with spaces.md"
b'doc/with byte \yff.md'
</pre>

Then you can decode it with *split command sub* (mentioned above):

    var decoded = @(cat lines.txt)

This file has:

1. An unquoted string
1. A JSON string with `"double quotes"`
1. A J8-style string: `u'unicode'` or `b'bytes'`

<!--
TODO: fromJ8Line() toJ8Line()
-->

#### JSON8 is Tree-Shaped

JSON8 is just like JSON, but it allows J8-style strings:

<pre>
{ "foo":  "hi \uD83D\uDE42"}  # valid JSON, and valid JSON8
{u'foo': u'hi \u{1F642}'   }  # valid JSON8, with J8-style strings
</pre>

<!--
In addition to strings and lines, you can write and read **tree-shaped** data
as [JSON][]:

    var d = {key: 'value'}
    json write (d)                 # dump variable d as JSON
    # =>
    # {
    #   "key": "value"
    # }

    echo '["ale", 42]' > example.json

    json read (&d2) < example.json  # parse JSON into var d2
    pp (d2)                         # pretty print it 
    # => (List)  ['ale', 42]

[JSON][] will lose information when strings have binary data, but the slight
[JSON8]($xref) upgrade won't:

    var b = {binary: $'\xff'}
    json8 write (b)
    # =>
    # {
    #   "binary": b'\yff'
    # }
-->

[JSON]: $xref

#### TSV8 is Table-Shaped

(TODO: not yet implemented.)

YSH supports data notation for tables:

1. Plain TSV files, which are untyped.  Every column has string data.
   - Cells with tabs, newlines, and binary data are a problem.
2. Our extension [TSV8]($xref), which supports typed data.
   - It uses JSON notation for booleans, integers, and floats.
   - It uses J8 strings, which can represent any string.

<!-- Figure out the API.  Does it work like JSON?

Or I think we just implement
- rows: 'where' or 'filter' (dplyr)
- cols: 'select' conflicts with shell builtin; call it 'cols'?
- sort: 'sort-by' or 'arrange' (dplyr)
- TSV8 <=> sqlite conversion.  Are these drivers or what?
  - and then let you pipe output?

Do we also need TSV8 space2tab or something?  For writing TSV8 inline.

More later:
- MessagePack (e.g. for shared library extension modules)
  - msgpack read, write?  I think user-defined function could be like this?
- SASH: Simple and Strict HTML?  For easy processing
-->

## YSH Modules are Files

A module is a **file** of source code, like `lib/myargs.ysh`.  The `use`
builtin turns it into an `Obj` that can be invoked and inspected:

    use myargs.ysh

    myargs proc1 --flag val   # module name becomes a prefix, via __invoke__
    var alias = myargs.proc1  # module has attributes

You can import specific names with the `--pick` flag:

    use myargs.ysh --pick p2 p3

    p2
    p3

- [Feature Index: Modules](ref/feature-index.html#Modules)

## The Runtime Shared by OSH and YSH

Although we describe OSH and YSH as different languages, they use the **same**
interpreter under the hood.

This interpreter has many `shopt` booleans to control behavior, like `shopt
--set parse_paren`.  The group `shopt --set ysh:all` flips all booleans to make
`bin/osh` behave like `bin/ysh`.

Understanding this common runtime, and its interface to the Unix kernel, will
help you understand **both** languages!

### Interpreter Data Model

The [Interpreter State](interpreter-state.html) doc is under construction.  It
will cover:

- The **call stack** for OSH and YSH
  - Each *stack frame* is a `{name -> cell}` mapping.
- Each cell has a **value**, with boolean flags
  - OSH has types `Str BashArray BashAssoc`, and flags `readonly export
    nameref`.
  - YSH has types `Bool Int Float Str List Dict Obj ...`, and the `readonly`
    flag.
- YSH **namespaces**
  - Modules with `use`
  - Builtin functions and commands
  - ENV
- Shell **options**
  - Boolean options with `shopt`: `parse_paren`, `simple_word_eval`, etc.
  - String options with `shvar`: `IFS`, `PATH`
- **Registers** that store interpreter state
  - `$?` and `_error`
  - `$!` for the last PID
  - `_this_dir`
  - `_reply`

### Process Model (the kernel)

The [Process Model](process-model.html) doc is **under construction**.  It will cover:

- Simple Commands, `exec` 
- Pipelines.  #[shell-the-good-parts](#blog-tag)
- `fork`, `forkwait`
- Command and process substitution
- Related:
  - [Tracing execution in Oils](xtrace.html) (xtrace), which divides
    process-based concurrency into **synchronous** and **async** constructs.
  - [Three Comics For Understanding Unix
    Shell](http://www.oilshell.org/blog/2020/04/comics.html) (blog)

<!--
Process model additions: Capers, Headless shell 

some optimizations: See YSH starts fewer processes than other shells.
-->

### Advanced: Reflecting on the Interpreter

You can reflect on the interpreter with APIs like `io->eval()` and
`vm.getFrame()`.

- [Feature Index: Reflection](ref/feature-index.html#Reflection)

This allows YSH to be a language for creating other languages.  (Ruby, Tcl, and
Racket also have this flavor.)

<!--

TODO: Hay and Awk examples
-->

## Summary

What have we described in this tour?

YSH is a programming language that evolved from Unix shell.  But you can
"forget" the bad parts of shell like `[ $x -lt $y ]`.

<!--
Instead, we've shown you shell-like commands, Python-like expressions on typed
data, and Ruby-like command blocks.
-->

Instead, focus on these central concepts:

1. Interleaved *word*, *command*, and *expression* languages.
2. A standard library of *builtin commands*, as well as *builtin functions*
3. Languages for *data*: J8 Notation, including JSON8 and TSV8
4. A *runtime* shared by OSH and YSH

## Appendix

### Related Docs

- [YSH vs. Shell Idioms](idioms.html) - YSH side-by-side with shell.
- [YSH Language Influences](language-influences.html) - In addition to shell,
  Python, and JavaScript, YSH is influenced by Ruby, Perl, Awk, PHP, and more.
- [A Feel For YSH Syntax](syntax-feelings.html) - Some thoughts that may help
  you remember the syntax.
- [YSH Language Warts](warts.html) documents syntax that may be surprising.


### YSH Script Template

YSH can be used to write simple "shell scripts" or longer programs.  It has
*procs* and *modules* to help with the latter.

A module is just a file, like this:

```
#!/usr/bin/env ysh
### Deploy script

use $_this_dir/lib/util.ysh --pick log

const DEST = '/tmp/ysh-tour'

proc my-sync(...files) {
  ### Sync files and show which ones

  cp --verbose @files $DEST
}

proc main {
  mkdir -p $DEST

  touch {foo,bar}.py {build,test}.sh

  log "Copying source files"
  my-sync *.py *.sh

  if test --dir /tmp/logs {
    cd /tmp/logs

    log "Copying logs"
    my-sync *.log
  }
}

if is-main {                    # The only top-level statement
  main @ARGV
}
```

<!--
TODO:
- Also show flags parsing?
- Show longer examples where it isn't boilerplate
-->

You wouldn't bother with the boilerplate for something this small.  But this
example illustrates the basic idea: the top level often contains these words:
`use`, `const`, `proc`, and `func`.


<!--
TODO: not mentioning __provide__, since it should be optional in the most basic usage?
-->

### YSH Features Not Shown

#### Advanced

These shell features are part of YSH, but aren't shown above:

- The `fork` and `forkwait` builtins, for concurrent execution and subshells.
- Process Substitution: `diff <(sort left.txt) <(sort right.txt)`

#### Deprecated Shell Constructs

The shared interpreter supports many shell constructs that are deprecated:

- YSH code uses shell's `||` and `&&` in limited circumstances, since `errexit`
  is on by default.
- Assignment builtins like `local` and `declare`.  Use YSH keywords.
- Boolean expressions like `[[ x =~ $pat ]]`.  Use YSH expressions.
- Shell arithmetic like `$(( x + 1 ))` and `(( y = x ))`.  Use YSH expressions.
- The `until` loop can always be replaced with a `while` loop
- Most of what's in `${}` can be written in other ways.  For example
  `${s#/tmp}` could be `s => removePrefix('/tmp')` (TODO).

#### Not Yet Implemented

This document mentions a few constructs that aren't yet implemented.  Here's a
summary:

```none
# Unimplemented syntax:

echo ${x|html}               # formatters

echo ${x %.2f}               # statically-parsed printf

var x = "<p>$x</p>"html      
echo "<p>$x</p>"html         # tagged string

var x = 15 Mi                # units suffix
```

<!--
- To implement: Capers: stateless coprocesses
-->

