// frontend_flag_spec.cc

#include "frontend_flag_spec.h"
#include "arg_types.h"

#ifndef CPP_UNIT_TEST
#include "osh_eval.h"  // args::Reader, etc.
#endif

namespace flag_spec {

using arg_types::kFlagSpecs;
using arg_types::kFlagSpecsAndMore;
using arg_types::kOilFlagSpecs;
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
    out->append(new Str(s));
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
      val = new value__Bool(pair->val.b);
      break;
    case flag_type_e::Int:
      val = new value__Int(pair->val.i);
      break;
    case flag_type_e::Float:
      val = new value__Float(pair->val.f);
      break;
    case flag_type_e::Str: {
      char* s = pair->val.s;
      if (s == nullptr) {
        val = new value__Undef();
      } else {
        val = new value__Str(new Str(s));
      }
    } break;
    default:
      assert(0);
    }
    out->set(new Str(pair->name), val);
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
        valid = new List<Str*>();
        _CreateStrList(p->strs, valid);
      }
      auto a = new args::SetToString(new Str(p->name), false, valid);
      action = a;
    } break;
    case ActionType_c::SetToString_q:
      action = new args::SetToString(new Str(p->name), true, nullptr);
      break;
    case ActionType_c::SetToInt:
      action = new args::SetToInt(new Str(p->name));
      break;
    case ActionType_c::SetToFloat:
      action = new args::SetToFloat(new Str(p->name));
      break;
    case ActionType_c::SetToTrue:
      action = new args::SetToTrue(new Str(p->name));
      break;
    case ActionType_c::SetAttachedBool:
      action = new args::SetAttachedBool(new Str(p->name));
      break;
    case ActionType_c::SetOption:
      action = new args::SetOption(new Str(p->name));
      break;
    case ActionType_c::SetNamedOption: {
      auto a = new args::SetNamedOption(false);
      if (p->strs) {
        _CreateStrList(p->strs, a->names);
      }
      action = a;
    } break;
    case ActionType_c::SetNamedOption_shopt: {
      auto a = new args::SetNamedOption(true);
      if (p->strs) {
        _CreateStrList(p->strs, a->names);
      }
      action = a;
    } break;
    case ActionType_c::SetAction:
      action = new args::SetAction(new Str(p->name));
      break;
    case ActionType_c::SetNamedAction: {
      auto a = new args::SetNamedAction();
      if (p->strs) {
        _CreateStrList(p->strs, a->names);
      }
      action = a;
    } break;
    }

    if (action) {
      out->set(new Str(p->key), action);
    }
    ++i;
  }
}
#endif

// "Inflate" the static C data into a heap-allocated ASDL data structure.
//
// TODO: Make a GLOBAL CACHE?  It could be shared between subinterpreters even?
flag_spec::_FlagSpec* CreateSpec(FlagSpec_c* in) {
  auto out = new flag_spec::_FlagSpec();
  out->arity0 = new List<Str*>();
  out->arity1 = new Dict<Str*, args::_Action*>();
  out->actions_long = new Dict<Str*, args::_Action*>();
  out->plus_flags = new List<Str*>();
  out->defaults = new Dict<Str*, runtime_asdl::value_t*>();

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
  auto out = new flag_spec::_FlagSpecAndMore();
  out->actions_short = new Dict<Str*, args::_Action*>();
  out->actions_long = new Dict<Str*, args::_Action*>();
  out->plus_flags = new List<Str*>();
  out->defaults = new Dict<Str*, runtime_asdl::value_t*>();

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

flag_spec::_OilFlagSpec* CreateSpecOil(OilFlagSpec_c* in) {
  auto out = new flag_spec::_OilFlagSpec();
  out->arity1 = new Dict<Str*, args::_Action*>();
  out->defaults = new Dict<Str*, runtime_asdl::value_t*>();

#ifndef CPP_UNIT_TEST
  if (in->arity1) {
    _CreateActions(in->arity1, out->arity1);
  }
#endif
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

flag_spec::_OilFlagSpec* LookupFlagSpecOil(Str* spec_name) {
  int i = 0;
  while (true) {
    const char* name = kOilFlagSpecs[i].name;
    if (name == nullptr) {
      break;
    }
    if (str_equals0(name, spec_name)) {
      // log("%s found", spec_name->data_);
      return CreateSpecOil(&kOilFlagSpecs[i]);
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
  auto arg_r = new args::Reader(cmd_val->argv, cmd_val->arg_spids);
  arg_r->Next();  // move past the builtin name

  flag_spec::_FlagSpec* spec = LookupFlagSpec(spec_name);
  assert(spec);  // should always be found
  return Tuple2<args::_Attributes*, args::Reader*>(args::Parse(spec, arg_r),
                                                   arg_r);
#endif
}

Tuple2<args::_Attributes*, args::Reader*> ParseLikeEcho(
    Str* spec_name, runtime_asdl::cmd_value__Argv* cmd_val) {
#ifdef CPP_UNIT_TEST
  return Tuple2<args::_Attributes*, args::Reader*>(nullptr, nullptr);
#else
  auto arg_r = new args::Reader(cmd_val->argv, cmd_val->arg_spids);
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
  // assert(spec);  // should always be found
  return args::ParseMore(spec, arg_r);
#endif
}

Tuple2<args::_Attributes*, args::Reader*> ParseOilCmdVal(
    Str* spec_name, runtime_asdl::cmd_value__Argv* cmd_val) {
#ifdef CPP_UNIT_TEST
  return Tuple2<args::_Attributes*, args::Reader*>(nullptr, nullptr);
#else
  auto arg_r = new args::Reader(cmd_val->argv, cmd_val->arg_spids);
  arg_r->Next();  // move past the builtin name

  flag_spec::_OilFlagSpec* spec = LookupFlagSpecOil(spec_name);
  assert(spec);  // should always be found
  return Tuple2<args::_Attributes*, args::Reader*>(args::ParseOil(spec, arg_r),
                                                   arg_r);
#endif
}

}  // namespace flag_spec
