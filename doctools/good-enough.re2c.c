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

  nul = [\x00];
  not_nul = [^\x00];
*/

typedef struct Token {
  int kind;
  int line_num;
  int end_col;
} Token;

typedef enum py_tok_e {
  IdComm,
  IdWS,
  IdDQ,
  IdSQ,
  IdOther,  // any other text
  IdUnknown,
} py_tok_e;

// TODO: consider C++, or use XMACROS

typedef enum py_line_mode_e {
  PyOuter,  // default
  MultiSQ,  // inside '''
  MultiDQ,  // inside """
} py_line_mode_e;

typedef enum cpp_line_mode_e {
  CppOuter,  // default
  Comm,      // inside /* */ comment
} cpp_line_mode_e;

typedef enum sh_line_mode_e {
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
} sh_line_mode_e;

typedef struct Lexer {
  const char* line;
  const char* p_current;     // points into line
  py_line_mode_e line_mode;  // current mode, starts with PyOuter
} Lexer;

// Returns whether EOL was hit
bool MatchPy(Lexer* lexer, struct Token* tok) {
  const char* p = lexer->p_current;  // mutated by re2c
  const char* YYMARKER = p;

  switch (lexer->line_mode) {
  case PyOuter:
    while (true) {
      // clang-format off
      /*!re2c

        sq_middle = ( [^\x00'\\] | "\\" not_nul )*;
        sq_string = ['] sq_middle ['];

        dq_middle = ( [^\x00"\\] | "\\" not_nul )*;
        dq_string = ["] dq_middle ["];

        triple_sq = "'''";
        triple_dq = ["]["]["];

        comment = "#" not_nul*;
        comment   { tok->kind = IdComm; break; }

        sq_string { tok->kind = IdSQ; break; }
        dq_string { tok->kind = IdDQ; break; }

        // Whitespace is needed for SLOC, to tell if a line is entirely blank
        whitespace = [ \t]*;
        whitespace { tok->kind = IdWS; break; }

        nul       { return true; }

        other = [^\x00"'#]+;
        other     { tok->kind = IdOther; break; }

        // This happens on unclosed quote like "foo
        // Should we raise an error?
        *         { tok->kind = IdUnknown; break; }

      */
      // clang-format on
    }
    break;

  case MultiSQ:
    assert(0);
    break;

  case MultiDQ:
    assert(0);
    break;
  }

  tok->end_col = p - lexer->line;
  lexer->p_current = p;
  return false;
}

// We don't care about internal NUL, so wrap this in an interface that doesn't

typedef struct Reader {
  FILE* f;

  char* line;             // valid for one NextLine() call, NULL on EOF or error
  size_t allocated_size;  // unused
  int err_num;            // set on error
} Reader;

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
      Lexer lexer = {
          .line = reader.line, .p_current = reader.line, .line_mode = PyOuter};

      int start_col = 0;
      while (true) {
        bool eol = MatchPy(&lexer, &tok);
        if (eol) {
          break;
        }
        char* p_start = reader.line + start_col;
        int num_bytes = tok.end_col - start_col;
        switch (tok.kind) {
        case IdComm:
          fputs(BLUE, stdout);
          fwrite(p_start, 1, num_bytes, stdout);
          fputs(RESET, stdout);
          break;
        case IdDQ:
        case IdSQ:
          fputs(RED, stdout);
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
        // printf("%d %d %d\n", tok.kind, start_col, tok.end_col);
        // printf("  -> mode %d\n", lexer.line_mode);
        start_col = tok.end_col;
      }
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
