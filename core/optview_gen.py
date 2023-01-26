#!/usr/bin/env python2
"""
optview_gen.py

"""
from __future__ import print_function

import sys

from frontend import option_def
#from core import optview


def GenMethods(opt_names, f):
  for n in opt_names:
    f.write('  bool %s() { return _Get(option_i::%s); }\n' % (n, n))


def main(argv):
  f = sys.stdout

  f.write("""\
#ifndef OPTVIEW_H
#define OPTVIEW_H

#include "_gen/frontend/option.asdl.h"
#include "mycpp/runtime.h"

namespace optview {

using option_asdl::option_i;

class _View {
 public:
  _View(List<bool>* opt0_array, List<List<bool>*>* opt_stacks)
      : GC_CLASS_FIXED(header_, field_mask(), sizeof(_View)),
        opt0_array(opt0_array), opt_stacks(opt_stacks) {
  }

  bool _Get(int opt_num) {
    List<bool>* overlay = opt_stacks->index_(opt_num);
    if ((overlay == nullptr) or len(overlay) == 0) {
      return opt0_array->index_(opt_num);
    } else {
      return overlay->index_(-1);
    }
  }

  GC_OBJ(header_);
  List<bool>* opt0_array;
  List<List<bool>*>* opt_stacks;

  static constexpr uint16_t field_mask() {
    return
      maskbit(offsetof(_View, opt0_array))
    | maskbit(offsetof(_View, opt_stacks));
  }
};

class Parse : public _View {
 public:
  Parse(List<bool>* opt0_array, List<List<bool>*>* opt_stacks)
      : _View(opt0_array, opt_stacks) {
  }
""")

  GenMethods(option_def.ParseOptNames(), f)

  f.write("""\
};

class Exec : public _View {
 public:
  Exec(List<bool>* opt0_array, List<List<bool>*>* opt_stacks)
      : _View(opt0_array, opt_stacks) {
  }
""")

  GenMethods(option_def.ExecOptNames(), f)

  f.write("""\
};

}  // namespace optview

#endif  // OPTVIEW_H
""")


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
