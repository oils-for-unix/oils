---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oils-sh
preserve_anchor_case: yes
---

Word Language
===

This chapter in the [Oils Reference](index.html) describes the word language
for OSH and YSH.

<div id="toc">
</div>

<h2 id="string-lit">String Literals</h2>

### multi-str

### j8-str

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

Also see [ysh-string](chap-expr-lang.html#ysh-string).

## Substitutions

### com-sub

Evaluates to the stdout of a command.  If a trailing newline is returned, it's
stripped:

    $ hostname
    example.com

    $ x=$(hostname)
    $ echo $x
    example.com

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

