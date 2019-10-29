<div style="float:right;">
  <span id="version-in-header">Version 0.7.pre5</span> <br/>

  <!-- TODO: date support in cmark.py -->
  <span style="" class="date">
  <!-- REPLACE_WITH_DATE -->
  </span>
</div>

Oil User Manual
===============

The Oil project aims to transform Unix shell into a better programming
language.

This manual covers the parts of Oil that are **new and unique**.  In contrast,
the [OSH User Manual](osh-manual.html) describes parts of `osh` that overlap
with other shells like `bash`.

Everything described here is part of the `osh` binary.  In other words, the Oil
language is implemented with a set of backward-compatible extensions, often
using shell options that are toggled with the `shopt` builtin.

(In the distant future, there may be a legacy-free `oil` binary.)

<!-- cmark.py expands this -->
<div id="toc">
</div>


## Sections


- [Options](oil-options.html)
- [Keywords and Builtins](oil-keywords-and-builtins.html)
  - [Assignment](oil-assignment.html)
- [Command vs. Expression Mode](command-vs-expression-mode.html)
- [Oil Expressions](oil-expressions.html)
  - [Literal Syntax](oil-literal-syntax.html)
- [Word Language](oil-word-language.html) - Oil extends the "word language".
- [Special Variables](oil-special-vars.html) - Oil extends the "word language".
- [funcs, procs, and blocks](func-proc-blocks.html)
- [Eggex](eggex.html) -- regular expression language.
- [Data Model](data-model.html) -- The interpreter


## Other Topics

### Scope

- `evalblock()`

