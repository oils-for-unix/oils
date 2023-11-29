---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oils-sh
preserve_anchor_case: yes
---

Mini Languages
===

This chapter in the [Oils Reference](index.html) describes "mini-languages".

In contrast, the main sub languages of YSH are [command](chap-cmd-lang.html),
[word](chap-word-lang.html), and [expression](chap-expr-lang.html).

<div id="toc">
</div>
<h2 id="sublang">Other Shell Sublanguages</h2>

## Arithmetic

### arith-context

### sh-numbers

### sh-arith

### sh-logical

### sh-bitwise

## Boolean

### dbracket

Compatible with bash.

### bool-expr

### bool-infix

### bool-path

### bool-str

### bool-other

## Patterns

### glob

### extglob

### regex

Part of [dbracket]($osh-help)

## Other Sublang

### braces

### histsub

History substitution uses `!`.

### char-escapes

These backslash escape sequences are used in `echo -e`, [printf]($osh-help),
and in C-style strings like `$'foo\n'`:

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

