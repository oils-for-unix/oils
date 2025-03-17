Micro Syntax
============

Lightweight, polyglot syntax analysis.

Motivations:

- YSH needs syntax highlighters, and this code is a GUIDE to writing one.
  - The lexer should run on its own.  Generated parsers like TreeSitter
    require such a lexer.  In contrast to recursive descent, grammars can't
    specify lexer modes.

Our own dev tools:

- The Github source viewer is too slow.  We want to publish a fast version of
  our source code to view.
  - Our docs need to link to link source code.
  - Github source viewing APPROXIMATE anyway, because they don't execute your
    build; they don't have ENV.  They would have to "solve the halting problem"
    - So let's be FAST and approximate, not SLOW and approximate.

- Multiple attempts at this polyglot problem
  - github/semantic in Haskell
  - facebook/pfff -- semgrep heritage

- Aesthetics
  - I don't like noisy keyword highlighting.  Just comments and string
    literals looks surprisingly good.
  - Can use this on the blog too.
- HTML equivalent of showsh, showpy -- quickly jump to definitions
- I think I can generate better ctags than `devtools/ctags.sh`!  It's a simple
  format.
- I realized that "sloccount" is the same problem as syntax highlighting --
  you exclude comments, whitespace, and lines with only string literals.
  - sloccount is a huge Perl codebase, and we can stop depending on that.

- could be used to spell check comments?
  - look at the tool sed in the PR from Martin

Other:

- Because re2c is fun, and I wanted to experiment with writing it directly.
- Ideas
  - use this on your blog?
  - embed in a text editor?  Can it be incremental?

## Related

Positively inspired:

- uchex static analysis paper (2016)
- ctags

(and re2c itself)

Also see my comment on: Rust is the future of JavaScript infrastructure -- you
need Rust/C++ semantics to be fast.  We're using C++ because it's already in
our codebase, but Rust is probably better for collaboration.  (I trust myself
to use ASAN and develop with it on, but I don't want to review other people's
code who haven't used ASAN :-P )


Negatively inspired:

- Github source viewer
- tree-sitter-bash, and to some degree seeing semgrep using tree-sitter-bash
- huge amount of Perl code in sloccount
- to some extent, also ctags -- low-level C code

## TODO

- `--long-flags` in C++, probably
- Export to parser combinators
  - Export to ctags

## Algorithm Notes

Two pass algorithm with StartLine:

First pass:

- Lexer modes with no lookahead or lookbehind
- This is "Pre-structuring", as we do in Oils!

Second pass:

- Python - StartLine WS -> Indent/Dedent
- C++ - StartLine MaybePreproc LineCont -> preprocessor

Q: Are here docs first pass or second pass?

TODO:

- C++
  - arbitrary raw strings R"zZXx(
- Shell
  - YSH multi-line strings

Parsing:

- Name tokens should also have contents?
  - at least for Python and C++
  - shell: we want these at start of line:
    - proc X, func X, f()
    - not echo proc X
- Some kind of parser combinator library to match definitions
  - like showpy, showsh, but you can export to HTML with line numbers, and
    anchor

### Design Question

- can they be made incremental?
  - run on every keystroke?  Supposedly IntelliJ does that.
  - <https://www.jetbrains.com/help/resharper/sdk/ImplementingLexers.html#strongly-typed-lexers>
- but if you reuse Python's lexer, it's probably not incremental
  - see Python's tokenize.py

### Lexing Model: micro-syntax vs. Oils `data_lang/`

- micro-syntax is line-based; Oils is file-based
- micro-syntax is for syntax highlighting and may not capture everything; Oils
  has to capture everything
  - micro-syntax may produce multiple tokens for `/* */`, because it doesn't matter for syntax hihlighting.
  - In Oils we want to produce one token for `<!-- -->` and `<? ?>` etc.
- micro-syntax doesn't have errors except for Id::Unknown
  - Oils has hard lex errors (and parse errors)
- micro-syntax uses raw re2c; Oils has `frontend/match`
- micro-syntax has the model of a "lexer mode" that runs on its own, plus
  - `hook->TryPreprocess()`
  - here docs
  - delimited strings
  - FixShellComments()

Not sure we can unify them, but HTM8 was a useful experiment.

## Notes

Why not reuse off-the-shelf tools?

1. Because we are a POLYGLOT codebase.
1. Because we care about speed.  (e.g. Github's source viewer is super slow
   now!)
   - and I think we can do a little bit better that `devtools/ctags.sh`.
   - That is, we can generate a better tags file.

We output 2 things:

1. A list of spans
   - type. TODO: see Vim and textmate types: comment, string, definition
   - location: line, begin:end col
2. A list of "OTAGS"
   - SYMBOL FILENAME LINE
   - generate ctags from this
   - generate HTML or JSON from this
     - recall Woboq code browser was entirely static, in C++
     - they used `compile_commands.json`

- Leaving out VARIABLES, because those are local.
  - I think the 'use' lexer is dynamic, sort of like it is in Vim.
  - 'find uses' can be approximated with `grep -n`?  I think that simplifies
    things a lot
    - it's a good practice for code to be greppable

### Languages

Note: All our source code, and generated Python and C++ code, should be lexable
like this.  Put it all in `src-tree.wwz`.

- Shell:
  - comments
  - `'' "" $''` string literals
  - here docs
  - functions
    - understand `{ }` matching?

- YSH
  - strings `j""`
  - multiline strings `''' """ j"""`
  - proc def
  - func def

- Python
  - # comments
  - `"" ''` strings
  - multi-line strings
  - these may require INDENT/DEDENT tokens
    - class
    - def
  - does it understand `state.Mem`?  Probably
    - vim only understands `Mem` though.  We might be able to convince it to.
  - Reference:
    - We may also need a fast whole-file lexer for `var_name` and `package.Var`,
      which does dynamic lookup.
   
- C++
  - `//` comments
  - `/* */` comments
  - preprocessor `#if #define`
  - multi-line strings in generated code
  - Parsing:
    - `class` declarations, with method declarations
    - function declarations (prototypes)
      - these are a bit hard - do they require parsing?
    - function and method definition
      - including templates?

- ASDL
  - # comments
  - I guess every single type can have a line number
    - it shouldn't jump to Python file
    - `value_e.Str` and `value.Str` and `value_t` can jump to the right
      definition

- R   # comments and "\n" strings

### More languages

- JS  // and `/* */` and `` for templates
- CSS `/* */`
  - there's no real symbols to extract here
- YAML - `#` and strings
  - there's no parsing, just highlighting
- Markdown 
  - the headings would be nice -- other stuff is more complex
  - the `==` and `--` styles require lookahead; they're not line-based
  - so it needs a different model than `ScanOne()`

- spec tests
