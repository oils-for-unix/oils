Oil Literals
------------

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

### List Literals Are Unchanged

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
