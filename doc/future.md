---
in_progress: true
---

Ideas for Future Deprecations
=============================

These are some ideas, extracted from [Shell Language
Deprecations](deprecations.html).

These breakages may never happen, as they require a significant new lexer mode.
If they do, you will want to avoid the following syntax:

- the character sequences `$/`, `'''`, `"""` anywhere

I expect that those sequences are rare, so this change would break few
programs.

<!-- cmark.py expands this -->
<div id="toc">
</div>

## First Class File Descriptors (`parse_amp`)

We want to make redirection simpler and more consistent.  We can remove the
confusing `<&` and `>&` operators, and instead use `>` and `<` with
descriptors.

Remains the same:

    echo foo >file
    read :var <file

Old:

    echo foo >& 2
    read var <& 0

New:

    echo foo > &2         # descriptor with &
    read :var < &0

    echo foo > &stderr    # named descriptor
    read :var < &stdin

Old:

    echo foo 1>& 2

New:

    echo foo &1 > &2

(Note: the syntax `{fd}> file.txt` will be replaced by the `open` builtin.)

<https://github.com/oilshell/oil/issues/673>

## Inline Eggex

Instead of:

    var pat = / digit+ /
    egrep $pat *.txt

You can imagine:

    egrep $/ digit+ / *.txt

Minor breakage: making `$/` significant.

Note: this is probably possible with `shopt --set strict_dollar`.

