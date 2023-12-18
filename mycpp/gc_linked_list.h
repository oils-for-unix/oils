#ifndef MYCPP_GC_LINKED_LIST_H
#define MYCPP_GC_LINKED_LIST_H

#include "mycpp/common.h"  // DCHECK
#include "mycpp/gc_obj.h"  // ObjHeader, maskbit

template <typename T>
class LinkedListNode {
 public:
  LinkedListNode() = delete;  // A list node with no object makes no sense.
  LinkedListNode(T obj) : obj_(obj), prev_(nullptr), next_(nullptr) {
  }

  T obj() const {
    return obj_;
  }

  LinkedListNode* prev() const {
    return prev_;
  }
  LinkedListNode* next() const {
    return next_;
  }

  // Replace the nodes predecessor with the given node.
  void set_prev(LinkedListNode* node) {
    prev_ = node;
  }

  // Replace the nodes sucessor with the given node.
  void set_next(LinkedListNode* node) {
    next_ = node;
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(LinkedListNode<T>));
  }

  static constexpr uint32_t field_mask() {
    return maskbit(offsetof(LinkedListNode, obj_)) |
           maskbit(offsetof(LinkedListNode, prev_)) |
           maskbit(offsetof(LinkedListNode, next_));
  }

 private:
  T obj_;
  LinkedListNode* prev_;
  LinkedListNode* next_;
};

template <typename T>
class LinkedList {
 public:
  LinkedList() : front_(nullptr), back_(nullptr) {
  }

  LinkedListNode<T>* front() const {
    return front_;
  }
  LinkedListNode<T>* back() const {
    return back_;
  }

  // Remove and return the first element in the list.
  LinkedListNode<T>* PopFront() {
    if (front_ == nullptr) {
      return nullptr;
    }

    LinkedListNode<T>* node = front_;
    LinkedListNode<T>* next = front_->next();
    if (next != nullptr) {
      next->set_prev(nullptr);
    }
    front_ = next;
    if (back_ == node) {
      back_ = front_;
    }

    node->set_prev(nullptr);
    node->set_next(nullptr);
    return node;
  }

  // Remove and return the last element in the list.
  LinkedListNode<T>* PopBack() {
    if (back_ == nullptr) {
      return nullptr;
    }

    LinkedListNode<T>* node = back_;
    LinkedListNode<T>* prev = back_->prev();
    if (prev != nullptr) {
      prev->set_next(nullptr);
    }
    back_ = prev;
    if (front_ == node) {
      front_ = back_;
    }

    node->set_prev(nullptr);
    node->set_next(nullptr);
    return node;
  }

  // Push the given node onto the front of the list.
  void PushFront(LinkedListNode<T>* node) {
    node->set_prev(nullptr);
    node->set_next(front_);
    if (front_ != nullptr) {
      front_->set_prev(node);
    }
    front_ = node;
    if (back_ == nullptr) {
      back_ = front_;
    }
  }

  // Push the given node onto the back of the list.
  void PushBack(LinkedListNode<T>* node) {
    node->set_prev(back_);
    node->set_next(nullptr);
    if (back_ != nullptr) {
      back_->set_next(node);
    }
    back_ = node;
    if (front_ == nullptr) {
      front_ = back_;
    }
  }

  // Remove the given node from the list.
  void Remove(LinkedListNode<T>* node) {
    // TODO: in debug mode should we DCHECK that node is actually in the list?
    LinkedListNode<T>* prev = node->prev();
    LinkedListNode<T>* next = node->next();

    if (prev != nullptr) {
      prev->set_next(next);
    }
    if (next != nullptr) {
      next->set_prev(prev);
    }

    node->set_prev(nullptr);
    node->set_next(nullptr);

    if (front_ == node) {
      front_ = next;
    }
    if (back_ == node) {
      back_ = prev;
    }
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(LinkedList<T>));
  }

  static constexpr uint32_t field_mask() {
    return maskbit(offsetof(LinkedList, front_)) |
           maskbit(offsetof(LinkedList, back_));
  }

 private:
  LinkedListNode<T>* front_;
  LinkedListNode<T>* back_;
};

#endif
