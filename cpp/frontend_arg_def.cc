// frontend_arg_def.cc

#include "frontend_arg_def.h"
#include "arg_types.h"

namespace arg_def {

using arg_types::kFlagSpecs;
using arg_types::kNumFlagSpecs;

_FlagSpec* LookupFlagSpec(Str* spec_name) {
  log("n = %d", kNumFlagSpecs);
  for (int i = 0; i < kNumFlagSpecs; ++i) {
    // TODO: Str* should be serialized with length?
    int n = std::min(static_cast<size_t>(spec_name->len_),
                     strlen(kFlagSpecs[i].name));
    if (memcmp(kFlagSpecs[i].name, spec_name->data_, n) == 0) {
      log("%s found", spec_name->data_);
      return NULL;
    }
  }
  log("%s not found", spec_name->data_);
  return NULL;
}

args::_Attributes* Parse(Str* spec_name, args::Reader* arg_r) {
  _FlagSpec* spec = LookupFlagSpec(spec_name);
  // Parse(Spec)
  // TODO:
  // lookup spec_name in a table of constants
  //
  // frontend/arg_gen.py should generate constants
  assert(0);
}

Tuple2<args::_Attributes*, int> ParseCmdVal(
    Str* spec_name, runtime_asdl::cmd_value__Argv* arg_r) {
  assert(0);
}

}  // namespace arg_def
