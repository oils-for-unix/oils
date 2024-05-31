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

### expr-splice

### var-splice

<h2 id="formatting">Formatting Typed Data as Strings</h2>

### ysh-printf

### ysh-format


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

OSH has shell-compatible command sub like `$(echo hi)`.  If a trailing newline
is returned, it's removed:

    $ hostname
    example.com

    $ echo "/tmp/$(hostname)"
    /tmp/example.com

YSH has spliced command subs, enabled by `shopt --set parse_at`.  The reuslt is
a **List** of strings, rather than a single string.

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

### op-test

### op-strip

### op-replace

### op-index

    ${a[i+1]}

### op-slice

### op-format

${x@P} evaluates x as a prompt string, e.g. the string that would be printed if
PS1=$x.

