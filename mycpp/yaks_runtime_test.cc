// yaks_runtime_test.cc
//
// Related to small_str_test.cc

#include <inttypes.h>
#include <limits.h>  // HOST_NAME_MAX
#include <unistd.h>  // gethostname()

#include <new>  // placement new

// #include "mycpp/runtime.h"
#include "mycpp/common.h"
#include "mycpp/gc_obj.h"  // ObjHeader
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

- Shadow Stack for Garbage Collection
  - our StackRoots({&a, &b, ...}) is slow
  - our StackRoot takes up a lot of code space!
  - It's better to spill pointers to a separate frame

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

TEST yaks_test() {
  log("hi = %s", "x");

  PASS();
}

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
