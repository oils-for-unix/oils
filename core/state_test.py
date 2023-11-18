#!/usr/bin/env python2
"""state_test.py: Tests for state.py."""

import unittest
import os.path

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import scope_e
from _devbuild.gen.syntax_asdl import source, SourceLine
from _devbuild.gen.value_asdl import (value, value_e, sh_lvalue)
from asdl import runtime
from core import error
from core import test_lib
from core import state  # module under test
from frontend import lexer
from frontend import location


def _InitMem():
    # empty environment, no arena.
    arena = test_lib.MakeArena('<state_test.py>')
    col = 0
    length = 1
    line_id = arena.AddLine(1, 'foo')
    arena.NewToken(-1, col, length, line_id, '')  # unused, could be NewToken()
    mem = state.Mem('', [], arena, [])

    parse_opts, exec_opts, mutable_opts = state.MakeOpts(mem, None)

    mem.exec_opts = exec_opts
    return mem


class MemTest(unittest.TestCase):

    def testGet(self):
        mem = _InitMem()

        tok_a = lexer.DummyToken(Id.Lit_Chars, 'a')
        tok_a.line = SourceLine(1, 'a b', source.Interactive)

        mem.PushCall('my-func', tok_a, ['a', 'b'])
        print(mem.GetValue('HOME'))
        mem.PopCall(True)
        print(mem.GetValue('NONEXISTENT'))

    def testSearchPath(self):
        mem = _InitMem()
        #print(mem)
        search_path = state.SearchPath(mem)

        # Relative path works without $PATH
        self.assertEqual(None, search_path.LookupOne('__nonexistent__'))
        self.assertEqual('bin/osh', search_path.LookupOne('bin/osh'))
        self.assertEqual(None, search_path.LookupOne('grep'))

        # Set $PATH
        mem.SetValue(location.LName('PATH'), value.Str('/bin:/usr/bin'),
                     scope_e.GlobalOnly)

        self.assertEqual(None, search_path.LookupOne('__nonexistent__'))
        self.assertEqual('bin/osh', search_path.LookupOne('bin/osh'))

        # Not hermetic, but should be true on POSIX systems.
        # Also see https://www.freedesktop.org/wiki/Software/systemd/TheCaseForTheUsrMerge/
        #  - on some systems, /bin is a symlink to /usr/bin
        if os.path.isfile('/bin/env'):
            self.assertEqual(search_path.LookupOne('env'), '/bin/env')
        else:
            self.assertEqual(search_path.LookupOne('env'), '/usr/bin/env')

    def testPushTemp(self):
        mem = _InitMem()

        # x=1
        mem.SetValue(location.LName('x'), value.Str('1'), scope_e.Dynamic)
        self.assertEqual('1', mem.var_stack[-1]['x'].val.s)

        mem.PushTemp()

        self.assertEqual(2, len(mem.var_stack))

        # x=temp E=3 read x <<< 'line'
        mem.SetValue(location.LName('x'), value.Str('temp'), scope_e.LocalOnly)
        mem.SetValue(location.LName('E'), value.Str('3'), scope_e.LocalOnly)
        mem.SetValue(location.LName('x'), value.Str('line'), scope_e.LocalOnly)

        self.assertEqual('3', mem.var_stack[-1]['E'].val.s)
        self.assertEqual('line', mem.var_stack[-1]['x'].val.s)
        self.assertEqual('1', mem.var_stack[-2]['x'].val.s)

        mem.PopTemp()
        self.assertEqual(1, len(mem.var_stack))
        self.assertEqual('1', mem.var_stack[-1]['x'].val.s)

    def testSetVarClearFlag(self):
        mem = _InitMem()
        print(mem)

        tok_one = lexer.DummyToken(Id.Lit_Chars, 'ONE')
        tok_one.line = SourceLine(1, 'ONE', source.Interactive)

        tok_two = lexer.DummyToken(Id.Lit_Chars, 'TWO')
        tok_two.line = SourceLine(1, 'TWO', source.Interactive)

        mem.PushCall('my-func', tok_one, ['ONE'])
        self.assertEqual(2, len(mem.var_stack))  # internal details

        # local x=y
        mem.SetValue(location.LName('x'), value.Str('y'), scope_e.LocalOnly)
        self.assertEqual('y', mem.var_stack[-1]['x'].val.s)

        # New frame
        mem.PushCall('my-func', tok_two, ['TWO'])
        self.assertEqual(3, len(mem.var_stack))  # internal details

        # x=y -- test out dynamic scope
        mem.SetValue(location.LName('x'), value.Str('YYY'), scope_e.Dynamic)
        self.assertEqual('YYY', mem.var_stack[-2]['x'].val.s)
        self.assertEqual(None, mem.var_stack[-1].get('x'))

        # myglobal=g
        mem.SetValue(location.LName('myglobal'), value.Str('g'),
                     scope_e.Dynamic)
        self.assertEqual('g', mem.var_stack[0]['myglobal'].val.s)
        self.assertEqual(False, mem.var_stack[0]['myglobal'].exported)

        # 'export PYTHONPATH=/'
        mem.SetValue(location.LName('PYTHONPATH'),
                     value.Str('/'),
                     scope_e.Dynamic,
                     flags=state.SetExport)
        self.assertEqual('/', mem.var_stack[0]['PYTHONPATH'].val.s)
        self.assertEqual(True, mem.var_stack[0]['PYTHONPATH'].exported)

        cmd_ev = mem.GetExported()
        self.assertEqual('/', cmd_ev['PYTHONPATH'])

        mem.SetValue(location.LName('PYTHONPATH'),
                     None,
                     scope_e.Dynamic,
                     flags=state.SetExport)
        self.assertEqual(True, mem.var_stack[0]['PYTHONPATH'].exported)

        # 'export myglobal'.  None means don't touch it.  Undef would be confusing
        # because it might mean "unset", but we have a separated API for that.
        mem.SetValue(location.LName('myglobal'),
                     None,
                     scope_e.Dynamic,
                     flags=state.SetExport)
        self.assertEqual(True, mem.var_stack[0]['myglobal'].exported)

        # export g2  -- define and export empty
        mem.SetValue(location.LName('g2'),
                     None,
                     scope_e.Dynamic,
                     flags=state.SetExport)
        self.assertEqual(value_e.Undef, mem.var_stack[0]['g2'].val.tag())
        self.assertEqual(True, mem.var_stack[0]['g2'].exported)

        # readonly myglobal
        self.assertEqual(False, mem.var_stack[0]['myglobal'].readonly)
        mem.SetValue(location.LName('myglobal'),
                     None,
                     scope_e.Dynamic,
                     flags=state.SetReadOnly)
        self.assertEqual(True, mem.var_stack[0]['myglobal'].readonly)

        mem.SetValue(location.LName('PYTHONPATH'), value.Str('/lib'),
                     scope_e.Dynamic)
        self.assertEqual('/lib', mem.var_stack[0]['PYTHONPATH'].val.s)
        self.assertEqual(True, mem.var_stack[0]['PYTHONPATH'].exported)

        # COMPREPLY=(1 2 3)
        # invariant to enforce: arrays can't be exported
        mem.SetValue(location.LName('COMPREPLY'),
                     value.BashArray(['1', '2', '3']), scope_e.GlobalOnly)
        self.assertEqual(['1', '2', '3'],
                         mem.var_stack[0]['COMPREPLY'].val.strs)

        # export COMPREPLY
        try:
            mem.SetValue(location.LName('COMPREPLY'),
                         None,
                         scope_e.Dynamic,
                         flags=state.SetExport)
        except error.FatalRuntime as e:
            pass
        else:
            self.fail("Expected failure")

        # readonly r=1
        mem.SetValue(location.LName('r'),
                     value.Str('1'),
                     scope_e.Dynamic,
                     flags=state.SetReadOnly)
        self.assertEqual('1', mem.var_stack[0]['r'].val.s)
        self.assertEqual(False, mem.var_stack[0]['r'].exported)
        self.assertEqual(True, mem.var_stack[0]['r'].readonly)
        print(mem)

        # r=newvalue
        try:
            mem.SetValue(location.LName('r'), value.Str('newvalue'),
                         scope_e.Dynamic)
        except error.FatalRuntime as e:
            pass
        else:
            self.fail("Expected failure")

        # readonly r2  -- define empty readonly
        mem.SetValue(location.LName('r2'),
                     None,
                     scope_e.Dynamic,
                     flags=state.SetReadOnly)
        self.assertEqual(value_e.Undef, mem.var_stack[0]['r2'].val.tag())
        self.assertEqual(True, mem.var_stack[0]['r2'].readonly)

        # export -n PYTHONPATH
        # Remove the exported property.  NOTE: scope is LocalOnly for Oil?
        self.assertEqual(True, mem.var_stack[0]['PYTHONPATH'].exported)
        mem.ClearFlag('PYTHONPATH', state.ClearExport)
        self.assertEqual(False, mem.var_stack[0]['PYTHONPATH'].exported)

        lhs = sh_lvalue.Indexed('a', 1, runtime.NO_SPID)
        # a[1]=2
        mem.SetValue(lhs, value.Str('2'), scope_e.Dynamic)
        self.assertEqual([None, '2'], mem.var_stack[0]['a'].val.strs)

        # a[1]=3
        mem.SetValue(lhs, value.Str('3'), scope_e.Dynamic)
        self.assertEqual([None, '3'], mem.var_stack[0]['a'].val.strs)

        # a[1]=(x y z)  # illegal but doesn't parse anyway
        if 0:
            try:
                mem.SetValue(lhs, value.BashArray(['x', 'y', 'z']),
                             scope_e.Dynamic)
            except error.FatalRuntime as e:
                pass
            else:
                self.fail("Expected failure")

        # readonly a
        mem.SetValue(location.LName('a'),
                     None,
                     scope_e.Dynamic,
                     flags=state.SetReadOnly)
        self.assertEqual(True, mem.var_stack[0]['a'].readonly)

        try:
            # a[1]=3
            mem.SetValue(lhs, value.Str('3'), scope_e.Dynamic)
        except error.FatalRuntime as e:
            pass
        else:
            self.fail("Expected failure")

    def testGetValue(self):
        mem = _InitMem()

        # readonly a=x
        mem.SetValue(location.LName('a'),
                     value.Str('x'),
                     scope_e.Dynamic,
                     flags=state.SetReadOnly)

        val = mem.GetValue('a', scope_e.Dynamic)
        test_lib.AssertAsdlEqual(self, value.Str('x'), val)

        val = mem.GetValue('undef', scope_e.Dynamic)
        test_lib.AssertAsdlEqual(self, value.Undef, val)

    def testExportThenAssign(self):
        """Regression Test."""
        mem = _InitMem()

        # export U
        mem.SetValue(location.LName('U'),
                     None,
                     scope_e.Dynamic,
                     flags=state.SetExport)
        print(mem)

        # U=u
        mem.SetValue(location.LName('U'), value.Str('u'), scope_e.Dynamic)
        print(mem)
        e = mem.GetExported()
        self.assertEqual('u', e['U'])

    def testUnset(self):
        mem = _InitMem()
        # unset a
        mem.Unset(location.LName('a'), scope_e.Shopt)

        return  # not implemented yet

        # unset a[1]
        mem.Unset(sh_lvalue.Indexed('a', 1, runtime.NO_SPID), False)

    def testArgv(self):
        mem = _InitMem()
        src = source.Interactive

        tok_a = lexer.DummyToken(Id.Lit_Chars, 'a')
        tok_a.line = SourceLine(1, 'a b', src)

        mem.PushCall('my-func', tok_a, ['a', 'b'])
        self.assertEqual(['a', 'b'], mem.GetArgv())

        tok_x = lexer.DummyToken(Id.Lit_Chars, 'x')
        tok_x.line = SourceLine(2, 'x y', src)

        mem.PushCall('my-func', tok_x, ['x', 'y'])
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

        mem.PopCall(True)
        self.assertEqual(['a', 'b'], mem.GetArgv())

    def testArgv2(self):
        mem = state.Mem('', ['x', 'y'], None, [])

        mem.Shift(1)
        self.assertEqual(['y'], mem.GetArgv())

        mem.SetArgv(['i', 'j', 'k'])
        self.assertEqual(['i', 'j', 'k'], mem.GetArgv())


if __name__ == '__main__':
    unittest.main()
