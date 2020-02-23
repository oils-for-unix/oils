---
in_progress: yes
---

Oil Word Language
=================

This document describes Oil's "word" language.  A word is an expression like
`$x`, `"hello $name"`, or `{build,test}/*.py`.  It evaluates to a string or an
array of strings.

Generally speaking, Oil behaves like a simpler version of POSIX shell / bash.
Sophisticated users can read [Simple Word Evaluation](simple-word-eval.html)
for a comparison.

This document mostly describes the differences.

<div id="toc">
</div>

## Sigils

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
var myarray = @(1 2 3)
```


## Inline function Calls

### That Return Strings

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

### That Return Arrays

```
cc -o foo -- @arrayfunc(x, y)

@split(mystr, '/')  # split on a delimiter
```

```
@array
```


## Joining

Shell has these odd "joining" semantics, which are supported in Oil but
generally discouraged:

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


## Oil Discourages Context-Sensitive Evaluation

The three contexts where splitting and globbing apply are the ones where a
**sequence** of words is evaluated (`EvalWordSequence`):

1. [Command]($help:simple-command): `echo $x foo`
2. [For loop]($help:for): `for i in $x foo; do ...`
3. [Array Literals]($help:array): `a=($x foo)` and `var a = @($x foo)` ([oil-array]($help))

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



## Design Note

This is the same discussion as `$f(x) vs `$(f(x))` on the [inline function calls thread](https://oilshell.zulipchat.com/#narrow/stream/121540-oil-discuss/topic/Inline.20function.20calls.20implemented).

We only want to interpolate **vars** and **functions**.  Arbitrary expressions aren't necessary.

In summary:

- `echo foo=$x` interpolates a variable into a unquoted word
- `echo foo=$f(x)` interpolates a call returning a string into an unquoted word
- `echo "foo=$[x] 1 2 3"` interpolates a variable into a double quoted string
- `echo "foo=${x} 1 2 3"` -- older, same
- `echo "foo=$[f(x)] 1 2 3"` interpolates a call returning a string into a
  double quoted string

OK I'm pretty happy with this explanation!    Shell is messy but Oil is bringing some order to it :)


---

And then for completeness we also have:

- `echo @x`  interpolates an array into a command
- `echo @f(x)` interpolates a function returning an array into a command

## Unimplemented

`${x|html}`

`${x %.3f}`

## Notes

### Shell Usage Tip: Use Only `"$@"`

This applies to all shells, not just Oil.

There's no reason to use anything but `"$@"`.  All the other forms like `$*`
can be disallowed, because if you want to join to a string, you can just write:

```
joined_str="$@"
```

The same advice applies to arrays for shells that have it.  You can always use
`"${myarray[@]}"`; you never need to use `${myarray[*]}` or any other form.

Related: [Thirteen Incorrect Ways and Two Awkward Ways to Use Arrays](http://www.oilshell.org/blog/2016/11/06.html)

### Oil vs. Bash Array Literals

Oil has a new array syntax, but it also supports the bash-compatible syntax:

```
local myarray=(one two *.py)  # bash

var myarray = @(one two *.py)  # Oil style
```

