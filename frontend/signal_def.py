#!/usr/bin/env python2
"""Signal_def.py."""
from __future__ import print_function

import signal

from typing import List, Dict, Tuple


def _MakeSignalsOld():
    # type: () -> Dict[str, int]
    """Piggy-back on CPython signal module.

    This causes portability problems
    """
    names = {}  # type: Dict[str, int]
    for name in dir(signal):
        # don't want SIG_DFL or SIG_IGN
        if name.startswith('SIG') and not name.startswith('SIG_'):
            int_val = getattr(signal, name)
            abbrev = name[3:]
            names[abbrev] = int_val
    return names


# POSIX 2018
# https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/signal.h.html

_PORTABLE_SIGNALS = [
    'SIGABRT',
    'SIGALRM',
    'SIGBUS',
    'SIGCHLD',
    'SIGCONT',
    'SIGFPE',
    'SIGHUP',
    'SIGILL',
    'SIGINT',
    #SIGKILL
    'SIGPIPE',
    'SIGQUIT',
    'SIGSEGV',
    'SIGSTOP',
    'SIGTERM',
    'SIGTSTP',
    'SIGTTIN',
    'SIGTTOU',
    'SIGUSR1',
    'SIGUSR2',
    'SIGSYS',
    'SIGTRAP',
    'SIGURG',
    'SIGVTALRM',
    'SIGXCPU',
    'SIGXFSZ',

    # Not part of POSIX, but essential for Oils to work
    'SIGWINCH',
]


def _MakeSignals():
    # type: () -> Dict[str, int]
    """Piggy-back on CPython signal module.

    This causes portability problems
    """
    names = {}  # type: Dict[str, int]
    for name in _PORTABLE_SIGNALS:
        int_val = getattr(signal, name)
        assert name.startswith('SIG'), name
        abbrev = name[3:]
        names[abbrev] = int_val
    return names


NO_SIGNAL = -1


def GetNumber(sig_spec):
    # type: (str) -> int
    return _SIGNAL_NAMES.get(sig_spec, NO_SIGNAL)


_SIGNAL_NAMES = _MakeSignals()

_BY_NUMBER = _SIGNAL_NAMES.items()
_BY_NUMBER.sort(key=lambda x: x[1])


def PrintSignals():
    # type: () -> None
    for name, int_val in _BY_NUMBER:
        print('%2d SIG%s' % (int_val, name))
