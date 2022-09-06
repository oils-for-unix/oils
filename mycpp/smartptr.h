// OLD UNUSED CODE

#include <assert.h>

#include "mycpp/gc_heap.h"

template <typename T>
class Local {
  // We can garbage collect at any Alloc() invocation, so we need a level of
  // indirection for locals / pointers directly on the stack.  Pointers on the
  // heap are updated by the Cheney GC algorithm.

 public:
  Local() : raw_pointer_(nullptr) {
  }

  // IMPLICIT conversion.  No 'explicit'.
  Local(T* raw_pointer) : raw_pointer_(raw_pointer) {
    // TODO(Jesse): Does this get called?
    // Is this NotImplemented() or InvalidCodePath() ??
    assert(0);
    // gHeap.PushRoot(this);
  }

  // Copy constructor, e.g. f(mylocal) where f(Local<T> param);
  Local(const Local& other) : raw_pointer_(other.raw_pointer_) {
    // TODO(Jesse): Does this get called?
    // Is this NotImplemented() or InvalidCodePath() ??
    assert(0);
    // gHeap.PushRoot(this);
  }

  void operator=(const Local& other) {  // Assignment operator
    raw_pointer_ = other.raw_pointer_;

    // Note: we could try to avoid PushRoot() as an optimization.  Example:
    //
    // Local<Str> a = StrFromC("foo");
    // Local<Str> b;
    // b = a;  // invokes operator=, it's already a root
    //
    // Local<Str> c = myfunc();  // T* constructor takes care of PushRoot()

    // log("operator=");

    // However the problem is that then we'll have an unbalanced PopRoot().
    // So we keep it for now.
    gHeap.PushRoot(this);
  }

  ~Local() {
    gHeap.PopRoot();
  }

  // This cast operator overload allows:
  //
  // Local<Str> s = StrFromC("foo");
  // node->mystr = s;  // convert from Local to raw
  //
  // As well as:
  //
  // Local<List<Str*>> strings = Alloc<List<Str*>>();
  // strings->append(StrFromC("foo"));  // convert from local to raw
  //
  // The heap should NOT have locals!  List<Str> and not List<Local<Str>>.
  //
  // Note: This could be considered dangerous if we don't maintain
  // discipline.
  //
  // https://www.informit.com/articles/article.aspx?p=31529&seqNum=7
  //
  // Putting .get() at the call site in mycpp is more explicit. The
  // readability of the generated code is important!
#if 1
  operator T*() {
    return raw_pointer_;
  }
#endif

  // Allows ref->field and ref->method()
  T* operator->() const {
    // log("operator->");
    return raw_pointer_;
  }
  T* Get() const {
    return raw_pointer_;
  }
  // called by the garbage collector when moved to a new location!
  void Update(T* moved) {
    raw_pointer_ = moved;
  }

  // Dereference to get the real value.  Doesn't seem like we need this.
#if 0
  T operator*() const {
    //log("operator*");
    return *raw_pointer_;
  }
#endif

  T* raw_pointer_;
};

template <typename T>
class Param : public Local<T> {
  // This could be an optimization like SpiderMonkey's Handle<T> vs Rooted<T>.
  // We use the names Param<T> and Local<T>.

 public:
  // hm this is awkward, I think we should NOT inherit!  We should only
  // convert.
  Param(const Local<T>& other) : Local<T>(nullptr) {
    this->raw_pointer_ = other.raw_pointer_;
  }

  ~Param() {  // do not PopRoot()
  }

  // Construct from T* -- PushRoot()
  // Construct from Local<T> -- we don't need to PushRoot()
  // operator= -- I don't think we need to PushRoot()
};
