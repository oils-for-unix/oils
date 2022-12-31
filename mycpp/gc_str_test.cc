#include "mycpp/runtime.h"
#include "vendor/greatest.h"

GLOBAL_STR(kSpace, " ");

void debug_string(Str* s) {
  int n = len(s);
  fputs("(", stdout);
  fwrite(s->data_, sizeof(char), n, stdout);
  fputs(")\n", stdout);
}

#define PRINT_INT(i) printf("(%d)\n", (i))
#define PRINT_STRING(str) debug_string(str)

#define PRINT_STR_INT(str, i)     \
  printf("(%s) -> ", str->data_); \
  PRINT_INT(i)

#define STRINGIFY(x) (#x)

#define PRINT_LIST(list)                                         \
  for (ListIter<Str*> iter((list)); !iter.Done(); iter.Next()) { \
    Str* piece = iter.Value();                                   \
    printf("(%.*s) ", len(piece), piece->data_);                 \
  }                                                              \
  printf("\n")

GLOBAL_STR(str4, "egg");

TEST test_str_gc_header() {
  ASSERT(str_equals(kEmptyString, kEmptyString));

  Str* str1 = nullptr;
  Str* str2 = nullptr;
  StackRoots _roots({&str1, &str2});

  str1 = StrFromC("");
  str2 = StrFromC("one\0two", 7);

  ASSERT_EQ_FMT(HeapTag::Opaque, str1->header_.heap_tag, "%d");
  ASSERT_EQ_FMT(kStrHeaderSize + 1, str1->header_.obj_len, "%d");
  ASSERT_EQ_FMT(kStrHeaderSize + 7 + 1, str2->header_.obj_len, "%d");

  // Make sure they're on the heap
#ifndef MARK_SWEEP
  int diff1 = reinterpret_cast<char*>(str1) - gHeap.from_space_.begin_;
  int diff2 = reinterpret_cast<char*>(str2) - gHeap.from_space_.begin_;
  ASSERT(diff1 < 1024);
  ASSERT(diff2 < 1024);
#endif

  ASSERT_EQ(0, len(str1));
  ASSERT_EQ(7, len(str2));

  // Global strings

  ASSERT_EQ('e', str4->data_[0]);
  ASSERT_EQ('g', str4->data_[1]);
  ASSERT_EQ('g', str4->data_[2]);
  ASSERT_EQ('\0', str4->data_[3]);
  ASSERT_EQ(HeapTag::Global, str4->header_.heap_tag);
  ASSERT_EQ(16, str4->header_.obj_len);
  ASSERT_EQ(3, len(str4));

  PASS();
}

// Emulating the gc_heap API.  COPIED from gc_heap_test.cc
TEST test_str_creation() {
  Str* s = StrFromC("foo");
  ASSERT_EQ(3, len(s));
  ASSERT_EQ(0, strcmp("foo", s->data_));

  // String with internal NUL
  Str* s2 = StrFromC("foo\0bar", 7);
  ASSERT_EQ(7, len(s2));
  ASSERT_EQ(0, memcmp("foo\0bar\0", s2->data_, 8));

  Str* s3 = NewStr(1);
  ASSERT_EQ(1, len(s3));
  ASSERT_EQ(0, memcmp("\0\0", s3->data_, 2));

  // Test truncating a string
  //
  // NOTE(Jesse): It's undefined to call `len()` after allocating with this
  // function because it explicitly doesn't set the length!!
  /* Str* s4 = mylib::OverAllocatedStr(7); */

  Str* s4 = NewStr(7);
  ASSERT_EQ(7, len(s4));
  ASSERT_EQ(0, memcmp("\0\0\0\0\0\0\0\0", s4->data_, 8));

  // Hm annoying that we have to do a const_cast
  memcpy(s4->data(), "foo", 3);
  strcpy(s4->data(), "foo");
  s4->SetObjLenFromStrLen(3);

  ASSERT_EQ(3, len(s4));
  ASSERT_EQ(0, strcmp("foo", s4->data_));

  PASS();
}

TEST test_str_find() {
  Str* s = StrFromC("abc-abc");
  ASSERT_EQ(-1, s->find(StrFromC("x")));
  ASSERT_EQ(-1, s->rfind(StrFromC("x")));

  ASSERT_EQ(0, s->find(StrFromC("a")));
  ASSERT_EQ(2, s->find(StrFromC("c")));

  ASSERT_EQ(4, s->rfind(StrFromC("a")));
  ASSERT_EQ(6, s->rfind(StrFromC("c")));

  PASS();
}

TEST test_str_strip() {
  printf("\n");

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

TEST test_str_upper_lower() {
  printf("\n");

  printf("------- Str::upper -------\n");

  {
    Str* result = (StrFromC(""))->upper();
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("")));
  }

  {
    Str* result = (StrFromC("upper"))->upper();
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("UPPER")));
  }

  {
    Str* result = (StrFromC("upPer_uPper"))->upper();
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("UPPER_UPPER")));
  }

  printf("------- Str::lower -------\n");

  {
    Str* result = (StrFromC(""))->lower();
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("")));
  }

  {
    Str* result = (StrFromC("LOWER"))->lower();
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("lower")));
  }

  {
    Str* result = (StrFromC("lOWeR_lowEr"))->lower();
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("lower_lower")));
  }

  printf("---------- Done ----------\n");

  PASS();
}

TEST test_str_replace() {
  printf("\n");

  Str* s0 = StrFromC("ab cd ab ef");

  printf("----- Str::replace -------\n");

  {
    Str* s1 = s0->replace(StrFromC("ab"), StrFromC("--"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("-- cd -- ef")));
  }

  {
    Str* s1 = s0->replace(StrFromC("ab"), StrFromC("----"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("---- cd ---- ef")));
  }

  {
    Str* s1 = s0->replace(StrFromC("ab cd ab ef"), StrFromC("0"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("0")));
  }

  {
    Str* s1 = s0->replace(s0, StrFromC("0"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("0")));
  }

  {
    Str* s1 = s0->replace(StrFromC("no-match"), StrFromC("0"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("ab cd ab ef")));
  }

  {
    Str* s1 = s0->replace(StrFromC("ef"), StrFromC("0"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("ab cd ab 0")));
  }

  {
    Str* s1 = s0->replace(StrFromC("f"), StrFromC("0"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("ab cd ab e0")));
  }

  {
    s0 = StrFromC("ab ab ab");
    Str* s1 = s0->replace(StrFromC("ab"), StrFromC("0"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("0 0 0")));
  }

  {
    s0 = StrFromC("ababab");
    Str* s1 = s0->replace(StrFromC("ab"), StrFromC("0"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("000")));
  }

  {
    s0 = StrFromC("abababab");
    Str* s1 = s0->replace(StrFromC("ab"), StrFromC("0"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("0000")));
  }

  {
    s0 = StrFromC("abc 123");
    Str* s1 = s0->replace(StrFromC("abc"), StrFromC(""));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC(" 123")));
  }

  {
    s0 = StrFromC("abc 123");
    Str* s1 = s0->replace(StrFromC("abc"), StrFromC(""));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC(" 123")));
  }

  {
    s0 = StrFromC("abc 123");
    Str* s1 = s0->replace(StrFromC("abc"), StrFromC("abc"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("abc 123")));
  }

  {
    s0 = StrFromC("aaaa");
    Str* s1 = s0->replace(StrFromC("aa"), StrFromC("bb"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("bbbb")));
  }

  {
    s0 = StrFromC("aaaaaa");
    Str* s1 = s0->replace(StrFromC("aa"), StrFromC("bb"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("bbbbbb")));
  }

  // Test NUL replacement
  {
    Str* s_null = StrFromC("abc\0bcd", 7);
    ASSERT_EQ(7, len(s_null));

    Str* re1 = s_null->replace(StrFromC("ab"), StrFromC("--"));
    ASSERT_EQ_FMT(7, len(re1), "%d");
    ASSERT(str_equals(StrFromC("--c\0bcd", 7), re1));

    Str* re2 = s_null->replace(StrFromC("bc"), StrFromC("--"));
    ASSERT_EQ_FMT(7, len(re2), "%d");
    ASSERT(str_equals(StrFromC("a--\0--d", 7), re2));

    Str* re3 = s_null->replace(StrFromC("\0", 1), StrFromC("__"));
    ASSERT_EQ_FMT(8, len(re3), "%d");
    ASSERT(str_equals(StrFromC("abc__bcd", 8), re3));
  }

  PASS();
}

TEST test_str_just() {
  printf("\n");

  printf("------- Str::ljust -------\n");

  {
    Str* result = (StrFromC(""))->ljust(0, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("")));
  }
  {
    Str* result = (StrFromC(""))->ljust(1, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("_")));
  }
  {
    Str* result = (StrFromC(""))->ljust(4, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("____")));
  }
  {
    Str* result = (StrFromC("x"))->ljust(0, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("x")));
  }
  {
    Str* result = (StrFromC("x"))->ljust(1, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("x")));
  }
  {
    Str* result = (StrFromC("x"))->ljust(2, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("x_")));
  }

  {
    Str* result = (StrFromC("xx"))->ljust(-1, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("xx")));
  }
  {
    Str* result = (StrFromC("xx"))->ljust(0, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("xx")));
  }
  {
    Str* result = (StrFromC("xx"))->ljust(1, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("xx")));
  }
  {
    Str* result = (StrFromC("xx"))->ljust(2, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("xx")));
  }
  {
    Str* result = (StrFromC("xx"))->ljust(4, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("xx__")));
  }

  printf("------- Str::rjust -------\n");
  {
    Str* result = (StrFromC(""))->rjust(0, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("")));
  }
  {
    Str* result = (StrFromC(""))->rjust(1, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("_")));
  }
  {
    Str* result = (StrFromC(""))->rjust(4, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("____")));
  }
  {
    Str* result = (StrFromC("x"))->rjust(0, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("x")));
  }
  {
    Str* result = (StrFromC("x"))->rjust(1, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("x")));
  }
  {
    Str* result = (StrFromC("x"))->rjust(2, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("_x")));
  }

  {
    Str* result = (StrFromC("xx"))->rjust(-1, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("xx")));
  }
  {
    Str* result = (StrFromC("xx"))->rjust(0, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("xx")));
  }
  {
    Str* result = (StrFromC("xx"))->rjust(1, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("xx")));
  }
  {
    Str* result = (StrFromC("xx"))->rjust(2, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("xx")));
  }
  {
    Str* result = (StrFromC("xx"))->rjust(4, StrFromC("_"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("__xx")));
  }
  printf("---------- Done ----------\n");

  PASS();
}

TEST test_str_slice() {
  printf("\n");

  Str* s0 = StrFromC("abcdef");

  printf("------- Str::slice -------\n");

  {  // Happy path
    Str* s1 = s0->slice(0, 5);
    ASSERT(str_equals(s1, StrFromC("abcde")));
    PRINT_STRING(s1);
  }
  {
    Str* s1 = s0->slice(1, 5);
    ASSERT(str_equals(s1, StrFromC("bcde")));
    PRINT_STRING(s1);
  }
  {
    Str* s1 = s0->slice(0, 0);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }
  {
    Str* s1 = s0->slice(0, 6);
    ASSERT(str_equals(s1, StrFromC("abcdef")));
    PRINT_STRING(s1);
  }
  {
    Str* s1 = s0->slice(-6, 6);
    ASSERT(str_equals(s1, StrFromC("abcdef")));
    PRINT_STRING(s1);
  }
  {
    Str* s1 = s0->slice(0, -6);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }
  {
    Str* s1 = s0->slice(-6, -6);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(5, 6);
    ASSERT(str_equals(s1, StrFromC("f")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(6, 6);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(0, -7);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(-7, -7);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(-7, 0);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(6, 6);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(7, 7);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(6, 5);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(7, 5);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(7, 6);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(7, 7);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  printf("---------- Done ----------\n");

  //  NOTE(Jesse): testing all permutations of boundary conditions for
  //  assertions
  int max_len = (len(s0) + 2);
  int min_len = -max_len;

  for (int outer = min_len; outer <= max_len; ++outer) {
    for (int inner = min_len; inner <= max_len; ++inner) {
      s0->slice(outer, inner);
    }
  }

  PASS();
}

TEST test_str_concat() {
  printf("\n");

  printf("------- str_concat -------\n");

  {
    Str* result = str_concat(StrFromC(""), StrFromC(""));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("")));
  }
  {
    Str* result = str_concat(StrFromC("a"), StrFromC(""));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("a")));
  }
  {
    Str* result = str_concat(StrFromC("aa"), StrFromC(""));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("aa")));
  }
  {
    Str* result = str_concat(StrFromC(""), StrFromC("b"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("b")));
  }
  {
    Str* result = str_concat(StrFromC(""), StrFromC("bb"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("bb")));
  }
  {
    Str* result = str_concat(StrFromC("a"), StrFromC("b"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("ab")));
  }
  {
    Str* result = str_concat(StrFromC("aa"), StrFromC("b"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("aab")));
  }
  {
    Str* result = str_concat(StrFromC("a"), StrFromC("bb"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("abb")));
  }
  {
    Str* result = str_concat(StrFromC("aa"), StrFromC("bb"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("aabb")));
  }

  printf("------- str_concat3 -------\n");

  {
    Str* result = str_concat3(StrFromC(""), StrFromC(""), StrFromC(""));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("")));
  }
  {
    Str* result = str_concat3(StrFromC("a"), StrFromC(""), StrFromC(""));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("a")));
  }
  {
    Str* result = str_concat3(StrFromC("a"), StrFromC("b"), StrFromC(""));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("ab")));
  }
  {
    Str* result = str_concat3(StrFromC("a"), StrFromC("b"), StrFromC("c"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("abc")));
  }
  {
    Str* result = str_concat3(StrFromC("a"), StrFromC(""), StrFromC("c"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("ac")));
  }

  {
    Str* result = str_concat3(StrFromC("aa"), StrFromC(""), StrFromC(""));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("aa")));
  }
  {
    Str* result = str_concat3(StrFromC("aa"), StrFromC("b"), StrFromC(""));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("aab")));
  }
  {
    Str* result = str_concat3(StrFromC("aa"), StrFromC("b"), StrFromC("c"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("aabc")));
  }
  {
    Str* result = str_concat3(StrFromC("aa"), StrFromC(""), StrFromC("c"));
    PRINT_STRING(result);
    ASSERT(str_equals(result, StrFromC("aac")));
  }

  printf("---------- Done ----------\n");

  PASS();
}

// TODO(Jesse): Might be worth making sure to_int() doesn't accept invalid
// inputs, but I didn't go down the rat hole of reading the spec for strtol to
// figure out if what that function considers an invalid input is the same as
// what Python considers an invalid input.
//
// I did at least find out that it doesn't accept hex values (encoded as
// "0xFFFFFFFF").  I'd assume it also wouldn't accept hex values without the 0x
// prefix, and setting the base to 16, but I did not verify.
//
TEST test_str_to_int() {
  printf("\n");

  printf("------- to_int -------\n");

  {
    Str* input = StrFromC("0");
    int result = to_int(input);
    PRINT_STR_INT(input, result);
    ASSERT(result == 0);
  }
  {
    Str* input = StrFromC("1");
    int result = to_int(input);
    PRINT_STR_INT(input, result);
    ASSERT(result == 1);
  }
  {
    Str* input = StrFromC("-1");
    int result = to_int(input);
    PRINT_STR_INT(input, result);
    ASSERT(result == -1);
  }
  {
    Str* input = StrFromC("100");
    int result = to_int(input);
    PRINT_STR_INT(input, result);
    ASSERT(result == 100);
  }
  {
    Str* input = StrFromC("2147483647");  // 0x7FFFFFFF
    int result = to_int(input);
    PRINT_STR_INT(input, result);
    ASSERT(result == INT_MAX);
  }
  {
    Str* input = StrFromC("-2147483648");  // -0x7FFFFFFF - 1
    int result = to_int(input);
    PRINT_STR_INT(input, result);
    ASSERT(result == INT_MIN);
  }

  printf("---------- Done ----------\n");

  PASS();
}

TEST test_str_size() {
  printf("---------- str_size ----------\n");

  PRINT_INT(kStrHeaderSize);
  PRINT_INT((int)sizeof(Str));

  ASSERT(kStrHeaderSize == 12);
  ASSERT(sizeof(Str) == 16);

  printf("---------- Done ----------\n");
  PASS();
}

TEST test_str_startswith() {
  printf("------ Str::helpers ------\n");

  ASSERT((StrFromC(""))->startswith(StrFromC("")) == true);
  ASSERT((StrFromC(" "))->startswith(StrFromC("")) == true);
  ASSERT((StrFromC(" "))->startswith(StrFromC(" ")) == true);

  ASSERT((StrFromC("  "))->startswith(StrFromC(" ")) == true);

  printf("---------- Done ----------\n");

  PASS();
}

TEST test_str_contains() {
  bool b;
  Str* s = nullptr;
  Str* nul = nullptr;
  StackRoots _roots({&s, &nul});

  log("  str_contains");

  s = StrFromC("foo\0 ", 5);
  ASSERT(str_contains(s, kSpace));

  // this ends with a NUL, but also has a NUL terinator.
  nul = StrFromC("\0", 1);
  ASSERT(str_contains(s, nul));
  ASSERT(!str_contains(kSpace, nul));

  b = str_contains(StrFromC("foo\0a", 5), StrFromC("a"));
  ASSERT(b == true);

  // this ends with a NUL, but also has a NUL terinator.
  s = StrFromC("foo\0", 4);
  b = str_contains(s, StrFromC("\0", 1));
  ASSERT(b == true);

  // Degenerate cases
  b = str_contains(StrFromC(""), StrFromC(""));
  ASSERT(b == true);
  b = str_contains(StrFromC("foo"), StrFromC(""));
  ASSERT(b == true);
  b = str_contains(StrFromC(""), StrFromC("f"));
  ASSERT(b == false);

  // Short circuit
  b = str_contains(StrFromC("foo"), StrFromC("too long"));
  ASSERT(b == false);

  b = str_contains(StrFromC("foo"), StrFromC("oo"));
  ASSERT(b == true);

  b = str_contains(StrFromC("foo"), StrFromC("ood"));
  ASSERT(b == false);

  b = str_contains(StrFromC("foo\0ab", 6), StrFromC("ab"));
  ASSERT(b == true);

  PASS();
}

TEST test_str_split() {
  printf("\n");

  Str* s0 = StrFromC("abc def");

  printf("------- Str::split -------\n");

  {
    List<Str*>* split_result = s0->split(StrFromC(" "));
    PRINT_LIST(split_result);
    ASSERT(len(split_result) == 2);
    ASSERT(are_equal(split_result->index_(0), StrFromC("abc")));
    ASSERT(are_equal(split_result->index_(1), StrFromC("def")));
  }

  {
    List<Str*>* split_result = (StrFromC("###"))->split(StrFromC("#"));
    PRINT_LIST(split_result);
    ASSERT(len(split_result) == 4);
    ASSERT(are_equal(split_result->index_(0), StrFromC("")));
    ASSERT(are_equal(split_result->index_(1), StrFromC("")));
    ASSERT(are_equal(split_result->index_(2), StrFromC("")));
    ASSERT(are_equal(split_result->index_(3), StrFromC("")));
  }

  {
    List<Str*>* split_result = (StrFromC(" ### "))->split(StrFromC("#"));
    PRINT_LIST(split_result);
    ASSERT(len(split_result) == 4);
    ASSERT(are_equal(split_result->index_(0), StrFromC(" ")));
    ASSERT(are_equal(split_result->index_(1), StrFromC("")));
    ASSERT(are_equal(split_result->index_(2), StrFromC("")));
    ASSERT(are_equal(split_result->index_(3), StrFromC(" ")));
  }

  {
    List<Str*>* split_result = (StrFromC(" # "))->split(StrFromC(" "));
    PRINT_LIST(split_result);
    ASSERT(len(split_result) == 3);
    ASSERT(are_equal(split_result->index_(0), StrFromC("")));
    ASSERT(are_equal(split_result->index_(1), StrFromC("#")));
    ASSERT(are_equal(split_result->index_(2), StrFromC("")));
  }

  {
    List<Str*>* split_result = (StrFromC("  #"))->split(StrFromC("#"));
    PRINT_LIST(split_result);
    ASSERT(len(split_result) == 2);
    ASSERT(are_equal(split_result->index_(0), StrFromC("  ")));
    ASSERT(are_equal(split_result->index_(1), StrFromC("")));
  }

  {
    List<Str*>* split_result = (StrFromC("#  #"))->split(StrFromC("#"));
    PRINT_LIST(split_result);
    ASSERT(len(split_result) == 3);
    ASSERT(are_equal(split_result->index_(0), StrFromC("")));
    ASSERT(are_equal(split_result->index_(1), StrFromC("  ")));
    ASSERT(are_equal(split_result->index_(2), StrFromC("")));
  }

  {
    List<Str*>* split_result = (StrFromC(""))->split(StrFromC(" "));
    PRINT_LIST(split_result);
    ASSERT(len(split_result) == 1);
    ASSERT(are_equal(split_result->index_(0), StrFromC("")));
  }

  {
    List<Str*>* result = (StrFromC("a,b,c,d,e,f,g"))->split(StrFromC(","));
    PRINT_LIST(result);
    ASSERT(len(result) == 7);
    ASSERT(are_equal(result->index_(0), StrFromC("a")));

    result = (StrFromC("a,b,c,d,e,f,g"))->split(StrFromC(","), 3);
    PRINT_LIST(result);
    ASSERT(len(result) == 4);
    ASSERT(are_equal(result->index_(0), StrFromC("a")));
    ASSERT(are_equal(result->index_(1), StrFromC("b")));
    ASSERT(are_equal(result->index_(2), StrFromC("c")));
    ASSERT(are_equal(result->index_(3), StrFromC("d,e,f,g")));
  }

  // NOTE(Jesse): Failure case.  Not sure if we care about supporting this.
  // It might happen if we do something like : 'weahtevr'.split()
  // Would need to check on what the Python interpreter does in that case to
  // decipher what we'd expect to see.
  //
  /* { */
  /*   List<Str*> *split_result = (StrFromC("weahtevr"))->split(0); */
  /*   PRINT_LIST(split_result); */
  /*   ASSERT(len(split_result) == 1); */
  /*   ASSERT(are_equal(split_result->index_(0), StrFromC(""))); */
  /* } */

  printf("---------- Done ----------\n");

  PASS();
}

TEST test_str_join() {
  printf("\n");

  printf("-------- Str::join -------\n");

  {
    Str* result =
        (StrFromC(""))->join(NewList<Str*>({StrFromC("abc"), StrFromC("def")}));
    PRINT_STRING(result);
    ASSERT(are_equal(result, StrFromC("abcdef")));
  }
  {
    Str* result = (StrFromC(" "))
                      ->join(NewList<Str*>({StrFromC("abc"), StrFromC("def"),
                                            StrFromC("abc"), StrFromC("def"),
                                            StrFromC("abc"), StrFromC("def"),
                                            StrFromC("abc"), StrFromC("def")}));
    PRINT_STRING(result);
    ASSERT(are_equal(result, StrFromC("abc def abc def abc def abc def")));
  }

  printf("---------- Done ----------\n");

  PASS();
}

TEST test_str_format() {
  // check trivial case
  ASSERT(str_equals(StrFromC("foo"), StrFormat("foo")));

  // check %s
  ASSERT(str_equals(StrFromC("foo"), StrFormat("%s", StrFromC("foo"))));
  ASSERT(str_equals(StrFromC("              foo"),
                    StrFormat("%17s", StrFromC("foo"))));
  ASSERT(str_equals(StrFromC("foo"), StrFormat("foo%s", StrFromC(""))));

  // check that NUL bytes are preserved
  ASSERT(str_equals(StrFromC("foo b\0ar", 8),
                    StrFormat("foo %s", StrFromC("b\0ar", 4))));
  ASSERT(str_equals(StrFromC("foo\0bar", 7),
                    StrFormat(StrFromC("foo\0%s", 6), StrFromC("bar"))));

  // check %d
  ASSERT(str_equals(StrFromC("12345"), StrFormat("%d", 12345)));
  ASSERT(str_equals(StrFromC("            12345"), StrFormat("%17d", 12345)));
  ASSERT(str_equals(StrFromC("00000000000012345"), StrFormat("%017d", 12345)));

  // check %o
  ASSERT(str_equals(StrFromC("30071"), StrFormat("%o", 12345)));
  ASSERT(str_equals(StrFromC("            30071"), StrFormat("%17o", 12345)));
  ASSERT(str_equals(StrFromC("00000000000030071"), StrFormat("%017o", 12345)));

  // check that %% escape works
  ASSERT(str_equals(StrFromC("%12345"), StrFormat("%%%d", 12345)));
  ASSERT(str_equals(StrFromC("%12345%%"), StrFormat("%%%d%%%%", 12345)));

  // check that operators can be combined
  ASSERT(str_equals(StrFromC("ABC      1234DfooEF"),
                    StrFormat("ABC%10dD%sEF", 1234, StrFromC("foo"))));

  // check StrFormat(char*) == StrFormat(Str*)
  ASSERT(str_equals(StrFormat("%10d%s", 1234, StrFromC("foo")),
                    StrFormat(StrFromC("%10d%s"), 1234, StrFromC("foo"))));

  // check that %r behaves like repr()
  ASSERT(str_equals0("''", StrFormat("%r", kEmptyString)));
  ASSERT(str_equals0("\"'\"", StrFormat("%r", StrFromC("'"))));
  ASSERT(str_equals0("\"'single'\"", StrFormat("%r", StrFromC("'single'"))));
  ASSERT(str_equals0("'\"double\"'", StrFormat("%r", StrFromC("\"double\""))));
  ASSERT(str_equals0("'NUL \\x00 NUL'",
                     StrFormat("%r", StrFromC("NUL \x00 NUL", 9))));
  ASSERT(str_equals0("'tab\\tline\\nline\\r\\n'",
                     StrFormat("%r", StrFromC("tab\tline\nline\r\n"))));
  ASSERT(str_equals0("'high \\xff \\xfe high'",
                     StrFormat("%r", StrFromC("high \xFF \xFE high"))));

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(test_str_gc_header);
  RUN_TEST(test_str_creation);

  // Members
  RUN_TEST(test_str_find);
  RUN_TEST(test_str_strip);
  RUN_TEST(test_str_upper_lower);
  RUN_TEST(test_str_replace);
  RUN_TEST(test_str_just);
  RUN_TEST(test_str_slice);

  // Free functions
  RUN_TEST(test_str_concat);
  RUN_TEST(test_str_to_int);
  RUN_TEST(test_str_size);
  RUN_TEST(test_str_contains);

  RUN_TEST(test_str_startswith);

  RUN_TEST(test_str_split);
  RUN_TEST(test_str_join);

  RUN_TEST(test_str_format);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
