// signal.cc

#include "signal__leaky.h"

#include <signal.h>

#define SIGINT_ SIGINT
#undef SIGINT

namespace signal_ {

const int SIGINT = SIGINT_;

}  // namespace signal_
