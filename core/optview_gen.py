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
    f.write('  bool %s() { return opt_array->index(option::%s); }\n' % (n, n))


def main(argv):
  f = sys.stdout

  f.write("""\
#ifndef OPTVIEW_H
#define OPTVIEW_H

#include "mylib.h"
#include "option_asdl.h"

// duplication because mycpp doesn't export headers
namespace state {
class _ErrExit {
 public:
  bool value();
};
}

namespace optview {

namespace option = option_asdl::option;

class Parse {
 public:
  Parse(List<bool>* opt_array)
      : opt_array(opt_array) {
  }
""")

  GenMethods(option_def.PARSE_OPTION_NAMES, f)

  f.write("""\

  List<bool>* opt_array;
};

class Exec {
 public:
  Exec(List<bool>* opt_array, state::_ErrExit* errexit)
      : opt_array(opt_array), errexit_(errexit) {
  }

  bool errexit() {
    return errexit_->value();
  }
""")

  GenMethods(option_def.EXEC_OPTION_NAMES, f)

  f.write("""\

  List<bool>* opt_array;
  state::_ErrExit* errexit_;
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
