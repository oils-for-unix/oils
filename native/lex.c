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
void debug(const char* fmt, ...) {
#if 1
  va_list args;
  va_start(args, fmt);
  vfprintf(stderr, fmt, args);
  va_end(args);
  fprintf(stderr, "\n");
#endif
}

static PyObject *
lex_MatchToken(PyObject *self, PyObject *args) {
  int lex_mode;
  const char* line;

  int line_len;
  // Doesn't work!  signed/unsigned confused?
  //Py_ssize_t line_len;

  int start_index;
  if (!PyArg_ParseTuple(args, "is#i",
                        &lex_mode, &line, &line_len, &start_index)) {
    return NULL;
  }
  debug("lex_mode %d, line_len %d, start_index %d\n",
        lex_mode, line_len, start_index);

  for (int i = 0; i < line_len; ++i) {
    printf("%d c: %c\n", i, line[i]);
  }

  int id;
  int end_index;
  MatchToken(lex_mode, line, line_len, start_index, &id, &end_index);
  return Py_BuildValue("(ii)", id, end_index);
}

// Rename to TokenMatcher?
// LineLexer holds CharMatcher?  or TokenMatcher?
// SlowTokenMatcher
// FastTokenMatcher

PyMethodDef methods[] = {
  {"MatchToken", lex_MatchToken, METH_VARARGS,
   "(lexer mode, line, start_index) -> (id, end_index)."},
  {NULL, NULL},
};

void initlex(void) {
  Py_InitModule("lex", methods);
}
