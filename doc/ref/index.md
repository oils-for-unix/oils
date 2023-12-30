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
  }
</style>

A guide to everything in Oils (in progress).

Go back to [All Docs on Oils](../index.html) for design docs and tutorials.

<div id="toc">
</div>

## Online HTML

<div class="highlight">

Oils has two major "modes" for shell:

[**OSH Table of Contents**](toc-osh.html) - Compatible

[**YSH Table of Contents**](toc-ysh.html) - New and Powerful

You can use OSH by itself, YSH by itself, or upgrade OSH to YSH.

</div>

Those two docs link to dozens of **topics** within these 12 **chapters**:

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

[**Data Notation Table of Contents**](toc-data.html) - Languages for data are
complementary to shell programs.

</div>

Topics in these 3 chapters:

13. [JSON / J8 Notation](chap-j8.html)
1. Packle (TODO)
1. [Errors](chap-errors.html)

## `help` builtin command

When you type `help` in OSH or YSH, the command shows some of this material,
and prints hyperlinks to it.

## More About This Reference

### Terminology

There are 3 levels in this tree of docs, which underlies the `help` builtin:

1. *Chapter* - An HTML doc that's part of the reference.  May apply to OSH, YSH
   or both.
1. *Section* - An `<h2>` heading in a chapter
1. *Topic* - An `<h3>` heading in a chapter.  
   - It has text with a **globally unique** name like `doc-comment`.
   - May apply to OSH, YSH or both.

More terminology:

- *Table of Contents* - a doc that links to topics, within chapters.
- *Card* - Topics maybe be exported as `help` builtin "cards", either as inline
  text, or a URL to online HTML.  A card may also have a URL to POSIX or bash
  docs.

### Directory Structures

The source code is simply a tree of Markdown files:

    doc/
      release-index.md     # /release/$VERSION/

      index.md             # All Docs on Oils, /release/$VERSION/doc/
      getting-started.md
      ...

      ref/
        index.md           # this page, the Oils Reference
        toc-osh.md       # link to OSH topics
        toc-ysh.md       # link to YSH topics
        toc-data.md

        chap-cmd-lang.md   # chapter on the command language
        ...


And the URLs basically mirror the source code:

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
          ...

You can link to topics with internal anchors:

- [chap-option.html#parse_at](chap-option.html#parse_at)
- [chap-builtin-cmd.html#compgen](chap-builtin-cmd.html#compgen)
