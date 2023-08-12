Doctools
========

Tools we use to generate the [Oils documentation](../doc/).  Some of this code
is used to build the [the blog](//www.oilshell.org/blog/) as well.

See [doc/doc-toolchain.md](../doc/doc-toolchain.md) for details.

- `cmark.py`: Our wrapper around CommonMark.
- `html_head.py`: Common HTML fragments.
- `oil_doc.py`: HTML filters.
- `split_doc.py`: Split "front matter" from Markdown.
- `make_help.py`: For `doc/ref/index-{osh,ysh}.md`.

