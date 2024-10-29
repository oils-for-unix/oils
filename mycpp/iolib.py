"""
mylib.py: Python stubs/interfaces that are reimplemented in C++, not directly
translated.
"""
from __future__ import print_function

import signal

from typing import List, Any

UNTRAPPED_SIGWINCH = -1


class SignalSafe(object):
    """State that is shared between the main thread and signal handlers.

    See C++ implementation in cpp/core.h
    """

    def __init__(self):
        # type: () -> None
        self.pending_signals = []  # type: List[int]
        self.last_sig_num = 0  # type: int
        self.sigint_trapped = False
        self.received_sigint = False
        self.received_sigwinch = False
        self.sigwinch_code = UNTRAPPED_SIGWINCH

    def UpdateFromSignalHandler(self, sig_num, unused_frame):
        # type: (int, Any) -> None
        """Receive the given signal, and update shared state.

        This method is registered as a Python signal handler.
        """
        self.pending_signals.append(sig_num)

        if sig_num == signal.SIGINT:
            self.received_sigint = True

        if sig_num == signal.SIGWINCH:
            self.received_sigwinch = True
            sig_num = self.sigwinch_code  # mutate param

        self.last_sig_num = sig_num

    def LastSignal(self):
        # type: () -> int
        """Return the number of the last signal received."""
        return self.last_sig_num

    def PollSigInt(self):
        # type: () -> bool
        """Has SIGINT received since the last time PollSigInt() was called?"""
        result = self.received_sigint
        self.received_sigint = False
        return result

    def PollUntrappedSigInt(self):
        # type: () -> bool
        """Has SIGINT received since the last time PollSigInt() was called?"""
        received = self.PollSigInt()
        return received and not self.sigint_trapped

    if 0:

        def SigIntTrapped(self):
            # type: () -> bool
            return self.sigint_trapped

    def SetSigIntTrapped(self, b):
        # type: (bool) -> None
        """Set a flag to tell us whether sigint is trapped by the user."""
        self.sigint_trapped = b

    def SetSigWinchCode(self, code):
        # type: (int) -> None
        """Depending on whether or not SIGWINCH is trapped by a user, it is
        expected to report a different code to `wait`.

        SetSigWinchCode() lets us set which code is reported.
        """
        self.sigwinch_code = code

    def PollSigWinch(self):
        # type: () -> bool
        """Has SIGWINCH been received since the last time PollSigWinch() was
        called?"""
        result = self.received_sigwinch
        self.received_sigwinch = False
        return result

    def TakePendingSignals(self):
        # type: () -> List[int]
        """Transfer ownership of queue of pending signals to caller."""

        # A note on signal-safety here. The main loop might be calling this function
        # at the same time a signal is firing and appending to
        # `self.pending_signals`. We can forgoe using a lock here
        # (which would be problematic for the signal handler) because mutual
        # exclusivity should be maintained by the atomic nature of pointer
        # assignment (i.e. word-sized writes) on most modern platforms.
        # The replacement run list is allocated before the swap, so it can be
        # interrupted at any point without consequence.
        # This means the signal handler always has exclusive access to
        # `self.pending_signals`. In the worst case the signal handler might write to
        # `new_queue` and the corresponding trap handler won't get executed
        # until the main loop calls this function again.
        # NOTE: It's important to distinguish between signal-safety an
        # thread-safety here. Signals run in the same process context as the main
        # loop, while concurrent threads do not and would have to worry about
        # cache-coherence and instruction reordering.
        new_queue = []  #  type: List[int]
        ret = self.pending_signals
        self.pending_signals = new_queue
        return ret

    def ReuseEmptyList(self, empty_list):
        # type: (List[int]) -> None
        """This optimization only happens in C++."""
        pass


gSignalSafe = None  #  type: SignalSafe

gOrigSigIntHandler = None  # type: Any


def InitSignalSafe():
    # type: () -> SignalSafe
    """Set global instance so the signal handler can access it."""
    global gSignalSafe
    gSignalSafe = SignalSafe()

    # See
    # - demo/cpython/keyboard_interrupt.py
    # - pyos::InitSignalSafe()

    # In C++, we do
    # RegisterSignalInterest(signal.SIGINT)

    global gOrigSigIntHandler
    gOrigSigIntHandler = signal.signal(signal.SIGINT,
                                       gSignalSafe.UpdateFromSignalHandler)

    return gSignalSafe


def RegisterSignalInterest(sig_num):
    # type: (int) -> None
    """Have the kernel notify the main loop about the given signal."""
    #log('RegisterSignalInterest %d', sig_num)

    assert gSignalSafe is not None
    signal.signal(sig_num, gSignalSafe.UpdateFromSignalHandler)


def sigaction(sig_num, handler):
    # type: (int, Any) -> None
    """
    Handle a signal with SIG_DFL or SIG_IGN, not our own signal handler.
    """
    # SIGINT and SIGWINCH must be registered through SignalSafe
    assert sig_num != signal.SIGINT
    assert sig_num != signal.SIGWINCH
    signal.signal(sig_num, handler)
