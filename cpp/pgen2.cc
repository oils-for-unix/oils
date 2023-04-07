// pgen2.cc

#include "pgen2.h"

#include <vector>

namespace pnode {

PNode::PNode(int typ, syntax_asdl::Token* tok, List<PNode*>*)
    : typ(typ), child_offset(0), tok(tok), children() {
}

void PNode::AddChild(PNode* node) {
  children.push_back(node);
}

PNode* PNode::GetChild(int i) {
  int j = i;
  if (j < 0) {
    j += NumChildren();
  }
  return children[child_offset + j];
}

int PNode::NumChildren() {
  return children.size() - child_offset;
}

void PNode::Advance(int n) {
  child_offset += n;
}

PNodeAllocator::PNodeAllocator() : arena_(new std::vector<PNode>()) {
  arena_->reserve(512);
}

PNode* PNodeAllocator::NewPNode(int typ, syntax_asdl::Token* tok) {
  CHECK(arena_->size() < arena_->capacity());
  arena_->emplace_back(typ, tok, nullptr);
  return arena_->data() + (arena_->size() - 1);
}

void PNodeAllocator::Clear() {
  delete arena_;
  arena_ = nullptr;
}

}  // namespace pnode
