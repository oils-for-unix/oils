// frontend_flag_spec.h

#ifndef FRONTEND_FLAG_SPEC_H
#define FRONTEND_FLAG_SPEC_H

#include "_gen/core/runtime.asdl.h"
#include "_gen/core/value.asdl.h"
#include "_gen/frontend/id_kind.asdl.h"
#include "mycpp/runtime.h"

// Forward declarations (can't include osh_eval.h)
namespace args {
class _Action;
class _Attributes;
class Reader;
};  // namespace args

//
// Types for compile-time FlagSpec
//

union Val_c {
  bool b;
  int i;
  float f;
  const char* s;
};

struct DefaultPair_c {
  const char* name;
  runtime_asdl::flag_type_t typ;
  Val_c val;
};

// all concrete subtypes of args::_Action
enum class ActionType_c {
  SetToString,    // name, valid
  SetToString_q,  // hack for quit_parsing_flags

  SetToInt,         // name
  SetToFloat,       // name
  SetToTrue,        // name
  SetAttachedBool,  // name, for OilFlags

  SetOption,             // name
  SetNamedOption,        // no args, valid
  SetNamedOption_shopt,  // no args, valid
  SetAction,             // name
  SetNamedAction,        // no args, valid
};

// TODO: Figure out the difference between name and key
// key = '--ast-format'
// name = 'ast-format'
// out.Set('ast-format', ...)
// So I want to compress these two

struct Action_c {
  const char* key;
  ActionType_c type;
  const char* name;
  // for --ast-format, SetNamedAction(), SetNamedOption()
  const char** strs;
};

struct FlagSpec_c {
  const char* name;         // e.g. 'wait'
  const char** arity0;      // NULL terminated array
  Action_c* arity1;         // NULL terminated array
  Action_c* actions_long;   // NULL terminated array
  const char** plus_flags;  // NULL terminated array
  DefaultPair_c* defaults;
};

struct FlagSpecAndMore_c {
  const char* name;  // e.g. 'osh'
  // These are Dict[str, _Action]
  Action_c* actions_short;
  Action_c* actions_long;
  const char** plus_flags;  // NULL terminated array
  DefaultPair_c* defaults;
};

namespace flag_spec {

class _FlagSpec {
 public:
  _FlagSpec()
      : arity0(nullptr),
        arity1(nullptr),
        plus_flags(nullptr),
        actions_long(nullptr),
        defaults(nullptr) {
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(_FlagSpec));
  }

  List<BigStr*>* arity0;
  Dict<BigStr*, args::_Action*>* arity1;
  List<BigStr*>* plus_flags;
  Dict<BigStr*, args::_Action*>* actions_long;
  Dict<BigStr*, value_asdl::value_t*>* defaults;

  static constexpr uint32_t field_mask() {
    return maskbit(offsetof(_FlagSpec, arity0)) |
           maskbit(offsetof(_FlagSpec, arity1)) |
           maskbit(offsetof(_FlagSpec, plus_flags)) |
           maskbit(offsetof(_FlagSpec, actions_long)) |
           maskbit(offsetof(_FlagSpec, defaults));
  }
};

class _FlagSpecAndMore {
 public:
  _FlagSpecAndMore()
      : actions_long(nullptr),
        actions_short(nullptr),
        plus_flags(nullptr),
        defaults(nullptr) {
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(_FlagSpecAndMore));
  }

  Dict<BigStr*, args::_Action*>* actions_long;
  Dict<BigStr*, args::_Action*>* actions_short;
  List<BigStr*>* plus_flags;
  Dict<BigStr*, value_asdl::value_t*>* defaults;

  static constexpr uint32_t field_mask() {
    return maskbit(offsetof(_FlagSpecAndMore, actions_long)) |
           maskbit(offsetof(_FlagSpecAndMore, actions_short)) |
           maskbit(offsetof(_FlagSpecAndMore, plus_flags)) |
           maskbit(offsetof(_FlagSpecAndMore, defaults));
  }
};

// for testing only
flag_spec::_FlagSpec* LookupFlagSpec(BigStr* spec_name);
flag_spec::_FlagSpecAndMore* LookupFlagSpec2(BigStr* spec_name);

args::_Attributes* Parse(BigStr* spec_name, args::Reader* arg_r);

Tuple2<args::_Attributes*, args::Reader*> ParseCmdVal(
    BigStr* spec_name, runtime_asdl::cmd_value::Argv* cmd_val);

// With optional arg
Tuple2<args::_Attributes*, args::Reader*> ParseCmdVal(
    BigStr* spec_name, runtime_asdl::cmd_value::Argv* cmd_val,
    bool accept_typed_args);

Tuple2<args::_Attributes*, args::Reader*> ParseLikeEcho(
    BigStr* spec_name, runtime_asdl::cmd_value::Argv* cmd_val);

args::_Attributes* ParseMore(BigStr* spec_name, args::Reader* arg_r);

}  // namespace flag_spec

#endif  // FRONTEND_FLAG_SPEC_H
