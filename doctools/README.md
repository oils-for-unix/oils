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

- Recast as TSV-Netstring, which is different than TSV8
  - select one of these cols:
    - Path, HTML, `num_lines`, `num_sig_lines`, and I guess ANSI?
      - line/tokens binary?  You have line number and so forth
  - 3:foo\t 5:foo\n  # last cell has to end with newline ?
    - preserves wc -l when data has no newlines?
    - or is this too easily confused with TSV8 itself?  You don't want it to be valid TSV8?
    - it can start out as text
    - !tsv8 Str
    - !type
    - !nets-row ?
  - another thing you can do is have a prefix of cells
    - netstring is 3:foo,
    - prefix is 5; 3:foo,
      - that's a command to read 5 net strings I guess?

- Parsing, jump to definition


