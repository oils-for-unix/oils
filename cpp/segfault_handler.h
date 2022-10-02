#ifndef SEGFAULT_HANDLER_H
#define SEGFAULT_HANDLER_H

static int segfault_handler_initialized;

// Handler
void complain_loudly_on_segfault_handler(int sig, siginfo_t *si, void *data) {
  fputs("OSH_CPP_SEGFAULT\n", stderr);
  exit(1);
}

// Register handler
void complain_loudly_on_segfault() {
  if (segfault_handler_initialized == 0) {
    struct sigaction sa;
    sa.sa_flags = SA_SIGINFO;
    sigemptyset(&sa.sa_mask);
    sa.sa_sigaction = complain_loudly_on_segfault_handler;
    if (sigaction(SIGSEGV, &sa, NULL) == -1) {
      fputs("Unable to register segfault handler\n", stderr);
    }

    segfault_handler_initialized = 1;
  }
}

#endif
