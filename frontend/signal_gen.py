#!/usr/bin/env python2
"""Signal_gen.py."""
from __future__ import print_function

import sys

import signal_def


def CppPrintSignals(f):
    f.write("""
void PrintSignals() {
""")

    for abbrev, _ in signal_def._BY_NUMBER:
        name = "SIG%s" % (abbrev, )
        f.write("""\
#ifdef %s
  printf("%%2d %s\\n", %s);
#endif
""" % (name, name, name))

    f.write("}\n")


def CppGetNumber(f):
    f.write("""\
int GetNumber(BigStr* sig_spec) {
  int length = len(sig_spec);
  if (length == 0) {
    return NO_SIGNAL;
  }

  const char* data = sig_spec->data_;

""")
    for abbrev, _ in signal_def._BY_NUMBER:
        name = "SIG%s" % (abbrev, )
        f.write("""\
  if ((length == %d && memcmp("%s", data, %d) == 0) ||
      (length == %d && memcmp("%s", data, %d) == 0)) {
    return %s;
  }
""" % (len(name), name, len(name), len(abbrev), abbrev, len(abbrev), name))
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

void PrintSignals();

int GetNumber(BigStr* sig_spec);

}  // namespace signal_def

#endif  // FRONTEND_SIGNAL_H
""")

        with open(out_prefix + '.cc', 'w') as f:
            f.write("""\
#include "signal.h"

#include <signal.h>  // SIG*
#include <stdio.h>  // printf

namespace signal_def {

""")
            CppPrintSignals(f)
            f.write("\n")
            CppGetNumber(f)

            f.write("""\

}  // namespace signal_def
""")


if __name__ == '__main__':
    try:
        main(sys.argv)
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
