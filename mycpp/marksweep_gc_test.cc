
#include "mycpp/runtime.h"
#include "vendor/greatest.h"

TEST string_collection_test() {

  Str *test_str = StrFromC("foo");
  {
    ASSERT(are_equal(test_str, StrFromC("foo")));

    StackRoots _roots({&test_str});

    ASSERT(are_equal(test_str, StrFromC("foo")));

    gHeap.Collect();

    ASSERT(are_equal(test_str, StrFromC("foo")));
  }

  // NOTE(Jesse): Technically UB.  If the collector hits between when the roots
  // go out of scope in the above block we'll get a UAF here.  ASAN should
  // detect this but we currently have no way of programatically verifying that
  // ASAN detects bugs.  AFAIK asan is not 100% reliable, so maybe that's a
  // path fraught with peril anyhow.
  //
  /* ASSERT(are_equal(test_str, StrFromC("foo"))); */

  gHeap.Collect();

  // NOTE(Jesse): ASAN detects UAF here when I tested by toggling this on
  //
  /* ASSERT(are_equal(test_str, StrFromC("foo"))); */

  PASS();
}


TEST list_collection_test() {

  {
    Str *test_str0 = StrFromC("foo_0");
    Str *test_str1 = StrFromC("foo_1");
    List<Str*> *test_list = NewList<Str*>();

    StackRoots _roots({&test_str0, &test_str1, &test_list});

    test_list->append(test_str0);
    test_list->append(test_str1);

    {
      auto str0 = test_list->index_(0);
      ASSERT(are_equal(str0, test_str0));
      auto str1 = test_list->index_(1);
      ASSERT(are_equal(str1, test_str1));
    }

    gHeap.Collect();

    {
      auto str0 = test_list->index_(0);
      ASSERT(are_equal(str0, test_str0));
      auto str1 = test_list->index_(1);
      ASSERT(are_equal(str1, test_str1));
    }
  }

  gHeap.Collect();

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init(Megabytes(64));

  PRINT_GC_MODE_STRING();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(string_collection_test);
  RUN_TEST(list_collection_test);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
