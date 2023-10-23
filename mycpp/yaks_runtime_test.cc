// yaks_runtime_test.cc
//
// Related to small_str_test.cc

#include <inttypes.h>
#include <limits.h>  // HOST_NAME_MAX
#include <unistd.h>  // gethostname()

#include <new>  // placement new

#include "mycpp/common.h"
#include "mycpp/gc_obj.h"  // ObjHeader
#include "mycpp/runtime.h"
#include "vendor/greatest.h"

// namespace yaks {

/*

Design
======

Everything is a value

- yaks_val_t contains a uint64_t  ?
  - this means any Str, List, Dict, Tuple, or class
  - can List and Dict have type tag in addition to pointer?

These are less than 8 bytes:

- int32_t
- float
- enum class value_e {}

Features that mycpp runtime doesn't have:

- More efficient rooting, either:
  - our StackRoots({&a, &b, ...}) is slow
  - our StackRoot takes up a lot of code space!
- Either
  - Shadow Stack for Garbage Collection
    - It's better to spill pointers to a separate frame
  - Hybrid rooting
    - ParamRoot, ParamRoot, SortedPointerRoots,

tagged value =
  Int %Int
| Frame %Dict[str, str]

Tagged Pointers ("Boxless optimization")

- Immediate Values - 8 bytes for variant type tag
  - Zero-arg constructors are integers
  - int32_t
  - float
  - Small Str
    - 4 bits len
      - how is this shared with type_tag?
      - are we reserving half of this space for small_str?
    - 6 bytes data
    - 1 byte nullptr
  - Pointer

Later:

- Value types?  How does the GC scan them on the stack???  That is hard

*/

/* Class translation


class Slice:
  def __init__(self, s: str, start: int, length: int):
    self.s = s
    self.start = start
    self.length = length

  def get(self) -> str:
    return self.s[self.start : self.start + self.length]


*/

union yaks_val_t {
  void* heap_obj;
  bool b;
  float f;

  int32_t i;
  uint64_t u64;  // the whole

  // TODO: where do we put
  // - 1 byte type_tag?  Or do we have fewer than that?  Maybe 5 bits, since 3
  // are for small_str len?
  //   - that's 32 immediate types, and then you can overflow into heap?
  //   - NO WE only have THREE BITS because our allocator is 24 or 48 byte
  //   aligned
  //   - so we have at most 8 immediate values, and the rest heap values?
  //   - but SmallStr always takes up some space

  // - NUL terminator for SmallStr
};

class Slice {
 public:
  Slice(Str* s, int start, int length) {
    // TODO: allocate Members
    self_.heap_obj = Alloc<Members>();

    self()->s_ = s;
    self()->start_ = start;
    self()->length_ = length;
  }

  struct Members {
    Str* s_;
    int start_;
    int length_;

    static constexpr ObjHeader obj_header() {
      return ObjHeader::ClassFixed(field_mask(), sizeof(Members));
    }
    static constexpr uint32_t field_mask() {
      return maskbit(offsetof(Members, s_));
    }
  };

  Members* self() {
    return static_cast<Members*>(self_.heap_obj);
  }

  int start() {
    return self()->start_;
  }

  // Field Accessors -- this will make the generated code a lot longer?
  // Naming convention is like protobuf

  int length() {
    return self()->length_;
  }

  // Methods
  Str* Get() {
    // return StrFromC("yo");

    int n = self()->length_;

    log("start = %d", self()->start_);
    log("n = %d", n);

    Str* result = NewStr(n);

    memcpy(result->data_, self()->s_->data_ + self()->start_, n);

    result->data_[n] = '\0';

    log("result->data %s", result->data_);

    return result;
  }

  yaks_val_t self_;
};

void SliceFunc(Slice myslice) {
  Str* s = myslice.Get();
  log("val = %s", s->data_);
  print(s);

  log("start %d length %d", myslice.start(), myslice.length());
}

TEST yaks_test() {
  Slice myslice(StrFromC("hello"), 1, 3);

  log("myslice %p", &myslice);

  SliceFunc(myslice);

  PASS();
}

// Based on _gen/core/runtime.asdl.h

class value_t {
 protected:
  value_t() {
  }

 public:
  int tag() const {
    return ObjHeader::FromObject(this)->type_tag;
  }
  // hnode_t* PrettyTree();
  DISALLOW_COPY_AND_ASSIGN(value_t)
};

//}  // namespace small_str_test

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  // gHeap.Init();

  GREATEST_MAIN_BEGIN();

  // RUN_TEST(yaks::yaks_test);
  RUN_TEST(yaks_test);

  // gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
