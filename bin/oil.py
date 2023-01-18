#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
oil.py - A busybox-like binary for OSH and Oil.

Based on argv[0], it acts like a few different programs.
- true, false
- readlink

Note: could also expose some other binaries for a smaller POSIX system?
- test / '['
- printf, echo
- cat
- seq
- 'time' -- has some different flags
"""
from __future__ import print_function

import posix_ as posix
import sys

# Needed for oil.ovm app bundle build, since there is an function-local import
# to break a circular build dep in frontend/consts.py.
from _devbuild.gen import id_kind
_ = id_kind

from bin import oils_cpp
from core import pyutil

from typing import List

# Called from Python-2.7.13/Modules/main.c.
def _cpython_main_hook():
  # type: () -> None
  sys.exit(oils_cpp.main(sys.argv))


def main(argv):
  # type: (List[str]) -> int
  return oils_cpp.main(sys.argv)


if __name__ == '__main__':
  if not pyutil.IsAppBundle():
    # For unmodified Python interpreters to simulate the OVM_MAIN patch
    import libc
    libc.cpython_reset_locale()

  pyann_out = posix.environ.get('PYANN_OUT')

  if pyann_out:
    from pyannotate_runtime import collect_types

    collect_types.init_types_collection()
    with collect_types.collect():
      status = main(sys.argv)
    collect_types.dump_stats(pyann_out)
    sys.exit(status)

  elif posix.environ.get('RESOLVE') == '1':
    from opy import resolve
    resolve.Walk(dict(sys.modules))

  elif posix.environ.get('CALLGRAPH') == '1':
    # NOTE: This could end up as opy.InferTypes(), opy.GenerateCode(), etc.
    from opy import callgraph
    callgraph.Walk(main, sys.modules)

  else:
    sys.exit(main(sys.argv))
