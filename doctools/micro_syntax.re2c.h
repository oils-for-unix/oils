#ifndef MICRO_SYNTAX_H
#define MICRO_SYNTAX_H

#include <assert.h>
#include <string.h>  // strlen()

enum class Id {
  Comm,
  WS,
  Preproc,   // for C++
  Re2c,      // embedded in C++
  LineCont,  // backslash at end of line, for #define continuation

  // Zero-width token to detect #ifdef and Python INDENT/DEDENT
  StartLine,

  Name,  // Keyword or Identifier

  Str,  // "" and Python r""
        // '' and Python r''
        // ''' """

  HereBegin,  // for shell
  HereEnd,
  RawStrBegin,  // for C++ R"zzz(hello)zzz"

  // Hm I guess we also need r''' and """ ?

  Other,  // any other text
  Unknown,

  // For C++ block structure
  // Could be done in second pass after removing comments/strings?
  LBrace,
  RBrace,

  // These are special zero-width tokens for Python
  Indent,
  Dedent,
  // Maintain our own stack!
  // https://stackoverflow.com/questions/40960123/how-exactly-a-dedent-token-is-generated-in-python
};

struct Token {
  Token()
      : kind(Id::Unknown),
        end_col(0),
        submatch_start(nullptr),
        submatch_end(nullptr) {
  }
  Token(Id id, int end_col)
      : kind(id),
        end_col(end_col),
        submatch_start(nullptr),
        submatch_end(nullptr) {
  }

  Id kind;
  int end_col;
  const char* submatch_start;
  const char* submatch_end;
};

// Lexer and Matcher are specialized on py_mode_e, cpp_mode_e, ...

template <typename T>
class Lexer {
 public:
  Lexer(char* line) : line_(line), p_current(line), line_mode(T::Outer) {
  }

  void SetLine(char* line) {
    line_ = line;
    p_current = line;
  }

  const char* line_;
  const char* p_current;  // points into line
  T line_mode;            // current mode, starts with Outer
};

template <typename T>
class Matcher {
 public:
  // Returns whether EOL was hit.  Mutates lexer state, and fills in tok out
  // param.
  bool Match(Lexer<T>* lexer, Token* tok);
};

// Macros for semantic actions

#define TOK(k)   \
  tok->kind = k; \
  break;

#define TOK_MODE(k, m)  \
  tok->kind = k;        \
  lexer->line_mode = m; \
  break;

// Must call TOK*() after this
#define SUBMATCH(s, e)     \
  tok->submatch_start = s; \
  tok->submatch_end = e;

// Regex definitions shared between languages

/*!re2c
  re2c:yyfill:enable = 0;
  re2c:define:YYCTYPE = char;
  re2c:define:YYCURSOR = p;

  nul = [\x00];
  not_nul = [^\x00];

  // Whitespace is needed for SLOC, to tell if a line is entirely blank
  whitespace = [ \t\r\n]*;

  identifier = [_a-zA-Z][_a-zA-Z0-9]*;

  // Python and C++ have "" strings
  // C++ char literals are similar, e.g. '\''
  // We are not more precise

  sq_middle = ( [^\x00'\\] | "\\" not_nul )*;
  dq_middle = ( [^\x00"\\] | "\\" not_nul )*;

  sq_string = ['] sq_middle ['];
  dq_string = ["] dq_middle ["];

  // Shell and Python have # comments
  pound_comment        = "#" not_nul*;

  // YSH and Python have ''' """
  triple_sq = "'''";
  triple_dq = ["]["]["];
*/

enum class text_mode_e {
  Outer,  // default
};

// Returns whether EOL was hit
template <>
bool Matcher<text_mode_e>::Match(Lexer<text_mode_e>* lexer, Token* tok) {
  const char* p = lexer->p_current;  // mutated by re2c

  while (true) {
    /*!re2c
      nul                    { return true; }

                             // whitespace at start of line
      whitespace             { TOK(Id::WS); }

                             // This rule consumes trailing whitespace, but
                             // it's OK.  We're counting significant lines, not
                             // highlighting.
      [^\x00]+               { TOK(Id::Other); }

      *                      { TOK(Id::Other); }

    */
  }

  tok->end_col = p - lexer->line_;
  lexer->p_current = p;
  return false;
}

enum class asdl_mode_e {
  Outer,
};

// Returns whether EOL was hit
template <>
bool Matcher<asdl_mode_e>::Match(Lexer<asdl_mode_e>* lexer, Token* tok) {
  const char* p = lexer->p_current;  // mutated by re2c

  switch (lexer->line_mode) {
  case asdl_mode_e::Outer:
    while (true) {
      /*!re2c
        nul                    { return true; }

        whitespace             { TOK(Id::WS); }

        identifier             { TOK(Id::Name); }

        pound_comment          { TOK(Id::Comm); }

        // Not the start of a comment, identifier
        [^\x00#_a-zA-Z]+       { TOK(Id::Other); }

        // e.g. unclosed quote like "foo
        *                      { TOK(Id::Unknown); }

      */
    }
    break;
  }

  tok->end_col = p - lexer->line_;
  lexer->p_current = p;
  return false;
}

enum class py_mode_e {
  Outer,    // default
  MultiSQ,  // inside '''
  MultiDQ,  // inside """
};

// Returns whether EOL was hit
template <>
bool Matcher<py_mode_e>::Match(Lexer<py_mode_e>* lexer, Token* tok) {
  const char* p = lexer->p_current;  // mutated by re2c
  const char* YYMARKER = p;

  switch (lexer->line_mode) {
  case py_mode_e::Outer:
    while (true) {
      /*!re2c
        nul                    { return true; }

        whitespace             { TOK(Id::WS); }

        identifier             { TOK(Id::Name); }

        [r]? sq_string         { TOK(Id::Str); }
        [r]? dq_string         { TOK(Id::Str); }

        // optional raw prefix
        [r]? triple_sq         { TOK_MODE(Id::Str, py_mode_e::MultiSQ); }
        [r]? triple_dq         { TOK_MODE(Id::Str, py_mode_e::MultiDQ); }

        pound_comment          { TOK(Id::Comm); }

        // Not the start of a string, comment, identifier
        [^\x00"'#_a-zA-Z]+     { TOK(Id::Other); }

        // e.g. unclosed quote like "foo
        *                      { TOK(Id::Unknown); }

      */
    }
    break;

  case py_mode_e::MultiSQ:
    while (true) {
      /*!re2c
        nul       { return true; }

        triple_sq { TOK_MODE(Id::Str, py_mode_e::Outer); }

        [^\x00']* { TOK(Id::Str); }

        *         { TOK(Id::Str); }

      */
    }
    break;

  case py_mode_e::MultiDQ:
    while (true) {
      /*!re2c
        nul       { return true; }

        triple_dq { TOK_MODE(Id::Str, py_mode_e::Outer); }

        [^\x00"]* { TOK(Id::Str); }

        *         { TOK(Id::Str); }

      */
    }
    break;
  }

  tok->end_col = p - lexer->line_;
  lexer->p_current = p;
  return false;
}

enum class cpp_mode_e {
  Outer,   // default
  Comm,    // inside /* */ comment
  RawStr,  // R"zz(string literal)zz"
  Re2c,    // /* !re2c
};

// Returns whether EOL was hit
template <>
bool Matcher<cpp_mode_e>::Match(Lexer<cpp_mode_e>* lexer, Token* tok) {
  const char* p = lexer->p_current;  // mutated by re2c
  const char* YYMARKER = p;
  const char *s, *e;  // submatch extraction

  // Autogenerated tag variables used by the lexer to track tag values.
  /*!stags:re2c format = 'const char *@@;\n'; */

  switch (lexer->line_mode) {
  case cpp_mode_e::Outer:

    while (true) {
      /*!re2c
        nul                    { return true; }

        whitespace             { TOK(Id::WS); }

        "{"                    { TOK(Id::LBrace); }
        "}"                    { TOK(Id::RBrace); }

        identifier             { TOK(Id::Name); }

        // approximation for C++ char literals
        sq_string              { TOK(Id::Str); }
        dq_string              { TOK(Id::Str); }

        // Not the start of a string, comment, identifier
        [^\x00"'/_a-zA-Z{}]+   { TOK(Id::Other); }

        "//" not_nul*          { TOK(Id::Comm); }

        // Treat re2c as preprocessor block
        "/" "*!re2c"           { TOK_MODE(Id::Re2c, cpp_mode_e::Re2c); }

        "/" "*"                { TOK_MODE(Id::Comm, cpp_mode_e::Comm); }

        // Not sure what the rules are for R"zz(hello)zz".  Make it similar to
        // here docs.
        delim = [_a-zA-Z]*;

        "R" ["] @s delim @e "(" {
                                SUBMATCH(s, e);
                                TOK_MODE(Id::RawStrBegin, cpp_mode_e::RawStr);
                              }

        // e.g. unclosed quote like "foo
        *                      { TOK(Id::Unknown); }

      */
    }
    break;

  case cpp_mode_e::Comm:
    // Search until next */
    while (true) {
      /*!re2c
        nul       { return true; }

        "*" "/"   { TOK_MODE(Id::Comm, cpp_mode_e::Outer); }

        [^\x00*]* { TOK(Id::Comm); }

        *         { TOK(Id::Comm); }

      */
    }
    break;

  case cpp_mode_e::Re2c:
    // Search until next */
    while (true) {
      /*!re2c
        nul       { return true; }

        "*" "/"   { TOK_MODE(Id::Re2c, cpp_mode_e::Outer); }

        [^\x00*]* { TOK(Id::Re2c); }

        *         { TOK(Id::Re2c); }

      */
    }
    break;

  case cpp_mode_e::RawStr:
    // Search until next */
    while (true) {
      /*!re2c
        nul       { return true; }

        ")" ["]   { TOK_MODE(Id::Str, cpp_mode_e::Outer); }

        [^\x00)]* { TOK(Id::Str); }

        *         { TOK(Id::Str); }

      */
    }
    break;
  }

  tok->end_col = p - lexer->line_;
  lexer->p_current = p;
  return false;
}

class Hook {
 public:
  virtual bool IsPreprocessorLine(char* line, Token* tok) {
    return false;
  }
  virtual ~Hook() {
  }
};

enum class preproc {
  No,
  Yes,          // #define X 0
  YesContinue,  // #define X \ continuation
};

class CppHook : public Hook {
 public:
  // Problems:
  // - Testing a single line isn't enough.  We also have to look at line
  // continuations.
  // - Comments can appear at the end of the line

  virtual bool IsPreprocessorLine(char* line, Token* tok) {
    const char* p = line;  // mutated by re2c
    const char* YYMARKER = p;

    while (true) {
      /*!re2c
        nul            { return false; }

                       // e.g. #ifdef
        whitespace '#' not_nul* { break; }

        *              { return false; }

      */
    }
    tok->kind = Id::Preproc;
    tok->end_col = p - line;
    // Log("line '%s' END %d strlen %d", line, tok->end_col, strlen(line));
    return true;
  }
};

enum class R_mode_e {
  Outer,  // default

  SQ,  // inside multi-line ''
  DQ,  // inside multi-line ""
};

// Returns whether EOL was hit
template <>
bool Matcher<R_mode_e>::Match(Lexer<R_mode_e>* lexer, Token* tok) {
  const char* p = lexer->p_current;  // mutated by re2c
  const char* YYMARKER = p;

  switch (lexer->line_mode) {
  case R_mode_e::Outer:
    while (true) {
      /*!re2c
        nul                    { return true; }

        whitespace             { TOK(Id::WS); }

        pound_comment          { TOK(Id::Comm); }

        identifier             { TOK(Id::Name); }

        // Not the start of a string, escaped, comment, identifier
        [^\x00"'#_a-zA-Z]+     { TOK(Id::Other); }

        [']                    { TOK_MODE(Id::Str, R_mode_e::SQ); }
        ["]                    { TOK_MODE(Id::Str, R_mode_e::DQ); }

        *                      { TOK(Id::Unknown); }

      */
    }
    break;

  case R_mode_e::SQ:
    while (true) {
      /*!re2c
        nul       { return true; }

        [']       { TOK_MODE(Id::Str, R_mode_e::Outer); }

        sq_middle { TOK(Id::Str); }

        *         { TOK(Id::Str); }

      */
    }
    break;

  case R_mode_e::DQ:
    while (true) {
      /*!re2c
        nul       { return true; }

        ["]       { TOK_MODE(Id::Str, R_mode_e::Outer); }

        dq_middle { TOK(Id::Str); }

        *         { TOK(Id::Str); }

      */
    }
    break;
  }

  tok->end_col = p - lexer->line_;
  lexer->p_current = p;
  return false;
}

// Problem with shell: nested double quotes!!!
// We probably discourage this in YSH

enum class sh_mode_e {
  Outer,  // default

  SQ,        // inside multi-line ''
  DollarSQ,  // inside multi-line $''
  DQ,        // inside multi-line ""

  HereSQ,  // inside <<'EOF' or <<\EOF
  HereDQ,  // inside <<EOF

  // We could have a separate thing for this
  YshSQ,  // inside '''
  YshDQ,  // inside """
  YshJ,   // inside j"""
};

// Returns whether EOL was hit

// Submatch docs:
//   https://re2c.org/manual/manual_c.html#submatch-extraction

template <>
bool Matcher<sh_mode_e>::Match(Lexer<sh_mode_e>* lexer, Token* tok) {
  const char* p = lexer->p_current;  // mutated by re2c
  const char* YYMARKER = p;
  const char *s, *e;  // submatch extraction

  // Autogenerated tag variables used by the lexer to track tag values.
  /*!stags:re2c format = 'const char *@@;\n'; */

  switch (lexer->line_mode) {
  case sh_mode_e::Outer:
    while (true) {
      /*!re2c
        nul                    { return true; }

        whitespace             { TOK(Id::WS); }

        pound_comment          { TOK(Id::Comm); }

        // not that relevant for shell
        identifier             { TOK(Id::Name); }

        // Not the start of a string, escaped, comment, identifier, here doc
        [^\x00"'$#_a-zA-Z\\<]+  { TOK(Id::Other); }

                               // echo is like a string
        "\\" .                 { TOK(Id::Str); }

        [']                    { TOK_MODE(Id::Str, sh_mode_e::SQ); }
        ["]                    { TOK_MODE(Id::Str, sh_mode_e::DQ); }
        "$'"                   { TOK_MODE(Id::Str, sh_mode_e::DollarSQ); }

        // <<- is another syntax
        here_op    = "<<" [-]? [ \t]*;
        h_delim    = [_a-zA-Z]+;

        // unquoted or quoted
        here_op @s      h_delim @e     { SUBMATCH(s, e); TOK(Id::HereBegin); }
        here_op [']  @s h_delim @e ['] { SUBMATCH(s, e); TOK(Id::HereBegin); }
        here_op ["]  @s h_delim @e ["] { SUBMATCH(s, e); TOK(Id::HereBegin); }
        here_op "\\" @s h_delim @e     { SUBMATCH(s, e); TOK(Id::HereBegin); }

                               // NOT Unknown, as in Python
        *                      { TOK(Id::Other); }

      */
    }
    break;

  case sh_mode_e::SQ:
    // Search until next ' unconditionally
    while (true) {
      /*!re2c
        nul       { return true; }

        [']       { TOK_MODE(Id::Str, sh_mode_e::Outer); }

        [^\x00']* { TOK(Id::Str); }

        *         { TOK(Id::Str); }

      */
    }
    break;

  case sh_mode_e::DQ:
    // Search until next " that's not preceded by "
    while (true) {
      /*!re2c
        nul       { return true; }

        ["]       { TOK_MODE(Id::Str, sh_mode_e::Outer); }

        dq_middle { TOK(Id::Str); }

        *         { TOK(Id::Str); }

      */
    }
    break;

  case sh_mode_e::DollarSQ:
    // Search until next ' that's not preceded by "
    while (true) {
      /*!re2c
        nul       { return true; }

        [']       { TOK_MODE(Id::Str, sh_mode_e::Outer); }

        sq_middle { TOK(Id::Str); }

        *         { TOK(Id::Str); }

      */
    }
    break;
  case sh_mode_e::HereSQ:
  case sh_mode_e::HereDQ:
  case sh_mode_e::YshSQ:
  case sh_mode_e::YshDQ:
  case sh_mode_e::YshJ:
    assert(0);
  }

  tok->end_col = p - lexer->line_;
  lexer->p_current = p;
  return false;
}

// TODO:
// - Lua / Rust-style multi-line strings, with matching delimiters e.g. r###"
//   - same as C++ raw string, I think
//   - similar to here docs, but less complex
//
// Inherent problems with "micro segmentation:
//
// - Nested double quotes in shell.  echo "hi ${name:-"default"}"
//   - This means that lexing is **dependent on** parsing: does the second
//   double quote **close** the first one, or does it start a nested string?
//   - lexing is non-recursive, parsing is recursive

// Shell Comments depend on operator chars
// echo one # comment
// echo $(( 16#ff ))'

#endif  // MICRO_SYNTAX_H
