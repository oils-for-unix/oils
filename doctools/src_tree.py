#!/usr/bin/env python2
"""
src_tree.py: Publish a directory tree as HTML
"""
from __future__ import print_function

import cgi
import cStringIO
import os
import re
import sys

from doctools.util import log
from doctools import html_head

from test import jsontemplate
from test import wild_report


def DetectType(path):
  if path.endswith('.test.sh'):
    return 'spec'

  elif path.endswith('.ysh'):
    return 'ysh'

  elif path.endswith('.sh'):
    return 'shell'

  elif path.endswith('.py'):
    return 'py'

  elif path.endswith('.cc') or path.endswith('.h'):
    return 'cc'

  else:
    # Markdown, CSS, etc.
    return 'other'


def Breadcrumb(rel_path, out_f):
  data = wild_report._MakeNav(rel_path, root_name='oils')
  out_f.write(wild_report.NAV_TEMPLATE.expand({'nav': data}))


# CSS class .line has white-space: pre

ROW_T = jsontemplate.Template("""\
<tr>
  <td class=num>{line_num}</td>
  <td id=L{line_num}>
    <span class="line {.section line_class}{@}{.end}">{line}</span>
  </td>
</tr>
""", default_formatter='html')


def Files(out_dir, paths):

  for path in paths:
    log(path)

    html_out = os.path.join(out_dir, path) + '.html'

    try:
      os.makedirs(os.path.dirname(html_out))
    except OSError:
      pass

    with open(path) as in_f, open(html_out, 'w') as out_f:
      title = path

      # How deep are we?
      n = path.count('/') + 2
      base_dir = '/'.join(['..'] * n)

      css_urls = ['%s/web/base.css' % base_dir, '%s/web/spec-code.css' % base_dir]
      html_head.Write(out_f, title, css_urls=css_urls)

      out_f.write('''
      <body class="width40">
        <table>
      ''')

      Breadcrumb(path, out_f)

      line_num = 1  # 1-based
      for line in in_f:
        if line.endswith('\n'):
          line = line[:-1]

        # Write line numbers
        row = {'line_num': line_num, 'line': line}

        if line.startswith('###'):
          row['line_class'] = 'comm3'
        elif line.startswith('#'):
          row['line_class'] = 'comm1'

        out_f.write(ROW_T.expand(row))

        line_num += 1

      # attrs
      print('%s lines=%d' %(path, line_num))

      out_f.write('''
        </table>
      </body>
    </html>''')


      # Write individual HTML files
      #
      # stdout: an ATTRS of line numbers
      #   TODO: this could be sloc
      #



def main(argv):
  action = argv[1]

  if action == 'files':
    out_dir = argv[2]
    paths = argv[3:]

    Files(out_dir, paths)

  elif action == 'dirs':
    # stdin: a bunch of merged ATTRs file?

    # We load them, and write a whole tree?
    out_dir = argv[0]


    pass

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  main(sys.argv)


# vim: sw=2
