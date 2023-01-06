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
  FanosError err = {0};
  fanos_send(sock_fd, blob->data(), len(blob), fds, &err);
  if (err.err_code != 0) {
    throw Alloc<IOError>(err.err_code);
  }
  if (err.value_err != NULL) {
    throw Alloc<ValueError>(StrFromC(err.value_err));
  }
}

Str* recv(int sock_fd, List<int>* fd_out) {
  FanosError err = {0};
  FanosResult res = {nullptr, -1};
  int fds[kNumFds] = {-1, -1, -1};
  fanos_recv(sock_fd, fds, &res, &err);
  if (err.err_code != 0) {
    throw Alloc<IOError>(err.err_code);
  }
  if (err.value_err != NULL) {
    throw Alloc<ValueError>(StrFromC(err.value_err));
  }

  for (int i = 0; i < 3; i++) {
    fd_out->append(fds[i]);
  }
  if (res.len == 0) {
    return nullptr;
  }

  Str* ret = StrFromC(res.data, res.len);
  free(res.data);
  return ret;
}

}  // namespace fanos
