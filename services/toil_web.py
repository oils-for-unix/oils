#!/usr/bin/env python2
"""
toil_index.py

Each continuous build run is assigned an ID.  Then it will generate:

- $ID.git-log 
- $ID.json  # metadata
- $ID.tsv   # benchmarks/time.py output?  success/failure for each task
- $ID.wwz   # files

This script should generate an index.html with links to all the logs.

"""
from __future__ import print_function

import sys
from doctools import html_head


def main(argv):
  html_head.Write(sys.stdout, 'Recent Jobs',
      css_urls=['/web/base.css', '/web/toil.css'])

  print('''\
  </body>
</html>
''')

  # TODO: read jobs on stdin
  # - open .tsv and JSON
  # - write HTML to output


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
