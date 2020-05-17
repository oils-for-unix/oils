// frontend_arg_def.cc

#include "frontend_arg_def.h"
#include "arg_types.h"

// "header" copied from _build/cpp/osh_eval.cc.  TODO: mycpp should be able to
// export headers!
namespace args {
args::_Attributes* Parse(runtime_asdl::FlagSpec_* spec, args::Reader* arg_r);
}

namespace arg_def {

using arg_types::kFlagSpecs;
using runtime_asdl::value__Undef;
using runtime_asdl::value_t;

// "Inflate" the static C data into a heap-allocated ASDL data structure.
//
// TODO: Make a GLOBAL CACHE?  It could be shared between subinterpreters even?
runtime_asdl::FlagSpec_* CreateSpec(FlagSpec_c* in) {
  auto out = new runtime_asdl::FlagSpec_();

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
      // log("a1 %s", p->name);
      ++i;
    }
  }

  if (in->options) {
    int i = 0;
    while (true) {
      const char* s = in->options[i];
      if (!s) {
        break;
      }
      // log("option %s", s);
      out->options->append(new Str(s));
      ++i;
    }
  }

  if (in->defaults) {
    int i = 0;
    while (true) {
      DefaultPair_c* d = &(in->defaults[i]);
      if (!d->name) {
        break;
      }
      // log("default %s", d->name);
      value_t* val = new value__Undef();
      out->defaults->set(new Str(d->name), val);
      ++i;
    }
  }

  return out;
}

runtime_asdl::FlagSpec_* LookupFlagSpec(Str* spec_name) {
  int i = 0;
  while (true) {
    const char* name = kFlagSpecs[i].name;
    if (name == nullptr) {
      break;
    }
    // TODO: Str* should be serialized with length?
    int n = std::min(spec_name->len_, static_cast<int>(strlen(name)));
    if (memcmp(name, spec_name->data_, n) == 0) {
      // log("%s found", spec_name->data_);
      return CreateSpec(&kFlagSpecs[i]);
    }

    i++;
  }
  // log("%s not found", spec_name->data_);
  return nullptr;
}

args::_Attributes* Parse(Str* spec_name, args::Reader* arg_r) {
  runtime_asdl::FlagSpec_* spec = LookupFlagSpec(spec_name);
  assert(spec);  // should always be found

#ifdef CPP_UNIT_TEST
  // hack because we don't want to depend on a translation of args.py
  return nullptr;
#else
  return args::Parse(spec, arg_r);
#endif
}

Tuple2<args::_Attributes*, int> ParseCmdVal(
    Str* spec_name, runtime_asdl::cmd_value__Argv* arg_r) {
  assert(0);
}

}  // namespace arg_def
