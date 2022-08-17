#ifndef LIST_TYPES_H
#define LIST_TYPES_H


// Type that is layout-compatible with List (unit tests assert this).  Two
// purposes:
// - To make globals of "plain old data" at compile-time, not at startup time.
//   This can't be done with subclasses of Obj.
// - To avoid invalid-offsetof warnings when computing GC masks.

template <typename T, int N>
class GlobalList {
 public:
  OBJ_HEADER()
  int len_;
  int capacity_;
  GlobalSlab<T, N>* slab_;
};

// A list has one Slab pointer which we need to follow.
constexpr uint16_t maskof_List() {
  return maskbit(offsetof(GlobalList<int COMMA 1>, slab_));
}

template <typename T>
class List : public Obj {
  // TODO: Move methods that don't allocate or resize: out of gc_heap?
  // - allocate: append(), extend()
  // - resize: pop(), clear()
  // - neither: reverse(), sort() -- these are more like functions.  Except
  //   sort() is a templated method that depends on type param T.
  // - neither: index(), slice()

  // 8 / 4 = 2 items, or 8 / 8 = 1 item
  static const int kCapacityAdjust = kSlabHeaderSize / sizeof(T);
  static_assert(kSlabHeaderSize % sizeof(T) == 0,
                "Slab header size should be multiple of item size");

 public:
  List() : Obj(Tag::FixedSize, maskof_List(), sizeof(List<T>)) {
    // Ensured by heap zeroing.  It's never directly on the stack.
    assert(len_ == 0);
    assert(capacity_ == 0);
    assert(slab_ == nullptr);
  }

  // Implements L[i]
  T index_(int i);

  // returns index of the element
  int index(T element);

  // Implements L[i] = item
  // Note: Unlike Dict::set(), we don't need to specialize List::set() on T for
  // StackRoots because it doesn't allocate.
  void set(int i, T item);

  // L[begin:]
  List* slice(int begin);

  // L[begin:end]
  // TODO: Can this be optimized?
  List* slice(int begin, int end);

  // Should we have a separate API that doesn't return it?
  // https://stackoverflow.com/questions/12600330/pop-back-return-value
  T pop();

  // Used in osh/word_parse.py to remove from front
  // TODO: Don't accept an arbitrary index?
  T pop(int i);

  void clear();

  // Used in osh/string_ops.py
  void reverse();

  // Templated function
  void sort();

  // Ensure that there's space for a number of items
  void reserve(int n);

  // Append a single element to this list.  Must be specialized List<int> vs
  // List<Str*>.
  //
  // NOTE(Jesse): The 'must be a specialized List<int> vs List<Str*>' part of
  // the comment above is correct, however the entirety of the codebase
  // completely ignores it.  See @template_specialization_append_pointer for
  // more details and the solution.
  //
  void append(T item);

  // Extend this list with multiple elements.
  void extend(List<T>* other);

  int len_;       // number of entries
  int capacity_;  // max entries before resizing

  // The container may be resized, so this field isn't in-line.
  Slab<T>* slab_;

  DISALLOW_COPY_AND_ASSIGN(List)
};

// "Constructors" as free functions since we can't allocate within a
// constructor.  Allocation may cause garbage collection, which interferes with
// placement new.

template <typename T>
List<T>* NewList() {
  return Alloc<List<T>>();
}

// Literal ['foo', 'bar']
template <typename T>
List<T>* NewList(std::initializer_list<T> init) {
  auto self = Alloc<List<T>>();
  StackRoots _roots({&self});

  int n = init.size();
  self->reserve(n);

  int i = 0;
  for (auto item : init) {
    self->set(i, item);
    ++i;
  }
  self->len_ = n;
  return self;
}

// ['foo'] * 3
template <typename T>
List<T>* NewList(T item, int times) {
  auto self = Alloc<List<T>>();
  StackRoots _roots({&self});

  self->reserve(times);
  self->len_ = times;
  for (int i = 0; i < times; ++i) {
    self->set(i, item);
  }
  return self;
}

// e.g. List<int>
template <typename T>
void list_append(List<T>* self, T item) {
  StackRoots _roots({&self});

  self->reserve(self->len_ + 1);
  self->set(self->len_, item);
  ++self->len_;
}

// e.g. List<Str*>
template <typename T>
void list_append(List<T*>* self, T* item) {
  StackRoots _roots({&self, &item});

  self->reserve(self->len_ + 1);
  self->set(self->len_, item);
  ++self->len_;
}

template <typename T>
void List<T>::append(T item) {
  auto self = this;
  StackRoots _roots({&self});

  // @template_specialization_append_pointer
  //
  // NOTE(Jesse): This is pretty gross, but the use of List<Str*>::append is so
  // pervasive that it's impractical to go through the codebase and change all
  // instances to something more idiomatic.  Furthermore, doing that would not
  // prevent users from calling this on pointer-types in the future, so it
  // seems ill-advised to do so.
  //
  // We cannot make a different template for append (ie `void List<T>::append(T *item)`)
  // because for List<Str*> that would mean `T *item` expands to `Str **item`
  //
  // We also cannot always register a stack-root because this gets expanded for
  // non-heap-allocated types as well (enums, ints, etc).
  //
  // This code will behave poorly if we ever create a List of char*, or any
  // primitive type for that matter.  I tried to create specializations that
  // would either complain at compile time or runtime, unfortunately due to the
  // structure of the include graph it was impossible for me to do it without a
  // great deal of FAFing with includes, which I did not want to do. See:
  // @primitive_pointer_template_specializations_List::append
  //
  //
  //
  // To fix this issue the entire container needs to be re-jigged such that we
  // create instances of List<Str> (and it allocates a buffer of pointers) to
  // solve this problem.
  //
  //
  // Also, for amusement, see comment at @template_specialization_append_pointer
  // which explicitly calls out this problem, then the entire codebase ignores it.
  //
  if (std::is_pointer<T>::value)
  {
    StackRoots _roots({&item});
    list_append(self, item);
  }
  else
  {
    list_append(self, item);
  }

}

// Unfortunately, this gets included in multiple translation units and I didn't
// want to FAF with the include graph anymore today.  Though the root cause of
// this whole debacle should probably be solved.  ie. append(T item) should be append(T *item)
//
// @primitive_pointer_template_specializations_List::append
#if 0
template<>
void List<char*>::append(char*)
{
  assert(!"Invalid use of append on a non-heap-allocated type.");
}

template<>
void List<int*>::append(int*)
{
  assert(!"Invalid use of append on a non-heap-allocated type.");
}

... etc

#endif

#endif // LIST_TYPES_H
