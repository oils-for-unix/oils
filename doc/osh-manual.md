OSH Reference Manual
--------------------

NOTE: This Document is in Progress.

## Parsing OSH vs. sh/bash

(NOTE: This section should encompass all the failures from the [wild tests](http://oilshell.org/cross-ref.html?tag=wild-test#wild-test).)

OSH is meant to run all POSIX shell programs and almost all bash
programs.  But it's also designed to be more strict -- i.e. it's [statically
parsed](http://www.oilshell.org/blog/2016/10/22.html) rather than dynamically
parsed.

Here is a list of differences from bash:

(1) **Array indexes that are strings should be quoted** (with either single or
double quotes).

NO:

    "${SETUP_STATE[$err.cmd]}"

YES:

    "${SETUP_STATE["$err.cmd"]}"

The period causes an ambiguity with respect to regular arrays vs. associative
arrays.  See [Parsing Bash is Undecidable](http://www.oilshell.org/blog/2016/10/20.html).


(2) **Assignments can't have redirects.**

NO:

    x=abc >out.txt
    x=${y} >out.txt
    x=$((1 + 2)) >out.txt

    # This is the only one that makes sense (can result in a non-empty file),
    # but is still disallowed.
    x=$(echo hi) >out.txt

YES:

    x=$(echo hi >out.txt)


(3) **Variable names must be static** -- they can't be variables themselves.

NO:

    declare "$1"=abc

YES:

    declare x=abc


NOTE: It would be possible to allow this.  However in the Oil language, the
two constructs will have different syntax.  For example, `x = 'abc'` vs.
`setvar($1, 'abc')`.

(4) **Disambiguating Arith Sub vs. Command Sub+Subshell**

NO:

    $((cd / && ls))

YES:

    $( (cd / && ls) )   # This is valid but usually doesn't make sense.
                          # Because () means subshell, not grouping.
    $({ cd / && ls; })  # {} means grouping.  Note trailing ;
    $(cd / && ls)

Unlike bash, `$((` is always starts an arith sub.  `$( (echo hi) )` is a
subshell inside a command sub.  (This construct should be written `({ echo
hi;})` anyway.

(5) **Disambiguating Extended Glob vs. Negation of Expression**

- `[[ !(a == a) ]]` is always an extended glob.  
- `[[ ! (a == a) ]]` is the negation of an equality test.
  - In bash the rules are much more complicated, and depend on `shopt -s
    extglob`.  That flag is a no-op in OSH.  OSH avoids dynamic parsing, while
    bash does it in many places.

(6) **Here Doc Terminators Must Be On Their Own Line**

NO:

    a=$(cat <<EOF
    abc
    EOF)

    a=$(cat <<EOF
    abc
    EOF  # not a comment, read as here doc delimiter
    )

YES:

    a=$(cat <<EOF
    abc
    EOF
    )  # newline

Just like `EOF]` will not end the here doc, `EOF)` doesn't end it either.  It
must be on its own line.

## set builtin

### errexit

It largely follows the logic of bash.  Any non-zero exit code causes a fatal
error, except in:
 
  - the condition part of if / while / until
  - a command/pipeline prefixed by !
  - Every clause in || and && except the last

However, we fix two bugs with bash's behavior:

  - failure in $() should be fatal, not ignored.  OSH behaves like dash and
    mksh, not bash.
  - failure in local foo=... should propagate.  
    OSH diverges because this is arguably a bug in all shells -- `local` is
    treated as a separate command, which means `local foo=bar` behaves
    differently than than `foo=bar`.

Here is another difference:

  - If 'set -o errexit' is active, and then we disable it (inside
    if/while/until condition, !, && ||), and the user tries to 'set +o
    errexit', back, then this is a fatal error.  Other shells delay setting
    back until after the whole construct.

Very good articles on bash errexit:

  - http://mywiki.wooledge.org/BashFAQ/105
  - http://fvue.nl/wiki/Bash:_Error_handling

## Unicode

Encoding of programs should be utf-8.

But those programs can manipulate data in ANY encoding?

    echo $'[\u03bc]'  # C-escaped string

vs literal unicode vs. `echo -e`.  `$''` is preferred because it's statically
parsed.

List of operations that are Unicode-aware:

- ${#s} -- number of characters in a string
- slice: ${s:0:1}
- any operations that uses glob, which has '.' and [[:alpha:]] expressions
  - case
  - [[ $x == . ]]
  - ${s/./x}
  - ${s#.}  # remove one character
- sorting [[ $a < $b ]] -- should use current locale?  I guess that is like the
  'sort' command.
- prompt string has time, which is locale-specific.


