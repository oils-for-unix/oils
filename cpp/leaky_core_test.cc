#include "cpp/leaky_core.h"

#include "vendor/greatest.h"

TEST environ_test() {
  Dict<Str*, Str*>* env = pyos::Environ();
  Str* p = env->get(StrFromC("PATH"));
  ASSERT(p != nullptr);
  log("PATH = %s", p->data_);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(environ_test);

  gHeap.OnProcessExit();

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
