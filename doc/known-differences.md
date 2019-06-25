Known Differences Between OSH and Other Shells
----------------------------------------------

OSH is meant to run all POSIX shell programs and almost all bash
programs.  But it's also designed to be more strict -- i.e. it's [statically
parsed](http://www.oilshell.org/blog/2016/10/22.html) rather than dynamically
parsed.

Here is a list of differences from sh/bash:

## Parsing

(NOTE: This section should encompass all the failures from the [wild
tests](http://oilshell.org/cross-ref.html?tag=wild-test#wild-test) and spec
tests.)


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

<!-- 
TODO: Add these

- dynamic parsing of `$(( $a $op $b ))`.  OSH requires an explicit eval.
- new one: `` as comments in sandstorm
  # This relates to comments being EOL or not
-->

(7) **Ambiguous Character Classes in Globs**

In short, don't use the ambiguous syntax `[[]` or `[]]` for a character class
consisting of a single left bracket or right bracket character.

Instead, use `[\[]` and `[\]]`.

TODO: Explanation.

(8) **Backslashes Within Backticks**

In rare cases, OSH processes backslashes within backticks differently than
other shells.  However there are always **two workarounds** that are compatible
with every shell:

1. Use `$(echo \")` instead of `` `echo \"` ``.  There's no downside to using
   `$()` **everywhere** -- it works in all shells and has no special quoting
   behavior.  Backticks are a "legacy" syntax precisely because of their
   unintuitive quoting rules (the bash project agrees).
2. Use `` `echo \\"` `` rather than `` `echo \"` ``.  Although there are
   different number of backslashes, these two statements **evaluate to the same
   thing** in all shells.
   - OSH accepts only the former.  The latter is interpreted as the start of a
     quoted string, and results in a syntax error.

Notes:

- This is tested in [spec/command-sub][].  (Case #25 fails for OSH, and all
  shells start to disagree on case #26.)
- The basic reason for the disagreement is that OSH doesn't have special cases
  for a particular number of backslashes.  The rules are consistent for any
    level of quoting, although incompatible in this edge case.

[spec/command-sub]: http://www.oilshell.org/release/0.6.pre22/test/spec.wwz/command-sub.html


(9) **Evaluation model of aliases**

It's largly compatible but differs with things like:

    alias left='{'
    left echo hi; }

    (cases #33-#34 in spec/alias)

or

    alias a=
    a (( var = 0 ))

(10) **break, continue, and return are control flow keywords, not builtins**

This means that they are not "dynamic":

    b=break
    while true; do
      $b  # in OSH, this tries to look up a command named 'break' and fails to
    done

    (see case in spec/loop)

(This could be changed, but I wanted control flow to be analyzable ...)

(11) **Brace Expansion is All Or Nothing**

Expansions like `{a,b}{` and `{a,b}{1...3}` arguably have bad syntax (note 3
dots instead of 2 in the second case).

bash will still do some brace expansion here, giving you `a{ b{`, etc.

OSH considers it a syntax error and aborts all brace expansion, giving you the
same thing back: `{a,b}{`.

The better way to write these examples is `{a,b}\{` and `{a,b}\{1...3\}`.


(12) **Tilde Expansion and Brace Expansion Don't Interact**

In bash, something like `{~bob,~jane}/src` will expand to home dirs for both
people.  OSH doesn't do this because it separates parsing and evaluation.  By
the time tilde expansion happens, we haven't *evaluated* the brace expansion.
We've only *parsed* it.

(mksh agrees with OSH, but zsh agrees with bash.)

## Runtime

### set -o errexit

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

### Completion

The OSH completion API is heavily based on the bash completion API, and
designed to be largely compatible.

See [doc/osh-manual.md][] for details.

[doc/osh-manual.md]: ./osh-manual.md 

## Interactive

### History Substitution Language

The rules for history substitution like `!echo` are simpler.  There are no
special cases to avoid clashes with `${!indirect}` and so forth.  TODO: See the
history lexer.

## Links

- [Bash POSIX
  Mode](https://www.gnu.org/software/bash/manual/html_node/Bash-POSIX-Mode.html)
  -- interesting for comparison.

