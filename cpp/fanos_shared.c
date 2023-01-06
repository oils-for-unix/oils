#include "cpp/fanos_shared.h"

#include <assert.h>
#include <errno.h>
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>   // vfprintf
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define SIZEOF_FDS (sizeof(int) * FANOS_NUM_FDS)

const char* kErrTooLarge = "Message too large";
const char* kErrSolSocket = "Expected cmsg_level SOL_SOCKET";
const char* kErrScmRights = "Expected cmsg_type SCM_RIGHTS";
const char* kErrUnexpectedEof = "Unexpected EOF";
const char* kErrMissingLength = "Expected netstring length";
const char* kErrMissingColon = "Expected : after netstring length";
const char* kErrMissingComma = "Expected ,";

void fanos_send(int sock_fd, char* blob, int blob_len, const int* fds,
                struct FanosError* err) {
  char buf[10];
  // snprintf() doesn't write more than 10 bytes, INCLUDING \0
  // It the number of bytes it would have written, EXCLUDING \0
  unsigned int full_length = snprintf(buf, 10, "%d:", blob_len);
  if (full_length > sizeof(buf)) {
    err->value_err = kErrTooLarge;
    return;
  }

  if (write(sock_fd, buf, full_length) < 0) {  // send '3:'
    err->err_code = errno;
    return;
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
    char buf[CMSG_SPACE(SIZEOF_FDS)];
    struct cmsghdr align;
  } u;

  // Optionally set up file descriptor data
  if (fds[0] != -1) {
    // If one FD is passed, all should be passed
    assert(fds[1] != -1);
    assert(fds[2] != -1);

    msg.msg_control = u.buf;
    msg.msg_controllen = sizeof u.buf;

    struct cmsghdr* cmsg = CMSG_FIRSTHDR(&msg);
    cmsg->cmsg_level = SOL_SOCKET;
    cmsg->cmsg_type = SCM_RIGHTS;
    cmsg->cmsg_len = CMSG_LEN(SIZEOF_FDS);

    int* fd_msg = (int*)CMSG_DATA(cmsg);
    memcpy(fd_msg, fds, SIZEOF_FDS);
  }

  int num_bytes = sendmsg(sock_fd, &msg, 0);
  if (num_bytes < 0) {
    err->err_code = errno;
    return;
  }

  buf[0] = ',';
  if (write(sock_fd, buf, 1) < 0) {
    err->err_code = errno;
    return;
  }
}

static int recv_fds_once(int sock_fd, int num_bytes, char* buf, int* buf_len,
                         int* fd_out, struct FanosError* err) {
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
    err->err_code = errno;
    return -1;
  }
  *buf_len = bytes_read;

  struct cmsghdr* cmsg = CMSG_FIRSTHDR(&msg);
  if (cmsg && cmsg->cmsg_len == CMSG_LEN(SIZEOF_FDS)) {
    if (cmsg->cmsg_level != SOL_SOCKET) {
      err->value_err = kErrSolSocket;
      return -1;
    }
    if (cmsg->cmsg_type != SCM_RIGHTS) {
      err->value_err = kErrScmRights;
      return -1;
    }

    int* fd_list = (int*)CMSG_DATA(cmsg);

    // Append the descriptors received
    fd_out[0] = fd_list[0];
    fd_out[1] = fd_list[1];
    fd_out[2] = fd_list[2];
  }

  return 0;
}

void fanos_recv(int sock_fd, int* fd_out, struct FanosResult* result_out,
                struct FanosError* err) {
  // Receive with netstring encoding
  char buf[10];  // up to 9 digits, then :
  char* p = buf;
  int n;
  for (int i = 0; i < 10; ++i) {
    n = read(sock_fd, p, 1);
    if (n < 0) {
      err->err_code = errno;
      return;
    }
    if (n != 1) {
      if (i == 0) {
        // read() returned 0 bytes, which means we got EOF at a message
        // boundary.  This is part of the protocol and the caller should handle
        // it.
        result_out->len = FANOS_EOF;
        return;
      } else {
        err->value_err = kErrUnexpectedEof;
        return;
      }
    }

    if ('0' <= *p && *p <= '9') {
      ;  // added to the buffer
    } else {
      break;
    }

    p++;
  }
  if (p == buf) {
    err->value_err = kErrMissingLength;
    return;
  }
  if (*p != ':') {
    err->value_err = kErrMissingColon;
    return;
  }

  *p = '\0';  // change : to NUL terminator
  int expected_bytes = atoi(buf);

  char* data_buf = (char*)malloc(expected_bytes + 1);
  data_buf[expected_bytes] = '\0';

  n = 0;
  while (n < expected_bytes) {
    int bytes_read;
    if (recv_fds_once(sock_fd, expected_bytes - n, data_buf + n, &bytes_read,
                      fd_out, err) < 0) {
      return;
    }
    n += bytes_read;
    break;
  }

  assert(n == expected_bytes);

  n = read(sock_fd, buf, 1);
  if (n < 0) {
    err->err_code = errno;
    return;
  }
  if (n != 1) {
    err->value_err = kErrUnexpectedEof;
    return;
  }
  if (buf[0] != ',') {
    err->value_err = kErrMissingComma;
    return;
  }

  result_out->data = data_buf;
  result_out->len = expected_bytes;
}
