---
title: Mini Languages (Oils Reference)
all_docs_url: ..
body_css_class: width40
default_highlighter: oils-sh
preserve_anchor_case: yes
---

<div class="doc-ref-header">

[Oils Reference](index.html) &mdash;
Chapter **Mini Languages**

</div>

This chapter describes "mini-languages" like glob patterns and brace expansion.

In contrast, the main sub languages of YSH are [command](chap-cmd-lang.html),
[word](chap-word-lang.html), and [expression](chap-expr-lang.html).

<span class="in-progress">(in progress)</span>

<div id="dense-toc">
</div>

<h2 id="sublang">Other Shell Sublanguages</h2>

## Arithmetic

### arith-context

Arithmetic expressions are parsed and evaluated in many parts of POSIX shell
and bash.

Static:

    a=$(( x + 1 ))  # POSIX shell

    # bash
    (( a = x + 1 ))

    for (( i = 0; i < n; ++i )); do
      echo $i
    done

Dynamic:

    [[ 5 -eq 3+x ]]   # but not test  5 -eq 3+x

Array index contexts:

    echo ${a[i+1]}      # get
    echo ${#a[i+1]}     # calculate

    a[i+1]=foo          # set

    printf -v 'a[i+1]'  # assign to this location
    unset 'a[i+1]'      # unset location

    echo ${a[@] : i+1 : i+2 }  # bash slicing

bash allows similar array expressions with `test -v`:

    test -v 'array[i+1]'       # is array item set?
    test -v 'assoc[$myvar]'    # is assoc array key set?

    [[ -v 'array[i+1]' ]]      # ditto
    [[ -v 'assoc[$myvar]' ]]

But OSH allows only integers and "bare" string constants:

    test -v 'array[42]'        # is array item set?
    test -v 'assoc[key]'       # is assoc array key set?

### sh-numbers

### sh-arith

### sh-logical

### sh-bitwise

## Boolean

### bool-expr

Boolean expressions can be use the `test` builtin:

    test ! $x -a $y -o $z

Or the `[[` command language:

    [[ ! $x && $y || $z ]]

### bool-infix

Examples:

    test $a -nt $b
    test $x == $y

### bool-path

Example:

    test -d /etc
    test -e /
    test -f myfile

YSH has long flags:

    test --dir /etc
    test --exists /
    test --file myfile

### bool-str

    test -n foo  # => status 0 / true -- foo is non-empty
    test -z ''   # => status 0 / true -- '' is empty / zero-length

### bool-other

Test if a shell option is set:

    test -o errexit      

Test the values of variables:

    test -v var_name     # is variable defined?
    test -v name[index]  # is an entry in a container set?

Notes:

- In `name[index]`, OSH doesn't allow arithmetic expressions / dynamic parsing,
  as bash does.
- `shopt --set strict_word_eval` exposes "syntax errors" in `name[index]`, and
  is recommended.
  - Without this option, `test -v` will silently return `1` (false) when given
    nonsense input, like `test -v /`.

## Patterns

### glob-pat

TODO: glob syntax

### extglob

TODO: extended glob syntax

### regex

Part of [dbracket](chap-cmd-lang.html#dbracket)

## Other Sublang

### braces

### histsub

History substitution uses `!`.

### char-escapes

These backslash escape sequences are used in [echo
-e](chap-builtin-cmd.html#echo), [printf](chap-builtin-cmd.html#printf), and in
C-style strings like `$'foo\n'`:

    \\         backslash
    \a         alert (BEL)
    \b         backspace
    \c         stop processing remaining input
    \e         the escape character \x1b
    \f         form feed
    \n         newline
    \r         carriage return
    \t         tab
    \v         vertical tab
    \xHH       the byte with value HH, in hexadecimal
    \uHHHH     the unicode char with value HHHH, in hexadecimal
    \UHHHHHHHH the unicode char with value HHHHHHHH, in hexadecimal

Also:

    \"         Double quote.

Inconsistent octal escapes:

    \0NNN      echo -e '\0123'
    \NNN       printf '\123'
               echo $'\123'

TODO: Verify other differences between `echo -e`, `printf`, and `$''`.  See
`frontend/lexer_def.py`.

