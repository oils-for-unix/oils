#! /usr/bin/env python
"""inspect_pyc module

This is a refactor of a recipe from Ned Batchelder's blog.  He has
given me permission to publish this.  You can find the post at the
following URL:

  http://nedbatchelder.com/blog/200804/the_structure_of_pyc_files.html

You may use this module as a script: "./inspect_pyc.py <PYC_FILE>".

"""

import dis, marshal, struct, sys, time, types, warnings
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


INDENT = " " * 3
MAX_HEX_LEN = 16
NAME_OFFSET = 20


def to_hexstr(bytes_value, level=0, wrap=False):
    indent = INDENT*level
    line = " ".join(("%02x",) * MAX_HEX_LEN)
    last = " ".join(("%02x",) * (len(bytes_value) % MAX_HEX_LEN))
    lines = (line,) * (len(bytes_value) // MAX_HEX_LEN)
    if last:
        lines += (last,)
    if wrap:
        template = indent + ("\n"+indent).join(lines)
    else:
        template = " ".join(lines)
    try:
        return template % tuple(bytes_value)
    except TypeError:
        return template % tuple(ord(char) for char in bytes_value)

def unpack_pyc(filename):
    f = open(filename, "rb")
    magic = f.read(4)
    unixtime = struct.unpack("I", f.read(4))[0]
    timestamp = time.asctime(time.localtime(unixtime))
    code = marshal.load(f)
    f.close()
    return filename, magic, unixtime, timestamp, code

def show_consts(consts, level=0):
    indent = INDENT*level
    i = 0
    for obj in consts:
        if isinstance(obj, types.CodeType):
            print(indent+"%s (code object)" % i)
            show_code(obj, level=level+1)
        else:
            print(indent+"%s %r" % (i, obj))
        i += 1

def show_bytecode(code, level=0):
    indent = INDENT*level
    print(to_hexstr(code.co_code, level, wrap=True))
    print(indent+"disassembled:")
    buffer = StringIO()
    sys.stdout = buffer
    # NOTE: This format has addresses in it, disable for now
    dis.disassemble(code)
    sys.stdout = sys.__stdout__
    print(indent + buffer.getvalue().replace("\n", "\n"+indent))


# TODO: Do this in a cleaner way.  Right now I'm avoiding modifying the
# consts module.
def build_flags_def(consts, co_flags_def):
  for name in dir(consts): 
    if name.startswith('CO_'):
      co_flags_def[name] = getattr(consts, name)

from compiler2 import consts
_CO_FLAGS_DEF = {}
build_flags_def(consts, _CO_FLAGS_DEF)

def show_flags(value):
    names = []
    for name, bit in _CO_FLAGS_DEF.items():
      if value & bit:
        names.append(name)

    h = "0x%05x" % value
    if names:
      return '%s %s' % (h, ' '.join(names))
    else:
      return h

def show_code(code, level=0):
    indent = INDENT*level

    for name in dir(code):
        if not name.startswith("co_"):
            continue
        if name in ("co_code", "co_consts"):
            continue
        value = getattr(code, name)
        if isinstance(value, str):
            value = repr(value)
        elif name == "co_flags":
            value = show_flags(value)
        elif name == "co_lnotab":
            value = "0x(%s)" % to_hexstr(value)
        print("%s%s%s" % (indent, (name+":").ljust(NAME_OFFSET), value))
    print("%sco_consts" % indent)
    show_consts(code.co_consts, level=level+1)
    print("%sco_code" % indent)
    show_bytecode(code, level=level+1)

def show_file(filename):
    filename, magic, unixtime, timestamp, code = unpack_pyc(filename)
    magic = "0x(%s)" % to_hexstr(magic)

    print("  ## inspecting pyc file ##")
    print("filename:     %s" % filename)
    print("magic number: %s" % magic)
    print("timestamp:    %s (%s)" % (unixtime, timestamp))
    print("code")
    show_code(code, level=1)
    print("  ## done inspecting pyc file ##")


if __name__ == "__main__":
    USAGE = "  usage: %s <PYC FILENAME>" % sys.argv[0]

    if len(sys.argv) == 1:
        sys.exit("Error: Too few arguments\n%s" % USAGE)
    if len(sys.argv) > 2:
        warnings.warn("Ignoring extra arguments: %s" % (sys.argv[2:],))

    if sys.argv[1] == "-h":
        print(USAGE)
    else:
        show_file(sys.argv[1])
