---
title: Command Language (Oils Reference)
all_docs_url: ..
body_css_class: width40
default_highlighter: oils-sh
preserve_anchor_case: yes
---

<div class="doc-ref-header">

[Oils Reference](index.html) &mdash;
Chapter **Command Language**

</div>

This chapter describes the command language for OSH, and some YSH extensions.

<span class="in-progress">(in progress)</span>

<div id="dense-toc">
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

### simple-command

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

### prefix-binding

Bindings are allowed before a simple command:

    PYTHONPATH=. mydir/myscript.py

These bindings set a variable and mark it exported.  This binding is usually
temporary, but when used with certain [special builtins][special], it persists.

[special]: https://www.gnu.org/software/bash/manual/html_node/Special-Builtins.html

- Related: [ysh-prefix-binding](ysh-prefix-binding)

### ysh-prefix-binding

YSH prefix bindings look exactly like they do in shell:

    PYTHONPATH=. mydir/myscript.py

However, they temporarily set `ENV.PYTHONPATH`, not `$PYTHONPATH`.  This is
done by adding a new `Dict` to the prototype chain of the `Obj`.

The new `ENV` then becomes the environment of the child processes for the
command.

(In YSH, prefix bindings only mean one thing.  They are temporary; they don't
persist depending on whether the command is a special builtin.)

- Related: [ENV](chap-special-var.html#ENV), [prefix-binding](chap-cmd-lang.html#prefix-binding)


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

Pipelines are a traditional POSIX shell construct:

    ls /tmp | grep ssh | sort

Related:

- [`PIPESTATUS`]() in OSH
- [`_pipeline_status`]() in YSH

[PIPESTATUS]: chap-special-var.html#PIPESTATUS
[_pipeline_status]: chap-special-var.html#_pipeline_status

<h3 id="ampersand" class="osh-topic">ampersand &amp;</h3>

Start a command as a background job.  Don't wait for it to finish, and return
control to the shell.

The PID of the job is recorded in the `$!` variable.

    sleep 1 &
    echo pid=$!
    { echo two; sleep 2 } &
    wait
    wait

In YSH, use the [fork][] builtin.

[fork]: chap-builtin-cmd.html#fork


<h2 id="Redirects">Redirects</h2>

### redir-file

The operators `>` and `>>` redirect the `stdout` of a process to a disk file.  
The `<` operator redirects `stdin` from a disk file.

---

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

Here documents let you write the `stdin` of a process in the shell program.

Specify a delimiter word (like EOF) after the redir operator (like `<<`).

If it's unquoted, then `$` expansion happens, like a double-quoted string:

    cat <<EOF
    here doc with $double ${quoted} substitution
    EOF

If the delimiter is quoted, then `$` expansion does **not** happen, like a
single-quoted string:

    cat <<'EOF'
    price is $3.99
    EOF

Leading tabs can be stripped with the `<<-` operator:

    myfunc() {
            cat <<-EOF
            here doc with one tab leading tab stripped
            EOF
    }

### here-str

The `<<<` operator means that the argument is a `stdin` string, not a
chosen delimiter.

    cat <<< 'here string'

The string **plus a newline** is the `stdin` value, which is consistent with
GNU bash.

### ysh-here-str

You can also use YSH multi-line strings as "here strings".  For example:

Double-quoted:

    cat <<< """
    double
    quoted = $x
    """

Single-quoted:

    cat <<< '''
    price is
    $3.99
    '''

J8-style with escapes:

    cat <<< u'''
    j8 style string price is
    mu = \u{3bc}
    '''

In these cases, a trailing newline is **not** added.  For example, the first
example is equivalent to:

    write --end '' -- """
    double
    quoted = $x
    """

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

    assert [42 === x] >out.txt

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

### ysh-if

Like shell, you can use a command:

    if test --file $x {
      echo "$x is a file"
    }

You can also use an expression:

    if (x > 0) {
      echo 'positive'
    }

## YSH Iter

### ysh-for

#### Words

This is a shell-style loop over "words":

    for name in README.md *.py {
      echo $name
    }
    # => README.md
    # => foo.py

You can also ask for the index:

    for i, name in README.md *.py {
      echo "$i $name"
    }
    # => 0 README.md
    # => 1 foo.py

#### Lines of `stdin`

Here's how to iterate over the lines of stdin:

    for line in (io.stdin) {
      echo $line
    }

Likewise, you can ask for the index with `for i, line in (io.stdin) { ...`.

### ysh-while

You can use an expression as the condition:

    var x = 5
    while (x < 0) {
      setvar x -= 1
    }

You or a command:

    while test -f myfile {
      echo 'myfile'
      sleep 1
    }

#### Expressions

Expressions are enclosed in `()`.

Iterating over a `List` or `Range` is like iterating over words or lines:

    var mylist = [42, 43]
    for item in (mylist) {
      echo $item
    }
    # => 42
    # => 43

    var n = 5
    for i in (3 .. n) {
      echo $i
    }
    # => 3
    # => 4

However, there are **three** ways of iterating over a `Dict`:

    for key in (mydict) {
      echo $key
    }

    for key, value in (mydict) {
      echo "$key $value"
    }

    for i, key, value in (mydict) {
      echo "$i $key $value"
    }

That is, if you ask for two things, you'll get the key and value.  If you ask
for three, you'll also get the index.

