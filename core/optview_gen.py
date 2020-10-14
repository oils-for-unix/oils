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
    f.write('  bool %s() { return opt0_array->index(option_i::%s); }\n' % (n, n))


def main(argv):
  f = sys.stdout

  f.write("""\
#ifndef OPTVIEW_H
#define OPTVIEW_H

#include "mylib.h"
#include "option_asdl.h"

namespace optview {

namespace option_i = option_asdl::option_i;

class Parse {
 public:
  Parse(List<bool>* opt0_array, List<List<bool>*>* opt_stacks)
      : opt0_array(opt0_array), opt_stacks(opt_stacks) {
  }
""")

  GenMethods(option_def.ParseOptNames(), f)

  f.write("""\

  List<bool>* opt0_array;
  List<List<bool>*>* opt_stacks;
};

#ifndef OSH_PARSE  // hack for osh_parse, set in build/mycpp.sh
class Exec {
 public:
  Exec(List<bool>* opt0_array, List<List<bool>*>* opt_stacks)
      : opt0_array(opt0_array), opt_stacks(opt_stacks) {
  }
""")

  GenMethods(option_def.ExecOptNames(), f)

  f.write("""\

  List<bool>* opt0_array;
  List<List<bool>*>* opt_stacks;
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
