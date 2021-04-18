/*
 * c5po: The Unix Coprocess Protocol.
 */

// - Enable GNU extensions in fnmatch.h for extended glob.
// - It's also apparently needed for wchar.h in combination with Python.
//   https://github.com/python-pillow/Pillow/issues/1850
//   - It's currently hard-coded in pyconfig.h.
#define _GNU_SOURCE 1

#include <assert.h>  // va_list, etc.
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>  // printf
#include <limits.h>
#include <stdlib.h>

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

void recv_helper(int sock_fd, char *msg, size_t *msg_len, PyObject *fd_out) {
}

static PyObject *
func_receive(PyObject *self, PyObject *args) {
  int sock_fd;
  PyObject* fd_out;

  if (!PyArg_ParseTuple(args, "iO", &sock_fd, &fd_out)) {
    return NULL;
  }

  fprintf(stderr, "todo: RECEIVE %d\n", sock_fd);

  // Append the descriptors, if any
  if (PyList_Append(fd_out, PyInt_FromLong(42)) != 0) {
    ;
  }

  // Receive with netstring encoding
  char buf[10];  // up to 9 digits, then :
  char* p = buf;
  for (int i = 0; i < 10; ++i) {
    ssize_t n = recv(sock_fd, p, 1, 0);
    if (n != 1) {
      debug("n = %d", n);
      PyErr_SetString(PyExc_RuntimeError, "recv(1) failed");
      return NULL;
    }
    debug("p %c", *p);

    if ('0' <= *p && *p <= '9') {
      ;  // added to the buffer
    } else {
      break;
    }

    p++;
  }
  if (p == buf) {
    debug("*p = %c", *p);
    PyErr_SetString(PyExc_RuntimeError, "Expected netstring length byte");
    return NULL;
  }
  if (*p != ':') {
    PyErr_SetString(PyExc_RuntimeError, "Expected : after netstring length");
    return NULL;
  }

  *p = '\0';  // NUL terminate
  int num_bytes = atoi(buf);

  debug("num_bytes = %d", num_bytes);

  // TODO: allocate this
  char *msg;
  int msg_len = 0;
  while (1) {
    recv_helper(sock_fd, &msg, &msg_len, fd_out);
    break;
  }

  Py_RETURN_NONE;
}

static PyObject *
func_send(PyObject *self, PyObject *args) {
  int sock_fd;
  const char *msg;
  int msg_len;
  int fds[3] = { -1, -1, -1 };

  // 3 optional file descriptors
  if (!PyArg_ParseTuple(args, "is#|iii",
                        &sock_fd, &msg, &msg_len,
                        &fds[0], &fds[1], &fds[2])) {
    return NULL;
  }

  fprintf(stderr, "SEND fd %d msg %s\n", sock_fd, msg);
  fprintf(stderr, "%d %d %d\n", fds[0], fds[1], fds[2]);

  if (fds[0] != -1) {
    // If one FD is passed, all should be passed
    assert(fds[1] != -1); 
    assert(fds[2] != -1);

    // TODO: Call sendmsg() instead!
  }

  char buf[10];
  // snprintf() returns the number of bytes it would have written, including \0
  int full_length  = snprintf(buf, 10, "%d:", msg_len);
  if (full_length > sizeof(buf)) {
    PyErr_SetString(PyExc_RuntimeError, "Message too large");
    return NULL;
  }

  if (send(sock_fd, buf, full_length, 0) < 0) {  // send '3:'
    goto send_error;
  }

  int num_bytes;
  if (num_bytes = send(sock_fd, msg, msg_len, 0) < 0) {  // send 'foo'
    goto send_error;
  }

  buf[0] = ',';
  if (send(sock_fd, buf, 1, 0) < 0) {  // send ','
    goto send_error;
  }

  // TODO: Should return something else?
  debug("num_bytes = %d", num_bytes);
  return PyInt_FromLong(num_bytes);

send_error:
  PyErr_SetString(PyExc_RuntimeError, "send() error");
  return NULL;
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
