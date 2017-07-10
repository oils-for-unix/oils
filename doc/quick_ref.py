#!/usr/bin/python
"""
quick_ref.py
"""

import sys


def main(argv):
  # inputs: -toc.txt, -pages.txt

  # outputs:
  #   tree of HTML

  # maybe: man page for OSH usage (need to learn troff formatting!)

  # syntactic elements:
  # - toc
  #   - links to pages
  #   - (X) for not implemented
  #   - aliases:  semicolon ;
  # - pages
  #   - usage line (^Usage:)
  #   - internal links read[1]
  #     - <a href="#read"><read>
  #     - read[1]
  #
  #   - example blocks

  # TODO:
  # - Copy sh_spec.py for # parsing
  # - Copy oilshell.org Snip for running examples and showing output!

  print 'Hello from quick_ref.py'


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
