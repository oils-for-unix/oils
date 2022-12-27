// frontend_flag_spec.cc

#include "cpp/frontend_flag_spec.h"

#include "_gen/frontend/arg_types.h"
#include "mycpp/gc_builtins.h"
// TODO: This prebuilt header should not be included in the tarball
// for definition of args::Reader, etc.
#include "prebuilt/frontend/args.mycpp.h"

namespace flag_spec {

using arg_types::kFlagSpecs;
using arg_types::kFlagSpecsAndMore;
using runtime_asdl::flag_type_e;
using runtime_asdl::value__Bool;
using runtime_asdl::value__Undef;
using runtime_asdl::value_t;

void _CreateStrList(const char** in, List<Str*>* out) {
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
                     Dict<Str*, runtime_asdl::value_t*>* out) {
  int i = 0;
  while (true) {
    DefaultPair_c* pair = &(in[i]);
    if (!pair->name) {
      break;
    }
    value_t* val;
    switch (pair->typ) {
    case flag_type_e::Bool:
      val = Alloc<value__Bool>(pair->val.b);
      break;
    case flag_type_e::Int:
      val = Alloc<value__Int>(pair->val.i);
      break;
    case flag_type_e::Float:
      val = Alloc<value__Float>(pair->val.f);
      break;
    case flag_type_e::Str: {
      const char* s = pair->val.s;
      if (s == nullptr) {
        val = Alloc<value__Undef>();
      } else {
        val = Alloc<value__Str>(StrFromC(s));
      }
    } break;
    default:
      FAIL(kShouldNotGetHere);
    }
    out->set(StrFromC(pair->name), val);
    ++i;
  }
}

#ifndef CPP_UNIT_TEST
void _CreateActions(Action_c* in, Dict<Str*, args::_Action*>* out) {
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
      List<Str*>* valid = nullptr;
      if (p->strs) {
        valid = NewList<Str*>();
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
    }

    if (action) {
      out->set(StrFromC(p->key), action);
    }
    ++i;
  }
}
#endif

// "Inflate" the static C data into a heap-allocated ASDL data structure.
//
// TODO: Make a GLOBAL CACHE?  It could be shared between subinterpreters even?
flag_spec::_FlagSpec* CreateSpec(FlagSpec_c* in) {
  auto out = Alloc<flag_spec::_FlagSpec>();
  out->arity0 = NewList<Str*>();
  out->arity1 = NewDict<Str*, args::_Action*>();
  out->actions_long = NewDict<Str*, args::_Action*>();
  out->plus_flags = NewList<Str*>();
  out->defaults = NewDict<Str*, runtime_asdl::value_t*>();

  if (in->arity0) {
    _CreateStrList(in->arity0, out->arity0);
  }
#ifndef CPP_UNIT_TEST
  if (in->arity1) {
    _CreateActions(in->arity1, out->arity1);
  }
  if (in->actions_long) {
    _CreateActions(in->actions_long, out->actions_long);
  }
#endif
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
  out->actions_short = NewDict<Str*, args::_Action*>();
  out->actions_long = NewDict<Str*, args::_Action*>();
  out->plus_flags = NewList<Str*>();
  out->defaults = NewDict<Str*, runtime_asdl::value_t*>();

#ifndef CPP_UNIT_TEST
  if (in->actions_short) {
    _CreateActions(in->actions_short, out->actions_short);
  }

  if (in->actions_long) {
    _CreateActions(in->actions_long, out->actions_long);
  }
#endif
  if (in->plus_flags) {
    _CreateStrList(in->plus_flags, out->plus_flags);
  }
  if (in->defaults) {
    _CreateDefaults(in->defaults, out->defaults);
  }
  return out;
}

flag_spec::_FlagSpec* LookupFlagSpec(Str* spec_name) {
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

flag_spec::_FlagSpecAndMore* LookupFlagSpec2(Str* spec_name) {
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

args::_Attributes* Parse(Str* spec_name, args::Reader* arg_r) {
  flag_spec::_FlagSpec* spec = LookupFlagSpec(spec_name);
  assert(spec);  // should always be found

#ifdef CPP_UNIT_TEST
  // hack because we don't want to depend on a translation of args.py
  return nullptr;
#else
  return args::Parse(spec, arg_r);
#endif
}

Tuple2<args::_Attributes*, args::Reader*> ParseCmdVal(
    Str* spec_name, runtime_asdl::cmd_value__Argv* cmd_val) {
#ifdef CPP_UNIT_TEST
  return Tuple2<args::_Attributes*, args::Reader*>(nullptr, nullptr);
#else
  auto arg_r = Alloc<args::Reader>(cmd_val->argv, cmd_val->arg_spids);
  arg_r->Next();  // move past the builtin name

  flag_spec::_FlagSpec* spec = LookupFlagSpec(spec_name);
  assert(spec);  // should always be found
  return Tuple2<args::_Attributes*, args::Reader*>(args::Parse(spec, arg_r),
                                                   arg_r);
#endif
}

// With optional arg
Tuple2<args::_Attributes*, args::Reader*> ParseCmdVal(
    Str* spec_name, runtime_asdl::cmd_value__Argv* cmd_val,
    bool accept_typed_args) {
  // TODO: disallow typed args!
  return ParseCmdVal(spec_name, cmd_val);
}

Tuple2<args::_Attributes*, args::Reader*> ParseLikeEcho(
    Str* spec_name, runtime_asdl::cmd_value__Argv* cmd_val) {
#ifdef CPP_UNIT_TEST
  return Tuple2<args::_Attributes*, args::Reader*>(nullptr, nullptr);
#else
  auto arg_r = Alloc<args::Reader>(cmd_val->argv, cmd_val->arg_spids);
  arg_r->Next();  // move past the builtin name

  flag_spec::_FlagSpec* spec = LookupFlagSpec(spec_name);
  assert(spec);  // should always be found
  return Tuple2<args::_Attributes*, args::Reader*>(
      args::ParseLikeEcho(spec, arg_r), arg_r);
#endif
}

args::_Attributes* ParseMore(Str* spec_name, args::Reader* arg_r) {
#ifdef CPP_UNIT_TEST
  return nullptr;
#else
  // TODO: Fill this in from constant data!
  flag_spec::_FlagSpecAndMore* spec = LookupFlagSpec2(spec_name);
  assert(spec);
  return args::ParseMore(spec, arg_r);
#endif
}

}  // namespace flag_spec
