#!/usr/bin/env python2
"""
osh_eval.py
"""
from __future__ import print_function

import sys

from asdl import runtime
from core import error
from core import shell
from core.pyerror import log
from core import pyos
from core import pyutil
from frontend import args
from frontend import flag_def  # side effect: flags are defined!
from mycpp.mylib import print_stderr
unused2 = flag_def

from typing import List


def main(argv):
  # type: (List[str]) -> int
  loader = pyutil.GetResourceLoader()
  login_shell = False

  environ = pyos.Environ()

  arg_r = args.Reader(argv, spids=[runtime.NO_SPID] * len(argv))

  try:
    status = shell.Main('osh', arg_r, environ, login_shell, loader,
                               None)
    return status
  except error.Usage as e:
    #builtin.Help(['oil-usage'], util.GetResourceLoader())
    log('oil: %s', e.msg)
    return 2
  except RuntimeError as e:
    if 0:
      import traceback
      traceback.print_exc()
    # NOTE: The Python interpreter can cause this, e.g. on stack overflow.
    # f() { f; }; f will cause this
    msg = e.message  # type: str
    print_stderr('osh fatal error: %s' % msg)
    return 1

  # Note: This doesn't happen in C++.
  except KeyboardInterrupt:
    print('')
    return 130  # 128 + 2

  except (IOError, OSError) as e:
    if 0:
      import traceback
      traceback.print_exc()

    # test this with prlimit --nproc=1 --pid=$$
    print_stderr('osh I/O error: %s' % pyutil.strerror(e))
    return 2  # dash gives status 2


if __name__ == '__main__':
  sys.exit(main(sys.argv))
