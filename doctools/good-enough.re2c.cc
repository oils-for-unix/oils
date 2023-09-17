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

/*!re2c

  re2c:yyfill:enable = 0;
  re2c:define:YYCTYPE = char;
  re2c:define:YYCURSOR = p;

  // Shared definitions

  nul = [\x00];
  not_nul = [^\x00];

  identifier = [_a-zA-Z][_a-zA-Z0-9]*;
*/

struct Token {
  int kind;
  int line_num;
  int end_col;
};

enum py_tok_e {
  IdComm,
  IdWS,  // TODO: indent, dedent

  IdName,  // foo

  IdDQ,  // ""
  IdSQ,  // ''

  IdRawDQ,  // r""
  IdRawSQ,  // r''

  IdTripleSQ,  // '''
  IdTripleDQ,  // """

  // Hm I guess we also need r''' and """ ?

  IdOther,  // any other text
  IdUnknown,
};

// TODO: consider C++, or use XMACROS

enum py_line_mode_e {
  PyOuter,  // default
  MultiSQ,  // inside '''
  MultiDQ,  // inside """
};

enum cpp_line_mode_e {
  CppOuter,  // default
  Comm,      // inside /* */ comment
};

enum sh_line_mode_e {
  Outer2,    // default
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

struct Lexer {
  const char* line;
  const char* p_current;     // points into line
  py_line_mode_e line_mode;  // current mode, starts with PyOuter
};

// Returns whether EOL was hit
bool MatchPy(Lexer* lexer, struct Token* tok) {
  const char* p = lexer->p_current;  // mutated by re2c
  const char* YYMARKER = p;

  // clang-format off
  /*!re2c

    triple_sq = "'''";
    triple_dq = ["]["]["];

  */
  // clang-format on

  switch (lexer->line_mode) {
  case PyOuter:
    while (true) {
      // clang-format off
      /*!re2c

        nul       { return true; }

        identifier { tok->kind = IdName; break; }

        sq_middle = ( [^\x00'\\] | "\\" not_nul )*;
        sq_string = [r]? ['] sq_middle ['];

        dq_middle = ( [^\x00"\\] | "\\" not_nul )*;
        dq_string = [r]? ["] dq_middle ["];

        sq_string { tok->kind = IdSQ; break; }
        dq_string { tok->kind = IdDQ; break; }

        // TODO: raw strings
        // Examples: r'foo' and r'\''
        //           r"foo" and r"\""

        comment = "#" not_nul*;
        comment   { tok->kind = IdComm; break; }

        // optional raw prefix
        [r]? triple_sq {
          tok->kind = IdTripleSQ;
          lexer->line_mode = MultiSQ;
          break;
        }
        [r]? triple_dq {
          tok->kind = IdTripleDQ;
          lexer->line_mode = MultiDQ;
          break;
        }

        // Whitespace is needed for SLOC, to tell if a line is entirely blank
        whitespace = [ \t]*;
        whitespace { tok->kind = IdWS; break; }

        // Not the start of quoted, comment, identifier
        other = [^\x00"'#_a-zA-Z]+;
        other     { tok->kind = IdOther; break; }

        // This happens on unclosed quote like "foo
        *         { tok->kind = IdUnknown; break; }

      */
      // clang-format on
    }
    break;

  case MultiSQ:
    while (true) {
      // clang-format off
      /*!re2c
        nul       { return true; }

        triple_sq {
          tok->kind = IdTripleSQ;
          lexer->line_mode = PyOuter;
          break;
        }

        // Highlighted like double-quoted contents
        [^\x00']* { tok->kind = IdTripleSQ; break; }

        // Catch all
        *        { tok->kind = IdTripleSQ; break; }
      */
      // clang-format on
    }
    break;

  case MultiDQ:
    while (true) {
      // clang-format off
      /*!re2c
        nul       { return true; }

        triple_dq {
          tok->kind = IdTripleDQ;
          lexer->line_mode = PyOuter;
          break;
        }

        // Highlighted like double-quoted contents
        [^\x00"]* { tok->kind = IdTripleDQ; break; }

        // Catch all
        *        { tok->kind = IdTripleDQ; break; }
      */
      // clang-format on
    }
    break;
  }

  tok->end_col = p - lexer->line;
  lexer->p_current = p;
  return false;
}

// We don't care about internal NUL, so wrap this in an interface that doesn't

struct Reader {
  FILE* f;

  char* line;             // valid for one NextLine() call, NULL on EOF or error
  size_t allocated_size;  // unused
  int err_num;            // set on error
};

void Init(Reader* reader, FILE* f) {
  reader->f = f;
  reader->line = NULL;
  reader->allocated_size = 0;  // must pass address to getline()
}

bool NextLine(Reader* reader) {
  // Returns true if it put a line in the Reader, or false for EOF.  Handles
  // I/O errors by printing to stderr.

  // Note: getline() frees the previous line, so we don't have to
  ssize_t len = getline(&(reader->line), &(reader->allocated_size), reader->f);
  // Log("len = %d", len);

  if (len < 0) {  // EOF is -1
    // man page says the buffer should be freed if getline() fails
    free(reader->line);

    reader->line = NULL;  // tell the caller not to continue

    if (errno != 0) {  // I/O error
      reader->err_num = errno;
      return false;
    }
  }
  return true;
}

void Close(Reader* reader) {
  fclose(reader->f);
}

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

  if (argc == 1) {
    Reader reader;
    Init(&reader, stdin);
    int line_num = 1;

    Lexer lexer = {
        .line = NULL,
        .p_current = NULL,
        .line_mode = PyOuter,
    };

    while (true) {
      if (!NextLine(&reader)) {
        Log("getline() error: %s", strerror(reader.err_num));
        break;
      }
      if (reader.line == NULL) {
        break;  // EOF
      }
      // Log("line = %s", reader.line);

      Token tok;
      lexer.line = reader.line;
      lexer.p_current = reader.line;

      int start_col = 0;
      while (true) {
        bool eol = MatchPy(&lexer, &tok);
        if (eol) {
          break;
        }
        if (1) {
          char* p_start = reader.line + start_col;
          int num_bytes = tok.end_col - start_col;
          switch (tok.kind) {
          case IdComm:
            fputs(BLUE, stdout);
            fwrite(p_start, 1, num_bytes, stdout);
            fputs(RESET, stdout);
            break;

          case IdName:
            fwrite(p_start, 1, num_bytes, stdout);
            break;

          case IdOther:
            fputs(PURPLE, stdout);
            fwrite(p_start, 1, num_bytes, stdout);
            fputs(RESET, stdout);
            break;

          case IdDQ:
          case IdSQ:
            fputs(RED, stdout);
            fwrite(p_start, 1, num_bytes, stdout);
            fputs(RESET, stdout);
            break;

          case IdTripleSQ:
          case IdTripleDQ:
            fputs(GREEN, stdout);
            fwrite(p_start, 1, num_bytes, stdout);
            fputs(RESET, stdout);
            break;

          case IdUnknown:
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
        } else {
          printf("%d %d %d\n", tok.kind, start_col, tok.end_col);
          printf("  -> mode %d\n", lexer.line_mode);
        }
        start_col = tok.end_col;
      }
      line_num += 1;
    }
    Close(&reader);

  } else {
    for (int i = 1; i < argc; ++i) {
      char* s = argv[i];
      printf("\n");

      // Should we loop until we need a new line, and then getline()?

      Token tok;
      Lexer lexer = {.line = s, .p_current = s, .line_mode = PyOuter};

      int len = strlen(s);
      printf("%d %s\n", len, s);

      int start_col = 0;
      while (true) {
        bool eol = MatchPy(&lexer, &tok);
        if (eol) {
          // TODO: refill lines here
          break;
        }
        printf("%d %d %d\n", tok.kind, start_col, tok.end_col);
        // printf("  -> mode %d\n", lexer.line_mode);
        start_col = tok.end_col;
      }
    }
  }
  return 0;
}
