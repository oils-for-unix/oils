#include <locale.h>  // setlocale()
#include <regex.h>   // regcomp()

#include "mycpp/runtime.h"
#include "vendor/greatest.h"

void FindAll(const char* p, const char* s) {
  regex_t pat;

  int cflags = REG_EXTENDED;
  if (regcomp(&pat, p, cflags) != 0) {
    FAIL();
  }
  int outlen = pat.re_nsub + 1;  // number of captures

  // TODO: Could statically allocate 99, and assert that re_nsub is less than
  // 99.  Would speed up loops.
  regmatch_t* pmatch =
      static_cast<regmatch_t*>(malloc(sizeof(regmatch_t) * outlen));

  int cur_pos = 0;
  // int n = strlen(s);
  while (true) {
    // Necessary so ^ doesn't match in the middle!
    int eflags = cur_pos == 0 ? 0 : REG_NOTBOL;
    bool match = regexec(&pat, s + cur_pos, outlen, pmatch, eflags) == 0;

    if (!match) {
      break;
    }
    int i;
    for (i = 0; i < outlen; i++) {
      int start = pmatch[i].rm_so;
      int end = pmatch[i].rm_eo;
      int len = end - start;
      BigStr* m = StrFromC(s + cur_pos + start, len);
      log("%d GROUP %d (%d .. %d) = [%s]", cur_pos, i, start, end, m->data_);
    }
    log("");
    int match_len = pmatch[0].rm_eo;
    if (match_len == 0) {
      break;
    }
    cur_pos += match_len;
  }

  free(pmatch);
  regfree(&pat);
}

// adjacent matches
const char* s = "a345y-axy- there b789y- cy-";

TEST regex_unanchored() {
  const char* unanchored = "[abc]([0-9]*)(x?)(y)-";
  FindAll(unanchored, s);

  PASS();
}

TEST regex_caret() {
  const char* anchored = "^[abc]([0-9]*)(x?)(y)-";
  FindAll(anchored, s);

  PASS();
}

TEST regex_lexer() {
  // like the Yaks / Make-a-Lisp pattern
  const char* lexer = "([a-z]+)|([0-9]+)|([ ]+)|([+-])";
  FindAll(lexer, s);

  PASS();
}

TEST regex_repeat_with_capture() {
  const char* lexer = "(([a-z]+)([0-9]+)-)*((A+)|(Z+))*";
  FindAll(lexer, "a0-b1-c2-AAZZZA");
  // Groups are weird
  // whole match 0: a0-b1-c2-
  //             1: c2-      # last repetition
  //             2: c        # last one
  //             3: 2        # last one
  //
  // And then there's an empty match
  //
  // Ideas:
  // - disallow nested groups in Eggex?
  // - I really care about the inner ones -- groups 2 and 3
  // - I want flat groups

  PASS();
}

// Disallow this in eggex, as well as the above
TEST regex_nested_capture() {
  const char* lexer = "(([a-z]+)([0-9]+))";
  FindAll(lexer, "a0");
  PASS();
}

// I think we allow this in eggex
TEST regex_alt_with_capture() {
  const char* lexer = "([a-z]+)|([0-9]+)(-)";
  FindAll(lexer, "x-");
  FindAll(lexer, "7-");
  PASS();
}

bool RegexMatch(const char* s, const char* regex_str) {
  regex_t pat;
  int status = regcomp(&pat, regex_str, REG_EXTENDED);
  if (status != 0) {
    assert(false);
  }
  log("*** Matching string %s against regex %s", s, regex_str);

  int num_groups = pat.re_nsub + 1;  // number of captures

  regmatch_t* pmatch =
      static_cast<regmatch_t*>(malloc(sizeof(regmatch_t) * num_groups));
  int eflags = 0;
  bool match = regexec(&pat, s, num_groups, pmatch, eflags) == 0;
  if (match) {
    printf("match\n");
    for (int i = 0; i < num_groups; i++) {
      int start = pmatch[i].rm_so;
      int end = pmatch[i].rm_eo;
      printf("start %d - %d\n", start, end);
    }
  }
  free(pmatch);
  regfree(&pat);

  return match;
}

TEST regex_unicode() {
  regex_t pat;

  const char* p = "_._";  // 1 byte, not code point?

  bool matched;

  matched = RegexMatch("_xyz_", p);
  ASSERT(not matched);

  matched = RegexMatch("_x_", p);
  ASSERT(matched);

  matched = RegexMatch("_\x01_", p);
  ASSERT(matched);

  const char* u1 = "_μ_";
  const char* u2 = "_\u03bc_";
  const char* u3 = "_\xce\xbc_";  // utf-8 encoding

  // Doesn't match without UTF-8 setting
  matched = RegexMatch(u1, p);
  // log("u1 %d", matched);
  ASSERT(not matched);

  matched = RegexMatch(u2, p);
  // log("u2 %d", matched);
  ASSERT(not matched);

  matched = RegexMatch(u3, p);
  // log("u3 %d", matched);
  ASSERT(not matched);

  // SETS GLOBAL
  char* saved_locale = setlocale(LC_ALL, "");
  log("saved_locale %s", saved_locale);
  if (saved_locale == nullptr) {
    FAIL();
  }

  // Now it matches
  matched = RegexMatch(u1, p);
  ASSERT(matched);
  matched = RegexMatch(u2, p);
  ASSERT(matched);
  matched = RegexMatch(u3, p);
  ASSERT(matched);

  // [^a] can match a code point
  matched = RegexMatch(u3, "_[^a]_");
  ASSERT(matched);

  const char* unicode_char_class = "[a\xce\xbc]";
  const char* s = "\xce\xbc";
  matched = RegexMatch(s, unicode_char_class);
  ASSERT(matched);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(regex_unanchored);
  RUN_TEST(regex_caret);
  RUN_TEST(regex_lexer);
  RUN_TEST(regex_repeat_with_capture);
  RUN_TEST(regex_alt_with_capture);
  RUN_TEST(regex_nested_capture);
  RUN_TEST(regex_unicode);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
