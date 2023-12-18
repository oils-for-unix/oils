#include "mycpp/gc_linked_list.h"

#include <vector>

#include "mycpp/gc_alloc.h"  // gHeap, Alloc
#include "vendor/greatest.h"

GREATEST_MAIN_DEFS();

// helpers
template <typename T>
LinkedListNode<T>* NewListNode(T obj) {
  return Alloc<LinkedListNode<T>>(obj);
}
template <typename T>
void clear(LinkedList<T>* l) {
  while (l->front() != nullptr) {
    l->PopFront();
  }
}

// On success returns the length of the expected sequence. Otherwise returns the
// index of the first mismatch.
template <typename T>
int check_sequence(LinkedList<T>* l, const std::vector<T>& expected) {
  auto cur = l->front();
  auto it = expected.begin();
  for (; cur != nullptr && it != expected.end(); cur = cur->next(), it++) {
    if (cur->obj() != *it) {
      break;
    }
  }
  return it - expected.begin();
}

TEST list_basics() {
  LinkedList<int>* l = Alloc<LinkedList<int>>();
  ASSERT_EQ(l->front(), nullptr);
  ASSERT_EQ(l->back(), nullptr);

  {
    l->PushFront(NewListNode(1));
    l->PushFront(NewListNode(2));
    l->PushFront(NewListNode(3));

    ASSERT(l->front() != nullptr);
    ASSERT(l->front()->obj() == 3);

    ASSERT(l->back() != nullptr);
    ASSERT(l->back()->obj() == 1);

    l->PopFront();

    ASSERT(l->front() != nullptr);
    ASSERT(l->front()->obj() == 2);

    ASSERT(l->back() != nullptr);
    ASSERT(l->back()->obj() == 1);
  }

  clear(l);
  ASSERT_EQ(l->front(), nullptr);
  ASSERT_EQ(l->back(), nullptr);

  {
    l->PushBack(NewListNode(1));
    l->PushBack(NewListNode(2));
    l->PushBack(NewListNode(3));

    ASSERT(l->front() != nullptr);
    ASSERT(l->front()->obj() == 1);

    ASSERT(l->back() != nullptr);
    ASSERT(l->back()->obj() == 3);

    l->PopBack();

    ASSERT(l->front() != nullptr);
    ASSERT(l->front()->obj() == 1);

    ASSERT(l->back() != nullptr);
    ASSERT(l->back()->obj() == 2);
  }

  PASS();
}

TEST list_rearrange() {
  LinkedList<int>* l = Alloc<LinkedList<int>>();

  auto nodeA = Alloc<LinkedListNode<int>>(1);
  auto nodeB = Alloc<LinkedListNode<int>>(2);
  auto nodeC = Alloc<LinkedListNode<int>>(3);
  auto nodeD = Alloc<LinkedListNode<int>>(4);
  auto nodeE = Alloc<LinkedListNode<int>>(5);

  // start with: 1 2 3 4 5
  l->PushBack(nodeA);
  l->PushBack(nodeB);
  l->PushBack(nodeC);
  l->PushBack(nodeD);
  l->PushBack(nodeE);
  ASSERT_EQ(check_sequence(l, {1, 2, 3, 4, 5}), 5);

  // Move 4 to the front.
  l->Remove(nodeD);
  ASSERT_EQ(check_sequence(l, {1, 2, 3, 5}), 4);
  l->PushFront(nodeD);
  ASSERT_EQ(check_sequence(l, {4, 1, 2, 3, 5}), 5);

  PASS();
}

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(list_basics);
  RUN_TEST(list_rearrange);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
