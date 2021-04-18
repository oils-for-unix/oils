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
#include <stdlib.h>
#include <sys/socket.h>

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

// same as 'sizeof fds' in send()
#define NUM_FDS 3
#define SIZEOF_FDS (sizeof(int) * NUM_FDS)

ssize_t recv_helper(int sock_fd, int num_bytes, char *buf, PyObject *fd_out) {
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
    PyErr_SetString(PyExc_RuntimeError, strerror(errno));
    return NULL;
  }

  struct cmsghdr *cmsg = CMSG_FIRSTHDR(&msg);
  if (cmsg && cmsg->cmsg_len == CMSG_LEN(SIZEOF_FDS)) {
    if (cmsg->cmsg_level != SOL_SOCKET) {
      PyErr_SetString(PyExc_RuntimeError, "Expected cmsg_level SOL_SOCKET");
      return NULL;
    }
    if (cmsg->cmsg_type != SCM_RIGHTS) {
      PyErr_SetString(PyExc_RuntimeError, "Expected cmsg_type SCM_RIGHTS");
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

  return bytes_read;

append_error:
  PyErr_SetString(PyExc_RuntimeError, "append() error");
  return NULL;
}

static PyObject *
func_receive(PyObject *self, PyObject *args) {
  int sock_fd;
  PyObject* fd_out;

  if (!PyArg_ParseTuple(args, "iO", &sock_fd, &fd_out)) {
    return NULL;
  }

  debug("cp5o.receive %d\n", sock_fd);

  // Receive with netstring encoding
  char buf[10];  // up to 9 digits, then :
  char* p = buf;
  size_t n;
  for (int i = 0; i < 10; ++i) {
    n = recv(sock_fd, p, 1, 0);
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

  *p = '\0';  // change : to NUL terminator
  int expected_bytes = atoi(buf);

  debug("expected_bytes = %d", expected_bytes);

  char *msg = malloc(expected_bytes + 1);
  msg[expected_bytes] = '\0';

  n = 0;
  while (n < expected_bytes) {
    ssize_t bytes_read = recv_helper(sock_fd, expected_bytes - n, msg + n,
                                     fd_out);
    debug("bytes_read = %d", bytes_read);
    n += bytes_read;
    break;
  }

  assert(n == expected_bytes);
  debug("msg = %s", msg);

  n = recv(sock_fd, buf, 1, 0 /*flags*/);
  if (n != 1) {
    PyErr_SetString(PyExc_RuntimeError, "recv(1) failed");
    return NULL;
  }
  if (buf[0] != ',') {
    PyErr_SetString(PyExc_RuntimeError, "Expected ,");
    return NULL;
  }

  return PyString_FromStringAndSize(msg, expected_bytes);
}

static PyObject *
func_send(PyObject *self, PyObject *args) {
  int sock_fd;
  const char *blob;
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
    PyErr_SetString(PyExc_RuntimeError, "Message too large");
    return NULL;
  }

  debug("full_length = %d", full_length);
  if (send(sock_fd, buf, full_length, 0) < 0) {  // send '3:'
    goto send_error;
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
    PyErr_SetString(PyExc_RuntimeError, strerror(errno));
    return NULL;
  }
  debug("sendmsg num_bytes = %d", num_bytes);

  buf[0] = ',';
  if (send(sock_fd, buf, 1, 0) < 0) {  // send ','
    goto send_error;
  }
  debug("sent ,");

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
