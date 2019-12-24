Lazy, Lossless Lexing Libraries
===============================

Right now we're using this Python code to process HTML in Oil docs.  Logically,
the doc pipeline looks like:

    Hand-written Markdown with embedded HTML --> cmark (CommonMark) -->
    HTML --> filter using lazy lexing -->
    HTML --> filter using lazy lexing -->
    ...
    Final HTML

Eventually it would be nice to expand this API design to more formats and make
it available to Oil language users.

## Why?

- To report good parse errors with location info
- To use like `sed` on HTML
- To minimize allocations, i.e. don't construct a DOM, and don't even construct
  substrings
- So we don't "lose the stack", unlike callback-based parsing
  - We get an iterator of events/spans
- A layer to build a "lossless syntax tree" on top of.

## HTML

HTML has two levels:

1. The `<>` structure, i.e. tags, the DOCTYPE declaration, comments, and processing
   instructions
2. The `name="value"` attributes inside start tags (and self-closing tags)

## TSV2

- This format is **designed** to be read line-by-line (unlike CSV).
- You can skip to any column, and optionally decode the field into an Bool,
  Int, Float, or Str.

## JSON

- py-yajl is event-based, but not lazy.  And it's a parser, not a lexer.
- We could LEX `{}` and `[] and `""` `\` in the first step.  This is lexing and
  not parsing.


## Links

- [pulldown-cmark][].  This is called a "pull parser" in reference to the *XML
  Pull Parsing* API at <http://xmlpull.org>.  However I would call this a
  *lexer* and not a *parser*.
  - Hm I think this indicates a need for **lossless** lexers as well?
    https://github.com/Byron/pulldown-cmark-to-cmark/blob/master/src/fmt.rs
  - It appears to be used in mdbook

[pulldown-cmark]: https://github.com/raphlinus/pulldown-cmark


