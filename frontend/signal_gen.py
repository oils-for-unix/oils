#!/usr/bin/env python2
from __future__ import print_function

import sys

import signal_def


def CppGetName(f):
    for abbrev, _ in signal_def._SIGNAL_LIST:
        name = "SIG%s" % (abbrev, )
        f.write('GLOBAL_STR(k%s, "%s");\n' % (name, name))

    f.write("""\
BigStr* GetName(int sig_num) {
  switch (sig_num) {
""")
    for abbrev, num in signal_def._SIGNAL_LIST:
        name = "SIG%s" % (abbrev, )
        f.write('  case %d:\n' % num)
        f.write('    return k%s;\n' % (name))
        f.write('    break;\n')
    f.write("""\
  default:
    return nullptr;
  }
}

""")


def CppGetNumber(f):
    f.write("""\
int GetNumber(BigStr* sig_spec) {
  int length = len(sig_spec);
  if (length == 0) {
    return NO_SIGNAL;
  }

  const char* data = sig_spec->data_;

""")
    for abbrev, _ in signal_def._SIGNAL_LIST:
        name = "SIG%s" % (abbrev, )
        f.write("""\
  if (length == %d && memcmp("%s", data, %d) == 0) {
    return %s;
  }
""" % (len(abbrev), abbrev, len(abbrev), name))
    f.write("""\
  return NO_SIGNAL;
}
""")


def main(argv):
    try:
        action = argv[1]
    except IndexError:
        raise RuntimeError('Action required')

    if action == 'cpp':
        out_prefix = argv[2]

        with open(out_prefix + '.h', 'w') as f:
            f.write("""\
#ifndef FRONTEND_SIGNAL_H
#define FRONTEND_SIGNAL_H

#include "mycpp/runtime.h"

namespace signal_def {

const int NO_SIGNAL = -1;

int MaxSigNumber();

int GetNumber(BigStr* sig_spec);

BigStr* GetName(int sig_num);

}  // namespace signal_def

#endif  // FRONTEND_SIGNAL_H
""")

        with open(out_prefix + '.cc', 'w') as f:
            f.write("""\
#include "signal.h"

#include <signal.h>  // SIG*
#include <stdio.h>  // printf

namespace signal_def {

int MaxSigNumber() {
  return %d;
}

""" % signal_def._MAX_SIG_NUMBER)

            CppGetNumber(f)
            f.write("\n")

            CppGetName(f)
            f.write("\n")

            f.write("""\

}  // namespace signal_def
""")


if __name__ == '__main__':
    try:
        main(sys.argv)
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
