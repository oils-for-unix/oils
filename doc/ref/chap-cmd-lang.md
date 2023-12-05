---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oils-sh
preserve_anchor_case: yes
---

Command Language
===

This chapter in the [Oils Reference](index.html) describes the command language
for both OSH and YSH.

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

Use [forkwait]($osh-help) in YSH instead.

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

<h2 id="Other Command">Other Command</h2>

<h3 id="dparen" class="osh-topic">dparen ((</h3>

<h3 id="time" class="osh-ysh-topic">time</h3>

    time [-p] pipeline

Measures the time taken by a command / pipeline.  It uses the `getrusage()`
function from `libc`.

Note that time is a KEYWORD, not a builtin!

<!-- Note: bash respects TIMEFORMAT -->


<h2 id="YSH Command">YSH Command</h2>

### proc

Procs are shell-like functions, but with named parameters, and without dynamic
scope (TODO):

    proc copy(src, dest) {
      cp --verbose --verbose $src $dest
    }

Compare with [sh-func]($osh-help).

### ysh-if

Command or expression:

    if (x > 0) {
      echo 'positive'
    }

### ysh-case

    case $x {
      # balanced parens around patterns
      (*.py)     echo 'Python' ;;
      ('README') echo 'README' ;;  # consatnt words must be quoted
      (*)        echo 'Other'  ;;
    }

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

### equal

The `=` keyword evaluates an expression and shows the result:

    oil$ = 1 + 2*3
    (Int)   7

It's meant to be used interactively.  Think of it as an assignment with no
variable on the left.

### call

The `call` keyword evaluates an expression and throws away the result:

    var x = :| one two |
    call x->append('three')
    call x->append(['typed', 'data'])

### typed-arg

Internal commands (procs and builtins) accept typed arguments.

    json write (myobj)

Block literals have a special syntax:

    cd /tmp {
      echo $PWD
    }

This is equivalent to:

    var cmd = ^(echo $PWD)  # unevaluated command

    cd /tmp (cmd)  # pass typed arg

### lazy-expr-arg

Expressions in brackets like this:

    assert [42 === x]

Are syntactic sugar for:

    assert (^[42 === x])

That is, it's single arg of type `value.Expr`.

### block-arg

Blocks can be passed to builtins (and procs eventually):

    cd /tmp {
      echo $PWD  # prints /tmp
    }
    echo $PWD

Compare with [sh-block]($osh-help).

# vim: sw=2
