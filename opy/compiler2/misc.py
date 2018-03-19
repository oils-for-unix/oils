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
