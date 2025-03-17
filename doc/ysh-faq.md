---
default_highlighter: oils-sh
---

YSH FAQ
=======

Here are some common questions about [YSH]($xref).  Many of the answers boil
down to the fact that YSH is a **smooth upgrade** from [bash]($xref).

Old and new constructs exist side-by-side.  New constructs have fewer
"gotchas".

<!-- cmark.py expands this -->
<div id="toc">
</div>

## What's the difference `myvar`, `$myvar`, and `"$myvar"` ?

YSH is more like Python/JavaScript rather than PHP/Perl, so it doesn't use the
`$` sigil as much.

Never use `$` on the left-hand side:

    var mystr = "foo"   # not var $mystr

Use `$` to **substitute** vars into commands:

    echo $mystr
    echo $mystr/subdir  # no quotes in commands

or quoted strings:

    echo "$mystr/subdir"
    var x = "$mystr/subdir"

Rarely use `$` on the right-hand side:

    var x = mystr       # preferred
    var x = $mystr      # ILLEGAL -- use remove $
    var x = ${mystr:-}  # occasionally useful

    var x = $?          # allowed

See [Command vs. Expression Mode](command-vs-expression-mode.html) for more
details.

## How do I write `~/src` or `~bob/git` in a YSH assignment?

This should cover 80% of cases:

    var path = "$HOME/src"  # equivalent to ~/src

The old shell style will cover the remaining cases:

    declare path=~/src
    readonly other=~bob/git

---

This is only in issue in *expressions*.  The traditional shell idioms work in
*command* mode:

    echo ~/src ~bob/git
    # => /home/alice/src /home/bob/git

The underlying design issue is that the YSH expression `~bob` looks like a
unary operator and a variable, not some kind of string substitution.

Also, quoted `"~"` is a literal tilde, and shells disagree on what `~""` means.
The rules are subtle, so we avoid inventing new ones.

<!--
TODO: I want the ${ ~/src } syntax though it's complicated by ksh command sub
-->

## How do I write the equivalent of `echo -e` or `echo -n`?

To echo special characters denoted by backslash escapes, use a
statically-parsed string literal, not `echo -e`:

    echo u'tab \t newline \n'       # YES: J8 style string is recommended in YSH
    echo $'tab \t newline \n'       #      bash-style string is also accepted

These styles don't work in YSH:

    echo -e "tab \\t newline \\n"   # NO: -e is printed literally
    echo -e "tab \t newline \n"     #     Error: Invalid char escape

To omit the trailing newline, use the `write` builtin:

    write -n       -- $prefix       # YES
    write --end '' -- $prefix       # synonym

    echo -n $prefix                 # NO: -n is printed literally

### Why Were `-e` and `-n` Removed?

The idioms with `u''` and `write` are more powerful and consistent.

Moreover, shell's `echo` is the *only* builtin that doesn't accept `--` to stop
flag processing.

That is, `echo "$flag"` always has a few bugs: when `$flag` is `-e`, `-n`,
`-en`, or `-ne`. There's **no** way to fix this bug in POSIX shell.

So portable shell scripts use:

    printf '%s\n' "$x"  # print $x "unmolested" in POSIX shell

We could have chosen to respect `echo -- $x`, but YSH already has:

    write -- $x         # print $x "unmolested" in YSH

That means YSH has:

    echo $x             # an even shorter way

So `echo` is technically superfluous in YSH, but it's also short, familiar, and
correct.

YSH isn't intended to be compatible with POSIX shell; only OSH is.

### How do I write a string literal with both `$myvar` and `\n`?

In YSH, either use `$[ \n ]` inside a double-quoted string:

    $ echo "$myvar $[ \n ] two"  # expression sub wraps \n
    value_of_myvar
    two

Or use the concatenation operator `++` with two styles of string literal:

    echo $[u'newline \n' ++ " $year/$month/$day"]

This POSIX shell behavior is probably not what you want:

    $ echo "\n"
    \n  # not a newline!

### How do I find all the `echo` invocations I need to change when using YSH?

A search like this can statically find most usages:

    $ egrep -n 'echo (-e|-n|-en|-ne)' *.sh
    test/syscall.sh:58: echo -n hi
    test/syscall.sh:76: echo -e '\t'

## What's the difference between `$(dirname $x)` and `$[len(x)]` ?

Superficially, both of these syntaxes take an argument `x` and return a
string.  But they are different:

- `$(dirname $x)` is a shell command substitution that returns a string, and
  **starts another process**.
- `$[len(x)]` is an expression sub containing a function call expression.
  - It doesn't need to start a process.
  - Note that `len(x)` evaluates to an integer, and `$[len(x)]` converts it to
    a string.

<!--
(Note: builtin subs like `${.myproc $x}` are meant to eliminate process
overhead, but they're not yet implemented.)
-->

## Why doesn't a raw string work here: `${array[r'\']}` ?

This boils down to the difference between OSH and YSH, and not being able to
mix the two.  Though they look similar, `${array[i]}` syntax (with braces) is
fundamentally different than `$[array[i]]` syntax (with brackets).

- OSH supports `${array[i]}`.
  - The index is legacy/deprecated shell arithmetic like `${array[i++]}` or
    `${assoc["$key"]}`.
  - The index **cannot** be a raw string like `r'\'`.
- YSH supports both, but [expression substitution][expr-sub] syntax
  `$[array[i]]` is preferred.
  - It accepts YSH expressions like `$[array[i + 1]` or `$[mydict[key]]`.
  - A raw string like `r'\'` is a valid key, e.g.  `$[mydict[r'\']]`.

[expr-sub]: ref/chap-expr-lang.html#expr-sub

Of course, YSH style is preferred when compatibility isn't an issue.

No:

    echo ${array[r'\']}

Yes:

    echo $[array[r'\']]

A similar issue exists with arithmetic.

Old:

    echo $((1 + 2))   # shell arithmetic

New:

    echo $[1 + 2]     # YSH expression

<!--

## Why doesn't the ternary operator work here: `${array[0 if cond else 5]}`?

The issue is the same as above.  YSH expression are allowed within `$[]` but
not `${}`.

-->

## How do I combine conditional commands and expressions: `if (myvar)` and `if test -f`?

You can use the `--true` and `--false` flags to the [YSH test][ysh-test]
builtin:

    if test --true $[myvar] && test --file x {
        echo ok
    }

They test if their argument is literally the string `"true"` or `"false"`.

This works because the boolean `true` *stringifies* to `"true"`, and likewise
with `false`.

[ysh-test]: ref/chap-builtin-cmd.html#ysh-test


## Why do I lose the value of `p` in `myproc (&p) | grep foo`?

In a pipeline, most components are **forked**.  This means that `myproc (&p)`
runs in a different process from the main shell.

The main shell can't see the memory of a subshell.

---

In general, you have to restructure your code to avoid this.  You could use a proc with multiple outputs:

    myproc (&p, &grepped_output)

Or you could use a function:

    var out1, out2 = myfunc(io)

---

[The Unix Shell Process Model - When Are Processes
Created?](process-model.html) may help.

This issue is similar to the `shopt -s lastpipe` issue:

    $ bash -c 'echo hi | read x; echo x=$x'
    x=

    $ zsh -c 'echo hi | read x; echo x=$x'
    x=hi

In bash, `read` runs in a subshell, but in `zsh` and OSH, it runs in the main
shell.

## Why are `Dict` and `Obj` different types?

*JavaScript has a single Object type, while Python has separate dicts and
objects.*

In YSH, we draw a line between data and code.

- A `Dict` is pure **data**, and may correspond to JSON from untrusted sources.
- An `Obj` bundles both data and **code**, and can't be serialized by default.

You can create an `Obj` from a `Dict` with the `Obj` constructor.  Conversely,
you can get the first Dict in an object with [first(myobj)][first].

There is no special `__proto__` or `prototype` name, which reduces the
likelihood of "prototype pollution" vulnerabilities.

---

This is essentially the [Interior vs. Exterior][interior-exterior] distinction:
An Obj lives inside the shell process, while a Dict may come from outside the
process (user input).

[first]: ref/chap-builtin-func.html#first
[interior-exterior]: https://www.oilshell.org/blog/2023/06/ysh-design.html

## Why are `Command` and `Proc` different types?

*Could a `Command` be a `Proc` with no arguments?  Similarly, could an `Expr` be a
`Func` with no arguments?*

Procs and Funcs both push a new stack frame, and bind arguments to declared
parameters.

On the other hand, `Command` and `Expr` are more "raw" and flexible:

- They can be evaluated in different stack frames &mdash;
  e.g. `io->eval(b, in_captured_frame)`
- They can have "undeclared" variable bindings &mdash; 
  e.g. `io->eval(b, vars={x: 42})`.

In other words, they're low-level, reflective types that allow users to create
expressive APIs, like:

    cd /tmp {                    # Command literal (block)
      ls -l
    }
    my-table | where [size > 3]  # Expr literal

---

Another way to think about it: we could have removed procs from the core YSH
language, and implemented them in terms of command blocks and `io->eval()`.
But that seems too low-level!

## Related

- [Oil Language FAQ]($wiki) on the wiki has more answers.  They may be migrated
  here at some point.

