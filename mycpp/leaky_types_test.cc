#ifdef LEAKY_BINDINGS
  #include "mycpp/mylib_old.h"
using mylib::StrFromC;
#else
  #include "mycpp/gc_builtins.h"
  #include "mycpp/gc_types.h"
using gc_heap::gHeap;
using gc_heap::kEmptyString;
using gc_heap::Str;
using gc_heap::StrFromC;
#endif

#include "vendor/greatest.h"

void debug_string(Str* s) {
  int n = len(s);
  fputs("(", stdout);
  fwrite(s->data_, sizeof(char), n, stdout);
  fputs(")\n", stdout);
}

#define PRINT_STRING(str) debug_string(str)

TEST test_str_strip() {
  printf("\n");

#if 0
  printf("------- Str::lstrip -------\n");

  {
    Str* result = (StrFromC("\n "))->lstrip();
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("")));
  }

  {
    Str* result = (StrFromC("\n #"))->lstrip();
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("#")));
  }

  {
    Str* result = (StrFromC("\n  #"))->lstrip();
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("#")));
  }

  {
    Str* result = (StrFromC("\n  #"))->lstrip();
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("#")));
  }

  {
    Str* result = (StrFromC("#"))->lstrip(StrFromC("#"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("")));
  }

  {
    Str* result = (StrFromC("##### "))->lstrip(StrFromC("#"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC(" ")));
  }

  {
    Str* result = (StrFromC("#  "))->lstrip(StrFromC("#"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("  ")));
  }

  {
    Str* result = (StrFromC(" # "))->lstrip(StrFromC("#"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC(" # ")));
  }
#endif

  printf("------- Str::rstrip -------\n");

  {
    Str* result = (StrFromC(" \n"))->rstrip();
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("")));
  }

  {
    Str* result = (StrFromC("# \n"))->rstrip();
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("#")));
  }

  {
    Str* result = (StrFromC("#  \n"))->rstrip();
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("#")));
  }

  {
    Str* s1 = StrFromC(" \n#");
    Str* result = s1->rstrip();
    PRINT_STRING(result);
    ASSERT(str_equals(result, s1));
    ASSERT_EQ(result, s1);  // objects are identical
  }

  {
    Str* result = (StrFromC("#  \n"))->rstrip();
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("#")));
  }

  {
    Str* result = (StrFromC("#"))->rstrip(StrFromC("#"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("")));
  }

  {
    Str* result = (StrFromC(" #####"))->rstrip(StrFromC("#"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC(" ")));
  }

  {
    Str* result = (StrFromC("  #"))->rstrip(StrFromC("#"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("  ")));
  }

  {
    Str* result = (StrFromC(" # "))->rstrip(StrFromC("#"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC(" # ")));
  }

  printf("------- Str::strip -------\n");

  {
    Str* result = (StrFromC(""))->strip();
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("")));

    ASSERT_EQ(result, kEmptyString);  // identical objects
  }

  {
    Str* result = (StrFromC(" "))->strip();
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("")));

    ASSERT_EQ(result, kEmptyString);  // identical objects
  }

  {
    Str* result = (StrFromC("  \n"))->strip();
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("")));

    ASSERT_EQ(result, kEmptyString);  // identical objects
  }

  {
    Str* result = (StrFromC(" ## "))->strip();
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("##")));
  }

  {
    Str* result = (StrFromC("  hi  \n"))->strip();
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("hi")));
  }

  printf("---------- Done ----------\n");

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init(1 << 20);

  GREATEST_MAIN_BEGIN();

  RUN_TEST(test_str_strip);

  GREATEST_MAIN_END();
  return 0;
}
