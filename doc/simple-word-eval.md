---
in_progress: yes
---

Simple Word Evaluation in Unix Shell
====================================

<!-- override web/language.css because there's too much bold -->
<style>
.sh-command {
  font-weight: normal;
}
</style>

This document describes Oil's word evaluation semantics (`shopt -s
simple_word_eval`) for experienced shell users.  It may be useful to
implementers who want to adopt this behavior in another shell.

The main idea is that Oil behaves like a traditional programming language:

1. It's **parsed** from start to end [in a single pass][parsing-shell]:
2. It's **evaluated** in a single step too.  Data isn't re-parsed and
   re-evaluated as code.


[parsing-shell]: https://www.oilshell.org/blog/2019/02/07.html

[posix-spec]: https://pubs.opengroup.org/onlinepubs/009695399/utilities/xcu_chap02.html#tag_02_06


<div id="toc">
</div>

## An Analogy

In Oil, "word expressions" like

    'abc'$x${y:-${z//pat/replace}}"$(echo hi)$((a[i] * 3))"
    
are parsed and evaluated in a straightforward way, like this arithmetic
expression when `x` is `2`:

    1 + x/2 + x*3 => 8

In contrast, in shell, such code is "expanded" in multiple stages, like:

    1 + "x/2 + \"x*3\"" => 8

Programmers used to languages like C, Python, and JavaScript are surprised by
this, which leads to incorrect programs.

That is, the **defaults are wrong**.  There's essentially a silent `eval`, and
you need quoting to inhibit it.  It can cause security problems due to
confusing code and data (links below).

So in Oil, you can opt out of the multiple "word expansion" stages described in
the [POSIX shell spec][posix-spec].  There's only **one stage**: evaluation.

## Design Goals

The new semantics should be easily adoptable by existing shell scripts.

- Importantly, `bin/osh` is POSIX-compatible and runs real [bash]($xref)
  scripts.  You can gradually opt into **stricter and saner** behavior with
  `shopt` options (or by running `bin/oil`).  The most important one is `shopt
  -s simple_word_eval`, and the others are listed below.
- Even after opting in, the new syntax shouldn't break many scripts.  If it
  does break, the change to fix it should be small.  For example, `echo @foo`
  is not too common, and it can be made bash-compatible by quoting it: `echo
  '@foo'`.

<!--
It's technically incompatible but I think it will break very few scripts.

-->

## Examples

In the following examples, the [argv][] command prints the `argv` array it
receives in a readable format:

```sh-prompt
$ argv one "two three"
['one', 'two three']
```

[argv]: $oil-src:spec/bin/argv.py

### No Implicit Splitting, Dynamic Globbing, or Empty Elision

Oil, these constructs in the word sublanguage always evaluate to **one
argument**:

That is, quotes aren't necessary to avoid word splitting, "empty elision", or
dynamic globbing:

```sh-prompt
oil$ var pic = 'my pic.jpg'  # filename with spaces
oil$ var empty = ''
oil$ var pat = '*.py'        # pattern stored in a string

oil$ argv ${pic} $empty $pat $(cat foo.txt) $((1 + 2))
['my pic.jpg', '', '*.py', 'contents of foo.txt', '3']
```

Shell:

```sh-prompt
sh$ pic='my pic.jpg'  # filename with spaces
sh$ empty=
sh$ pat='*.py'        # pattern stored in a string

sh$ argv ${pic} $empty $pat $(cat foo.txt) $((1 + 2))
['my', 'pic.jpg', 'a.py', 'b.py', 'contents', 'of', 'foo.txt', '3']
```

To get the desired behavior, you'd have to quote everything:

```sh-prompt
sh$ argv "${pic}" "$empty" "$pat", "$(cat foo.txt)" "$((1 + 2))"
['my pic.jpg', '', '*.py', 'contents of foo.txt', '3']
```

<!--
com-sub
var-sub
arith-sub
not used: tilde-sub
-->

### Splicing, Static Globbing, and Brace Expansion

The constructs in the last section evaluate to a **single argument**.  In
contrast, these three constructs evaluate to **0 to N arguments**:

1. Splicing an array: `"$@"` and `"${myarray[@]}"`
2. Static globbing: `echo *.py`
3. Brace expansion: `{alice,bob}@example.com`

In Oil, `shopt -s parse_at` enables these shortcuts for splicing:

- `@myarray` for `"${myarray[@]}"`
- `@ARGV` for `"$@"`

Example:

```sh-prompt
oil$ var myarray = @('a b' c)  # array with 2 elements
oil$ set -- 'd e' f            # 2 arguments

oil$ argv @myarray @ARGV *.py {ian,jack}@sh.com
['a b', 'c', 'd e', 'f', 'g.py', 'h.py', 'ian@sh.com', 'jack@sh.com']
```

is just like:


```sh-prompt
bash$ myarray=('a b' c)
bash$ set -- 'd e' f

bash$ argv "${myarray[@]}" "$@" *.py {alice,bob}@sh.com
['a b', 'c', 'd e', 'f', 'g.py', 'h.py', 'ian@sh.com', 'jack@sh.com']
```

These globs are **static** because they occur in the program text, not in user
data (e.g. an environment variable, a file, etc.)

<!--
Key differences is **quoting** and the `@` **splice** operator.

The "arity" of the command is more static than dynamic, because there's no
splitting.  Splitting can be done with `@split(mystr)` and dynamic globbing
could be `@glob(myglobstr)` (not implemented)
-->

<!--
help topics:

- braces
- glob
- splice

More:
- inline-call

-->

### Joining

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

## Opt In to the Old Behavior With Explicit Expressions

Oil can express everything that shell can.

- Split with `@split(mystr)`
- Glob with `@glob(mypat)` (not implemented)
- Elide an empty string by converting it to an array of length 0 or 1,
  then splice that array into a command.  See the [example in the last
  section](#elision-example).


## More Word Evaluation Issues

### More `shopt` Options

- [nullglob]($help) - Globs matching nothing don't evaluate to code.
- [dashglob]($help) is *disabled* when Oil is enabled.  Files that begin with
  `-` aren't returned.

Strict options cause fatal errors:

- [strict_tilde]($help) - Failed tilde expansions don't evaluate to code.
- [strict_word_eval]($help) - Invalid slices and invalid UTF-8 aren't ignored.

### Arithmetic Is Statically Parsed

This is an intentional incompatibility described in the [Known
Differences](known-differences.html#static-parsing) doc.

### Oil Discourages Context-Sensitive Evaluation

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

<!--
TODO: also allow

var parts = @split(x) 
var python = @glob('*.py')
-->

## Summary

Oil word evaluation is enabled with `shopt -s simple_word_eval`, and proceeds
in a single step.

There's no implicit splitting, globbing, or elision of empty words.  You can
opt into those behaviors with explicit expressions like `@split(mystr)`, which
evaluates to an array.

Variable, command, and arithmetic substitutions predictably evaluate to a
**single argument**, regardless of whether they're empty or have spaces.

Oil supports shell features that evaluate to **0 to N arguments**: splicing,
globbing, and brace expansion.

There are other options that "clean up" word evaluation.  All options are
designed to be gradually adopted by other shells, shell scripts, and eventually
POSIX.

## Links

- [The Simplest Explanation of
  Oil](http://www.oilshell.org/blog/2020/01/simplest-explanation.html).  Some
  color on the rest of the language.
- [Known Differences Between OSH and Other Shells](known-differences.html).
  Mentioned above: Arithmetic is statically parsed.  Arrays and strings are
  kept separate.
- [OSH Word Evaluation Algorithm][wiki-word-eval] on the Wiki.  Informally
  describes the data structures, and describes legacy constructs.
- [Security implications of forgetting to quote a variable in bash/POSIX
  shells](https://unix.stackexchange.com/questions/171346/security-implications-of-forgetting-to-quote-a-variable-in-bash-posix-shells)
  by Stéphane Chazelas.  Describes the "implicit split+glob" operator, which
  Oil word evaluation removes.
  - This is essentially the same [security
    issue](http://www.oilshell.org/blog/2019/01/18.html#a-story-about-a-30-year-old-security-problem)
    I rediscovered in January 2019.  It appears in all [ksh]($xref)-derived shells, and some shells
    recently patched it.  I wasn't able to exploit in a "real" context;
    otherwise I'd have made more noise about it.

[wiki-word-eval]: https://github.com/oilshell/oil/wiki/OSH-Word-Evaluation-Algorithm


## Notes


### Tip: View the Syntax Tree With `-n`

This gives insight into [how Oil parses shell][parsing-shell]:

```sh-prompt
$ osh -n -c 'echo ${x:-default}$(( 1 + 2 ))'
(C {<echo>} 
  {
    (braced_var_sub
      token: <Id.VSub_Name x>
      suffix_op: (suffix_op.Unary op_id:Id.VTest_ColonHyphen arg_word:{<default>})
    ) 
    (word_part.ArithSub
      anode: 
        (arith_expr.Binary
          op_id: Id.Arith_Plus
          left: (arith_expr.ArithWord w:{<Id.Lit_Digits 1>})
          right: (arith_expr.ArithWord w:{<Id.Lit_Digits 2>})
        )
    )
  }
)
```

You can pass `--ast-format text` for more details.

Evaluation of the syntax tree is a single step.

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

### Elision Example

The elision of empty strings from commands is verbose but we could simplify it
with a builtin function if necessary:

```sh-prompt
var x = ''         # empty in this case
var tmp = @()
if (x) {           # test if string is non-empty
  append :tmp $x   # appends 'x' to the array variable 'tmp'
}

argv a @tmp b

# OUTPUT:
# ['a', 'b']
```

When it's not empty:

```sh-prompt
var x = 'X'

...

argv a @tmp b

# OUTPUT:
# ['a', 'X', 'b']
```
