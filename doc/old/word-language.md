---
in_progress: yes
default_highlighter: oils-sh
css_files: ../../web/base.css ../../web/manual.css ../../web/toc.css
---

Word Language
=============

Recall that Oil is composed of three interleaved languages: **words**,
[commands](command-language.html), and [expressions](expression-language.html).

This doc describes words, but only the things that are **not** in:

- [A Tour of the Oil Language](oil-language-tour.html)
- The `#word-lang` section of [OSH Help
  Topics](osh-help-topics.html#word-lang)
- The `#word-lang` section of [Oil Help
  Topics](oil-help-topics.html#word-lang)

<div id="toc">
</div>

## What's a Word?

A word is an expression like `$x`, `"hello $name"`, or `{build,test}/*.py`.  It
evaluates to a string or an array of strings.

Generally speaking, Oil behaves like a simpler version of POSIX shell / bash.
Sophisticated users can read [Simple Word Evaluation](simple-word-eval.html)
for a comparison.

## Contexts Where Words Are Used

### Words Are Part of Expressions and Commands

Part of an expression:

    var x = ${y:-'default'}

Part of a command:

    echo ${y:-'default'}

### Word Sequences: in for loops and array literals

The three contexts where splitting and globbing apply are the ones where a
**sequence** of words is evaluated (`EvalWordSequence`):

1. [Command]($help:simple-command): `echo $x foo`
2. [For loop]($help:for): `for i in $x foo; do ...`
3. [Array Literals]($help:array): `a=($x foo)` and `var a = :| $x foo |` ([oil-array]($help))

### Oil vs. Bash Array Literals

Oil has a new array syntax, but it also supports the bash-compatible syntax:

```
local myarray=(one two *.py)  # bash

var myarray = :| one two *.py |  # Oil style
```

### Oil Discourages Context-Sensitive Evaluation

Shell also has contexts where it evaluates words to a **single string**, rather
than a sequence, like:

```sh
# RHS of Assignment
x="${not_array[@]}"
x=*.py  # not a glob

# Redirect Arg
echo foo > "${not_array[@]}"
echo foo > *.py  # not a glob

# Case variables and patterns
case "${not_array1[@]}" in 
  "${not_array2[@]}")
    echo oops
    ;;
esac

case *.sh in   # not a glob
  *.py)        # a string pattern, not a file system glob
    echo oops
    ;;
esac
```

The behavior of these snippets diverges a lot in existing shells.  That is,
shells are buggy and poorly-specified.

Oil disallows most of them.  Arrays are considered separate from strings and
don't randomly "decay".

Related: the RHS of an Oil assignment is an expression, which can be of any
type, including an array:

```
var parts = split(x)       # returns an array
var python = glob('*.py')  # ditto

var s = join(parts)        # returns a string
```

## Sigils

This is a recap of [A Feel for Oil's Syntax](syntax-feelings.html).

### `$` Means "Returns One String"

Examples:

- All substitutions: var, command, arith
  - TODO: Do we have `$[a[x+1]]` as an expression substitution?
  - Or `$[ /pat+ /]`?
  - I don't think so.

- Inline function calls, a YSH extension: `$[join(myarray)]`

(C-style strings like `$'\n'` use `$`, but that's more of a bash anachronism.
In Oil, `c'\n'` is preferred.

### `@` Means "Returns An Array of Strings"

Enabled with `shopt -s parse_at`.

Examples:

- `@myarray`
- `@[arrayfunc(x, y)]`

These are both Oil extensions.

The array literal syntax also uses a `@`:

```
var myarray = :| 1 2 3 |
```

## OSH Features

### Word Splitting and Empty String Elision

Uses POSIX behavior for unquoted substitutions like `$x`.

- The string value is split into args with `$IFS`.
- If the string value is empty, no args are produced.

### Implicit Joining

Shell has odd "joining" semantics, which are supported in Oil but generally
discouraged:

    set -- 'a b' 'c d'
    argv.py X"$@"X  # => ['Xa', 'b', 'c', 'dX']

In Oil, the RHS of an assignment is an expression, and joining only occurs
within double quotes:

    # Oil
    var joined = $x$y    # parse error
    var joined = "$x$y"  # OK

    # Shell
    joined=$x$y          # OK
    joined="$x$y"        # OK

<a name="extended-glob"></a>
### Extended Globs

Extended globs in OSH are a "legacy syntax" modelled after the behavior of
`bash` and `mksh`.  This features adds alternation, repetition, and negation to
globs, giving the power of regexes.

You can use them to match strings:

    $ [[ foo.cc == *.(cc|h) ]] && echo 'matches'  # => matches

Or produce lists of filename arguments:

    $ touch foo.cc foo.h
    $ echo *.@(cc|h)  # => foo.cc foo.h

There are some limitations and differences:

- Extended globs are supported only when Oil is built with GNU libc.
  - GNU libc has the `FNM_EXTMATCH` extension to `fnmatch()`.  Unlike bash and
    mksh, Oil doesn't implement its own extended glob matcher.
- They're more **static**, like in `mksh`.  When an extended glob appears in a
  word, we evaluate the word, match filenames, and **skip** the rest of the
  word evaluation pipeline.  This means:
  - Automatic word splitting is skipped in something like
    `$unquoted/@(*.cc|h)`.
  - You can't use arrays like `"$@"` and extended globs in the same word, e.g.
    `"$@"_*.@(cc|h)`.  This is usually nonsensical anyway.
- OSH only accepts them in **contexts** that make sense.
  - For example, `echo foo > @(cc|h)` is a runtime error in OSH, but other
    shells will write a file literally named `@(cc|h)`.
  - OSH doesn't accept `${undef:-@(cc)}`.  But it does accept `${x%@(cc)}`,
    since string strip operators like `%` accept a glob.
- Extended globbing is always on in OSH, regardless of `shopt -s extglob`.
  - Trivia: `bash` can't parse some extended globs unless `extglob` is on.  But
    it parses others when it's off.
- Extended globs can't be used in the `PATTERN` in `${x//PATTERN/replace}`.
  This is because we only translate normal (non-extended) globs to regexes (in
  order to get the position information necessary for string replacement).
- They're not supported when `shopt --set simple_word_eval` (Oil word
  evaluation).
  - For similar reasons, they're also not supported in assignment builtins.
    (This is a good thing!)
