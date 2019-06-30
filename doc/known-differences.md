Known Differences Between OSH and Other Shells
----------------------------------------------

This document is for **sophisticated shell users**.

You're unlikely to encounter these incompatibilities in everyday shell usage.
If you do, there's almost always a **simple workaround**, like adding a space
or a backslash.

OSH is meant to run all POSIX shell programs and almost all bash programs.

<!-- cmark.py expands this -->
<div id="toc">
</div>

<!-- 
TODO:

- `` as comments in sandstorm
  # This relates to comments being EOL or not
-->

### Numbers and Arithmetic

Roughly speaking, shells treat arithmetic like "macro processing", while OSH
treats it more like part of a programming language.

Despite these differences, OSH is very compatible with existing shell scripts.

#### Static Parsing

Arithmetic are statically parsed, so expressions like `$(( 1 $op 2 ))` aren't
allowed.  Use an explicit `eval` for those rare use cases.

#### No Coercion to Zero

Strings like `''` or `'foo'` aren't coerced to `0` in arithmetic contexts.
OSH produces a fatal error unless you opt out with `shopt -u strict-arith`.
(This is the only strict option that's on by default.)

#### printf '%d' and other numeric formats require a valid integer

In other shells, `printf %d invalid_integer` prints `0` and a warning.

OSH gives you a runtime error.

### Parsing Differences

This section describes differences related to [static
parsing](http://www.oilshell.org/blog/2016/10/22.html).  OSH avoids the
dynamic parsing of most shells.

(NOTE: This section should encompass all the failures from the [wild
tests](http://oilshell.org/cross-ref.html?tag=wild-test#wild-test) and [spec
tests](http://oilshell.org/cross-ref.html?tag=spec-test#spec-test).

#### Strings vs. Bare words in array indices

Strings should be quoted inside array indices:

No:

    "${SETUP_STATE[$err.cmd]}"

Yes:

    "${SETUP_STATE["$err.cmd"]}"

When unquoted, the period causes an ambiguity with respect to regular arrays
vs. associative arrays.  See [Parsing Bash is
Undecidable](http://www.oilshell.org/blog/2016/10/20.html).


#### Subshell in command sub

You can have a subshell in a command sub, but it usually doesn't make sense.

In OSH you need a space after `$(`.  The characters `$((` always start an
arith sub.

No:

    $((cd / && ls))

Yes:

    $( (cd / && ls) )   # Valid but usually doesn't make sense.
    $({ cd / && ls; })  # Use {} for grouping, not {}.  Note trailing ;
    $(cd / && ls)       # Even better


#### Extended glob vs. Negation of expression

- `[[ !(a == a) ]]` is an extended glob.  
- `[[ ! (a == a) ]]` is the negation of an equality test.

In bash the rules are much more complicated, and depend on `shopt -s extglob`.
That flag is a no-op in OSH.  OSH avoids dynamic parsing, while bash does it
in many places.

#### Here doc terminators must be on their own line

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


#### break / continue / return are statically parsed keywords, not builtins

This means that they are not "dynamic":

    b=break
    while true; do
      $b  # doesn't break in OSH
    done

This could be changed, but I wanted control flow to be analyzable.

(Test cases are in `spec/loop`).


#### Spaces aren't allowed in LHS indices

Bash allows:

    a[1 + 2 * 3]=value

OSH only allows

    a[1+2*3]=value

because it parses with limited lookahead.  The first line would result in the
execution of a command named `a[1`.

### More Parsing Differences

These differences occur in "second passes" of the parser.

#### Assignments can't have redirects

No:

    x=abc >out.txt
    x=${y} >out.txt
    x=$((1 + 2)) >out.txt

    # This is the only one that makes sense, but is still disallowed.
    x=$(echo hi) >out.txt

Yes:

    x=$(echo hi >out.txt)

The first three constructs don't make sense, and the fourth has a clearer
alternative spelling, so OSH disallows the construct altogether.

#### Variable names in assignments must be constants

They can't be variables themselves.

No:

    declare "$1"=abc

Yes:

    declare x=abc


NOTE: This restriction will probably be relaxed.  (In the Oil
language, the two constructs will have different syntax.  For example, `x =
'abc'` vs.  `setvar($1, 'abc')`).

#### Brace expansion is all or nothing

No:

    {a,b}{        # what does the second { mean?
    {a,b}{1...3}  # note 3 dots instead of 2

Yes:

    {a,b}\{
    {a,b}\{1...3\}

bash will do a **partial expansion** in the former cases, giving you `a{ b{`
and `a{1...3} b{1...3}`.

OSH considers them syntax errors and aborts all brace expansion, giving you
the same thing back: `{a,b}{` and `{a,b}{1...3}`.


#### Tilde expansion and Brace expansion don't interact

In bash, something like `{~bob,~jane}/src` will expand to home dirs for both
people.  OSH doesn't do this because it separates parsing and evaluation.  By
the time tilde expansion happens, we haven't *evaluated* the brace expansion.
We've only *parsed* it.

(mksh agrees with OSH, but zsh agrees with bash.)

#### Brackets should be escaped within character classes

No:

    echo [[]
    echo []]

Yes:

    echo [\[]
    echo [\]]

Don't use the ambiguous syntax `[[]` or `[]]` for a character class consisting
of a single left bracket or right bracket character.

(NOTE: The ambiguous syntax is allowed when we pass globs through to `libc`,
but it's good practice to be explicit.)

#### Double quotes within backticks

In rare cases, OSH processes backslashes within backticks differently than
other shells.  However there are **two workarounds** that are compatible with
every shell.

No:

    `echo \"`     # is this a literal quote, or does it start a string?

Yes:

    $(echo \")    # $() should always be used instead of ``.
                  # There's no downside to the more modern construct.
    `echo \\"`    # also valid but discouraged


Notes:

- This is tested in [spec/command-sub][].  (Case #25 fails for OSH, and all
  shells start to disagree on case #26.)
- The basic reason for the disagreement is that OSH doesn't have special cases
  for a particular number of backslashes.  The rules are consistent for any
    level of quoting, although incompatible in this edge case.

[spec/command-sub]: http://www.oilshell.org/release/0.6.pre22/test/spec.wwz/command-sub.html


### Differences at Runtime

#### Alias Expansion

Almost all aliases should work in OSH, but there a slight differences with
tings like:

    alias left='{'
    left echo hi; }

    (cases #33-#34 in spec/alias)

or

    alias a=
    a (( var = 0 ))


#### Arrays aren't split inside ${}

Most shells split the entries of arrays like `"$@"` and `"${a[@]}"` here:

    echo ${undef:-"$@"}

In OSH, write this if you want splitting:

    echo ${undef:-$@}

I think OSH is more consistent, but it disagrees with other shells.


#### Touching `errexit` while it's temporarily disabled

In all shells, `errexit` checking is disabled in these situations:
 
1. The condition of the `if`, `while`, and `until`  constructs
2. A command/pipeline prefixed by !
3. Every clause in `||` and `&&` except the last.

Now consider this situation:

- `errexit` is **on**
- The shell disables it one of those three situations
- The user invokes `set -o errexit` to turn it **back on**.

This is a fatal error in OSH.  Other shells delay the restoration of `errexit`
until *after* the temporary disablement.

Good articles on `errexit`:

- <http://mywiki.wooledge.org/BashFAQ/105>
- <http://fvue.nl/wiki/Bash:_Error_handling>

OSH also has `strict-errexit`, to fix two issue with bash's behavior:

- failure in `$()` should be fatal, not ignored.  OSH behaves like dash and
  mksh, not bash.
- failure in `local foo=...` should propagate.  OSH diverges because this is
  arguably a bug in all shells -- `local` is treated as a separate command,
  which means `local foo=bar` behaves differently than than `foo=bar`.

#### Completion

Although the OSH completion API is largely compatible with the bash completion
API, it relieves plugins of the responsibility for quoting.  They should
return candidates as `argv` entries, not shell words.

See the [OSH manual][] for details.

[OSH manual]: osh-manual.html

### Interactive Features

#### History Substitution Language

The rules for history substitution like `!echo` are simpler.  There are no
special cases to avoid clashes with `${!indirect}` and so forth.

TODO: Link to the history lexer.

### Links

- [OSH Spec Tests](../test/spec.wwz/) run shell snippets with OSH and other
  shells to compare their behavior.

External:

- This list may seem long, but compare the list of differences in [Bash POSIX
  Mode](https://www.gnu.org/software/bash/manual/html_node/Bash-POSIX-Mode.html).
  This tells you what `set -o posix` does in bash.

