#ifndef FANOS_SHARED_H
#define FANOS_SHARED_H

struct FanosError {
  int err_code;
  char const* value_err;  // borrowed
};

struct FanosResult {
  char* data;  // owned
  int len;
};

// Upon failure `err` may be populated with an error message. The caller does
// NOT have to free the message.
void fanos_send(int sock_fd, char* blob, int blob_len, const int* fds,
                struct FanosError* err);

// The caller owns any allocated memory referred to by `result_out`.
// Upon failure `err` may be populated with an error message. The caller does
// NOT have to free the message.
void fanos_recv(int sock_fd, int* fd_out, struct FanosResult* result_out,
                struct FanosError* err);

#endif  // FANOS_SHARED_H
