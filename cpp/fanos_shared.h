#ifndef FANOS_SHARED_H
#define FANOS_SHARED_H

void fanos_send(int sock_fd, char* blob, int blob_len, const int* fds,
                int* errno_out, char** value_err_out);

char* fanos_recv(int sock_fd, int* fd_out, int* len_out, int* errno_out,
                 char** value_err_out);

#endif  // FANOS_SHARED_H
