<div style="float:right;">
  <span id="version-in-header">Version 0.7.pre2</span> <br/>

  <!-- TODO: date support in cmark.py -->
  <span style="" class="date">
  <!-- REPLACE_WITH_DATE -->
  </span>
</div>

Oil User Manual
---------------

The Oil project aims to transform Unix shell into a better programming
language.

This manual covers the parts of Oil that are **new and unique**.  In contrast,
the [OSH User Manual](osh-manual.html) describes parts of `osh` that overlap
with other shells like `bash`.

Everything described here is part of the `osh` binary.  In other words, the Oil
language is implemented with a set of backward-compatible extensions, often
using shell options that are toggled with the `shopt` builtin.

(In the distant future, there may be a legacy-free `oil` binary.)

<!-- cmark.py expands this -->
<div id="toc">
</div>

### Options

#### Parsing Options

Options that affect parsing start with `parse-`.

- `shopt -s parse-at` enables splicing:

```
echo @words
```

and inline function calls.

```
echo @split(x)
```

See examples below.

#### Runtime Options

- `simple-word-eval`
  - Meant to be implemented by other shells

TODO: copy examples from spec tests

```
echo $dir/*.py
```

### Keywords

#### `var` to declare variables

Python- or JavaScript- like syntax on RHS.

```
var myint = 1
var mystring = 'str'
var doublequoted = "hello $name"
var myarray = @(ls -a -l)
var mydict = {name: 'bob', age: 10}
var mylist = [42, false, "hello"]
```

#### `setvar` or `set` to update variables

```
setvar myint = 1
```

Spelled with `set`:

```
shopt -s parse-set

set mylist[0] = 43
set mylist[0] += 1  # increment by 1
set mydict['name'] = 'other'
```

#### Future

(Not implemented)

- const (compile-time?)
- auto for "auto-vivifcation"

### Expressions

#### Shell Array Literals with @()

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

#### Shell Command Substitution with $()

The `$(echo hi)` construct works in shell commands, and it also works in Oil
expressions:

```
var x = $(echo hi)           # no quotes necessary
var x = "$(echo hi) there"
```

#### Splice Arrays with @array

```
var a1 = @(a b)
var a2 = @(c d)
echo / @a1 / @a2 /   # gives / a b / c d /
```

#### Future

- "Legacy-free" command substitution with `$[echo hi]`
- "Legacy-free" and typed literals like
  - `@[a 'b c' "hi $name"]`
  - `@[1 2 3]` 
  - `@[3.14 1.50 2.33]`
- For details, see the wiki page [Implementing the Oil Expression
  Language](https://github.com/oilshell/oil/wiki/Implementing-the-Oil-Expression-Language)

### Inline function Calls

#### That Return Strings

```
echo $stringfunc(x, y)
```

NOTE: `"__$stringfunc(x, y)__"` doesn't work.  Do this instead:

```
var s = stringfunc(x, y)
echo "__$s__"
```

#### That Return Arrays

```
cc -o foo -- @arrayfunc(x, y)
```


### Special Variables

- `ARGV` instead of `"$@"`

In command mode:

```
f() {
  echo @ARGV
}
f 'foo bar' 'spam eggs'
```

In expression mode:

```
var length = len(ARGV)
var s = sorted(ARGV)
```

### Builtins

- push

#### Future

- fork, wait
- log, die
- write


### Links

- TODO: Examples on the blog

#### Blog Post

Five different things have to come together!

- keywords: `var`, `setvar`
- expressions:
  - `var myarray = @(one two three)` (array of strings)
- options:
  - `simple-word-eval`
    - meant to be implemented by other shells
  - `parse-at`
    - `@words` and `@arrayfunc(x, y)`
- builtin: `push`
  - syntactic sugar for `do myarray.push(...)`
- special vars: `ARGV`

Higher Level: "A Plan to Transform Shell into a Better Language".

Maybe do an overview.
