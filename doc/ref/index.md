---
in_progress: yes
default_highlighter: oil-sh
---

Oils Reference
=============


<div id="toc">
</div>

## Online HTML

This reference has N chapters:

1. [Front End](chap-front-end.html)
1. [Command Language](TODO)
1. ...
1. [Data Languages](chap-data-lang.html)

Which are linked from these indices:

- [OSH Reference Index](../osh-help-topics.html)
- [YSH Reference Index](../ysh-help-topics.html)

The idea is that you can use OSH by itself, YSH by itself, or upgrade OSH to
YSH.

Or go back to [All Oils Documentation](../index.html).


## `help` builtin command

When you type `help` in OSH or YSH, the command shows some of this material,
and prints hyperlinks to it.

## Directory Structures

### Source Code

    doc/  # all docs
      index.md  # index of docs
      getting-started.md
      ...

      ref/                    # the reference
        index.md              # this page
        chap-command-lang.md  # chapter
        ...

        osh-index.md          # TODO
        ysh-index.md          # TODO


### URLs

URLs mirror the source code:

    /release/$VERSION/doc/
      index.html
      getting-started.html
      ...

      ref/
        index.html
        chap-command-lang.html
        osh-index.html
        ysh-index.html

With internal anchors:

    ref/chap-option.html#strict_errexit

    ref/chap-builtin.html#compgen

## TODO

- Later: alphabetical list of options

### Link Shortcuts For Writing Docs

- ($command-lang:for)
- ($option:strict_errexit)
- ($builtin:compgen)

Or maybe:

- ($ref-c:for)
- ($ref-opt:strict_errexit)
- ($ref-builtin:compgen)
- ($ref-word:brace)

### Multiple headings without messing up HTML?

Like say you want all the `[[` language stuff together, and you want to create
a link, but not explain it all.

