// frontend_arg_def.h

#ifndef FRONTEND_ARG_DEF_H
#define FRONTEND_ARG_DEF_H

#include "mylib.h"

namespace args {
class _Action;
class SetToArg;
};

namespace arg_def {

class _FlagSpec {
 public:
  Dict<Str*, bool>* arity0;
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
 
}  // namespace arg_def

#endif  // FRONTEND_ARG_DEF_H

