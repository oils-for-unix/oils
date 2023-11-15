---
in_progress: true
---

YSH vs. Shell
=============

This doc aims to help shell users understand YSH

If you don't want to read a comparison, see [A Tour of YSH](ysh-tour.html).

<div id="toc">
</div>

## Strictness At Parse Time and Runtime

- Parse time: statically parsed.
- Runtime: Many `strict_*` shell options to reduce edge cases.  YSH generally
  fails faster than shell.

## There Are 3 Core Sublanguages Instead of 4

- Shell: Command, Word, Arith, Bool
- YSH: Command, Word, Expression (Python-Like Expressions)

### Expressions Replace Arith and Bool

So Many Shell Constructs Are Deprecated/Discouraged.

All of this is discouraged in favor of YSH expressions:

- `[[ $x =~ $pat ]]`
- `x=$(( x + 1 ))` and `(( x = x + 1 ))` and `let`, etc.
- `declare -A assoc=(['k1']=v1 ['k2']=v2)`

See [YSH vs. Shell Idioms](idioms.html) for more rewrites.

### Command Language Differences

- **Curly Braces** instead of `then fi` and `do done`
- **[Procs and Blocks](proc-block-func.html)** for Modularity
  - Shell functions are "upgraded" into procs, e.g. with named parameters
  - Ruby-like Blocks, and metaprogramming
- **Keywords for Variables** like `var`, `const`, `setvar` instead of builtins
  like `local`, `readonly`, `myvar=foo`, etc.
  - Array literals like `var a = :| ale bean |` instead of `local a=(ale bean)`.
- **Multiline strings** replace here docs
- `fork` and `forkwait` **builtins** instead of `&` and `()`.  Parentheses are
  generally used for Python-like expressions, e.g. `if (x > 0) { echo
  'positive' }`

See [A Tour of YSH](ysh-tour.html) for more details.

### Word Language Differences

- [Simple Word Evaluation](simple-word-eval.html)
  - Splicing with arrays
- Expression substitution like `$[42 + a[i] + f(x)]`
- Inline function calls like `echo $[join(['pea', nut'])]`
- You can write raw strings like `echo r'C:\Program Files\'`

See [A Tour of YSH](ysh-tour.html) for more details.

## Runtime

### Builtins

- YSH adds long flags like `read --line`
- YSH has builtin Functions

### Shell Options, `shvar`, Registers

- shopts: `shopt --set parse_brace`
- shvars: `IFS`, `_DIALECT`
- Registers: `_pipeline_status`, `_match()`, etc.

## Big Feature Categories

- **Builtin sub** with `${.myproc arg1 $x}` (TODO)
- String Safety (TODO)
- [Modules](modules.html): for organizing code into files
- Metaprogramming with Blocks (TODO)

## Some Shell Features That YSH Retains

Here's an incomplete list of bash features that are preserved:

- C-style strings like `$'line\n'`
- Brace expansion like `{alice,bob}@example.com`
- Process Substitution like `diff <(sort left.txt) <(sort right.txt)`

## Related Links

- [YSH vs. Shell Idioms](idioms.html) shows example of YSH and shell side by
  side.
- [What Breaks When You Upgrade to YSH](upgrade-breakage.html).  These are
  breaking changes.
- [YSH Expressions vs. Python](ysh-vs-python.html)
