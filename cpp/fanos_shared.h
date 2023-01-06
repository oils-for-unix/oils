#ifndef FANOS_SHARED_H
#define FANOS_SHARED_H

// FANOS: File descriptors And Netstrings Over Sockets.
//
// This library is shared between cpp/ and pyext/.

// Callers should initalize
//   FanosError to { 0, NULL }, and
//   FanosResult to { NULL, FANOS_INVALID_LEN }

// Callers should check for BOTH I/O errors and protocol errors.
struct FanosError {
  int err_code;           // errno for IOError
  char const* value_err;  // caller must not free; it's global
};

#define FANOS_INVALID_LEN -1
#define FANOS_EOF -2

struct FanosResult {
  char* data;  // caller must free if non-NULL
  int len;
};

// We send or receive 3 file descriptors at a time (for stdin, stdout, stderr)

#define FANOS_NUM_FDS 3

// Send a byte string and optional FDs to a Unix socket.
//
// Upon failure `err` may be populated with an error message. The caller does
// NOT have to free the message.
void fanos_send(int sock_fd, char* blob, int blob_len, const int* fds,
                struct FanosError* err);

// Receive a byte string and possibly FDs from a Unix socket.
//
// If a message is received, result_out->data is set to a malloc()'d buffer.
// The caller must fre() it.
//
// If there are no more messages, then the result_out->len is set to FANOS_EOF.
//
// Upon failure `err` may be populated with an error message. The caller does
// NOT have to free the message.
void fanos_recv(int sock_fd, int* fd_out, struct FanosResult* result_out,
                struct FanosError* err);

#endif  // FANOS_SHARED_H
