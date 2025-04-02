"""
pyos.py -- Wrappers for the operating system.

Like py{error,util}.py, it won't be translated to C++.
"""
from __future__ import print_function

from errno import EINTR
import pwd
import resource
import select
import sys
import termios  # for read -n
import time

from mycpp import iolib
from mycpp import mops
from mycpp.mylib import log

import posix_ as posix
from posix_ import WUNTRACED

from typing import Optional, Tuple, List, Dict, cast, Any, TYPE_CHECKING
if TYPE_CHECKING:
    from core import error

_ = log

EOF_SENTINEL = 256  # bigger than any byte
NEWLINE_CH = 10  # ord('\n')


def FlushStdout():
    # type: () -> Optional[error.IOError_OSError]
    """Flush CPython buffers.

    Return error because we call this in a C++ destructor, and those can't
    throw exceptions.
    """
    err = None  # type: Optional[error.IOError_OSError]
    try:
        sys.stdout.flush()
    except (IOError, OSError) as e:
        err = e
    return err


def WaitPid(waitpid_options):
    # type: (int) -> Tuple[int, int]
    """
    Return value:
      pid is 0 if WNOHANG passed, and nothing has changed state
      status: value that can be parsed with WIFEXITED() etc.
    """
    try:
        # Notes:
        # - The arg -1 makes it like wait(), which waits for any process.
        # - WUNTRACED is necessary to get stopped jobs.  What about WCONTINUED?
        # - We don't retry on EINTR, because the 'wait' builtin should be
        #   interruptible.
        # - waitpid_options can be WNOHANG
        pid, status = posix.waitpid(-1, WUNTRACED | waitpid_options)
    except OSError as e:
        if e.errno == EINTR and iolib.gSignalSafe.PollUntrappedSigInt():
            raise KeyboardInterrupt()
        return -1, e.errno

    return pid, status


class ReadError(Exception):
    """Wraps errno returned by read().

    Used by 'read' and 'mapfile' builtins.
    """

    def __init__(self, err_num):
        # type: (int) -> None
        self.err_num = err_num


def Read(fd, n, chunks):
    # type: (int, int, List[str]) -> Tuple[int, int]
    """C-style wrapper around Python's posix.read() that uses return values
    instead of exceptions for errors.

    We will implement this directly in C++ and not use exceptions at all.

    It reads n bytes from the given file descriptor and appends it to chunks.

    Returns:
      (-1, errno) on failure
      (number of bytes read, 0) on success.  Where 0 bytes read indicates EOF.
    """
    try:
        chunk = posix.read(fd, n)
    except OSError as e:
        if e.errno == EINTR and iolib.gSignalSafe.PollUntrappedSigInt():
            raise KeyboardInterrupt()
        return -1, e.errno
    else:
        length = len(chunk)
        if length:
            chunks.append(chunk)
        return length, 0


def ReadByte(fd):
    # type: (int) -> Tuple[int, int]
    """Low-level interface that returns values rather than raising exceptions.

    Used by _ReadUntilDelim() and _ReadLineSlowly().

    Returns:
      failure: (-1, errno) on failure
      success: (ch integer value or EOF_SENTINEL, 0)
    """
    try:
        b = posix.read(fd, 1)
    except OSError as e:
        if e.errno == EINTR and iolib.gSignalSafe.PollUntrappedSigInt():
            raise KeyboardInterrupt()
        return -1, e.errno
    else:
        if len(b):
            return ord(b), 0
        else:
            return EOF_SENTINEL, 0


def Environ():
    # type: () -> Dict[str, str]
    return posix.environ


def Chdir(dest_dir):
    # type: (str) -> int
    """Returns 0 for success and nonzero errno for error."""
    try:
        posix.chdir(dest_dir)
    except OSError as e:
        return e.errno
    return 0


def GetMyHomeDir():
    # type: () -> Optional[str]
    """Get the user's home directory from the /etc/pyos.

    Used by $HOME initialization in osh/state.py.  Tilde expansion and
    readline initialization use mem.GetValue('HOME').
    """
    uid = posix.getuid()
    try:
        e = pwd.getpwuid(uid)
    except KeyError:
        return None

    return e.pw_dir


def GetHomeDir(user_name):
    # type: (str) -> Optional[str]
    """For ~otheruser/src.

    TODO: Should this be cached?
    """
    # http://linux.die.net/man/3/getpwnam
    try:
        e = pwd.getpwnam(user_name)
    except KeyError:
        return None

    return e.pw_dir


class PasswdEntry(object):

    def __init__(self, pw_name, uid, gid):
        # type: (str, int, int) -> None
        self.pw_name = pw_name
        self.pw_uid = uid
        self.pw_gid = gid


def GetAllUsers():
    # type: () -> List[PasswdEntry]
    users = [
        PasswdEntry(u.pw_name, u.pw_uid, u.pw_gid) for u in pwd.getpwall()
    ]
    return users


def GetUserName(uid):
    # type: (int) -> str
    try:
        e = pwd.getpwuid(uid)
    except KeyError:
        return "<ERROR: Couldn't determine user name for uid %d>" % uid
    else:
        return e.pw_name


def GetRLimit(res):
    # type: (int) -> Tuple[mops.BigInt, mops.BigInt]
    """
    Raises IOError
    """
    soft, hard = resource.getrlimit(res)
    return (mops.IntWiden(soft), mops.IntWiden(hard))


def SetRLimit(res, soft, hard):
    # type: (int, mops.BigInt, mops.BigInt) -> None
    """
    Raises IOError
    """
    resource.setrlimit(res, (soft.i, hard.i))


def Time():
    # type: () -> Tuple[float, float, float]
    t = time.time()  # calls gettimeofday() under the hood
    u = resource.getrusage(resource.RUSAGE_SELF)
    return t, u.ru_utime, u.ru_stime


def PrintTimes():
    # type: () -> None
    utime, stime, cutime, cstime, elapsed = posix.times()
    print("%dm%.3fs %dm%.3fs" %
          (utime / 60, utime % 60, stime / 60, stime % 60))
    print("%dm%.3fs %dm%.3fs" %
          (cutime / 60, cutime % 60, cstime / 60, cstime % 60))


# So builtin_misc.py doesn't depend on termios, which makes C++ translation
# easier
TERM_ICANON = termios.ICANON
TERM_ECHO = termios.ECHO


def PushTermAttrs(fd, mask):
    # type: (int, int) -> Tuple[int, Any]
    """Returns opaque type (void* in C++) to be reused in the PopTermAttrs()"""
    # https://docs.python.org/2/library/termios.html
    term_attrs = termios.tcgetattr(fd)

    # Flip the bits in one field, e.g. ICANON to disable canonical (buffered)
    # mode.
    orig_local_modes = cast(int, term_attrs[3])
    term_attrs[3] = orig_local_modes & mask

    termios.tcsetattr(fd, termios.TCSANOW, term_attrs)
    return orig_local_modes, term_attrs


def PopTermAttrs(fd, orig_local_modes, term_attrs):
    # type: (int, int, Any) -> None

    term_attrs[3] = orig_local_modes
    try:
        termios.tcsetattr(fd, termios.TCSANOW, term_attrs)
    except termios.error as e:
        # Superficial fix for issue #1001.  I'm not sure why we get errno.EIO,
        # but we can't really handle it here.  In C++ I guess we ignore the
        # error.
        pass


def OsType():
    # type: () -> str
    """Compute $OSTYPE variable."""
    return posix.uname()[0].lower()


def InputAvailable(fd):
    # type: (int) -> bool
    # similar to lib/sh/input_avail.c in bash
    # read, write, except
    r, _, _ = select.select([fd], [], [], 0)
    return len(r) != 0


def WaitForReading(fd_list):
    # type: (List[int]) -> List[int]
    # Get a list of fds and return fds which have available input
    # read, write, except
    r, _, _ = select.select(fd_list, [], [])
    return r


def MakeDirCacheKey(path):
    # type: (str) -> Tuple[str, int]
    """Returns a pair (path with last modified time) that can be used to cache
    directory accesses."""
    st = posix.stat(path)
    return (path, int(st.st_mtime))
