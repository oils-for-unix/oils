#! /usr/bin/env python
from __future__ import print_function
"""inspect_pyc module

This is a refactor of a recipe from Ned Batchelder's blog.  He has
given me permission to publish this.  You can find the post at the
following URL:

  http://nedbatchelder.com/blog/200804/the_structure_of_pyc_files.html

You may use this module as a script: "./inspect_pyc.py <PYC_FILE>".

NOTE:
You can also see bytecode with:
import os, dis
dis.dis(os)

But that doesn't give all the metadata.  It's also nicer than
tools/dumppyc.py, which came with the 'compiler2' package.
"""

import cStringIO, dis, marshal, struct, sys, time, types
from ..compiler2 import consts


INDENT = '  '
MAX_HEX_LEN = 16
NAME_OFFSET = 20


def to_hexstr(bytes_value, level=0, wrap=False):
    indent = INDENT * level
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


# TODO: Do this in a cleaner way.  Right now I'm avoiding modifying the
# consts module.
def build_flags_def(consts, co_flags_def):
  for name in dir(consts): 
    if name.startswith('CO_'):
      co_flags_def[name] = getattr(consts, name)


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


def unpack_pyc(f):
    magic = f.read(4)
    unixtime = struct.unpack("I", f.read(4))[0]
    timestamp = time.asctime(time.localtime(unixtime))
    code = marshal.load(f)
    return magic, unixtime, timestamp, code


# NOTE:
# - We could change this into a bytecode visitor.  It's a tree of code
# objects.  Each code object contains constants, and a constant can be another
# code object.

# Enhancements:
# - Actually print the line of code!  That will be very helpful.
# - Print a histogram of byte codes.  Print toal number of bytecodes.
#   - Copy of the

def disassemble(co, indent, f):
  """Copied from dis module.

  It doesn't do the indent we want.
  """
  def ind(*args, **kwargs):
    print(indent, end='')
    print(*args, file=f, **kwargs)

  def out(*args, **kwargs):
    print(*args, file=f, **kwargs)

  code = co.co_code
  labels = dis.findlabels(code)
  linestarts = dict(dis.findlinestarts(co))
  n = len(code)
  i = 0
  extended_arg = 0
  free = None

  while i < n:
      c = code[i]
      op = ord(c)
      if i in linestarts:
          if i > 0:
              out()
          ind("%3d" % linestarts[i], end=' ')
      else:
          ind('   ', end=' ')

      out('   ', end=' ')
      if i in labels:  # Jump targets get a special symbol
        out('>>', end=' ')
      else:
        out('  ', end=' ')

      out(repr(i).rjust(4), end=' ')
      out(dis.opname[op].ljust(20), end=' ')
      i += 1
      if op >= dis.HAVE_ARGUMENT:
          oparg = ord(code[i]) + ord(code[i+1])*256 + extended_arg
          extended_arg = 0
          i += 2
          if op == dis.EXTENDED_ARG:
              extended_arg = oparg*65536L

          out(repr(oparg).rjust(5), end=' ')
          if op in dis.hasconst:
              out('(' + repr(co.co_consts[oparg]) + ')', end=' ')
          elif op in dis.hasname:
              out('(' + co.co_names[oparg] + ')', end=' ')
          elif op in dis.hasjrel:
              out('(to ' + repr(i + oparg) + ')', end=' ')
          elif op in dis.haslocal:
              out('(' + co.co_varnames[oparg] + ')', end=' ')
          elif op in dis.hascompare:
              out('(' + dis.cmp_op[oparg] + ')', end=' ')
          elif op in dis.hasfree:
              if free is None:
                  free = co.co_cellvars + co.co_freevars
              out('(' + free[oparg] + ')', end=' ')
      out()


class Visitor(object):

  def __init__(self, dis_bytecode=True):
    self.dis_bytecode = dis_bytecode  # Whether to show disassembly.

  def show_consts(self, consts, level=0):
    indent = INDENT * level
    i = 0
    for obj in consts:
      if isinstance(obj, types.CodeType):
        print(indent+"%s (code object)" % i)
        # RECURSIVE CALL.
        self.show_code(obj, level=level+1)
      else:
        print(indent+"%s %r" % (i, obj))
      i += 1

  def show_bytecode(self, code, level=0):
    """Call dis.disassemble() to show bytecode."""

    indent = INDENT * level
    print(to_hexstr(code.co_code, level, wrap=True))

    if self.dis_bytecode:
      print(indent + "disassembled:")
      disassemble(code, indent, sys.stdout)

  def show_code(self, code, level=0):
    """Print a code object, e.g. metadata, bytecode, and consts."""

    indent = INDENT * level

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
    self.show_consts(code.co_consts, level=level+1)

    print("%sco_code" % indent)
    self.show_bytecode(code, level=level+1)

  def Visit(self, f):
    """Write a readable listing of a .pyc file to stdout."""

    magic, unixtime, timestamp, code = unpack_pyc(f)

    magic = "0x(%s)" % to_hexstr(magic)
    print("  ## inspecting pyc file ##")
    print("magic number: %s" % magic)
    print("timestamp:    %s (%s)" % (unixtime, timestamp))
    print("code")
    self.show_code(code, level=1)
    print("  ## done inspecting pyc file ##")
