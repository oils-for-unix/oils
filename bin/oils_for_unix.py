#!/usr/bin/env python2
"""
oils_for_unix.py - A busybox-like binary for OSH and YSH (formerly Oil).

This is the main program that is translated to C++ by mycpp.

Based on argv[0], it acts like a few different programs.
- true, false
- readlink

We could could also expose some other binaries for a smaller POSIX system:

- test / '['
- printf, echo
- cat
- 'time' -- different usage
"""
from __future__ import print_function

import posix_ as posix
import sys

from _devbuild.gen.syntax_asdl import loc, CompoundWord
from core import error
from core import shell
from core import pyos
from core import pyutil
from core import util
from frontend import args
from frontend import py_readline
from mycpp import mylib
from mycpp.mylib import print_stderr, log
from pylib import os_path

if mylib.PYTHON:
    from tools import readlink

import fanos

from typing import List


def CaperDispatch():
    # type: () -> int
    log('Running Oil in ---caper mode')
    fd_out = []  # type: List[int]
    while True:
        try:
            msg = fanos.recv(0, fd_out)
        except ValueError as e:
            # TODO: recv() needs to detect EOF condition.  Should it return ''
            # like sys.stdin.readline(), or something else?
            # Should that be distinguished from '0:,' ?   with None perhaps?
            log('FANOS error: %s', e)
            fanos.send(1, 'ERROR %s' % e)
            continue

        log('msg = %r', msg)

        command, arg = mylib.split_once(msg, ' ')
        if command == 'GETPID':
            pass
        elif command == 'CHDIR':
            pass
        elif command == 'SETENV':
            pass
        elif command == 'MAIN':
            #argv = ['TODO']
            # I think we need to factor the oil.{py,ovm} condition out and call it like this:
            # MainDispatch(main_name, argv) or
            # MainDispatch(main_name, arg_r)
            pass

        # fanos.send(1, reply)

    return 0  # Does this fail?


# TODO: Hook up valid applets (including these) to completion
# APPLETS = ['osh', 'ysh', 'oil', 'readlink', 'true', 'false']


def AppBundleMain(argv):
    # type: (List[str]) -> int

    # NOTE: This has a side effect of deleting _OVM_* from the environment!
    loader = pyutil.GetResourceLoader()

    b = os_path.basename(argv[0])
    main_name, ext = os_path.splitext(b)

    missing = None  # type: CompoundWord
    arg_r = args.Reader(argv, locs=[missing] * len(argv))

    login_shell = False

    # Are we running the C++ bundle or the Python bundle directly, without a
    # symlink?
    if mylib.PYTHON:
        bundle = 'oils_for_unix'  # bin/oils_for_unix.py
    else:
        bundle = 'oils-for-unix'  # _bin/cxx-dbg/oils-for-unix

    # for legacy oil.ovm
    if main_name == bundle or (main_name == 'oil' and len(ext)):
        arg_r.Next()
        first_arg = arg_r.Peek()
        if first_arg is None:
            raise error.Usage('Missing required applet name.', loc.Missing)

        # Special flags to the top level binary: bin/oil.py --help, ---caper, etc.
        if first_arg in ('-h', '--help'):
            util.HelpFlag(loader, 'oils-usage', mylib.Stdout())
            return 0

        if first_arg in ('-V', '--version'):
            util.VersionFlag(loader, mylib.Stdout())
            return 0

        # This has THREE dashes since it isn't a normal flag
        if first_arg == '---caper':
            return CaperDispatch()

        applet = first_arg
    else:
        applet = main_name

        if applet.startswith('-'):
            login_shell = True
            applet = applet[1:]

    readline = py_readline.MaybeGetReadline()

    environ = pyos.Environ()

    if applet.startswith('ysh') or applet == 'oil':
        return shell.Main('ysh', arg_r, environ, login_shell, loader, readline)

    elif applet.startswith('osh') or applet.endswith(
            'sh'):  # sh, osh, bash imply OSH
        return shell.Main('osh', arg_r, environ, login_shell, loader, readline)

    # For testing latency
    elif applet == 'true':
        return 0
    elif applet == 'false':
        return 1
    elif applet == 'readlink':
        if mylib.PYTHON:
            # TODO: Move this to 'internal readlink' (issue #1013)
            main_argv = arg_r.Rest()
            return readlink.main(main_argv)
        else:
            print_stderr('readlink not translated')
            return 2

    else:
        raise error.Usage("Invalid applet %r" % applet, loc.Missing)


def main(argv):
    # type: (List[str]) -> int

    if mylib.PYTHON:
        if not pyutil.IsAppBundle():
            # For unmodified Python interpreters to simulate the OVM_MAIN patch
            import libc
            libc.cpython_reset_locale()

    try:
        return AppBundleMain(argv)

    except error.Usage as e:
        #builtin.Help(['oil-usage'], util.GetResourceLoader())
        log('oils: %s', e.msg)
        return 2

    except KeyboardInterrupt:
        # The interactive shell and the batch shell both handle
        # KeyboardInterrupt themselves.
        # This is a catch-all for --tool and so forth.
        print('')
        return 130  # 128 + 2

    except (IOError, OSError) as e:
        if 0:
            import traceback
            traceback.print_exc()

        # test this with prlimit --nproc=1 --pid=$$
        print_stderr('oils I/O error (main): %s' % posix.strerror(e.errno))

        # dash gives status 2.  Consider changing: it conflicts a bit with
        # usage errors.
        return 2

    # We don't catch RuntimeError (including AssertionError/NotImplementedError),
    # because those are simply bugs, and we want to see a Python stack trace.


if __name__ == '__main__':
    sys.exit(main(sys.argv))
