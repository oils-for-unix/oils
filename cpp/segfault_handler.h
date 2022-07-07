#pragma once

static int segfault_handler_initialized;

#define WRITE_STRING_TO_STDERR(s) (write(2, (s), sizeof(s) - 1))

void complain_loudly_on_segfault_handler(int sig, siginfo_t *si, void *data) {
  WRITE_STRING_TO_STDERR("OSH_CPP_SEGFAULT\n");
  exit(1);
}

void complain_loudly_on_segfault() {
  if (segfault_handler_initialized == 0) {
    struct sigaction sa;
    sa.sa_flags = SA_SIGINFO;
    sigemptyset(&sa.sa_mask);
    sa.sa_sigaction = complain_loudly_on_segfault_handler;
    if (sigaction(SIGSEGV, &sa, NULL) == -1) {
      WRITE_STRING_TO_STDERR("Unable to register segfault handler\n");
    }

    segfault_handler_initialized = 1;
  }
}
