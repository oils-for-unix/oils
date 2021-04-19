/*
 * NUDS: Netstrings (and file descriptors) over Unix Domain Sockets.
 */

#include <assert.h>
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>  // vfprintf
#include <stdlib.h>
#include <sys/socket.h>

#include <Python.h>

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

// same as 'sizeof fds' in send()
#define NUM_FDS 3
#define SIZEOF_FDS (sizeof(int) * NUM_FDS)

// Helper that calls recvmsg() once.
PyObject* recv_fds_once(
    int sock_fd, int num_bytes,
    char *buf, int* buf_len, PyObject *fd_out) {
  // Where to put data
  struct iovec iov = {0};
  iov.iov_base = buf;
  iov.iov_len = num_bytes;  // number of bytes REQUESTED

  struct msghdr msg = {0};
  msg.msg_iov = &iov;
  msg.msg_iovlen = 1;

  union {
    char control[CMSG_SPACE(SIZEOF_FDS)];
    struct cmsghdr align;
  } u;
  msg.msg_control = u.control;
  msg.msg_controllen = sizeof u.control;

  size_t bytes_read = recvmsg(sock_fd, &msg, 0);
  if (bytes_read < 0) {
    return PyErr_SetFromErrno(io_error);
  }
  *buf_len = bytes_read;

  struct cmsghdr *cmsg = CMSG_FIRSTHDR(&msg);
  if (cmsg && cmsg->cmsg_len == CMSG_LEN(SIZEOF_FDS)) {
    if (cmsg->cmsg_level != SOL_SOCKET) {
      PyErr_SetString(fanos_error, "Expected cmsg_level SOL_SOCKET");
      return NULL;
    }
    if (cmsg->cmsg_type != SCM_RIGHTS) {
      PyErr_SetString(fanos_error, "Expected cmsg_type SCM_RIGHTS");
      return NULL;
    }

    int* fd_list = (int *) CMSG_DATA(cmsg);

    // Append the descriptors received
    if (PyList_Append(fd_out, PyInt_FromLong(fd_list[0])) != 0) {
      goto append_error;
    }
    if (PyList_Append(fd_out, PyInt_FromLong(fd_list[1])) != 0) {
      goto append_error;
    }
    if (PyList_Append(fd_out, PyInt_FromLong(fd_list[2])) != 0) {
      goto append_error;
    }

  } else {
    debug("NO FDS");
  }

  Py_RETURN_NONE;

append_error:
  PyErr_SetString(PyExc_RuntimeError, "Couldn't append()");
  return NULL;
}

static PyObject *
func_recv(PyObject *self, PyObject *args) {
  int sock_fd;
  PyObject* fd_out;

  if (!PyArg_ParseTuple(args, "iO", &sock_fd, &fd_out)) {
    return NULL;
  }

  debug("fanos.recv %d\n", sock_fd);

  // Receive with netstring encoding
  char buf[10];  // up to 9 digits, then :
  char* p = buf;
  size_t n;
  for (int i = 0; i < 10; ++i) {
    n = read(sock_fd, p, 1);
    if (n < 0) {
      return PyErr_SetFromErrno(io_error);
    }
    if (n != 1) {
      debug("n = %d", n);
      PyErr_SetString(fanos_error, "Unexpected EOF");
      return NULL;
    }
    // debug("p %c", *p);

    if ('0' <= *p && *p <= '9') {
      ;  // added to the buffer
    } else {
      break;
    }

    p++;
  }
  if (p == buf) {
    debug("*p = %c", *p);
    PyErr_SetString(fanos_error, "Expected netstring length byte");
    return NULL;
  }
  if (*p != ':') {
    PyErr_SetString(fanos_error, "Expected : after netstring length");
    return NULL;
  }

  *p = '\0';  // change : to NUL terminator
  int expected_bytes = atoi(buf);

  debug("expected_bytes = %d", expected_bytes);

  char *data_buf = malloc(expected_bytes + 1);
  data_buf[expected_bytes] = '\0';

  n = 0;
  while (n < expected_bytes) {
    int bytes_read;
    PyObject* result = recv_fds_once(
        sock_fd, expected_bytes - n,
        data_buf + n, &bytes_read, fd_out);
    if (result == NULL) {
      return NULL;  // error already set
    }
    debug("bytes_read = %d", bytes_read);
    n += bytes_read;
    break;
  }

  assert(n == expected_bytes);
  debug("data_buf = %s", data_buf);

  n = read(sock_fd, buf, 1);
  if (n < 0) {
    return PyErr_SetFromErrno(io_error);
  }
  if (n != 1) {
    PyErr_SetString(fanos_error, "Unexpected EOF");
    return NULL;
  }
  if (buf[0] != ',') {
    PyErr_SetString(fanos_error, "Expected ,");
    return NULL;
  }

  return PyString_FromStringAndSize(data_buf, expected_bytes);
}

static PyObject *
func_send(PyObject *self, PyObject *args) {
  int sock_fd;
  char *blob;
  int blob_len;
  int fds[NUM_FDS] = { -1, -1, -1 };

  // 3 optional file descriptors
  if (!PyArg_ParseTuple(args, "is#|iii",
                        &sock_fd, &blob, &blob_len,
                        &fds[0], &fds[1], &fds[2])) {
    return NULL;
  }

  debug("SEND fd %d blob %s\n", sock_fd, blob);
  debug("%d %d %d\n", fds[0], fds[1], fds[2]);

  char buf[10];
  // snprintf() doesn't write more than 10 bytes, INCLUDING \0
  // It the number of bytes it would have written, EXCLUDING \0
  int full_length = snprintf(buf, 10, "%d:", blob_len);
  if (full_length > sizeof(buf)) {
    PyErr_SetString(fanos_error, "Message too large");
    return NULL;
  }

  debug("full_length = %d", full_length);
  if (write(sock_fd, buf, full_length) < 0) {  // send '3:'
    goto write_error;
  }

  // Example code adapted from 'man CMSG_LEN' on my machine.  (Is this
  // portable?)
  //
  // The APUE code only sends a single FD and doesn't use CMSG_SPACE.

  // Set up the blob data
  struct iovec iov = {0};
  iov.iov_base = blob;
  iov.iov_len = blob_len;

  struct msghdr msg = {0};
  msg.msg_iov = &iov;
  msg.msg_iovlen = 1;

  // This stack buffer has to live until the sendmsg() call!
  union {
     /* ancillary data buffer, wrapped in a union in order to ensure
        it is suitably aligned */
     char buf[CMSG_SPACE(sizeof fds)];
     struct cmsghdr align;
  } u;
  debug("sizeof fds = %d", sizeof fds);  // 12
  debug("cmsg space = %d", CMSG_SPACE(sizeof fds));  // 32!
  debug("cmsg len = %d", CMSG_LEN(sizeof fds));  // 28!

  // Optionally set up file descriptor data
  if (fds[0] != -1) {
    // If one FD is passed, all should be passed
    assert(fds[1] != -1); 
    assert(fds[2] != -1);

    msg.msg_control = u.buf;
    msg.msg_controllen = sizeof u.buf;

    struct cmsghdr *cmsg = CMSG_FIRSTHDR(&msg);
    cmsg->cmsg_level = SOL_SOCKET;
    cmsg->cmsg_type = SCM_RIGHTS;
    cmsg->cmsg_len = CMSG_LEN(sizeof fds);

    int *fd_msg = (int *) CMSG_DATA(cmsg);
    memcpy(fd_msg, fds, sizeof fds);
  }

  int num_bytes = sendmsg(sock_fd, &msg, 0);
  if (num_bytes < 0) {
    goto write_error;
  }
  debug("sendmsg num_bytes = %d", num_bytes);

  buf[0] = ',';
  if (write(sock_fd, buf, 1) < 0) {
    goto write_error;
  }
  debug("sent ,");

  return PyInt_FromLong(num_bytes);

write_error:
  return PyErr_SetFromErrno(io_error);
}

#ifdef OVM_MAIN
#include "native/c5po.c/methods.def"
#else
static PyMethodDef methods[] = {
  // Receive message and FDs from socket.
  {"recv", func_recv, METH_VARARGS, ""},

  // Send a message across a socket.
  {"send", func_send, METH_VARARGS, ""},

  {NULL, NULL},
};
#endif

void initfanos(void) {
  Py_InitModule("fanos", methods);

  // error with errno
  io_error = PyErr_NewException("fanos.IOError", PyExc_IOError, NULL);

  // other protocol errors
  fanos_error = PyErr_NewException("fanos.ValueError", PyExc_ValueError, NULL);
}
