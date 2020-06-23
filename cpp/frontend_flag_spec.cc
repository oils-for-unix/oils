// frontend_arg_def.cc

#include "frontend_flag_spec.h"
#include "arg_types.h"

#ifndef CPP_UNIT_TEST
#include "osh_eval.h"  // args::Reader, etc.
#endif

namespace flag_spec {

using arg_types::kFlagSpecs;
using arg_types::kFlagSpecsAndMore;
using runtime_asdl::flag_type__Str;
using runtime_asdl::value__Bool;
using runtime_asdl::value__Undef;
using runtime_asdl::value_t;

// "Inflate" the static C data into a heap-allocated ASDL data structure.
//
// TODO: Make a GLOBAL CACHE?  It could be shared between subinterpreters even?
flag_spec::_FlagSpec* CreateSpec(FlagSpec_c* in) {
  auto out = new flag_spec::_FlagSpec();
  out->arity0 = new List<Str*>();
  out->arity1 = new Dict<Str*, args::_Action*>();
  out->plus_flags = new List<Str*>();
  out->defaults = new Dict<Str*, runtime_asdl::value_t*>();

  if (in->arity0) {
    int i = 0;
    while (true) {
      const char* s = in->arity0[i];
      if (!s) {
        break;
      }
      // log("a0 %s", s);
      out->arity0->append(new Str(s));
      ++i;
    }
  }

  if (in->arity1) {
    int i = 0;
    while (true) {
      SetToArg_c* p = &(in->arity1[i]);
      if (!p->name) {
        break;
      }
      // TODO: Instantiate action!
      // log("a1 %s", p->name);
      ++i;
    }
  }

  if (in->plus_flags) {
    int i = 0;
    while (true) {
      const char* s = in->plus_flags[i];
      if (!s) {
        break;
      }
      // log("option %s", s);
      out->plus_flags->append(new Str(s));
      ++i;
    }
  }

  if (in->defaults) {
    int i = 0;
    while (true) {
      DefaultPair_c* pair = &(in->defaults[i]);
      if (!pair->name) {
        break;
      }
      // log("default %s", d->name);
      value_t* val;
      switch (pair->default_val) {
      case Default_c::Undef:
        val = new value__Undef();
        break;
      case Default_c::False:
        val = new value__Bool(false);
        break;
      case Default_c::True:
        val = new value__Bool(true);
        break;
      default:
        assert(0);
      }
      out->defaults->set(new Str(pair->name), val);
      ++i;
    }
  }

  return out;
}

#ifndef CPP_UNIT_TEST
flag_spec::_FlagSpecAndMore* CreateSpec2(FlagSpecAndMore_c* in) {
  auto out = new flag_spec::_FlagSpecAndMore();
  out->actions_short = new Dict<Str*, args::_Action*>();
  out->actions_long = new Dict<Str*, args::_Action*>();
  out->plus_flags = new List<Str*>();
  out->defaults = new Dict<Str*, runtime_asdl::value_t*>();

  if (in->actions_short) {
    int i = 0;
    while (true) {
      Action_c* p = &(in->actions_short[i]);
      if (!p->name) {
        break;
      }
      // log("a1 %s", p->name);
      args::_Action* action = nullptr;
      switch (p->type) {
      case ActionType_c::SetToArg: {
        action = new args::SetToString(new Str(p->name), p->quit_parsing_flags, nullptr);
        break;
      }
      case ActionType_c::SetToTrue:  // not generated yet
        break;
      }
      if (action) {
        out->actions_short->set(new Str(p->name), action);
      }
      ++i;
    }
  }

  if (in->defaults) {
    int i = 0;
    while (true) {
      DefaultPair_c* pair = &(in->defaults[i]);
      if (!pair->name) {
        break;
      }
      // log("default %s", d->name);
      value_t* val;
      switch (pair->default_val) {
      case Default_c::Undef:
        val = new value__Undef();
        break;
      case Default_c::False:
        val = new value__Bool(false);
        break;
      case Default_c::True:
        val = new value__Bool(true);
        break;
      default:
        assert(0);
      }
      out->defaults->set(new Str(pair->name), val);
      ++i;
    }
  }
  return out;
}
#endif

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
#ifdef CPP_UNIT_TEST
      return nullptr;
#else
      return CreateSpec2(&kFlagSpecsAndMore[i]);
#endif
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

}  // namespace flag_spec
