The Expression Language Is Mostly Python
========================================



## Expressions

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

## d->key is a shortcut for d['key']

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





Slices and Ranges
-----------------

---

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

