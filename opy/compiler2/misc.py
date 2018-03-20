import os
import struct

# mangle() is used by both symbols and pycodegen.

MANGLE_LEN = 256  # magic constant from compile.c

def mangle(name, klass):
    if klass is None:  # nothing to mangle
        return name
    if not name.startswith('__'):  # not a private var
        return name

    if len(name) + 2 >= MANGLE_LEN:
        return name
    if name.endswith('__'):
        return name
    try:
        i = 0
        while klass[i] == '_':
            i = i + 1
    except IndexError:
        return name
    klass = klass[i:]

    tlen = len(klass) + len(name)
    if tlen > MANGLE_LEN:
        klass = klass[:MANGLE_LEN-tlen]

    return "_%s%s" % (klass, name)


PY27_MAGIC = b'\x03\xf3\r\n'  # removed host dep imp.get_magic()

def getPycHeader(filename):
    # compile.c uses marshal to write a long directly, with
    # calling the interface that would also generate a 1-byte code
    # to indicate the type of the value.  simplest way to get the
    # same effect is to call marshal and then skip the code.
    mtime = os.path.getmtime(filename)
    mtime = struct.pack('<i', int(mtime))

    # Update for Python 3:
    # https://nedbatchelder.com/blog/200804/the_structure_of_pyc_files.html
    # https://gist.github.com/anonymous/35c08092a6eb70cdd723

    return PY27_MAGIC + mtime
