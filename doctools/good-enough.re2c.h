#ifndef GOOD_ENOUGH_H
#define GOOD_ENOUGH_H

enum class Id {
  Comm,
  WS,
  Preproc,  // for C++

  Name,  // foo

  Str,  // "" and Python r""
        // '' and Python r''
        // ''' """

  // Hm I guess we also need r''' and """ ?

  Other,  // any other text
  Unknown,

  // For C++ block structure
  LBrace, RBrace,

  // These are special zero-width tokens for Python
  Indent, Dedent,
  // Maintain our own stack!
  // https://stackoverflow.com/questions/40960123/how-exactly-a-dedent-token-is-generated-in-python
};

struct Token {
  Id kind;
  int end_col;
};

enum class py_mode_e {
  Outer,    // default
  MultiSQ,  // inside '''
  MultiDQ,  // inside """
};

enum class cpp_mode_e {
  Outer,   // default
  Comm,    // inside /* */ comment
  RawStr,  // R"zz(string literal)zz"
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

// Returns whether EOL was hit
template <>
bool Matcher<cpp_mode_e>::Match(Lexer<cpp_mode_e>* lexer, Token* tok) {
  const char* p = lexer->p_current;  // mutated by re2c
  const char* YYMARKER = p;
  // const char* YYCTXMARKER = p;  // needed for re2c lookahead operator '/'

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

        "/" "*"                { TOK_MODE(Id::Comm, cpp_mode_e::Comm); }

        "R" ["] "("            { TOK_MODE(Id::Str, cpp_mode_e::RawStr); }

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

#endif  // GOOD_ENOUGH_H
