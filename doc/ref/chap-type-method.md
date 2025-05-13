---
title: Types and Methods (Oils Reference)
all_docs_url: ..
body_css_class: width40
default_highlighter: oils-sh
preserve_anchor_case: yes
---

<div class="doc-ref-header">

[Oils Reference](index.html) &mdash; Chapter **Types and Methods**

</div>

This chapter describes YSH types and methods.  There are also two OSH types for
bash compatibility.

<span class="in-progress">(in progress)</span>

<div id="dense-toc">
</div>

## OSH

These two types are for OSH code only.

### BashArray

A bash array holds a sequence of strings.  Some entries may be **unset** (not
an empty string).

See [sh-init-list][] and [sh-array][] for creation/mutation of BashArray.
In YSH, prefer to use [List](#List) instances.

[sh-array]: chap-osh-assign.html#sh-array
[sh-init-list]: chap-osh-assign.html#sh-init-list

### BashAssoc

A bash associative array is a mapping from strings to strings.

See [sh-init-list][] and [sh-assoc][] for creation/mutation of BashAssoc.  In
YSH, prefer to use [Dict](#Dict) instances.

[sh-assoc]: chap-osh-assign.html#sh-assoc

## Atoms

<!-- TODO:
true and false should be SINGLETONS
null is already a singleton
-->

### Null

An `Obj` instance representing the `Null` type.

The `Null` type has a single value spelled `null`.  (Related:
[atom-literal][]).

[atom-literal]: chap-expr-lang.html#atom-literal

### null

A value that's not equal to any other.  Values that aren't explicitly
initialized are `null`, e.g.

    var x
    = x  # => (Null)   null

Its type is `Null`.

### Bool

An `Obj` instance representing the boolean type.

This type has 2 values: `true` and `false`.  (Related: [atom-literal][]).

### expr/true

A single value representing truth, e.g.

    = 42 === 42  # => true

### expr/false

A single value representing the opposite of truth, e.g.

    = 42 === 3  # => false

## Numbers

### Int

Integers are currently 64-bit signed integers (on all platforms).  TODO: they
should be arbitrary precision.

There are many way of writing integers; see [int-literal][].

In shell, ASCII strings like `'42'` are often used for calculations on
integers.  But you can use a "real" integer type in YSH.

[int-literal]: chap-expr-lang.html#int-literal


### Float

YSH has 64-bit floating point numbers.  See [float-literal][] for how to denote
them.

[float-literal]: chap-expr-lang.html#float-literal

### Range
  
A `Range` is a pair of two numbers, used for iteration.  See [range][] for how
to denote them.

Ranges are used for iteration; see [ysh-for][].

[range]: chap-expr-lang.html#range
[ysh-for]: chap-cmd-lang.html#ysh-for

## String

In Oils, strings may contains any sequence of bytes, which may be UTF-8
encoded.

Internal NUL bytes (`0x00`) are allowed.

When passing such strings to say the [cd][] builtin, the string will be
truncated before the NUL.  This is because most C functions like `chdir()` take
NUL-terminated strings.

[cd]: chap-builtin-cmd.html#cd

### Str

An `Obj` instance representing the string type.

### find()

TODO:

    var i = mystr.find('foo')

Similar to

    = 'foo' in mystr

Both of them do substring search.

Also similar to `mystr.search(eggex)`.

<!-- Python also has start, end indices, to reduce allocations -->

### replace()

Replace substrings with a given string.

    = mystr => replace("OSH", "YSH")

Or match with an Eggex.

    = mystr => replace(/ d+ /, "<redacted>")  # => "code is <redacted>"

Refer to Eggex captures with replacement expressions. Captured values can be
referenced with `$1`, `$2`, etc.

    var mystr = "1989-06-08"
    var pat = / <capture d{4}> '-' <capture d{2}> '-' <capture d{2}> /
    = mystr => replace(pat, ^"Year: $1, Month: $2, Day: $3")

Captures can also be named.

    = mystr2 => replace(/ <capture digit{4} as year : int> /, ^"$[year + 1]")

`$0` refers to the entire capture itself in a substitution string.

    var mystr = "replace with mystr => replace()"
    = mystr => replace(/ alpha+ '=>' alpha+ '()' /, ^"<code>$0</code>")
    # => "replace with <code>mystr => replace()</code>"

In addition to captures, other variables can be referenced within a replacement
expression.

    = mystr => replace(/ <capture alpha+> /, ^"$1 and $anotherVar")

To limit the number of replacements, pass in a named count argument. By default
the count is `-1`. For any count in [0, MAX_INT], there will be at most count
replacements. Any negative count means "replace all" (ie. `count=-2` behaves
exactly like `count=-1`).

    var mystr = "bob has a friend named bob"
    = mystr => replace("bob", "Bob", count=1)   # => "Bob has a friend named bob"
    = mystr => replace("bob", "Bob", count=-1)  # => "Bob has a friend named Bob"

The following matrix of signatures are supported by `replace()`:

    s => replace(string_val, subst_str)
    s => replace(string_val, subst_expr)
    s => replace(eggex_val, subst_str)
    s => replace(eggex_val, subst_expr)

Replacing by an `Eggex` has some limitations:

- If a `search()` results in an empty string match, eg.
  `'abc'.split(/ space* /)`, then we raise an error to avoid an infinite loop.
- The string to replace on cannot contain NUL bytes because we use the libc
  regex engine.

### startsWith()

Checks if a string starts with a pattern, returning true if it does or false if
it does not.

    = b'YSH123' => startsWith(b'YSH')  # => true
    = b'123YSH' => startsWith(b'YSH')  # => false
    = b'123YSH' => startsWith(/ d+ /)  # => true
    = b'YSH123' => startsWith(/ d+ /)  # => false

Matching is done based on bytes, not runes.

    = b'\yce\ya3'                 # => (Str)   "Σ"
    = 'Σ' => startsWith(b'\yce')  # => true
    = 'Σ' => endsWith(b'\ya3')    # => true

### endsWith()

Like `startsWith()` but returns true if the _end_ of the string matches.

    = b'123YSH' => endsWith("YSH")   # => true
    = b'YSH123' => endsWith(/ d+ /)  # => true

### trim()

Removes characters matching a pattern from the start and end of a string.
With no arguments, whitespace is removed. When given a string or eggex pattern,
that pattern is removed if it matches the start or end.

    = b' YSH\n'    => trim()        # => "YSH"
    = b'xxxYSHxxx' => trim('xxx')   # => "YSH"
    = b'xxxYSH   ' => trim('xxx')   # => "YSH   "
    = b'   YSHxxx' => trim('xxx')   # => "   YSH"
    = b'   YSH   ' => trim('xxx')   # => "   YSH   "
    = b'123YSH456' => trim(/ d+ /)  # => "YSH"

#### A note on whitespace

When stripping whitespace, Oils decodes the bytes in string as utf-8
characters. Only the following Unicode codepoints are considered to be
whitespace.

 - U+0009 -- Horizontal tab (`\t`)
 - U+000A -- Newline (`\n`)
 - U+000B -- Vertical tab (`\v`)
 - U+000C -- Form feed (`\f`)
 - U+000D -- Carriage return (`\r`)
 - U+0020 -- Normal space
 - U+00A0 -- No-break space `<NBSP>`
 - U+FEFF -- Zero-width no-break space `<ZWNBSP>`

While the Unicode standard defines other codepoints as being spaces, Oils
limits itself to just these codepoints so that the specification is stable, and
doesn't depend on an external standard that has reclassify characters.

### trimStart()

Like `trim()` but only removes characters from the _start_ of the string.

    = b' YSH\n'    => trimStart()        # => "YSH\n"
    = b'xxxYSHxxx' => trimStart(b'xxx')  # => "YSHxxx"
    = b'123YSH456' => trimStart(/ d+ /)  # => "YSH456"

### trimEnd()

Like `trim()` but only removes characters from the _end_ of the string.

    = b' YSH\n'    => trimEnd()        # => " YSH"
    = b'xxxYSHxxx' => trimEnd(b'xxx')  # => "YxxxSH"
    = b'123YSH456' => trimEnd(/ d+ /)  # => "123YSH"

### upper()

Respects unicode.

### lower()

Respects unicode.

### search()

Search for the first occurrence of a regex in the string.

    var m = 'hi world' => search(/[aeiou]/)  # search for vowels
    # matches at position 1 for 'i'

Returns a `value.Match()` if it matches, otherwise `null`.

You can start searching in the middle of the string:

    var m = 'hi world' => search(/dot 'orld'/, pos=3)
    # also matches at position 4 for 'o'

The `%start` or `^` metacharacter will only match when `pos` is zero.

(Similar to Python's `re.search()`.)

### leftMatch()

`leftMatch()` is like `search()`, but it checks

    var m = 'hi world' => leftMatch(/[aeiou]/)  # search for vowels
    # doesn't match because h is not a vowel

    var m = 'aye' => leftMatch(/[aeiou]/)
    # matches 'a'

`leftMatch()` Can be used to implement lexers that consume every byte of input.

    var lexer = / <capture digit+> | <capture space+> /

(Similar to Python's `re.match()`.)

### split()

Split a string by a `Str` separator `sep` into a `List` of chunks.

    pp ('a;b;;c'.split(';'))       # => ["a", "b", "", "c"]
    pp ('a<>b<>c<d'.split('<>'))   # => ["a", "b", "c<d"]
    pp ('🌞🌝🌞🌝🌞'.split('🌝'))  # => ["🌞", "🌞", "🌞"]

Or split using an `Eggex`.

    pp ('a b  cd'.split(/ space+ /))   # => ["a", "b", "cd"]
    pp ('a,b;c'.split(/ ',' | ';' /))  # => ["a", "b", "c"]

Optionally, provide a `count` to split on `sep` at most `count` times. A
negative `count` will split on all occurrences of `sep`.

    pp ('a;b;;c'.split(';', count=2))   # => ["a", "b", ";c"]
    pp ('a;b;;c'.split(';', count=-1))  # => ["a", "b", "", "c"]

Passing an empty `sep` will result in an error.

    pp ('abc'.split(''))  # => Error: Sep cannot be ""

Splitting by an `Eggex` has some limitations:

- If a `search()` results in an empty string match, eg.
  `'abc'.split(/ space* /)`, then we raise an error to avoid an infinite loop.
- The string to split cannot contain NUL bytes because we use the libc regex
  engine.

### lines()

Split a string into lines N lines, where N is the number of newlines.

    var s = u'foo\nbar\n'  # 2 lines
    = s.lines()            # => ['foo', 'bar']

Notice that the result has 2 lines, where as `s.split('\n')` would have 3.

---

Pass `eol=` to override the default delimiter of `\n`:

    var s = b'foo\y00bar\y00'  # 2 lines terminated by NUL
    = s.lines(eol=\y00)        # => ['foo', 'bar']

(This is useful for the output of `find . -print0`.)

Notes:

- Use `read --all` and `_reply.lines()` to replace the bash builtin
  [readarray][] aka [mapfile][].
- There is no special handling of carriage returns (`\r`), although you can
  pass `eol=u'\r\n'`.

[readarray]: chap-builtin-cmd.html#readarray
[mapfile]: chap-builtin-cmd.html#mapfile

## Patterns

### Eggex

An `Eggex` is a composable regular expression.  It can be spliced into other
regular expressions.

### Match

A `Match` is the result searching for an `Eggex` within a `Str`.

### group()

Returns the string that matched a regex capture group.  Group 0 is the entire
match.

    var m = '10:59' => search(/ ':' <capture d+> /)
    echo $[m => group(0)]  # => ':59'
    echo $[m => group(1)]  # => '59'

Matches can be named with `as NAME`:

    var m = '10:59' => search(/ ':' <capture d+ as minute> /)

And then accessed by the same name:

    echo $[m => group('minute')]  # => '59'

<!--
    var m = '10:59' => search(/ ':' <capture d+ as minutes: int> /)
-->

### start()

Like `group()`, but returns the **start** position of a regex capture group,
rather than its value.

    var m = '10:59' => search(/ ':' <capture d+ as minute> /)
    echo $[m => start(0)]         # => position 2 for ':59'
    echo $[m => start(1)]         # => position 3 for '59'

    echo $[m => start('minute')]  # => position 3 for '59'

### end()

Like `group()`, but returns the **end** position of a regex capture group,
rather than its value.

    var m = '10:59' => search(/ ':' <capture d+ as minute> /)
    echo $[m => end(0)]         # => position 5 for ':59'
    echo $[m => end(1)]         # => position 5 for '59'

    echo $[m => end('minute')]  # => 5 for '59'


## Containers

### List

An `Obj` instance representing the `List` type.

A List contains an ordered sequence of values.

### List/append()

Add an element to a list.

    var fruits = :|apple banana pear|
    call fruits->append("orange")
    echo @fruits  # => apple banana pear orange

Similar names: [append][]

[append]: chap-index.html#append

### pop()

remove an element from a list and return it.

    var fruits = :|apple banana pear orange|
    var last = fruits->pop()  # "orange" is removed AND returned
    echo $last                # => orange
    echo @fruits              # => apple banana pear

### extend()

Extend an existing list with the elements of another list.

    var foods = :|cheese chocolate|
    var fruits = :|apple banana|
    call foods->extend(fruits)
    echo @foods  # => cheese chocolate apple banana

### indexOf()

Returns the first index of the element in the list, or -1 if it's not present.

    var names = :| Jane Peter Joana Sam |
    echo $[names => indexOf("Sam")]    # => 3
    echo $[names => indexOf("Simon")]  # => -1

### insert()

Insert an element into the list at the given index.

    var hills = :| pillar glaramara helvellyn |
    call hills->insert(1, "raise")
    echo @hills  # => pillar raise glaramara helvellyn

- If you pass an index greater than the list length, the item will be inserted
  at the end.
- If you pass a negative index, it's interpreted as relative to the end of the
  list, like slicing.
  - If the negative index is out of bounds, the item will be inserted at the
    beginning of the list.

### lastIndexOf()

Returns the index of the last occurring instance of the specified
element in the list, or -1 if it's not present.

    var names = :| Sam Alice Sam Sam |
    echo $[names => lastIndexOf("Sam")]    # => 3
    echo $[names => lastIndexOf("Simon")]  # => -1

### remove()

Remove the first instance of the specified element from the list, if it exists.
Returns `null`, even if the element did not exist.

    var lakes = :| coniston derwent wast |
    call lakes->remove("wast")
    echo @lakes  # => coniston derwent

### reverse()

Reverses a list in place.

    var fruits = :|apple banana pear|
    call fruits->reverse()
    echo @fruits  # => pear banana apple

### List/clear()

Remove all entries from the List:

    var fruits = :|apple banana pear|
    call mylist->clear()
    echo @fruits # =>

### Dict

An `Obj` instance representing the `Dict` type.

A Dict contains an ordered sequence of key-value pairs.  Given the key, the
value can be retrieved efficiently.

### erase()

Ensures that the given key does not exist in the dictionary.

    var book = {
      title: "The Histories",
      author: "Herodotus",
    }
    = book
    # => (Dict)   {title: "The Histories", author: "Herodotus"}

    call book->erase("author")
    = book
    # => (Dict)   {title: "The Histories"}

    # repeating the erase call does not cause an error
    call book->erase("author")
    = book
    # => (Dict)   {title: "The Histories"}

### accum()

TODO:

    call mydict->accum('key', 'string to append')

Similar:

    setvar mydict['k'] += 3  # TODO: default value of 0


### Dict/clear()

TODO:

Remove all entries from the Dict:

    call mydict->clear()

### Place

### setValue()

A Place is used as an "out param" by calling setValue():

    proc p (out) {
      call out->setValue('hi')
    }

    var x
    p (&x)
    echo x=$x  # => x=hi

## Code Types

### Func

The type of a user-defined function.

A Func captures the stack frame it was defined in, making it a closure.  It
also captures the frame of the module it was defined in.

### BuiltinFunc

A func that's part of Oils, like `len()`.

### BoundFunc

The [thin-arrow][] and [fat-arrow][] create bound funcs:

    var bound = '' => upper
    var bound2 = [] -> append

[thin-arrow]: chap-expr-lang.html#thin-arrow
[fat-arrow]: chap-expr-lang.html#thin-arrow

### Proc

The type of a user-defined proc &mdash; i.e. a "procedure" or "process".

A Proc captures the stack frame it was defined in, making it a closure.  It
also captures the frame of the module it was defined in.

### BuiltinProc

A builtin proc, aka builtin command, like `module-invoke`.

## Objects

### Obj

An instance of `Obj`, representing the `Obj` type.

TODO: make it callable.

### `__invoke__`

<!-- copied from doc/proc-func-md -->

The `__invoke__` meta-method makes an Object "proc-like".

First, define a proc, with the first typed arg named `self`:

    proc myInvoke (word_param; self, int_param) {
      echo "sum = $[self.x + self.y + int_param]"
    }

Make it the `__invoke__` method of an `Obj`:

    var methods = Object(null, {__invoke__: myInvoke})
    var invokable_obj = Object(methods, {x: 1, y: 2})

Then invoke it like a proc:

    invokable_obj myword (3)
    # sum => 6

### new

Create an object:

    var methods = Obj.new({mymethod: foo}, null)
    var instance = Obj.new({x: 3, y: 4}, methods)

TODO: This will become `Obj.__call__`, which means it's written `Obj`.

### `__call__`

TODO

### `__index__`

The `__index__` meta-method controls what happens when `obj[x]` is evaluated.

It's currently used for type objects:

    var t = Dict[Str, Int]
    assert [t is Dict[Str, Int]]  # always evaluates to the same instance

### `__str__`

TODO


## Reflection

### Command

A value of type `Command` represents an unevaluated command.  There are **two**
syntaxes for such values:

1. In [expression mode][command-vs-expression-mode], a [block
   expression][block-expr] looks like this:

       var block = ^(echo $PWD; ls *.txt)

   This is similar to `$(echo $PWD)` in shell.

2. In [command mode][command-vs-expression-mode], a YSH [block-arg][] is 
   also of type `Command`:

       myproc { 
         echo $PWD
       }

   This is similar to `{ echo $PWD; }` in shell ([sh-block][])

[brace-group]: chap-cmd-lang.html#sh-block

---

The `Command` value is bound to a stack frame.  This frame will be pushed as an
"enclosed frame" when the command is evaluated.

[block-expr]: chap-expr-lang.html#block-expr
[block-arg]: chap-cmd-lang.html#block-arg

[command-vs-expression-mode]: ../command-vs-expression-mode.html

### sourceCode

The `Command.sourceCode()` method returns a `Dict` with the source code and
location info for a literal block.

    # define a proc
    proc p ( ; ; ; block) {
      = block.sourceCode()
    }

    # call it with a literal block, getting the source code
    p { echo hi }  # => { location_str:        "[stdin]",
                   #      location_start_line: 1,
                   #      code_str:            "echo hi\n" }

The `location_str` and `location_start_line` fields can be passed back into the
YSH interpreter, so that error messages blame the original location, not new
locations from `code_str`:

    ... ysh 
        --location-str        $[src.location_str]
        --location-start-line $[src.location_start_line]
        file_with_code_str.ysh
        ;

Currently, you can't extract the source code of an `Command` expression.  The
method returns `null`:

    var cmd = ^(echo hi)
    = cmd.sourceCode()  # => null

Related topic: [shell-flags][] documents the `--location-str` and
`--location-start-line` flags.

[shell-flags]: chap-front-end.html#shell-flags

### Expr

A value of type `Expr` represents an unevaluated expression.  There are **three**
syntaxes for such values:

1. In [expression mode][command-vs-expression-mode], an
   [expression literal][expr-literal] looks like this:

       var expr = ^[42 + a[i]]

1. There's also a shortcut for string literals:

       var s = "foo".replace('o', ^"-$0-")
       echo $s  # => f-o--o-

   The syntax `^"-$0-"` is short for `^["-$0-"]`.  You can omit the brackets.

1. In [command mode][command-vs-expression-mode], a YSH [lazy-expr-arg][] is
   also of type `Expr`:

       ls | my-where [size > 42]

   This is a shortcut for:

       ls | my-where (^[size > 42])  # same as syntax 1

[lazy-expr-arg]: chap-cmd-lang.html#lazy-expr-arg

---

The `Expr` value is bound to a stack frame.  This frame will be pushed as an
"enclosed frame" when the expression is evaluated.

[expr-literal]: chap-expr-lang.html#expr-lit

### Frame

A value that represents a stack frame.

You can turn it into a Dict with `dict(myframe)`.

### DebugFrame

An opaque value returned by [vm.getDebugStack()][], which has a `toString()`
method.

[vm.getDebugStack()]: chap-type-method.html#getDebugStack

Logically, it represents one of:

1. An invocation of a proc or shell function 
1. A YSH func call
1. The OSH [source][] builtin
1. The YSH [use][] builtin

[source]: chap-builtin-cmd.html#source
[use]: chap-builtin-cmd.html#use

### toString()

Return a string representing the `DebugFrame` value.

We recommend that you print each frame with a numeric prefix, like this:

<!-- bug: highlighting finds # within "" -->

```none
proc print-stack {
  for i, frame in (vm.getDebugStack()) {
    write --end '' -- "  #$[i+1] $[frame.toString()]"
  }
}
```

Then the output will look like:

```none
  #1 main.ysh
    source lib.ysh
    ^~~~~~
  #2 lib.ysh
    print-stack
    ^~~~~~~~~~~
``` 

### io

### stdin

Returns the singleton `stdin` value, which you can iterate over:

    for line in (io.stdin) {
       echo $line
    }

This is buffered line-based I/O, as opposed to the unbuffered I/O of the `read`
builtin.

### io/eval()

Given a `Command` value (e.g. a block argument), execute it, and return `null`.

    var cmd = ^(echo hi)
    call io->eval(cmd)  # => hi

This method is more principled and flexible than shell's [eval][] builtin.
It's especially useful in pure functions.

[eval]: chap-builtin-cmd.html#cmd/eval

It accepts optional args that let you control name binding:

- `dollar0` for `$0`
- `pos_args` for `$1 $2 $3`
- `vars` for named variables

Example:

    var cmd = ^(echo "zero $0, one $1, named $x")
    call io->eval(cmd, dollar0="z", pos_args=['one'], vars={x: "x"})
    # => zero z, one one, named x

Scoping rules:

- The frame that contains the `Command`, e.g.  `^(echo hi)` or `p { echo hi }`,
  is called the *captured* frame.
- Normally, a `Command` is evaluated in a new stack frame, which "encloses" the
  captured frame.  That is, a `Command` is a *closure*.

The `in_captured_frame` argument changes this behavior:

    call io->eval(cmd, in_captured_frame=true)

In this case, the captured frame becomes the local frame.  It's useful for
creating procs that behave like builtins:

    my-cd /tmp {           # my-cd is a proc, which pushes a new stack frame
      var listing = $(ls)  # This variable is created in the captured frame
    }
    echo $listing          # It's still visible after the proc returns

---

When the `eval()` method is passed `to_dict=true`, it returns a `Dict`
corresponding to the stack frame that the `Command` is evaluated in.

Example:

    var x = 10  # captured
    var cmd = ^(var a = 42; var hidden_ = 'h'; var b = x + 1)

    var d = io->evalToDict(cmd)

    pp (d)  # => {a: 42, b: 11}

Names that end with an underscore `_` are not copied, so `hidden_` is not in
the `Dict`.

---

To evaluate "purely", use the [`eval()`][func/eval] function.

[func/eval]: chap-builtin-func.html#func/eval

### io/evalExpr()

Given an `Expr` value, evaluate it and return its value:

    var i = 42
    var expr = ^[i + 1] 

    = io->evalExpr(expr)  # => 43

It accepts optional args that let you control name binding:

- `pos_args` for `$1 $2 $3`
- `dollar0` for `$0`
- `vars` for named variables

Example:

    var expr = ^["zero $0, one $1, named $x"]
    var s = io->evalExpr(expr, dollar0="z", pos_args=['one'], vars={x: "x"})
    echo $s  # => zero z, one one, named x

Note that these expressions that have effects:

- `^[ myplace->setValue(42) ]` - memory operation
- `^[ $(echo 42 > hi) ]` - I/O operation

---

To evaluate "purely", use the [`evalExpr()`][func/evalExpr] function.

[func/evalExpr]: chap-builtin-func.html#func/evalExpr

### captureStdout()

Run a Command, and return its stdout as a astring.

    var c = ^(echo hi)
    var stdout_str = io.captureStdout(c)  # => "hi"

It's like `$()` [command subs][command-sub], but can be used in pure functions
that have access to `io`.

[command-sub]: chap-word-lang.html#command-sub

`NUL` bytes and any trailing newline `\n` is removed,

If the command fails, `captureStdout()` raises an error, which can be caught
with `try`.

    try {
      var s = io.captureStdout(c)
    }

### captureAll()

Run a Command, and return its `stdout` string, `stderr` string, and integer
`status`.

    var c = ^(echo out; echo err >&2)
    var r = io.captureAll(c)  # => { stdout: "out", stderr: "err", status: 0 }

It's similar to `io.captureStdout`, but returns more info.

- NUL bytes and trailing newlines `\n` are **not** removed.
- Because it captures the status, it doesn't fail when the status is non-zero.

    = io.captureAll(^(echo stdout; echo stderr >&2; exit 3))
    (Dict)
    {
        stdout: 'stdout\n',
        stderr: 'stderr\n',
        status: 3
    }

### promptVal()

An API the wraps the `$PS1` language.  For example, to simulate `PS1='\w\$ '`:

    func renderPrompt(io) {
      var parts = []
      call parts->append(io.promptVal('w'))  # pass 'w' for \w
      call parts->append(io.promptVal('$'))  # pass '$' for \$
      call parts->append(' ')
      return (join(parts))
    }

### time()

TODO: Depends on system clock.

### strftime()

TODO: Like the awk function, this takes an timestamp directly.

In other words, it calls C localtime() (which depends on the time zone
database), and then C strftime().

### glob()

TODO: The free function glob() actually does I/O.  Although maybe it doesn't
fail?

### vm

An object with functions for introspecting the Oils VM.

### getFrame()

Given an index, get a handle to a call stack frame.

    var frame = vm.getFrame(0)   # global frame
    var frame = vm.getFrame(1)   # first frame pushed on the global frame

    var frame = vm.getFrame(-1)  # the current frame, aka local frame
    var frame = vm.getFrame(-2)  # the calling frame

If the index is out of range, an error is raised.

### getDebugStack()

Returns a list of [DebugFrame][] values, representing the current call stack.

[DebugFrame]: #DebugFrame

### id()

Returns an integer ID for mutable values like List, Dict, and Obj.

    = vm.id({})
    (Int)  123

You can use it to test if two names refer to the same instance.

`vm.id()` is undefined on immutable values like Bool, Int, Float, Str, etc.

