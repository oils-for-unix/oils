---
in_progress: yes
default_highlighter: oil-sh
---

Examples of HTML Plugins
========================

This file is essentially a unit test for [doctools/oil_doc.py]($oil-src), which
contains all the HTML plugins.

Related: [How We Build Oil's Documentation](doc-toolchain.html).

<div id="toc">
</div>

## Link Shortcuts with `$`

- `$xref`: [bash]($xref)
- `$blog-tag`: [oil-release]($blog-tag)
- `$oil-src`: [INSTALL.txt]($oil-src), [INSTALL.txt]($oil-src:INSTALL.txt)
- `$blog-code-src`: [interactive-shell/README.md]($blog-code-src)
- `$issue`: [issue 11]($issue:11)
- `$oil-commit`: [this commit]($oil-commit:a1dad10d53b1fb94a164888d9ec277249ae98b58)

## Syntax Highlighting Specified In Front matter

If every `pre` block in a document needs the same higlighter, you can specify
it in the front matter like this:

    ---
    default_highlighter: oil-sh
    ---

    My Title
    ========

Right now we only allow `oil-sh`, which is a generic formatter that works for
both shell and Oil code (detail: it's the same as `sh-prompt` for now).  This
is what we use in [idioms.html](idioms.html) and [known
differences](known-differences.html).

## Syntax Highlighting With Fenced Code Blocks

### sh-prompt

```sh-prompt
$ echo hi   # comment
hi
```

### Pygments

```python
x = 42
print(x, file=sys.stderr)
```

### Plugins We Should Have

- Side-by-side sh and Oil
- Side-by-side PCRE and Eggex
- sh-session - How to replace the data?

A shell session could look like this:

<div shell="sh">

```
$ echo one
$ echo two
```

</div>

Embeddings:

- Embed Image Preview of Web Page?
- Embed Github Commit?
- Graphviz
  - LaTeX (although I don't really use it)

