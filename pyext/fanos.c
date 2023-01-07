// Python wrapper for FANOS library in cpp/fanos_shared.h

#include <assert.h>
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>  // vfprintf
#include <stdlib.h>
#include <sys/socket.h>

#include <Python.h>

#include "cpp/fanos_shared.h"

// Log messages to stderr.
static void debug(const char* fmt, ...) {
#if 0
  va_list args;
  va_start(args, fmt);
  vfprintf(stderr, fmt, args);
  va_end(args);
  fprintf(stderr, "\n");
#endif
}

static PyObject *io_error;
static PyObject *fanos_error;

static PyObject *
func_recv(PyObject *self, PyObject *args) {
  int sock_fd;
  PyObject* fd_out;

  if (!PyArg_ParseTuple(args, "iO", &sock_fd, &fd_out)) {
    return NULL;
  }

  debug("fanos.recv %d\n", sock_fd);

  struct FanosError err = {0};
  struct FanosResult res = {NULL, FANOS_INVALID_LEN};
  int fds[FANOS_NUM_FDS] = { -1, -1, -1 };

  fanos_recv(sock_fd, fds, &res, &err);

  if (err.err_code != 0) {
    // uses the errno global, which is apparently still set (see tests)
    debug("func_recv errno = %d", err.err_code);
    return PyErr_SetFromErrno(io_error);
  }
  if (err.value_err != NULL) {
    PyErr_SetString(fanos_error, err.value_err);
    return NULL;
  }

  if (res.len == FANOS_EOF) {
    Py_RETURN_NONE;  // EOF sentinel
  }
  for (int i = 0; i < 3; i++) {
    if (fds[i] != -1 && PyList_Append(fd_out, PyInt_FromLong(fds[i])) != 0) {
      PyErr_SetString(PyExc_RuntimeError, "Couldn't append()");
      return NULL;
    }
  }

  PyObject *ret = PyString_FromStringAndSize(res.data, res.len);
  free(res.data);
  return ret;
}

static PyObject *
func_send(PyObject *self, PyObject *args) {
  int sock_fd;
  char *blob;
  int blob_len;
  int fds[FANOS_NUM_FDS] = { -1, -1, -1 };

  // 3 optional file descriptors
  if (!PyArg_ParseTuple(args, "is#|iii",
                        &sock_fd, &blob, &blob_len,
                        &fds[0], &fds[1], &fds[2])) {
    return NULL;
  }

  debug("SEND fd %d blob %s\n", sock_fd, blob);
  debug("%d %d %d\n", fds[0], fds[1], fds[2]);

  struct FanosError err = {0};
  fanos_send(sock_fd, blob, blob_len, fds, &err);
  if (err.err_code != 0) {
    // uses the errno global, which is apparently still set (see tests)
    debug("func_send errno %d", err.err_code);
    return PyErr_SetFromErrno(io_error);
  }
  if (err.value_err != NULL) {
    PyErr_SetString(fanos_error, err.value_err);
    return NULL;
  }

  Py_RETURN_NONE;
}

static PyMethodDef methods[] = {
  // Receive message and FDs from socket.
  {"recv", func_recv, METH_VARARGS, ""},

  // Send a message across a socket.
  {"send", func_send, METH_VARARGS, ""},

  {NULL, NULL},
};

void initfanos(void) {
  Py_InitModule("fanos", methods);

  // error with errno
  io_error = PyErr_NewException("fanos.IOError", PyExc_IOError, NULL);

  // other protocol errors
  fanos_error = PyErr_NewException("fanos.ValueError", PyExc_ValueError, NULL);
}
