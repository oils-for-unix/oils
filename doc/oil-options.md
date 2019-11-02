---
in_progress: yes
---

Oil Options
===========

<!--

Notes:
- OSH manual describes some options.  Could move them here.
- Copy in frmo quick ref
-->

<div id="toc">
</div>


## Use **Option Groups** To Gradually Opt In to Oil
 
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

## That Affect Parsing

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


---

`shopt -s parse_brace` does three things:

- allow builtins like `cd` to take a block (discussed in a [recent thread](https://oilshell.zulipchat.com/#narrow/stream/121540-oil-discuss/topic/cd.20now.20takes.20a.20Ruby-like.20block))
- `if`, `while/until`, `for`, `case` not use curly brace delimiters instead of `then/fi`, `do/done`, etc.  See below.
- To remove confusion, braces must be balanced inside a word.  echo `foo{` is an error.  It has to be `echo foo\{` or `echo 'foo{'`.
  - This is so that the syntax errors are better when you forget a space.
  - In a correct brace expansion, they're always balanced: `echo {andy,bob}@example.com`


Test cases start here:

https://github.com/oilshell/oil/blob/master/spec/oil-options.test.sh#L257

Examples:

```
if test -d / {
  echo one
} elif test -d /tmp {
  echo two
} else {
   echo none
}
# can also be put all on one line

while true {
  echo hi
  break
}

for x in a b c {
  echo $x
}

case $x {
  *.py)
    echo python
    ;;
  *.sh)
    echo shell
    ;;
}
```


What's the motivation for this?  Mainly familiarity: I hear a lot of feedback that nobody can remember how to write an if statement or a for loop in shell.  I believe this syntax is easier to remember, with the possible exception of `case`, which still has some shell legacy.

Spoiler: there will also be **expression**-based variants of each of these constructs:

```
if (x > 0) {
  echo hi
}
while (x > 0) {
  echo hi
}
for (x in @(a b c)) {
  echo $x
}
```

There is probably going to be `switch/case` or `match/case`, but that will
likely come much later!

## That Affect Runtime Behavior

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

## Strict Option Produce More Errors

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

