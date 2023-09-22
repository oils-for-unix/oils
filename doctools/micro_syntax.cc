// Micro Syntax
//
// See doctools/micro-syntax.md

#include "micro_syntax.h"  // requires -I $BASE_DIR

#include <assert.h>
#include <errno.h>
#include <getopt.h>
#include <stdarg.h>  // va_list, etc.
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>  // free
#include <string.h>

#include <string>
#include <vector>

const char* RESET = "\x1b[0;0m";
const char* BOLD = "\x1b[1m";
const char* REVERSE = "\x1b[7m";  // reverse video

const char* BLACK = "\x1b[30m";
const char* RED = "\x1b[31m";
const char* GREEN = "\x1b[32m";
const char* YELLOW = "\x1b[33m";
const char* BLUE = "\x1b[34m";
const char* PURPLE = "\x1b[35m";

const char* BLACK2 = "\x1b[90m";

void Log(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  vfprintf(stderr, fmt, args);
  va_end(args);
  fputs("\n", stderr);
}

void die(const char* message) {
  fprintf(stderr, "micro-syntax: %s\n", message);
  exit(1);
}

enum class lang_e {
  None,

  Py,
  Shell,
  Ysh,  // ''' etc.

  Cpp,  // including C
  R,    // uses # comments
  JS,   // uses // comments
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
  virtual void PrintLineNumber(int line_num) = 0;
  virtual void PrintToken(const char* line, int line_num, int start_col,
                          Token token) = 0;
  virtual void Swap(std::string* s) {
    assert(0);
  }
  virtual ~Printer() {
  }
};

class HtmlPrinter : public Printer {
 public:
  HtmlPrinter() : Printer(), out_() {
  }

  virtual void Swap(std::string* s) {
    // assert(s != nullptr);
    out_.swap(*s);
  }

  virtual void PrintLineNumber(int line_num) {
    out_.append("<tr><td class=num>");

    char buf[16];
    snprintf(buf, 16, "%d", line_num);
    out_.append(buf);

    out_.append("</td>");
  }

  void PrintSpan(const char* css_class, const char* s, int len) {
    out_.append("<span class=");
    out_.append(css_class);
    out_.append(">");

    // HTML escape the code string
    for (int i = 0; i < len; ++i) {
      char c = s[i];

      switch (c) {
      case '<':
        out_.append("&lt;");
        break;
      case '>':
        out_.append("&gt;");
        break;
      case '&':
        out_.append("&amp;");
        break;
      default:
        // Is this inefficient?  Fill 1 char
        out_.append(1, s[i]);
        break;
      }
    }

    out_.append("</span>");
  }

  virtual void PrintToken(const char* line, int line_num, int start_col,
                          Token tok) {
    const char* p_start = line + start_col;
    int num_bytes = tok.end_col - start_col;
    switch (tok.kind) {
    case Id::Comm:
      PrintSpan("comm", p_start, num_bytes);
      break;

    case Id::Name:
      out_.append(p_start, num_bytes);
      break;

    case Id::Preproc:
      PrintSpan("preproc", p_start, num_bytes);
      break;

    case Id::Other:
      // PrintSpan("other", p_start, num_bytes);
      out_.append(p_start, num_bytes);
      break;

    case Id::Str:
      PrintSpan("str", p_start, num_bytes);
      break;

    case Id::LBrace:
    case Id::RBrace:
      PrintSpan("brace", p_start, num_bytes);
      break;

    case Id::Unknown:
      PrintSpan("x", p_start, num_bytes);
      break;
    default:
      out_.append(p_start, num_bytes);
      break;
    }
  }

 private:
  std::string out_;
};

class AnsiPrinter : public Printer {
 public:
  AnsiPrinter(bool more_color) : Printer(), more_color_(more_color) {
  }

  virtual void PrintLineNumber(int line_num) {
    printf("%s%5d%s ", BLACK2, line_num, RESET);
  }

  virtual void PrintToken(const char* line, int line_num, int start_col,
                          Token tok) {
    const char* p_start = line + start_col;
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
  virtual void PrintLineNumber(int line_num) {
    ;
  }

  virtual void Swap(std::string* s) {
    // out_.swap(*s);
  }

  virtual void PrintToken(const char* line, int line_num, int start_col,
                          Token tok) {
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
  bool web;
  bool more_color;

  int argc;
  char** argv;
};

class OutputStream {
  // stdout contains either
  // - netstrings of HTML, or TSV Token structs
  // - ANSI text

 public:
  OutputStream(Printer* pr) : pr_(pr) {
  }
  virtual void PathBegin(const char* path) = 0;
  virtual void Line(int line_num, const char* line,
                    const std::vector<Token>& tokens) = 0;
  virtual void PathEnd(int num_lines, int num_sig_lines) = 0;
  virtual ~OutputStream() {
  }

 protected:
  Printer* pr_;  // how to print each file
};

class NetStringOutput : public OutputStream {
 public:
  NetStringOutput(Printer* pr) : OutputStream(pr) {
  }
  void PrintNetString(const char* s, int len) {
    fprintf(stdout, "%d:%*s,", len, len, s);
  }

  virtual void PathBegin(const char* path) {
    if (path == nullptr) {
      path = "<stdin>";
    }
    PrintNetString(path, strlen(path));
  }

  virtual void Line(int line_num, const char* line,
                    const std::vector<Token>& tokens) {
    pr_->PrintLineNumber(line_num);

    int start_col = 0;
    for (auto tok : tokens) {
      pr_->PrintToken(line, line_num, start_col, tok);
      start_col = tok.end_col;
    }
  }

  virtual void PathEnd(int num_lines, int num_sig_lines) {
    std::string string_for_file;
    pr_->Swap(&string_for_file);

    PrintNetString(string_for_file.c_str(), string_for_file.size());

    char buf[64];
    int n =
        snprintf(buf, 64, "%d lines, %d significant", num_lines, num_sig_lines);
    PrintNetString(buf, n);
  }
};

class AnsiOutput : public OutputStream {
 public:
  AnsiOutput(Printer* pr) : OutputStream(pr) {
  }

  virtual void PathBegin(const char* path) {
    if (path == nullptr) {
      path = "<stdin>";
    }
    // diff uses +++ ---
    printf("\n");
    printf("=== %s%s%s%s ===\n", BOLD, PURPLE, path, RESET);
    printf("\n");
  }

  virtual void Line(int line_num, const char* line,
                    const std::vector<Token>& tokens) {
    pr_->PrintLineNumber(line_num);

    int start_col = 0;
    for (auto tok : tokens) {
      pr_->PrintToken(line, line_num, start_col, tok);
      start_col = tok.end_col;
    }
  };

  virtual void PathEnd(int num_lines, int num_sig_lines) {
    fprintf(stdout, "%d lines, %d significant\n", num_lines, num_sig_lines);
  };
};

// This templated method causes some code expansion, but not too much.  The
// binary went from 38 KB to 42 KB, after being stripped.
// We get a little type safety with py_mode_e vs cpp_mode_e.

template <typename T>
int Scan(const Flags& flag, Reader* reader, OutputStream* out) {
  Lexer<T> lexer(nullptr);
  Matcher<T> matcher;

  int line_num = 1;
  int num_sig = 0;

  while (true) {  // read each line, handling errors
    if (!reader->NextLine()) {
      Log("getline() error: %s", strerror(reader->err_num_));
      return 1;
    }
    char* line = reader->Current();
    if (line == nullptr) {
      break;  // EOF
    }

    lexer.SetLine(line);

    std::vector<Token> tokens;
    bool line_is_sig = false;
    while (true) {  // tokens on each line
      Token tok;
      bool eol = matcher.Match(&lexer, &tok);
      if (eol) {
        break;
      }
      tokens.push_back(tok);  // make a copy

      if (TokenIsSignificant(tok.kind)) {
        line_is_sig = true;
      }
    }
    out->Line(line_num, line, tokens);
    tokens.clear();

    line_num += 1;
    num_sig += line_is_sig;
  }

  out->PathEnd(line_num - 1, num_sig);
  return 0;
}

int PrintFiles(const Flags& flag, std::vector<char*> files) {
  Printer* pr;        // for each file
  OutputStream* out;  // the entire stream

  if (flag.tsv) {
    pr = new TsvPrinter();
    out = new NetStringOutput(pr);
  } else if (flag.web) {
    pr = new HtmlPrinter();
    out = new NetStringOutput(pr);
  } else {
    pr = new AnsiPrinter(flag.more_color);
    out = new AnsiOutput(pr);
  }
  Hook* hook = nullptr;
  Reader* reader = nullptr;

  int status = 0;
  for (auto path : files) {
    FILE* f;
    if (path == nullptr) {
      f = stdin;
    } else {
      f = fopen(path, "r");
    }
    out->PathBegin(path);

    reader = new Reader(f);

    switch (flag.lang) {
    case lang_e::None:
      hook = new Hook();  // default hook
      status = Scan<none_mode_e>(flag, reader, out);
      break;

    case lang_e::Py:
      hook = new Hook();  // default hook
      status = Scan<py_mode_e>(flag, reader, out);
      break;

    case lang_e::Cpp:
      hook = new CppHook();  // preprocessor
      status = Scan<cpp_mode_e>(flag, reader, out);
      break;

    case lang_e::Shell:
      hook = new Hook();  // default hook
      status = Scan<sh_mode_e>(flag, reader, out);
      break;

    default:
      assert(0);
    }

    delete hook;
    delete reader;

    if (path == nullptr) {
      ;
    } else {
      fclose(f);
    }

    if (status != 0) {
      break;
    }
  }

  delete pr;
  delete out;

  return status;
}

void PrintHelp() {
  puts(R"(Usage: micro-syntax FLAGS* FILE*

Recognizes the syntax of each file,, and prints it to stdout.

If there are no files, reads stdin.

Flags:

  -l    Language: py|cpp|shell
  -t    Print tokens as TSV, instead of ANSI color
  -w    Print HTML for the web

  -m    More color, useful for debugging tokens
  -h    This help
)");
}

int main(int argc, char** argv) {
  // Outputs:
  // - syntax highlighting
  // - SLOC - (file, number), number of lines with significant tokens
  // - LATER: parsed definitions, for now just do line by line
  //   - maybe do a transducer on the tokens

  Flags flag = {lang_e::None};

  // http://www.gnu.org/software/libc/manual/html_node/Example-of-Getopt.html
  // + means to be strict about flag parsing.
  int c;
  while ((c = getopt(argc, argv, "+hl:mtw")) != -1) {
    switch (c) {
    case 'h':
      PrintHelp();
      return 0;

    case 'l':
      if (strcmp(optarg, "py") == 0) {
        flag.lang = lang_e::Py;

      } else if (strcmp(optarg, "cpp") == 0) {
        flag.lang = lang_e::Cpp;

      } else if (strcmp(optarg, "shell") == 0) {
        flag.lang = lang_e::Shell;

      } else {
        Log("Expected -l LANG to be py|cpp|shell, got %s", optarg);
        return 2;
      }
      break;

    case 'm':
      flag.more_color = true;
      break;

    case 't':
      flag.tsv = true;
      break;

    case 'w':
      flag.web = true;
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

  std::vector<char*> files;  // filename, or nullptr for stdin
  if (flag.argc != 0) {
    for (int i = 0; i < flag.argc; ++i) {
      files.push_back(flag.argv[i]);
    }
  } else {
    files.push_back(nullptr);  // stands for stdin
  }

  return PrintFiles(flag, files);
}
