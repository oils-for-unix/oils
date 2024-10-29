#include "mycpp/gc_iolib.h"

#include <errno.h>

namespace iolib {

SignalSafe* gSignalSafe = nullptr;

SignalSafe* InitSignalSafe() {
  gSignalSafe = Alloc<SignalSafe>();
  gHeap.RootGlobalVar(gSignalSafe);

  RegisterSignalInterest(SIGINT);  // for KeyboardInterrupt checks

  return gSignalSafe;
}

static void OurSignalHandler(int sig_num) {
  assert(gSignalSafe != nullptr);
  gSignalSafe->UpdateFromSignalHandler(sig_num);
}

void RegisterSignalInterest(int sig_num) {
  struct sigaction act = {};
  act.sa_handler = OurSignalHandler;
  if (sigaction(sig_num, &act, nullptr) != 0) {
    throw Alloc<OSError>(errno);
  }
}

// Note that the Python implementation of pyos.sigaction() calls
// signal.signal(), which calls PyOS_setsig(), which calls sigaction() #ifdef
// HAVE_SIGACTION.
void sigaction(int sig_num, void (*handler)(int)) {
  // SIGINT and SIGWINCH must be registered through SignalSafe
  DCHECK(sig_num != SIGINT);
  DCHECK(sig_num != SIGWINCH);

  struct sigaction act = {};
  act.sa_handler = handler;
  if (sigaction(sig_num, &act, nullptr) != 0) {
    throw Alloc<OSError>(errno);
  }
}

}  // namespace iolib
