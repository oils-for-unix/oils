#!/usr/bin/env python2
"""
osh_eval.py
"""
from __future__ import print_function

import sys

from asdl import runtime
from core import error
from core import pure
from core.pyerror import log
from core import pyutil
from core.pyutil import stderr_line
from frontend import args
from frontend import flag_def  # side effect: flags are defined!
_ = flag_def


import posix_ as posix

from typing import List, Dict


def main(argv):
  # type: (List[str]) -> int
  loader = pyutil.GetResourceLoader()
  login_shell = False

  environ = {}  # type: Dict[str, str]
  environ['PWD'] = posix.getcwd()

  arg_r = args.Reader(argv, spids=[runtime.NO_SPID] * len(argv))

  try:
    status = pure.Main('osh', arg_r, environ, login_shell, loader, None)
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
    stderr_line('osh fatal error: %s', msg)
    return 1
  except KeyboardInterrupt:
    print('')
    return 130  # 128 + 2
  except OSError as e:
    if 0:
      import traceback
      traceback.print_exc()

    # test this with prlimit --nproc=1 --pid=$$
    stderr_line('osh I/O error: %s', pyutil.strerror_OS(e))
    return 2  # dash gives status 2

  except IOError as e:  # duplicate of above because CPython is inconsistent
    stderr_line('osh I/O error: %s', pyutil.strerror_IO(e))
    return 2


if __name__ == '__main__':
  sys.exit(main(sys.argv))
