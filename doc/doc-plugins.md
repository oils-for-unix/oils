---
in_progress: yes
default_highlighter: oil-sh
---

Examples of HTML Plugins
========================

This file is a sort of unit test for [doctools/]($oil-src).

<div id="toc">
</div>

## Link Shortcuts with `$`

- `$xref`: [bash]($xref)
- `$blog-tag`: [oil-release]($blog-tag)
- `$oil-src`: [INSTALL.txt]($oil-src), [INSTALL.txt]($oil-src:INSTALL.txt)
- `$blog-code-src`: [interactive-shell/README.md]($blog-code-src)
- `$issue`: [issue 11]($issue:11)
- `$oil-commit`: [this commit]($oil-commit:a1dad10d53b1fb94a164888d9ec277249ae98b58)


## Syntax Highlighting With Markdown Code Blocks

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

### `default_highlighter` in Front matter

`oil-sh` is a generic formatter that works for both shell and Oil code.  This
is what we use in [idioms.html](idioms.html).

No:

    pat='*.py'         # pattern stored in a string
    echo $pat          # implicit glob in shell

Yes:

    var pat = '*.py'   # Oil assignment
    echo @glob(pat)    # explicit

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

## Related Docs

- [doc-toolchain](doc-toolchain.html)
