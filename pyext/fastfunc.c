// Python wrapper for FANOS library in cpp/fanos_shared.h

#include <assert.h>
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>  // vfprintf
#include <stdlib.h>

#include "data_lang/j8.h"  // CanOmitQuotes
#include "data_lang/j8_libc.h"
#include "data_lang/utf8.h"

#include <Python.h>

#if 0
// Log messages to stderr.
static void debug(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  vfprintf(stderr, fmt, args);
  va_end(args);
  fprintf(stderr, "\n");
}
#endif

static PyObject *
func_J8EncodeString(PyObject *self, PyObject *args) {
  j8_buf_t in;
  int j8_fallback;

  if (!PyArg_ParseTuple(args, "s#i", &(in.data), &(in.len), &j8_fallback)) {
    return NULL;
  }

  j8_buf_t out;
  J8EncodeString(in, &out, j8_fallback);

  PyObject *ret = PyString_FromStringAndSize(out.data, out.len);
  return ret;
}

static PyObject *
func_ShellEncodeString(PyObject *self, PyObject *args) {
  j8_buf_t in;
  int ysh_fallback;

  if (!PyArg_ParseTuple(args, "s#i", &(in.data), &(in.len), &ysh_fallback)) {
    return NULL;
  }

  j8_buf_t out;
  ShellEncodeString(in, &out, ysh_fallback);

  PyObject *ret = PyString_FromStringAndSize(out.data, out.len);
  return ret;
}

static PyObject *
func_PartIsUtf8(PyObject *self, PyObject *args) {
  j8_buf_t in;
  int start;
  int end;

  if (!PyArg_ParseTuple(args, "s#ii", &(in.data), &(in.len), &start, &end)) {
    return NULL;
  }
  // Bounds check for safety
  assert(0 <= start);
  assert(end <= in.len);

  Utf8Result_t result;
  for (int i = start; i < end;) {
    utf8_decode(in.data + i, &result);
    if (result.error) {
      return PyBool_FromLong(0);
    }

    i += result.bytes_read;
  }

  return PyBool_FromLong(1);
}

static PyObject *
func_CanOmitQuotes(PyObject *self, PyObject *args) {
  j8_buf_t in;
  if (!PyArg_ParseTuple(args, "s#", &(in.data), &(in.len))) {
    return NULL;
  }
  int result = CanOmitQuotes(in.data, in.len);
  return PyBool_FromLong(result);
}

static PyMethodDef methods[] = {
  {"J8EncodeString", func_J8EncodeString, METH_VARARGS, ""},
  {"ShellEncodeString", func_ShellEncodeString, METH_VARARGS, ""},
  {"PartIsUtf8", func_PartIsUtf8, METH_VARARGS, ""},
  {"CanOmitQuotes", func_CanOmitQuotes, METH_VARARGS, ""},

  {NULL, NULL},
};

void initfastfunc(void) {
  Py_InitModule("fastfunc", methods);
}
