---
default_highlighter: oil-sh
---

Oils Reference
=============

A guide to everything in Oils (in progress).

Go back to [All Docs on Oils](../index.html) for design docs and tutorials.

<div id="toc">
</div>

## Online HTML

Start from one of these indexes:

- [Index of OSH Topics](index-osh.html)
- [Index of YSH Topics](index-ysh.html)
- [Index of Data Topics](index-data.html)

They link to **topics** within these 13 chapters:

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
1. [Data Languages](chap-data-lang.html)

The idea is that you can use OSH by itself, YSH by itself, or upgrade OSH to
YSH.

## `help` builtin command

When you type `help` in OSH or YSH, the command shows some of this material,
and prints hyperlinks to it.

## Directory Structures

How are the docs organized?  The source code is simply a tree of Markdown
files:

    doc/
      index.md             # All Docs on Oils
      getting-started.md
      ...

      ref/
        index.md           # this page, the Oils Reference
        index-osh.md       # link to OSH topics
        index-ysh.md       # link to YSH topics

        chap-cmd-lang.md   # chapter on the command language
        ...
        osh.txt            # Plain text help "card"
        ysh.txt


And the URLs mirror the source code:

    /release/$VERSION/doc/
      index.html
      getting-started.html
      ...

      ref/
        index.html
        index-osh.html
        index-ysh.html

        chap-cmd-lang.html
        ...

You can link to topics with internal anchors:

- [chap-option.html#parse_at](chap-option.html#parse_at)
- [chap-builtin-cmd.html#compgen](chap-builtin-cmd.html#compgen)
