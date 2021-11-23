#!/usr/bin/env python2
"""
args_test.py: Tests for args.py
"""

import unittest

from _devbuild.gen.runtime_asdl import cmd_value
from asdl import runtime
from core import error
from frontend import flag_spec
from frontend import args  # module under test


def _MakeBuiltinArgv(argv):
  argv = [''] + argv  # add dummy since arg_vec includes argv[0]
  # no location info
  return cmd_value.Argv(argv, [runtime.NO_SPID] * len(argv))


def _MakeReader(argv):
  cmd_val = _MakeBuiltinArgv(argv)
  arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
  arg_r.Next()
  return arg_r


def _ParseCmdVal(spec, cmd_val):
  # type: (cmd_value__Argv) -> Tuple[args._Attributes, int]
  """For testing only
  """
  arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
  arg_r.Next()  # move past the builtin name
  return args.Parse(spec, arg_r), arg_r.i


class ArgsTest(unittest.TestCase):

  def testFlagSpecAndMore(self):
    s = flag_spec._FlagSpecAndMore()
    s.ShortFlag('-c', args.String)
    s.ShortFlag('-i', args.String)

    s.LongFlag('--help')
    s.LongFlag('--rcfile', args.String)

    s.LongFlag('--ast-format', ['text', 'html'])

    s.InitOptions()
    s.Option('e', 'errexit')
    s.Option('u', 'nounset')
    s.Option(None, 'pipefail')

    # don't parse args afterward
    arg_r = args.Reader(
        ['-c', 'echo hi', '-e', '-o', 'nounset', 'foo', '--help'])
    arg = args.ParseMore(s, arg_r)

    self.assertEqual(['foo', '--help'], arg_r.Rest())
    self.assertEqual('echo hi', arg.c)
    self.assertEqual(None, arg.help)
    self.assertEqual(None, arg.i)

    self.assertEqual(
        [('errexit', True), ('nounset', True)], arg.opt_changes)

    arg_r = args.Reader(['+e', '+o', 'nounset', '-o', 'pipefail', 'foo'])
    arg = args.ParseMore(s, arg_r)

    self.assertEqual(['foo'], arg_r.Rest())
    self.assertEqual(None, arg.i)
    self.assertEqual(
        [('errexit', False), ('nounset', False), ('pipefail', True)],
        arg.opt_changes)

    arg_r = args.Reader(['-c', 'echo hi', '--help', '--rcfile', 'bashrc'])
    arg = args.ParseMore(s, arg_r)
    self.assertEqual('echo hi', arg.c)
    self.assertEqual(True, arg.help)
    self.assertEqual('bashrc', arg.rcfile)

    # This is an odd syntax!
    arg_r = args.Reader(['-euo', 'pipefail'])
    arg = args.ParseMore(s, arg_r)
    self.assertEqual(
        [('errexit', True), ('nounset', True), ('pipefail', True)],
        arg.opt_changes)
    self.assertEqual(2, arg_r.i)

    # Even weirder!
    arg_r = args.Reader(['+oeu', 'pipefail'])
    arg = args.ParseMore(s, arg_r)
    self.assertEqual(
        [('pipefail', False), ('errexit', False), ('nounset', False)],
        arg.opt_changes)
    self.assertEqual(2, arg_r.i)

    # Even weirder!
    arg_r = args.Reader(['+oo', 'pipefail', 'errexit'])
    arg = args.ParseMore(s, arg_r)
    self.assertEqual(
        [('pipefail', False), ('errexit', False)],
        arg.opt_changes)
    self.assertEqual(3, arg_r.i)

    # Now this is an arg.  Gah.
    arg_r = args.Reader(['+o', 'pipefail', 'errexit'])
    arg = args.ParseMore(s, arg_r)
    self.assertEqual([('pipefail', False)], arg.opt_changes)
    self.assertEqual(['errexit'], arg_r.Rest())

    # NOTE: 'set -ooo' and 'set -o -o -o' bash runs 'set -o' three times!
    # We're not going to replicate that silly behavior.

  def testChoices(self):
    s = flag_spec._FlagSpecAndMore()
    s.LongFlag('--ast-format', ['text', 'html'])

    arg_r = args.Reader(['--ast-format', 'text'])
    arg = args.ParseMore(s, arg_r)
    self.assertEqual('text', arg.ast_format)

    self.assertRaises(
        error.Usage, args.Parse, s, args.Reader(['--ast-format', 'oops']))

  def testFlagSpec(self):
    s = flag_spec._FlagSpec()
    s.ShortFlag('-f')
    s.ShortFlag('-n')
    s.ShortFlag('-d', args.String)  # delimiter

    # like declare +rx
    s.PlusFlag('r')
    s.PlusFlag('x')

    arg, i = _ParseCmdVal(s, _MakeBuiltinArgv(['-f', 'foo', 'bar']))
    self.assertEqual(1, i-1)
    self.assertEqual(True, arg.f)
    #self.assertEqual(False, arg.n)
    self.assertEqual(False, arg.n)

    self.assertRaises(
        error.Usage, _ParseCmdVal, s, _MakeBuiltinArgv(['-f', '-d']))

    arg, i = _ParseCmdVal(s, _MakeBuiltinArgv(['-d', ' ', 'foo']))
    self.assertEqual(2, i-1)
    self.assertEqual(' ', arg.d)

    arg, i = _ParseCmdVal(s, _MakeBuiltinArgv(['-d,',  'foo']))
    self.assertEqual(1, i-1)
    self.assertEqual(',', arg.d)
    #self.assertEqual(False, arg.r)
    self.assertEqual(None, arg.r)

    arg, i = _ParseCmdVal(s, _MakeBuiltinArgv(['-d,', '-r', '-x']))
    self.assertEqual(4, i)
    self.assertEqual(',', arg.d)
    self.assertEqual('-', arg.r)
    self.assertEqual('-', arg.x)

    arg, i = _ParseCmdVal(s, _MakeBuiltinArgv(['-d,', '+rx']))
    self.assertEqual(3, i)
    self.assertEqual(',', arg.d)
    self.assertEqual('+', arg.r)
    self.assertEqual('+', arg.x)

  def testReadFlagSpec(self):
    s = flag_spec._FlagSpec()
    s.ShortFlag('-r')  # no backslash escapes
    s.ShortFlag('-t', args.Float)  # timeout
    s.ShortFlag('-p', args.String)  # prompt string

    arg, i = _ParseCmdVal(s, _MakeBuiltinArgv(['-r', 'foo']))
    self.assertEqual(True, arg.r)
    self.assertEqual(1, i-1)

    arg, i = _ParseCmdVal(s, _MakeBuiltinArgv(['-p', '>']))
    self.assertEqual(False, arg.r)
    self.assertEqual('>', arg.p)
    self.assertEqual(2, i-1)

    arg, i = _ParseCmdVal(s, _MakeBuiltinArgv(['-rp', '>']))
    self.assertEqual(True, arg.r)
    self.assertEqual('>', arg.p)
    self.assertEqual(2, i-1)

    # REALLY ANNOYING: The first r is a flag, the second R is the prompt!  Only
    # works in that order
    # Does that mean anything with an arity consumes the rest?
    # read -p line
    #
    arg, i = _ParseCmdVal(s, _MakeBuiltinArgv(['-rpr']))
    self.assertEqual(True, arg.r)
    self.assertEqual('r', arg.p)
    self.assertEqual(1, i-1)

    argv = ['-t1.5', '>']
    arg, i = _ParseCmdVal(s, _MakeBuiltinArgv(argv))
    self.assertEqual(1.5, arg.t)
    self.assertEqual(1, i-1)

    # Invalid flag 'z'
    self.assertRaises(error.Usage, _ParseCmdVal, s, _MakeBuiltinArgv(['-rz']))

  def testParseLikeEcho(self):
    s = flag_spec._FlagSpec()
    s.ShortFlag('-e')  # no backslash escapes
    s.ShortFlag('-n')

    arg_r = _MakeReader(['-e', '-n', 'foo'])
    arg = args.ParseLikeEcho(s, arg_r)
    self.assertEqual(True, arg.e)
    self.assertEqual(True, arg.n)
    self.assertEqual(3, arg_r.i)

    arg_r = _MakeReader(['-en', 'foo'])
    arg = args.ParseLikeEcho(s, arg_r)
    self.assertEqual(True, arg.e)
    self.assertEqual(True, arg.n)
    self.assertEqual(2, arg_r.i)

    arg_r = _MakeReader(['-ez', 'foo'])
    arg = args.ParseLikeEcho(s, arg_r)
    #self.assertEqual(False, arg.e)
    #self.assertEqual(False, arg.n)
    self.assertEqual(False, arg.e)
    self.assertEqual(False, arg.n)
    self.assertEqual(1, arg_r.i)


if __name__ == '__main__':
  unittest.main()
