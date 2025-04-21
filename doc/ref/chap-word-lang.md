---
title: Word Language (Oils Reference)
all_docs_url: ..
body_css_class: width40
default_highlighter: oils-sh
preserve_anchor_case: yes
---

<div class="doc-ref-header">

[Oils Reference](index.html) &mdash;
Chapter **Word Language**

</div>

This chapter describes the word language for OSH and YSH.  Words evaluate to
strings, or arrays of strings.

<span class="in-progress">(in progress)</span>

<div id="dense-toc">
</div>

<h2 id="expression">Expressions to Words</h2>

### expr-sub

Try to turn an expression into a string.  Examples:

    $ echo $[3 * 2]
    6

    $ var s = 'foo'
    $ echo $[s[1:]]
    oo

Some types can't be stringified, like Dict and List:

    $ var d = {k: 42}

    $ echo $[d]
    fatal: expected Null, Bool, Int, Float, Eggex

You can explicitly use `toJson8` or `toJson()`:

    $ echo $[toJson8(d)]
    {"k":42}

(This is similar to `json write (d)`)

### expr-splice

Splicing puts the elements of a `List` into a string array context:

    $ var foods = ['ale', 'bean', 'corn']
    $ echo pizza @[foods[1:]] worm
    pizza bean corn worm

This syntax is enabled by `shopt --set` [parse_at][], which is part of YSH.

[parse_at]: chap-option.html#ysh:upgrade

### var-splice

    $ var foods = ['ale', 'bean', 'corn']
    echo @foods

This syntax is enabled by `shopt --set` [parse_at][], which is part of YSH.


<h2 id="formatting">Formatting Typed Data as Strings</h2>

### ysh-printf

Not done.

    echo ${x %.3f}

### ysh-format

Not done.

    echo ${x|html}

## Quotes

### osh-string

- Single quotes
- Double Quotes
- C-style strings: `$'\n'`

TODO: elaborate

### ysh-string

YSH strings in the word language are the same as in the expression language.

See [ysh-string in chap-expr-lang](chap-expr-lang.html#ysh-string).

### triple-quoted

Triple-quoted in the word language are the same as in the expression language.

See [triple-quoted in chap-expr-lang](chap-expr-lang.html#triple-quoted).

### tagged-str

Not done.

## Substitutions

### command-sub

Executes a command and captures its stdout.

If stdout has a trailing newline, it's removed:

    $ hostname
    example.com

    $ echo "/tmp/$(hostname)"
    /tmp/example.com

If stdout has any NUL bytes, they are removed (regardless of position).

Related: [captureStdout()](chap-type-method.html#captureStdout)

### ysh-command-sub

YSH also has spliced command subs, enabled by `shopt --set parse_at`.  The
result is a **List** of strings, rather than a single string.

    $ write -- @(echo foo; echo 'with spaces')
    foo
    with-spaces

The command's stdout parsed as the "J8 Lines" format, where each line is
either:

1. An unquoted string, which must be valid UTF-8.  Whitespace is allowed, but
   not other ASCII control chars.
2. A quoted J8 string (JSON style `""` or J8-style `b'' u'' ''`)
3. An **ignored** empty line

See [J8 Notation](../j8-notation.html) for more details.

### var-sub

Evaluates to the value of a variable:

    $ x=X
    $ echo $x ${x}
    X X

### arith-sub

Shell has C-style arithmetic:

    $ echo $(( 1 + 2*3 ))
    7

### tilde-sub

Used as a shortcut for a user's home directory:

    ~/src     # my home dir
    ~bob/src  # user bob's home dir

### proc-sub

Open stdout as a named file in `/dev/fd`, which can be passed to a command:

    diff <(sort L.txt) <(sort R.txt)

Open stdin as a named file in `/dev/fd`:

    seq 3 | tee >(sleep 1; tac)


## Var Ops

There are three types of braced variable expansions:

    ${!name*} or ${!name@}
    ${!name[@]} or ${!name[*]}
    ${ops var ops}

`name` needs to be a valid identifier.  If the expansion matches the first
form, the variable names starting with `name` are generated.  Otherwise, if the
expansion matches the second form, the keys of the indexed or associative array
named `name` are generated.  When the expansion does not much either the first
or second forms, it is interpreted as the third form of the variable name
surrounded by operators.


### op-bracket

The value within brackets is called an "index", and retrieves a value from an
array:

    ${A[i+1]}
    ${A['key']}

If `A` is an indexed array, the index is interpreted as an arithmetic
expression.  Arithmetic evaluation is performed, and the value at that numeric
offset is retrieved.

If `A` is an associative array, the index is interpreted as a string.  The
value associated with that string is retrieved.

If `A` is a string, it's treated as an indexed array with a single element,
i.e. so that `${A[0]}` is `${A}`.

---

    ${A[*]}
    ${A[@]}

The index expressions `[*]` and `[@]` are special cases.  Both generate a word
list of all elements in `a`.

When the variable substitution is **unquoted**, there's no difference between
`[*]` and `[@]`:

    $ A=(1 2 3)
    $ printf '<%s>\n' ${A[*]}
    <1>
    <2>
    <3>

    $ printf '<%s>\n' ${A[@]}
    <1>
    <2>
    <3>

When double-quoted, the `[*]` form joins the elements by the first character of
`IFS`:

    $ IFS=x
    $ printf '<%s>\n' "${A[*]}"
    <1x2x3>

When double-quoted, the `[@]` form generates a word list by splitting the word
at the boundary of every element in `A`:

    $ printf '<%s>\n' "-${A[@]}-"
    <-1>
    <2>
    <3->

If the container `A` has no elements, and the variable substitution has no
other parts, `[@]` evaluates to an empty word list:

    $ empty=()
    $ set -- "${empty[@]}"
    $ echo $#
    0

---

These rules for `[*]` and `[@]` also apply to:

- `$*` and `$@`
- `${!name*}` and `${!name@}`
- `${!name[*]}` and `${!name[@]}`, etc.

<!--
Note: OSH currently joins the values by `IFS` even for unquoted `$*` and
performs word splitting afterward.  This is different from the POSIX standard.
-->

### op-indirect

The indirection operator `!` is a prefix operator, and it interprets the
received string as a variable name `name`, an array element `name[key]`, or an
arrat list `name[@]` / `name[*]` and reads its values.

    $ a=1234
    $ v=a
    $ echo $v
    a
    $ echo ${!v}
    1234

### op-test

Shell has boolean operations within `${}`.  I use `:-` most frequently:

    x=${1:-default}
    osh=${OSH:-default}

This idiom is also useful:

    : ${LIB_OSH=stdlib/osh}

---

There are test operators with colons, and without:

    ${x-default}
    ${x:-default}

    ${x=default}
    ${x:=default}

    ${x+other}
    ${x:+other}

    ${x?error}
    ${x:?error}

**Without** the colon, the shell checks whether a value is **defined**.  In the
case of a word list, e.g. generated by `$*` or `$@`, it tests whether there is
at least one element.

**With** the colon, the shell checks whether the value is **non-empty** (is not
the empty string).  In the case of a word list, the test is performed after
joining the elements by a space.

Elements are joined by the first character of `IFS` only with double-quoted
`"${*:-}"`. 

In contrast, `${*:-}`, `${@:-}`, and `"${@:-}"` are joined by a space.  This is
because the joining of `"$*"` by `IFS` is performed earlier than the joining by
space for the test.

<!--
Note: OSH currently joins the values by `IFS` even for unquoted `$*`.  This is
different from Bash.
-->

### op-strip

Remove prefixes or suffixes from strings:

    echo ${y#prefix}
    echo ${y##'prefix'}

    echo ${y%suffix}
    echo ${y%%'suffix'}

The prefix and suffix can be glob patterns, but this usage is discouraged
because it may be slow.

### op-patsub

Replace a substring or pattern.

The character after the first `/` can be `/` to replace all occurrences:

    $ x=food

    $ echo ${x//o/--}      # replace 1 o with 2 --
    f----d

It can be `#` or `%` for an anchored replacement:

    $ echo ${x/#f/--}      # left anchored f
    --ood

    $ echo ${x/%d/--}      # right anchored d
    foo--

The pattern can also be a glob:

    $ echo ${x//[a-z]/o}   # replace 1 char with o
    oooo

    $ echo ${x//[a-z]+/o}  # replace multiple chars
    o

### op-slice

    echo ${a[@]:1:2}
    echo ${@:1:2}

### op-format

${x@P} evaluates x as a prompt string, i.e. the string that would be printed if
PS1=$x.

---

`${x@Q}` quotes the value of `x`, if necessary, so that it can be evaluated as
a shell word.

    $ x='<'
    $ echo "value = $x, quoted = ${x@Q}."
    value = <, quoted = '<'.

    $ x=a
    $ echo "value = $x, quoted = ${x@Q}."
    value = a, quoted = a.

In the second case, the string `a` doesn't need to be quoted.

---

Format operations like `@Q` generally treat **empty** variables differently
than **unset** variables.

That is, `${empty@Q}` is the string `''`, while `${unset@Q}` is an empty
string:

    $ x=''
    $ echo "value = $x, quoted = ${x@Q}."
    value = , quoted = ''.

    $ unset -v x
    $ echo "value = $x, quoted = ${x@Q}."
    value = , quoted = .

---

`${x@a}` returns characters that represent the attributes of the `${x}`, or
more precisely, the *h-value* of `${x}`.

Definitions:

- *h-value* is the variable (or the object that the variable directly points)
  from which the result of `${x}` would originally come.
- *r-value* is the value of the expansion of `${x}`

For example, with `arr=(1 2 3)`:

<style>
table { 
  width: 100%;
  margin-left: 2em;  /* matches p text in manual.css */
}
thead {
  text-align: left;
}
</style>

<table>

- thead
  - Reference
  - Expression
  - H-value
  - R-value
  - Flags returned
- tr
  - <!-- empty -->
  - `${arr[0]@a}` or <br/> `${arr@a}`
  - array<br/> `(1 2 3)`
  - string<br/> `1`
  - `a`
- tr
  - <!-- empty -->
  - `${arr[@]@a}`
  - array<br/> `(1 2 3)`
  - array<br/> `(1 2 3)`
  - `a a a`
- tr
  - `ref=arr` or `ref=arr[0]`
  - `${!ref@a}`
  - array<br/> `(1 2 3)`
  - string<br/> `1`
  - `a`
  - <!-- empty -->
- tr
  - `ref=arr[@]`
  - `${!ref@a}`
  - array<br/> `(1 2 3)`
  - array<br/> `(1 2 3)`
  - `a a a`

</table>

When `${x}` would result in a word list, `${x@a}` returns a word list
containing the attributes of the *h-value* of each word.

---

These characters may be returned:

<table>

- thead
  - Character
  - Where `${x}` would be obtained
- tr
  - `a`
  - indexed array
- tr
  - `A`
  - associative array
- tr
  - `r`
  - readonly container
- tr
  - `x`
  - exported variable
- tr
  - `n`
  - name reference (OSH extension)

</table>
