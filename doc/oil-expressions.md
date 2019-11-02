---
in_progress: yes
---

The Expression Language Is Mostly Python
========================================

<div id="toc">
</div>

## Literals for Primitives

### String Literals


The last few commits implement **string literals** in expression mode.  They evaluate to Python-like byte strings (which may be utf-8 encoded) but have shell-like syntax: double-quoted strings allow `$subs` and single-quoted ones don't.

I had originally intended for something different for Oil, but I want command context and word context to be compatible.  You can just move words to the right of `=` and it still works.

```
echo 'sq' $'c-string\n' "dq $var"

# equivalent:
var x = 'sq'
var y = $'c-string\n'
var z = "dq $var"
echo $x $y $z
```

There are test cases at the end of this file:

https://github.com/oilshell/oil/blob/master/spec/oil-expr.test.sh

However, I dislike the shell syntax `$'\n'` for C strings.  `$` generally means substitution/interpolation, and this usage has nothing to do with it.  One of Oil's principles is **syntax should match semantics**.  Another feature is to try not to **invent new syntax**.  So a Python-like syntax is an alias:

```
var x = r'raw string\n'  # ends with backslash and n
var y = c'c-string\n'  # ends with newline
```

In addition I have **disallowed** this case:

```
$ var x = '\n'
  var x = '\n'
           ^~
[ interactive ]:1: Strings with backslashes should look like r'\n' or c'\n'
```

In expression mode, to the right of `=`, you are forced to specify an explicit `r` or `c` when the string has backslashes.  This is basically because shell has the opposite default as Python.  In shell, unadorned strings are raw.  In Python, unadorned strings respect C escapes.

Let me know if this makes sense!

----

Ideas for things to do:

- Allow C variants of double-quoted strings?  This is an odd omission from shell:

```
var x = c"$var\n"  # ends with newline
```

- Add `shopt -s parse_rawc`

```
echo r'sq' c'c-string\n'   # works the same in command mode as in expression mode, deprecating $'\n'
```

Of course, in shell

```
echo r'sq'
```

prints `rsq`, because of word joining!  So this would be a breaking change, hence the `parse_rawc` option.

I'm not sure how high priority these are.  I think I want to get on to ints, floats, dicts, and lists, but let me know!



### Bool, Int, Float, null literals

Implemented the following last night:

- `null`, `true`, `false` are our spellings instead of `None`, `True`, `False`
  - this follows JSON/JavaScript (and C/C++ to some extent), rather than Python
- decimal, binary, octal, hex literals.  Just like Python with `1_000_000`.
  - Except the tiny special case: we only support `0` and not `0_000` !
- Floating point literals are also like C/Python: `1.23e-10`.  Except:
  - A number is required before the `.` now
  - No `1_000_000.123_456` because that was hard to implement as a hand-written Python regex.

Those last two caveats about floats are TODOs:

https://github.com/oilshell/oil/issues/483

If anyone wants to work with re2c, let me know!  It's a very powerful tool.

## Literals for Collections

### Dict Literals Look Like JavaScript

The last few commits implement dict literals.  They're pretty much exactly what
JavaScript provides, as far as I can tell.

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

https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Object_initializer

Questions/comments are welcome!

### List Literals Are Like Python

Lists are heterogeneous.  Syntax is unchanged.

I don't expect list lists to be used that much.  They're mostly for JSON
compatibility.

Arrays and Tuples are preferred.

Or maybe lists are for composite data types?  Arrays are for primitives.

### Tuple Literals

I implemented tuple literals just like Python, since Oil is borrowing Python's
grammar.

https://github.com/oilshell/oil/commit/b738883bdd31aa5b0fbf640f67816d62943dc2a5

However it still has the annoying one-tuple issue:

```
x = f(3,5),  # tuple of return value because of trailing comma
x = 1,  # easier to see this way
```

The last option is kinda ugly but explicit.  The thing is: 1-tuples almost
never occur.  So it's OK if it's ugly!

```
x = tup(42)
```

I guess there is no problem with `()` as an empty tuple? 



### Two Types of Array Literals

#### Word Syntax for String Arrays

#### Expression Syntax for Typed Arrays

I implemented the literal syntax for Bool, Int, Float, and Str arrays.  The semantics still need to be polished, but the syntax is there.

Recall that Oil has **homogeneous string arrays**, borrowed from shell, instantiated using shell-like syntax

```
var myarray = @(bare words 'sq' "dq $var" ${other})
```

It also has Python-like **heterogeneous lists**.

```
var mylist = [1, 2, "hi", ['other', 'list']]  # Python/JavaScript/JSON-like syntax
```

In addition to sequences of heterogeneous type, they're also probably useful for sequences of compound types, as in JSON.  `[{dict: one}, {dict: two}]`

Now we have **homogeneous typed arrays**, i.e. for types other than string:

```
var mybools = @[true false false]
var myints = @[1 2 3]
var myfloats = @[1.2 3.3]
var mystrings = @['sq' "dq" (other.upper()) $x ${x}]
```

Important notes:


* There are **no commas**, which is consistent with the shell array syntax.
* Bare variables are **not allowed**.   They have to be `(x)` or `$x`.  This is to avoid confusion with the similar shell syntax, which uses "bare words".
* Items can be literal bools, ints, floats, strings, or **parenthesized expressions**
* The type of the **first element** determines the type of the entire array.  They are homogeneous!
* The columns of **data frames** i.e. the `Table` type in Oil, will be arrays.
In R they're called vectors.
  * https://github.com/oilshell/oil/wiki/Structured-Data-in-Oil

Most of these tests pass:

https://github.com/oilshell/oil/blob/master/spec/oil-array.test.sh

Note the important difference between these two expressions:

```
var x = @(1.0 2.0)  # these are STRINGS as in shell, like doing echo 1.0 2.0
var y = @[1.0 2.0]  # these are floating point numbers
```


As part of these changes, I also implemented **generator expressions**.

```
$ bin/oil
oil$ pp  Array[Int](x + 5 for x in 1:10)
IntArray        [6, 7, 8, 9, 10, 11, 12, 13, 14]
```

Well, at least the syntax.  The semantics still need work, especially with regard to scope.

Note that the `pp` **keyword** pretty-prints the result of an expression.  ([thread](https://oilshell.zulipchat.com/#narrow/stream/121540-oil-discuss/topic/pass.20and.20pp.20keywords.20implemented))


### Shell Array Literals with @()

```
var x = @(a b c)
var x = @(
  'single quoted'
  "double quoted"
  $'c string'
  glob/*.py
  brace-{a,b,c}-{1..3}
)
```

### Shell Command Substitution with $()

The `$(echo hi)` construct works in shell commands, and it also works in Oil
expressions:

```
var x = $(echo hi)           # no quotes necessary
var x = "$(echo hi) there"
```

## Operators


### Splice Arrays with @array

```
var a1 = @(a b)
var a2 = @(c d)
echo / @a1 / @a2 /   # gives / a b / c d /
```

### Future

- "Legacy-free" command substitution with `$[echo hi]`
- "Legacy-free" and typed literals like
  - `@[a 'b c' "hi $name"]`
  - `@[1 2 3]` 
  - `@[3.14 1.50 2.33]`
- For details, see the wiki page [Implementing the Oil Expression
  Language](https://github.com/oilshell/oil/wiki/Implementing-the-Oil-Expression-Language)



Most of the operator language is now implemented (in the metacircular style).

Oil's operators largely follow Python, except:

- integer division `//` is `div`.  I guess this is a purely aesthetic thing.
- Exponentation is `^` rather than `**`.  This is what R does (and I think Julia too.)
- xor is `xor` instead of `^`.

I noted that here awhile ago, and largely followed it.

https://github.com/oilshell/oil/wiki/Implementing-the-Oil-Expression-Language

One complication is that there's no equivalent of `//=` or `^=`, like `div=` and `xor=`.  That just feels silly.  I'm inclined to leave those out because you can always write:

```
set x = x xor y
set x = x div d
```

I don't expect those to be particularly common.   `x |= mask` is common but I
don't think `x ^= mask` is ?

Comments welcome!

https://github.com/oilshell/oil/commit/41f53e9d2180feea1c283118909a12a250efda07

Comment about it here:

https://lobste.rs/s/2cw6ov/say_something_you_dislike_about_language#c_c5mk2l

### d->key is a shortcut for d['key']

> the distinction between attributes and dictionary members always seemed weird and unnecessary to me.

I've been thinking about this for [the Oil language](http://www.oilshell.org/blog/2019/08/22.html), which is heavily influenced by Python.

The problem is that dictionary attributes come from user data, i.e. from JSON, while methods like `.keys()` come from the interpreter, and Python allows you to provide user-defined methods like `mydict.mymethod()` too.

Mixing all of those things in the same namespace seems like a bad idea.

In Oil I might do introduce an `->` operator, so `d->mykey` is a shortcut for `d['mykey']`.

```
d.keys(), d.values(), d.items()  # methods
d->mykey
d['mykey']
```

Maybe you could disallow user-defined attributes on dictionaries, and make them free:

```
keys(d), values(d), items(d)
d.mykey  # The whole namespace is available for users
```

However I don't like that this makes dictionaries a special case.  Thoughts?





### Slices and Ranges


OK I solved this problem in pretty much the way I said I would.

The thing that convinced me is that R only has `start:end`, it doesn't have `start:end:step`.  And Julia has `start:step:end`!

I don't think the **step** is so useful that it has to be first class syntax.  In other words, Python's syntax is optimized for a rare case -- e.g. `a[::2]`.

Summary:

* Python doesn't have a special range syntax, i.e. you have to write `range(0, n)`.  In Oil you can write `0:n`.
* So he syntax is `0:n` for both slices (indices of collections) and ranges (iterables over integers).  
* But there's no literal syntax for the "step". If you want to use the step, you have to write it out like `range(1, 100, step=2)`.
  * (TODO: consider making step a **named** argument.  That is, it always has to be passed with a name, unlike in Python)
* A syntactic difference between slices and ranges: slice endpoints can be **implicit**, like `a[:n]` and `a[3:]`.
* Ranges and slices aren't unified -- that's the one failing tests.  But I'm pretty sure they should be, and they're each implemented in only 300-400 lines of C.   If anyone wants to hack on CPython, let me know!
  * https://github.com/oilshell/oil/blob/master/Python-2.7.13/Objects/sliceobject.c
  * https://github.com/oilshell/oil/blob/master/Python-2.7.13/Objects/rangeobject.c
* All these tests pass except one: https://github.com/oilshell/oil/blob/master/spec/oil-slice-range.test.sh

This is all still up for discussion!  I'm going to write a blog post about it later, but I appreciate any early feedback.


```
for (i in 0:n) {
  echo $i
}
```

### Chained Comparison

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

