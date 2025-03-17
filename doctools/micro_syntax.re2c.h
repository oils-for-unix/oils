#ifndef MICRO_SYNTAX_H
#define MICRO_SYNTAX_H

#include <assert.h>
#include <string.h>  // strlen()

#include <vector>

enum class Id {
  // Common to nearly all languages
  Comm,
  MaybeComment,  // for shell, resolved in a fix-up pass

  WS,

  Name,  // Keyword or Identifier
  Str,   // "" and Python r""
         // '' and Python r''
         // ''' """
         // body of here docs

  Other,  // any other text
  Unknown,

  // C++
  DelimStrBegin,  // for C++ R"zzz(hello)zzz"
  DelimStrEnd,
  Re2c,  // re2c code block

  MaybePreproc,    // resolved to PreprocCommand/PreprocOther in fix-up pass
  PreprocCommand,  // resolved #define
  PreprocOther,    // any other text
  LineCont,        // backslash at end of line, for #define continuation

  // Braces for C++ block structure. Could be done in second pass after
  // removing comments/strings?
  LBrace,
  RBrace,

  // Shell
  HereBegin,
  HereEnd,

  // Html
  TagNameLeft,   // start <a> or <br id=foo />
  SelfClose,     // />
  TagNameRight,  // >
  EndTag,        // </a>
  CharEscape,    // &amp;
  AttrName,      // foo=
  BadAmpersand,
  BadLessThan,
  BadGreaterThan,
  // Reused: Str Other

  // Zero-width token to detect #ifdef and Python INDENT/DEDENT
  // StartLine,

  // These are special zero-width tokens for Python
  // Indent,
  // Dedent,
  // Maintain our own stack!
  // https://stackoverflow.com/questions/40960123/how-exactly-a-dedent-token-is-generated-in-python
};

struct Token {
  Token() : id(Id::Unknown), end_col(0), submatch_start(0), submatch_end(0) {
  }
  Token(Id id, int end_col)
      : id(id), end_col(end_col), submatch_start(0), submatch_end(0) {
  }

  Id id;
  int end_col;         // offset from char* line
  int submatch_start;  // ditto
  int submatch_end;    // ditto
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

#define TOK(k) \
  tok->id = k; \
  break;

#define TOK_MODE(k, m)  \
  tok->id = k;          \
  lexer->line_mode = m; \
  break;

// Must call TOK*() after this
#define SUBMATCH(s, e)                    \
  tok->submatch_start = s - lexer->line_; \
  tok->submatch_end = e - lexer->line_;

// Regex definitions shared between languages

/*!re2c
  re2c:yyfill:enable = 0;
  re2c:define:YYCTYPE = char;
  re2c:define:YYCURSOR = p;

  nul = [\x00];
  not_nul = [^\x00];

  // Whitespace is needed for SLOC, to tell if a line is entirely blank
  whitespace = [ \t\r\n]*;
  space_required = [ \t\r\n]+;

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
  Outer,     // default
  Comm,      // inside /* */ comment
  DelimStr,  // R"zz(string literal)zz"
  Re2c,      // /* !re2c
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
        nul                     { return true; }

        whitespace              { TOK(Id::WS); }

        "{"                     { TOK(Id::LBrace); }
        "}"                     { TOK(Id::RBrace); }

        identifier              { TOK(Id::Name); }

        // approximation for C++ char literals
        sq_string               { TOK(Id::Str); }
        dq_string               { TOK(Id::Str); }

        // Not the start of a string, comment, identifier
        [^\x00"'/_a-zA-Z{}]+    { TOK(Id::Other); }

        "//" not_nul*           { TOK(Id::Comm); }

        // Treat re2c as preprocessor block
        "/" "*!re2c"            { TOK_MODE(Id::Re2c, cpp_mode_e::Re2c); }

        "/" "*"                 { TOK_MODE(Id::Comm, cpp_mode_e::Comm); }

        // Not sure what the rules are for R"zz(hello)zz".  Make it similar to
        // here docs.
        cpp_delim_str = [_a-zA-Z]*;

        "R" ["] @s cpp_delim_str @e "(" {
          SUBMATCH(s, e);
          TOK_MODE(Id::DelimStrBegin, cpp_mode_e::DelimStr);
        }

        // e.g. unclosed quote like "foo
        *                       { TOK(Id::Unknown); }

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

  case cpp_mode_e::DelimStr:
    // Search until next */
    while (true) {
      /*!re2c
        nul       { return true; }

        ")" @s cpp_delim_str @e ["] {
          SUBMATCH(s, e);
          TOK(Id::DelimStrEnd);

          // Caller is responsible for checking the extracted delimiter, and
          // setting mode back to Cpp::Outer!
        }

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
  // Return true if this is a preprocessor line, and fill in tokens
  // Caller should check last token for whether there is a continuation line.
  virtual void TryPreprocess(char* line, std::vector<Token>* tokens) {
    ;
  }
  virtual ~Hook() {
  }
};

enum class pp_mode_e {
  Outer,
};

// Returns whether EOL was hit
template <>
bool Matcher<pp_mode_e>::Match(Lexer<pp_mode_e>* lexer, Token* tok) {
  const char* p = lexer->p_current;  // mutated by re2c
  const char* YYMARKER = p;

  switch (lexer->line_mode) {
  case pp_mode_e::Outer:
    while (true) {
      /*!re2c
        nul                    { return true; }

                               // Resolved in fix-up pass
                               // #include #define etc. only valid at the
                               // beginning
        [ \t]* "#" [a-z]+      { TOK(Id::MaybePreproc); }

                               // C-style comments can end these lines
        "//" not_nul*          { TOK(Id::Comm); }

        [\\] [\n]              { TOK(Id::LineCont); }

                               // A line could be all whitespace, then \ at the
                               // end.  And it's not significant
        whitespace             { TOK(Id::WS); }

                               // Not the start of a command, comment, or line
                               // continuation
        [^\x00#/\\]+           { TOK(Id::PreprocOther); }

        *                      { TOK(Id::PreprocOther); }

      */
    }
    break;
  }

  tok->end_col = p - lexer->line_;
  lexer->p_current = p;
  return false;
}

class CppHook : public Hook {
 public:
  virtual void TryPreprocess(char* line, std::vector<Token>* tokens);
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

                               // Resolved in fix-up pass
        pound_comment          { TOK(Id::MaybeComment); }

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
        h_delim    = [_a-zA-Z][_a-zA-Z0-9]*;

        // unquoted or quoted
        here_op      @s h_delim @e     { SUBMATCH(s, e); TOK(Id::HereBegin); }
        here_op [']  @s h_delim @e ['] { SUBMATCH(s, e); TOK(Id::HereBegin); }
        here_op ["]  @s h_delim @e ["] { SUBMATCH(s, e); TOK(Id::HereBegin); }
        here_op "\\" @s h_delim @e     { SUBMATCH(s, e); TOK(Id::HereBegin); }

                                       // NOT Unknown, as in Python
        *                              { TOK(Id::Other); }

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
  case sh_mode_e::YshSQ:
  case sh_mode_e::YshDQ:
  case sh_mode_e::YshJ:
    assert(0);
  }

  tok->end_col = p - lexer->line_;
  lexer->p_current = p;
  return false;
}

enum class html_mode_e {
  Outer,          // <NAME enters the TAG state
  AttrName,       // NAME="  NAME='  NAME=  NAME
  AttrValue,      // NAME="  NAME='  NAME=
  SQ,             // respects Chars, can contain "
  DQ,             // respects Chars, can contain '
  Comm,           // <!-- -->
  Preprocessing,  // <? ?>
  CData,          // <![CDATA[ x  ]]>
  HtmlCData,      // <script> <style>
};

// LeftStartTag -> RightStartTag  <a href=/ >
// LeftStartTag -> SelfClose      <br id=foo />

// Returns whether EOL was hit
template <>
bool Matcher<html_mode_e>::Match(Lexer<html_mode_e>* lexer, Token* tok) {
  const char* p = lexer->p_current;  // mutated by re2c
  const char* YYMARKER = p;

  /*!re2c
    // Common definitions

                // Like _NAME_RE in HTM8
    name      = [a-zA-Z][a-zA-Z0-9:_-]* ;

                // TODO: check this pattern
    char_name = "&"   [a-zA-Z][a-zA-Z0-9]* ";" ;
    char_dec  = "&#"  [0-9]+ ";"              ;
    char_hex  = "&#x" [0-9a-fA-F]+ ";"        ;
  */

  switch (lexer->line_mode) {
  case html_mode_e::Outer:
    while (true) {
      /*!re2c
                      // accepted EOF
        nul           { return true; }

        char_name     { TOK(Id::CharEscape); }
        char_dec      { TOK(Id::CharEscape); }
        char_hex      { TOK(Id::CharEscape); }

        "&"           { TOK(Id::BadAmpersand); }
        ">"           { TOK(Id::BadGreaterThan); }
        "<"           { TOK(Id::BadLessThan); }

        "</" name ">" { TOK(Id::EndTag); }

        "<"  name     {
          TOK_MODE(Id::TagNameLeft, html_mode_e::AttrName);
          // TODO: <script> <style> - special logic for strstr()
        }

        // Problem: these can span more than one linee ... it needs to be
        // another mode?  The end tag might be technically the same.
        "<!" [^\x00>]* ">"  { TOK(Id::Comm); }

        "<!--"        { TOK_MODE(Id::Comm, html_mode_e::Comm); }
        "<?"          { TOK_MODE(Id::Comm, html_mode_e::Preprocessing); }
        "<![CDATA["   { TOK_MODE(Id::Str, html_mode_e::CData); }


                      // Like RawData
        *             { TOK(Id::Other); }

      */
    }
    break;
  case html_mode_e::AttrName:
    while (true) {
      /*!re2c
        nul           { return true; }  // TODO: error

        // TODO: If the tag was <script> or <STYLE>, then we want to enter
        // HtmlCData mode, until we hit </script> or </STYLE>.
        // This is live throughout AttrName, AttrValue, SQ, DQ states?
        ">"           { TOK_MODE(Id::TagNameRight, html_mode_e::Outer); }
        "/>"          { TOK_MODE(Id::SelfClose, html_mode_e::Outer); }

        space_required name {
          // <a missing> - stay in the AttrName mode
          TOK(Id::AttrName);
        }

        space_required name whitespace '=' whitespace {
          // NAME= NAME=' NAME=" - expecting a value
          TOK_MODE(Id::AttrName, html_mode_e::AttrValue);
        }

        *             { TOK(Id::Unknown); }
      */
    }
    break;
  case html_mode_e::AttrValue:
    while (true) {
      /*!re2c
        nul            { return true; }  // TODO: error

        ["]            { TOK_MODE(Id::Str, html_mode_e::DQ); }
        [']            { TOK_MODE(Id::Str, html_mode_e::SQ); }

        // Unquoted value - a single token
        unquoted_value = [^\x00 \r\n\t<>&"']+ ;

        unquoted_value { TOK_MODE(Id::Str, html_mode_e::AttrName); }

        *              { TOK(Id::Unknown); }
      */
    }
    break;

  case html_mode_e::DQ:
    while (true) {
      /*!re2c
        nul           { return true; }  // TODO: error
        char_name     { TOK(Id::CharEscape); }
        char_dec      { TOK(Id::CharEscape); }
        char_hex      { TOK(Id::CharEscape); }

                      // we would only need these for translation to XML, not
                      // highlighting?
        "&"           { TOK(Id::BadAmpersand); }
        ">"           { TOK(Id::BadGreaterThan); }
        "<"           { TOK(Id::BadLessThan); }

        ["]           { TOK_MODE(Id::Str, html_mode_e::AttrName); }
        *             { TOK(Id::Str); }
      */
    }
    break;
  case html_mode_e::SQ:
    while (true) {
      /*!re2c
        nul           { return true; }  // TODO: error
        char_name     { TOK(Id::CharEscape); }
        char_dec      { TOK(Id::CharEscape); }
        char_hex      { TOK(Id::CharEscape); }

                      // we would only need these for translation to XML, not
                      // highlighting?
        "&"           { TOK(Id::BadAmpersand); }
        ">"           { TOK(Id::BadGreaterThan); }
        "<"           { TOK(Id::BadLessThan); }
        [']           { TOK_MODE(Id::Str, html_mode_e::AttrName); }

        *             { TOK(Id::Str); }
      */
    }
    break;
  case html_mode_e::Comm:
    // Search until next -->
    while (true) {
      /*!re2c
        nul       { return true; }

        "-->"     { TOK_MODE(Id::Comm, html_mode_e::Outer); }

        [^\x00-]* { TOK(Id::Comm); }

        *         { TOK(Id::Comm); }

      */
    }
    break;
  case html_mode_e::Preprocessing:
    // Search until next ?>
    while (true) {
      /*!re2c
        nul       { return true; }

        "?>"      { TOK_MODE(Id::Comm, html_mode_e::Outer); }

        [^\x00?]* { TOK(Id::Comm); }

        *         { TOK(Id::Comm); }

      */
    }
    break;
  case html_mode_e::CData:
    // Search until next ]]>
    while (true) {
      /*!re2c
        nul        { return true; }

        "]]>"      { TOK_MODE(Id::Str, html_mode_e::Outer); }

        [^\x00\]]* { TOK(Id::Str); }

        *          { TOK(Id::Str); }

      */
    }
    break;

  default:
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
// Inherent problems with "micro segmentation":
//
// - Nested double quotes in shell.  echo "hi ${name:-"default"}"
//   - This means that lexing is **dependent on** parsing: does the second
//   double quote **close** the first one, or does it start a nested string?
//   - lexing is non-recursive, parsing is recursive

// Shell Comments depend on operator chars
//   echo one # comment
//   echo $(( 16#ff ))'

#endif  // MICRO_SYNTAX_H
