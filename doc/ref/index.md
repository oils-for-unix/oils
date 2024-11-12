---
title: Oils Reference
all_docs_url: ..
css_files: ../../web/base.css ../../web/manual.css ../../web/ref-index.css
default_highlighter: oils-sh
preserve_anchor_case: yes
---

<div class="doc-ref-header">

**Oils Reference** &mdash;
[OSH](toc-osh.html) | [YSH](toc-ysh.html) | [Data Notation](toc-data.html)

</div>

<style>
  .highlight {
      background-color: #eee;
      padding-top: 0.1em;
      padding-bottom: 0.1em;
      padding-left: 1em;
      padding-right: 1em;
      /*
      font-size: 1.2em;
      */
  }
</style>

This reference has **three** tables of contents.  They link to topics within 15
chapters.

<span class="in-progress">(in progress)</span>

<div class="highlight">

[**Data Notation Table of Contents**](toc-data.html)

</div>

1. [JSON / J8 Notation](chap-j8.html)
1. [Errors](chap-errors.html)

<div class="highlight">

[**OSH Table of Contents**](toc-osh.html) - Compatible

[**YSH Table of Contents**](toc-ysh.html) - New and Powerful

</div>

3. [Types and Methods](chap-type-method.html)
1. [Builtin Functions](chap-builtin-func.html)
1. [Builtin Commands](chap-builtin-cmd.html)
1. [Front End](chap-front-end.html)
1. [Command Language](chap-cmd-lang.html)
1. [Standard Library](chap-stdlib.html)
1. [OSH Assignment](chap-osh-assign.html)
1. [YSH Command Language Keywords](chap-ysh-cmd.html)
1. [Word Language](chap-word-lang.html)
1. [YSH Expression Language](chap-expr-lang.html)
1. [Mini Languages](chap-mini-lang.html)
1. [Global Shell Options](chap-option.html)
1. [Special Variables](chap-special-var.html)
1. [Plugins and Hooks](chap-plugin.html)

<div class="highlight">

[**Index**](chap-index.html) - resolves topic name conflicts

</div>

[Topics By Feature](feature-index.html) - topics for modules, env vars, etc.


## `help` command

When you type [`help`][help] in OSH or YSH, it shows a URL to this reference,
or text extracted from it.

[help]: chap-builtin-cmd.html#help

## About

[The source files]($oils-src:doc/) for this reference are in Markdown:

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

The URLs mirror the source, with minor differences:

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
