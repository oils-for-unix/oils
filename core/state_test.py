#!/usr/bin/env python
"""
state_test.py: Tests for state.py
"""

import unittest

from core import runtime
from core import state  # module under test
from core import util

# Hm this doesn't use scope_e or var_flags_e
scope = runtime.scope
value_e = runtime.value_e
var_flags = runtime.var_flags


class MemTest(unittest.TestCase):

  def testGet(self):
    mem = state.Mem('', [], {})
    mem.PushCall('my-func', ['a', 'b'])
    print(mem.GetVar('HOME'))
    mem.PopCall()
    print(mem.GetVar('NONEXISTENT'))

  def testSetVarClearFlag(self):
    mem = state.Mem('', [], {})
    print(mem)

    mem.PushCall('my-func', ['ONE'])
    self.assertEqual(2, len(mem.var_stack))  # internal details

    # local x=y
    mem.SetVar(
        runtime.LhsName('x'), runtime.Str('y'), (), scope.LocalOnly)
    self.assertEqual('y', mem.var_stack[-1]['x'].val.s)

    # New frame
    mem.PushCall('my-func', ['TWO'])
    self.assertEqual(3, len(mem.var_stack))  # internal details

    # x=y -- test out dynamic scope
    mem.SetVar(
        runtime.LhsName('x'), runtime.Str('YYY'), (), scope.Dynamic)
    self.assertEqual('YYY', mem.var_stack[-2]['x'].val.s)
    self.assertEqual(None, mem.var_stack[-1].get('x'))

    # myglobal=g
    mem.SetVar(
        runtime.LhsName('myglobal'), runtime.Str('g'), (), scope.Dynamic)
    self.assertEqual('g', mem.var_stack[0]['myglobal'].val.s)
    self.assertEqual(False, mem.var_stack[0]['myglobal'].exported)

    # 'export PYTHONPATH=/'
    mem.SetVar(
        runtime.LhsName('PYTHONPATH'), runtime.Str('/'), (var_flags.Exported,),
        scope.Dynamic)
    self.assertEqual('/', mem.var_stack[0]['PYTHONPATH'].val.s)
    self.assertEqual(True, mem.var_stack[0]['PYTHONPATH'].exported)

    self.assertEqual({'PYTHONPATH': '/'}, mem.GetExported())

    mem.SetVar(
        runtime.LhsName('PYTHONPATH'), None, (var_flags.Exported,),
        scope.Dynamic)
    self.assertEqual(True, mem.var_stack[0]['PYTHONPATH'].exported)

    # 'export myglobal'.  None means don't touch it.  Undef would be confusing
    # because it might mean "unset", but we have a separated API for that.
    mem.SetVar(
        runtime.LhsName('myglobal'), None, (var_flags.Exported,),
        scope.Dynamic)
    self.assertEqual(True, mem.var_stack[0]['myglobal'].exported)

    # export g2  -- define and export empty
    mem.SetVar(
        runtime.LhsName('g2'), None, (var_flags.Exported,),
        scope.Dynamic)
    self.assertEqual(value_e.Undef, mem.var_stack[0]['g2'].val.tag)
    self.assertEqual(True, mem.var_stack[0]['g2'].exported)

    # readonly myglobal
    self.assertEqual(False, mem.var_stack[0]['myglobal'].readonly)
    mem.SetVar(
        runtime.LhsName('myglobal'), None, (var_flags.ReadOnly,),
        scope.Dynamic)
    self.assertEqual(True, mem.var_stack[0]['myglobal'].readonly)

    mem.SetVar(
        runtime.LhsName('PYTHONPATH'), runtime.Str('/lib'), (),
        scope.Dynamic)
    self.assertEqual('/lib', mem.var_stack[0]['PYTHONPATH'].val.s)
    self.assertEqual(True, mem.var_stack[0]['PYTHONPATH'].exported)

    # COMPREPLY=(1 2 3)
    # invariant to enforce: arrays can't be exported
    mem.SetVar(
        runtime.LhsName('COMPREPLY'), runtime.StrArray(['1', '2', '3']),
        (), scope.GlobalOnly)
    self.assertEqual(['1', '2', '3'], mem.var_stack[0]['COMPREPLY'].val.strs)

    # export COMPREPLY
    try:
      mem.SetVar(
          runtime.LhsName('COMPREPLY'), None, (var_flags.Exported,),
          scope.Dynamic)
    except util.FatalRuntimeError as e:
      pass
    else:
      self.fail("Expected failure")

    # readonly r=1
    mem.SetVar(
        runtime.LhsName('r'), runtime.Str('1'), (var_flags.ReadOnly,),
        scope.Dynamic)
    self.assertEqual('1', mem.var_stack[0]['r'].val.s)
    self.assertEqual(False, mem.var_stack[0]['r'].exported)
    self.assertEqual(True, mem.var_stack[0]['r'].readonly)
    print(mem)

    # r=newvalue
    try:
      mem.SetVar(
          runtime.LhsName('r'), runtime.Str('newvalue'), (), scope.Dynamic)
    except util.FatalRuntimeError as e:
      pass
    else:
      self.fail("Expected failure")

    # readonly r2  -- define empty readonly
    mem.SetVar(
        runtime.LhsName('r2'), None, (var_flags.ReadOnly,),
        scope.Dynamic)
    self.assertEqual(value_e.Undef, mem.var_stack[0]['r2'].val.tag)
    self.assertEqual(True, mem.var_stack[0]['r2'].readonly)

    # export -n PYTHONPATH
    # Remove the exported property.  NOTE: scope is LocalOnly for Oil?
    self.assertEqual(True, mem.var_stack[0]['PYTHONPATH'].exported)
    mem.ClearFlag('PYTHONPATH', var_flags.Exported, scope.Dynamic)
    self.assertEqual(False, mem.var_stack[0]['PYTHONPATH'].exported)

    # a[2]=2
    mem.SetVar(
        runtime.LhsIndexedName('a', 1), runtime.Str('2'), (),
        scope.Dynamic)
    self.assertEqual(['', '2'], mem.var_stack[0]['a'].val.strs)

    # a[2]=3
    mem.SetVar(
        runtime.LhsIndexedName('a', 1), runtime.Str('3'), (),
        scope.Dynamic)
    self.assertEqual(['', '3'], mem.var_stack[0]['a'].val.strs)

    # a[2]=(x y z)  # illegal
    try:
      mem.SetVar(
          runtime.LhsIndexedName('a', 1), runtime.StrArray(['x', 'y', 'z']), (),
          scope.Dynamic)
    except util.FatalRuntimeError as e:
      pass
    else:
      self.fail("Expected failure")

    # readonly a
    mem.SetVar(
        runtime.LhsName('a'), None, (var_flags.ReadOnly,),
        scope.Dynamic)
    self.assertEqual(True, mem.var_stack[0]['a'].readonly)

    try:
      # a[2]=3
      mem.SetVar(
          runtime.LhsIndexedName('a', 1), runtime.Str('3'), (),
          scope.Dynamic)
    except util.FatalRuntimeError as e:
      pass
    else:
      self.fail("Expected failure")

  def testGetVar(self):
    mem = state.Mem('', [], {})

    # readonly a=x
    mem.SetVar(
        runtime.LhsName('a'), runtime.Str('x'), (var_flags.ReadOnly,),
        scope.Dynamic)

    val = mem.GetVar('a', scope.Dynamic)
    self.assertEqual(runtime.Str('x'), val)

    val = mem.GetVar('undef', scope.Dynamic)
    self.assertEqual(runtime.Undef(), val)

  def testExportThenAssign(self):
    """Regression Test"""
    mem = state.Mem('', [], {})

    # export U
    mem.SetVar(
        runtime.LhsName('U'), None, (var_flags.Exported,), scope.Dynamic)
    print(mem)

    # U=u
    mem.SetVar(
        runtime.LhsName('U'), runtime.Str('u'), (), scope.Dynamic)
    print(mem)
    e = mem.GetExported()
    self.assertEqual({'U': 'u'}, e)

  def testUnset(self):
    mem = state.Mem('', [], {})
    # unset a
    mem.Unset(runtime.LhsName('a'), scope.Dynamic)

    return  # not implemented yet

    # unset a[1]
    mem.Unset(runtime.LhsIndexedName('a', 1), scope.Dynamic)

  def testArgv(self):
    mem = state.Mem('', [], {})
    mem.PushCall('my-func', ['a', 'b'])
    self.assertEqual(['a', 'b'], mem.GetArgv())

    mem.PushCall('my-func', ['x', 'y'])
    self.assertEqual(['x', 'y'], mem.GetArgv())

    status = mem.Shift(1)
    self.assertEqual(['y'], mem.GetArgv())
    self.assertEqual(0, status)

    status = mem.Shift(1)
    self.assertEqual([], mem.GetArgv())
    self.assertEqual(0, status)

    status = mem.Shift(1)
    self.assertEqual([], mem.GetArgv())
    self.assertEqual(1, status)  # error

    mem.PopCall()
    self.assertEqual(['a', 'b'], mem.GetArgv())

  def testArgv2(self):
    mem = state.Mem('', ['x', 'y'], {})

    mem.Shift(1)
    self.assertEqual(['y'], mem.GetArgv())

    mem.SetArgv(['i', 'j', 'k'])
    self.assertEqual(['i', 'j', 'k'], mem.GetArgv())


if __name__ == '__main__':
  unittest.main()
