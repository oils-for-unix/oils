// pgen2.h

#ifndef CPP_PGEN2_H
#define CPP_PGEN2_H

#include <vector>

#include "_gen/frontend/syntax.asdl.h"
#include "mycpp/runtime.h"

namespace grammar {

typedef Tuple2<int, int> arc_t;
typedef Dict<int, int> first_t;
typedef List<List<arc_t*>*> states_t;
typedef Tuple2<states_t*, first_t*> dfa_t;

class Grammar {
 public:
  Grammar();

  Dict<Str*, int>* symbol2number;
  Dict<int, Str*>* number2symbol;
  List<List<Tuple2<int, int>*>*>* states;
  Dict<int, Tuple2<List<List<Tuple2<int, int>*>*>*, Dict<int, int>*>*>* dfas;
  List<int>* labels;
  Dict<Str*, int>* keywords;
  Dict<int, int>* tokens;
  Dict<Str*, int>* symbol2label;
  int start;

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassScanned(8, sizeof(Grammar));
  }

  DISALLOW_COPY_AND_ASSIGN(Grammar)
};

}  // namespace grammar

namespace pnode {

class PNode {
 public:
  PNode(int typ, syntax_asdl::Token* tok, List<PNode*>*);

  void AddChild(PNode* node);
  PNode* GetChild(int i);
  int NumChildren();
  void Advance(int n);

  int typ;
  syntax_asdl::Token* tok;
  std::vector<PNode*> children;
  int child_offset;
};

class PNodeAllocator {
 public:
  PNodeAllocator();

  PNode* NewPNode(int typ, syntax_asdl::Token* tok);
  void Clear();

  static constexpr ObjHeader obj_header() {
    return ObjHeader::Class(HeapTag::Opaque, kZeroMask, sizeof(PNodeAllocator));
  }

 private:
  // We put this on the heap so we can call its destructor from `Clear()`...
  std::vector<PNode>* arena_;
};

}  // namespace pnode

#endif  // CPP_PGEN2_H
