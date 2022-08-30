#ifndef OLDSTL_CONTAINERS_H
#define OLDSTL_CONTAINERS_H

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


class Obj;

struct Heap {
  void Init(int byte_count) {
  }

  void Bump() {
  }

  void Collect() {
  }

  void* Allocate(int num_bytes) {
    return calloc(num_bytes, 1);
  }

  void PushRoot(Obj** p) {
  }

  void PopRoot() {
  }
};

extern Heap gHeap;

struct StackRoots {
  StackRoots(std::initializer_list<void*> roots) {
  }
};

// clang-format off

#include "mycpp/gc_tag.h"
#include "mycpp/gc_obj.h"
#include "mycpp/gc_alloc.h"

#include "mycpp/gc_str.h"

#include "mycpp/tuple_types.h"
#include "mycpp/error_types.h"

#include "mycpp/oldstl_mylib.h" // mylib namespace

#include "mycpp/gc_slab.h"

#include "mycpp/gc_list.h"
#include "mycpp/gc_list_iter.h"

#include <mycpp/oldstl_dict.h>
#include <mycpp/oldstl_dict_impl.h>

// clang-format on
//
#endif  // OLDSTL_CONTAINERS_H
