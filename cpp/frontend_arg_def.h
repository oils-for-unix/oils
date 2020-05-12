// frontend_arg_def.h

#ifndef FRONTEND_ARG_DEF_H
#define FRONTEND_ARG_DEF_H

#include "id_kind_asdl.h"
#include "mylib.h"
#include "runtime_asdl.h"

// TODO: Move to mylib.h?
//
// Add List too.

template <class K, class V>
class ConstantDict {
 public:
  // So you can specialize this to take a pointer to some kind of literal?
  // Or use initializer_list in C++?
  ConstantDict() {
  }

  // Get a key.
  // Returns nullptr if not found (Can't use this for non-pointer types?)
  V get(K key) {
    return false;
  }
};



namespace args {
class _Action;
class SetToArg;

class _Attributes;
class Reader;
};  // namespace args

namespace arg_def {

class _FlagSpec {
 public:
  //Dict<Str*, bool>* arity0;
  ConstantDict<Str*, bool>* arity0;
  Dict<Str*, args::SetToArg*>* arity1;
  Dict<Str*, bool>* options;
  Dict<Str*, runtime_asdl::value_t*>* defaults;
};

class _FlagSpecAndMore {
 public:
  Dict<Str*, args::_Action*>* actions_long;
  Dict<Str*, args::_Action*>* actions_short;
  Dict<Str*, runtime_asdl::value_t*>* defaults;
};

args::_Attributes* Parse(Str* spec_name, args::Reader* arg_r);

Tuple2<args::_Attributes*, int> ParseCmdVal(
    Str* spec_name, runtime_asdl::cmd_value__Argv* arg_r);

}  // namespace arg_def

#endif  // FRONTEND_ARG_DEF_H
