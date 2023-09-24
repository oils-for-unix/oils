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

## TODO

Immediate:

- SLOC
  - add to index.html, with attrs
    - light grey monospace?
  - Subsumes these tools:
    - <https://github.com/AlDanial/cloc> - this is a 17K line Perl script!
    - <https://dwheeler.com/sloccount/> - no release since 2004 ?

- shell here doc fix
  - requires captures?
- Shell comment fix
- C preprocessor highlighting

- Maybe add language for `*.test.sh`
  - the `####` and `##` lines are special

src-tree:

- should README.md be inserted in index.html ?
  - probably, sourcehut has this too
  - use cmark
    - also use our TOC plugin
- line counts in metrics/source-code.sh could link to src-tree
  - combine the CI jobs
  - should use `micro_syntax --wc` to count SLOC
    - Also `micro_syntax` --print --format ansi
      - this is the default?

Later:

- Parsing, jump to definition


