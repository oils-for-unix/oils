#!/usr/bin/python
"""
args.py

All shells have their own flag parsing, so I guses we need our own too.

Differences with getopt/optparse:

- accepts +o +n for 'set' and bin/osh
  - pushd and popd also uses +, although it's not an arg.
- parses args -- well argparse is supposed to do this
- maybe: integrate with usage
- maybe: integrate with flags

- Actually I think optparse does the same thing?
  - maybe just fork it?
  - I don't like the store_true crap

issue:
  - does it support long args
    - --foo bar
    - --foo=bar
    - ABBREVIATIONS for long args
  - does it abort after arg
    - echo -n foo -e   #  GNU allows, but bash doesn't

optparse: 
  - has option groups

- notes about builtins:
  - eval implicitly joins it args, we don't want to do that
    - how about strict-builtin-syntax ?

spec = args.Spec()
# maybe: spec.RespectDoubleDash(False)  # for echo?

spec.FlagForOptionOn('-o')
spec.FlagForOptionOff('+o')  # -s -u for shopt

spec.Flag('-c', None, args.Str)  # opt.c
spec.Flag('-i', None, args.Str)
spec.Flag(None, '--debug-spans')
spec.Flag(None, '--debug-spans')

# TODO: repeated flags for --trace?

spec.Option('u', 'nounset')  # -o nounset
spec.Option(None, 'pipefail')

# Function to call with a boolean
spec.Option('e', 'errexit', callback=exec_opts.errexit.Set)

args = spec.Parse(argv)  # how to set?

flag = Flags()  # dumb thing
exec_opts = ExecOpts()
rest = []
i = spec.Parse(argv, flag, exec_opts)
rest = argv[i:]

args.flags.c
args.flags.debug_spans

args.options.nounset  # always the long one
args.options.pipefail

args.rest == argv if not


spec = args.Spec()
spec.Arg(1, 'args.Int', 'num')   # for shift

# If args are specified, then it limits errors
# Otherwise no options

# GOALS: sharing

NOTE: 
- bash is inconsistent about checking for extra args
  - exit 1 2 complains, but pushd /lib /bin just ignores second argument
  - it has a no_args() function that isn't called everywhere.  It's not
    declarative.

"""

import sys

class UsageError(Exception):
  """Raised by builtins upon flag parsing error."""
  pass


def main(argv):
  print 'Hello from args.py'


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
