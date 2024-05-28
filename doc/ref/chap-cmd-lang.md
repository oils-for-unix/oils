---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oils-sh
preserve_anchor_case: yes
---

Command Language
===

This chapter in the [Oils Reference](index.html) describes the command language
for OSH, and some YSH extensions.

- Back: [OSH Table of Contents](toc-osh.html) |
  [YSH Table of Contents](toc-ysh.html)

<div id="toc">
</div>

## Quick Sketch: What's a Command?

OSH:

    print-files() {
      for name in *.py; do
        if test -x "$name"; then
          echo "$name is executable"
        fi
      done
    }

YSH:

    proc print-files {
      for name in *.py {
        if test -x $name {  # no quotes needed
          echo "$name is executable"
        }
      }
    }
  

<h2 id="Commands">Commands</h2>

<h3 id="simple-command" class="osh-ysh-topic">simple-command</h3>

Commands are composed of words.  The first word may be the name of

1. A builtin shell command
1. A YSH `proc` or shell "function"
1. A Hay node declared with `hay define`
1. An external command
1. An alias

Examples:

    echo hi               # a shell builtin doesn't start a process
    ls /usr/bin ~/src     # starts a new process
    myproc "hello $name"
    myshellfunc "hello $name"
    myalias -l
<!-- TODO: document lookup order -->

Redirects are also allowed in any part of the command:

    echo 'to stderr' >&2
    echo >&2 'to stderr'

    echo 'to file' > out.txt
    echo > out.txt 'to file'

<h3 id="semicolon" class="osh-ysh-topic">semicolon ;</h3>

Run two commands in sequence like this:

    echo one; echo two

or this:

    echo one
    echo two

<h3 id="ampersand" class="osh-topic">ampersand &amp;</h3>

Run a command, but don't wait for it to finish.

    sleep 1 &
    { echo two; sleep 2 } &
    wait
    wait

In YSH, use the [fork][] builtin.

[fork]: chap-builtin-cmd.html#fork

<h2 id="Conditional">Conditional</h2>

<h3 id="case" class="osh-topic">case</h3>

Match a string against a series of glob patterns.  Execute code in the section
below the matching pattern.

    path='foo.py'
    case "$path" in
      *.py)
        echo 'python'
        ;;
      *.sh)
        echo 'shell'
        ;;
    esac

For bash compatibility, the `;;` terminator can be substituted with either:

- `;&`   - fall through to next arm, ignoring the condition
- `;;&`  - fall through to next arm, respecting the condition

<h3 id="if" class="osh-topic">if</h3>

Test if a command exited with status zero (true).  If so, execute the
corresponding block of code.

Shell:

    if test -d foo; then
      echo 'foo is a directory'
    elif test -f foo; then
      echo 'foo is a file'
    else
      echo 'neither'
    fi

YSH:

    if test -d foo {
      echo 'foo is a directory'
    } elif test -f foo {
      echo 'foo is a file'
    } else {
      echo 'neither'
    }

<h3 id="dbracket" class="osh-topic">dbracket [[</h3>

Statically parsed boolean expressions, from bash and other shells:

    x=42
    if [[ $x -eq 42 ]]; then
      echo yes
    fi  # => yes

Compare with the [test][] builtin, which is dynamically parsed.

See [bool-expr][] for the expression syntax.

[test]: chap-builtin-cmd.html#test
[bool-expr]: chap-mini-lang.html#bool-expr


<h3 id="true" class="osh-ysh-topic">true</h3>

Do nothing and return status 0.

    if true; then
      echo hello
    fi

<h3 id="false" class="osh-ysh-topic">false</h3>

Do nothing and return status 1.

    if false; then
      echo 'not reached'
    else
      echo hello
    fi

<h3 id="colon" class="osh-topic">colon :</h3>

Like `true`: do nothing and return status 0.

<h3 id="bang" class="osh-ysh-topic">bang !</h3>

Invert an exit code:

    if ! test -d /tmp; then   
      echo "No temp directory
    fi

<h3 id="and" class="osh-ysh-topic">and &amp;&amp;</h3>

    mkdir -p /tmp && cp foo /tmp

<h3 id="or" class="osh-ysh-topic">or ||</h3>

    ls || die "failed"

<h2 id="Iteration">Iteration</h2>

<h3 id="while" class="osh-ysh-topic">while</h3>

POSIX

<h3 id="until" class="osh-topic">until</h3>

POSIX

<h3 id="for" class="osh-ysh-topic">for</h3>

For loops iterate over words.

YSH style:

    var mystr = 'one'
    var myarray = :| two three |

    for i in $mystr @myarray *.py {
      echo $i
    }


Shell style:

    local mystr='one'
    local myarray=(two three)

    for i in "mystr" "${myarray[@]}" *.py; do
      echo $i
    done

Both fragments output 3 lines and then Python files on remaining lines.

<h3 id="for-expr-sh" class="osh-topic">for-expr-sh</h3>

A bash/ksh construct:

    for (( i = 0; i < 5; ++i )); do
      echo $i
    done

<h2 id="Control Flow">Control Flow</h2>

These are keywords in Oils, not builtins!

### break

Break out of a loop.  (Not used for case statements!)

### continue

Continue to the next iteration of a loop.

### return

Return from a function.

### exit

Exit the shell process with the given status:

    exit 2

<h2 id="Grouping">Grouping</h2>

### sh-func

POSIX:

    f() {
      echo args "$@"
    }
    f 1 2 3

### sh-block

POSIX:

    { echo one; echo two; }

The trailing `;` is necessary in OSH, but not YSH.  In YSH, `parse_brace` makes
`}` is more of a special word.


### subshell

    ( echo one; echo two )

In YSH, use [forkwait](chap-builtin-cmd.html#forkwait) instead of parentheses.

<h2 id="Concurrency">Concurrency</h2>

### pipe

### ampersand

    CMD &

The `&` language construct runs CMD in the background as a job, immediately
returning control to the shell.

The resulting PID is recorded in the `$!` variable.

<h2 id="Redirects">Redirects</h2>

### redir-file

Examples of redirecting the `stdout` of a command:

    echo foo > out.txt   # overwrite out.txt
    date >> stamp.txt    # append to stamp.txt

<!--
    echo foo >| out.txt   # clobber the file even if set -o noclobber
-->

Redirect to the `stdin` of a command:

    cat < in.txt

Redirects are compatible with POSIX and bash, so they take descriptor numbers
on the left:

    make 2> stderr.txt   # '2>' is valid, but '2 >' is not

Note that the word argument to **file** redirects is evaluated like bash, which
is different than other arguments to other redirects:

    tar -x -z < Python*  # glob must expand to exactly 1 file
    tar -x -z < $myvar   # $myvar is split because it's unquoted

In other words, it's evaluated **as** a sequence of 1 word, which **produces**
zero to N strings.  But redirects are only valid when it produces exactly 1
string.

(Related: YSH uses `shopt --set simple_word_eval`, which means that globs that
match nothing evaluate to zero strings, not themselves.)

<!-- They also take a file descriptor on the left -->


### redir-desc

Redirect to a file descriptor:

    echo 'to stderr' >&2

<!--
NOTE: >&2 is just like <&2 
There's no real difference.
-->

### here-doc

TODO: unbalanced HTML if we use \<\<?

    cat <<EOF
    here doc with $double ${quoted} substitution
    EOF

    myfunc() {
            cat <<-EOF
            here doc with one tab leading tab stripped
            EOF
    }

    cat <<< 'here string'

<!-- TODO: delimiter can be quoted -->
<!-- Note: Python's HTML parser thinks <EOF starts a tag -->

## Other Command

<h3 id="dparen" class="osh-topic">dparen ((</h3>

<h3 id="time" class="osh-ysh-topic">time</h3>

    time [-p] pipeline

Measures the time taken by a command / pipeline.  It uses the `getrusage()`
function from `libc`.

Note that time is a KEYWORD, not a builtin!

<!-- Note: bash respects TIMEFORMAT -->


## YSH Simple

### typed-arg

Internal commands (procs and builtins) accept typed arguments in parentheses:

    json write (myobj)

Redirects can also appear after the typed args:

    json write (myobj) >out.txt

### lazy-expr-arg

Expressions in brackets like this:

    assert [42 === x]

Are syntactic sugar for:

    assert (^[42 === x])

That is, it's single arg of type `value.Expr`.

Redirects can also appear after the lazy typed args:

    assert [42 ===x] >out.txt

### block-arg

Blocks can be passed to simple commands, either literally:

    cd /tmp {
      echo $PWD  # prints /tmp
    }
    echo $PWD

Or as an expression:

    var block = ^(echo $PWD)
    cd /tmp (; ; block)

Note that `cd` has no typed or named arguments, so the two semicolons are
preceded by nothing.

Compare with [sh-block](#sh-block).

Redirects can appear after the block arg:

    cd /tmp {
      echo $PWD  # prints /tmp
    } >out.txt

## YSH Cond

### ysh-if

Like shell, you can use a command:

    if test --file $x {
      echo "$x is a file"
    }

You can also use an expression:

    if (x > 0) {
      echo 'positive'
    }

### ysh-case

Like the shell case statement, the Ysh case statement has **string/glob** patterns.

    var s = 'README.md'
    case (s) {
      *.py           { echo 'Python' }
      *.cc | *.h     { echo 'C++' }
      *              { echo 'Other' }
    }
    # => Other

We also generated it to **typed data** within `()`:

    var x = 43
    case (x) {
      (30 + 12)      { echo 'the integer 42' }
      (else)         { echo 'neither' }
    }
    # => neither

The `else` is a special keyword that matches any value.

    case (s) {
      / dot* '.md' / { echo 'Markdown' }
      (else)         { echo 'neither' }
    }
    # => Markdown

## YSH Iter

### ysh-while

Command or expression:

    var x = 5
    while (x < 0) {
      setvar x -= 1
    }

### ysh-for

Two forms for shell-style loops:

    for name in *.py {
      echo "$name"
    }

    for i, name in *.py {
      echo "$i $name"
    }

Two forms for expressions that evaluate to a `List`:

    for item in (mylist) {
      echo "$item"
    }

    for i, item in (mylist) {
      echo "$i $item"
    }

Three forms for expressions that evaluate to a `Dict`:

    for key in (mydict) {
      echo "$key"
    }

    for key, value in (mydict) {
      echo "$key $value"
    }

    for i, key, value in (mydict) {
      echo "$i $key $value"
    }
