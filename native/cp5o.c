/*
 * c5po: The Unix Coprocess Protocol.
 */

// - Enable GNU extensions in fnmatch.h for extended glob.
// - It's also apparently needed for wchar.h in combination with Python.
//   https://github.com/python-pillow/Pillow/issues/1850
//   - It's currently hard-coded in pyconfig.h.
#define _GNU_SOURCE 1

#include <stdarg.h>  // va_list, etc.
#include <stdio.h>  // printf
#include <limits.h>
#include <wchar.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <locale.h>
#include <fnmatch.h>
#include <glob.h>
#include <regex.h>

#include <Python.h>

// Log messages to stderr.
static void debug(const char* fmt, ...) {
#ifdef LIBC_VERBOSE
  va_list args;
  va_start(args, fmt);
  vfprintf(stderr, fmt, args);
  va_end(args);
  fprintf(stderr, "\n");
#endif
}

static PyObject *
func_receive(PyObject *self, PyObject *args) {
  int fd;
  // int fd_out[3];

  // TODO: How to specify list (of integers)?
  if (!PyArg_ParseTuple(args, "i", &fd)) {
    return NULL;
  }

  fprintf(stderr, "todo: RECEIVE %d\n", fd);

  Py_RETURN_NONE;
}

static PyObject *
func_send(PyObject *self, PyObject *args) {
  int fd;
  const char *msg;

  if (!PyArg_ParseTuple(args, "is", &fd, &msg)) {
    return NULL;
  }

  fprintf(stderr, "todo: SEND %d %s\n", fd, msg);

  Py_RETURN_NONE;
}

#ifdef OVM_MAIN
#include "native/c5po.c/methods.def"
#else
static PyMethodDef methods[] = {
  // Receive message and FDs from socket.
  {"receive", func_receive, METH_VARARGS, ""},

  // Send a message across a socket.
  {"send", func_send, METH_VARARGS, ""},

  {NULL, NULL},
};
#endif

static PyObject *errno_error;

void initcp5o(void) {
  Py_InitModule("cp5o", methods);
  errno_error = PyErr_NewException("cp5o.error",
                                    PyExc_IOError, NULL);
}
