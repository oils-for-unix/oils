// pgen2.cc

#include "pgen2.h"

#include <vector>

namespace pnode {

PNode::PNode(int typ, syntax_asdl::Token* tok, List<PNode*>*)
    : typ(typ), tok(tok), children() {
}

void PNode::AddChild(PNode* node) {
  children.push_back(node);
}

PNode* PNode::GetChild(int i) {
  int j = i;
  if (j < 0) {
    j += NumChildren();
  }
  return children[j];
}

int PNode::NumChildren() {
  return children.size();
}

// TODO: It would be nicer to reuse the std::deque arena_ throughout the whole
// program.  Rather than new/delete for parsing each YSH expression.
PNodeAllocator::PNodeAllocator() : arena_(new std::deque<PNode>()) {
}

PNode* PNodeAllocator::NewPNode(int typ, syntax_asdl::Token* tok) {
  arena_->emplace_back(typ, tok, nullptr);
  return &(arena_->back());
}

void PNodeAllocator::Clear() {
  delete arena_;
  arena_ = nullptr;
}

}  // namespace pnode
