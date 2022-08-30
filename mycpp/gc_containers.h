// mycpp/gc_containers.h
//
// Definitions of Str, List<T>, Dict<K, V>, and related functions.

#ifndef GC_TYPES_H
#define GC_TYPES_H

#ifdef OLDSTL_BINDINGS
  #error "dafuq?"
#endif

#include "mycpp/gc_heap.h"
#include "mycpp/gc_str.h"
#include "mycpp/comparators.h"
#include "mycpp/gc_slab.h"
#include "mycpp/gc_list.h"
#include "mycpp/tuple_types.h"

#include <mycpp/gc_dict.h>
#include <mycpp/gc_dict_impl.h>
#include "mycpp/dict_iter.h"


#endif  // GC_TYPES_H
