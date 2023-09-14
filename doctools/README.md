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

## Idea for Minimal Comment/String/Def/Use Lexers

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

### Design Question

- can they be made incremental?
  - run on every keystroke?  Supposedly IntelliJ does that.
  - <https://www.jetbrains.com/help/resharper/sdk/ImplementingLexers.html#strongly-typed-lexers>
- but if you reuse Python's lexer, it's probably not incremental
  - see Python's tokenize.py


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
  - preprocessor `#if`
  - `class` declarations, with method declarations
  - function declarations (prototypes)
    - these are a bit hard - do they require parsing?
  - function and method definition
    - including templates?
  - multi-line strings in generated code

- ASDL
  - # comments
  - I guess every single type can have a line number
    - it shouldn't jump to Python file
    - `value_e.Str` and `value.Str` and `value_t` can jump to the right
      definition
