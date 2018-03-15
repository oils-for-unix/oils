#!/usr/bin/python
from __future__ import print_function
"""
callgraph.py
"""

import sys
import dis

import __builtin__  # For looking up names
#import exceptions  

from core import util
log = util.log


def Disassemble(co, of_interest):
  """Given a code object, yield instructions of interest.

  Args:
    co: __code__ attribute
    of_interest: names of opcodes that are interesting.

  Structure copied from misc/inspect_pyc.py, which was copied from
  dis.disassemble().
  """
  code = co.co_code
  extended_arg = 0  # Not used

  i = 0
  n = len(code)
  #log('\tLENGTH OF CODE %s: %d', co.co_name, n)

  while i < n:
    #log('\ti = %d, n = %d', i, n)
    op = ord(code[i])
    i += 1

    op_name = dis.opname[op]

    # operation is 1 byte, argument is 2 bytes.
    if op >= dis.HAVE_ARGUMENT:
      oparg = ord(code[i]) + ord(code[i+1])*256 + extended_arg
      extended_arg = 0

      if op == dis.EXTENDED_ARG:
        # Hm not used?
        raise AssertionError
        extended_arg = oparg*65536L

      i += 2

      const_name = None
      var_name = None

      if op_name not in of_interest:
        continue  # don't try to interpret the argument

      if op in dis.hasconst:
        const_name = co.co_consts[oparg]

      elif op in dis.hasname:
        try:
          var_name = co.co_names[oparg]
        except IndexError:
          log('Error: %r cannot index %s with %d', op_name, co.co_names,
              oparg)
          raise

      elif op in dis.hasjrel:
        raise AssertionError(op_name)

      elif op in dis.haslocal:
        raise AssertionError(op_name)

      elif op in dis.hascompare:
        raise AssertionError(op_name)

      elif op in dis.hasfree:
        raise AssertionError(op_name)

    yield op_name, const_name, var_name
    #log('\t==> i = %d, n = %d', i, n)


def _Walk(func, module, out):
  """
  Discover statically what (globally-accessible) functions and classes are
  used.

  Something like this is OK:

  def Adder(x):
    def f(y):
      return x + y
    return f

  Because we'll still have access to the inner code object.  We probably won't
  compile it though.
  """
  # Most functions and classes we call are globals!

  of_interest = ('LOAD_GLOBAL', 'LOAD_ATTR', 'CALL_FUNCTION')

  log('\t_Walk %s %s', func, module)

  #log('\t%s', sorted(dir(module)))

  # PROBLEM with this algorithm.  Need to analyze MODULES.  foo.Bar.
  # foo.Bar() is the common case!

  # Have to account for this sequence:
  # 2           0 LOAD_GLOBAL              0 (foo)
  #             3 LOAD_ATTR                1 (Bar)
  #             6 CALL_FUNCTION            0


  # TODO: Look for a sequence.  How to do that?
  # It probably breaks with stuff like foo.Bar(foo.Baz)
  # The you have two sequences for CALL_FUNCTION
  # You have to respect the nargs argument to CALL_FUNCTION.

  for op, const, var in Disassemble(func.__code__, of_interest):

    #log('\top %2d %s', j, op)

    if op == 'LOAD_GLOBAL':
      try:
        val = getattr(module, var)
      except AttributeError:
        # This could raise too
        val = getattr(__builtin__, var)

      if callable(val):
        print(val)
        if hasattr(val, '__code__'):  # Builtins don't have bytecode.
          out.append(val)
          log('\tNAME %s', val.__code__.co_name)
          log('\tNAMES %s', val.__code__.co_names)

          _Walk(val, sys.modules[val.__module__], out)   # Recursive call.

  log('\tDone _Walk %s %s', func, module)


def Walk(main, modules):
  """Given a function main, finds all functions it transitively calls.

  Uses heuristic bytecode analysis.  Limitations:

  - functions that are local variables might not work?  But this should work:

  if x > 0:
    f = GlobalFunc
  else:
    f = OtherGlobalFunc
  f()    # The LOAD_GLOBAL will be found.

  Args:
    main: function
    modules: Dict[str, module]

  Returns:
    TODO: callgraph?  Flat dict of all functions called?  Or edges?
  """
  out = []
  _Walk(main, modules['__main__'], out)
  print('---')
  for o in out:
    print(o)


def main(argv):
  from core import util
  out = []
  #_Walk(util.log, util, out)
  _Walk(util.ShowAppVersion, util, out)

  #_Walk(util.log, sys.modules['core.util'], out)
  print('---')
  for o in out:
    print(o)


if __name__ == '__main__':
  main(sys.argv)
