#!/usr/bin/env python2
"""
state_test.py: Tests for state.py
"""

import unittest
import os.path

from _devbuild.gen.runtime_asdl import (
    scope_e, lvalue, value, value_e, var_flags_e,
)
from core import error
from core import test_lib
from osh import state  # module under test


def _InitMem():
  # empty environment, no arena.
  arena = test_lib.MakeArena('<state_test.py>')
  line_id = arena.AddLine(1, 'foo')
  unused = arena.AddLineSpan(line_id, 0, 1)  # dummy
  return state.Mem('', [], {}, arena)


class MemTest(unittest.TestCase):

  def testGet(self):
    mem = _InitMem()
    mem.PushCall('my-func', 0, ['a', 'b'])
    print(mem.GetVar('HOME'))
    mem.PopCall()
    print(mem.GetVar('NONEXISTENT'))

  def testSearchPath(self):
    mem = _InitMem()
    #print(mem)
    search_path = state.SearchPath(mem)

    # Relative path works without $PATH
    self.assertEqual(None, search_path.Lookup('__nonexistent__'))
    self.assertEqual('bin/osh', search_path.Lookup('bin/osh'))
    self.assertEqual(None, search_path.Lookup('grep'))

    # Set $PATH
    mem.SetVar(lvalue.Named('PATH'), value.Str('/bin:/usr/bin'),
               (), scope_e.GlobalOnly)

    self.assertEqual(None, search_path.Lookup('__nonexistent__'))
    self.assertEqual('bin/osh', search_path.Lookup('bin/osh'))

    # Not hermetic, but should be true on POSIX systems.
    # Also see https://www.freedesktop.org/wiki/Software/systemd/TheCaseForTheUsrMerge/
    #  - on some systems, /bin is a symlink to /usr/bin
    if os.path.isfile('/bin/env'):
        self.assertEqual(search_path.Lookup('env'), '/bin/env')
    else:
        self.assertEqual(search_path.Lookup('env'), '/usr/bin/env')


  def testPushTemp(self):
    mem = _InitMem()

    # x=1
    mem.SetVar(
        lvalue.Named('x'), value.Str('1'), (), scope_e.Dynamic)
    self.assertEqual('1', mem.var_stack[-1]['x'].val.s)

    mem.PushTemp()

    self.assertEqual(2, len(mem.var_stack))

    # x=temp E=3 read x <<< 'line'
    mem.SetVar(
        lvalue.Named('x'), value.Str('temp'), (), scope_e.LocalOnly)
    mem.SetVar(
        lvalue.Named('E'), value.Str('3'), (), scope_e.LocalOnly)
    mem.SetVar(
        lvalue.Named('x'), value.Str('line'), (), scope_e.LocalOnly)

    self.assertEqual('3', mem.var_stack[-1]['E'].val.s)
    self.assertEqual('line', mem.var_stack[-1]['x'].val.s)
    self.assertEqual('1', mem.var_stack[-2]['x'].val.s)

    mem.PopTemp()
    self.assertEqual(1, len(mem.var_stack))
    self.assertEqual('1', mem.var_stack[-1]['x'].val.s)

  def testSetVarClearFlag(self):
    mem = _InitMem()
    print(mem)

    mem.PushCall('my-func', 0, ['ONE'])
    self.assertEqual(2, len(mem.var_stack))  # internal details

    # local x=y
    mem.SetVar(
        lvalue.Named('x'), value.Str('y'), (), scope_e.LocalOnly)
    self.assertEqual('y', mem.var_stack[-1]['x'].val.s)

    # New frame
    mem.PushCall('my-func', 0, ['TWO'])
    self.assertEqual(3, len(mem.var_stack))  # internal details

    # x=y -- test out dynamic scope
    mem.SetVar(
        lvalue.Named('x'), value.Str('YYY'), (), scope_e.Dynamic)
    self.assertEqual('YYY', mem.var_stack[-2]['x'].val.s)
    self.assertEqual(None, mem.var_stack[-1].get('x'))

    # myglobal=g
    mem.SetVar(
        lvalue.Named('myglobal'), value.Str('g'), (), scope_e.Dynamic)
    self.assertEqual('g', mem.var_stack[0]['myglobal'].val.s)
    self.assertEqual(False, mem.var_stack[0]['myglobal'].exported)

    # 'export PYTHONPATH=/'
    mem.SetVar(
        lvalue.Named('PYTHONPATH'), value.Str('/'),
        (var_flags_e.Exported,), scope_e.Dynamic)
    self.assertEqual('/', mem.var_stack[0]['PYTHONPATH'].val.s)
    self.assertEqual(True, mem.var_stack[0]['PYTHONPATH'].exported)

    ex = mem.GetExported()
    self.assertEqual('/', ex['PYTHONPATH'])

    mem.SetVar(
        lvalue.Named('PYTHONPATH'), None, (var_flags_e.Exported,),
        scope_e.Dynamic)
    self.assertEqual(True, mem.var_stack[0]['PYTHONPATH'].exported)

    # 'export myglobal'.  None means don't touch it.  Undef would be confusing
    # because it might mean "unset", but we have a separated API for that.
    mem.SetVar(
        lvalue.Named('myglobal'), None, (var_flags_e.Exported,),
        scope_e.Dynamic)
    self.assertEqual(True, mem.var_stack[0]['myglobal'].exported)

    # export g2  -- define and export empty
    mem.SetVar(
        lvalue.Named('g2'), None, (var_flags_e.Exported,),
        scope_e.Dynamic)
    self.assertEqual(value_e.Undef, mem.var_stack[0]['g2'].val.tag)
    self.assertEqual(True, mem.var_stack[0]['g2'].exported)

    # readonly myglobal
    self.assertEqual(False, mem.var_stack[0]['myglobal'].readonly)
    mem.SetVar(
        lvalue.Named('myglobal'), None, (var_flags_e.ReadOnly,),
        scope_e.Dynamic)
    self.assertEqual(True, mem.var_stack[0]['myglobal'].readonly)

    mem.SetVar(
        lvalue.Named('PYTHONPATH'), value.Str('/lib'), (),
        scope_e.Dynamic)
    self.assertEqual('/lib', mem.var_stack[0]['PYTHONPATH'].val.s)
    self.assertEqual(True, mem.var_stack[0]['PYTHONPATH'].exported)

    # COMPREPLY=(1 2 3)
    # invariant to enforce: arrays can't be exported
    mem.SetVar(
        lvalue.Named('COMPREPLY'), value.MaybeStrArray(['1', '2', '3']),
        (), scope_e.GlobalOnly)
    self.assertEqual(
        ['1', '2', '3'], mem.var_stack[0]['COMPREPLY'].val.strs)

    # export COMPREPLY
    try:
      mem.SetVar(
          lvalue.Named('COMPREPLY'), None, (var_flags_e.Exported,),
          scope_e.Dynamic)
    except error.FatalRuntime as e:
      pass
    else:
      self.fail("Expected failure")

    # readonly r=1
    mem.SetVar(
        lvalue.Named('r'), value.Str('1'), (var_flags_e.ReadOnly,),
        scope_e.Dynamic)
    self.assertEqual('1', mem.var_stack[0]['r'].val.s)
    self.assertEqual(False, mem.var_stack[0]['r'].exported)
    self.assertEqual(True, mem.var_stack[0]['r'].readonly)
    print(mem)

    # r=newvalue
    try:
      mem.SetVar(
          lvalue.Named('r'), value.Str('newvalue'), (), scope_e.Dynamic)
    except error.FatalRuntime as e:
      pass
    else:
      self.fail("Expected failure")

    # readonly r2  -- define empty readonly
    mem.SetVar(
        lvalue.Named('r2'), None, (var_flags_e.ReadOnly,),
        scope_e.Dynamic)
    self.assertEqual(value_e.Undef, mem.var_stack[0]['r2'].val.tag)
    self.assertEqual(True, mem.var_stack[0]['r2'].readonly)

    # export -n PYTHONPATH
    # Remove the exported property.  NOTE: scope is LocalOnly for Oil?
    self.assertEqual(True, mem.var_stack[0]['PYTHONPATH'].exported)
    mem.ClearFlag('PYTHONPATH', var_flags_e.Exported, scope_e.Dynamic)
    self.assertEqual(False, mem.var_stack[0]['PYTHONPATH'].exported)

    lhs = lvalue.Indexed('a', 1)
    lhs.spids.append(0)
    # a[1]=2
    mem.SetVar(lhs, value.Str('2'), (), scope_e.Dynamic)
    self.assertEqual([None, '2'], mem.var_stack[0]['a'].val.strs)

    # a[1]=3
    mem.SetVar(lhs, value.Str('3'), (), scope_e.Dynamic)
    self.assertEqual([None, '3'], mem.var_stack[0]['a'].val.strs)

    # a[1]=(x y z)  # illegal but doesn't parse anyway
    if 0:
      try:
        mem.SetVar(lhs, value.MaybeStrArray(['x', 'y', 'z']), (), scope_e.Dynamic)
      except error.FatalRuntime as e:
        pass
      else:
        self.fail("Expected failure")

    # readonly a
    mem.SetVar(
        lvalue.Named('a'), None, (var_flags_e.ReadOnly,),
        scope_e.Dynamic)
    self.assertEqual(True, mem.var_stack[0]['a'].readonly)

    try:
      # a[1]=3
      mem.SetVar(lhs, value.Str('3'), (), scope_e.Dynamic)
    except error.FatalRuntime as e:
      pass
    else:
      self.fail("Expected failure")

  def testGetVar(self):
    mem = _InitMem()

    # readonly a=x
    mem.SetVar(
        lvalue.Named('a'), value.Str('x'), (var_flags_e.ReadOnly,),
        scope_e.Dynamic)

    val = mem.GetVar('a', scope_e.Dynamic)
    test_lib.AssertAsdlEqual(self, value.Str('x'), val)

    val = mem.GetVar('undef', scope_e.Dynamic)
    test_lib.AssertAsdlEqual(self, value.Undef(), val)

  def testExportThenAssign(self):
    """Regression Test"""
    mem = _InitMem()

    # export U
    mem.SetVar(
        lvalue.Named('U'), None, (var_flags_e.Exported,), scope_e.Dynamic)
    print(mem)

    # U=u
    mem.SetVar(
        lvalue.Named('U'), value.Str('u'), (), scope_e.Dynamic)
    print(mem)
    e = mem.GetExported()
    self.assertEqual('u', e['U'])

  def testUnset(self):
    mem = _InitMem()
    # unset a
    mem.Unset(lvalue.Named('a'), scope_e.Dynamic)

    return  # not implemented yet

    # unset a[1]
    mem.Unset(lvalue.Indexed('a', 1), scope_e.Dynamic)

  def testArgv(self):
    mem = _InitMem()
    mem.PushCall('my-func', 0, ['a', 'b'])
    self.assertEqual(['a', 'b'], mem.GetArgv())

    mem.PushCall('my-func', 0, ['x', 'y'])
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
