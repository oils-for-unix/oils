<div style="float:right;">
  <span id="version-in-header">Version 0.7.pre5</span> <br/>

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

#### "Meta" Options Are The Most Important
 
This is how you opt into the Oil language:

```
shopt -s oil:all
```

It turns on:

- `errexit`, `nounset` (`sh` modes to get more errors)
- `pipefail` and `inherit_errexit` (`bash` modes to get more errors)
- Oil modes:
  - `simple-word-eval` (subsumes `nullglob` that `strict:all` includes)
  - `more_errexit`
  - `strict-*` (`strict-array`, etc.)
  - `parse-*` (`parse-at`, etc.)

When you care about running your script under other shells, use `shopt -s
strict:all`, which is documented in the [OSH manual](osh-manual.html).

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

- `simple_echo`.  Changes the flags accepted by the `echo` builtin, and style of flag parsing.
  See the `Builtins > echo` below.

- `simple-word-eval`.  Word evaluation consists of one stage rather than three:
  - No word splitting or empty elision.  (In other words, arity isn't data-dependent.)
  - Static globbing, but no dynamic globbing.  (In other words, data isn't re-parsed as code.)
  - This option is intended to be implemented by other shells.

TODO: copy examples from spec tests

```
echo $dir/*.py
```

- `more_errexit`.  A error in a command sub can cause the **parent shell** to
  exit fatally.  Also see `inherit_errexit` and `strict_errexit`.

#### Strict Options

These options produce more **programming errors**.  Importantly, the resulting
program is still compatible with other shells.

For example, `shopt -s strict-array` produces runtime errors when you confuse
strings and arrays.  After you fix these problems, your program will still run
correctly under `bash`.

In contrast, if you set `shopt -s simple-word-eval` (an option that doesn't
start with `strict-`), the semantics of your program have changed, and you can
no longer run it under other shells.  It's considered an "Oil option": by
setting it, you're upgrading to the Oil language.

See the [OSH manual](osh-manual.html) for a list of strict options and their
meaning.

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

In Oil, `set` is a keyword.  To use the `set` builtin, prefix it with `builtin`:

```
builtin set -o errexit
builtin set -- a b c
```

You can also turn on `set` options with the `shopt -o` flag: `shopt -o -s
errexit`.

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

### Builtins Can Accept Ruby-Style Blocks

Example of syntax that works:

```
cd / {
  echo $PWD
}
cd / { echo $PWD }
cd / { echo $PWD }; cd / { echo $PWD }
```

Syntax errors:

```
a=1 { echo bad };        # assignments can't take blocks
>out.txt { echo bad };   # bare redirects can't take blocks
break { echo bad };      # control flow can't take blocks
```

Runtime errors

```
local a=1 { echo bad };  # assignment builtins can't take blocks
```

#### Caveat: Blocks Are Space Sensitive

```
cd {a,b}  # brace substitution
cd { a,b }  # tries to run command 'a,b', which probably doesn't exist
```

more:

```
echo these are literal braces not a block \{ \}
echo these are literal braces not a block '{' '}'
# etc.
```


#### What's Allowed in Blocks?

You can break out with `return`, and it accepts Oil**expressions** (not
shell-like words) (note: not implemented yet).


```
cd {
  # return is for FUNCTIONS.
  return 1 + 2 * 3
}
```

The block can set vars in enclosing scope:

```
setvar('name', 1+2, up=1)
```

They can also get the value:

```
var namespace = evalblock('name', 1+2, up=1)

# _result is set if there was a return statement!

# namespace has all vars except those prefixed with _
var result = namespace->_result
```


#### Scope

evalblock()



### Builtins

#### cd

It now takes a block:

```
cd ~/src {
  echo $PWD
  ls -l
}

# current directory restored here

echo $PWD
ls -l
```

(This subsumes the functinoality of bash builtins `pushd` and `popd`.)

When a block is passed:

- `cd` doesn't set The `OLDPWD` variable (which is used to implement the `cd -`
  shortcut.)
- The directory stack for `pushd` and `popd` isn't cleared, as it is with a
	normal `cd` command.

#### echo

`shopt -s simple_echo` changes the `echo` builtin to accept the following long
flags, as well as the `--` separator between flags and args.

- `-sep`: Characters to separate each argument.  (Default: newline)
- `-end`: Characters to terminate the whole invocation.  (Default: newline)
- `-n`: A synonym for `-end ''`.

#### push

Append one or more strings to an array.

```
var array = @(1 '2 two')
push :array three four
echo @array  # prints 4 lines
```

### Builtin Flag Syntax

Oil's builtins accept long flags like `--verbose` and short flags like `-v`.

They behave like the popular GNU utilities on Linux distros, except that
`-long` (single hyphen) means the same thing as `--long`.  It's not a shortcut
for `-l -o -n -g` or `-l=ong`.  (This rule is consistent with the [Go flags
  package][goflags].)

[goflags]: https://golang.org/pkg/flag/

In addition, all of these are equivalent:

- `-sep x`
- `-sep=x`
- `--sep x`
- `--sep=x`

The first is preferred because it's the simplest and shortest.

(Trivia: Oil's flag syntax avoids the issue where `set -oo errexit nounset` is
a confusing equivalent to `set -o errexit -o nounset`.)

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
