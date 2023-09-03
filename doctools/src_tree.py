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
    # For now, YSH highlighting is identical
    return 'sh'

  elif path.endswith('.sh'):
    return 'sh'

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

# To avoid copy-paste problem, you could try the <div> solutions like this:
# https://gitlab.com/gitlab-examples/python-getting-started/-/blob/master/manage.py?ref_type=heads

ROW_T = jsontemplate.Template("""\
<tr>
  <td class=num>{line_num}</td>
  <td id=L{line_num}>
    <span class="line {.section line_class}{@}{.end}">{line}</span>
  </td>
</tr>
""", default_formatter='html')


def Files(pairs, spec_to_html=False):

  for i, (path, html_out) in enumerate(pairs):
    log(path)

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

      if not spec_to_html:  # Don't need navigation here
        Breadcrumb(path, out_f)

      file_type = DetectType(path)

      line_num = 1  # 1-based
      for line in in_f:
        if line.endswith('\n'):
          line = line[:-1]

        # Write line numbers
        row = {'line_num': line_num, 'line': line}

        s = line.lstrip()

        if file_type == 'spec':
          if s.startswith('###'):
            row['line_class'] = 'comm3'
          elif s.startswith('#'):
            row['line_class'] = 'comm1'

        elif file_type in ('spec', 'sh', 'py'):
          if s.startswith('#'):
            row['line_class'] = 'comm1'

        elif file_type == 'cc':
          # Real cheap solution for now
          if s.startswith('//'):
            row['line_class'] = 'comm1'

        out_f.write(ROW_T.expand(row))

        line_num += 1

      # ATTRS
      #print('%s lines=%d' %(path, line_num))

      out_f.write('''
        </table>
      </body>
    </html>''')

  return i + 1


def main(argv):
  action = argv[1]

  if action == 'files':
    out_dir = argv[2]
    paths = argv[3:]

    pairs = []
    for path in paths:
      html_out = os.path.join(out_dir, '%s.html' % path)
      pairs.append((path, html_out))

    n = Files(pairs)
    log('%s: Wrote %d HTML files -> %s', os.path.basename(sys.argv[0]), n,
        out_dir)

  elif action == 'spec-files':
    # Policy for _tmp/spec/osh-minimal/foo.test.html

    out_dir = argv[2]
    spec_names = argv[3:]

    pairs = []
    for name in spec_names:
       src = 'spec/%s.test.sh' % name
       html_out = os.path.join(out_dir, '%s.test.html' % name)
       pairs.append((src, html_out))

    n = Files(pairs, spec_to_html=True)
    log('%s: Wrote %d HTML files -> %s', os.path.basename(sys.argv[0]), n,
        out_dir)

  elif action == 'dirs':
    # stdin: a bunch of merged ATTRs file?

    # We load them, and write a whole tree?
    out_dir = argv[0]

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  main(sys.argv)


# vim: sw=2
