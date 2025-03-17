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
const char* UNDERLINE = "\x1b[4m";
const char* REVERSE = "\x1b[7m";  // reverse video

const char* BLACK = "\x1b[30m";
const char* RED = "\x1b[31m";
const char* GREEN = "\x1b[32m";
const char* YELLOW = "\x1b[33m";
const char* BLUE = "\x1b[34m";
const char* PURPLE = "\x1b[35m";
const char* CYAN = "\x1b[36m";
const char* WHITE = "\x1b[37m";

const char* BLACK2 = "\x1b[90m";
const char* RED2 = "\x1b[91m";
const char* BLUE2 = "\x1b[94m";

void Log(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  vfprintf(stderr, fmt, args);
  va_end(args);
  fputs("\n", stderr);
}

enum class lang_e {
  PlainText,

  Cpp,  // including C
  Py,
  Shell,
  Ysh,  // ''' etc.
  Html,
  Asdl,
  R,  // uses # comments

  // JS,  // uses // comments
};

class Reader {
  // We don't care about internal NUL, so this interface doesn't allow it

 public:
  Reader(FILE* f, const char* filename)
      : f_(f), filename_(filename), line_(nullptr), allocated_size_(0) {
  }

  const char* Filename() {  // for error messages only, nullptr for stdin
    return filename_;
  }

  bool NextLine() {
    // Returns false if there was an error, and sets err_num_.
    // Returns true if not error, and Current() can be checked.

    // Note: getline() frees the previous line, so we don't have to
    ssize_t len = getline(&line_, &allocated_size_, f_);

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
    // Returns nullptr on EOF.
    return line_;
  }

  FILE* f_;
  const char* filename_;

  char* line_;  // valid for one NextLine() call, nullptr on EOF or error
  size_t allocated_size_;  // unused, but must pass address to getline()
  int err_num_;            // set on error
};

class Printer {
 public:
  virtual void PrintLineNumber(int line_num) = 0;
  virtual void PrintLineEnd() {
  }
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
    char buf[16];
    snprintf(buf, 16, "%d", line_num);

    out_.append("<tr><td class=num>");  // <tr> closed by PrintLineEnd()
    out_.append(buf);
    out_.append("</td><td id=L");  // jump to line with foo.html#L32
    out_.append(buf);
    out_.append(" class=line>");  // <td> closed by PrintLineEnd()
  }

  virtual void PrintLineEnd() {
    out_.append("</td></tr>");
  }

  virtual void PrintToken(const char* line, int line_num, int start_col,
                          Token tok) {
    const char* p_start = line + start_col;
    int num_bytes = tok.end_col - start_col;

    switch (tok.id) {
    case Id::Comm:
      PrintSpan("comm", p_start, num_bytes);
      break;

    case Id::Name:
      PrintEscaped(p_start, num_bytes);
      break;

    case Id::PreprocCommand:
    case Id::LineCont:
      PrintSpan("preproc", p_start, num_bytes);
      break;

    case Id::Re2c:
      PrintSpan("re2c", p_start, num_bytes);
      break;

    case Id::Other:
      // PrintSpan("other", p_start, num_bytes);
      PrintEscaped(p_start, num_bytes);
      break;

      // for now these are strings
    case Id::HereBegin:
    case Id::HereEnd:
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
      PrintEscaped(p_start, num_bytes);
      break;
    }
  }

 private:
  void PrintEscaped(const char* s, int len) {
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
  }

  void PrintSpan(const char* css_class, const char* s, int len) {
    out_.append("<span class=");
    out_.append(css_class);
    out_.append(">");

    PrintEscaped(s, len);

    out_.append("</span>");
  }

  std::string out_;
};

struct Flags {
  lang_e lang;
  bool tsv;
  bool web;
  bool more_color;
  bool comments_only;

  int argc;
  char** argv;
};

class AnsiPrinter : public Printer {
 public:
  AnsiPrinter(const Flags& flag) : Printer(), flag_(flag) {
  }

  virtual void PrintLineNumber(int line_num) {
    if (flag_.comments_only) {
      return;
    }
    printf("%s%5d%s ", BLACK2, line_num, RESET);
  }

  virtual void PrintToken(const char* line, int line_num, int start_col,
                          Token tok) {
    const char* p_start = line + start_col;
    int num_bytes = tok.end_col - start_col;
    switch (tok.id) {
    case Id::Comm:
      if (flag_.comments_only) {
        PrintAlways(p_start, num_bytes);
      } else {
        PrintColor(BLUE, p_start, num_bytes);
      }
      break;

    case Id::Name:
      PrintText(p_start, num_bytes);
      break;

    case Id::PreprocCommand:
    case Id::LineCont:
      PrintColor(PURPLE, p_start, num_bytes);
      break;

    case Id::Re2c:
      PrintColor(PURPLE, p_start, num_bytes);
      break;

    case Id::Other:
      if (flag_.more_color) {
        PrintColor(PURPLE, p_start, num_bytes);
      } else {
        PrintText(p_start, num_bytes);
      }
      break;

    case Id::WS:
      if (flag_.more_color) {
        fputs(REVERSE, stdout);
        PrintColor(WHITE, p_start, num_bytes);
      } else {
        PrintText(p_start, num_bytes);
      }
      break;

    case Id::Str:
      PrintColor(RED, p_start, num_bytes);
      break;

    case Id::HereBegin:
    case Id::HereEnd: {
      PrintColor(RED2, p_start, num_bytes);

      // Debug submatch extraction
#if 0
      fputs(RED, stdout);
      int n = tok.submatch_len;
      fwrite(tok.submatch_start, 1, n, stdout);
      fputs(RESET, stdout);
#endif
    } break;

    case Id::DelimStrBegin:
    case Id::DelimStrEnd: {
      PrintColor(RED2, p_start, num_bytes);

      // Debug submatch extraction
#if 0
      fputs(RED, stdout);
      int n = tok.submatch_len;
      fwrite(tok.submatch_start, 1, n, stdout);
      fputs(RESET, stdout);
#endif
    } break;

    case Id::LBrace:
    case Id::RBrace:
      PrintColor(GREEN, p_start, num_bytes);
      break;

    case Id::TagNameLeft:
    case Id::TagNameRight:
      PrintColor(PURPLE, p_start, num_bytes);
      break;

    case Id::SelfClose:
    case Id::EndTag:
      PrintColor(RED2, p_start, num_bytes);
      break;

    case Id::CharEscape:
      PrintColor(BLUE, p_start, num_bytes);
      break;

    case Id::Unknown:
    case Id::BadAmpersand:
    case Id::BadGreaterThan:
    case Id::BadLessThan:
      // Make errors red
      fputs(REVERSE, stdout);
      PrintColor(RED, p_start, num_bytes);
      break;

    default:
      PrintText(p_start, num_bytes);
      break;
    }
  }

 private:
  void PrintColor(const char* color, const char* s, int n) {
    fputs(color, stdout);
    PrintText(s, n);
    fputs(RESET, stdout);
  }

  void PrintText(const char* s, int n) {
    if (flag_.comments_only) {
      for (int i = 0; i < n; ++i) {
        // Replace everything but newline with space
        // TODO: I think we always want a newline token, including in comments.
        // That will simplify this.
        char c = (s[i] == '\n') ? '\n' : ' ';
        fwrite(&c, 1, 1, stdout);
      }
    } else {
      fwrite(s, 1, n, stdout);
    }
  }

  void PrintAlways(const char* s, int n) {
    fwrite(s, 1, n, stdout);
  }

  const Flags& flag_;
};

const char* Id_str(Id id) {
  switch (id) {
  case Id::Comm:
    return "Comm";
  case Id::MaybeComment:  // fix-up doesn't guarantee this is gone
    return "MaybeComment";
  case Id::WS:
    return "WS";
  case Id::Re2c:
    return "Re2c";

  case Id::MaybePreproc:  // fix-up doesn't guarantee this is gone
    return "MaybePreproc";
  case Id::PreprocCommand:
    return "PreprocCommand";
  case Id::PreprocOther:
    return "PreprocOther";
  case Id::LineCont:
    return "LineCont";

  case Id::Name:
    return "Name";
  case Id::Other:
    return "Other";

  case Id::Str:
    return "Str";

  case Id::HereBegin:
    return "HereBegin";
  case Id::HereEnd:
    return "HereEnd";
  case Id::DelimStrBegin:
    return "DelimStrBegin";
  case Id::DelimStrEnd:
    return "DelimStrEnd";

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
    printf("%d\t%s\t%d\t%d\n", line_num, Id_str(tok.id), start_col,
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
  case Id::PreprocCommand:
  case Id::PreprocOther:
  case Id::Re2c:
    return true;

  // Comments, whitespace, and string literals aren't significant
  // TODO: can abort on Id::Unknown?
  default:
    break;
  }
  return false;
}

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

    pr_->PrintLineEnd();
  }

  virtual void PathEnd(int num_lines, int num_sig_lines) {
    std::string string_for_file;
    pr_->Swap(&string_for_file);

    PrintNetString(string_for_file.c_str(), string_for_file.size());

    // Output summary in JSON
    // TODO: change this to a 4th column
    char buf[64];
    int n = snprintf(buf, 64, "{\"num_lines\": %d, \"num_sig_lines\": %d}",
                     num_lines, num_sig_lines);
    PrintNetString(buf, n);
  }

 private:
  void PrintNetString(const char* s, int len) {
    fprintf(stdout, "%d:%*s,", len, len, s);
  }
};

class AnsiOutput : public OutputStream {
 public:
  AnsiOutput(Printer* pr) : OutputStream(pr) {
  }

  // TODO: Can respect --comments-only
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

    pr_->PrintLineEnd();
  };

  // TODO: Can respect --comments-only
  virtual void PathEnd(int num_lines, int num_sig_lines) {
    fprintf(stdout, "%s%d lines, %d significant%s\n", GREEN, num_lines,
            num_sig_lines, RESET);
  };
};

void PrintTokens(std::vector<Token>& toks) {
  int start_col = 0;
  int i = 0;
  Log("===");
  for (auto tok : toks) {
    Log("%2d %10s %2d %2d", i, Id_str(tok.id), start_col, tok.end_col);
    start_col = tok.end_col;
    ++i;
  }
  Log("===");
}

// BUGGY, needs unit tests

// Fiddly function, reduces the size of the output a bit
// "hi" becomes 1 Id::DQ token instead of 3 separate Id::DQ tokens
void Optimize(std::vector<Token>* tokens) {
  std::vector<Token>& toks = *tokens;  // alias

  // PrintTokens(toks);

  int n = toks.size();
  if (n < 1) {  // nothing to de-duplicate
    return;
  }

  int left = 0;
  int right = 1;
  while (right < n) {
    Log("right ID = %s, end %d", Id_str(toks[right].id), toks[right].end_col);

    if (toks[left].id == toks[right].id) {
      //  Join the tokens together
      toks[left].end_col = toks[right].end_col;
    } else {
      toks[left] = toks[right];
      left++;
      Log("  not eq, left = %d", left);
    }
    right++;
  }
  Log("left = %d, right = %d", left, right);

  // Fiddly condition: one more iteration.  Need some unit tests for this.
  toks[left] = toks[right - 1];
  left++;
  assert(left <= n);

  // Erase the remaining ones
  toks.resize(left);

  // PrintTokens(toks);
}

// Version of the above that's not in-place, led to a bug fix
void Optimize2(std::vector<Token>* tokens) {
  std::vector<Token> optimized;

  int n = tokens->size();
  if (n < 1) {
    return;
  }

  optimized.reserve(n);

  int left = 0;
  int right = 1;
  while (right < n) {
    optimized.push_back((*tokens)[left]);
    left++;
    right++;
  }
  optimized.push_back((*tokens)[left]);
  left++;

  tokens->swap(optimized);
}

bool LineEqualsHereDelim(const char* line, std::string& here_delim) {
  // Compare EOF vs. EOF\n or EOF\t\n or x\n

  // Hack: skip leading tab unconditionally, even though that's only alowed in
  // <<- Really we should capture the operator and the delim?
  if (*line == '\t') {
    line++;
  }

  int n = strlen(line);
  int h = here_delim.size();

  // Log("Here delim=%s line=%s", here_delim.c_str(), line);

  // Line should be at least one longer, EOF\n
  if (n <= h) {
    // Log("  [0] line too short");
    return false;
  }

  int i = 0;
  for (; i < h; ++i) {
    if (here_delim[i] != line[i]) {
      // Log("  [1] byte %d not equal", i);
      return false;
    }
  }

  while (i < n) {
    switch (line[i]) {
    case ' ':
    case '\t':
    case '\r':
    case '\n':
      break;
    default:
      // Log("  [2] byte %d not whitespace", i);
      return false;  // line can't have whitespace on the end
    }
    ++i;
  }

  return true;
}

void CppHook::TryPreprocess(char* line, std::vector<Token>* tokens) {
  // Fills tokens, which can be checked for beginning and end tokens

  Lexer<pp_mode_e> lexer(line);
  Matcher<pp_mode_e> matcher;

  while (true) {  // tokens on each line
    Token tok;
    // Log("Match %d", lexer.p_current - lexer.line_);
    bool eol = matcher.Match(&lexer, &tok);
    // Log("EOL %d", eol);
    if (eol) {
      break;
    }
    // Log("TOK %s %d", Id_str(tok.id), tok.end_col);
    tokens->push_back(tok);  // make a copy
  }
}

void FixShellComments(std::vector<Token>& tokens) {
  int n = tokens.size();
  for (int i = 0; i < n; ++i) {
    // # comment at start of line
    if (tokens[i].id == Id::MaybeComment) {
      if (i == 0) {
        tokens[i].id = Id::Comm;
      }
      if (i != 0 and tokens[i - 1].id == Id::WS) {
        tokens[i].id = Id::Comm;
      }
    }
  }
}

// This templated method causes some code expansion, but not too much.  The
// binary went from 38 KB to 42 KB, after being stripped.
// We get a little type safety with py_mode_e vs cpp_mode_e.

template <typename T>
int ScanOne(Reader* reader, OutputStream* out, Hook* hook) {
  Lexer<T> lexer(nullptr);
  Matcher<T> matcher;

  int line_num = 1;
  int num_sig = 0;

  std::vector<std::string> here_list;  // delimiters to pop
  std::vector<int> here_start_num;

  // For multi-line strings.  This has 0 or 1 entries, and the 1 entry can be
  // the empty string.
  std::vector<std::string> delim_begin;

  while (true) {  // read each line, handling errors
    if (!reader->NextLine()) {
      const char* name = reader->Filename() ?: "<stdin>";
      Log("micro-syntax: getline() error on %s: %s", name,
          strerror(reader->err_num_));
      return 1;
    }
    char* line = reader->Current();
    if (line == nullptr) {
      break;  // EOF
    }

    std::vector<Token> pre_tokens;

    hook->TryPreprocess(line, &pre_tokens);

    // e.g #define at beginning of line
    if (pre_tokens.size() && pre_tokens[0].id == Id::MaybePreproc) {
      pre_tokens[0].id = Id::PreprocCommand;

      out->Line(line_num, line, pre_tokens);

      line_num += 1;
      num_sig += 1;

      Token last = pre_tokens.back();
      while (last.id == Id::LineCont) {
        const char* blame = reader->Filename() ?: "<stdin>";
        if (!reader->NextLine()) {
          Log("micro-syntax: getline() error on %s: %s", blame,
              strerror(reader->err_num_));
          return 1;
        }
        char* line = reader->Current();
        if (line == nullptr) {
          Log("Unexpected end-of-file in preprocessor in %s", blame);
          return 1;
        }

        pre_tokens.clear();
        hook->TryPreprocess(line, &pre_tokens);

        out->Line(line_num, line, pre_tokens);

        line_num += 1;
        num_sig += 1;

        last = pre_tokens.back();
      }
      continue;  // Skip the rest of the loop
    }

    //
    // Main Loop for "normal" lines (not preprocessor or here doc)
    //

    std::vector<Token> tokens;
    lexer.SetLine(line);

    bool line_is_sig = false;
    while (true) {  // tokens on each line
      Token tok;
      bool eol = matcher.Match(&lexer, &tok);
      if (eol) {
        break;
      }

      switch (tok.id) {
      case Id::HereBegin: {
        // Put a copy on the stack
        int n = tok.submatch_end - tok.submatch_start;
        here_list.emplace_back(line + tok.submatch_start, n);
        here_start_num.push_back(line_num);
      } break;

      case Id::DelimStrBegin: {
        if (delim_begin.empty()) {
          int n = tok.submatch_end - tok.submatch_start;
          delim_begin.emplace_back(line + tok.submatch_start, n);
        } else {
          // We have entered cpp_mode_e::DelimStr, which means we should never
          // return another DelimStrBegin
          assert(0);
        }
      } break;

      case Id::DelimStrEnd: {
        if (delim_begin.empty()) {
          // We should never get this unless we got a DelimStrBegin first
          assert(0);
        } else {
          size_t n = tok.submatch_end - tok.submatch_start;
          std::string end_delim(line + tok.submatch_start, n);

          if (end_delim == delim_begin.back()) {
            lexer.line_mode = T::Outer;  // the string is ended
            delim_begin.pop_back();
          } else {
            tok.id = Id::Str;  // mismatched delimiter is just a string
          }
        }
      } break;

      // TODO: I think we need a mode to escape into strstr(), for
      // C++  - ending */
      // HTML - ending -->  ?>  ]]>  </SCRipt>
      //
      // So instead of returning 'eol', we can return a string to search for?
      // Then we keep looking for more lines.
      //
      // This is similar to the problems of here doc and C++ multi-line
      // strings.  The main difference is that we're not using a submatch.
      default:
        break;
      }

      tokens.push_back(tok);  // make a copy

      if (TokenIsSignificant(tok.id)) {
        line_is_sig = true;
      }
    }

#if 0
    PrintTokens(tokens);
    Log("%d tokens before", tokens.size());
    Optimize(&tokens);
    Log("%d tokens after", tokens.size());
    PrintTokens(tokens);
#endif

    FixShellComments(tokens);

    out->Line(line_num, line, tokens);
    tokens.clear();

    // Potentially multiple here docs for this line
    int here_index = 0;
    for (auto here_delim : here_list) {
      // Log("HERE %s", here_delim.c_str());

      while (true) {
        const char* blame = reader->Filename() ?: "<stdin>";
        if (!reader->NextLine()) {
          Log("micro-syntax: getline() error on %s: %s", blame,
              strerror(reader->err_num_));
          return 1;
        }
        char* line = reader->Current();
        if (line == nullptr) {
          int start_line = here_start_num[here_index];
          Log("Unexpected end-of-file in here doc in %s, start line %d", blame,
              start_line);
          return 1;
        }

        line_num++;

        if (LineEqualsHereDelim(line, here_delim)) {
          int n = strlen(line);
          Token whole_line(Id::HereEnd, n);
          tokens.push_back(whole_line);
          out->Line(line_num, line, tokens);
          tokens.clear();
          break;

        } else {
          int n = strlen(line);
          Token whole_line(Id::Str, n);
          tokens.push_back(whole_line);
          out->Line(line_num, line, tokens);
          tokens.clear();

          // Log("  not equal: %s", line);
        }
      }
      here_index++;
    }
    here_list.clear();
    here_start_num.clear();

    line_num++;
    num_sig += line_is_sig;
  }

  out->PathEnd(line_num - 1, num_sig);
  return 0;
}

int ScanFiles(const Flags& flag, std::vector<char*> files, OutputStream* out,
              Hook* hook) {
  Reader* reader = nullptr;

  int status = 0;
  for (auto path : files) {
    FILE* f;
    if (path == nullptr) {
      f = stdin;
    } else {
      f = fopen(path, "r");
      if (f == nullptr) {
        Log("Error opening %s: %s", path, strerror(errno));
        return 1;
      }
    }
    out->PathBegin(path);

    reader = new Reader(f, path);

    switch (flag.lang) {
    case lang_e::PlainText:
      status = ScanOne<text_mode_e>(reader, out, hook);
      break;

    case lang_e::Py:
      status = ScanOne<py_mode_e>(reader, out, hook);
      break;

    case lang_e::Cpp:
      status = ScanOne<cpp_mode_e>(reader, out, hook);
      break;

    case lang_e::Shell:
      status = ScanOne<sh_mode_e>(reader, out, hook);
      break;

    case lang_e::Asdl:
      status = ScanOne<asdl_mode_e>(reader, out, hook);
      break;

    case lang_e::R:
      status = ScanOne<R_mode_e>(reader, out, hook);
      break;

    case lang_e::Html:
      status = ScanOne<html_mode_e>(reader, out, hook);
      break;

    default:
      assert(0);
    }

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

  return status;
}

void PrintHelp() {
  puts(R"(Usage: micro-syntax FLAGS* FILE*

Recognizes the syntax of each file,, and prints it to stdout.

If there are no files, reads stdin.

Flags:
  -h --help   This help

  -l --lang   Language: py|cpp|shell|...
  -t          Print tokens as TSV, instead of ANSI color
  -w          Print HTML for the web

  -m          More color, useful for debugging tokens

  -n --no-comments    Omit comments
  -o --comments-only  Only print comments
  -e --empty-strs     Substitute string literals for empty strings
     --color          on off always more

)");
}

int main(int argc, char** argv) {
  Flags flag = {lang_e::PlainText};

  // http://www.gnu.org/software/libc/manual/html_node/Example-of-Getopt.html
  // + means to be strict about flag parsing.
  int c;
  while ((c = getopt(argc, argv, "+hl:motw")) != -1) {
    switch (c) {
    case 'h':
      PrintHelp();
      return 0;

    case 'l':
      if (strcmp(optarg, "cpp") == 0) {
        flag.lang = lang_e::Cpp;

      } else if (strcmp(optarg, "py") == 0) {
        flag.lang = lang_e::Py;

      } else if (strcmp(optarg, "shell") == 0) {
        flag.lang = lang_e::Shell;

      } else if (strcmp(optarg, "asdl") == 0) {
        flag.lang = lang_e::Asdl;

      } else if (strcmp(optarg, "R") == 0) {
        flag.lang = lang_e::R;

        // TODO: implement all of these
      } else if (strcmp(optarg, "js") == 0) {
        flag.lang = lang_e::PlainText;

      } else if (strcmp(optarg, "css") == 0) {
        flag.lang = lang_e::PlainText;

      } else if (strcmp(optarg, "md") == 0) {
        flag.lang = lang_e::PlainText;

      } else if (strcmp(optarg, "yaml") == 0) {
        flag.lang = lang_e::PlainText;

      } else if (strcmp(optarg, "html") == 0) {
        flag.lang = lang_e::Html;

      } else if (strcmp(optarg, "txt") == 0) {
        flag.lang = lang_e::PlainText;

      } else if (strcmp(optarg, "other") == 0) {
        flag.lang = lang_e::PlainText;

      } else {
        Log("Expected -l LANG to be "
            "cpp|py|shell|asdl|R|js|css|md|yaml|html|txt, "
            "got %s",
            optarg);
        return 2;
      }
      break;

    case 'm':
      flag.more_color = true;
      break;

    case 'o':
      flag.comments_only = true;
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

  Printer* pr;        // for each file
  OutputStream* out;  // the entire stream

  if (flag.tsv) {
    pr = new TsvPrinter();
    out = new NetStringOutput(pr);
  } else if (flag.web) {
    pr = new HtmlPrinter();
    out = new NetStringOutput(pr);
  } else {
    pr = new AnsiPrinter(flag);
    out = new AnsiOutput(pr);
  }

  Hook* hook = nullptr;
  if (flag.lang == lang_e::Cpp) {
    hook = new CppHook();
  } else {
    hook = new Hook();  // default hook
  }

  int status = ScanFiles(flag, files, out, hook);

  delete hook;
  delete pr;
  delete out;

  return status;
}
