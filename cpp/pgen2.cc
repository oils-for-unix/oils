// pgen2.cc

#include "pgen2.h"

#include <vector>

namespace pnode {

static std::vector<PNode> pnode_arena;

PNode* NewPNode(int typ, syntax_asdl::Token* tok) {
  if (tok == nullptr) {
    pnode_arena.reserve(1000000);
    pnode_arena.clear();
  }
  CHECK(pnode_arena.size() < pnode_arena.capacity());
  pnode_arena.emplace_back(typ, tok, nullptr);
  return pnode_arena.data() + (pnode_arena.size() - 1);
}

}  // namespace pnode
