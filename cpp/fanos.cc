// fanos.cc

#include "cpp/fanos.h"

#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>

#include "cpp/fanos_shared.h"

namespace fanos {

static constexpr int kNumFds = 3;
static constexpr int kSizeOfFds = sizeof(int) * kNumFds;

void send(int sock_fd, Str* blob) {
  int fds[kNumFds] = {-1, -1, -1};
  char* value_err = NULL;
  int err_code = 0;
  fanos_send(sock_fd, blob->data(), len(blob), fds, &err_code, &value_err);
  if (err_code != 0) {
    throw Alloc<IOError>(err_code);
  }
  if (value_err != NULL) {
    throw Alloc<ValueError>(StrFromC(value_err));
  }
}

Str* recv(int sock_fd, List<int>* fd_out) {
  int fds[kNumFds] = {-1, -1, -1};
  char* value_err = NULL;
  int err_code = 0;
  int data_len = -1;
  char* data_buf = fanos_recv(sock_fd, fds, &data_len, &err_code, &value_err);
  if (err_code != 0) {
    throw Alloc<IOError>(err_code);
  }
  if (value_err != NULL) {
    throw Alloc<ValueError>(StrFromC(value_err));
  }

  for (int i = 0; i < 3; i++) {
    fd_out->append(fds[i]);
  }
  if (data_len == 0) {
    return nullptr;
  }

  return StrFromC(data_buf, data_len);
}

}  // namespace fanos
