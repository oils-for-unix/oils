#!/usr/bin/env python2
"""
github_issues.py
"""
from __future__ import print_function

import cgi
import json
import sys


def main(argv):
  # - .number
  # - .title
  # - .html_url
  #
  # And then format as HTML.

  issues = json.load(sys.stdin)
  for issue in issues:  # dict
    d = {}
    d['html_url'] = issue['html_url'].encode('utf-8')
    d['number'] = issue['number']
    d['title'] = cgi.escape(issue['title'].encode('utf-8'))
    print('''\
<tr>
  <td class="issue-num">
    <a href="%(html_url)s">#%(number)s</a>
  </td>
  <td class="issue-title">
    %(title)s
  </td>
</tr>
''' % d)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
