// Header for asdl/runtime, which is itself translated and used by ASDL code.
// Most Oil code can go in a single

#ifndef ASDL_RUNTIME_H
#define ASDL_RUNTIME_H

#include "hnode_asdl.h"
#include "mylib.h"  // Str*

namespace runtime {

hnode_asdl::hnode__Record* NewRecord(Str* node_type);
hnode_asdl::hnode__Leaf* NewLeaf(Str* s, hnode_asdl::color_t e_color);
extern Str* TRUE_STR;
extern Str* FALSE_STR;
extern int NO_SPID;

}  // namespace runtime

#endif  // ASDL_RUNTIME_H
