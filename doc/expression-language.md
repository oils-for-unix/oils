---
in_progress: yes
---

Oil's Expression Language: A Mix of Python and JavaScript
=========================================================

Recall that Oil is composed of three interleaved languages: words, commands,
and expressions.

For now, this document describes things that are **not** covered in:

- [A Tour of the Oil Language](oil-language-tour.html)
- The `#expr-lang` section of [Oil Help
  Topics](oil-help-topics.html#expr-lang)

That is, it has both trivia or high-level concepts that aren't covered
elsewhere.

For a short summary, see [Oil vs. Python](oil-vs-python.html).

<div id="toc">
</div>

## Literals

### String Literals Come From Shell, With Less Confusion About Backslashes

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

### The List Type Has Both "Array" and List Literals

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

## Constructs Shared Between Word and Expression Languages

### All Substitutions: `$myvar`, `$(hostname)`, etc.

Variable subs:

    echo $myvar
    var x = $myvar

Command subs:

    echo $(hostname)
    var x = $(hostname)  # no quotes necessary
    var y = "name is $(hostname)"

### String Literals : `'foo'` or `"hello $name"`

Same rules.

## Boolean Operators

### Logical: `not` `and` `or`

Like Python.

### Ternary

    var cond = true
    var x = 'yes' if cond else 'no'

## Integer Operators

### Arithmetic `+ - * / // %` and `**`

Like Python.

### Bitwise `~ & | ^ << >>`

Like Python.

### Comparison (Chained) `<`, `<=` etc.

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

## Equality and Pattern Matching

### Pattern Matching With Eggex and Globs

- Eggex: `~` `!~` 
  - Similar to bash's `[[ $x =~ $pat ]]`
- Glob: `~~` `!~~`
  - Similar to bash's `[[ $x == *.py ]]`

### Equality Is Exact or Approximate

- Exact: `===`, `!==`
- Approximate: `~==`
  - negation should use explicit `not`

## String and Array Operators

In addition to pattern matching.

### Indexing

    var s = 'foo'
    var second = s[1]    # are these integers though?  maybe slicing gives you things of length 1
    echo $second  # 'o'

    var a = %(spam eggs ham)
    var second = a[1]
    echo $second  # 'eggs'

Like Python semantics.  Out of bounds is an error.

### Slicing

    var s = 'food'
    var slice = s[1:3]
    echo $second  # 'oo'

    var a = %(spam eggs ham)
    var slice = a[1:3]
    write -- @slice  # eggs, ham

Like Python semantics.  Out of bounds isn't an error.

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

## Function and Method Calls Are Like Python

    var result = add(x, y)
    var result = foo(x, named='default')

    if (s.startswith('prefix')) {
      echo yes
    }

## Deferred

### Ranges like `1:n`

Deferred because you can do `@(seq $n)`  in Oil.  We don't yet have a "fast"
for loop?

OK I solved this problem in pretty much the way I said I would.

The thing that convinced me is that R only has `start:end`, it doesn't have
`start:end:step`.  And Julia has `start:step:end`!

I don't think the **step** is so useful that it has to be first class syntax.
In other words, Python's syntax is optimized for a rare case -- e.g. `a[::2]`.

Summary:

* Python doesn't have a special range syntax, i.e. you have to write `range(0,
  n)`.  In Oil you can write `0:n`.
* So he syntax is `0:n` for both slices (indices of collections) and ranges
  (iterables over integers).  
* But there's no literal syntax for the "step". If you want to use the step, you have to write it out like `range(1, 100, step=2)`.
  * (TODO: consider making step a **named** argument.  That is, it always has to be passed with a name, unlike in Python)
* A syntactic difference between slices and ranges: slice endpoints can be
  **implicit**, like `a[:n]` and `a[3:]`.
* Ranges and slices aren't unified -- that's the one failing tests.  But I'm
  pretty sure they should be, and they're each implemented in only 300-400
  lines of C.   If anyone wants to hack on CPython, let me know!
  * https://github.com/oilshell/oil/blob/master/Python-2.7.13/Objects/sliceobject.c
  * https://github.com/oilshell/oil/blob/master/Python-2.7.13/Objects/rangeobject.c
* All these tests pass except one:
  https://github.com/oilshell/oil/blob/master/spec/oil-slice-range.test.sh

This is all still up for discussion!  I'm going to write a blog post about it
later, but I appreciate any early feedback.

```
for (i in 0:n) {
  echo $i
}
```

### List and Dict Comprehensions

List comprehensions might be useful for a "faster" for loop?  It only does
expressions?

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

