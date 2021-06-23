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


## Concept: Three Sublanguages

Oil is best explained as three interleaved languages:

1. **Words** are expressions for strings, and arrays of strings.  This
   includes:
   - literals like `'mystr'`
   - substitutions like `$(hostname)`,
   - globs like `*.sh`, and more.
2. **Commands** are used for
   - I/O (pipelines),
   - control flow (`if`, `for`),
   - abstraction (`proc`), and more.
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

This shell operator `:-` is occasionally useful:

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

The `$[]` syntax evaluates an expression and converts it to a string:

    echo $[a]                        # => ale
    echo $[1 + 2]                    # => 3
    echo "_ $[1 + 2] _"              # => _ 3 _

<!-- TODO: safe substitution -->

#### Function Sub

As a shortcut for `$[f(x)]`, you can turn the result of a function into a
string with `$f(x)`:

    var foods = ['pea', 'nut']
    echo $join(foods)               # => peanut

Note that function subs **cannot** be used in double quotes.  Use the longer
expression sub instead:

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

#### Split Command Sub / Split Builtin Sub

There are also variants of **command sub** and **builtin sub** that split
first:

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

Pipelines may contain lines of text, JSON, TSV, etc.  More on that below.

### Variable Declaration and Mutation

Constants can't be modified:

    const s = 'mystr'
    # setvar s = 'foo' would be an error

Modify variables with the `setvar` keyword:

    var num_eggs = 12
    setvar num_eggs = 13

A more complex example:

    var d = {name: 'bob', age: 42}  # dict literal
    setvar d->name = 'alice'        # d->name is a synonym for d['name']
    echo $[d->name]                 # => alice

That's about all you need to know.

Advanced users may want to use `setglobal` or `setref` in certain situations:

    var g = 1
    proc demo(:out) {
      setglobal g = 42
      setref out = 43
    }
    demo :g  # pass a reference to g
    echo $g  # => 43

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

When the condition is surrounded with `()`, it's a Python-like expression
rather than a command:

    if (num_eggs > 0) {
      echo 'so many eggs'
    }

    var done = false
    if (not done) {              # negate with 'not' operator
      echo 'not done'
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

(You can use shell style `if foo; then ... fi` and `case $x in ...  esac`, but
this is discouraged in Oil.)

### Loops: `for`, `while`

For loops iterate over words:

    for x in oil $num_eggs {pea,coco}nut {
      echo $x
    }
    # =>
    # oil
    # 13
    # peanut
    # coconut

Like if statements, while loops have a command variant:

   while test --file lock {
     sleep 1
   }

and an expression variant:

    var x = 0
    while (x > 0) {
      echo "x = $x"
      # TODO: implement this
      #setvar x -= 1
    }

#### `break`, `continue`, `return`, `exit`

The `exit` keyword (*not* a shell builtin) exits a process.  The other 3
keywords behave like they do in Python and JavaScript.

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

### Builtin Commands

**Shell builtins** like `cd` and `read` are the "standard library" of the
command language.  Each one takes various flags:

    cd -L .                      # follow symlinks

    echo foo | read --line       # read a line of stdin
    
TODO: List categories of builtin

- I/O: `echo  printf  write  read`
- Introspection: `type`
- Interpreter settings: `shopt shvar`

## Expression Language: Python-like Types

Oil expressions will be familiar Python and JavaScript users.  They're easier
to remember than the shell syntax to perform similar operations, like
`${x#prefix}` and `[[ x =~ $pat ]]`.

### Types and Literals: `Bool`, `Int`, `List`, `Dict`, ...

Let's go through all the Python-like data types here.

#### Null and Bool

JavaScript-like spellings are preferred for these three "atoms":

    var x = null

    var b1, b2 = true, false

    if (b1) {
      echo 'yes'
    }

For compatibility, you can also use `None`, `True`, and `False`.  But that
breaks the rule that types are spelled with capital letters (e.g. `Str`,
`Dict`).

#### Int

There are many ways to write integers:

    #var small, big = 42, 65_536         # TODO: _ not supported yet
    #echo "$small $big"                  # => 42 65536

    var hex, octal, binary = 0xFF, 0o755, 0b0101

Character literals can appear outside of strings, and are actually integers:

    # TODO: not supported yet
    #var newline, mu, a = \n, \u3bc, #'a'
    #echo "$newline $mu $a"               # => 255 493 5

#### Float

Floats are written like you'd expect, but the initial version of the Oil
language doesn't have them.  (Help wanted!)

    var small = 1.5e-10
    var big = 3.14

#### Str

See *Three Kinds of String Literals* above.  It describes `'single quoted'`,
`"double ${quoted}"`, and $'c-style\n'` strings; as well as their multiline
variants.  

- Oil has no unicode type.  Strings in Oil are UTF-8 encoded in memory, like
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

#### Block, Expr, ArgList

These are types of code.

- `Block`: an unevaluated code block.
  - rarely-used literal: `^(ls | wc -l)`
- `Expr`: an unevaluated expression.
- `ArgList`: a lazily-evaluated argument list.
  - rarely-used literal: `^[42, f(x), verbose = true]`

### Operators

Operators are generally the same as in Python:

    if (10 <= num_eggs and num_eggs < 20) {
      echo 'enough'
    }  # => enough

Here are a few things Oil adds:

The `->` operator lets you use unquoted keys for dicts:

    echo $[d->name]    # => bob
    echo $[d['name']]  # => bob (the same thing)

Equality can be approximate:

    var s = '42'
    if (s ~== 42) {
      echo 'equal after type conversion'
    }  # => equal after type conversion

There are pattern matching operators `~ !~` and `~~ !~~`:

    if (s ~~ '*.py') {
      echo 'Python'
    }

(See the Eggex section for an example of `~`.)

Concatenation is `++` rather than `+` because it avoids confusion in the
presence of type conversion:

    var n = 42 + 1 
    echo $n           # => 43

    var y = $'ale\n' ++ "bean $n"
    echo $y
    # =>
    # ale
    # bean 43

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

<!-- TODO: What about list comprehensions? -->


<!--
- No string formatting with %
- No @ matrix multiply
-->



### Builtin Functions

These are the "standard library" for the expression language.

- `split()  join()`
- `min()  max()`
- ...

## Egg Expressions (Oil Regexes)

*Eggex* is a readable and composable language for regular expressions.  It
translates to POSIX ERE syntax, for use with tools like `egrep`, `awk`, and
`sed --regexp-extended` (GNU only).

    var z = '3.14'
    if (z ~ /d+ '.' d+/) {           # Use the ~ operator to match
      echo "$z looks like a number"
    }
    # =>
    # 3.14 looks like a number

See the [Egg Expressions doc](eggex.html) for details.

## Interchange Formats (Languages for Data)

### Lines of Text (traditional) and QSN

Traditional Unix

QSN too.

### JSON, QTT (structured)

Tree-shaped data can be read and written as JSON:

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

<!-- TODO: Fix pp cell output -->

Table-shaped data can be read and written as QTT (quoted, typed table):

And QTT:

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

<!--

There is also QTT space2tab or something?  Change spaces to tabs

More later:
- MessagePack (e.g. for shared library extension modules)
- SASH: Simple and Strict HTML?  For easy processing
- QTT: should also allow hex float representation for exactness
-->

## The Runtime (shared by OSH and Oil)

Although we talk about OSH and Oil as different languages, they both use the
**same** interpreter under the hood.  The interpreter has various `shopt` flags
that are flipped for different behavior, e.g. with `shopt --set oil:all`.

Understanding this interpreter and its interface to the Unix kernel will help
you understand **both** languages!

### Data Model (the interpreter)


- proc namespace
- variable namespace
  - readonly, export, nameref flags
  - including shvar
- shell options
- Various registers

#### `shopt`, `shvar`, and Registers

- `simple_word_eval`

#### shvars

- `IFS`
- `_ESCAPE`
- `_DIALECT`

#### Registers

- `$?` and `_status`
- `_buffer`
- `_this_dir`

### Process Model (the kernel)

See Oil tracing with `-x`.

- synchronous constructs
- async constructs
- some optimizations: See Oil starts fewer processes than other shells.

- TODO
  - Kernel.  Comics.
  - Coprocesses

<!-- Process model additions: Capers, Headless shell -->


## Summary

Oil is a useful, large, and simplified language, with these concepts:

- Word Language: for strings and arrays
- Command Language: for I/O, abstraction, and control flow
  - With a standard library of *shell builtins*
  - With Ruby-like blocks
- Expressions: for Python-like types
  - With a standard library of *builtin functions*

## Related Docs

- [Oil Language Idioms](idioms.html) - Oil side-by-side with shell.
- [Oil Language Influences](language-influences.html) - In addition to shell,
  Python, and JavaScript, Oil is influenced by Ruby, Perl, Awk, PHP, and more.
- [Oil Language Warts](warts.html) docuemnts syntax that may be surprising.
- *A Tour of the Oil project*. TODO: Describe Oil, OSH, oven, the shell
  runtime, headless shell, etc.

Details:

- [Oil Word Language](oil-word-language.html)

## Appendix: Features Not Shown

### Deprecated Shell Constructs

Oil and OSH are actually variants of the same interpreter, with different
`shopt` settings.  The interpreter supports many shell constructs that are
deprecated:

- Most of what's in `${}`, like `${!indirect}`.  Use Oil functions instead.
- Assignment builtins like `local` and `declare`.  Use Oil keywords.
- Boolean expressions like `[[ x =~ $pat ]]`
- Shell arithmetic like `$(( x + 1 ))` and `(( y = x ))`.  Use Oil expressions
  instead.
- The `until` loop can always be replaced with a `while` loop
- Oil code uses shell's `||` and `&&` in limited circumstances, since `errexit`
  is on by default.

### Advanced

These shell features are part of Oil, but aren't shown for brevity.

- The `fork` and `forkwait` builtins, for concurrent execution and subshells.
- Process Substitution: `diff <(sort left.txt) <(sort right.txt)`
- Unevaluated blocks and expressions: `^(ls | wc-l)` and `^[42 + a[i]]`

### Not Yet Implemented

TODO: We need to implement these things!

- QTT support
- Capers / coprocesses
- Defining functions in shared libraries?  What about shell builtins?

```none
qtt | filter [size > 10]  # lazy arg lists
echo ${x|html}            # formatters
echo ${x %.2f}            # statically-parsed printf

echo ${.myproc arg1}      # builtin sub

... cat file.txt          # convenient multiline syntax
  | sort
  | uniq -c
  ;
```

## Appendix: Example of an Oil Module

Oil can be used to write simple "shell scripts" or longer programs.  It has
*procs* and *modules* to help with the latter.

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

<!-- TODO: Also show flags parsing? -->

For something this small, you usually wouldn't bother with the boilerplate.
(TODO: see longer examples ...)

But this example just illustrates the idea, which is that these commands appear
at the top level: `proc`, `const`, `module`, `source`, and `use`.
