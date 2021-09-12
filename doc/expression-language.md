---
in_progress: yes
---

Oil's Expression Language: A Mix of Python and JavaScript
=========================================================

Recall that Oil is composed of three interleaved languages:
[words](word-language.html), commands, and **expressions**.

This doc describes expressions, but only the things that are **not** in:

- [A Tour of the Oil Language](oil-language-tour.html).  The best intro.
- The `#expr-lang` section of [Oil Help
  Topics](oil-help-topics.html#expr-lang).  A reference.
- [Egg Expressions](eggex.html).  A "sublanguage" this language.

TODO: This doc should have example shell sessions, like the tour does.

<div id="toc">
</div>

## Preliminaries

### Comparison to Python and JavaScript

For a short summary, see [Oil vs. Python](oil-vs-python.html).  

### Constructs Shared Between Word and Expression Languages

All Substitutions: `$myvar`, `$(hostname)`, etc.

Variable subs:

    echo $myvar
    var x = $myvar

Command subs:

    echo $(hostname)
    var x = $(hostname)  # no quotes necessary
    var y = "name is $(hostname)"

String Literals:

    echo 'foo'
    var x = 'foo'
    echo "hello $name"

## Literals for Data Types

### String Literals: Like Shell, But Less Confusion About Backslashes

Oil has 3 kinds of string literal.  See the docs in the intro for detail, as
well as the [Strings](strings.html) doc.

As a detail, Oil disallows this case:

    $ var x = '\n'
      var x = '\n'
               ^~
    [ interactive ]:1: Strings with backslashes should look like r'\n' or $'\n'

In expression mode, you're forced to specify an explicit `r` or `$` when the
string has backslashes.  This is because shell has the opposite default as
Python: In shell, unadorned strings are raw.  In Python, unadorned strings
respect C escapes.

### Float Literals

- Floating point literals are also like C/Python: `1.23e-10`.  Except:
  - A number is required before the `.` now
  - No `1_000_000.123_456` because that was hard to implement as a hand-written
    Python regex.

Those last two caveats about floats are TODOs:
<https://github.com/oilshell/oil/issues/483>

### List Type: Both "Array" and List Literals

There is a single list type, but it has two syntaxes:

- `%(one two three)` for an "array" of strings.  This is equivalent to `['one',
  'two', 'three']`.
- `[1, [2, 'three', {}]]` for arbitrary Python-like "lists".

Longer example:

    var x = %(a b c)
    var x = %(
      'single quoted'
      "double quoted"
      $'c string'
      glob/*.py
      brace-{a,b,c}-{1..3}
    )

### Dict Literals Look Like JavaScript

Dict literals use JavaScript's rules, which are similar but not idential to
Python.

The key can be either a **bare word** or **bracketed expression**.

(1) For example, `{age: 30}` means what `{'age': 30}` does in Python.  That is,
`age` is **not** the name of a variable.  This fits more with the "dict as ad
hoc struct" philosophy.

(2) In `{[age]: 30}`, `age` is a variable.  You can put an arbitrary expression
in there like `{['age'.upper()]: 30}`.  (Note: Lua also has this bracketed key
syntax.)

(3) `{age, key2}` is the same as `{age: age, key2: key2}`.  That is, if the
name is a bare word, you can leave off the value, and it will be looked up in
the context where the dictionary is defined. 

This is what ES2015 calls "shorthand object properties":

- <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Object_initializer>

### Block, Expr, ArgList

TODO:

    var myblock = ^(ls | wc -l)  



## Operators on Multiple Types

Like JavaScript, Oil has two types of equality, but uses `===` and `~==` rather
than `===` and `==`.

### Exact Equality `=== !==`

- TODO: types must be the same, so `'42' === 42` is not just false, but it's an
  **error**.

### Approximate Equality `~==`

- There's no negative form like `!==`.  Use `not (a ~== b)` instead.
- Valid Operand Types:
  - LHS: `Str` only
  - RHS: `Str`, `Int`, `Bool`

Examples:

    ' foo ' ~== 'foo'  # whitespace stripped on LEFT only
    ' 42 ' ~== 42
    ' TRue ' ~== true  # true, false, 0, 1, and I think T, F

Currently, there are no semantics for floats, so none of these work:

    ' 42.0 ' ~== 42
    ' 42 ' ~== 42.0
    42.0 ~== 42
    42 ~== 42.0

(Should `float_equals()` be a separate function?)

### Function and Method Calls

    var result = add(x, y)
    var result = foo(x, named='default')

    if (s.startswith('prefix')) {
      echo yes
    }

Use Cases:

    var d = {1: 2, 3: 4}
    const k = keys(d)


## Boolean Operators

### Logical: `not` `and` `or`

Like Python.

### Ternary

    var cond = true
    var x = 'yes' if cond else 'no'

## Integer Operators

TODO: All of these do string -> int conversion, like

    '1_000' => 1000   
    '0xff' => 255
    '0o010' => 8
    '0b0001_0000' => 32

### Arithmetic `+ - * / // %` and `**`

Like Python.

### Bitwise `~ & | ^ << >>`

Like Python.

## Comparison on Integers and Floats `< <= > >=`

- NOTE: 
  - do we have `is` and `is not`?  Not sure I want identity in the language?
  - is everything nullable too?

https://github.com/oilshell/oil/blob/master/spec/oil-expr.test.sh#L550

```
if (1 < 2 <= 2 <= 3 < 4) {
  echo '123'
}
```

This syntax is directly from Python.  That is,

`x op y op  z`

is a shortcut for

`x op y and y op z`

Comments welcome!

## String Pattern Matching `~` and `~~`

- Eggex: `~` `!~` 
  - Similar to bash's `[[ $x =~ $pat ]]`
- Glob: `~~` `!~~`
  - Similar to bash's `[[ $x == *.py ]]`

## String and List Operators

In addition to pattern matching.

### Concatenation with `++`

    s ++ 'suffix'
    L ++ [1, 2] ++ %(a b)

### Indexing `a[i]`

    var s = 'foo'
    var second = s[1]    # are these integers though?  maybe slicing gives you things of length 1
    echo $second  # 'o'

    var a = %(spam eggs ham)
    var second = a[1]
    echo $second  # => 'eggs'

    echo $[a[-1]]  # => ham

Semantics are like Python:  Out of bounds is an error.

### Slicing `a[i:j]`

    var s = 'food'
    var slice = s[1:3]
    echo $second  # 'oo'

    var a = %(spam eggs ham)
    var slice = a[1:3]
    write -- @slice  # eggs, ham

Semantics are like Python:  Out of bounds is **not** an error.

## Dict Operators

### Membership with `in`

- And `not in`
- But strings and arrays use functions?
  - .find() ?  It's more of an algorithm.

### `d->key` is a shortcut for `d['key']`

> the distinction between attributes and dictionary members always seemed weird
> and unnecessary to me.

I've been thinking about this for [the Oil
language](http://www.oilshell.org/blog/2019/08/22.html), which is heavily
influenced by Python.

The problem is that dictionary attributes come from user data, i.e. from JSON,
while methods like `.keys()` come from the interpreter, and Python allows you
  to provide user-defined methods like `mydict.mymethod()` too.

Mixing all of those things in the same namespace seems like a bad idea.

In Oil I might do introduce an `->` operator, so `d->mykey` is a shortcut for
`d['mykey']`.

```
d.keys(), d.values(), d.items()  # methods
d->mykey
d['mykey']
```

Maybe you could disallow user-defined attributes on dictionaries, and make them
free:

```
keys(d), values(d), items(d)
d.mykey  # The whole namespace is available for users
```

However I don't like that this makes dictionaries a special case.  Thoughts?

## Deferred

### List and Dict Comprehensions

List comprehensions might be useful for a "faster" for loop?  It only does
expressions?

### Splat `*` and `**`

Python allows splatting into lists:

    a = [1, 2] 
    b = [*a, 3]

And dicts:

    d = {'name': 'alice'}
    d2 = {**d, age: 42}

### Ranges `1:n` (vs slices)

Deferred because you can use 

    for i in @(seq $n) {
      echo $i
    }

This gives you strings but that's OK for now.  We don't yet have a "fast" for
loop.

Notes:

- Oil slices don't have a "step" argument.  Justification:
  - R only has `start:end`, it doesn't have `start:end:step`
  - Julia has `start:step:end`!
  - I don't think the **step** is so useful that it has to be first class
    syntax.  In other words, Python's syntax is optimized for a rare case --
    e.g. `a[::2]`.
- Python has slices, but it doesn't have a range syntax.  You have to write
  `range(0, n)`. 
- A syntactic difference between slices and ranges: slice endpoints can be
  **implicit**, like `a[:n]` and `a[3:]`.

## Appendices

### Oil vs. Tea

- Tea: truthiness of `Str*` is a problem.  Nul, etc.
  - `if (mystr)` vs `if (len(mystr))`
  - though I think strings should be non-nullable value types?  They are
    slices.
  - they start off as the empty slice
- Coercsions of strings to numbers
  - `42` and `3.14` and `1e100`

### Implementation Notes

- Limitation:
  - Start with Str, StrArray, and AssocArray data model
  - Then add int, float, bool, null (for JSON)
  - Then add fuly recursive data model (depends on FC)
    - `value = ... | dict[str, value]`

