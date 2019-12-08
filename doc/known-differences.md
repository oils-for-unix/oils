Known Differences Between OSH and Other Shells
==============================================

This document is for **sophisticated shell users**.

You're unlikely to encounter these incompatibilities in everyday shell usage.
If you do, there's almost always a **simple workaround**, like adding a space
or a backslash.

OSH is meant to run all POSIX shell programs, and most bash programs.

<!-- cmark.py expands this -->
<div id="toc">
</div>

<!-- 
TODO:

- `` as comments in sandstorm
  # This relates to comments being EOL or not

- Document when declare / local / readonly/ export are KEYWORDS, and when they
  are BUILTINS.

-->

## Numbers and Arithmetic

Roughly speaking, shells treat arithmetic like "macro processing", while OSH
treats it more like part of a programming language.

Despite these differences, OSH is very compatible with existing shell scripts.

Note that you can opt into more errors with `shopt -s strict_arith`.

### Static Parsing

Arithmetic is statically parsed, so expressions like `$(( 1 $op 2 ))` fail with
a parse error.  Use an explicit `eval` for these rare use cases.

### printf '%d' and other numeric formats require a valid integer

In other shells, `printf %d invalid_integer` prints `0` and a warning.  OSH
gives you a runtime error.

## Parsing Differences

This section describes differences related to [static
parsing](http://www.oilshell.org/blog/2016/10/22.html).  OSH avoids the
dynamic parsing of most shells.

(Note: This section should encompass all the failures from the [wild
tests](http://oilshell.org/cross-ref.html?tag=wild-test#wild-test) and [spec
tests](http://oilshell.org/cross-ref.html?tag=spec-test#spec-test).

### Strings vs. Bare words in array indices

Strings should be quoted inside array indices:

No:

    "${SETUP_STATE[$err.cmd]}"

Yes:

    "${SETUP_STATE["$err.cmd"]}"

When unquoted, the period causes an ambiguity with respect to regular arrays
vs. associative arrays.  See [Parsing Bash is
Undecidable](http://www.oilshell.org/blog/2016/10/20.html).


### Subshell in command sub

You can have a subshell in a command sub, but it usually doesn't make sense.

In OSH you need a space after `$(`.  The characters `$((` always start an
arith sub.

No:

    $((cd / && ls))

Yes:

    $( (cd / && ls) )   # Valid but usually doesn't make sense.
    $({ cd / && ls; })  # Use {} for grouping, not ().  Note trailing ;
    $(cd / && ls)       # Even better


### Extended glob vs. Negation of boolean expression

- `[[ !(a == a) ]]` is an extended glob.  
- `[[ ! (a == a) ]]` is the negation of an equality test.

In bash the rules are more complicated, and depend on `shopt -s extglob`.  The
`extglob` setting does nothing in OSH.

### Here doc terminators must be on their own line

Lines like `EOF]` or `EOF)` don't end here docs.  The delimiter must be on its
own line.

No:

    a=$(cat <<EOF
    abc
    EOF)

    a=$(cat <<EOF
    abc
    EOF  # this is not a comment; it makes the EOF delimiter invalid
    )

Yes:

    a=$(cat <<EOF
    abc
    EOF
    )  # this is actually a comment


### Spaces aren't allowed in LHS indices

Bash allows:

    a[1 + 2 * 3]=value

OSH only allows:

    a[1+2*3]=value

because it parses with limited lookahead.  The first line would result in the
execution of a command named `a[1`.

### break / continue / return are keywords, not builtins

This means that they aren't "dynamic":

    b=break
    while true; do
      $b  # doesn't break in OSH
    done

Static control flow will allow static analysis of shell scripts.

(Test cases are in [spec/loop][]).

### Oil Has More Builtins, Which Shadow External Commands

For example, `push` is a builtin in Oil, but not in `bash`.  Use `env push` or
`/path/to/push` if you want to run an external command.

(Note that a user-defined function `push` take priority over the builtin
`push`.

### Oil Has More Keywords, Which Shadow Builtins, Functions, and Commands

In contrast with builtins, **keywords** affect shell parsing.

For example, `func` is a keyword in Oil, but not in `bash`.  To run a command
named `func`, use `command func arg1`.

Note that all shells have extensions that cause this issue.  For example, `[[`
is a keyword in `bash` but not in POSIX shell.

## More Parsing Differences

These differences occur in subsequent stages of parsing, or in runtime parsing.

### Brace expansion is all or nothing

No:

    {a,b}{        # what does the second { mean?
    {a,b}{1...3}  # 3 dots instead of 2

Yes:

    {a,b}\{
    {a,b}\{1...3\}

bash will do a **partial expansion** in the former cases, giving you `a{ b{`
and `a{1...3} b{1...3}`.

OSH considers them syntax errors and aborts all brace expansion, giving you
the same thing back: `{a,b}{` and `{a,b}{1...3}`.


### Tilde expansion and Brace expansion don't interact

In bash, `{~bob,~jane}/src` will expand the home dirs of both people.  OSH
doesn't do this because it separates parsing and evaluation.  By the time tilde
expansion happens, we haven't *evaluated* the brace expansion.  We've only
*parsed* it.

(mksh agrees with OSH, but zsh agrees with bash.)

### Brackets should be escaped within character classes

Don't use ambiguous syntax for a character class consisting of a single bracket
character.

No:

    echo [[]
    echo []]

Yes:

    echo [\[]
    echo [\]]


The ambiguous syntax is allowed when we pass globs through to `libc`, but it's
good practice to be explicit.

### Double quotes within backticks

In rare cases, OSH processes backslashes within backticks differently than
other shells.  However there are **two workarounds** that are compatible with
every shell.

No:

    `echo \"`     # is this a literal quote, or does it start a string?

Yes:

    $(echo \")    # $() can always be used instead of ``.
                  # There's no downside to the more modern construct.
    `echo \\"`    # also valid, but $() is more readable


Notes:

- This is tested in [spec/command-sub][].  (Case #25 fails for OSH, and all
  shells start to disagree on case #26.)
- The reason for the disagreement is that OSH doesn't have special cases for a
  particular number of backslashes.  The rules are consistent for any level of
  quoting, although incompatible in this edge case.

## Differences at Runtime

### Alias Expansion

Almost all "real" aliases should work in OSH.  But these don't work:

    alias left='{'
    left echo hi; }

(cases #33-#34 in [spec/alias][])

or

    alias a=
    a (( var = 0 ))

Details on the OSH parsing model:

1. Your code is statically parsed into an abstract syntax tree, which contains
   many types of nodes.
2. `SimpleCommand` are the only ones that are further alias-expanded.

For example, these result in `SimpleCommand` nodes:

- `ls -l` 
- `read -n 1` (normally a builtin)
- `myfunc foo`

These don't:

- `x=42`
- `declare -r x=42`
- `break`, `continue`, `return`, `exit` &mdash; as explained above, these are
  keywords and not builtins.
- `{ echo one; echo two; }`
- `for`, `while`, `case`, functions, etc.

### Array References Must be Explicit

In bash, `$array` is equivalent to `${array[0]}`, which is very confusing
(especially when combined with `set -o nounset`).

No:

    array=(1 2 3)
    echo $array         # Runtime error in OSH

Yes:

    echo ${array[0]}    # explicitly choose the first element
    echo "${array[@]}"  # explicitly choose the whole array

NOTE: Setting `shopt -s strict-array` further reduces the confusion between
strings and arrays.  See [the manual](osh-manual.html) for details.

### Arrays aren't split inside ${}

Most shells split the entries of arrays like `"$@"` and `"${a[@]}"` here:

    echo ${undef:-"$@"}

In OSH, omit the quotes if you want splitting:

    echo ${undef:-$@}

I think OSH is more consistent, but it disagrees with other shells.

### Indexed and Associative Arrays are Distinct

OSH has bash-compatible arrays, which are created like this:

    local indexed=(foo bar)
    local -a indexed=(foo bar)            # -a is redundant
    echo ${indexed[1]}                    # bar

    local assoc=(['one']=1 ['two']=2)
    local -A assoc=(['one']=1 ['two']=2)  # -A is redundant
    echo ${assoc['one']}                  # 1

In bash, the distinction between the two is blurry, e.g. in cases like this:

    local -A x=(foo bar)                  # -A disagrees with literal
    local -a y=(['one']=1 ['two']=2)      # -a disagrees with literal

### Args to Assignment Builtins Aren't Split or Globbed

The assignment builtins are `export`, `readonly`, `local`, and
`declare`/`typeset`.

In bash, you can do unusual things with them:

    vars='a=b x=y'
    touch foo=bar.py spam=eggs.py

    declare $vars *.py       # assigns at least 4 variables
    echo $a       # b
    echo $x       # y
    echo $foo     # bar.py
    echo $spam    # eggs.py

In contrast, OSH disables splitting and globbing within assignment builtins.
This is more like the behavior of zsh.

On a related note, assignment builtins are both statically and dynamically
parsed:

- Statically: to avoid splitting `declare x=$y` when `$y` contains spaces.
- Dynamically: to handle expressions like `declare $1` where `$1` is `a=b`

### Completion

The OSH completion API is mostly compatible with the bash completion API,
except that it moves the **responsibility for quoting** out of plugins and onto
the shell itself.  Plugins should return candidates as `argv` entries, not
shell words.

See the [OSH manual][] for details.

[OSH manual]: osh-manual.html

## Interactive Features

### History Substitution Language

The rules for history substitution like `!echo` are simpler.  There are no
special cases to avoid clashes with `${!indirect}` and so forth.

TODO: Link to the history lexer.

## Links

- [OSH Spec Tests](../test/spec.wwz/) run shell snippets with OSH and other
  shells to compare their behavior.

External:

- This list may seem long, but compare the list of differences in [Bash POSIX
  Mode](https://www.gnu.org/software/bash/manual/html_node/Bash-POSIX-Mode.html).
  That page tells you what `set -o posix` does in bash.


[spec/command-sub]: ../test/spec.wwz/command-sub.html
[spec/loop]: ../test/spec.wwz/loop.html
[spec/alias]: ../test/spec.wwz/alias.html


