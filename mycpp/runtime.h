#ifndef MYCPP_RUNTIME_H
#define MYCPP_RUNTIME_H

// clang-format off
#include "mycpp/common.h"
#include "mycpp/gc_obj.h"

#include "mycpp/gc_alloc.h"  // gHeap, NewStr(), NewSlab(), Alloc<T>, ...
#include "mycpp/gc_builtins.h"  // Python builtins like to_int(), ValueError

// Python-like compound data structures
#include "mycpp/gc_tuple.h"
#include "mycpp/gc_list.h"
#include "mycpp/gc_dict.h"

#include "mycpp/gc_mylib.h"  // Python-like file I/O, etc.

// clang-format on

#endif  // MYCPP_RUNTIME_H
