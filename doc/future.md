---
in_progress: true
---

Ideas for Future Deprecations
=============================

These are some **ideas** extracted from [Shell Language
Deprecations](deprecations.html).  These breakages may never happen!

<!-- cmark.py expands this -->
<div id="toc">
</div>

<https://github.com/oilshell/oil/issues/673>

## Inline Eggex

Instead of:

    var pat = / digit+ /
    egrep $pat *.txt

You can imagine:

    egrep $/ digit+ / *.txt

Minor breakage: making `$/` significant.

Note: this is probably possible with `shopt --set strict_dollar`.

