#!/usr/bin/env python2
from __future__ import print_function

import signal

from typing import Dict, Tuple, List

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
    # type: () -> List[Tuple[str, int]]
    """Piggy-back on CPython signal module.

    This causes portability problems
    """
    pairs = []  # type: List[Tuple[str, int]]
    for name in _PORTABLE_SIGNALS:
        int_val = getattr(signal, name)
        assert name.startswith('SIG'), name
        abbrev = name[3:]
        pairs.append((abbrev, int_val))

    pairs.sort(key=lambda x: x[1])
    return pairs


NO_SIGNAL = -1

_SIGNAL_LIST = _MakeSignals()

_SIGNAL_NAMES = {}  # type: Dict[str, int]
for name, int_val in _SIGNAL_LIST:
    _SIGNAL_NAMES[name] = int_val

_SIGNAL_NUMBERS = {}  # type: Dict[int, str]
for name, int_val in _SIGNAL_LIST:
    _SIGNAL_NUMBERS[int_val] = name

_MAX_SIG_NUMBER = max(int_val for _, int_val in _SIGNAL_LIST)


def MaxSigNumber():
    # type: () -> int
    """Iterate over xrange(n + 1)"""
    return _MAX_SIG_NUMBER


def GetNumber(sig_spec):
    # type: (str) -> int
    return _SIGNAL_NAMES.get(sig_spec, NO_SIGNAL)


def GetName(sig_num):
    # type: (int) -> str
    s = _SIGNAL_NUMBERS.get(sig_num)
    if s is None:
        return None
    return 'SIG' + s
