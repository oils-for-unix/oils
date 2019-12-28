Lazy, Lossless Lexing Libraries
===============================

Right now we're using this Python code to process HTML in Oil docs.  Logically,
the doc pipeline looks like:

(Hand-written Markdown with embedded HTML) <br/>
&rarr; CommonMark renderer &rarr; <br/>
(HTML) <br/>
&rarr; Filter with lazy lexing &rarr; <br/>
(HTML) <br/>
&rarr; Filter with lazy lexing &rarr; <br/>
(HTML) <br/>
<br/>
*... repeat N times ...* <br/>
<br/>
(Final HTML) <br/>

Eventually it would be nice to expand this API design to more formats and make
it available to Oil language users.

<div id="toc">
</div>

## Why?

- To report good parse errors with location info
- To use like `sed` on HTML
- To minimize allocations, i.e. don't construct a DOM, and don't even construct
  substrings
- So we don't "lose the stack", unlike callback-based parsing
  - We get an iterator of events/spans
- A layer to build a "lossless syntax tree" on top of.

## Formats

### HTML

HTML has two levels:

1. The `<>` structure, i.e. tags, the DOCTYPE declaration, comments, and processing
   instructions
2. The `name="value"` attributes inside start tags (and self-closing tags)

### TSV2

- This format is **designed** to be read line-by-line (unlike CSV).
- You can skip to any column, and optionally decode the field into an Bool,
  Int, Float, or Str.

### JSON

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
- [simdjson][]: This pasrer is designed for extreme speed, and the  first stage
  of it "lazy" and uses integer indices.  (We're only trying to avoid
  allocation; we're not avoiding branches or using SIMD!  We also aim to
  transform the underlying data, not just parse it.)

[simdjson]: https://branchfree.org/2019/02/25/paper-parsing-gigabytes-of-json-per-second/

[pulldown-cmark]: https://github.com/raphlinus/pulldown-cmark

## Design Notes

### Lessons/Claims

- You can parse HTML quickly and correctly with regexes!  It has a simple
  syntax that's almost designed for this.
  - Key point: We're not parsing them **only** with regexes.
  - The parser is correct in the sense that its behavior on every input is
    fully-defined.  There are no buffer overflows on edge cases -- that's the
    magic of regexes and the corresponding state machines.  However it doesn't
    recognize every weird document on the web.  It recognizes something close
    to "well-formed XML" (but it's not XHTML.)
- Parsing with spans / integer positions is efficient, **composable**, and
  leads  to better **syntax errors**.
  - Example: spec test format parse errors aren't good.  Info is lost.
    Or ASDL parser?  I guess it has some line info.
- The API is easier to use than SAX because you're not losing the stack.
  (Previous transformations used Python's HTMLParser, which is a SAX API.)
- It's more efficient than a DOM API.  DOM allocates a lot and loses
  whitespace.  (Speed matters when rebuilding the whole site.  Each page has
  multiple stages.  It makes the code cleaner to do multiple quick passes, like
  a compiler.)
  - In many instances, you can MODIFY the HTML doc correctly without
    deserializing something.  For example, adding `<b>` tags around a line
    doesn't require unquoting and quoting `&gt;` within them.
- Preserving whitespace is useful because I want to use 'diff' to test
  correctness against the old pipeline.
- Python's `pat.match(s, start_pos, end_pos)` is very useful for efficient
  lexing.
  - TODO: Convert to re2c to see how it does.  Need YYLIMIT.
- TODO: Issue of non-greedy matches.
- TODO: Issue of unquoting and quoting (escaping).
- The triple backtick extension to Markdown (part of CommonMark) is useful.
  - Although it should generate arbitrary `<div name="val">` instead.  This
    allow natural plugins.  You can write `<div>` in Markdown, but it's
    annoying to manually escape `<` to `&gt;`, e.g. in graphviz or TeX.
  HTML is analgous to shell.  A web site is a directory tree of text files!
  - It's better than the Snip `-->` syntax, which didn't play well with syntax
    highlighting.
- Composable grammars: Is this the basis for Pulp?

### Open Problems

- Python generators (`yield`) make the code more natural, but that's not
  possible in C or C++.  (C++20 has coroutines though.)
  - Could write a compiler?  Would be an excuse to clean up the OPy or mycpp
    ASTs.
- Input handling in C/shell:
  - Unlike Python's regex engine, libc `regexec()` doesnt have an `end_pos`,
    requires `NUL` termination.
  - We're also using `re2c` this way.  Can se use `YYLIMIT`?
  - Simple solution: copy the subrange, or temporarily mutate the buffer (would
    cause copy-on-write)
  - Is there a zero-copytehre a 

### Comparisons

- mdbook (in Rust, using [pulldown-cmark][]).  Has Rust plugins.
- pandoc.  Supports many formats, not just HTML.  Has plugins that take an AST
  in JSON.  The AST represents pandoc-flavored Markdown.  pandoc differs from
  Markdown in that it discourages HTML extensions.
- ReStructuredText.  Sphinx has plugins.
  - https://www.sphinx-doc.org/en/master/usage/extensions/index.html
- XML Starlet (dormant, understands XPath and CSS Starlet)
- R's Sweave?
  - bookdown?
- Jupyter notebooks have code and data.  Do they have plugins?
- Are there tools in node.js?
  - https://stackoverflow.com/questions/6657216/why-doesnt-node-js-have-a-native-dom
  - jsdom?

## To Build On Top

- CSS selectors
- DOM

