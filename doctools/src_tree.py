#!/usr/bin/env python2
"""
src_tree.py: Publish a directory tree as HTML

TODO:

- dir listing:
  - should have columns
  - or add line counts, and file counts?
  - render README.md - would be nice

- Could use JSON Template {.template} like test/wild_report.py
  - for consistent header and all that

AUTO

- overview.html and for-translation.html should link to these files, not Github
  - also add Github link at top of file?

- devtools/release.sh should change to build this
  - and link it from release-quality.md

"""
from __future__ import print_function

import os
import shutil
import sys

from doctools.util import log
from doctools import html_head

from test import jsontemplate
from test import wild_report

T = jsontemplate.Template


def DetectType(path):
  if path.endswith('.test.sh'):
    return 'spec'

  elif path.endswith('.ysh'):
    # For now, YSH highlighting is identical
    return 'sh'

  elif path.endswith('.sh'):
    return 'sh'

  elif path.endswith('.py') or path.endswith('.pyi'):
    return 'py'

  # Same lexical syntax
  elif path.endswith('.pgen2') or path.endswith('.asdl'):
    return 'py'

  # C files are the same
  elif path.endswith('.cc') or path.endswith('.h') or path.endswith('.c'):
    return 'cc'

  elif path.endswith('.js'):
    return 'js'

  elif path.endswith('.R'):
    return 'R'

  else:
    # Markdown, CSS, etc.
    return 'other'


def Breadcrumb(rel_path, out_f, is_file=False):
  offset = -1 if is_file else 0
  data = wild_report.MakeNav(rel_path, root_name='OILS', offset=offset)
  out_f.write(wild_report.NAV_TEMPLATE.expand({'nav': data}))


# CSS class .line has white-space: pre

# To avoid copy-paste problem, you could try the <div> solutions like this:
# https://gitlab.com/gitlab-examples/python-getting-started/-/blob/master/manage.py?ref_type=heads

# Note: we are compressing some stuff

ROW_T = T("""\
<tr>
  <td class=num>{line_num}</td>
  <td id=L{line_num}>
    <span class="line {.section line_class}{@}{.end}">{line}</span>
  </td>
</tr>
""", default_formatter='html')


LISTING_T = T("""\
<body class="width40">

{.section dirs}
<div id="dirs">
  <h1>Dirs</h1>
  {.repeated section @}
    <a href="{name|htmltag}/index.html">{name|html}/</a> <br/>
  {.end}
</div>
{.end}

{.section files}
<div id="files">
  <h1>Files</h1>
  {.repeated section @}
    <a href="{url|htmltag}">{anchor|html}</a> <br/>
  {.end}
</div>
{.end}

</body>
""")


def Files(pairs, attrs_f, spec_to_html=False):

  for i, (path, html_out) in enumerate(pairs):
    #log(path)

    try:
      os.makedirs(os.path.dirname(html_out))
    except OSError:
      pass

    with open(path) as in_f, open(html_out, 'w') as out_f:
      title = path

      # How deep are we?
      n = path.count('/') + 2
      base_dir = '/'.join(['..'] * n)

      css_urls = ['%s/web/base.css' % base_dir, '%s/web/src-tree.css' % base_dir]
      html_head.Write(out_f, title, css_urls=css_urls)

      out_f.write('''
      <body class="width40">
        <p id="home-link">
          <a href="https://github.com/oilshell/oil/blob/master/%s">View on Github</a>
          |
          <a href="/">oilshell.org</a>
        </p>
        <table>
      ''' % path)

      if not spec_to_html:  # Don't need navigation here
        Breadcrumb(path, out_f, is_file=True)

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

        elif file_type in ('spec', 'sh', 'py', 'R'):
          if s.startswith('#'):
            row['line_class'] = 'comm1'

        elif file_type == 'cc':
          # Real cheap solution for now
          if s.startswith('//'):
            row['line_class'] = 'comm1'

        elif file_type == 'js':
          if s.startswith('//'):
            row['line_class'] = 'comm1'

        out_f.write(ROW_T.expand(row))

        line_num += 1

      # parsed by 'dirs'
      print('%s lines=%d' % (path, line_num), file=attrs_f)

      out_f.write('''
        </table>
      </body>
    </html>''')

  return i + 1


class DirNode:
  """Entry in the file system tree.

  Similar to test/wild_report.py
  """

  def __init__(self):
    self.files = {}  # filename -> attrs dict
    self.dirs = {}  # subdir name -> DirNode object

    # Can accumulate total lines here
    self.subtree_stats = {}  # name -> value


def DebugPrint(node, indent=0):
  """Debug print."""
  ind = indent * '    '
  #print('FILES', node.files.keys())
  for name in node.files:
    print('%s%s - %s' % (ind, name, node.files[name]))

  for name, child in node.dirs.iteritems():
    print('%s%s/ - %s' % (ind, name, child.subtree_stats))
    DebugPrint(child, indent=indent+1)


def UpdateNodes(node, path_parts, attrs):
  """Similar to test/wild_report.y"""

  first = path_parts[0]
  rest = path_parts[1:]

  if rest:  # update an intermediate node
    if first in node.dirs:
      child = node.dirs[first]
    else:
      child = DirNode()
      node.dirs[first] = child

    UpdateNodes(child, rest, attrs)

  else:
    # leaf node
    node.files[first] = attrs


def MakeTree(stdin, root_node):
  for line in sys.stdin:
    parts = line.split()
    path = parts[0]

    # Examples:
    # {'lines': '345'}
    # {'raw': '1'}
    attrs = {}
    for part in parts[1:]:
      k, v = part.split('=')
      attrs[k] = v

    path_parts = path.split('/')
    UpdateNodes(root_node, path_parts, attrs)


def WriteHtmlFiles(node, out_dir, rel_path='', base_url=''):
  log('WriteHtmlFiles %s %s %s', out_dir, rel_path, base_url)

  files = []
  for name in sorted(node.files):
    attrs = node.files[name]

    # Big files are raw, e.g. match.re2c.h and syntax_asdl.py
    url = name if attrs.get('raw') else '%s.html' % name
    f = {'url': url, 'anchor': name}
    files.append(f)

  dirs = []
  for name in sorted(node.dirs):
    dirs.append({'name': name})

  data = {'files': files, 'dirs': dirs}
  body = LISTING_T.expand(data)

  path = os.path.join(out_dir, 'index.html')
  with open(path, 'w') as f:

    title = '%s - Listing' % rel_path
    css_urls = ['%s../../web/base.css' % base_url, '%s../../web/src-tree.css' % base_url]
    html_head.Write(f, title, css_urls=css_urls)

    Breadcrumb(rel_path, f)

    f.write(body)

    f.write('</html>')

  # Recursive
  for name, child in node.dirs.iteritems():
    child_out = os.path.join(out_dir, name)
    child_rel = os.path.join(rel_path, name)
    child_base = base_url + '../'
    WriteHtmlFiles(child, child_out, rel_path=child_rel, base_url=child_base)


def main(argv):
  action = argv[1]

  if action == 'files':
    # Policy for _tmp/src-tree

    out_dir = argv[2]
    paths = argv[3:]

    attrs_f = sys.stdout

    pairs = []
    for path in paths:

      # _gen/frontend/match.re2c.h is 367 KB, and gets expanded to over 2 MB of HTML.
      # So render big files as plain text.
      # TODO: directory lister needs to take this into account

      file_size = os.path.getsize(path)
      if file_size > 100000:
        out_path = os.path.join(out_dir, path)
        try:
          os.makedirs(os.path.dirname(out_path))
        except OSError:
          pass

        shutil.copyfile(path, out_path)
        print('%s raw=1' % path, file=attrs_f)
        log('Copied %d byte file %s -> %s, no HTML', file_size, path, out_path)
        continue

      html_out = os.path.join(out_dir, '%s.html' % path)
      pairs.append((path, html_out))

    n = Files(pairs, attrs_f)
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

    attrs_f = sys.stdout
    n = Files(pairs, attrs_f, spec_to_html=True)
    log('%s: Wrote %d HTML files -> %s', os.path.basename(sys.argv[0]), n,
        out_dir)

  elif action == 'dirs':
    # stdin: a bunch of merged ATTRs file?

    # We load them, and write a whole tree?
    out_dir = argv[2]

    # I think we make a big data structure here

    root_node = DirNode()
    MakeTree(sys.stdin, root_node)

    if 1:
      DebugPrint(root_node)

    WriteHtmlFiles(root_node, out_dir)

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  main(sys.argv)


# vim: sw=2
