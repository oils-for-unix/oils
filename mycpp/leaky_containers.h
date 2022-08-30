// clang-format off

#ifndef LEAKY_CONTAINERS_H
#define LEAKY_CONTAINERS_H

#ifndef OLDSTL_BINDINGS
  #error \
      "This file contains definitions for OLDSTL containers.  If you wanted a gc'd container build, include gc_containers.h"
#endif

#include <ctype.h>   // isalpha(), isdigit()
#include <string.h>  // strlen
#include <algorithm>  // sort() is templated
#include <initializer_list>
#include <vector>

#include "common.h"

#ifdef DUMB_ALLOC
  #include "cpp/dumb_alloc.h"
  #define malloc dumb_malloc
  #define free dumb_free
#endif

#include "mycpp/leaky_heap.h"

#include "mycpp/error_types.h"

#include "mycpp/containers.h"

#endif  // LEAKY_CONTAINERS_H

// clang-format on

