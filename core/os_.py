#!/usr/bin/python
"""
os_.py - Copy of code from Python's os module, which we don't want to include.
"""
from __future__ import print_function

import errno
import posix
import sys

from core import os_path

#
# From os.py
#

def execvpe(file, args, env):
    """execvpe(file, args, env)

    Execute the executable file (which is searched for along $PATH)
    with argument list args and environment env , replacing the
    current process.
    args may be a list or tuple of strings. """
    _execvpe(file, args, env)


def _execvpe(file, args, env=None):
    if env is not None:
        func = posix.execve
        argrest = (args, env)
    else:
        func = posix.execv
        argrest = (args,)
        env = posix.environ

    head, tail = os_path.split(file)
    if head:
        func(file, *argrest)
        return
    if 'PATH' in env:
        envpath = env['PATH']
    else:
        envpath = os_path.defpath
    PATH = envpath.split(os_path.pathsep)
    saved_exc = None
    saved_tb = None
    for dir in PATH:
        fullname = os_path.join(dir, file)
        try:
            func(fullname, *argrest)
        except posix.error as e:
            tb = sys.exc_info()[2]
            if (e.errno != errno.ENOENT and e.errno != errno.ENOTDIR
                and saved_exc is None):
                saved_exc = e
                saved_tb = tb

    # TODO: Don't use this archaic syntax?
    if saved_exc:
        raise posix.error, saved_exc, saved_tb
    raise posix.error, e, tb
