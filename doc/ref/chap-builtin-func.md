---
title: Builtin Functions (Oils Reference)
all_docs_url: ..
body_css_class: width40
default_highlighter: oils-sh
preserve_anchor_case: yes
---

<div class="doc-ref-header">

[Oils Reference](index.html) &mdash;
Chapter **Builtin Functions**

</div>

This chapter describes builtin functions (as opposed to [builtin
commands](chap-builtin-cmd.html).)

<span class="in-progress">(in progress)</span>

<div id="dense-toc">
</div>

## Values

### len()

Returns the

- number of entries in a `List`
- number of pairs in a `Dict`
- number of bytes in a `Str`
  - TODO: `countRunes()` can return the number of UTF-8 encoded code points.

### func/type()

Given an arbitrary value, returns a string representing the value's runtime
type.

For example:

    var d = {'foo': 'bar'}
    var n = 42

    = type(d)    # => (Str)    'Dict'
    = type(n)    # => (Str)    'Int'

Similar names: [type][]

[type]: chap-index.html#type


## Conversions

### bool()

Returns the truth value of its argument. Similar to `bool()` in python, it
returns `false` for:

- `false`, `0`, `0.0`, `''`, `{}`, `[]`, and `null`.

Returns `true` for all other values.

### int()

Given a float, returns the largest integer that is less than its argument (i.e. `floor()`).

    = int(1.99)  # => (Int)    1

Given a string, `Int()` will attempt to convert the string to a base-10
integer.

    = int('10')  # => (Int)   10

<!-- TODO
The base can be overridden by calling with a second argument.
    = int('10', base=2)  # => (Int)   2
-->

```raw
= int('not_an_integer')  # fails with an expression error
```

### float()

Given an integer, returns the corresponding floating point representation.

    = float(1)       # => (Float)   1.0

Given a string, `Float()` will attempt to convert the string to float.

    = float('1.23')  # => (Float)   1.23

```raw
= float('bar')  # fails with an expression error
```

### str()

Converts a `Float` or `Int` to a string.

### list()

Given a list, returns a shallow copy of the original.

    = list({'a': 1, 'b': 2})  # => (List)   ['a', 'b']

Given an iterable value (e.g. a range or dictionary), returns a list containing
one element for each item in the original collection.

    = list(1 ..= 5)           # =>  (List)   [1, 2, 3, 4, 5]

### dict()

Given a dictionary, returns a shallow copy of the original.

### runes()

TODO

Given a string, decodes UTF-8 into a List of integer "runes" (aka code points).

Each rune is in the range `U+0` to `U+110000`, and **excludes** the surrogate
range.

```raw
runes(s, start=-1, end=-1)
```

TODO: How do we signal errors?

(`runes()` can be used to implement implemented Python's `ord()`.)

### encodeRunes()

TODO

Given a List of integer "runes" (aka code points), return a string.

(`encodeRunes()` can be used to implement implemented Python's `chr()`.)

### bytes()

TODO

Given a string, return a List of integer byte values.

Each byte is in the range 0 to 255.

### encodeBytes()

TODO

Given a List of integer byte values, return a string.

## Str

### strcmp()

Compare 2 strings, using lexicographic order on bytes.

Returns 0 if the strings are equal:

    = strcmp('z', 'z')   # => (Int) 0

Or -1 if the first is less than the second:

    = strcmp('a', 'aa')  # => (Int) -1

Or 1 if the first is greater than the second:

    = strcmp('z', 'a')   # => (Int) 1

## List

### join()

Given a List, stringify its items, and join them by a separator.  The default
separator is the empty string.

    var x = ['a', 'b', 'c']

    echo $[join(x)]       # => abc

    # optional separator
    echo $[join(x, ' ')]  # => a b c

As a reminder, you can call it with the [fat-arrow][] operator `=>` for function chaining:

    var items = [1, 2, 3]

    json write (items => join())      # => "123"
    json write (items => join(' '))   # => "1 2 3"
    json write (items => join(', '))  # => "1, 2, 3"

[fat-arrow]: chap-expr-lang.html#fat-arrow

## Dict

### keys()

Returns all existing keys from a dict as a list of strings.

    var en2fr = {
      hello: "bonjour",
      friend: "ami",
      cat: "chat"
    }
    = keys(en2fr)
    # => (List 0x4689)   ["hello","friend","cat"]

### values()

Similar to `keys()`, but returns the values of the dictionary.

    var person = {
      name: "Foo",
      age: 25,
      hobbies: :|walking reading|
    }
    = values(en2fr)
    # => (List 0x4689)   ["Foo",25,["walking","reading"]]

### get()

Return value for given key, falling back to the default value if the key 
doesn't exist.

    var book = {
      title: "Hitchhiker's Guide",
      published: 1979,
    }

    var published = get(book, 'published', null)
    = published
    # => (Int)   1979

    var author = get(book, 'author', "???")
    = author
    # => (Str)   "???"

If not specified, the default value is `null`:

    var author = get(book, 'author')
    = author
    # => (Null)   null

## Float

### floatsEqual()

Check if two floating point numbers are equal.

    = floatsEqual(42.0, 42.0)  # => (Bool)   true

It's usually better to make an approximate comparison:

    use $LIB_YSH/math.ysh --pick abs
    var f1 = 0.3
    var f2 = 0.4
    = abs(f1 - f2) < 0.001    # => (Bool)   false

## Obj

Let's use this definition:

    var fields = {x: 42}
    var obj = Obj.new(fields, null)

### first()

Get the Dict that contains an object's properties.

    = first(obj)  # => (Dict)  {x: 42}

The Dict and Obj share the same storage.  So if the Dict is modified, the
object is too.

If you want a copy, use `dict(obj)`.

### rest()

Get the "prototype" of an Obj, which is another Obj, or null:

    = rest(obj)  # => (Null)  null

## Word

### maybe()

Turn a string into a list, based on its emptiness.

It's designed to be used to construct `argv` arrays, along with
[expr-splice][].

    var empty = ''
    write -- ale @[maybe(empty)] corn  # => ale corn

    var s = 'bean'
    write -- ale @[maybe(s)] corn     # => ale bean corn

[expr-splice]: chap-word-lang.html#expr-splice

### shSplit()

Split a string into a List of strings, using the shell algorithm that respects
`$IFS`.

Prefer [split()][split] to `shSplit()`.

[split]: chap-type-method.html#split

## Serialize

### toJson()

Convert an object in memory to JSON text:

    = toJson({name: "alice"})          # => (Str)   '{"name":"alice"}'

Add indentation by passing the `space` param:

    = toJson([42], space=2)            # => (Str)   "[\n  42\n]"

Turn non-serializable types into `null`, instead of raising an error:

    = toJson(/d+/, type_errors=false)  # => (Str)   'null'

The `toJson()` function is to `json write (x)`, except the default value of
`space` is 0.

See [err-json-encode][] for errors.

[err-json-encode]: chap-errors.html#err-json-encode

### fromJson()

Convert JSON text to an object in memory:

    = fromJson('{"name":"alice"}')     # => (Dict)   {"name": "alice"}

Similar to `json read <<< '{"name": "alice"}'`.

See [err-json-decode][] for errors.

[err-json-decode]: chap-errors.html#err-json-decode

### toJson8()

Like `toJson()`, but it also converts binary data (non-Unicode strings) to
J8-style `b'foo \yff'` strings.

In contrast, `toJson()` will do a lossy conversion with the Unicode replacement
character.

See [err-json8-encode][] for errors.

[err-json8-encode]: chap-errors.html#err-json8-encode

### fromJson8()

Like `fromJson()`, but it also accepts binary data denoted by J8-style `b'foo
\yff'` strings.

See [err-json8-decode][] for errors.

[err-json8-decode]: chap-errors.html#err-json8-decode

## Pattern

### `_group()`

Like `Match.group()`, but accesses the global match created by `~`:

    if ('foo42' ~ / d+ /) {
      echo $[_group(0)]  # => 42
    }

### `_start()`

Like `Match.start()`, but accesses the global match created by `~`:

    if ('foo42' ~ / d+ /) {
      echo $[_start(0)]  # => 3
    }

### `_end()`

Like `Match.end()`, but accesses the global match created by `~`:

    if ('foo42' ~ / d+ /) {
      echo $[_end(0)]  # => 5
    }

## Reflection

### func/eval()

This function is like [`io->eval()`][io/eval], but it disallows I/O.

Example:

    var cmd = ^(const x = 42; )
    = eval(cmd, to_dict=true)  # => (Dict)   {x: 42}

[io/eval]: chap-type-method.html#io/eval

### func/evalExpr()

This function is like [`io->evalExpr()`][io/evalExpr], but it disallows I/O.

Example:

    var x = 42
    var expr = ^[x + 1]
    var val = evalExpr(expr)  # 43

[io/evalExpr]: chap-type-method.html#io/evalExpr

## Introspect

### `shvarGet()`

Given a variable name, return its value.  It uses the "dynamic scope" rule,
which looks up the stack for a variable.

It's meant to be used with `shvar`:

    proc proc1 {
      shvar PATH=/tmp {  # temporarily set PATH in this stack frame
        echo
      }

      proc2
    }

    proc proc2 {
      proc3
    }

    proc proc3 {
      var path = shvarGet('PATH')  # Look up the stack (dynamic scoping)
      echo $path  # => /tmp
    }

    proc1

Note that `shvar` is usually for string variables, and is analogous to `shopt`
for "booleans".

If the variable isn't defined, `shvarGet()` returns `null`.  So there's no way
to distinguish an undefined variable from one that's `null`.

### `getVar()`

Given a variable name, return its value.

    var x = 42
    = getVar('x')  # => (Int)   42

The variable may be local or global.  (Compare with `shvarGet()`.) the "dynamic
scope" rule.)

If the variable isn't defined, `getVar()` returns `null`.  So there's no way to
distinguish an undefined variable from one that's `null`.

### `setVar()`

Bind a name to a value, in the local scope.  Returns nothing.

    call setVar('myname', 42)

This is like

    setvar myname = 42

except the name can is a string, which can be constructed at runtime.

---

You can also bind globals:

    call setVar('myname', 42, global=true)

which is like

    setglobal myname = 42

### `getShFunction`

Given the name of a shell function, return the corresponding [Proc][] value, or
`null` if it's not found.

[Proc]: chap-type-method.html#Proc

### `parseCommand()`

Given a code string, parse it as a command (with the current parse options).

Returns a `value.Command` instance, or raises an error.

### `parseExpr()`

TODO:

Given a code string, parse it as an expression.

Returns a `value.Expr` instance, or raises an error.

### `bindFrame()`

TODO

## Hay Config

### parseHay()

### evalHay()


## Hashing

### sha1dc()

Git's algorithm.

### sha256()


<!--

### Better Syntax

These functions give better syntax to existing shell constructs.

- `shQuote()` for `printf %q` and `${x@Q}`
- `trimLeft()` for `${x#prefix}` and  `${x##prefix}`
- `trimRight()` for `${x%suffix}` and  `${x%%suffix}` 
- `trimLeftGlob()` and `trimRightGlob()` for slow, legacy glob
- `upper()` for `${x^^}`
- `lower()` for `${x,,}`
- `strftime()`: hidden in `printf`

-->
