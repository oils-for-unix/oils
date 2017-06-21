#!/usr/bin/python -S
"""
args_test.py: Tests for args.py
"""

import unittest

from core import args  # module under test


class ArgsTest(unittest.TestCase):

  def testBuiltinFlags(self):
    return
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

  def testChoices(self):
    s = args.FlagsAndOptions()
    s.LongFlag('--ast-format', ['text', 'html'])

    arg, i = s.Parse(['--ast-format', 'text'])
    self.assertEqual('text', arg.ast_format)

    self.assertRaises(args.UsageError, s.Parse, ['--ast-format', 'oops'])

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

    # Also: 'set -ooo' and 'set -o -o -o' bash runs in three times!  How dumb.

    # This is an odd syntax!
    argv = ['-euo', 'pipefail']
    arg, i = s.Parse(argv)

    # Even weirder!
    argv = ['-oeu', 'pipefail']
    arg, i = s.Parse(argv)

    # Even weirder!
    argv = ['+oo', 'pipefail', 'errexit']
    arg, i = s.Parse(argv)

    # Now this is an arg.  Gah.
    argv = ['+o', 'pipefail', 'errexit'] 
    arg, i = s.Parse(argv)

  def testParseRead(self):
    return
    # -r is arity0
    # -p is arity1
    argv = ['-rp', '>']
    arg, i = s.Parse(argv)

    # REALLY ANNOYING: The first r is a flag, the second R is the prompt!  Only
    # works in that order
    # Does that mean anything with an arity consumes the rest?
    # read -p line
    #
    argv = ['-rpr']
    arg, i = s.Parse(argv)

    argv = ['-t1.0', '>']
    arg, i = s.Parse(argv)

    # This is an array name!  Not an invalid option.
    # I think there are TWO KINDS OF OPTION PARSERS.  Yeah it's all custom
    # code.

    # ParseFlagsAndOptions -- uses
    #  this is DIFFERENT because -opipefail is NOT allowed!
    #  must be -o pipefail

    # ParseBuiltinFlags -- uses internal_getopt
    #  allows -t1.0  but also -rp>

    # ParseLikeEcho -- ignores --

    #   bashgetopt has a *opts == '+' check
    #   leading +: allow options
    #   codes:
    #   : requires argument
    #   ; argument may be missing
    #   # numeric argument
    #
    # However I don't see these used anywhere!  I only see ':' used.
    argv = ['-azzz']
    arg, i = s.Parse(argv)


if __name__ == '__main__':
  unittest.main()
