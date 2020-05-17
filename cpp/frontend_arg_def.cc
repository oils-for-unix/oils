// frontend_arg_def.cc

#include "frontend_arg_def.h"
#include "arg_types.h"

// "header" copied from _build/cpp/osh_eval.cc.  TODO: mycpp should be able to
// export headers!
namespace args {
args::_Attributes* Parse(runtime_asdl::FlagSpec_* spec, args::Reader* arg_r);
}

namespace arg_def {

using arg_types::kFlagSpecs;

void* LookupFlagSpec(Str* spec_name) {
  int i = 0;
  while (true) {
    const char* name = kFlagSpecs[i].name;
    if (name == nullptr) {
      break;
    }
    // TODO: Str* should be serialized with length?
    int n = std::min(static_cast<size_t>(spec_name->len_), strlen(name));
    if (memcmp(name, spec_name->data_, n) == 0) {
      log("%s found", spec_name->data_);
      return nullptr;
    }

    i++;
  }
  log("%s not found", spec_name->data_);
  return nullptr;
}

static void FillSpec(void* const_spec, runtime_asdl::FlagSpec_* out) {
}

args::_Attributes* Parse(Str* spec_name, args::Reader* arg_r) {
  void* const_spec = LookupFlagSpec(spec_name);
  // compile time data

  // TODO:
  // - lookup spec_name in a table of constants
  // - frontend/arg_gen.py should generate constants
  // - Manual code to create runtime
  // - Fill it in here.
  // - Make a GLOBAL CACHE?  It could be shared between subinterpreters even?

  runtime_asdl::FlagSpec_ spec;
  FillSpec(const_spec, &spec);

#ifdef CPP_UNIT_TEST
  // hack because we don't want to depend on a translation of args.py
  return nullptr;
#else
  return args::Parse(&spec, arg_r);
#endif
}

Tuple2<args::_Attributes*, int> ParseCmdVal(
    Str* spec_name, runtime_asdl::cmd_value__Argv* arg_r) {
  assert(0);
}

}  // namespace arg_def
