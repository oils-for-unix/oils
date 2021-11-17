#include "greatest.h"

#include "core_error.h"
#include "core_pyerror.h"
#include "core_pyos.h"    // Chdir
#include "core_pyutil.h"  // BackslashEscape
#include "frontend_flag_spec.h"
#include "frontend_match.h"
#include "id.h"
#include "libc.h"
#include "osh_bool_stat.h"
#include "posix.h"
#include "pylib_os_path.h"
#include "runtime_asdl.h"  // cell, etc
#include "time_.h"

namespace Id = id_kind_asdl::Id;
using runtime_asdl::flag_type_e;

TEST show_sizeof() {
  // Without sed hack, it's 24 bytes because we have tag (2), id (4), val,
  // span_id.
  // Now 16 bytes.
  log("sizeof(Token) = %d", sizeof(syntax_asdl::Token));
  log("alignof(Token) = %d", alignof(syntax_asdl::Token));
  log("alignof(Token*) = %d", alignof(syntax_asdl::Token*));

  // Without sed hack, it's 12 bytes for tag (2) id (4) and span_id (4).
  // Now 8 bytes.
  log("sizeof(speck) = %d", sizeof(syntax_asdl::speck));

  // 16 bytes: 2 byte tag + 3 integer fields
  log("sizeof(line_span) = %d", sizeof(syntax_asdl::line_span));

  // Reordered to be 16 bytes
  log("sizeof(cell) = %d", sizeof(runtime_asdl::cell));

  // 24 bytes: std::vector
  log("sizeof(List<int>) = %d", sizeof(List<int>));
  log("sizeof(List<Str*>) = %d", sizeof(List<Str*>));

  // Unlike Python, this is -1, not 255!
  int mod = -1 % 256;
  log("mod = %d", mod);

  log("alignof(bool) = %d", alignof(bool));
  log("alignof(int) = %d", alignof(int));
  log("alignof(float) = %d", alignof(float));

  log("sizeof(Str) = %d", sizeof(Str));
  log("alignof(Str) = %d", alignof(Str));

  log("sizeof(Str*) = %d", sizeof(Str*));
  log("alignof(Str*) = %d", alignof(Str*));

  log("sizeof(flag_spec::_FlagSpecAndMore) = %d",
      sizeof(flag_spec::_FlagSpecAndMore));
  // alignment is 8, so why doesn't it work?
  log("alignof(flag_spec::_FlagSpecAndMore) = %d",
      alignof(flag_spec::_FlagSpecAndMore));

  // throw off the alignment
  auto i = new bool[1];

  auto out = new flag_spec::_FlagSpecAndMore();
  log("sizeof(out) = %d", sizeof(out));

  log("sizeof(flag_spec::_FlagSpec) = %d", sizeof(flag_spec::_FlagSpec));
  // alignment is 8, so why doesn't it work?
  log("alignof(flag_spec::_FlagSpec) = %d", alignof(flag_spec::_FlagSpec));
  auto out2 = new flag_spec::_FlagSpec();
  log("sizeof(out2) = %d", sizeof(out2));

  log("alignof(max_align_t) = %d", alignof(max_align_t));

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

    // BUG: cstring-TODO: Truncated string causes read past len_
    // Need a length check!
#if 0
  match::SimpleLexer* lex2 = match::BraceRangeLexer(new Str("1234", 2));
  while (true) {
    auto t = lex2->Next();
    int id = t.at0();
    if (id == id__Eol_Tok) {
      break;
    }
    log("id = %d", id);
    log("val = %s", t.at1()->data_);
  }
#endif

  // Similar to native/fastlex_test.py.  Just test that it matched
  ASSERT_EQ(0, match::MatchOption(new Str("")));
  ASSERT(match::MatchOption(new Str("pipefail")) > 0);

  ASSERT_EQ(0, match::MatchOption(new Str("pipefai")));
  ASSERT_EQ(0, match::MatchOption(new Str("pipefail_")));

  ASSERT_EQ(Id::BoolUnary_G, match::BracketUnary(new Str("-G")));
  ASSERT_EQ(Id::Undefined_Tok, match::BracketUnary(new Str("-Gz")));
  ASSERT_EQ(Id::Undefined_Tok, match::BracketUnary(new Str("")));

  ASSERT_EQ(Id::BoolBinary_NEqual, match::BracketBinary(new Str("!=")));
  ASSERT_EQ(Id::Undefined_Tok, match::BracketBinary(new Str("")));

  // This still works, but can't it overflow a buffer?
  Str* s = new Str("!= ");
  Str* stripped = s->strip();

  ASSERT_EQ(3, len(s));
  ASSERT_EQ(2, len(stripped));

  ASSERT_EQ(Id::BoolBinary_NEqual, match::BracketBinary(stripped));

  PASS();
}

TEST util_test() {
  // OK this seems to work
  Str* escaped = pyutil::BackslashEscape(new Str("'foo bar'"), new Str(" '"));
  ASSERT(str_equals(escaped, new Str("\\'foo\\ bar\\'")));

  Str* escaped2 = pyutil::BackslashEscape(new Str(""), new Str(" '"));
  ASSERT(str_equals(escaped2, new Str("")));

  Str* s = pyutil::ChArrayToString(new List<int>({65}));
  ASSERT(str_equals(s, new Str("A")));
  ASSERT_EQ_FMT(1, len(s), "%d");

  Str* s2 = pyutil::ChArrayToString(new List<int>({102, 111, 111}));
  ASSERT(str_equals(s2, new Str("foo")));
  ASSERT_EQ_FMT(3, len(s2), "%d");

  PASS();
}

TEST libc_test() {
  Str* s1 = (new Str("foo.py "))->strip();
  ASSERT(libc::fnmatch(new Str("*.py"), s1));
  ASSERT(!libc::fnmatch(new Str("*.py"), new Str("foo.p")));

  // extended glob
  ASSERT(libc::fnmatch(new Str("*(foo|bar).py"), new Str("foo.py")));
  ASSERT(!libc::fnmatch(new Str("*(foo|bar).py"), new Str("foo.p")));

  List<Str*>* results =
      libc::regex_match(new Str("(a+).(a+)"), new Str("-abaacaaa"));
  ASSERT_EQ_FMT(3, len(results), "%d");
  ASSERT(str_equals(new Str("abaa"), results->index(0)));  // whole match
  ASSERT(str_equals(new Str("a"), results->index(1)));
  ASSERT(str_equals(new Str("aa"), results->index(2)));

  results = libc::regex_match(new Str("z+"), new Str("abaacaaa"));
  ASSERT_EQ(nullptr, results);

  Tuple2<int, int>* result;
  Str* s = new Str("oXooXoooXoX");
  result = libc::regex_first_group_match(new Str("(X.)"), s, 0);
  ASSERT_EQ_FMT(1, result->at0(), "%d");
  ASSERT_EQ_FMT(3, result->at1(), "%d");

  result = libc::regex_first_group_match(new Str("(X.)"), s, 3);
  ASSERT_EQ_FMT(4, result->at0(), "%d");
  ASSERT_EQ_FMT(6, result->at1(), "%d");

  result = libc::regex_first_group_match(new Str("(X.)"), s, 6);
  ASSERT_EQ_FMT(8, result->at0(), "%d");
  ASSERT_EQ_FMT(10, result->at1(), "%d");

  // This depends on the file system
  auto files = libc::glob(new Str("*.md"));
  ASSERT_EQ_FMT(1, len(files), "%d");
  print(files->index(0));  // should get README.md only

  auto files2 = libc::glob(new Str("*.pyzzz"));
  ASSERT_EQ_FMT(0, len(files2), "%d");

  Str* h = libc::gethostname();
  log("gethostname() =");
  print(h);

  PASS();
}

TEST time_test() {
  int ts = time_::time();
  log("ts = %d", ts);
  ASSERT(ts > 0);
  PASS();
}

TEST posix_test() {
  Str* cwd = posix::getcwd();
  log("getcwd() =");
  print(cwd);

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

Action_c arity1_1[] = {
    {"z", ActionType_c::SetToInt, "z"},
    {"zz", ActionType_c::SetToString, "zz"},
    {},  // sentinel
};

Action_c actions_long_1[] = {
    {"all", ActionType_c::SetToTrue, "all"},
    {"line", ActionType_c::SetToTrue, "line"},
    {},  // sentinel
};

const char* plus_1[] = {"o", "p", nullptr};

DefaultPair_c defaults_1[] = {
    {"x", flag_type_e::Bool},
    {"y", flag_type_e::Int},
    {},
};

DefaultPair_c defaults_2[] = {
    {"b", flag_type_e::Bool, {.b = true}},
    {"i", flag_type_e::Int, {.i = 42}},
    {"f", flag_type_e::Float, {.f = 3.14}},
    {"s", flag_type_e::Str, {.s = "foo"}},
    {},
};

FlagSpec_c spec1 = {"export",       arity0_1, arity1_1,
                    actions_long_1, plus_1,   defaults_1};
// a copy for demonstrations
FlagSpec_c spec2 = {"unset",        arity0_1, arity1_1,
                    actions_long_1, plus_1,   defaults_1};

TEST flag_spec_test() {
  // Test the declared constants
  log("spec1.arity0 %s", spec1.arity0[0]);
  log("spec1.arity0 %s", spec1.arity0[1]);

  log("spec1.arity1 %s", spec1.arity1[0].name);
  log("spec1.arity1 %s", spec1.arity1[1].name);

  log("spec1.plus_flags %s", spec1.plus_flags[0]);
  log("spec1.plus_flags %s", spec1.plus_flags[1]);

  log("spec1.defaults %s", spec1.defaults[0].name);
  log("spec1.defaults %s", spec1.defaults[1].name);

  log("sizeof %d", sizeof(spec1.arity0));  // 8
  log("sizeof %d", sizeof(arity0_1) / sizeof(arity0_1[0]));

  flag_spec::LookupFlagSpec(new Str("new_var"));
  flag_spec::LookupFlagSpec(new Str("readonly"));
  flag_spec::LookupFlagSpec(new Str("zzz"));

  int i = 0;
  while (true) {
    DefaultPair_c* d = &(defaults_2[i]);
    if (!d->name) {
      break;
    }
    switch (d->typ) {
    case flag_type_e::Bool:
      log("b = %d", d->val.b);
      break;
    case flag_type_e::Int:
      log("i = %d", d->val.i);
      break;
    case flag_type_e::Float:
      log("b = %f", d->val.f);
      break;
    case flag_type_e::Str:
      log("b = %s", d->val.s);
      break;
    }
    ++i;
  }

  PASS();
}

TEST bool_stat_test() {
  int fail = 0;
  try {
    bool b1 = bool_stat::isatty(new Str("invalid"), nullptr);
  } catch (error::FatalRuntime* e) {
    fail++;
  }
  ASSERT_EQ(1, fail);

  bool b2 = bool_stat::isatty(new Str("0"), nullptr);
  // This will be true interactively
  log("stdin isatty = %d", b2);

  PASS();
}

TEST pyos_test() {
  // This test isn't hermetic but it should work in most places, including in a
  // container

  int err_num = pyos::Chdir(new Str("/"));
  ASSERT(err_num == 0);

  err_num = pyos::Chdir(new Str("/nonexistent__"));
  ASSERT(err_num != 0);

  Dict<Str*, Str*>* env = pyos::Environ();
  Str* p = env->get(new Str("PATH"));
  ASSERT(p != nullptr);
  log("PATH = %s", p->data_);

  PASS();
}

TEST os_path_test() {
  // TODO: use mylib2 here, with NewStr(), StackRoots, etc.
  Str* s = nullptr;

  s = os_path::rstrip_slashes(new Str(""));
  ASSERT(str_equals(s, new Str("")));

  s = os_path::rstrip_slashes(new Str("foo"));
  ASSERT(str_equals(s, new Str("foo")));

  s = os_path::rstrip_slashes(new Str("foo/"));
  ASSERT(str_equals(s, new Str("foo")));

  s = os_path::rstrip_slashes(new Str("/foo/"));
  ASSERT(str_equals(s, new Str("/foo")));

  // special case of not stripping
  s = os_path::rstrip_slashes(new Str("///"));
  ASSERT(str_equals(s, new Str("///")));

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  // TODO: use garbage collection in this test?

  GREATEST_MAIN_BEGIN();
  RUN_TEST(show_sizeof);
  RUN_TEST(match_test);
  RUN_TEST(util_test);
  RUN_TEST(libc_test);
  RUN_TEST(time_test);
  RUN_TEST(posix_test);
  RUN_TEST(exceptions);
  RUN_TEST(flag_spec_test);
  RUN_TEST(bool_stat_test);
  RUN_TEST(pyos_test);
  RUN_TEST(os_path_test);
  GREATEST_MAIN_END(); /* display results */
  return 0;
}
