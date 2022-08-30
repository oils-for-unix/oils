#include "mycpp/common.h"
#include "mycpp/error_types.h"

#ifdef OLDSTL_BINDINGS
#include "mycpp/leaky_heap.h"
#else
#include "mycpp/gc_heap.h"
#endif

#include "mycpp/containers.h"
#include "mycpp/builtins.h"

