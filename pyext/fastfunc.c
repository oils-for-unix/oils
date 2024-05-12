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
func_Utf8DecodeOne(PyObject *self, PyObject *args) {
  char *string;
  size_t length;
  int start;

  if (!PyArg_ParseTuple(args, "s#i", &string, &length, &start)) {
    return NULL;
  }

  // Bounds check for safety
  assert(0 <= start && start < length);

  Utf8Result_t decode_result;
  utf8_decode(string + start, &decode_result);
  int32_t codepoint_or_error;
  if (decode_result.error) {
    codepoint_or_error = -decode_result.error;
  } else {
    codepoint_or_error = decode_result.codepoint;
  }

  // utf8_decode treats zero-bytes as an end-of-string marker. But python2/oils
  // strings do not. Translate END_OF_STREAM errors to valid zero-codepoints.
  if (decode_result.error == UTF8_ERR_END_OF_STREAM) {
    codepoint_or_error = 0;
    decode_result.bytes_read = 1;  // Read past that zero-byte
  }

  PyObject *ret_val = PyTuple_New(2);
  PyTuple_SET_ITEM(ret_val, 0, PyInt_FromLong(codepoint_or_error));
  PyTuple_SET_ITEM(ret_val, 1, PyInt_FromLong(decode_result.bytes_read));
  return ret_val;
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
  {"Utf8DecodeOne", func_Utf8DecodeOne, METH_VARARGS, ""},
  {"CanOmitQuotes", func_CanOmitQuotes, METH_VARARGS, ""},

  {NULL, NULL},
};

void initfastfunc(void) {
  Py_InitModule("fastfunc", methods);
}
