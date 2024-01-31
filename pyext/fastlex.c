/*
 * Fast lexer using re2c.
 */

#include <stdarg.h>  // va_list, etc.
#include <stdio.h>  // printf

#include <Python.h>

#include "_gen/frontend/id_kind.asdl_c.h"
#include "_gen/frontend/types.asdl_c.h"  // for lex_mode_e
#include "_gen/frontend/match.re2c.h"

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
fastlex_MatchOshToken(PyObject *self, PyObject *args) {
  int lex_mode;

  unsigned char* line;
  int line_len;

  int start_pos;
  if (!PyArg_ParseTuple(args, "is#i",
                        &lex_mode, &line, &line_len, &start_pos)) {
    return NULL;
  }

  // Bounds checking.  It's OK to be called with a start_pos looking at \0.
  // Eol_Tok is inserted everywhere.
  if (start_pos > line_len) {
    PyErr_Format(PyExc_ValueError,
                 "Invalid MatchOshToken call (start_pos = %d, line_len = %d)",
                 start_pos, line_len);
    return NULL;
  }

  int id;
  int end_pos;
  MatchOshToken(lex_mode, line, line_len, start_pos, &id, &end_pos);
  return Py_BuildValue("(ii)", id, end_pos);
}

static PyObject *
fastlex_MatchEchoToken(PyObject *self, PyObject *args) {
  unsigned char* line;
  int line_len;

  int start_pos;
  if (!PyArg_ParseTuple(args, "s#i", &line, &line_len, &start_pos)) {
    return NULL;
  }

  // Bounds checking.
  if (start_pos > line_len) {
    PyErr_Format(PyExc_ValueError,
                 "Invalid MatchEchoToken call (start_pos = %d, line_len = %d)",
                 start_pos, line_len);
    return NULL;
  }

  int id;
  int end_pos;
  MatchEchoToken(line, line_len, start_pos, &id, &end_pos);
  return Py_BuildValue("(ii)", id, end_pos);
}

static PyObject *
fastlex_MatchGlobToken(PyObject *self, PyObject *args) {
  unsigned char* line;
  int line_len;

  int start_pos;
  if (!PyArg_ParseTuple(args, "s#i", &line, &line_len, &start_pos)) {
    return NULL;
  }

  // Bounds checking.
  if (start_pos > line_len) {
    PyErr_Format(PyExc_ValueError,
                 "Invalid MatchGlobToken call (start_pos = %d, line_len = %d)",
                 start_pos, line_len);
    return NULL;
  }

  int id;
  int end_pos;
  MatchGlobToken(line, line_len, start_pos, &id, &end_pos);
  return Py_BuildValue("(ii)", id, end_pos);
}

static PyObject *
fastlex_MatchPS1Token(PyObject *self, PyObject *args) {
  unsigned char* line;
  int line_len;

  int start_pos;
  if (!PyArg_ParseTuple(args, "s#i", &line, &line_len, &start_pos)) {
    return NULL;
  }

  // Bounds checking.
  if (start_pos > line_len) {
    PyErr_Format(PyExc_ValueError,
                 "Invalid MatchPS1Token call (start_pos = %d, line_len = %d)",
                 start_pos, line_len);
    return NULL;
  }

  int id;
  int end_pos;
  MatchPS1Token(line, line_len, start_pos, &id, &end_pos);
  return Py_BuildValue("(ii)", id, end_pos);
}

static PyObject *
fastlex_MatchHistoryToken(PyObject *self, PyObject *args) {
  unsigned char* line;
  int line_len;

  int start_pos;
  if (!PyArg_ParseTuple(args, "s#i", &line, &line_len, &start_pos)) {
    return NULL;
  }

  // Bounds checking.
  if (start_pos > line_len) {
    PyErr_Format(PyExc_ValueError,
                 "Invalid MatchHistoryToken call (start_pos = %d, line_len = %d)",
                 start_pos, line_len);
    return NULL;
  }

  int id;
  int end_pos;
  MatchHistoryToken(line, line_len, start_pos, &id, &end_pos);
  return Py_BuildValue("(ii)", id, end_pos);
}

static PyObject *
fastlex_MatchBraceRangeToken(PyObject *self, PyObject *args) {
  unsigned char* line;
  int line_len;

  int start_pos;
  if (!PyArg_ParseTuple(args, "s#i", &line, &line_len, &start_pos)) {
    return NULL;
  }

  // Bounds checking.
  if (start_pos > line_len) {
    PyErr_Format(PyExc_ValueError,
                 "Invalid MatchBraceRangeToken call (start_pos = %d, line_len = %d)",
                 start_pos, line_len);
    return NULL;
  }

  int id;
  int end_pos;
  MatchBraceRangeToken(line, line_len, start_pos, &id, &end_pos);
  return Py_BuildValue("(ii)", id, end_pos);
}

static PyObject *
fastlex_MatchJ8Token(PyObject *self, PyObject *args) {
  unsigned char* line;
  int line_len;

  int start_pos;
  if (!PyArg_ParseTuple(args, "s#i", &line, &line_len, &start_pos)) {
    return NULL;
  }

  // Bounds checking.
  if (start_pos > line_len) {
    PyErr_Format(PyExc_ValueError,
                 "Invalid MatchJ8Token call (start_pos = %d, line_len = %d)",
                 start_pos, line_len);
    return NULL;
  }

  int id;
  int end_pos;
  MatchJ8Token(line, line_len, start_pos, &id, &end_pos);
  return Py_BuildValue("(ii)", id, end_pos);
}

static PyObject *
fastlex_MatchJ8StrToken(PyObject *self, PyObject *args) {
  unsigned char* line;
  int line_len;

  int start_pos;
  if (!PyArg_ParseTuple(args, "s#i", &line, &line_len, &start_pos)) {
    return NULL;
  }

  // Bounds checking.
  if (start_pos > line_len) {
    PyErr_Format(PyExc_ValueError,
                 "Invalid MatchJ8StrToken call (start_pos = %d, line_len = %d)",
                 start_pos, line_len);
    return NULL;
  }

  int id;
  int end_pos;
  MatchJ8StrToken(line, line_len, start_pos, &id, &end_pos);
  return Py_BuildValue("(ii)", id, end_pos);
}

static PyObject *
fastlex_MatchJsonStrToken(PyObject *self, PyObject *args) {
  unsigned char* line;
  int line_len;

  int start_pos;
  if (!PyArg_ParseTuple(args, "s#i", &line, &line_len, &start_pos)) {
    return NULL;
  }

  // Bounds checking.
  if (start_pos > line_len) {
    PyErr_Format(PyExc_ValueError,
                 "Invalid MatchJsonStrToken call (start_pos = %d, line_len = %d)",
                 start_pos, line_len);
    return NULL;
  }

  int id;
  int end_pos;
  MatchJsonStrToken(line, line_len, start_pos, &id, &end_pos);
  return Py_BuildValue("(ii)", id, end_pos);
}

static PyObject *
fastlex_IsValidVarName(PyObject *self, PyObject *args) {
  unsigned  char *name;
  int len;

  if (!PyArg_ParseTuple(args, "s#", &name, &len)) {
    return NULL;
  }
  return PyBool_FromLong(IsValidVarName(name, len));
}

static PyObject *
fastlex_ShouldHijack(PyObject *self, PyObject *args) {
  unsigned char *name;
  int len;

  if (!PyArg_ParseTuple(args, "s#", &name, &len)) {
    return NULL;
  }
  return PyBool_FromLong(ShouldHijack(name, len));
}

static PyObject *
fastlex_LooksLikeInteger(PyObject *self, PyObject *args) {
  unsigned char *name;
  int len;

  if (!PyArg_ParseTuple(args, "s#", &name, &len)) {
    return NULL;
  }
  return PyBool_FromLong(LooksLikeInteger(name, len));
}

static PyObject *
fastlex_LooksLikeFloat(PyObject *self, PyObject *args) {
  unsigned char *name;
  int len;

  if (!PyArg_ParseTuple(args, "s#", &name, &len)) {
    return NULL;
  }
  return PyBool_FromLong(LooksLikeFloat(name, len));
}

#ifdef OVM_MAIN
#include "pyext/fastlex.c/methods.def"
#else
static PyMethodDef methods[] = {
  {"MatchOshToken", fastlex_MatchOshToken, METH_VARARGS,
   "(lexer mode, line, start_pos) -> (id, end_pos)."},
  {"MatchEchoToken", fastlex_MatchEchoToken, METH_VARARGS,
   "(line, start_pos) -> (id, end_pos)."},
  {"MatchGlobToken", fastlex_MatchGlobToken, METH_VARARGS,
   "(line, start_pos) -> (id, end_pos)."},
  {"MatchPS1Token", fastlex_MatchPS1Token, METH_VARARGS,
   "(line, start_pos) -> (id, end_pos)."},
  {"MatchHistoryToken", fastlex_MatchHistoryToken, METH_VARARGS,
   "(line, start_pos) -> (id, end_pos)."},
  {"MatchBraceRangeToken", fastlex_MatchBraceRangeToken, METH_VARARGS,
   "(line, start_pos) -> (id, end_pos)."},
  {"MatchJ8Token", fastlex_MatchJ8Token, METH_VARARGS,
   "(line, start_pos) -> (id, end_pos)."},
  {"MatchJ8StrToken", fastlex_MatchJ8StrToken, METH_VARARGS,
   "(line, start_pos) -> (id, end_pos)."},
  {"MatchJsonStrToken", fastlex_MatchJsonStrToken, METH_VARARGS,
   "(line, start_pos) -> (id, end_pos)."},
  {"IsValidVarName", fastlex_IsValidVarName, METH_VARARGS,
   "Is it a valid var name?"},
  // Should we hijack this shebang line?
  {"ShouldHijack", fastlex_ShouldHijack, METH_VARARGS, ""},
  {"LooksLikeInteger", fastlex_LooksLikeInteger, METH_VARARGS, ""},
  {"LooksLikeFloat", fastlex_LooksLikeFloat, METH_VARARGS, ""},
  {NULL, NULL},
};
#endif

void initfastlex(void) {
  Py_InitModule("fastlex", methods);
}
