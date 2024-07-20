"""
os_path.py - Copy of code from Python's posixpath.py and genericpath.py.
"""

import posix_ as posix

from mycpp import mylib
from typing import Tuple, List

extsep = '.'
sep = '/'


def join(s1, s2):
  # type: (str, str) -> str
  """Join pathnames.

  Ignore the previous parts if a part is absolute.  Insert a '/' unless the
  first part is empty or already ends in '/'.

  Special case of os.path.join() which avoids varargs.
  """
  if s2.startswith('/') or len(s1) == 0:
    # absolute path
    return s2

  if s1.endswith('/'):
    return s1 + s2

  return '%s/%s' % (s1, s2)


if mylib.PYTHON:
  def rstrip_slashes(s):
    # type: (str) -> str
    """Helper for split() and dirname()."""

    # This is an awkward implementation from the Python stdlib, but we rewrite it
    # in C++.
    n = len(s)
    if n and s != '/'*n:
      s = s.rstrip('/')
    return s


# Split a path in head (everything up to the last '/') and tail (the
# rest).  If the path ends in '/', tail will be empty.  If there is no
# '/' in the path, head  will be empty.
# Trailing '/'es are stripped from head unless it is the root.

def split(p):
    # type: (str) -> Tuple[str, str]
    """Split a pathname.  Returns tuple "(head, tail)" where "tail" is
    everything after the final slash.  Either part may be empty."""
    i = p.rfind('/') + 1
    head = p[:i]
    tail = p[i:]
    head = rstrip_slashes(head)
    return head, tail


# Split a path in root and extension.
# The extension is everything starting at the last dot in the last
# pathname component; the root is everything before that.
# It is always true that root + ext == p.

# Generic implementation of splitext, to be parametrized with
# the separators
def _splitext(p, sep, extsep):
    # type: (str, str, str) -> Tuple[str, str]
    """Split the extension from a pathname.

    Extension is everything from the last dot to the end, ignoring
    leading dots.  Returns "(root, ext)"; ext may be empty."""

    sepIndex = p.rfind(sep)
    dotIndex = p.rfind(extsep)
    if dotIndex > sepIndex:
        # skip all leading dots
        filenameIndex = sepIndex + 1
        while filenameIndex < dotIndex:
            if p[filenameIndex] != extsep:
                return p[:dotIndex], p[dotIndex:]
            filenameIndex += 1

    return p, ''


# Split a path in root and extension.
# The extension is everything starting at the last dot in the last
# pathname component; the root is everything before that.
# It is always true that root + ext == p.

def splitext(p):
    # type: (str) -> Tuple[str, str]
    return _splitext(p, sep, extsep)


# Return the tail (basename) part of a path, same as split(path)[1].

def basename(p):
    # type: (str) -> str
    """Returns the final component of a pathname"""
    i = p.rfind('/') + 1
    return p[i:]


# Return the head (dirname) part of a path, same as split(path)[0].

def dirname(p):
    # type: (str) -> str
    """Returns the directory component of a pathname"""
    i = p.rfind('/') + 1
    head = p[:i]
    head = rstrip_slashes(head)
    return head


# Normalize a path, e.g. A//B, A/./B and A/foo/../B all become A/B.
# It should be understood that this may change the meaning of the path
# if it contains symbolic links!

def normpath(path):
    # type: (str) -> str
    """Normalize path, eliminating double slashes, etc."""

    slash = '/'
    dot = '.'
    if path == '':
        return dot
    initial_slashes = path.startswith('/')  # type: int
    # POSIX allows one or two initial slashes, but treats three or more
    # as single slash.
    if (initial_slashes and
        path.startswith('//') and not path.startswith('///')):
        initial_slashes = 2
    comps = path.split('/')
    new_comps = []  # type: List[str]
    for comp in comps:
        if len(comp) == 0 or comp == '.':  # mycpp rewrite: comp in ('', '.')
            continue
        if (comp != '..' or (initial_slashes == 0 and len(new_comps) == 0) or
            (len(new_comps) and new_comps[-1] == '..')):
            new_comps.append(comp)
        elif len(new_comps):
            new_comps.pop()
    comps = new_comps
    path = slash.join(comps)
    if initial_slashes:
        path = slash*initial_slashes + path
    return path if len(path) else dot


# Return whether a path is absolute.
# Trivial in Posix, harder on the Mac or MS-DOS.

def isabs(s):
    # type: (str) -> bool
    """Test whether a path is absolute"""
    return s.startswith('/')


def abspath(path):
    # type: (str) -> str
    """Return an absolute path."""
    if not isabs(path):
        cwd = posix.getcwd()
        path = join(cwd, path)
    return normpath(path)
