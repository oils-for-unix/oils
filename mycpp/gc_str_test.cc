#include "mycpp/gc_str.h"

#include <limits.h>  // INT_MAX

#include "mycpp/comparators.h"  // str_equals
#include "mycpp/gc_alloc.h"     // gHeap
#include "mycpp/gc_builtins.h"  // print()
#include "mycpp/gc_list.h"
#include "vendor/greatest.h"

GLOBAL_STR(kSpace, " ");
GLOBAL_STR(kStrFood, "food");
GLOBAL_STR(kWithNull, "foo\0bar");

static void ShowString(BigStr* s) {
  int n = len(s);
  fputs("(", stdout);
  fwrite(s->data_, sizeof(char), n, stdout);
  fputs(")\n", stdout);
}

static void ShowStringInt(BigStr* str, int i) {
  printf("(%s) -> ", str->data_);
  printf("(%d)\n", i);
}

static void ShowList(List<BigStr*>* list) {
  for (ListIter<BigStr*> iter((list)); !iter.Done(); iter.Next()) {
    BigStr* piece = iter.Value();
    printf("(%.*s) ", len(piece), piece->data_);
  }
  printf("\n");
}

GLOBAL_STR(str4, "egg");

TEST test_str_gc_header() {
  ASSERT(str_equals(kEmptyString, kEmptyString));

  BigStr* str1 = nullptr;
  BigStr* str2 = nullptr;
  StackRoots _roots({&str1, &str2});

  str1 = StrFromC("");
  str2 = StrFromC("one\0two", 7);

  ASSERT_EQ_FMT(HeapTag::Opaque, ObjHeader::FromObject(str2)->heap_tag, "%d");
  // ASSERT_EQ_FMT(kStrHeaderSize + 1, str1->header_.obj_len, "%d");
  // ASSERT_EQ_FMT(kStrHeaderSize + 7 + 1, str2->header_.obj_len, "%d");

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
  ASSERT_EQ(HeapTag::Global, ObjHeader::FromObject(str4)->heap_tag);
  // ASSERT_EQ(16, str4->header_.obj_len);
  ASSERT_EQ(3, len(str4));

  PASS();
}

// Emulating the gc_heap API.  COPIED from gc_heap_test.cc
TEST test_str_creation() {
  BigStr* s = StrFromC("foo");
  ASSERT_EQ(3, len(s));
  ASSERT_EQ(0, strcmp("foo", s->data_));

  // String with internal NUL
  BigStr* s2 = StrFromC("foo\0bar", 7);
  ASSERT_EQ(7, len(s2));
  ASSERT_EQ(0, memcmp("foo\0bar\0", s2->data_, 8));

  BigStr* s3 = NewStr(1);
  ASSERT_EQ(1, len(s3));
  ASSERT_EQ('\0', s3->data_[1]);  // NUL terminated

  // Test truncating a string
  //
  // NOTE(Jesse): It's undefined to call `len()` after allocating with this
  // function because it explicitly doesn't set the length!!
  /* BigStr* s4 = mylib::OverAllocatedStr(7); */

  BigStr* s4 = NewStr(7);
  ASSERT_EQ(7, len(s4));
  ASSERT_EQ('\0', s4->data_[7]);

  // Hm annoying that we have to do a const_cast
  memcpy(s4->data_, "foo", 3);
  s4->MaybeShrink(3);
  ASSERT_EQ('\0', s4->data_[3]);

  ASSERT_EQ(3, len(s4));
  ASSERT_EQ(0, strcmp("foo", s4->data_));

  PASS();
}

TEST test_str_find() {
  BigStr* s = StrFromC("abc-abc\xff");
  ASSERT_EQ_FMT(-1, s->find(StrFromC("x")), "%d");
  ASSERT_EQ_FMT(-1, s->rfind(StrFromC("x")), "%d");

  // find() 1 byte
  ASSERT_EQ_FMT(0, s->find(StrFromC("a")), "%d");
  ASSERT_EQ_FMT(2, s->find(StrFromC("c")), "%d");

  // find() from starting pos
  ASSERT_EQ_FMT(4, s->find(StrFromC("a"), 4), "%d");
  ASSERT_EQ_FMT(6, s->find(StrFromC("c"), 4), "%d");

  ASSERT_EQ_FMT(-1, s->find(StrFromC("a"), 7), "%d");
  ASSERT_EQ_FMT(-1, s->find(StrFromC("c"), 7), "%d");

  // rfind() 1 byte
  ASSERT_EQ_FMT(4, s->rfind(StrFromC("a")), "%d");
  ASSERT_EQ_FMT(6, s->rfind(StrFromC("c")), "%d");

  // end before finding it
  ASSERT_EQ_FMT(-1, s->find(StrFromC("a"), 0, 0), "%d");
  ASSERT_EQ_FMT(-1, s->find(StrFromC("c"), 0, 2), "%d");

  // find multiple bytes
  ASSERT_EQ_FMT(0, s->find(StrFromC("abc")), "%d");
  ASSERT_EQ_FMT(4, s->find(StrFromC("abc"), 1), "%d");

  // find empty string
  ASSERT_EQ_FMT(0, s->find(kEmptyString), "%d");
  ASSERT_EQ_FMT(5, s->find(kEmptyString, 5), "%d");

  // Empty string not found in degenerate range
  ASSERT_EQ_FMT(-1, s->find(kEmptyString, 5, 4), "%d");

  ASSERT_EQ_FMT(5, s->find(kEmptyString, 5, 5), "%d");
  ASSERT_EQ_FMT(5, s->find(kEmptyString, 5, 6), "%d");

  // Not used by Oils
  // ASSERT_EQ_FMT(4, s->rfind(StrFromC("abc")), "%d");

  ASSERT_EQ_FMT(7, s->find(StrFromC("\xff")), "%d");
  ASSERT_EQ_FMT(7, s->rfind(StrFromC("\xff")), "%d");
  ASSERT_EQ_FMT(-1, s->rfind(StrFromC("\xfe")), "%d");

  PASS();
}

TEST test_str_strip() {
  printf("\n");

  printf("------- BigStr::lstrip -------\n");

  {
    BigStr* result = (StrFromC("\n "))->lstrip();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("")));
  }

  // carriage return is space, consistent with JSON spec and lexing rules in
  // frontend/lexer_def.py
  {
    BigStr* result = (StrFromC("\n\r #"))->lstrip();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("#")));
  }

  // but \v vertical tab is not
  {
    BigStr* result = (StrFromC("\v #"))->lstrip();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("\v #")));
  }

  {
    BigStr* result = (StrFromC("\n  #"))->lstrip();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("#")));
  }

  {
    BigStr* result = (StrFromC("\n  #"))->lstrip();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("#")));
  }

  {
    BigStr* result = (StrFromC("#"))->lstrip(StrFromC("#"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("")));
  }

  {
    BigStr* result = (StrFromC("##### "))->lstrip(StrFromC("#"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC(" ")));
  }

  {
    BigStr* result = (StrFromC("#  "))->lstrip(StrFromC("#"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("  ")));
  }

  {
    BigStr* result = (StrFromC(" # "))->lstrip(StrFromC("#"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC(" # ")));
  }

  printf("------- BigStr::rstrip -------\n");

  {
    BigStr* result = (StrFromC(" \n"))->rstrip();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("")));
  }

  {
    BigStr* result = (StrFromC("# \n"))->rstrip();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("#")));
  }

  {
    BigStr* result = (StrFromC("#  \n"))->rstrip();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("#")));
  }

  {
    BigStr* s1 = StrFromC(" \n#");
    BigStr* result = s1->rstrip();
    ShowString(result);
    ASSERT(str_equals(result, s1));
    ASSERT_EQ(result, s1);  // objects are identical
  }

  {
    BigStr* result = (StrFromC("#  \n"))->rstrip();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("#")));
  }

  {
    BigStr* result = (StrFromC("#"))->rstrip(StrFromC("#"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("")));
  }

  {
    BigStr* result = (StrFromC(" #####"))->rstrip(StrFromC("#"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC(" ")));
  }

  {
    BigStr* result = (StrFromC("  #"))->rstrip(StrFromC("#"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("  ")));
  }

  {
    BigStr* result = (StrFromC(" # "))->rstrip(StrFromC("#"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC(" # ")));
  }

  printf("------- BigStr::strip -------\n");

  {
    BigStr* result = (StrFromC(""))->strip();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("")));

    ASSERT_EQ(result, kEmptyString);  // identical objects
  }

  {
    BigStr* result = (StrFromC(" "))->strip();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("")));

    ASSERT_EQ(result, kEmptyString);  // identical objects
  }

  {
    BigStr* result = (StrFromC("  \n"))->strip();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("")));

    ASSERT_EQ(result, kEmptyString);  // identical objects
  }

  {
    BigStr* result = (StrFromC(" ## "))->strip();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("##")));
  }

  {
    BigStr* result = (StrFromC("  hi  \n"))->strip();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("hi")));
  }

  printf("---------- Done ----------\n");

  PASS();
}

TEST test_str_upper_lower() {
  printf("\n");

  printf("------- BigStr::upper -------\n");

  {
    BigStr* result = (StrFromC(""))->upper();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("")));
  }

  {
    BigStr* result = (StrFromC("upper"))->upper();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("UPPER")));
  }

  {
    BigStr* result = (StrFromC("upPer_uPper"))->upper();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("UPPER_UPPER")));
  }

  printf("------- BigStr::lower -------\n");

  {
    BigStr* result = (StrFromC(""))->lower();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("")));
  }

  {
    BigStr* result = (StrFromC("LOWER"))->lower();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("lower")));
  }

  {
    BigStr* result = (StrFromC("lOWeR_lowEr"))->lower();
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("lower_lower")));
  }

  printf("---------- Done ----------\n");

  PASS();
}

TEST test_str_replace() {
  printf("\n");

  BigStr* s0 = StrFromC("ab cd ab ef");

  printf("----- BigStr::replace -------\n");

  {
    BigStr* s1 = s0->replace(StrFromC("ab"), StrFromC("--"));
    ShowString(s1);
    ASSERT(str_equals(s1, StrFromC("-- cd -- ef")));
  }

  {
    BigStr* s1 = s0->replace(StrFromC("ab"), StrFromC("----"));
    ShowString(s1);
    ASSERT(str_equals(s1, StrFromC("---- cd ---- ef")));
  }

  {
    BigStr* s1 = s0->replace(StrFromC("ab cd ab ef"), StrFromC("0"));
    ShowString(s1);
    ASSERT(str_equals(s1, StrFromC("0")));
  }

  {
    BigStr* s1 = s0->replace(s0, StrFromC("0"));
    ShowString(s1);
    ASSERT(str_equals(s1, StrFromC("0")));
  }

  {
    BigStr* s1 = s0->replace(StrFromC("no-match"), StrFromC("0"));
    ShowString(s1);
    ASSERT(str_equals(s1, StrFromC("ab cd ab ef")));
  }

  {
    BigStr* s1 = s0->replace(StrFromC("ef"), StrFromC("0"));
    ShowString(s1);
    ASSERT(str_equals(s1, StrFromC("ab cd ab 0")));
  }

  {
    BigStr* s1 = s0->replace(StrFromC("f"), StrFromC("0"));
    ShowString(s1);
    ASSERT(str_equals(s1, StrFromC("ab cd ab e0")));
  }

  {
    s0 = StrFromC("ab ab ab");
    BigStr* s1 = s0->replace(StrFromC("ab"), StrFromC("0"));
    ShowString(s1);
    ASSERT(str_equals(s1, StrFromC("0 0 0")));
  }

  {
    s0 = StrFromC("ababab");
    BigStr* s1 = s0->replace(StrFromC("ab"), StrFromC("0"));
    ShowString(s1);
    ASSERT(str_equals(s1, StrFromC("000")));
  }

  {
    s0 = StrFromC("abababab");
    BigStr* s1 = s0->replace(StrFromC("ab"), StrFromC("0"));
    ShowString(s1);
    ASSERT(str_equals(s1, StrFromC("0000")));
  }

  {
    s0 = StrFromC("abc 123");
    BigStr* s1 = s0->replace(StrFromC("abc"), StrFromC(""));
    ShowString(s1);
    ASSERT(str_equals(s1, StrFromC(" 123")));
  }

  {
    s0 = StrFromC("abc 123");
    BigStr* s1 = s0->replace(StrFromC("abc"), StrFromC(""));
    ShowString(s1);
    ASSERT(str_equals(s1, StrFromC(" 123")));
  }

  {
    s0 = StrFromC("abc 123");
    BigStr* s1 = s0->replace(StrFromC("abc"), StrFromC("abc"));
    ShowString(s1);
    ASSERT(str_equals(s1, StrFromC("abc 123")));
  }

  {
    s0 = StrFromC("aaaa");
    BigStr* s1 = s0->replace(StrFromC("aa"), StrFromC("bb"));
    ShowString(s1);
    ASSERT(str_equals(s1, StrFromC("bbbb")));
  }

  {
    s0 = StrFromC("aaaaaa");
    BigStr* s1 = s0->replace(StrFromC("aa"), StrFromC("bb"));
    ShowString(s1);
    ASSERT(str_equals(s1, StrFromC("bbbbbb")));
  }

  // Test NUL replacement
  {
    BigStr* s_null = StrFromC("abc\0bcd", 7);
    ASSERT_EQ(7, len(s_null));

    BigStr* re1 = s_null->replace(StrFromC("ab"), StrFromC("--"));
    ASSERT_EQ_FMT(7, len(re1), "%d");
    ASSERT(str_equals(StrFromC("--c\0bcd", 7), re1));

    BigStr* re2 = s_null->replace(StrFromC("bc"), StrFromC("--"));
    ASSERT_EQ_FMT(7, len(re2), "%d");
    ASSERT(str_equals(StrFromC("a--\0--d", 7), re2));

    BigStr* re3 = s_null->replace(StrFromC("\0", 1), StrFromC("__"));
    ASSERT_EQ_FMT(8, len(re3), "%d");
    ASSERT(str_equals(StrFromC("abc__bcd", 8), re3));
  }

  PASS();
}

TEST test_str_just() {
  printf("\n");

  printf("------- BigStr::ljust -------\n");

  {
    BigStr* result = (StrFromC(""))->ljust(0, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("")));
  }
  {
    BigStr* result = (StrFromC(""))->ljust(1, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("_")));
  }
  {
    BigStr* result = (StrFromC(""))->ljust(4, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("____")));
  }
  {
    BigStr* result = (StrFromC("x"))->ljust(0, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("x")));
  }
  {
    BigStr* result = (StrFromC("x"))->ljust(1, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("x")));
  }
  {
    BigStr* result = (StrFromC("x"))->ljust(2, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("x_")));
  }

  {
    BigStr* result = (StrFromC("xx"))->ljust(-1, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("xx")));
  }
  {
    BigStr* result = (StrFromC("xx"))->ljust(0, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("xx")));
  }
  {
    BigStr* result = (StrFromC("xx"))->ljust(1, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("xx")));
  }
  {
    BigStr* result = (StrFromC("xx"))->ljust(2, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("xx")));
  }
  {
    BigStr* result = (StrFromC("xx"))->ljust(4, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("xx__")));
  }

  printf("------- BigStr::rjust -------\n");
  {
    BigStr* result = (StrFromC(""))->rjust(0, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("")));
  }
  {
    BigStr* result = (StrFromC(""))->rjust(1, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("_")));
  }
  {
    BigStr* result = (StrFromC(""))->rjust(4, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("____")));
  }
  {
    BigStr* result = (StrFromC("x"))->rjust(0, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("x")));
  }
  {
    BigStr* result = (StrFromC("x"))->rjust(1, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("x")));
  }
  {
    BigStr* result = (StrFromC("x"))->rjust(2, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("_x")));
  }

  {
    BigStr* result = (StrFromC("xx"))->rjust(-1, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("xx")));
  }
  {
    BigStr* result = (StrFromC("xx"))->rjust(0, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("xx")));
  }
  {
    BigStr* result = (StrFromC("xx"))->rjust(1, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("xx")));
  }
  {
    BigStr* result = (StrFromC("xx"))->rjust(2, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("xx")));
  }
  {
    BigStr* result = (StrFromC("xx"))->rjust(4, StrFromC("_"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("__xx")));
  }
  printf("---------- Done ----------\n");

  PASS();
}

TEST test_str_slice() {
  printf("\n");

  BigStr* s0 = StrFromC("abcdef");

  printf("------- BigStr::slice -------\n");

  {  // Happy path
    BigStr* s1 = s0->slice(0, 5);
    ASSERT(str_equals(s1, StrFromC("abcde")));
    ShowString(s1);
  }
  {
    BigStr* s1 = s0->slice(1, 5);
    ASSERT(str_equals(s1, StrFromC("bcde")));
    ShowString(s1);
  }
  {
    BigStr* s1 = s0->slice(0, 0);
    ASSERT(str_equals(s1, StrFromC("")));
    ShowString(s1);
  }
  {
    BigStr* s1 = s0->slice(0, 6);
    ASSERT(str_equals(s1, StrFromC("abcdef")));
    ShowString(s1);
  }
  {
    BigStr* s1 = s0->slice(-6, 6);
    ASSERT(str_equals(s1, StrFromC("abcdef")));
    ShowString(s1);
  }
  {
    BigStr* s1 = s0->slice(0, -6);
    ASSERT(str_equals(s1, StrFromC("")));
    ShowString(s1);
  }
  {
    BigStr* s1 = s0->slice(-6, -6);
    ASSERT(str_equals(s1, StrFromC("")));
    ShowString(s1);
  }

  {
    BigStr* s1 = s0->slice(5, 6);
    ASSERT(str_equals(s1, StrFromC("f")));
    ShowString(s1);
  }

  {
    BigStr* s1 = s0->slice(6, 6);
    ASSERT(str_equals(s1, StrFromC("")));
    ASSERT(kEmptyString == s1);
    ShowString(s1);
  }

  {
    BigStr* s1 = s0->slice(0, -7);
    ASSERT(str_equals(s1, StrFromC("")));
    ShowString(s1);
  }

  {
    BigStr* s1 = s0->slice(-7, -7);
    ASSERT(str_equals(s1, StrFromC("")));
    ShowString(s1);
  }

  {
    BigStr* s1 = s0->slice(-7, 0);
    ASSERT(str_equals(s1, StrFromC("")));
    ShowString(s1);
  }

  {
    BigStr* s1 = s0->slice(6, 6);
    ASSERT(str_equals(s1, StrFromC("")));
    ShowString(s1);
  }

  {
    BigStr* s1 = s0->slice(7, 7);
    ASSERT(str_equals(s1, StrFromC("")));
    ShowString(s1);
  }

  {
    BigStr* s1 = s0->slice(6, 5);
    ASSERT(str_equals(s1, StrFromC("")));
    ShowString(s1);
  }

  {
    BigStr* s1 = s0->slice(7, 5);
    ASSERT(str_equals(s1, StrFromC("")));
    ShowString(s1);
  }

  {
    BigStr* s1 = s0->slice(7, 6);
    ASSERT(str_equals(s1, StrFromC("")));
    ShowString(s1);
  }

  {
    BigStr* s1 = s0->slice(7, 7);
    ASSERT(str_equals(s1, StrFromC("")));
    ShowString(s1);
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
    BigStr* result = str_concat(StrFromC(""), StrFromC(""));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("")));
  }
  {
    BigStr* result = str_concat(StrFromC("a"), StrFromC(""));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("a")));
  }
  {
    BigStr* result = str_concat(StrFromC("aa"), StrFromC(""));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("aa")));
  }
  {
    BigStr* result = str_concat(StrFromC(""), StrFromC("b"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("b")));
  }
  {
    BigStr* result = str_concat(StrFromC(""), StrFromC("bb"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("bb")));
  }
  {
    BigStr* result = str_concat(StrFromC("a"), StrFromC("b"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("ab")));
  }
  {
    BigStr* result = str_concat(StrFromC("aa"), StrFromC("b"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("aab")));
  }
  {
    BigStr* result = str_concat(StrFromC("a"), StrFromC("bb"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("abb")));
  }
  {
    BigStr* result = str_concat(StrFromC("aa"), StrFromC("bb"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("aabb")));
  }

  printf("------- str_concat3 -------\n");

  {
    BigStr* result = str_concat3(StrFromC(""), StrFromC(""), StrFromC(""));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("")));
  }
  {
    BigStr* result = str_concat3(StrFromC("a"), StrFromC(""), StrFromC(""));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("a")));
  }
  {
    BigStr* result = str_concat3(StrFromC("a"), StrFromC("b"), StrFromC(""));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("ab")));
  }
  {
    BigStr* result = str_concat3(StrFromC("a"), StrFromC("b"), StrFromC("c"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("abc")));
  }
  {
    BigStr* result = str_concat3(StrFromC("a"), StrFromC(""), StrFromC("c"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("ac")));
  }

  {
    BigStr* result = str_concat3(StrFromC("aa"), StrFromC(""), StrFromC(""));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("aa")));
  }
  {
    BigStr* result = str_concat3(StrFromC("aa"), StrFromC("b"), StrFromC(""));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("aab")));
  }
  {
    BigStr* result = str_concat3(StrFromC("aa"), StrFromC("b"), StrFromC("c"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("aabc")));
  }
  {
    BigStr* result = str_concat3(StrFromC("aa"), StrFromC(""), StrFromC("c"));
    ShowString(result);
    ASSERT(str_equals(result, StrFromC("aac")));
  }

  PASS();
}

TEST test_str_to_int() {
  log("");
  log("------- to_int -------");

  {
    BigStr* input = StrFromC("0");
    int result = to_int(input);
    ShowStringInt(input, result);
    ASSERT(result == 0);
  }
  {
    BigStr* input = StrFromC("1");
    int result = to_int(input);
    ShowStringInt(input, result);
    ASSERT(result == 1);
  }
  {
    BigStr* input = StrFromC("-1");
    int result = to_int(input);
    ShowStringInt(input, result);
    ASSERT(result == -1);
  }
  {
    BigStr* input = StrFromC("100");
    int result = to_int(input);
    ShowStringInt(input, result);
    ASSERT(result == 100);
  }
  {
    // one less than 0x7FFFFFFF, because that value can be LONG_MAX
    BigStr* input = StrFromC("2147483646");
    int result = to_int(input);
    ShowStringInt(input, result);
    ASSERT(result == 2147483646);
  }
  {
    // one less than -0x7FFFFFFF - 1, because that value can be LONG_MIN
    BigStr* input = StrFromC("-2147483647");
    int result = to_int(input);
    ShowStringInt(input, result);
    ASSERT(result == -2147483647);
  }

  bool caught;
  int z = 0;
  caught = false;
  try {
    z = to_int(StrFromC("2147483648"));
    log("z = %d", z);
  } catch (ValueError*) {
    caught = true;
  }
  ASSERT(caught);

  caught = false;
  try {
    z = to_int(StrFromC("-2147483649"));
    log("z = %d", z);
  } catch (ValueError*) {
    caught = true;
  }
  ASSERT(caught);

  PASS();
}

TEST test_str_startswith() {
  printf("------ BigStr::helpers ------\n");

  ASSERT((StrFromC(""))->startswith(StrFromC("")) == true);
  ASSERT((StrFromC(" "))->startswith(StrFromC("")) == true);
  ASSERT((StrFromC(" "))->startswith(StrFromC(" ")) == true);

  ASSERT((StrFromC("  "))->startswith(StrFromC(" ")) == true);

  PASS();
}

TEST test_str_contains() {
  bool b;
  BigStr* s = nullptr;
  BigStr* nul = nullptr;
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

  printf("------- BigStr::split -------\n");

  {
    BigStr* s = StrFromC("abc def");
    // No split
    List<BigStr*>* parts = s->split(StrFromC("x"));
    ShowList(parts);
    ASSERT_EQ(1, len(parts));
    ASSERT_EQ(parts->at(0), s);
  }

  {
    List<BigStr*>* parts = StrFromC("abc def")->split(StrFromC(" "));
    ShowList(parts);
    ASSERT_EQ(2, len(parts));
    ASSERT(items_equal(parts->at(0), StrFromC("abc")));
    ASSERT(items_equal(parts->at(1), StrFromC("def")));
  }

  {
    List<BigStr*>* parts = StrFromC("###")->split(StrFromC("#"));
    ShowList(parts);
    ASSERT_EQ_FMT(4, len(parts), "%d");
    // Identical objects
    ASSERT_EQ(kEmptyString, parts->at(0));
    ASSERT_EQ(kEmptyString, parts->at(1));
    ASSERT_EQ(kEmptyString, parts->at(2));
    ASSERT_EQ(kEmptyString, parts->at(3));
  }

  {
    List<BigStr*>* parts = StrFromC(" ### ")->split(StrFromC("#"));
    ShowList(parts);
    ASSERT_EQ(4, len(parts));
    ASSERT(items_equal(parts->at(0), StrFromC(" ")));
    ASSERT(items_equal(parts->at(1), StrFromC("")));
    ASSERT(items_equal(parts->at(2), StrFromC("")));
    ASSERT(items_equal(parts->at(3), StrFromC(" ")));
  }

  {
    List<BigStr*>* parts = StrFromC(" # ")->split(StrFromC(" "));
    ShowList(parts);
    ASSERT_EQ(3, len(parts));
    ASSERT(items_equal(parts->at(0), StrFromC("")));
    ASSERT(items_equal(parts->at(1), StrFromC("#")));
    ASSERT(items_equal(parts->at(2), StrFromC("")));
  }

  {
    List<BigStr*>* parts = StrFromC("  #")->split(StrFromC("#"));
    ShowList(parts);
    ASSERT_EQ(2, len(parts));
    ASSERT(items_equal(parts->at(0), StrFromC("  ")));
    ASSERT(items_equal(parts->at(1), StrFromC("")));
  }

  {
    List<BigStr*>* parts = StrFromC("#  #")->split(StrFromC("#"));
    ShowList(parts);
    ASSERT_EQ(3, len(parts));
    ASSERT(items_equal(parts->at(0), StrFromC("")));
    ASSERT(items_equal(parts->at(1), StrFromC("  ")));
    ASSERT(items_equal(parts->at(2), StrFromC("")));
  }

  {
    List<BigStr*>* parts = StrFromC("")->split(StrFromC(" "));
    ShowList(parts);
    ASSERT_EQ(1, len(parts));
    ASSERT(items_equal(parts->at(0), StrFromC("")));
  }

  {
    BigStr* s = StrFromC("a,b,c,d,e,f,g");
    List<BigStr*>* parts = s->split(StrFromC(","));
    ShowList(parts);
    ASSERT_EQ(7, len(parts));
    ASSERT(items_equal(parts->at(0), StrFromC("a")));

    // ask for 3 splits
    parts = s->split(StrFromC(","), 3);
    ShowList(parts);
    ASSERT_EQ_FMT(4, len(parts), "%d");
    ASSERT(items_equal(parts->at(0), StrFromC("a")));
    ASSERT(items_equal(parts->at(1), StrFromC("b")));
    ASSERT(items_equal(parts->at(2), StrFromC("c")));
    ASSERT(items_equal(parts->at(3), StrFromC("d,e,f,g")));

    // ask for 0 splits
    parts = s->split(StrFromC(","), 0);
    ShowList(parts);
    ASSERT_EQ(1, len(parts));
    // identical objects
    ASSERT_EQ(parts->at(0), s);

    parts = StrFromC("###")->split(StrFromC("#"), 2);
    ShowList(parts);
    ASSERT_EQ(3, len(parts));
    ASSERT(items_equal(parts->at(0), StrFromC("")));
    ASSERT(items_equal(parts->at(1), StrFromC("")));
    ASSERT(items_equal(parts->at(2), StrFromC("#")));
  }

  printf("---------- Done ----------\n");

  PASS();
}

TEST test_str_join() {
  printf("\n");

  printf("-------- BigStr::join -------\n");

  {
    BigStr* result = kEmptyString->join(Alloc<List<BigStr*>>());
    ShowString(result);
    ASSERT(items_equal(kEmptyString, result));
    ASSERT_EQ(kEmptyString, result);  // pointers equal
  }

  {
    BigStr* result = StrFromC("anything")->join(Alloc<List<BigStr*>>());
    ShowString(result);
    ASSERT(items_equal(kEmptyString, result));
    ASSERT_EQ(kEmptyString, result);  // pointers equal
  }

  {
    BigStr* one_string = StrFromC("one string");
    // NewList avoids std::initializer_list()
    BigStr* result = StrFromC("anything")->join(NewList<BigStr*>({one_string}));
    ShowString(result);
    ASSERT(items_equal(one_string, result));
    ASSERT_EQ(one_string, result);  // pointers equal
  }

  {
    BigStr* result = kEmptyString->join(
        NewList<BigStr*>({StrFromC("abc"), StrFromC("def")}));
    ShowString(result);
    ASSERT(items_equal(result, StrFromC("abcdef")));
  }
  {
    BigStr* result = (StrFromC(" "))
                         ->join(NewList<BigStr*>(
                             {StrFromC("abc"), StrFromC("def"), StrFromC("abc"),
                              StrFromC("def"), StrFromC("abc"), StrFromC("def"),
                              StrFromC("abc"), StrFromC("def")}));
    ShowString(result);
    ASSERT(items_equal(result, StrFromC("abc def abc def abc def abc def")));
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

  // check StrFormat(char*) == StrFormat(BigStr*)
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

  // check that justification can be set with -
  ASSERT(str_equals0("foo  ", StrFormat("%-5s", StrFromC("foo"))));
  ASSERT(str_equals0("  bar", StrFormat("%5s", StrFromC("bar"))));

  PASS();
}

// a very innovative hash function
unsigned coffee_hash(const char*, int) {
  return 0xc0ffeeu;
}

TEST test_str_hash() {
  BigStr* s1 = StrFromC("a string");
  BigStr* s2 = StrFromC("a different string");
  unsigned h1 = s1->hash(fnv1);
  unsigned h2 = s2->hash(fnv1);
  ASSERT(h1 != h2);

  // flag bit should be set and we should return the cached hash.
  ASSERT_EQ(h1, s1->hash(coffee_hash));
  ASSERT_EQ(h2, s2->hash(coffee_hash));

  PASS();
}

GLOBAL_STR(kStrFoo, "foo");
GLOBAL_STR(a, "a");
GLOBAL_STR(XX, "XX");

TEST str_replace_test() {
  BigStr* o = nullptr;
  BigStr* _12 = nullptr;
  BigStr* _123 = nullptr;
  BigStr* s = nullptr;
  BigStr* foxo = nullptr;
  BigStr* expected = nullptr;
  StackRoots _roots({&o, &_12, &_123, &s, &foxo, &expected});

  o = StrFromC("o");
  _12 = StrFromC("12");
  _123 = StrFromC("123");

  s = kStrFood->replace(o, _12);
  ASSERT(str_equals0("f1212d", s));
  print(s);

  s = kStrFoo->replace(o, _123);
  ASSERT(str_equals0("f123123", s));
  print(s);

  foxo = StrFromC("foxo");
  s = foxo->replace(o, _123);
  ASSERT(str_equals0("f123x123", s));
  print(s);

  s = kWithNull->replace(a, XX);
  print(s);

  // Explicit length because of \0
  expected = StrFromC("foo\0bXXr", 8);
  ASSERT(str_equals(expected, s));

  PASS();
}

void Print(List<BigStr*>* parts) {
  log("---");
  log("len = %d", len(parts));
  for (int i = 0; i < len(parts); ++i) {
    printf("%d [", i);
    BigStr* s = parts->at(i);
    int n = len(s);
    fwrite(s->data_, sizeof(char), n, stdout);
    fputs("]\n", stdout);
  }
}

TEST str_split_test() {
  BigStr* s = nullptr;
  BigStr* sep = nullptr;
  List<BigStr*>* parts = nullptr;

  StackRoots _roots({&s, &sep, &parts});
  sep = StrFromC(":");

  parts = kEmptyString->split(sep);
  ASSERT_EQ(1, len(parts));
  Print(parts);

  s = StrFromC(":");
  parts = s->split(sep);
  ASSERT_EQ_FMT(2, len(parts), "%d");
  ASSERT(str_equals(kEmptyString, parts->at(0)));
  ASSERT(str_equals(kEmptyString, parts->at(1)));
  Print(parts);

  s = StrFromC("::");
  parts = s->split(sep);
  ASSERT_EQ(3, len(parts));
  ASSERT(str_equals(kEmptyString, parts->at(0)));
  ASSERT(str_equals(kEmptyString, parts->at(1)));
  ASSERT(str_equals(kEmptyString, parts->at(2)));
  Print(parts);

  s = StrFromC("a:b");
  parts = s->split(sep);
  ASSERT_EQ(2, len(parts));
  Print(parts);
  ASSERT(str_equals0("a", parts->at(0)));
  ASSERT(str_equals0("b", parts->at(1)));

  s = StrFromC("abc:def:");
  parts = s->split(sep);
  ASSERT_EQ(3, len(parts));
  Print(parts);
  ASSERT(str_equals0("abc", parts->at(0)));
  ASSERT(str_equals0("def", parts->at(1)));
  ASSERT(str_equals(kEmptyString, parts->at(2)));

  s = StrFromC(":abc:def:");
  parts = s->split(sep);
  ASSERT_EQ(4, len(parts));
  Print(parts);

  s = StrFromC("abc:def:ghi");
  parts = s->split(sep);
  ASSERT_EQ(3, len(parts));
  Print(parts);

  PASS();
}

TEST str_methods_test() {
  log("char funcs");
  ASSERT(!(StrFromC(""))->isupper());
  ASSERT(!(StrFromC("a"))->isupper());
  ASSERT((StrFromC("A"))->isupper());
  ASSERT((StrFromC("AB"))->isupper());

  ASSERT((StrFromC("abc"))->isalpha());
  ASSERT((StrFromC("3"))->isdigit());
  ASSERT(!(StrFromC(""))->isdigit());

  log("slice()");
  ASSERT(str_equals0("f", kStrFood->at(0)));

  ASSERT(str_equals0("d", kStrFood->at(-1)));

  ASSERT(str_equals0("ood", kStrFood->slice(1)));
  ASSERT(str_equals0("oo", kStrFood->slice(1, 3)));
  ASSERT(str_equals0("oo", kStrFood->slice(1, -1)));
  ASSERT(str_equals0("o", kStrFood->slice(-3, -2)));
  ASSERT(str_equals0("fo", kStrFood->slice(-4, -2)));

  log("strip()");
  ASSERT(str_equals0(" abc", StrFromC(" abc ")->rstrip()));
  ASSERT(str_equals0(" def", StrFromC(" def")->rstrip()));

  ASSERT(str_equals0("", kEmptyString->rstrip()));
  ASSERT(str_equals0("", kEmptyString->strip()));

  ASSERT(str_equals0("123", StrFromC(" 123 ")->strip()));
  ASSERT(str_equals0("123", StrFromC(" 123")->strip()));
  ASSERT(str_equals0("123", StrFromC("123 ")->strip()));

  BigStr* input = nullptr;
  BigStr* arg = nullptr;
  BigStr* expected = nullptr;
  BigStr* result = nullptr;
  StackRoots _roots({&input, &arg, &expected, &result});

  log("startswith endswith");

  // arg needs to be separate here because order of evaluation isn't defined!!!
  // CRASHES:
  //   ASSERT(input->startswith(StrFromC("ab")));
  // Will this because a problem for mycpp?  I think you have to detect this
  // case:
  //   f(Alloc<Foo>(), new Alloc<Bar>())
  // Allocation can't happen INSIDE an arg list.

  input = StrFromC("abc");
  ASSERT(input->startswith(kEmptyString));
  ASSERT(input->endswith(kEmptyString));

  ASSERT(input->startswith(input));
  ASSERT(input->endswith(input));

  arg = StrFromC("ab");
  ASSERT(input->startswith(arg));
  ASSERT(!input->endswith(arg));

  arg = StrFromC("bc");
  ASSERT(!input->startswith(arg));
  ASSERT(input->endswith(arg));

  log("rjust() and ljust()");
  input = StrFromC("13");
  ASSERT(str_equals0("  13", input->rjust(4, kSpace)));
  ASSERT(str_equals0(" 13", input->rjust(3, kSpace)));
  ASSERT(str_equals0("13", input->rjust(2, kSpace)));
  ASSERT(str_equals0("13", input->rjust(1, kSpace)));

  ASSERT(str_equals0("13  ", input->ljust(4, kSpace)));
  ASSERT(str_equals0("13 ", input->ljust(3, kSpace)));
  ASSERT(str_equals0("13", input->ljust(2, kSpace)));
  ASSERT(str_equals0("13", input->ljust(1, kSpace)));

  log("join()");

  List<BigStr*>* L1 = nullptr;
  List<BigStr*>* L2 = nullptr;
  List<BigStr*>* empty_list = nullptr;
  StackRoots _roots2({&L1, &L2, &empty_list});

  L1 = NewList<BigStr*>(std::initializer_list<BigStr*>{kStrFood, kStrFoo});

  // Join by empty string
  ASSERT(str_equals0("foodfoo", kEmptyString->join(L1)));

  // Join by NUL
  expected = StrFromC("food\0foo", 8);
  arg = StrFromC("\0", 1);
  result = arg->join(L1);
  ASSERT(str_equals(expected, result));

  // Singleton list
  L2 = NewList<BigStr*>(std::initializer_list<BigStr*>{kStrFoo});
  ASSERT(str_equals0("foo", kEmptyString->join(L2)));

  // Empty list
  empty_list = NewList<BigStr*>(std::initializer_list<BigStr*>{});

  result = kEmptyString->join(empty_list);
  ASSERT(str_equals(kEmptyString, result));
  ASSERT_EQ(0, len(result));

  result = kSpace->join(empty_list);
  ASSERT(str_equals(kEmptyString, result));
  ASSERT_EQ(0, len(result));

  PASS();
}

TEST str_funcs_test() {
  BigStr* s = nullptr;

  log("ord()");
  s = StrFromC("A");
  print(repr(s));
  ASSERT_EQ(65, ord(s));

  log("chr()");
  ASSERT(str_equals(s, chr(65)));

  log("str_concat()");
  ASSERT(str_equals0("foodfood", str_concat(kStrFood, kStrFood)));
  ASSERT(str_equals(kEmptyString, str_concat(kEmptyString, kEmptyString)));

  log("str_repeat()");

  // -1 is allowed by Python and used by Oil!
  s = StrFromC("abc");
  ASSERT(str_equals(kEmptyString, str_repeat(s, -1)));
  ASSERT(str_equals(kEmptyString, str_repeat(s, 0)));

  ASSERT(str_equals(s, str_repeat(s, 1)));

  ASSERT(str_equals0("abcabcabc", str_repeat(s, 3)));

  log("repr()");

  s = kEmptyString;
  print(repr(s));
  ASSERT(str_equals0("''", repr(s)));

  s = StrFromC("'");
  print(repr(s));
  ASSERT(str_equals0("\"'\"", repr(s)));

  s = StrFromC("'single'");
  ASSERT(str_equals0("\"'single'\"", repr(s)));

  s = StrFromC("\"double\"");
  ASSERT(str_equals0("'\"double\"'", repr(s)));

  // this one is truncated
  s = StrFromC("NUL \x00 NUL", 9);
  print(repr(s));
  ASSERT(str_equals0("'NUL \\x00 NUL'", repr(s)));

  s = StrFromC("tab\tline\nline\r\n");
  print(repr(s));
  ASSERT(str_equals0("'tab\\tline\\nline\\r\\n'", repr(s)));

  s = StrFromC("high \xFF \xFE high");
  print(repr(s));
  ASSERT(str_equals0("'high \\xff \\xfe high'", repr(s)));

  PASS();
}

TEST str_iters_test() {
  for (StrIter it(kStrFood); !it.Done(); it.Next()) {
    print(it.Value());
  }

  PASS();
}

// Also see mycpp/small_str_test.cc
TEST small_big_test() {
  // TODO:
  // Need GC rooting for these values
  // Make len() work

  Str s(StrFromC("hello"));
  for (int i = 0; i < len(s); ++i) {
    Str ch = s.at(i);
    log("s[%d] = %s", i, ch.data());
  }

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
  RUN_TEST(test_str_contains);

  RUN_TEST(test_str_startswith);

  RUN_TEST(test_str_split);
  RUN_TEST(test_str_join);

  RUN_TEST(test_str_format);

  RUN_TEST(test_str_hash);

  // Duplicate
  RUN_TEST(str_replace_test);
  RUN_TEST(str_split_test);

  RUN_TEST(str_methods_test);
  RUN_TEST(str_funcs_test);
  RUN_TEST(str_iters_test);

  RUN_TEST(small_big_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
