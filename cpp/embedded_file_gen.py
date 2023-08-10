#!/usr/bin/env python2
from __future__ import print_function
"""
Generate C++ strings that can be used by pyutil._ResourceLoader

Used for 

- _devbuild/help/
- stdlib/
"""

import sys
from mycpp.mylib import log


def main(argv):
  paths = argv[1:]

  out_f = sys.stdout

  # Invoked with _devbuild/help/* stdlib/*.ysh 

  #log('paths %s', paths)

  out_f.write('''
#include "cpp/embedded_file.h"

namespace embedded_file {
''')

  # Write global strings
  for i, rel_path in enumerate(paths):
    with open(rel_path) as f:
      contents = f.read()

    # zZXx is a unique string that shouldn't appear in any file
    out_f.write('GLOBAL_STR(gStr%d, R"zZXx(%s)zZXx");\n\n' % (i, contents))

  out_f.write('''

TextFile array[] = {
''')

  # Write global array entries
  for i, rel_path in enumerate(paths):
    out_f.write('    {.rel_path = "%s", .contents = gStr%d},\n' % (rel_path, i))

  out_f.write('''
    {.rel_path = nullptr, .contents = nullptr},
};

}  // namespace embedded_file

TextFile* gEmbeddedFiles = embedded_file::array;  // turn array into pointer
''')


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)


# vim: sw=2
