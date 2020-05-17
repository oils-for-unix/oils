// frontend_arg_def.h

#ifndef FRONTEND_ARG_DEF_H
#define FRONTEND_ARG_DEF_H

#include "id_kind_asdl.h"
#include "mylib.h"
#include "runtime_asdl.h"

// Forward declarations
namespace args {
class _Action;
class SetToArg;

class _Attributes;
class Reader;
};  // namespace args

//
// Types for compile-time FlagSpec
//

struct SetToArg_c {
  const char* name;  // note: this field is redundant
  int flag_type;
  bool quit_parsing;
};

enum class Default_c {
  Undef,  // default for strings
  False,
  True,
};

struct DefaultPair_c {
  const char* name;
  Default_c default_val;
};

struct FlagSpec_c {
  const char* name;
  const char** arity0;   // NULL terminated array
  SetToArg_c* arity1;    // NULL terminated array
  const char** options;  // NULL terminated array
  DefaultPair_c* defaults;
};

namespace arg_def {

// TODO: Should be replaced with an ASDL type.
class _FlagSpecAndMore {
 public:
  Dict<Str*, args::_Action*>* actions_long;
  Dict<Str*, args::_Action*>* actions_short;
  Dict<Str*, runtime_asdl::value_t*>* defaults;
};

// for testing only
runtime_asdl::FlagSpec_* LookupFlagSpec(Str* spec_name);

args::_Attributes* Parse(Str* spec_name, args::Reader* arg_r);

Tuple2<args::_Attributes*, int> ParseCmdVal(
    Str* spec_name, runtime_asdl::cmd_value__Argv* arg_r);

}  // namespace arg_def

#endif  // FRONTEND_ARG_DEF_H
