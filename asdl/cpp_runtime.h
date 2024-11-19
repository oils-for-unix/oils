// Experiment toward trying to generate less C++ code in *.asdl.cc
// Problems:
// - BigStr* runtime::NewLeaf()
// - Id_t type -> dependency issue

#ifndef ASDL_CPP_RUNTIME_H
#define ASDL_CPP_RUNTIME_H

#include "_gen/asdl/hnode.asdl.h"
#include "mycpp/runtime.h"

using hnode_asdl::color_e;
using hnode_asdl::hnode;
using hnode_asdl::hnode_t;

#if 0
template <typename T>
hnode_t* ToPretty(T item) {
  return Alloc<hnode::Leaf>("TODO");
}
#endif

inline hnode_t* ToPretty(bool item) {
  // T and F are also in asdl/runtime.py
  return Alloc<hnode::Leaf>(item ? StrFromC("T") : StrFromC("F"),
                            color_e::OtherConst);
}

// uint16_t, int, double are the same
inline hnode_t* ToPretty(uint16_t item) {
  return Alloc<hnode::Leaf>(str(item), color_e::OtherConst);
}

inline hnode_t* ToPretty(int item) {
  return Alloc<hnode::Leaf>(str(item), color_e::OtherConst);
}

inline hnode_t* ToPretty(double item) {
  return Alloc<hnode::Leaf>(str(item), color_e::OtherConst);
}

inline hnode_t* ToPretty(mops::BigInt item) {
  return Alloc<hnode::Leaf>(mops::ToStr(item), color_e::OtherConst);
}

inline hnode_t* ToPretty(BigStr* item) {
  // return Alloc<hnode::Leaf>(item, color_e::StringConst);

  // generated code
  // runtime::NewLeaf()
  assert(0);
}

// Problem: we can't distinguish between T* and void* ?
// We need to call obj->PrettyTree() sometimes
inline hnode_t* ToPretty(void* item) {
  return Alloc<hnode::External>(item);
}

// The T param here is the item type
template <typename T>
hnode_t* ListPretty(List<T>* li, Dict<int, bool>* seen) {
  seen = seen ? seen : Alloc<Dict<int, bool>>();
  int heap_id = ObjectId(li);
  if (dict_contains(seen, heap_id)) {
    return Alloc<hnode::AlreadySeen>(heap_id);
  }

  hnode::Array* a = Alloc<hnode::Array>(Alloc<List<hnode_t*>>());
  for (ListIter<T> it(li); !it.Done(); it.Next()) {
    T item = it.Value();
    hnode_t* h = ToPretty(item);
    a->children->append(h);
  }
  return a;
}

#endif  // ASDL_CPP_RUNTIME_H
