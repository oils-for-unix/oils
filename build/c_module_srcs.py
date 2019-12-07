#!/usr/bin/env python2
from __future__ import print_function
"""
c_module_srcs.py
"""

import os
import glob
import sys


def main(argv):
  manifest_path = argv[1]
  discovered = argv[2]

  manifest = {}
  with open(manifest_path) as f:
    for line in f:
      line = line.strip()
      mod_name, rel_path = line.split(None, 2)
      manifest[mod_name] = rel_path

  #print manifest
  with open(discovered) as f:
    for line in f:
      line = line.strip()
      mod_name, _ = line.split(None, 2)

      # Hard-coded special cases for now.

      if mod_name in ('libc', 'fastlex', 'line_input'):  # Our own modules
        # Relative to Python-2.7.13 dir
        print('../native/%s.c' % mod_name)

      elif mod_name == 'posix_':
        print('../native/posixmodule.c')

      elif mod_name == 'math':
        print('Modules/mathmodule.c')
        print('Modules/_math.c')

      # Hm OPy needs these for hashlib in 'opy dis-md5'.  OK fine.
      elif mod_name == '_md5':
        print('Modules/md5module.c')
        print('Modules/md5.c')
      elif mod_name == '_sha':
        print('Modules/shamodule.c')
      elif mod_name == '_sha256':
        print('Modules/sha256module.c')
      elif mod_name == '_sha512':
        print('Modules/sha512module.c')

      elif mod_name == '_io':
        # This data is in setup.py and Modules/Setup.dist.
        #_io -I$(srcdir)/Modules/_io _io/bufferedio.c _io/bytesio.c
        #    _io/fileio.c _io/iobase.c _io/_iomodule.c _io/stringio.c
        #    _io/textio.c
        print('Modules/_io/bufferedio.c')
        print('Modules/_io/bytesio.c')
        print('Modules/_io/fileio.c')
        print('Modules/_io/iobase.c')
        print('Modules/_io/_iomodule.c')
        print('Modules/_io/stringio.c')
        print('Modules/_io/textio.c')

      elif mod_name == 'yajl':
        # Not including headers
        globs = [
            'py-yajl/*.c',
            'py-yajl/yajl/src/*.c',
        ]
        paths = []
        for g in globs:
          paths.extend(glob.glob(g))
        for path in paths:
          # UNUSED file.  It's an optional layer on top.
          if os.path.basename(path) == 'yajl_tree.c':
            continue
          print('../' + path)

      else:
        print(manifest[mod_name])


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
