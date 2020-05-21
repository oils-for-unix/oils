#include "greatest.h"

#include "frontend_arg_def.h"
#include "frontend_match.h"
#include "id.h"
#include "libc.h"            // cell, etc
#include "osh_eval_stubs.h"  // util::BackslashEscape
#include "preamble.h"
#include "runtime_asdl.h"  // cell, etc

TEST show_sizeof() {
  // Without sed hack, it's 24 bytes because we have tag (2), id (4), val,
  // span_id.
  // Now 16 bytes.
  log("sizeof(Token) = %d", sizeof(syntax_asdl::Token));

  // Without sed hack, it's 12 bytes for tag (2) id (4) and span_id (4).
  // Now 8 bytes.
  log("sizeof(speck) = %d", sizeof(syntax_asdl::speck));

  // 16 bytes: 2 byte tag + 3 integer fields
  log("sizeof(line_span) = %d", sizeof(syntax_asdl::line_span));

  // Reordered to be 16 bytes
  log("sizeof(cell) = %d", sizeof(runtime_asdl::cell));

  // 16 bytes: pointer and length
  log("sizeof(Str) = %d", sizeof(Str));

  // 24 bytes: std::vector
  log("sizeof(List<int>) = %d", sizeof(List<int>));
  log("sizeof(List<Str*>) = %d", sizeof(List<Str*>));

  PASS();
}

TEST match_test() {
  match::SimpleLexer* lex = match::BraceRangeLexer(new Str("{-1..22}"));

  while (true) {
    auto t = lex->Next();
    int id = t.at0();
    if (id == id__Eol_Tok) {
      break;
    }
    log("id = %d", id);
    log("val = %s", t.at1()->data_);
  }

  // Similar to native/fastlex_test.py.  Just test that it matched
  ASSERT_EQ(0, match::MatchOption(new Str("")));
  ASSERT(match::MatchOption(new Str("pipefail")) > 0);

  ASSERT_EQ(0, match::MatchOption(new Str("pipefai")));
  ASSERT_EQ(0, match::MatchOption(new Str("pipefail_")));

  PASS();
}

TEST util_test() {
  // OK this seems to work
  Str* escaped = util::BackslashEscape(new Str("'foo bar'"), new Str(" '"));
  ASSERT(str_equals(escaped, new Str("\\'foo\\ bar\\'")));

  log("x = %s %d", escaped->data_, escaped->len_);

  Str* escaped2 = util::BackslashEscape(new Str(""), new Str(" '"));
  ASSERT(str_equals(escaped2, new Str("")));

  PASS();
}

TEST libc_test() {
  ASSERT(libc::fnmatch(new Str("*.py"), new Str("foo.py"), false));
  ASSERT(!libc::fnmatch(new Str("*.py"), new Str("foo.p"), false));

  // extended glob
  ASSERT(libc::fnmatch(new Str("*(foo|bar).py"), new Str("foo.py"), true));
  ASSERT(!libc::fnmatch(new Str("*(foo|bar).py"), new Str("foo.p"), true));

  // looks like extended glob, but didn't turn it on
  ASSERT(!libc::fnmatch(new Str("*(foo|bar).py"), new Str("foo.py"), false));

  PASS();
}

// HACK!  asdl/runtime.py isn't translated, but core_error.h uses it...
namespace runtime {
int NO_SPID = -1;
};

TEST exceptions() {
  bool caught = false;
  try {
    e_strict(new Str("foo"));
  } catch (error::Strict* e) {  // Catch by reference!
    // log("%p ", e);
    caught = true;
  }
  ASSERT(caught);

  PASS();
}

//
// FlagSpec Literals
//

// must be NUL terminated
//
// I tried to make this constexpr, but ran into errors.  Here is some
// std::array crap, but let's keep it simple.
//
// https://groups.google.com/a/isocpp.org/forum/#!topic/std-proposals/EcWhnxFdFwE

const char* arity0_1[] = {"foo", "bar", nullptr};

SetToArg_c arity1_1[] = {
    {"z", 0, false}, {"zz", 1, false}, {},  // sentinel
};

const char* options_1[] = {"o", "p", nullptr};

DefaultPair_c defaults_1[] = {
    {"x", Default_c::False},
    {"y", Default_c::Undef},
    {},
};

FlagSpec_c spec1 = {"export", arity0_1, arity1_1, options_1, defaults_1};
// a copy for demonstrations
FlagSpec_c spec2 = {"unset", arity0_1, arity1_1, options_1, defaults_1};

TEST arg_def_test() {
  // Test the declared constants
  log("spec1.arity0 %s", spec1.arity0[0]);
  log("spec1.arity0 %s", spec1.arity0[1]);

  log("spec1.arity1 %s", spec1.arity1[0].name);
  log("spec1.arity1 %s", spec1.arity1[1].name);

  log("spec1.options %s", spec1.options[0]);
  log("spec1.options %s", spec1.options[1]);

  log("spec1.defaults %s", spec1.defaults[0].name);
  log("spec1.defaults %s", spec1.defaults[1].name);

  log("sizeof %d", sizeof(spec1.arity0));  // 8
  log("sizeof %d", sizeof(arity0_1) / sizeof(arity0_1[0]));

  arg_def::LookupFlagSpec(new Str("new_var"));
  arg_def::LookupFlagSpec(new Str("readonly"));
  arg_def::LookupFlagSpec(new Str("zzz"));

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  GREATEST_MAIN_BEGIN();
  RUN_TEST(show_sizeof);
  RUN_TEST(match_test);
  RUN_TEST(util_test);
  RUN_TEST(libc_test);
  RUN_TEST(exceptions);
  RUN_TEST(arg_def_test);
  GREATEST_MAIN_END(); /* display results */
  return 0;
}
