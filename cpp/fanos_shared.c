#include "cpp/fanos_shared.h"

#include <assert.h>
#include <errno.h>
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>   // vfprintf
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static const int kNumFds = 3;
static const int kSizeOfFds = sizeof(int) * kNumFds;

// error string helper
static void set_err(char** dst, const char* msg) {
  *dst = (char*)malloc(strlen(msg) + 1);
  assert(*dst != NULL);
  strcpy(*dst, msg);
}

void fanos_send(int sock_fd, char* blob, int blob_len, const int* fds,
                int* errno_out, char** value_err_out) {
  char buf[10];
  // snprintf() doesn't write more than 10 bytes, INCLUDING \0
  // It the number of bytes it would have written, EXCLUDING \0
  unsigned int full_length = snprintf(buf, 10, "%d:", blob_len);
  if (full_length > sizeof(buf)) {
    set_err(value_err_out, "Message too large");
    return;
  }

  if (write(sock_fd, buf, full_length) < 0) {  // send '3:'
    *errno_out = errno;
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
    char buf[CMSG_SPACE(kSizeOfFds)];
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
    cmsg->cmsg_len = CMSG_LEN(kSizeOfFds);

    int* fd_msg = (int*)CMSG_DATA(cmsg);
    memcpy(fd_msg, fds, kSizeOfFds);
  }

  int num_bytes = sendmsg(sock_fd, &msg, 0);
  if (num_bytes < 0) {
    *errno_out = errno;
    return;
  }

  buf[0] = ',';
  if (write(sock_fd, buf, 1) < 0) {
    *errno_out = errno;
    return;
  }
}

static int recv_fds_once(int sock_fd, int num_bytes, char* buf, int* buf_len,
                         int* fd_out, int* errno_out, char** value_err_out) {
  // Where to put data
  struct iovec iov = {0};
  iov.iov_base = buf;
  iov.iov_len = num_bytes;  // number of bytes REQUESTED

  struct msghdr msg = {0};
  msg.msg_iov = &iov;
  msg.msg_iovlen = 1;

  union {
    char control[CMSG_SPACE(kSizeOfFds)];
    struct cmsghdr align;
  } u;
  msg.msg_control = u.control;
  msg.msg_controllen = sizeof u.control;

  size_t bytes_read = recvmsg(sock_fd, &msg, 0);
  if (bytes_read < 0) {
    *errno_out = errno;
    return -1;
  }
  *buf_len = bytes_read;

  struct cmsghdr* cmsg = CMSG_FIRSTHDR(&msg);
  if (cmsg && cmsg->cmsg_len == CMSG_LEN(kSizeOfFds)) {
    if (cmsg->cmsg_level != SOL_SOCKET) {
      set_err(value_err_out, "Expected cmsg_level SOL_SOCKET");
      return -1;
    }
    if (cmsg->cmsg_type != SCM_RIGHTS) {
      set_err(value_err_out, "Expected cmsg_type SCM_RIGHTS");
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

char* fanos_recv(int sock_fd, int* fd_out, int* len_out, int* errno_out,
                 char** value_err_out) {
  // Receive with netstring encoding
  char buf[10];  // up to 9 digits, then :
  char* p = buf;
  int n;
  for (int i = 0; i < 10; ++i) {
    n = read(sock_fd, p, 1);
    if (n < 0) {
      *errno_out = errno;
      return NULL;
    }
    if (n != 1) {
      if (i == 0) {
        *len_out = 0;
        return NULL;
      } else {
        set_err(value_err_out, "Unexpected EOF");
        return NULL;
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
    set_err(value_err_out, "Expected netstring length");
    return NULL;
  }
  if (*p != ':') {
    set_err(value_err_out, "Expected : after netstring length");
    return NULL;
  }

  *p = '\0';  // change : to NUL terminator
  int expected_bytes = atoi(buf);

  char* data_buf = (char*)malloc(expected_bytes + 1);
  data_buf[expected_bytes] = '\0';

  n = 0;
  while (n < expected_bytes) {
    int bytes_read;
    if (recv_fds_once(sock_fd, expected_bytes - n, data_buf + n, &bytes_read,
                      fd_out, errno_out, value_err_out) < 0) {
      return NULL;
    }
    n += bytes_read;
    break;
  }

  assert(n == expected_bytes);

  n = read(sock_fd, buf, 1);
  if (n < 0) {
    *errno_out = errno;
    return NULL;
  }
  if (n != 1) {
    set_err(value_err_out, "Unexpected EOF");
    return NULL;
  }
  if (buf[0] != ',') {
    set_err(value_err_out, "Expected ,");
    return NULL;
  }

  *len_out = expected_bytes;
  return data_buf;
}
