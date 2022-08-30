#ifndef LEAKY_CONTAINERS_H
#define LEAKY_CONTAINERS_H

#ifndef OLDSTL_BINDINGS
  #error \
      "This file contains definitions for OLDSTL containers.  If you wanted a gc'd container build, include gc_containers.h"
#endif

#include <assert.h>
#include <ctype.h>   // isalpha(), isdigit()
#include <stdlib.h>  // malloc
#include <string.h>  // strlen

#include <algorithm>  // sort() is templated
// https://stackoverflow.com/questions/3882346/forward-declare-file
#include <climits>  // CHAR_BIT
#include <cstdint>
#include <cstdio>  // FILE*
#include <initializer_list>
#include <vector>

#include "common.h"

#ifdef DUMB_ALLOC
  #include "cpp/dumb_alloc.h"
  #define malloc dumb_malloc
  #define free dumb_free
#endif

#include "mycpp/leaky_heap.h"

// clang-format off

#include "mycpp/gc_tag.h"
#include "mycpp/gc_obj.h"
#include "mycpp/gc_alloc.h"

#include "mycpp/gc_str.h"

#include "mycpp/tuple_types.h"
#include "mycpp/error_types.h"

#include "mycpp/leaky_mylib.h"

#include "mycpp/gc_slab.h"

#include "mycpp/gc_list.h"
#include "mycpp/gc_list_iter.h"

#include <mycpp/gc_dict.h>
#include <mycpp/gc_dict_impl.h>
#include "mycpp/dict_iter.h"

// clang-format on

#endif  // LEAKY_CONTAINERS_H
