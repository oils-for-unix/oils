"""
path_stat.py - Functions from os.path that import 'stat'.

We want to keep bin/osh_parse free of I/O.  It's a pure stdin/stdout filter.
"""
import posix
import stat


def exists(path):
    """Test whether a path exists.  Returns False for broken symbolic links"""
    try:
        posix.stat(path)
    except posix.error:
        return False
    return True


def isdir(s):
    """Return true if the pathname refers to an existing directory."""
    try:
        st = posix.stat(s)
    except posix.error:
        return False
    return stat.S_ISDIR(st.st_mode)
