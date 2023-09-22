Doctools
========

Tools we use to generate the [Oils documentation](../doc/).  Some of this code
is used to build the [the blog](//www.oilshell.org/blog/) as well.

See [doc/doc-toolchain.md](../doc/doc-toolchain.md) for details.

Tools shared with the blog:

- `cmark.py`: Our wrapper around CommonMark.
- `spelling.py`: spell checker
- `split_doc.py`: Split "front matter" from Markdown.

More tools:

- `html_head.py`: Common HTML fragments.
- `oil_doc.py`: HTML filters.
- `help_gen.py`: For `doc/ref/index-{osh,ysh}.md`.

## Micro Syntax

- `src_tree.py` is a fast and minimal source viewer.
- It uses polyglot syntax analysis called "micro syntax".  See
  [micro-syntax.md](micro-syntax.md).

