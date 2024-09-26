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

A bash array holds a sequence of strings.  Some entries may be unset, i.e.
*not* an empty string.

See [sh-array][] for details.  In YSH, prefer to use [List](#List) instances.

[sh-array]: chap-osh-assign.html#sh-array


### BashAssoc

A bash associative array is a mapping from strings to strings.

See [sh-assoc][] for details.  In YSH, prefer to use [Dict](#Dict) instances.

[sh-assoc]: chap-osh-assign.html#sh-assoc

## Atom Types

### Null

The `Null` type has a single value spelled `null`.  (Related:
[atom-literal][]).

[atom-literal]: chap-expr-lang.html#atom-literal

### Bool

The `Bool` type has 2 values: `true` and `false`.  (Related: [atom-literal][]).

## Number Types

### Int

Integers are currently 64-bit signed integers (on all platforms).  TODO: they
should be arbitrary precision.

There are many way of writing integers; see [int-literal][].

In shell, ASCII strings like `'42'` are often used for calculations on
integers.  But you can use a "real" integer type in YSH.

[int-literal]: chap-expr-lang.html#int-literal


### Float

Floats are at least 32 bits wide.

See [float-literal][] for how to denote them.

[float-literal]: chap-expr-lang.html#float-literal

<!-- TODO: reduce from 64-bit to 32-bit -->

## Str

In Oils, strings may contains any sequence of bytes, which may be UTF-8
encoded.

Internal NUL bytes (`0x00`) are allowed.

When passing such strings to say the [cd][] builtin, the string will be
truncated before the NUL.  This is because most C functions like `chdir()` take
NUL-terminated strings.

[cd]: chap-builtin-cmd.html#cd

### find()

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

## List

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

### remove()

### reverse()

Reverses a list in place.

    var fruits = :|apple banana pear|
    call fruits->reverse()
    echo @fruits  # => pear banana apple

## Dict

A Dict contains an ordered sequence of key-value pairs.  Given the key, the
value can be retrieved efficiently.

### keys()

Returns all existing keys from a dict as a list of strings.

    var en2fr = {
      hello: "bonjour",
      friend: "ami",
      cat: "chat"
    }
    = en2fr => keys()
    # => (List 0x4689)   ["hello","friend","cat"]

### values()

Similar to `keys()`, but returns the values of the dictionary.

    var person = {
      name: "Foo",
      age: 25,
      hobbies: :|walking reading|
    }
    = en2fr => values()]
    # => (List 0x4689)   ["Foo",25,["walking","reading"]]

### get()

Return value for given key, falling back to the default value if the key 
doesn't exist. Default is required.

    var book = {
      title: "Hitchhiker's Guide",
      published: 1979,
    }
    var published = book => get("published", null)
    = published
    # => (Int 1979)

    var author = book => get("author", "???")
    = author
    # => (Str "???")

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

### inc()

### accum()

## Range
  
A `Range` is a pair of two numbers, like `42 .. 45`.

Ranges are used for iteration; see [ysh-for][].

[ysh-for]: chap-cmd-lang.html#ysh-for

## Eggex

An `Eggex` is a composable regular expression.  It can be spliced into other
regular expressions.

## Match

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

## Place

### setValue()

A Place is used as an "out param" by calling setValue():

    proc p (out) {
      call out->setValue('hi')
    }

    var x
    p (&x)
    echo x=$x  # => x=hi


## Code Types

### Expr

An unevaluated expression.  You can create an `Expr` with an expression literal
([expr-literal][]):

    var expr = ^[42 + a[i]]

[expr-literal]: chap-expr-lang.html#expr-lit

### Command

An unevaluated command.  You can create a `Command` with a "block expression"
([block-expr][]):

    var block = ^(echo $PWD; ls *.txt)

[block-expr]: chap-expr-lang.html#block-expr

### BuiltinFunc

A func that's part of Oils, like `len()`.

### BoundFunc

The [thin-arrow][] and [fat-arrow][] create bound funcs:

    var bound = '' => upper
    var bound2 = [] -> append

[thin-arrow]: chap-expr-lang.html#thin-arrow
[fat-arrow]: chap-expr-lang.html#thin-arrow

## Func

User-defined functions.

## Proc

User-defined procs.

## Module

TODO:

A module is a file with YSH code.

<!-- can it be a directory or tree of files too? -->

## IO

### eval()

Evaluate a command, and return `null`.

    var c = ^(echo hi)
    call io->eval(c)

It's like like the `eval` builtin, and meant to be used in pure functions.

<!--
TODO: We should be able to bind positional args, env vars, and inspect the
shell VM.

Though this runs in the same VM, not a new one.
-->

### evalToDict()

The `evalToDict()` method is like the `eval()` method, but it also returns a
Dict of bindings.

TODO:

- Does it push a new frame?  Or is this a new module?
  - I think we have to change the lookup rules
- Move functions like `len()` to their own `__builtin__` module?

### captureStdout()

Capture stdout of a command a string.

    var c = ^(echo hi)
    var stdout_str = _io.captureStdout(c)  # => "hi"

It's like `$()`, but useful in pure functions.  Trailing newlines `\n` are
removed.

If the command fails, `captureStdout()` raises an error, which can be caught
with `try`.

    try {
      var s = _io->captureStdout(c)
    }

### promptVal()

An API the wraps the `$PS1` language.  For example, to simulate `PS1='\w\$ '`:

    func renderPrompt(io) {
      var parts = []
      call parts->append(io.promptval('w'))  # pass 'w' for \w
      call parts->append(io.promptval('$'))  # pass '$' for \$
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

