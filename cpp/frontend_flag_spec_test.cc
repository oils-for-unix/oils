#include "cpp/frontend_flag_spec.h"

#include "vendor/greatest.h"

using runtime_asdl::flag_type_e;

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

  flag_spec::_FlagSpec* spec;

  spec = flag_spec::LookupFlagSpec(StrFromC("new_var"));
  ASSERT(spec != nullptr);

  spec = flag_spec::LookupFlagSpec(StrFromC("readonly"));
  ASSERT(spec != nullptr);

  spec = flag_spec::LookupFlagSpec(StrFromC("zzz"));
  ASSERT(spec == nullptr);

  flag_spec::_FlagSpecAndMore* spec2;

  spec2 = flag_spec::LookupFlagSpec2(StrFromC("main"));
  ASSERT(spec2 != nullptr);

  spec2 = flag_spec::LookupFlagSpec2(StrFromC("zzz"));
  ASSERT(spec2 == nullptr);

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

TEST show_sizeof() {
  log("sizeof(flag_spec::_FlagSpecAndMore) = %d",
      sizeof(flag_spec::_FlagSpecAndMore));
  // alignment is 8, so why doesn't it work?
  log("alignof(flag_spec::_FlagSpecAndMore) = %d",
      alignof(flag_spec::_FlagSpecAndMore));

#if 0
  // throw off the alignment
  __attribute__((unused)) auto i = new bool[1];
#endif

  auto out = Alloc<flag_spec::_FlagSpecAndMore>();
  log("sizeof(out) = %d", sizeof(out));

  log("sizeof(flag_spec::_FlagSpec) = %d", sizeof(flag_spec::_FlagSpec));
  // alignment is 8, so why doesn't it work?
  log("alignof(flag_spec::_FlagSpec) = %d", alignof(flag_spec::_FlagSpec));
  auto out2 = Alloc<flag_spec::_FlagSpec>();
  log("sizeof(out2) = %d", sizeof(out2));

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(flag_spec_test);
  RUN_TEST(show_sizeof);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
