#!/usr/bin/env python2
"""
spec_params.py - Generate params for various spec test runs

e.g. Python vs. C++, or OSH vs other shells
"""
from __future__ import print_function

import collections
import sys

from test import spec_osh
from test import spec_ysh

File = collections.namedtuple('File', 'name suite compare_shells our_shell allowed_failures')


class SpecParams(object):

  def __init__(self):
    self.files = []

  def File(self,
      name,  # e.g. alias, oil-blocks
      compare_shells='',  # e.g. 'bash' or 'bash dash mksh zsh'
      our_shell='',  # osh or ysh
      allowed_failures=0):

    # our_shell may be bin/osh, _bin/cxx-asan/osh, _bin/cxx-gclaways/osh, an
    # optimized release tarball version, etc.
    if name.startswith('oil-') or name.startswith('hay'):
      suite = 'ysh'
      o = our_shell or 'ysh'
    else:
      suite = 'osh'
      o = our_shell or 'osh'

    # Note: Can also select bash 4.4 vs. bash 5.2 here
    c = compare_shells.split() if compare_shells else []

    fi = File(name, suite, c, o, allowed_failures)
    self.files.append(fi)


def main(argv):

  sp = SpecParams()

  # Example of what we want to generate
  if 0:
    sp.File('alias', compare_shells='bash')
    sp.File('append', compare_shells='bash dash mksh zsh', allowed_failures=5)
    sp.File('oil-blocks')
    sp.File('oil-builtins', our_shell='osh')

  spec_osh.Define(sp)
  spec_ysh.Define(sp)

  action = argv[1]

  if action == 'vars-for-file':
    name = argv[2]
    for fi in sp.files:
      if name == fi.name:
        # TODO: Could print a shell string to evaluate
        #print('%s\t%s\t%d\t%s' % (fi.suite, fi.our_shell, fi.allowed_failures, fi.name))

        # Meant for local $(spec_params.py vars-for-file oil-blocks)
        print('suite=%s our_shell=%s allowed_failures=%d' %
              (fi.suite, fi.our_shell, fi.allowed_failures))

        # TODO: print the list of shells, space separated
        #
        # Could flatten this table for parallel execution?
        #print(fi.compare_shells)

        break
    else:
      raise RuntimeError('File %r not found' % name)

  elif action == 'print-table':
    # called by write-suite-manifest

    #suite = argv[2]
    #assert suite in ('osh', 'ysh', 'tea'), suite
    for fi in sp.files:
      #if fi.suite == suite:
      print('%s\t%s\t%d\t%s' % (fi.suite, fi.our_shell, fi.allowed_failures, fi.name))

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
