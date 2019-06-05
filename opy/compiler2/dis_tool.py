#!/usr/bin/env python2
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

import marshal, struct, sys, time, types

import consts  # this package

from opy.lib import dis


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


def ShowFlags(flags):
  flag_names = []
  for bit in sorted(consts.VALUE_TO_NAME):
    if flags & bit:
      flag_names.append(consts.VALUE_TO_NAME[bit])

  h = "0x%05x" % flags
  if flag_names:
    return '%s %s' % (h, ' '.join(flag_names))
  else:
    return h


def unpack_pyc(f):
    magic = f.read(4)
    unixtime = struct.unpack("I", f.read(4))[0]
    timestamp = time.asctime(time.localtime(unixtime))
    code = marshal.load(f)
    return magic, unixtime, timestamp, code


# Enhancements:
# - Actually print the line of code!  That will be very helpful.

def disassemble(co, indent, f):
  """Copied from dis module.

  Args:
    co: code object
    indent: indentation to print with

  NOTE: byterun/pyobj.py:Frame.decode_next does something very similar.
  """
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
          prefix = linestarts[i]
      else:
          prefix = ''
      out('%s%4s' % (indent, prefix), end=' ')

      if i in labels:  # Jump targets get a special symbol
        arrow = '>>'
      else:
        arrow = '  '

      out(' %s %4r %-20s ' % (arrow, i, dis.opname[op]), end=' ')
      i += 1
      if op >= dis.HAVE_ARGUMENT:
          oparg = ord(code[i]) + ord(code[i+1])*256 + extended_arg
          extended_arg = 0
          i += 2
          if op == dis.EXTENDED_ARG:
              extended_arg = oparg*65536L

          oparg_str = None

          if op in dis.hasconst:
            c = co.co_consts[oparg]
            if isinstance(c, types.CodeType):
              # %r prints a memory address, which inhibits diffing
              oparg_str = '(code object %s %s %s)' % (
                  c.co_name, c.co_filename, c.co_firstlineno)
            else:
              oparg_str = '(%r)' % (c,)

          elif op in dis.hasname:
            oparg_str = '(%s)' % (co.co_names[oparg],)

          elif op in dis.hasjrel:
            oparg_str = '(to %r)' % (i + oparg,)

          elif op in dis.haslocal:
            oparg_str = '(%s)' % (co.co_varnames[oparg],)

          elif op in dis.hascompare:
            oparg_str = '(%s)' % (dis.cmp_op[oparg],)

          elif op in dis.hasfree:
            if free is None:
              free = co.co_cellvars + co.co_freevars
            oparg_str = '(%s)' % (free[oparg],)

          if oparg_str:
            out('%5r %s' % (oparg, oparg_str), end=' ')
          else:
            out('%5r' % oparg, end=' ')

      out()


def ParseOps(code):
  """A lightweight parser.  Does some of what disassemble() does.
  """
  n = len(code)
  i = 0
  extended_arg = 0

  while i < n:
      c = code[i]
      op = ord(c)

      i += 1
      if op >= dis.HAVE_ARGUMENT:
          oparg = ord(code[i]) + ord(code[i+1])*256 + extended_arg
          extended_arg = 0
          i += 2
          if op == dis.EXTENDED_ARG:
              extended_arg = oparg*65536L

      yield dis.opname[op], oparg


class Visitor(object):

  def __init__(self, dis_bytecode=True, co_name=None):
    """
    Args:
      dis_bytecode: Whether to show disassembly.
      co_name: only print code object with exact name (and its children)
    """
    self.dis_bytecode = dis_bytecode
    # Name of thing to print
    self.co_name = co_name

  def show_consts(self, consts, level=0):
    indent = INDENT * level
    for i, obj in enumerate(consts):
      if isinstance(obj, types.CodeType):
        print("%s%s (code object)" % (indent, i))
        # RECURSIVE CALL.
        self.show_code(obj, level=level+1)
      else:
        print("%s%s %r" % (indent, i, obj))

  def maybe_show_consts(self, consts, level=0):
    for obj in consts:
      if isinstance(obj, types.CodeType):
        self.show_code(obj, level=level+1)   # RECURSIVE CALL.

  def show_bytecode(self, code, level=0):
    """Call dis.disassemble() to show bytecode."""

    indent = INDENT * level
    print(to_hexstr(code.co_code, level, wrap=True))

    if self.dis_bytecode:
      print(indent + "disassembled:")
      disassemble(code, indent, sys.stdout)

  def show_code(self, code, level=0):
    """Print a code object, e.g. metadata, bytecode, and consts."""

    # Filter recursive call
    if self.co_name and code.co_name != self.co_name:
      self.maybe_show_consts(code.co_consts, level=level+1)
      return

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
        value = ShowFlags(value)
      elif name == "co_lnotab":
        value = "0x(%s)" % to_hexstr(value)
      print("%s%s%s" % (indent, (name+":").ljust(NAME_OFFSET), value))

    # Show bytecode FIRST, and then consts.  There is nested bytecode in the
    # consts, so it's a 'top-down' order.
    print("%sco_code" % indent)
    self.show_bytecode(code, level=level+1)

    print("%sco_consts" % indent)
    self.show_consts(code.co_consts, level=level+1)

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
