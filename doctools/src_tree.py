#!/usr/bin/env python2
"""src_tree.py: Publish a directory tree as HTML.

TODO:

- dir listing:
  - should have columns
  - or add line counts, and file counts?
  - render README.md - would be nice

- Could use JSON Template {.template} like test/wild_report.py
  - for consistent header and all that

AUTO

- overview.html and for-translation.html should link to these files, not Github
"""
from __future__ import print_function

import json
import os
import shutil
import sys

from vendor.typing import IO

from doctools.util import log
from doctools import html_head
from test import wild_report
from vendor import jsontemplate

T = jsontemplate.Template


def DetectType(path):

    # Most support moved to src-tree.sh and micro-syntax

    if path.endswith('.test.sh'):
        return 'spec'

    else:
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
""",
          default_formatter='html')

LISTING_T = T("""\
{.section dirs}
<h1>Dirs</h1>
<div id="dirs" class="listing">
  {.repeated section @}
    <a href="{name|htmltag}/index.html">{name|html}/</a> <br/>
  {.end}
</div>
{.end}

{.section files}
<h1>Files</h1>
<div id="files" class="listing">
  {.repeated section @}
    <a href="{url|htmltag}">{anchor|html}</a> <br/>
  {.end}
</div>
{.end}

</body>
""")

FILE_COUNTS_T = T("""\
<div id="file-counts"> {num_lines} lines, {num_sig_lines} significant </div>
""",
                  default_formatter='html')


def SpecFiles(pairs, attrs_f):

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

            #css_urls = ['%s/web/base.css' % base_dir, '%s/web/src-tree.css' % base_dir]
            css_urls = ['%s/web/src-tree.css' % base_dir]

            html_head.Write(out_f, title, css_urls=css_urls)

            out_f.write('''
      <body class="">
        <div id="home-link">
          <a href="https://github.com/oilshell/oil/blob/master/%s">View on Github</a>
          |
          <a href="/">oils.pub</a>
        </div>
        <table>
      ''' % path)

            file_type = DetectType(path)

            line_num = 1  # 1-based
            for line in in_f:
                if line.endswith('\n'):
                    line = line[:-1]

                # Write line numbers
                row = {'line_num': line_num, 'line': line}

                s = line.lstrip()

                if file_type == 'spec':
                    if s.startswith('####'):
                        row['line_class'] = 'spec-comment'
                    elif s.startswith('#'):
                        row['line_class'] = 'comm'

                out_f.write(ROW_T.expand(row))

                line_num += 1

            # could be parsed by 'dirs'
            print('%s lines=%d' % (path, line_num), file=attrs_f)

            out_f.write('''
        </table>
      </body>
    </html>''')

    return i + 1


def ReadFragments(in_f):
    while True:
        path = ReadNetString(in_f)
        if path is None:
            break

        html_frag = ReadNetString(in_f)
        if html_frag is None:
            raise RuntimeError('Expected 2nd record (HTML fragment)')

        s = ReadNetString(in_f)
        if s is None:
            raise RuntimeError('Expected 3rd record (file summary)')

        summary = json.loads(s)

        yield path, html_frag, summary


def WriteHtmlFragments(in_f, out_dir, attrs_f=sys.stdout):

    i = 0
    for rel_path, html_frag, summary in ReadFragments(in_f):
        html_size = len(html_frag)
        if html_size > 300000:
            out_path = os.path.join(out_dir, rel_path)
            try:
                os.makedirs(os.path.dirname(out_path))
            except OSError:
                pass

            shutil.copyfile(rel_path, out_path)

            # Attrs are parsed by MakeTree(), and then used by WriteDirsHtml().
            # So we can print the right link.
            print('%s raw=1' % rel_path, file=attrs_f)

            file_size = os.path.getsize(rel_path)
            log('Big HTML fragment of %.1f KB', float(html_size) / 1000)
            log('Copied %s -> %s, %.1f KB', rel_path, out_path,
                float(file_size) / 1000)

            continue

        html_out = os.path.join(out_dir, rel_path + '.html')

        try:
            os.makedirs(os.path.dirname(html_out))
        except OSError:
            pass

        with open(html_out, 'w') as out_f:
            title = rel_path

            # How deep are we?
            n = rel_path.count('/') + 2
            base_dir = '/'.join(['..'] * n)

            #css_urls = ['%s/web/base.css' % base_dir, '%s/web/src-tree.css' % base_dir]
            css_urls = ['%s/web/src-tree.css' % base_dir]
            html_head.Write(out_f, title, css_urls=css_urls)

            out_f.write('''
      <body class="">
      <p>
      ''')
            Breadcrumb(rel_path, out_f, is_file=True)

            out_f.write('''
        <span id="home-link">
          <a href="https://github.com/oilshell/oil/blob/master/%s">View on Github</a>
          |
          <a href="/">oils.pub</a>
        </span>
      </p>
      ''' % rel_path)

            out_f.write(FILE_COUNTS_T.expand(summary))

            out_f.write('<table>')
            out_f.write(html_frag)

            print('%s lines=%d' % (rel_path, summary['num_lines']),
                  file=attrs_f)

            out_f.write('''
        </table>
      </body>
    </html>''')

        i += 1

    log('Wrote %d HTML fragments', i)


class DirNode:
    """Entry in the file system tree.

    Similar to test/wild_report.py
    """

    def __init__(self):
        # type: () -> None
        self.files = {}  # filename -> attrs dict
        self.dirs = {}  # subdir name -> DirNode object

        # Can accumulate total lines here
        self.subtree_stats = {}  # name -> value


def DebugPrint(node, indent=0):
    """Pretty-print our tree data structure."""
    ind = indent * '    '
    #print('FILES', node.files.keys())
    for name in node.files:
        print('%s%s - %s' % (ind, name, node.files[name]))

    for name, child in node.dirs.iteritems():
        print('%s%s/ - %s' % (ind, name, child.subtree_stats))
        DebugPrint(child, indent=indent + 1)


def UpdateNodes(node, path_parts, attrs):
    """Similar to test/wild_report.py."""

    first = path_parts[0]
    rest = path_parts[1:]

    if rest:  # update an intermediate node
        if first in node.dirs:
            child = node.dirs[first]
        else:
            child = DirNode()
            node.dirs[first] = child

        UpdateNodes(child, rest, attrs)
        # TODO: Update subtree_stats

    else:
        # leaf node
        node.files[first] = attrs


def MakeTree(stdin, root_node):
    """Reads a stream of lines Each line contains a path and key=value attrs.

    - Doesn't handle filenames with spaces
    - Doesn't handle empty dirs that are leaves (since only files are first
      class)
    """
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


def WriteDirsHtml(node, out_dir, rel_path='', base_url=''):
    #log('WriteDirectory %s %s %s', out_dir, rel_path, base_url)

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
        prefix = '%s../..' % base_url
        css_urls = ['%s/web/base.css' % prefix, '%s/web/src-tree.css' % prefix]
        html_head.Write(f, title, css_urls=css_urls)

        f.write('''
    <body>
      <p>
    ''')
        Breadcrumb(rel_path, f)

        f.write('''
        <span id="home-link">
          <a href="/">oils.pub</a>
        </span>
      </p>
    ''')

        f.write(body)

        f.write('</html>')

    # Recursive
    for name, child in node.dirs.iteritems():
        child_out = os.path.join(out_dir, name)
        child_rel = os.path.join(rel_path, name)
        child_base = base_url + '../'
        WriteDirsHtml(child,
                      child_out,
                      rel_path=child_rel,
                      base_url=child_base)


def ReadNetString(in_f):
    # type: (IO[str]) -> str

    digits = []
    for i in xrange(10):  # up to 10 digits
        c = in_f.read(1)
        if c == '':
            return None  # EOF

        if c == ':':
            break

        if not c.isdigit():
            raise RuntimeError('Bad byte %r' % c)

        digits.append(c)

    if c != ':':
        raise RuntimeError('Expected colon, got %r' % c)

    n = int(''.join(digits))

    s = in_f.read(n)
    if len(s) != n:
        raise RuntimeError('Expected %d bytes, got %d' % (n, len(s)))

    c = in_f.read(1)
    if c != ',':
        raise RuntimeError('Expected comma, got %r' % c)

    return s


def main(argv):
    action = argv[1]

    if action == 'spec-files':
        # Policy for _tmp/spec/osh-minimal/foo.test.html
        # This just changes the HTML names?

        out_dir = argv[2]
        spec_names = argv[3:]

        pairs = []
        for name in spec_names:
            src = 'spec/%s.test.sh' % name
            html_out = os.path.join(out_dir, '%s.test.html' % name)
            pairs.append((src, html_out))

        attrs_f = sys.stdout
        n = SpecFiles(pairs, attrs_f)
        log('%s: Wrote %d HTML files -> %s', os.path.basename(sys.argv[0]), n,
            out_dir)

    elif action == 'smoosh-file':
        # TODO: Should fold this generated code into the source tree, and run in CI

        in_path = argv[2]
        out_path = argv[3]
        pairs = [(in_path, out_path)]

        attrs_f = sys.stdout
        n = SpecFiles(pairs, attrs_f)
        log('%s: %s -> %s', os.path.basename(sys.argv[0]), in_path, out_path)

    elif action == 'write-html-fragments':

        out_dir = argv[2]
        WriteHtmlFragments(sys.stdin, out_dir)

    elif action == 'dirs':
        # stdin: a bunch of merged ATTRs file?

        # We load them, and write a whole tree?
        out_dir = argv[2]

        # I think we make a big data structure here

        root_node = DirNode()
        MakeTree(sys.stdin, root_node)

        if 0:
            DebugPrint(root_node)

        WriteDirsHtml(root_node, out_dir)

    else:
        raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
    main(sys.argv)
