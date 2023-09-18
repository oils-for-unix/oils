// Good Enough Syntax Recognition

// Motivation:
//
// - The Github source viewer is too slow.  We want to publish a fast version
//   of our source code to view.
//   - We need to link source code from Oils docs.
// - Aesthetics
//   - I don't like noisy keyword highlighting.  Just comments and string
//     literals looks surprisingly good.
//   - Can use this on the blog too.
// - YSH needs syntax highlighters, and this code is a GUIDE to writing one.
//   - The lexer should run on its own.  Generated parsers like TreeSitter
//     require such a lexer.  In contrast to recursive descent, grammars can't
//     specify lexer modes.
// - I realized that "sloccount" is the same problem as syntax highlighting --
//   you exclude comments, whitespace, and lines with only string literals.
//   - sloccount is a huge Perl codebase, and we can stop depending on that.
// - Because re2c is fun, and I wanted to experiment with writing it directly.
// - Ideas
//   - use this on your blog?
//   - embed in a text editor?

// Later:
// - Extract declarations, and navigate to source.  This may be another step
//   that processes the TSV file.

// TODO:
// - Python: Indent hook can maintain a stack, and emit tokens
// - C++ 
//   - multi-line preprocessor
//   - arbitrary raw strings R"zZXx(
// - Shell
//   - here docs 
//   - many kinds of multi-line strings

#include <assert.h>
#include <errno.h>
#include <getopt.h>
#include <stdarg.h>  // va_list, etc.
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>  // free
#include <string.h>

const char* RESET = "\x1b[0;0m";
const char* BOLD = "\x1b[1m";
const char* REVERSE = "\x1b[7m";  // reverse video

const char* RED = "\x1b[31m";
const char* GREEN = "\x1b[32m";
const char* YELLOW = "\x1b[33m";
const char* BLUE = "\x1b[34m";
const char* PURPLE = "\x1b[35m";

void Log(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  vfprintf(stderr, fmt, args);
  va_end(args);
  fputs("\n", stderr);
}

void die(const char* message) {
  fprintf(stderr, "good-enough: %s\n", message);
  exit(1);
}

enum class lang_e {
  Unspecified,

  Py,
  Shell,
  Ysh,  // ''' etc.

  Cpp,  // including C
  R,    // uses # comments
  JS,   // uses // comments
};

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

enum class sh_mode_e {
  Outer,  // default

  SQ,        // inside multi-line ''
  DollarSQ,  // inside multi-line $''
  DQ,        // inside multi-line ""

  HereSQ,  // inside <<'EOF'
  HereDQ,  // inside <<EOF

  // We could have a separate thing for this
  YshSQ,  // inside '''
  YshDQ,  // inside """
  YshJ,   // inside j"""
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

class Hook {
 public:
  virtual bool IsPreprocessorLine(char* line, Token* tok) {
    return false;
  }
};

class CppHook : public Hook {
 public:
  // Note: testing a single line isn't enough.  We also have to look at line
  // continuations.
  // So we may need to switch into another mode.

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

// Problems matching #ifdef only at beginning of line
// I might need to make a special line lexer for that, and it might be used
// for INDENT/DEDENT too?
//
// The start conditions example looks scary, with YYCURSOR and all that
// https://re2c.org/manual/manual_c.html#start-conditions

#if 0
    // at start of line?
    if (lexer->p_current == lexer->line_) {
      // printf("STARTING ");
      while (true) {
      /*!re2c
                                // break out of case
        whitespace "#" not_nul* { tok->kind = Id::Preproc; goto outer2; }
        *                       { goto outer1; }

      */
      }
    }
#endif
/* this goes into an infinite loop
        "" / whitespace "#" not_nul* {
          if (lexer->p_current == lexer->line_) {
            TOK(Id::Preproc);
          }
        }
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

class Reader {
  // We don't care about internal NUL, so this interface doesn't allow it

 public:
  Reader(FILE* f) : f_(f), line_(nullptr), allocated_size_(0) {
  }

  bool NextLine() {
    // Returns true if it put a line in the Reader, or false for EOF.  Handles
    // I/O errors by printing to stderr.

    // Note: getline() frees the previous line, so we don't have to
    ssize_t len = getline(&line_, &allocated_size_, f_);
    // Log("len = %d", len);

    if (len < 0) {  // EOF is -1
      // man page says the buffer should be freed if getline() fails
      free(line_);

      line_ = nullptr;  // tell the caller not to continue

      if (errno != 0) {  // I/O error
        err_num_ = errno;
        return false;
      }
    }
    return true;
  }

  char* Current() {
    return line_;
  }

  FILE* f_;

  char* line_;  // valid for one NextLine() call, nullptr on EOF or error
  size_t allocated_size_;  // unused, but must pass address to getline()
  int err_num_;            // set on error
};

class Printer {
 public:
  virtual void Print(char* line, int line_num, int start_col, Token token) = 0;
  virtual ~Printer() {
  }
};

class AnsiPrinter : public Printer {
 public:
  AnsiPrinter(bool more_color) : Printer(), more_color_(more_color) {
  }

  virtual void Print(char* line, int line_num, int start_col, Token tok) {
    char* p_start = line + start_col;
    int num_bytes = tok.end_col - start_col;
    switch (tok.kind) {
    case Id::Comm:
      fputs(BLUE, stdout);
      fwrite(p_start, 1, num_bytes, stdout);
      fputs(RESET, stdout);
      break;

    case Id::Name:
      fwrite(p_start, 1, num_bytes, stdout);
      break;

    case Id::Preproc:
      fputs(PURPLE, stdout);
      fwrite(p_start, 1, num_bytes, stdout);
      fputs(RESET, stdout);
      break;

    case Id::Other:
      if (more_color_) {
        fputs(PURPLE, stdout);
      }
      fwrite(p_start, 1, num_bytes, stdout);
      if (more_color_) {
        fputs(RESET, stdout);
      }
      break;

    case Id::Str:
      fputs(RED, stdout);
      fwrite(p_start, 1, num_bytes, stdout);
      fputs(RESET, stdout);
      break;

    case Id::LBrace:
    case Id::RBrace:
      fputs(GREEN, stdout);
      fwrite(p_start, 1, num_bytes, stdout);
      fputs(RESET, stdout);
      break;

    case Id::Unknown:
      // Make errors red
      fputs(REVERSE, stdout);
      fputs(RED, stdout);
      fwrite(p_start, 1, num_bytes, stdout);
      fputs(RESET, stdout);
      break;
    default:
      fwrite(p_start, 1, num_bytes, stdout);
      break;
    }
  }
  virtual ~AnsiPrinter() {
  }

 private:
  bool more_color_;
};

const char* Id_str(Id id) {
  switch (id) {
  case Id::Comm:
    return "Comm";
  case Id::WS:
    return "WS";
  case Id::Preproc:
    return "Preproc";

  case Id::Name:
    return "Name";
  case Id::Other:
    return "Other";

  case Id::Str:
    return "Str";

  case Id::LBrace:
    return "LBrace";
  case Id::RBrace:
    return "RBrace";

  case Id::Unknown:
    return "Unknown";
  default:
    assert(0);
  }
}

class TsvPrinter : public Printer {
 public:
  virtual void Print(char* line, int line_num, int start_col, Token tok) {
    printf("%d\t%s\t%d\t%d\n", line_num, Id_str(tok.kind), start_col,
           tok.end_col);
    // printf("  -> mode %d\n", lexer.line_mode);
  }
  virtual ~TsvPrinter() {
  }
};

bool TokenIsSignificant(Id id) {
  switch (id) {
  case Id::Name:
  case Id::Other:
    return true;

  // Comments, whitespace, and string literals aren't significant
  // TODO: can abort on Id::Unknown?
  default:
    break;
  }
  return false;
}

struct Flags {
  lang_e lang;
  bool tsv;
  bool more_color;

  int argc;
  char** argv;
};

// This templated method causes some code expansion, but not too much.  The
// binary went from 38 KB to 42 KB, after being stripped.
// We get a little type safety with py_mode_e vs cpp_mode_e.

template <typename T>
int GoodEnough(const Flags& flag, Printer* pr, Hook* hook) {
  Reader reader(stdin);

  Lexer<T> lexer(nullptr);
  Matcher<T> matcher;

  int line_num = 1;
  int num_sig = 0;

  while (true) {  // read each line, handling errors
    if (!reader.NextLine()) {
      Log("getline() error: %s", strerror(reader.err_num_));
      return 1;
    }
    char* line = reader.Current();
    if (line == nullptr) {
      break;  // EOF
    }
    int start_col = 0;

    Token pre_tok;
    if (hook->IsPreprocessorLine(line, &pre_tok)) {
      pr->Print(line, line_num, start_col, pre_tok);

      num_sig += 1;  // a preprocessor line is real code
      line_num += 1;
      continue;
    }

    lexer.SetLine(line);
    // Log("line = %s", line);

    bool line_is_sig = false;
    while (true) {  // tokens on each line
      Token tok;
      bool eol = matcher.Match(&lexer, &tok);
      if (eol) {
        break;
      }
      pr->Print(line, line_num, start_col, tok);
      start_col = tok.end_col;

      if (TokenIsSignificant(tok.kind)) {
        line_is_sig = true;
      }
    }
    line_num += 1;
    num_sig += line_is_sig;
  }

  Log("%d lines, %d significant", line_num - 1, num_sig);

  return 0;
}

void PrintHelp() {
  puts(R"(Usage: good-enough FLAGS*

Recognizes the syntax of the text on stdin, and prints it to stdout.

Flags:

  -l    Language: py|cpp
  -m    More color, useful for debugging tokens
  -t    Print tokens as TSV, instead of ANSI color

  -h    This help
)");
}

int main(int argc, char** argv) {
  // Outputs:
  // - syntax highlighting
  // - SLOC - (file, number), number of lines with significant tokens
  // - LATER: parsed definitions, for now just do line by line
  //   - maybe do a transducer on the tokens

  Flags flag = {lang_e::Unspecified};

  // http://www.gnu.org/software/libc/manual/html_node/Example-of-Getopt.html
  // + means to be strict about flag parsing.
  int c;
  while ((c = getopt(argc, argv, "+hl:mt")) != -1) {
    switch (c) {
    case 'h':
      PrintHelp();
      return 0;

    case 'l':
      if (strcmp(optarg, "py") == 0) {
        flag.lang = lang_e::Py;

      } else if (strcmp(optarg, "cpp") == 0) {
        flag.lang = lang_e::Cpp;

      } else {
        Log("Expected -l LANG to be py|cpp, got %s", optarg);
        return 2;
      }
      break;

    case 'm':
      flag.more_color = true;
      break;

    case 't':
      flag.tsv = true;
      break;

    case '?':  // getopt library will print error
      return 2;

    default:
      abort();  // should never happen
    }
  }

  int a = optind;  // index into argv
  flag.argv = argv + a;
  flag.argc = argc - a;

  Printer* pr;
  if (flag.tsv) {
    pr = new TsvPrinter();
  } else {
    pr = new AnsiPrinter(flag.more_color);
  }

  Hook* hook;

  int status = 0;
  switch (flag.lang) {
  case lang_e::Py:
    hook = new Hook();  // default hook
    status = GoodEnough<py_mode_e>(flag, pr, hook);
    break;

  case lang_e::Cpp:
    hook = new CppHook();  // preprocessor
    status = GoodEnough<cpp_mode_e>(flag, pr, hook);
    break;

  default:
    hook = new Hook();  // default hook
    status = GoodEnough<py_mode_e>(flag, pr, hook);
    break;
  }

  delete hook;
  delete pr;

  return status;
}
