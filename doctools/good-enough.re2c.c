#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>
#include <stdlib.h>  // free
#include <string.h>

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
*/

typedef struct Token {
  const char *kind;
  int line_num;
  int start_col;
  int end_col;
} Token;

// TODO: consider C++, or use XMACROS

typedef enum py_line_mode_e {
  PyOuter,  // default
  MultiSQ,  // inside '''
  MultiDQ,  // inside """
} py_line_mode_e;

typedef enum cpp_line_mode_e {
  CppOuter,  // default
  Comm,  // inside /* */ comment
} cpp_line_mode_e;

typedef enum sh_line_mode_e {
  Outer2,  // default
  SQ,  // inside multi-line ''
  DollarSQ,  // inside multi-line $''
  DQ,  // inside multi-line ""

  HereSQ,  // inside <<'EOF'
  HereDQ,  // inside <<EOF

  // We could have a separate thing for this
  YshSQ,  // inside '''
  YshDQ,  // inside """
  YshJ,  // inside j"""
} sh_line_mode_e;

typedef struct Lexer {
  const char* line;
  const char* p_current;  // points into line
  py_line_mode_e line_mode;  // current mode, starts with PyOuter
} Lexer;

// Returns whether there is more input
bool step_py(Lexer* lexer, struct Token* tok) {
  const char *p = lexer->p_current;  // mutated by re2c
  const char *YYMARKER = p;

  tok->start_col = p - lexer->line;

  while (1) {
  /*!re2c

    eol = [\x00\n];

    not_end = [^\x00\n];
    comment = "#" not_end*;

    sq_middle = ( [^\x00\n'\\] | "\\" not_end )*;
    sq_string = ['] sq_middle ['];

    dq_middle = ( [^\x00\n"\\] | "\\" not_end )*;
    dq_string = ["] dq_middle ["];

    multi_sq = "'''";
    multi_dq = ["]["]["];

    eol       { return true; }
    sq_string { tok->kind = "SQ"; break; }
    dq_string { tok->kind = "DQ"; break; }
    comment   { tok->kind = "COM"; break; }

    other = [^\x00\n"'#]+;
    other     { tok->kind = "OTHER"; break; }

    *         { tok->kind = "X"; }

  */
  }

  tok->end_col = p - lexer->line;
  lexer->p_current = p;
  return false;
}

int main(int argc, char **argv) {

  // TODO: 
  // - make sure the whole thing matches
  // - wrap in Python API
  // - wrap in command line API with TSV?

  // -l LANG - one of cpp py sh ysh R
  //
  // otherwise it's guessed from the file extension

  // Outputs:
  // - syntax highlighting
  // - SLOC - (file, number), number of lines with significant tokens
  // - LATER: parsed definitions, for now just do line by line
  //
  // Tokens
  // KIND LINE startcol, endcol
  //
  // Line States
  //   Outer
  //   SQ
  //   DQ
  //   Comm - for C++

  // Kinds:
  //   Python: COMM STR OTHER

  if (argc == 1) {
    size_t allocated_size = 0;  // unused

    FILE* f = stdin;
    char* line;
    while (true) {
      ssize_t len = getline(&line, &allocated_size, f);
      if (len < 0) {
        // man page says the buffer should be freed even if getline fails
        free(line);
        if (errno != 0) {  // Unexpected error
          Log("getline() error: %s", strerror(errno));
        }
        Log("Break");
        break;
      }
      Log("line = %s", line);
    }
    fclose(f);

    printf("done\n");

  } else {
    for (int i = 1; i < argc; ++i) {
      char* s = argv[i];
      printf("\n");

      // Should we loop until we need a new line, and then getline()?

      Token tok;
      Lexer lexer = { .line = s, .p_current = s, .line_mode = PyOuter };

      int len = strlen(s);
      printf("%d %s\n", len, s);

      while (true) {
        bool eol = step_py(&lexer, &tok);
        if (eol) {
          // TODO: refill lines here
          break;
        }
        printf("%s %d %d\n", tok.kind, tok.start_col, tok.end_col);
        printf("  -> mode %d\n", lexer.line_mode);
      }
    }
  }
  return 0;
}
