---
---

YSH vs. Shell
=============

This doc may help shell users understand YSH.  If you don't want to read a
comparison, see [A Tour of YSH](ysh-tour.html).

<div id="toc">
</div>

## YSH is Stricter at Parse Time, and Runtime

OSH and YSH both prefer [static
parsing](https://www.oilshell.org/blog/2016/10/22.html), so you get syntax
errors up front.  In shell, syntax errors can occur at runtime.

At runtime, we have `strict_*` shell options that handle edge cases.  YSH
generally fails faster than shell.  They're in the [option group](options.html)
`strict:all`.

## Three Core Sublanguages, Instead of 4

- Sublanguages in Bash: Command, Word, Arith, Bool
- Sublanguages in YSH: Command, Word, **Expression**

See the [List of
Sublanguages](https://www.oilshell.org/blog/2019/02/07.html#list-of-sublanguages)
on the blog.

### Python-like Expressions Replace Arith and Bool

This means that all these constructs are discouraged in favor of YSH
expressions:

```
[[ $x =~ $pat ]]

x=$(( x + 1 ))
(( x = x + 1 ))
let x=x+1

declare -A assoc=(['k1']=v1 ['k2']=v2)
```

See [YSH vs. Shell Idioms](idioms.html) for more rewrites.

### Command Sublanguage

Notable differences:

**Curly Braces** `{ }`, instead of `then fi` and `do done`.

**Keywords for Variable Assignment** like `var`, `const`, `setvar`, instead of
builtins like `local`, `readonly`, `myvar=foo`, etc.

Array literals like `var a = :| ale bean |` instead of `local a=(ale bean)`

**[Procs, Funcs, and Blocks](proc-func.html)** for modularity:

- Shell functions are "upgraded" into procs, with typed and named parameters.
- Python-like pure funcs compute on "interior" data.
- Ruby-like blocks enable reflection and metaprogramming.
  - Including declarative [Hay](hay.html) blocks

**Multiline strings** replace here docs.

`fork` and `forkwait` **builtins**, instead of `&` and `()`

Parentheses are instead used for Python-like expressions, e.g.

    if (x > 0) {
      echo 'positive'
    }

### Word Sublanguage

Notable differences:

[Simple Word Evaluation](simple-word-eval.html) replaces implicit word
splitting, and dynamic parsing/evaluation of globs.  It adds splicing of Lists
into `argv` arrays.

**Expression substitution** like `echo $[42 + a[i]]`.

This includes function calls: `echo $[join(['pea', nut'])]`

Raw strings can have an `r` prefix, like `echo r'C:\Program Files\'`.

## Runtime

### Builtin Commands and Functions

- YSH adds long flags to builtin commands, like `read --line`.
- YSH has builtin functions like `join()`.

### Shell Options, `shvar`, Registers

We upgrade bash's `shopt` mechanism with more options, like `shopt --set
parse_brace`.  These global options are controlled with scope

    shopt --unset errexit {
      rm /tmp/*
      rm /etc/*
    }

A `shvar` is similar to a `shopt`, but it has a string value, like `$IFS` and
`$PATH`.

    shvar PATH=. {
      my-command /tmp
    }

**Registers** are special variables set by the interpreter, beginning with `_`:

- `try` sets `_status` (preferred over `$?`)
- `_pipeline_status`, `_match()`, etc.

<!--
## TODO

- String Safety: tagged strings, ${x|html}
  - maybe captureBuffer(^(echo hi))
- [Modules](modules.html): for organizing code into files.  'use'

-->

### Data Languages, Not Ad Hoc Parsing

YSH programs are encouraged to use our JSON-like data languages to serialize
data.

For example, using an encoded array like `["one\n", "two \t three"]` results in
more obviously correct code than using ad hoc delimiters like spaces, commas,
or colons.

## Shell Features Retained

These bash features are still idiomatic in YSH:

- Brace expansion like `{alice,bob}@example.com`
- Process Substitution like `diff <(sort left.txt) <(sort right.txt)`

## Related Links

- [YSH vs. Shell Idioms](idioms.html) shows example of YSH and shell side by
  side.
- [What Breaks When You Upgrade to YSH](upgrade-breakage.html).  These are
  breaking changes.
- [YSH Expressions vs. Python](ysh-vs-python.html)
