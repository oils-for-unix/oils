#include "_gen/frontend/arg_types.h"
#include "_gen/core/runtime.asdl.h"
#include "vendor/greatest.h"

using runtime_asdl::value;

TEST opaque_test() {
  // struct for command -v is HeapTag::Opaque

  auto attrs = Alloc<Dict<Str*, runtime_asdl::value_t*>>();
  StackRoots _r({&attrs});

  auto b = Alloc<value::Bool>(true);
  attrs->set(StrFromC("v"), b);

  for (int i = 0; i < 10; ++i) {
    auto m = Alloc<arg_types::command>(attrs);
    StackRoots _r2({&m});

    mylib::MaybeCollect();

    ASSERT_EQ(true, m->v);
  }

  PASS();
}

TEST pointer_test() {
  // struct for printf -v is has Str*

  auto attrs = Alloc<Dict<Str*, runtime_asdl::value_t*>>();
  StackRoots _r({&attrs});

  auto s = Alloc<value::Str>(StrFromC("hi %s"));
  attrs->set(StrFromC("v"), s);

  for (int i = 0; i < 10; ++i) {
    auto m = Alloc<arg_types::printf>(attrs);
    StackRoots _r2({&m});

    mylib::MaybeCollect();

    ASSERT(str_equals(StrFromC("hi %s"), m->v));
  }

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(opaque_test);
  RUN_TEST(pointer_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
