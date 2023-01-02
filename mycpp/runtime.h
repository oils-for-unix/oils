#ifndef MYCPP_RUNTIME_H
#define MYCPP_RUNTIME_H

// clang-format off
#include "mycpp/common.h"
#include "mycpp/gc_obj.h"

// We could put 'extern gHeap' declarations here, and then have runtime.cc
// BUMP_LEAK and MARK_SWEEP are sometimes both defined.  TODO: MARK_SWEEP is
// the default and we should have #ifdef CHENEY_HEAP.

#if defined(BUMP_LEAK)
#include "mycpp/bump_leak_heap.h"
#elif defined(MARK_SWEEP)
#include "mycpp/mark_sweep_heap.h"
#endif

#include "mycpp/gc_alloc.h"

#include "mycpp/gc_builtins.h"  // Emulates Python builtins

// Python-like data structures
#include "mycpp/gc_tuple.h"
#include "mycpp/gc_str.h"  // NewStr() uses gHeap
#include "mycpp/gc_slab.h"  // NewSlab uses gHeap
#include "mycpp/gc_list.h"  // ListIter MAY use gHeap
#include "mycpp/gc_dict.h"

#include "mycpp/gc_mylib.h"  // global vars register with gHeap

// clang-format on

#endif  // MYCPP_RUNTIME_H
