#include "cpp/leaky_core.h"
#include "cpp/leaky_core_error.h"
#include "vendor/greatest.h"

static_assert(offsetof(Obj, field_mask_) == offsetof(error::Usage, field_mask_),
              "Invalid layout");
static_assert(offsetof(Obj, field_mask_) ==
                  offsetof(error::_ErrorWithLocation, field_mask_),
              "Invalid layout");

TEST exceptions_test() {
  bool caught = false;
  try {
    throw Alloc<error::Usage>(StrFromC("msg"), 42);
  } catch (error::Usage* e) {
    log("e %p", e);
    gHeap.RootInCurrentFrame(e);
    caught = true;
  }

  ASSERT(caught);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(exceptions_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
