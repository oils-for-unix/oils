#!/usr/bin/env python2
"""Osh_eval.py."""
from __future__ import print_function

import sys

from _devbuild.gen.syntax_asdl import CompoundWord
from core import error
from core import shell
from core import pyos
from core import pyutil
from core import ui
from frontend import args
from frontend import flag_def  # side effect: flags are defined!
from mycpp.mylib import print_stderr, log
from osh import builtin_misc

unused2 = flag_def

from typing import List, Dict


def main(argv):
    # type: (List[str]) -> int
    loader = pyutil.GetResourceLoader()

    # TODO: for a pure build, remove deps on osh/builtin_misc, and maybe
    # core/ui
    errfmt = ui.ErrorFormatter()
    topic_meta = None  # type: Dict[str, str]
    help_builtin = builtin_misc.Help(loader, topic_meta, errfmt)

    login_shell = False

    environ = pyos.Environ()

    missing = None  # type: CompoundWord
    arg_r = args.Reader(argv, [missing] * len(argv))

    try:
        status = shell.Main('osh', arg_r, environ, login_shell, loader,
                            help_builtin, None)
        return status
    except error.Usage as e:
        #builtin.Help(['oil-usage'], util.GetResourceLoader())
        log('oils: %s', e.msg)
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
        print_stderr('oils I/O error: %s' % pyutil.strerror(e))
        return 2  # dash gives status 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
