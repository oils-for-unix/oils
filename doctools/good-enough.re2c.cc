#include <assert.h>
#include <errno.h>
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

enum class Id {
  Comm,
  WS,  // TODO: indent, dedent

  Name,  // foo

  DQ,  // "" and Python r""
  SQ,  // '' and Python r''

  TripleSQ,  // '''
  TripleDQ,  // """

  // Hm I guess we also need r''' and """ ?

  Other,  // any other text
  Unknown,
};

struct Token {
  Id kind;
  int line_num;
  int end_col;
};

enum class line_mode_e {
  PyOuter,  // default
  MultiSQ,  // inside '''
  MultiDQ,  // inside """
};

enum class cpp_line_mode_e {
  Outer,  // default
  Comm,   // inside /* */ comment
};

enum class sh_line_mode_e {
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

class Lexer {
 public:
  Lexer(char* line)
      : line_(line), p_current(line), line_mode(line_mode_e::PyOuter) {
  }

  void SetLine(char* line) {
    line_ = line;
    p_current = line;
  }

  const char* line_;
  const char* p_current;  // points into line
  line_mode_e line_mode;  // current mode, starts with PyOuter
};

// Macros for semantic actions

#define TOK(k)   \
  tok->kind = k; \
  break;
#define TOK_MODE(k, m)               \
  tok->kind = k;                     \
  lexer->line_mode = line_mode_e::m; \
  break;

// Definitions shared between languages

/*!re2c
  re2c:yyfill:enable = 0;
  re2c:define:YYCTYPE = char;
  re2c:define:YYCURSOR = p;

  nul = [\x00];
  not_nul = [^\x00];

  identifier = [_a-zA-Z][_a-zA-Z0-9]*;

  // Shell and Python have # comments
  pound_comment        = "#" not_nul*;

  // YSH and Python have ''' """
  triple_sq = "'''";
  triple_dq = ["]["]["];
*/

// Returns whether EOL was hit
bool MatchPy(Lexer* lexer, struct Token* tok) {
  const char* p = lexer->p_current;  // mutated by re2c
  const char* YYMARKER = p;

  switch (lexer->line_mode) {
  case line_mode_e::PyOuter:
    while (true) {
      /*!re2c
        nul                    { return true; }

        // optional raw prefix
        [r]? triple_sq         { TOK_MODE(Id::TripleSQ, MultiSQ); }
        [r]? triple_dq         { TOK_MODE(Id::TripleDQ, MultiDQ); }

        identifier             { TOK(Id::Name); }

        sq_middle = ( [^\x00'\\] | "\\" not_nul )*;
        dq_middle = ( [^\x00"\\] | "\\" not_nul )*;

        [r]? ['] sq_middle ['] { TOK(Id::SQ); }
        [r]? ["] dq_middle ["] { TOK(Id::DQ); }

        pound_comment          { TOK(Id::Comm); }

        // Whitespace is needed for SLOC, to tell if a line is entirely blank
        // TODO: Also compute INDENT DEDENT tokens

        whitespace = [ \t\r\n]*;
        whitespace             { TOK(Id::WS); }

        // Not the start of a string, comment, identifier
        [^\x00"'#_a-zA-Z]+     { TOK(Id::Other); }

        // e.g. unclosed quote like "foo
        *                      { TOK(Id::Unknown); }

      */
    }
    break;

  case line_mode_e::MultiSQ:
    while (true) {
      /*!re2c
        nul       { return true; }

        triple_sq { TOK_MODE(Id::TripleSQ, PyOuter); }

        [^\x00']* { TOK(Id::TripleSQ); }

        *         { TOK(Id::TripleSQ); }

      */
    }
    break;

  case line_mode_e::MultiDQ:
    while (true) {
      /*!re2c
        nul       { return true; }

        triple_dq { TOK_MODE(Id::TripleDQ, PyOuter); }

        [^\x00"]* { TOK(Id::TripleDQ); }

        *         { TOK(Id::TripleDQ); }

      */
    }
    break;
  }

  tok->end_col = p - lexer->line_;
  lexer->p_current = p;
  return false;
}

// We don't care about internal NUL, so wrap this in an interface that doesn't

class Reader {
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

    case Id::Other:
      fputs(PURPLE, stdout);
      fwrite(p_start, 1, num_bytes, stdout);
      fputs(RESET, stdout);
      break;

    case Id::DQ:
    case Id::SQ:
      fputs(RED, stdout);
      fwrite(p_start, 1, num_bytes, stdout);
      fputs(RESET, stdout);
      break;

    case Id::TripleSQ:
    case Id::TripleDQ:
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
};

char* Id_str(Id id) {
  switch (id) {
  case Id::Comm:
    return "Comm";
  case Id::WS:
    return "WS";
  case Id::Name:
    return "Name";
  case Id::Other:
    return "Other";
  case Id::DQ:
    return "DQ";
  case Id::SQ:
    return "SQ";
  case Id::TripleSQ:
    return "TripleSQ";
  case Id::TripleDQ:
    return "TripleDQ";
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

int main(int argc, char** argv) {
  // TODO:
  // - make sure the whole thing matches
  // - wrap in Python API
  // - wrap in command line API with TSV?

  // -l LANG - one of cpp py sh ysh R
  //           otherwise it's guessed from the file extension
  // -tokens - output tokens.tsv
  //           default: print syntax highlighting
  //           and print SLOC

  // Outputs:
  // - syntax highlighting
  // - SLOC - (file, number), number of lines with significant tokens
  // - LATER: parsed definitions, for now just do line by line
  //   - maybe do a transducer on the tokens

  Reader reader(stdin);
  Lexer lexer(nullptr);

  Printer* pr;
  if (0) {
    pr = new AnsiPrinter();
  } else {
    pr = new TsvPrinter();
  }

  int line_num = 1;
  while (true) {  // read each line, handling errors
    if (!reader.NextLine()) {
      Log("getline() error: %s", strerror(reader.err_num_));
      break;
    }
    char* line = reader.Current();
    if (line == nullptr) {
      break;  // EOF
    }
    lexer.SetLine(line);
    // Log("line = %s", line);

    int start_col = 0;
    while (true) {  // tokens on each line
      Token tok;
      bool eol = MatchPy(&lexer, &tok);
      if (eol) {
        break;
      }
      pr->Print(line, line_num, start_col, tok);
      start_col = tok.end_col;
    }
    line_num += 1;
  }
  delete pr;

  return 0;
}
