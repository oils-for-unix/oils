// Python wrapper for FANOS library in cpp/fanos_shared.h

#include <assert.h>
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>  // vfprintf
#include <stdlib.h>

#include "data_lang/j8c.h"

#include <Python.h>

// Log messages to stderr.
static void debug(const char* fmt, ...) {
#if 1
  va_list args;
  va_start(args, fmt);
  vfprintf(stderr, fmt, args);
  va_end(args);
  fprintf(stderr, "\n");
#endif
}

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

static PyMethodDef methods[] = {
  {"J8EncodeString", func_J8EncodeString, METH_VARARGS, ""},

  {NULL, NULL},
};

void initfastfunc(void) {
  Py_InitModule("fastfunc", methods);
}
