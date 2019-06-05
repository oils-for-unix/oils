#!/usr/bin/env python2
"""
refactor.py
"""
from __future__ import print_function

import re
import sys


COND_RE = re.compile(r'''
^
(?P<begin>.*?)
(?P<var>\w+)\.tag
\s*
== 
\s*
(?P<sum>[\w_]+)_e\.(?P<variant>[\w_]+)
(?P<end>.*)
$
''', re.VERBOSE)


def main(argv):
  action = argv[1]
  if action == 'sub':
    for line in sys.stdin:
      m = COND_RE.match(line)
      if m:
        print('%sisinstance(%s, %s__%s)%s' % (
          m.group('begin'),
          m.group('var'),
          m.group('sum'),
          m.group('variant'),
          m.group('end')
        ))
      else:
        sys.stdout.write(line)



if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
