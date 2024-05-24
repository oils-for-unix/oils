---
default_highlighter: oils-sh
preserve_anchor_case: yes
---

Oils Reference
=============

<style>
  .highlight {
      background-color: #eee;
      padding-top: 0.2em;
      padding-bottom: 0.2em;
      padding-left: 1em;
      padding-right: 1em;
      font-size: x-large;
  }
</style>

This reference has **three** tables of contents.  They link to topics within 15
chapters.  (in progress)

<div class="highlight">

[**OSH Table of Contents**](toc-osh.html) - Compatible

[**YSH Table of Contents**](toc-ysh.html) - New and Powerful

</div>

1. [Front End](chap-front-end.html)
1. [Command Language](chap-cmd-lang.html)
1. [Word Language](chap-word-lang.html)
1. [OSH Assignment](chap-osh-assign.html)
1. [Mini Languages](chap-mini-lang.html)
1. [Builtin Commands](chap-builtin-cmd.html)
1. [Global Shell Options](chap-option.html)
1. [Special Variables](chap-special-var.html)
1. [Plugins and Hooks](chap-plugin.html)
1. [YSH Expression Language](chap-expr-lang.html)
1. [YSH Types and Methods](chap-type-method.html)
1. [Builtin Functions](chap-builtin-func.html)

<div class="highlight">

[**Data Notation Table of Contents**](toc-data.html)

</div>

13. [JSON / J8 Notation](chap-j8.html)
1. Packle (TODO)
1. [Errors](chap-errors.html)

## `help` builtin command

When you type `help` in OSH or YSH, it shows a URL to this reference, or text
extracted from it.

## About

### Source

[The source code]($oils-src:doc/) is a simple tree of Markdown files:

    REPO/
      doc/
        release-index.md     # /release/$VERSION/

        index.md             # All Docs on Oils, /release/$VERSION/doc/
        getting-started.md
        ...

        ref/
          index.md           # this page, the Oils Reference
          toc-osh.md         # OSH topics
          toc-ysh.md         # YSH topics
          toc-data.md        # Data language topics

          chap-cmd-lang.md   # chapter on the command language
          chap-front-end.md
          ...

### HTML

The URLs mirror the source code, with minor differences:

    /release/$VERSION/
      index.html
      doc/
        index.html
        getting-started.html
        ...

        ref/
          index.html
          toc-osh.html
          toc-ysh.html
          toc-data.html

          chap-cmd-lang.html
          chap-front-end.html
          ...

You can link to topics with internal anchors:

- [chap-cmd-lang.html#simple-command](chap-cmd-lang.html#simple-command)
- [chap-builtin-cmd.html#compgen](chap-builtin-cmd.html#compgen)

### Terminology

This reference has a 3-level structure:

1. *Chapter* - A big HTML page.
   - A chapter may apply to OSH, YSH, or both.
1. *Section* - An `<h2>` heading in a chapter
1. *Topic* - An `<h3>` heading in a chapter.  
   - It has a **globally unique** name like `doc-comment`, which is used in the
     `help` builtin.
   - A topic may apply to OSH, YSH, or both.

More terminology:

- *Table of Contents* - a doc with a dense list of topic links.
- *Card* - Some topics are exported as `help` builtin "cards".  They can be
  inline text, or a URL pointer.  A card may also link to POSIX or bash docs.

