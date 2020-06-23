// frontend_arg_def.h

#ifndef FRONTEND_ARG_DEF_H
#define FRONTEND_ARG_DEF_H

#include "id_kind_asdl.h"
#include "mylib.h"
#include "runtime_asdl.h"

// Forward declarations (can't include osh_eval.h)
namespace args {
class _Action;
class SetToArgAction;

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
  const char** plus_flags;  // NULL terminated array
  DefaultPair_c* defaults;
};

//
// For FlagSpecAndMore
//

enum class ActionType_c {
  SetToArg,        // name, flag_type, quit_parsing_flags
  SetBoolToArg,    // name
  SetToTrue,       // name
  SetOption,       // name
  SetNamedOption,  // no args
  SetAction,       // name
  SetNamedAction,  // no args
};

// TODO: Figure out the difference between name and key
// key = '--ast-format'
// name = 'ast-format'
// out.Set('ast-format', ...)
// So I want to compress these two

struct Action_c {
  ActionType_c type;
  const char* name;

  // TODO: fold this into ActionType_c
  int flag_type;
  // TODO: also get rid of it somehow
  bool quit_parsing_flags;

  // to replace flag_type.Enum
  // for SetNamedAction() and SetNamedOption
  const char** valid;
};

struct FlagSpecAndMore_c {
  const char* name;
  // These are Dict[str, _Action]
  Action_c* actions_short;
  Action_c* actions_long;
  // TODO: need strings as defaults
  DefaultPair_c* defaults;
};

namespace flag_spec {

class _FlagSpec {
 public:
  List<Str*>* arity0;
  Dict<Str*, args::SetToArgAction*>* arity1;
  Dict<Str*, runtime_asdl::value_t*>* defaults;
  List<Str*>* plus_flags;
};

class _FlagSpecAndMore {
 public:
  Dict<Str*, args::_Action*>* actions_long;
  Dict<Str*, args::_Action*>* actions_short;
  Dict<Str*, runtime_asdl::value_t*>* defaults;
  List<Str*>* plus_flags;
};

// for testing only
flag_spec::_FlagSpec* LookupFlagSpec(Str* spec_name);

args::_Attributes* Parse(Str* spec_name, args::Reader* arg_r);

Tuple2<args::_Attributes*, args::Reader*> ParseCmdVal(
    Str* spec_name, runtime_asdl::cmd_value__Argv* cmd_val);

Tuple2<args::_Attributes*, args::Reader*> ParseLikeEcho(
    Str* spec_name, runtime_asdl::cmd_value__Argv* cmd_val);

args::_Attributes* ParseMore(Str* spec_name, args::Reader* arg_r);

}  // namespace flag_spec

#endif  // FRONTEND_ARG_DEF_H
