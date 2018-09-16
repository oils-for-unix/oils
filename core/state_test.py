#!/usr/bin/env python
"""
state_test.py: Tests for state.py
"""

import unittest

from osh.meta import runtime
from core import state  # module under test
from core import util
from core import test_lib

scope_e = runtime.scope_e
value_e = runtime.value_e
var_flags_e = runtime.var_flags_e


def _InitMem():
  # empty environment, no arena.
  return state.Mem('', [], {}, None)


class MemTest(unittest.TestCase):

  def testGet(self):
    mem = _InitMem()
    mem.PushCall('my-func', ['a', 'b'])
    print(mem.GetVar('HOME'))
    mem.PopCall()
    print(mem.GetVar('NONEXISTENT'))

  def testPushTemp(self):
    mem = _InitMem()

    # x=1
    mem.SetVar(
        runtime.LhsName('x'), runtime.Str('1'), (), scope_e.Dynamic)
    self.assertEqual('1', mem.var_stack[-1].vars['x'].val.s)

    mem.PushTemp()

    self.assertEqual(2, len(mem.var_stack))

    # Temporary frame is readonly
    self.assertEqual(True, mem.var_stack[-1].readonly)
    self.assertEqual(False, mem.var_stack[-2].readonly)

    # x=temp E=3 read x <<< 'line'
    mem.SetVar(
        runtime.LhsName('x'), runtime.Str('temp'), (), scope_e.TempEnv)
    mem.SetVar(
        runtime.LhsName('E'), runtime.Str('3'), (), scope_e.TempEnv)
    mem.SetVar(
        runtime.LhsName('x'), runtime.Str('line'), (), scope_e.LocalOnly)

    self.assertEqual('3', mem.var_stack[-1].vars['E'].val.s)
    self.assertEqual('temp', mem.var_stack[-1].vars['x'].val.s)
    self.assertEqual('line', mem.var_stack[-2].vars['x'].val.s)

    mem.PopTemp()
    self.assertEqual(1, len(mem.var_stack))
    self.assertEqual('line', mem.var_stack[-1].vars['x'].val.s)

  def testSetVarClearFlag(self):
    mem = _InitMem()
    print(mem)

    mem.PushCall('my-func', ['ONE'])
    self.assertEqual(2, len(mem.var_stack))  # internal details

    # local x=y
    mem.SetVar(
        runtime.LhsName('x'), runtime.Str('y'), (), scope_e.LocalOnly)
    self.assertEqual('y', mem.var_stack[-1].vars['x'].val.s)

    # New frame
    mem.PushCall('my-func', ['TWO'])
    self.assertEqual(3, len(mem.var_stack))  # internal details

    # x=y -- test out dynamic scope
    mem.SetVar(
        runtime.LhsName('x'), runtime.Str('YYY'), (), scope_e.Dynamic)
    self.assertEqual('YYY', mem.var_stack[-2].vars['x'].val.s)
    self.assertEqual(None, mem.var_stack[-1].vars.get('x'))

    # myglobal=g
    mem.SetVar(
        runtime.LhsName('myglobal'), runtime.Str('g'), (), scope_e.Dynamic)
    self.assertEqual('g', mem.var_stack[0].vars['myglobal'].val.s)
    self.assertEqual(False, mem.var_stack[0].vars['myglobal'].exported)

    # 'export PYTHONPATH=/'
    mem.SetVar(
        runtime.LhsName('PYTHONPATH'), runtime.Str('/'),
        (var_flags_e.Exported,), scope_e.Dynamic)
    self.assertEqual('/', mem.var_stack[0].vars['PYTHONPATH'].val.s)
    self.assertEqual(True, mem.var_stack[0].vars['PYTHONPATH'].exported)

    self.assertEqual({'PYTHONPATH': '/'}, mem.GetExported())

    mem.SetVar(
        runtime.LhsName('PYTHONPATH'), None, (var_flags_e.Exported,),
        scope_e.Dynamic)
    self.assertEqual(True, mem.var_stack[0].vars['PYTHONPATH'].exported)

    # 'export myglobal'.  None means don't touch it.  Undef would be confusing
    # because it might mean "unset", but we have a separated API for that.
    mem.SetVar(
        runtime.LhsName('myglobal'), None, (var_flags_e.Exported,),
        scope_e.Dynamic)
    self.assertEqual(True, mem.var_stack[0].vars['myglobal'].exported)

    # export g2  -- define and export empty
    mem.SetVar(
        runtime.LhsName('g2'), None, (var_flags_e.Exported,),
        scope_e.Dynamic)
    self.assertEqual(value_e.Undef, mem.var_stack[0].vars['g2'].val.tag)
    self.assertEqual(True, mem.var_stack[0].vars['g2'].exported)

    # readonly myglobal
    self.assertEqual(False, mem.var_stack[0].vars['myglobal'].readonly)
    mem.SetVar(
        runtime.LhsName('myglobal'), None, (var_flags_e.ReadOnly,),
        scope_e.Dynamic)
    self.assertEqual(True, mem.var_stack[0].vars['myglobal'].readonly)

    mem.SetVar(
        runtime.LhsName('PYTHONPATH'), runtime.Str('/lib'), (),
        scope_e.Dynamic)
    self.assertEqual('/lib', mem.var_stack[0].vars['PYTHONPATH'].val.s)
    self.assertEqual(True, mem.var_stack[0].vars['PYTHONPATH'].exported)

    # COMPREPLY=(1 2 3)
    # invariant to enforce: arrays can't be exported
    mem.SetVar(
        runtime.LhsName('COMPREPLY'), runtime.StrArray(['1', '2', '3']),
        (), scope_e.GlobalOnly)
    self.assertEqual(
        ['1', '2', '3'], mem.var_stack[0].vars['COMPREPLY'].val.strs)

    # export COMPREPLY
    try:
      mem.SetVar(
          runtime.LhsName('COMPREPLY'), None, (var_flags_e.Exported,),
          scope_e.Dynamic)
    except util.FatalRuntimeError as e:
      pass
    else:
      self.fail("Expected failure")

    # readonly r=1
    mem.SetVar(
        runtime.LhsName('r'), runtime.Str('1'), (var_flags_e.ReadOnly,),
        scope_e.Dynamic)
    self.assertEqual('1', mem.var_stack[0].vars['r'].val.s)
    self.assertEqual(False, mem.var_stack[0].vars['r'].exported)
    self.assertEqual(True, mem.var_stack[0].vars['r'].readonly)
    print(mem)

    # r=newvalue
    try:
      mem.SetVar(
          runtime.LhsName('r'), runtime.Str('newvalue'), (), scope_e.Dynamic)
    except util.FatalRuntimeError as e:
      pass
    else:
      self.fail("Expected failure")

    # readonly r2  -- define empty readonly
    mem.SetVar(
        runtime.LhsName('r2'), None, (var_flags_e.ReadOnly,),
        scope_e.Dynamic)
    self.assertEqual(value_e.Undef, mem.var_stack[0].vars['r2'].val.tag)
    self.assertEqual(True, mem.var_stack[0].vars['r2'].readonly)

    # export -n PYTHONPATH
    # Remove the exported property.  NOTE: scope is LocalOnly for Oil?
    self.assertEqual(True, mem.var_stack[0].vars['PYTHONPATH'].exported)
    mem.ClearFlag('PYTHONPATH', var_flags_e.Exported, scope_e.Dynamic)
    self.assertEqual(False, mem.var_stack[0].vars['PYTHONPATH'].exported)

    lhs = runtime.LhsIndexedName('a', 1)
    lhs.spids.append(0)
    # a[1]=2
    mem.SetVar(lhs, runtime.Str('2'), (), scope_e.Dynamic)
    self.assertEqual([None, '2'], mem.var_stack[0].vars['a'].val.strs)

    # a[1]=3
    mem.SetVar(lhs, runtime.Str('3'), (), scope_e.Dynamic)
    self.assertEqual([None, '3'], mem.var_stack[0].vars['a'].val.strs)

    # a[1]=(x y z)  # illegal
    try:
      mem.SetVar(lhs, runtime.StrArray(['x', 'y', 'z']), (), scope_e.Dynamic)
    except util.FatalRuntimeError as e:
      pass
    else:
      self.fail("Expected failure")

    # readonly a
    mem.SetVar(
        runtime.LhsName('a'), None, (var_flags_e.ReadOnly,),
        scope_e.Dynamic)
    self.assertEqual(True, mem.var_stack[0].vars['a'].readonly)

    try:
      # a[1]=3
      mem.SetVar(lhs, runtime.Str('3'), (), scope_e.Dynamic)
    except util.FatalRuntimeError as e:
      pass
    else:
      self.fail("Expected failure")

  def testGetVar(self):
    mem = _InitMem()

    # readonly a=x
    mem.SetVar(
        runtime.LhsName('a'), runtime.Str('x'), (var_flags_e.ReadOnly,),
        scope_e.Dynamic)

    val = mem.GetVar('a', scope_e.Dynamic)
    test_lib.AssertAsdlEqual(self, runtime.Str('x'), val)

    val = mem.GetVar('undef', scope_e.Dynamic)
    test_lib.AssertAsdlEqual(self, runtime.Undef(), val)

  def testExportThenAssign(self):
    """Regression Test"""
    mem = _InitMem()

    # export U
    mem.SetVar(
        runtime.LhsName('U'), None, (var_flags_e.Exported,), scope_e.Dynamic)
    print(mem)

    # U=u
    mem.SetVar(
        runtime.LhsName('U'), runtime.Str('u'), (), scope_e.Dynamic)
    print(mem)
    e = mem.GetExported()
    self.assertEqual({'U': 'u'}, e)

  def testUnset(self):
    mem = _InitMem()
    # unset a
    mem.Unset(runtime.LhsName('a'), scope_e.Dynamic)

    return  # not implemented yet

    # unset a[1]
    mem.Unset(runtime.LhsIndexedName('a', 1), scope_e.Dynamic)

  def testArgv(self):
    mem = _InitMem()
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
    mem = state.Mem('', ['x', 'y'], {}, None)

    mem.Shift(1)
    self.assertEqual(['y'], mem.GetArgv())

    mem.SetArgv(['i', 'j', 'k'])
    self.assertEqual(['i', 'j', 'k'], mem.GetArgv())


if __name__ == '__main__':
  unittest.main()
