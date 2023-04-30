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

File = collections.namedtuple('File',
    'name suite tags compare_shells our_shell allowed_failures')


class SpecParams(object):
  """
  There are 3 suites:

    osh, ysh, tea

  The suites are a bit historical, because we compare them over time in the
  release notes.

  We also have tags:

    interactive  # cases that use $SH -i should also run under a 'docker -t'
    osh-minimal  # smoke test for dev-minimal
    smoosh       # currently not run in CI, but we should

  There are also tests from 'toysh', but they're currently part of 'osh'.
  """
  def __init__(self):
    self.files = []

  def File(self,
      name,  # e.g. alias, oil-blocks
      suite=None,
      tags=None,
      compare_shells='',  # e.g. 'bash' or 'bash dash mksh zsh'
      our_shell='',  # osh or ysh
      allowed_failures=0):

    assert suite is not None

    # our_shell may be bin/osh, _bin/cxx-asan/osh, _bin/cxx-gclaways/osh, an
    # optimized release tarball version, etc.
    if name.startswith('oil-') or name.startswith('hay'):
      o = our_shell or 'ysh'
    elif name.startswith('tea-'):
      # Tea could run from OSH with parse_tea!  Nothing here passes yet.
      o = our_shell or 'osh'  
    else:
      o = our_shell or 'osh'

    # Note: Can also select bash 4.4 vs. bash 5.2 here
    c = compare_shells.split() if compare_shells else []

    fi = File(name, suite, tags or [], c, o, allowed_failures)
    self.files.append(fi)

  def OshFile(self, name, *args, **kwargs):
    self.File(name, suite='osh', **kwargs)

  def YshFile(self, name, **kwargs):
    self.File(name, suite='ysh', **kwargs)


def main(argv):

  sp = SpecParams()

  # Example of what we want to generate
  if 0:
    sp.File('alias', compare_shells='bash')
    sp.File('append', compare_shells='bash dash mksh zsh', allowed_failures=5)
    sp.File('oil-blocks')
    sp.File('oil-builtins', our_shell='osh')


  # Not part of OSH or YSH
  sp.File('tea-func', suite='tea')

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
    # called by test/spec-runner.sh write-suite-manifest

    # TODO:
    # SUITE-{osh,ysh,tea} for CI, let's restore that
    #
    # SUITE-osh-interactive for 'interactive' job with docker -t

    # SUITE-osh-minimal too

    # SUITE-osh-noninteractive for release?  Not sure about this
    # Or at least we want to separate the interactive from non-interactive ones

    #suite = argv[2]
    #assert suite in ('osh', 'ysh', 'tea'), suite
    for fi in sp.files:
      #if fi.suite == suite:
      print('%s\t%s\t%d\t%s' % (fi.suite, fi.our_shell, fi.allowed_failures, fi.name))

  elif action == 'print-tagged':
    tag = argv[2]

    for fi in sp.files:
      if tag in fi.tags:
        #print('%s\t%s\t%d\t%s' % (fi.suite, fi.our_shell, fi.allowed_failures, fi.name))
        print(fi.name)

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
