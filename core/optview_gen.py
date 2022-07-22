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

#include "_build/cpp/option_asdl.h"
#ifdef LEAKY_BINDINGS
  #include "mycpp/mylib_old.h"
#else
  #include "mycpp/gc_heap.h"
  using gc_heap::List;
#endif

namespace optview {

namespace option_i = option_asdl::option_i;

class _View {
 public:
  _View(List<bool>* opt0_array, List<List<bool>*>* opt_stacks)
      : opt0_array(opt0_array), opt_stacks(opt_stacks) {
  }

  bool _Get(int opt_num) {
    List<bool>* overlay = opt_stacks->index_(opt_num);
    if ((overlay == nullptr) or len(overlay) == 0) {
      return opt0_array->index_(opt_num);
    } else {
      return overlay->index_(-1);
    }
  }

  List<bool>* opt0_array;
  List<List<bool>*>* opt_stacks;
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

#ifndef OSH_PARSE  // hack for osh_parse, set in build/mycpp.sh
class Exec : public _View {
 public:
  Exec(List<bool>* opt0_array, List<List<bool>*>* opt_stacks)
      : _View(opt0_array, opt_stacks) {
  }
""")

  GenMethods(option_def.ExecOptNames(), f)

  f.write("""\
};
#endif  // OSH_PARSE

}  // namespace optview

#endif  // OPTVIEW_H
""")


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
