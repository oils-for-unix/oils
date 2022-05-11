---
in_progress: yes
default_highlighter: oil-sh
---

Oil Reference
=============

Design:

- Online HTML
- Linked From 'help' builtin
- Supplants faq-doc.md
- Linked to from `{osh,oil}-topics.md` 
  - Do we need some kind of 'setvalue' HTML instruction there?
  - `<setvalue name=foo value="value" />`
- doc/ref might be better?

Table of contents / index:

- [Oil Topics](oil-topics.html)
- [OSH Topics](osh-topics.html)

<div id="toc">
</div>

## Two of Four Kinds of Docs

- Tutorial -- learning oriented
- How To -- task oriented
- Explanation -- design docs
- Reference

## Organization

### Directory Structure

    doc/
      ref/
        index.html          # this page
        command-lang.html   # reference page

      # design docs at the top level
      error-handling.html
      index.html            # narrative ot index of docs

### URLs

    /release/$VERSION/doc/ref/option.html#strict_errexit

    /release/$VERSION/doc/ref/builtin.html#compgen

These are h3 tags.

What about the h2 tags -- do we do anything with them?

- h2 tags:
  - OSH or Oil
  - Category of Builtin (Shell State, Child Process)
  - Category of Option

&nbsp;

- Later: alphabetical list of options

### Help

    help strict_errexit
    help compgen

They link directly
         
## List of Reference Documents

Note that h3 tags are the topics.

Union of `{osh,oil}-help-topics`


- ref-overview -- usage, config, startup
  - todo: change this into ref-usage?  Or just a non-reference document?

&nbsp;

- OSH
  - command-lang
  - assign
  - word-lang
  - other-sublang
  - builtins or builtin
  - option
  - env -- environment variables
  - special - special variables
  - plugin -- hooks for code
- Oil
  - expr-lang
  - enhanced
    - command-lang, word-lang, builtins, options
    - env, special
  - lib -- standard library functions

# OSH or Oil?

- TODO: Figure out good POSIX shell and bash resources.
  - Most of the reference will just link to them, at least at first.

- Some differences:
  - arithmetic is statically parsed
  - Extended globs cleaned up
  - Brace expansion affected by `shopt -s parse_brace`.


## TODO

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

### Refactor Docs

- Language
  - word-language -> ref/word-lang.md
  - command-language -> ref/command-lang.md

- Help Topics
  - osh-help-topics -> ref/osh-topics.md
  - oil-help-topics -> ref/oil-topics.md

- Help Body
  - osh-help.md -> ref/{builtin,option,...}.md
  - oil-help.md -> ref/{builtin,option,...}.md

- Index
  - doc/index.md   -- This needs some rewriting with the new reference.


## Related Links

- [Doc Overview](../index.html)
