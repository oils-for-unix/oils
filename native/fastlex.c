/*
 * Fast lexer using re2c.
 */

#include <stdarg.h>  // va_list, etc.
#include <stdio.h>  // printf

#include <Python.h>

#include "id.h"
#include "osh-types.h"  // for lex_mode_e
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

  // bounds checking.  It's OK to be called with a start_pos looking at \0.
  // Eol_Tok is inserted everywhere.
  if (start_pos > line_len) {
    PyErr_Format(PyExc_ValueError,
                 "Invalid MatchToken call (start_pos = %d, line_len = %d)",
                 start_pos, line_len);
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

static PyObject *
fastlex_IsValidVarName(PyObject *self, PyObject *args) {
  const char *name;
  int len;

  if (!PyArg_ParseTuple(args, "s#", &name, &len)) {
    return NULL;
  }
  return PyBool_FromLong(IsValidVarName(name, len));
}

static PyObject *
fastlex_IsPlainWord(PyObject *self, PyObject *args) {
  const char *name;
  int len;

  if (!PyArg_ParseTuple(args, "s#", &name, &len)) {
    return NULL;
  }
  return PyBool_FromLong(IsPlainWord(name, len));
}


static PyMethodDef methods[] = {
  {"MatchToken", fastlex_MatchToken, METH_VARARGS,
   "(lexer mode, line, start_pos) -> (id, end_pos)."},
  {"IsValidVarName", fastlex_IsValidVarName, METH_VARARGS,
   "Is it a valid var name?"},
  {"IsPlainWord", fastlex_IsPlainWord, METH_VARARGS,
   "Can the string be pretty-printed without quotes?"},
  {NULL, NULL},
};

void initfastlex(void) {
  Py_InitModule("fastlex", methods);
}
