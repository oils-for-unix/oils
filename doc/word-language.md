---
in_progress: yes
---

Word Language
=============

Recall that Oil is composed of three interleaved languages: words, commands,
and expressions.

For now, this document describes things that are **not** covered in:

- [A Tour of the Oil Language](oil-language-tour.html)
- The `#word-lang` section of [OSH Help
  Topics](osh-help-topics.html#word-lang)
- The `#word-lang` section of [Oil Help
  Topics](oil-help-topics.html#word-lang)

That is, it has both trivia or high-level concepts that aren't covered
elsewhere.

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
3. [Array Literals]($help:array): `a=($x foo)` and `var a = %($x foo)` ([oil-array]($help))

### Oil vs. Bash Array Literals

Oil has a new array syntax, but it also supports the bash-compatible syntax:

```
local myarray=(one two *.py)  # bash

var myarray = %(one two *.py)  # Oil style
```

### Oil Discourages Context-Sensitive Evaluation

Shell also has contexts where it evaluates words to a **single string**, rather
than a sequence, like:

```sh
# RHS of Assignemnt
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

- All subsitutions: var, command, arith
  - TODO: Do we have `$[a[x+1]]` as an expression substitution?
  - Or `$[ /pat+ /]`?
  - I don't think so.

- Inline function calls, an Oil extension: `$join(myarray)`

(C-style strings like `$'\n'` use `$`, but that's more of a bash anachronism.
In Oil, `c'\n'` is preferred.

### `@` Means "Returns An Array of Strings"

Enabled with `shopt -s parse_at`.

Examples:

- `@myarray`
- `@arrayfunc(x, y)`

These are both Oil extensions.

The array literal syntax also uses a `@`:

```
var myarray = %(1 2 3)
```

## Inline Function Calls

This feature is purely syntactic sugar.  Instead of:

    write $strfunc(x) @arrayfunc(y)

You can always refactor to:

    var mystr = strfunc(x)
    var myarray = arrayfunc(y)

    write $mystr @myarray

### That Return Strings (Function Sub)

Examples:

```
echo $join(myarray, '/')
echo $len(mystr)  # len returns an int, but it's automatically converted to a string
echo foo=$len(mystr)  # also works
```

Note that inline function calls can't be placed in double quoted strings:
`"__$len(s)__"` 

You can either extract a variable:

```
var x = len(s)
echo "__$x__"
```

or use an expression substitution ([expr-sub]($help)):

```
echo $[len(x)]
```

`$[]` is for Oil expressions, while `${}` is shell.

This is documented in [warts](warts.html).

### That Return Arrays (Function Splice)

    cc -o foo -- @arrayfunc(x, y)

    echo @split(mystr, '/')  # split on a delimiter

## Implicit Joining

Shell has odd "joining" semantics, which are supported in Oil but generally
discouraged:

    set -- 'a b' 'c d'
    argv.py X"$@"X
    ['Xa', 'b', 'c', 'dX']

In Oil, the RHS of an assignment is an expression, and joining only occurs
within double quotes:

    # Oil
    var joined = $x$y    # parse error
    var joined = "$x$y"  # OK

    # shell
    joined=$x$y          # OK
    joined="$x$y"        # OK

## Notes

### On The Design of Substitution

This is the same discussion as `$f(x) vs `$(f(x))` on the [inline function
calls
thread](https://oilshell.zulipchat.com/#narrow/stream/121540-oil-discuss/topic/Inline.20function.20calls.20implemented).

We only want to interpolate **vars** and **functions**.  Arbitrary expressions
aren't necessary.

In summary:

- `echo foo=$x` interpolates a variable into a unquoted word
- `echo foo=$f(x)` interpolates a call returning a string into an unquoted word
- `echo "foo=$[x] 1 2 3"` interpolates a variable into a double quoted string
- `echo "foo=${x} 1 2 3"` -- older, same
- `echo "foo=$[f(x)] 1 2 3"` interpolates a call returning a string into a
  double quoted string

---

And then for completeness we also have:

- `echo @x`  interpolates an array into a command
- `echo @f(x)` interpolates a function returning an array into a command

