/*
 * Fast lexer using re2c.
 */

#include <stdarg.h>  // va_list, etc.
#include <stdio.h>  // printf

#include <Python.h>

#include "id.h"
#include "osh-ast.h"
// this is generated C code, but we want a single translation unit
#include "osh-lex.h"

// TODO: Should this be shared among all extensions?
// Log messages to stderr.
#if 0
static void debug(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  vfprintf(stderr, fmt, args);
  va_end(args);
  fprintf(stderr, "\n");
}
#endif

static PyObject *
fastlex_MatchToken(PyObject *self, PyObject *args) {
  int lex_mode;
  unsigned char* line;

  int line_len;
  // Doesn't work!  signed/unsigned confused?
  //Py_ssize_t line_len;

  int start_pos;
  if (!PyArg_ParseTuple(args, "is#i",
                        &lex_mode, &line, &line_len, &start_pos)) {
    return NULL;
  }
  /*
  debug("lex_mode %d, line_len %d, start_pos %d\n",
        lex_mode, line_len, start_pos);
  */

  /*
  for (int i = 0; i < line_len; ++i) {
    printf("%d c: %c\n", i, line[i]);
  }
  */

  int id;
  int end_pos;
  MatchToken(lex_mode, line, line_len, start_pos, &id, &end_pos);
  return Py_BuildValue("(ii)", id, end_pos);
}

// Rename to TokenMatcher?
// LineLexer holds CharMatcher?  or TokenMatcher?
// SlowTokenMatcher
// FastTokenMatcher

static PyMethodDef methods[] = {
  {"MatchToken", fastlex_MatchToken, METH_VARARGS,
   "(lexer mode, line, start_pos) -> (id, end_pos)."},
  {NULL, NULL},
};

void initfastlex(void) {
  Py_InitModule("fastlex", methods);
}
