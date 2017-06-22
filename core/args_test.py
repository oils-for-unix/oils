#!/usr/bin/python -S
"""
args_test.py: Tests for args.py
"""

import unittest

from core import args  # module under test


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

    argv = ['-c', 'echo hi', '-e', '-o', 'nounset', 'foo', '--help']  # don't parse args afterward
    arg, i = s.Parse(argv)
    print(arg, argv[i:])

    self.assertEqual(['foo', '--help'], argv[i:])
    self.assertEqual('echo hi', arg.c)
    self.assertEqual(None, arg.help)
    self.assertEqual(None, arg.i)

    self.assertEqual(
        [('errexit', True), ('nounset', True)], arg.opt_changes)

    argv = ['+e', '+o', 'nounset', '-o', 'pipefail', 'foo']
    arg, i = s.Parse(argv)
    print(arg, argv[i:])

    self.assertEqual(['foo'], argv[i:])
    self.assertEqual(None, arg.i)
    self.assertEqual(
        [('errexit', False), ('nounset', False), ('pipefail', True)],
        arg.opt_changes)

    self.assertRaises(args.UsageError, s.Parse, ['-o', 'pipefailX'])

    argv = ['-c', 'echo hi', '--help', '--rcfile', 'bashrc']
    arg, i = s.Parse(argv)
    self.assertEqual('echo hi', arg.c)
    self.assertEqual(True, arg.help)
    self.assertEqual('bashrc', arg.rcfile)

    # This is an odd syntax!
    argv = ['-euo', 'pipefail']
    arg, i = s.Parse(argv)
    self.assertEqual(
        [('errexit', True), ('nounset', True), ('pipefail', True)],
        arg.opt_changes)
    self.assertEqual(2, i)

    # Even weirder!
    argv = ['+oeu', 'pipefail']
    arg, i = s.Parse(argv)
    self.assertEqual(
        [('pipefail', False), ('errexit', False), ('nounset', False)],
        arg.opt_changes)
    self.assertEqual(2, i)

    # Even weirder!
    argv = ['+oo', 'pipefail', 'errexit']
    arg, i = s.Parse(argv)
    self.assertEqual(
        [('pipefail', False), ('errexit', False)],
        arg.opt_changes)
    self.assertEqual(3, i)

    # Now this is an arg.  Gah.
    argv = ['+o', 'pipefail', 'errexit'] 
    arg, i = s.Parse(argv)
    self.assertEqual([('pipefail', False)], arg.opt_changes)
    self.assertEqual(['errexit'], argv[i:])

    # NOTE: 'set -ooo' and 'set -o -o -o' bash runs 'set -o' three times!
    # We're not going to replicate that silly behavior.

  def testChoices(self):
    s = args.FlagsAndOptions()
    s.LongFlag('--ast-format', ['text', 'html'])

    arg, i = s.Parse(['--ast-format', 'text'])
    self.assertEqual('text', arg.ast_format)

    self.assertRaises(args.UsageError, s.Parse, ['--ast-format', 'oops'])

  def testBuiltinFlags(self):
    s = args.BuiltinFlags()
    s.ShortFlag('-f')
    s.ShortFlag('-n')
    s.ShortFlag('-d', args.Str)  # delimiter

    arg, i = s.Parse(['-f', 'foo', 'bar'])
    self.assertEqual(1, i)
    self.assertEqual(True, arg.f)
    self.assertEqual(None, arg.n)

    self.assertRaises(args.UsageError, s.Parse, ['-f', '-d'])

    arg, i = s.Parse(['-d', ' ', 'foo'])
    self.assertEqual(2, i)
    self.assertEqual(' ', arg.d)

    arg, i = s.Parse(['-d,',  'foo'])
    self.assertEqual(1, i)
    self.assertEqual(',', arg.d)

  def testReadBuiltinFlags(self):
    s = args.BuiltinFlags()
    s.ShortFlag('-r')  # no backslash escapes
    s.ShortFlag('-t', args.Float)  # timeout
    s.ShortFlag('-p', args.Str)  # prompt string

    arg, i = s.Parse(['-r', 'foo'])
    self.assertEqual(True, arg.r)
    self.assertEqual(1, i)

    arg, i = s.Parse(['-p', '>'])
    self.assertEqual(None, arg.r)
    self.assertEqual('>', arg.p)
    self.assertEqual(2, i)

    arg, i = s.Parse(['-rp', '>'])
    self.assertEqual(True, arg.r)
    self.assertEqual('>', arg.p)
    self.assertEqual(2, i)

    # REALLY ANNOYING: The first r is a flag, the second R is the prompt!  Only
    # works in that order
    # Does that mean anything with an arity consumes the rest?
    # read -p line
    #
    arg, i = s.Parse(['-rpr'])
    self.assertEqual(True, arg.r)
    self.assertEqual('r', arg.p)
    self.assertEqual(1, i)

    argv = ['-t1.5', '>']
    arg, i = s.Parse(argv)
    self.assertEqual(1.5, arg.t)
    self.assertEqual(1, i)

    # Invalid flag 'z'
    self.assertRaises(args.UsageError, s.Parse, ['-rz'])


if __name__ == '__main__':
  unittest.main()
