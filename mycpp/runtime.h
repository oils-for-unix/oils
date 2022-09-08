#ifndef MYCPP_RUNTIME_H
#define MYCPP_RUNTIME_H

#define GiB(bytes) (MiB(bytes) * 1024)
#define MiB(bytes) (KiB(bytes) * 1024)
#define KiB(bytes) ((bytes)*1024)

// clang-format off
#include "mycpp/common.h"
#include "mycpp/gc_obj.h"
#include "mycpp/gc_heap.h"
#include "mycpp/builtins.h"

#include "mycpp/tuple_types.h"
#include "mycpp/gc_str.h"
#include "mycpp/gc_slab.h"
#include "mycpp/gc_list.h"
#include "mycpp/gc_dict.h"

#include "mycpp/leaky_mylib.h"
// clang-format on

#endif  // MYCPP_RUNTIME_H
