// frontend_flag_spec.cc

#include "cpp/frontend_flag_spec.h"

#include "_gen/frontend/arg_types.h"
#include "mycpp/gc_builtins.h"
// TODO: This prebuilt header should not be included in the tarball
// for definition of args::Reader, etc.
#include "prebuilt/frontend/args.mycpp.h"

namespace flag_util {

using runtime_asdl::flag_type_e;
using value_asdl::value;
using value_asdl::value_t;

void _CreateStrList(const char** in, List<BigStr*>* out) {
  int i = 0;
  while (true) {
    const char* s = in[i];
    if (!s) {
      break;
    }
    // log("a0 %s", s);
    out->append(StrFromC(s));
    ++i;
  }
}

void _CreateDefaults(DefaultPair_c* in,
                     Dict<BigStr*, value_asdl::value_t*>* out) {
  int i = 0;
  while (true) {
    DefaultPair_c* pair = &(in[i]);
    if (!pair->name) {
      break;
    }
    value_t* val;
    switch (pair->typ) {
    case flag_type_e::Bool:
      val = Alloc<value::Bool>(pair->val.b);
      break;
    case flag_type_e::Int:
      val = Alloc<value::Int>(pair->val.i);
      break;
    case flag_type_e::Float:
      val = Alloc<value::Float>(pair->val.f);
      break;
    case flag_type_e::Str: {
      const char* s = pair->val.s;
      if (s == nullptr) {
        val = value::Undef;
      } else {
        val = Alloc<value::Str>(StrFromC(s));
      }
    } break;
    default:
      FAIL(kShouldNotGetHere);
    }
    out->set(StrFromC(pair->name), val);
    ++i;
  }
}

void _CreateActions(Action_c* in, Dict<BigStr*, args::_Action*>* out) {
  int i = 0;
  while (true) {
    Action_c* p = &(in[i]);
    if (!p->key) {
      break;
    }
    // log("a1 %s", p->name);
    args::_Action* action = nullptr;
    switch (p->type) {
    case ActionType_c::SetToString: {
      List<BigStr*>* valid = nullptr;
      if (p->strs) {
        valid = NewList<BigStr*>();
        _CreateStrList(p->strs, valid);
      }
      auto a = Alloc<args::SetToString>(StrFromC(p->name), false, valid);
      action = a;
    } break;
    case ActionType_c::SetToString_q:
      action = Alloc<args::SetToString>(StrFromC(p->name), true, nullptr);
      break;
    case ActionType_c::SetToInt:
      action = Alloc<args::SetToInt>(StrFromC(p->name));
      break;
    case ActionType_c::SetToFloat:
      action = Alloc<args::SetToFloat>(StrFromC(p->name));
      break;
    case ActionType_c::SetToTrue:
      action = Alloc<args::SetToTrue>(StrFromC(p->name));
      break;
    case ActionType_c::SetAttachedBool:
      action = Alloc<args::SetAttachedBool>(StrFromC(p->name));
      break;
    case ActionType_c::SetOption:
      action = Alloc<args::SetOption>(StrFromC(p->name));
      break;
    case ActionType_c::SetNamedOption: {
      auto a = Alloc<args::SetNamedOption>(false);
      if (p->strs) {
        _CreateStrList(p->strs, a->names);
      }
      action = a;
    } break;
    case ActionType_c::SetNamedOption_shopt: {
      auto a = Alloc<args::SetNamedOption>(true);
      if (p->strs) {
        _CreateStrList(p->strs, a->names);
      }
      action = a;
    } break;
    case ActionType_c::SetAction:
      action = Alloc<args::SetAction>(StrFromC(p->name));
      break;
    case ActionType_c::SetNamedAction: {
      auto a = Alloc<args::SetNamedAction>();
      if (p->strs) {
        _CreateStrList(p->strs, a->names);
      }
      action = a;
    } break;
    case ActionType_c::AppendEvalFlag:
      action = Alloc<args::AppendEvalFlag>(StrFromC(p->name));
      break;
    }  // switch

    if (action) {
      out->set(StrFromC(p->key), action);
    }
    ++i;
  }
}

// Convenience function
template <typename K, typename V>
Dict<K, V>* NewDict() {
  return Alloc<Dict<K, V>>();
}

// "Inflate" the static C data into a heap-allocated ASDL data structure.
//
// TODO: Make a GLOBAL CACHE?  It could be shared between subinterpreters even?
flag_spec::_FlagSpec* CreateSpec(FlagSpec_c* in) {
  auto out = Alloc<flag_spec::_FlagSpec>();
  out->arity0 = NewList<BigStr*>();
  out->arity1 = NewDict<BigStr*, args::_Action*>();
  out->actions_long = NewDict<BigStr*, args::_Action*>();
  out->plus_flags = NewList<BigStr*>();
  out->defaults = NewDict<BigStr*, value_asdl::value_t*>();

  if (in->arity0) {
    _CreateStrList(in->arity0, out->arity0);
  }
  if (in->arity1) {
    _CreateActions(in->arity1, out->arity1);
  }
  if (in->actions_long) {
    _CreateActions(in->actions_long, out->actions_long);
  }
  if (in->plus_flags) {
    _CreateStrList(in->plus_flags, out->plus_flags);
  }
  if (in->defaults) {
    _CreateDefaults(in->defaults, out->defaults);
  }
  return out;
}

flag_spec::_FlagSpecAndMore* CreateSpec2(FlagSpecAndMore_c* in) {
  auto out = Alloc<flag_spec::_FlagSpecAndMore>();
  out->actions_short = NewDict<BigStr*, args::_Action*>();
  out->actions_long = NewDict<BigStr*, args::_Action*>();
  out->plus_flags = NewList<BigStr*>();
  out->defaults = NewDict<BigStr*, value_asdl::value_t*>();

  if (in->actions_short) {
    _CreateActions(in->actions_short, out->actions_short);
  }
  if (in->actions_long) {
    _CreateActions(in->actions_long, out->actions_long);
  }
  if (in->plus_flags) {
    _CreateStrList(in->plus_flags, out->plus_flags);
  }
  if (in->defaults) {
    _CreateDefaults(in->defaults, out->defaults);
  }
  return out;
}

using arg_types::kFlagSpecs;
using arg_types::kFlagSpecsAndMore;

flag_spec::_FlagSpec* LookupFlagSpec(BigStr* spec_name) {
  int i = 0;
  while (true) {
    const char* name = kFlagSpecs[i].name;
    if (name == nullptr) {
      break;
    }
    if (str_equals0(name, spec_name)) {
      // log("%s found", spec_name->data_);
      return CreateSpec(&kFlagSpecs[i]);
    }

    i++;
  }
  // log("%s not found", spec_name->data_);
  return nullptr;
}

flag_spec::_FlagSpecAndMore* LookupFlagSpec2(BigStr* spec_name) {
  int i = 0;
  while (true) {
    const char* name = kFlagSpecsAndMore[i].name;
    if (name == nullptr) {
      break;
    }
    if (str_equals0(name, spec_name)) {
      // log("%s found", spec_name->data_);
      return CreateSpec2(&kFlagSpecsAndMore[i]);
    }

    i++;
  }
  // log("%s not found", spec_name->data_);
  return nullptr;
}

}  // namespace flag_util
