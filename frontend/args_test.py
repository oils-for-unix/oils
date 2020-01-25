#!/usr/bin/env python2
"""
args_test.py: Tests for args.py
"""

import unittest

from _devbuild.gen.runtime_asdl import cmd_value
from asdl import runtime
from frontend import args  # module under test


def _MakeBuiltinArgv(argv):
  argv = [''] + argv  # add dummy since arg_vec includes argv[0]
  # no location info
  return cmd_value.Argv(argv, [runtime.NO_SPID] * len(argv))


class ArgsTest(unittest.TestCase):

  def testFlagsAndOptions(self):
    s = args.FlagsAndOptions()
    s.ShortFlag('-c', args.Str)
    s.ShortFlag('-i', args.Str)

    s.LongFlag('--help')
    s.LongFlag('--rcfile', args.Str)

    s.LongFlag('--ast-format', ['text', 'html'])

    s.Option('e', 'errexit')
    s.Option('u', 'nounset')
    s.Option(None, 'pipefail')

    # don't parse args afterward
    arg_r = args.Reader(
        ['-c', 'echo hi', '-e', '-o', 'nounset', 'foo', '--help'])
    arg = s.Parse(arg_r)

    self.assertEqual(['foo', '--help'], arg_r.Rest())
    self.assertEqual('echo hi', arg.c)
    self.assertEqual(None, arg.help)
    self.assertEqual(None, arg.i)

    self.assertEqual(
        [('errexit', True), ('nounset', True)], arg.opt_changes)

    arg_r = args.Reader(['+e', '+o', 'nounset', '-o', 'pipefail', 'foo'])
    arg = s.Parse(arg_r)

    self.assertEqual(['foo'], arg_r.Rest())
    self.assertEqual(None, arg.i)
    self.assertEqual(
        [('errexit', False), ('nounset', False), ('pipefail', True)],
        arg.opt_changes)

    self.assertRaises(
        args.UsageError, s.Parse, args.Reader(['-o', 'pipefailX']))

    arg_r = args.Reader(['-c', 'echo hi', '--help', '--rcfile', 'bashrc'])
    arg = s.Parse(arg_r)
    self.assertEqual('echo hi', arg.c)
    self.assertEqual(True, arg.help)
    self.assertEqual('bashrc', arg.rcfile)

    # This is an odd syntax!
    arg_r = args.Reader(['-euo', 'pipefail'])
    arg = s.Parse(arg_r)
    self.assertEqual(
        [('errexit', True), ('nounset', True), ('pipefail', True)],
        arg.opt_changes)
    self.assertEqual(2, arg_r.i)

    # Even weirder!
    arg_r = args.Reader(['+oeu', 'pipefail'])
    arg = s.Parse(arg_r)
    self.assertEqual(
        [('pipefail', False), ('errexit', False), ('nounset', False)],
        arg.opt_changes)
    self.assertEqual(2, arg_r.i)

    # Even weirder!
    arg_r = args.Reader(['+oo', 'pipefail', 'errexit'])
    arg = s.Parse(arg_r)
    self.assertEqual(
        [('pipefail', False), ('errexit', False)],
        arg.opt_changes)
    self.assertEqual(3, arg_r.i)

    # Now this is an arg.  Gah.
    arg_r = args.Reader(['+o', 'pipefail', 'errexit'])
    arg = s.Parse(arg_r)
    self.assertEqual([('pipefail', False)], arg.opt_changes)
    self.assertEqual(['errexit'], arg_r.Rest())

    # NOTE: 'set -ooo' and 'set -o -o -o' bash runs 'set -o' three times!
    # We're not going to replicate that silly behavior.

  def testChoices(self):
    s = args.FlagsAndOptions()
    s.LongFlag('--ast-format', ['text', 'html'])

    arg_r = args.Reader(['--ast-format', 'text'])
    arg = s.Parse(arg_r)
    self.assertEqual('text', arg.ast_format)

    self.assertRaises(
        args.UsageError, s.Parse, args.Reader(['--ast-format', 'oops']))

  def testBuiltinFlags(self):
    s = args.BuiltinFlags()
    s.ShortFlag('-f')
    s.ShortFlag('-n')
    s.ShortFlag('-d', args.Str)  # delimiter

    # like declare +rx
    s.ShortOption('r')
    s.ShortOption('x')

    arg, i = s.ParseVec(_MakeBuiltinArgv(['-f', 'foo', 'bar']))
    self.assertEqual(1, i-1)
    self.assertEqual(True, arg.f)
    self.assertEqual(None, arg.n)

    self.assertRaises(
        args.UsageError, s.ParseVec, _MakeBuiltinArgv(['-f', '-d']))

    arg, i = s.ParseVec(_MakeBuiltinArgv(['-d', ' ', 'foo']))
    self.assertEqual(2, i-1)
    self.assertEqual(' ', arg.d)

    arg, i = s.ParseVec(_MakeBuiltinArgv(['-d,',  'foo']))
    self.assertEqual(1, i-1)
    self.assertEqual(',', arg.d)
    self.assertEqual(None, arg.r)

    arg, i = s.ParseVec(_MakeBuiltinArgv(['-d,', '-r', '-x']))
    self.assertEqual(4, i)
    self.assertEqual(',', arg.d)
    self.assertEqual('-', arg.r)
    self.assertEqual('-', arg.x)

    arg, i = s.ParseVec(_MakeBuiltinArgv(['-d,', '+rx']))
    self.assertEqual(3, i)
    self.assertEqual(',', arg.d)
    self.assertEqual('+', arg.r)
    self.assertEqual('+', arg.x)

  def testReadBuiltinFlags(self):
    s = args.BuiltinFlags()
    s.ShortFlag('-r')  # no backslash escapes
    s.ShortFlag('-t', args.Float)  # timeout
    s.ShortFlag('-p', args.Str)  # prompt string

    arg, i = s.ParseVec(_MakeBuiltinArgv(['-r', 'foo']))
    self.assertEqual(True, arg.r)
    self.assertEqual(1, i-1)

    arg, i = s.ParseVec(_MakeBuiltinArgv(['-p', '>']))
    self.assertEqual(None, arg.r)
    self.assertEqual('>', arg.p)
    self.assertEqual(2, i-1)

    arg, i = s.ParseVec(_MakeBuiltinArgv(['-rp', '>']))
    self.assertEqual(True, arg.r)
    self.assertEqual('>', arg.p)
    self.assertEqual(2, i-1)

    # REALLY ANNOYING: The first r is a flag, the second R is the prompt!  Only
    # works in that order
    # Does that mean anything with an arity consumes the rest?
    # read -p line
    #
    arg, i = s.ParseVec(_MakeBuiltinArgv(['-rpr']))
    self.assertEqual(True, arg.r)
    self.assertEqual('r', arg.p)
    self.assertEqual(1, i-1)

    argv = ['-t1.5', '>']
    arg, i = s.ParseVec(_MakeBuiltinArgv(argv))
    self.assertEqual(1.5, arg.t)
    self.assertEqual(1, i-1)

    # Invalid flag 'z'
    self.assertRaises(args.UsageError, s.ParseVec, _MakeBuiltinArgv(['-rz']))

  def testParseLikeEcho(self):
    s = args.BuiltinFlags()
    s.ShortFlag('-e')  # no backslash escapes
    s.ShortFlag('-n')

    arg, i = s.ParseLikeEcho(['-e', '-n', 'foo'])
    self.assertEqual(True, arg.e)
    self.assertEqual(True, arg.n)
    self.assertEqual(2, i)

    arg, i = s.ParseLikeEcho(['-en', 'foo'])
    self.assertEqual(True, arg.e)
    self.assertEqual(True, arg.n)
    self.assertEqual(1, i)

    arg, i = s.ParseLikeEcho(['-ez', 'foo'])
    self.assertEqual(None, arg.e)
    self.assertEqual(None, arg.n)
    self.assertEqual(0, i)

  def testOilFlags(self):
    s = args.OilFlags()
    s.Flag('-docstring', args.Bool, default=True)
    s.Flag('-out-file', args.Str)
    s.Flag('-retries', args.Int)

    arg, i = s.ParseArgv(['-docstring=0', 'x', 'y'])
    self.assertEqual(False, arg.docstring)
    self.assertEqual(None, arg.out_file)
    self.assertEqual(1, i)

    # This turns it on too
    arg, i = s.ParseArgv(['-docstring', '0', 'x', 'y'])
    self.assertEqual(True, arg.docstring)
    self.assertEqual(None, arg.out_file)
    self.assertEqual(1, i)

    arg, i = s.ParseArgv(['-out-file', 'out', 'y'])
    self.assertEqual(True, arg.docstring)
    self.assertEqual('out', arg.out_file)
    self.assertEqual(2, i)

    arg, i = s.ParseArgv(['-retries', '3'])
    self.assertEqual(3, arg.retries)

    arg, i = s.ParseArgv(['-retries=3'])
    self.assertEqual(3, arg.retries)

    # Like GNU: anything that starts with -- is parsed like an option.
    self.assertRaises(args.UsageError, s.ParseArgv, ['---'])

    self.assertRaises(args.UsageError, s.ParseArgv, ['-oops'])

    # Invalid boolean arg
    self.assertRaises(args.UsageError, s.ParseArgv, ['--docstring=YEAH'])

    arg, i = s.ParseArgv(['--'])
    self.assertEqual(1, i)

    arg, i = s.ParseArgv(['-'])
    self.assertEqual(0, i)

    arg, i = s.ParseArgv(['abc'])
    self.assertEqual(0, i)

  def testFlagRegex(self):
    import libc
    CASES = [
        '-',
        '--',
        '--+',
        '---',  # invalid flag but valid arg
        '---invalid',  # invalid flag but valid arg?
        '-port',
        '--port',
        '--port-num',
        '--port-num=8000',
        '--port-num=',  # empty value
        '--port-num=x=y',  # only first = matters

        # We should point out the bad +.  It should match but then become an
        # error.  It shoudl NOT be an arg!
        '--port-num+',  # invalid
        ]
    for case in CASES:
      print('%s\t%s' % (case, libc.regex_match(args._FLAG_ERE, case)))


if __name__ == '__main__':
  unittest.main()
