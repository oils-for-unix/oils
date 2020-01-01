#!/usr/bin/env python2
from __future__ import print_function
"""
wild_report.py
"""

import json
import optparse
import os
import sys

import jsontemplate

# JSON Template Evaluation:
#
# - {.if}{.or} is confusing
# I think there is even a bug with {.if}{.else}{.end} -- it accepts it but
# doesn't do the right thing!
#   - {.if test} does work though, but it took me awhile to remember that or
#   - I forgot about {.link?} too
#   even find it in the source code.  I don't like this separate predicate
#   language.  Could just be PHP-ish I guess.
# - Predicates are a little annoying.
# - Lack of location information on undefined variables is annoying.  It spews
# a big stack trace.
# - The styles thing seems awkward.  Copied from srcbook.
# - I don't have {total_secs|%.3f} , but the
# LookupChain/DictRegistry/CallableRegistry thing is quite onerous.
#
# Good parts:
# Just making one big dict is pretty nice.

T = jsontemplate.Template

F = {
    'commas': lambda n: '{:,}'.format(n),
    #'urlesc': urllib.quote_plus,
    }

def MakeHtmlGroup(title_str, body_str):
  """Make a group of templates that we can expand with a common style."""
  return {
      'TITLE': T(title_str, default_formatter='html', more_formatters=F),
      'BODY': T(body_str, default_formatter='html', more_formatters=F),
      'NAV': NAV_TEMPLATE,
  }

BODY_STYLE = jsontemplate.Template("""\
<!DOCTYPE html>
<html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{.template TITLE}</title>

    <script type="text/javascript" src="{base_url}../../web/ajax.js"></script>
    <script type="text/javascript" src="{base_url}../../web/table/table-sort.js"></script>
    <link rel="stylesheet" type="text/css" href="{base_url}../../web/base.css" />
    <link rel="stylesheet" type="text/css" href="{base_url}../../web/table/table-sort.css" />
    <link rel="stylesheet" type="text/css" href="{base_url}../../web/wild.css" />
  </head>

  <body onload="initPage(gUrlHash, gTables, gTableStates, kStatusElem);"
        onhashchange="onHashChange(gUrlHash, gTableStates, kStatusElem);"
        class="width60">
    <p id="status"></p>

    <p style="text-align: right"><a href="/">oilshell.org</a></p>
{.template NAV}

{.template BODY}
  </body>

</html>
""", default_formatter='html')

# NOTE: {.link} {.or id?} {.or} {.end} doesn't work?  That is annoying.
NAV_TEMPLATE = jsontemplate.Template("""\
{.section nav}
<p id="nav">
{.repeated section @}
  {.link?}
    <a href="{link|htmltag}">{anchor}</a>
  {.or}
    {anchor}
  {.end}
{.alternates with}
  /
{.end}
</p>
{.end}
""", default_formatter='html')


PAGE_TEMPLATES = {}

# <a href="{base_url}osh-to-oil.html#{rel_path|htmltag}/{name|htmltag}">view</a>
PAGE_TEMPLATES['FAILED'] = MakeHtmlGroup(
    '{task}_failed',
"""\
<h1>{failures|size} {task} failures</h1>

{.repeated section failures}
  <a href="{base_url}osh-to-oil.html#{rel_path|htmltag}">{rel_path|html}</a>
  <pre>
  {stderr}
  </pre>
{.end}
""")

# One is used for sort order.  One is used for alignment.
# type="string"
# should we use the column css class as the sort order?  Why not?

# NOTES on columns:
# - The col is used to COLOR the column when it's being sorted by
#   - But it can't be use to align text right.  See
#   https://stackoverflow.com/questions/1238115/using-text-align-center-in-colgroup
# - type="number" is used in table-sort.js for the sort order.
# - We use CSS classes on individual cells like <td class="name"> to align
#   columns.  That seems to be the only way to do it?

PAGE_TEMPLATES['LISTING'] = MakeHtmlGroup(
    'WILD/{rel_path} - Parsing and Translating Shell Scripts with Oil',
"""\

{.section subtree_stats}
<div id="summary">
<ul>
{.parse_failed?}
  <li>
    Attempted to parse <b>{num_files|commas}</b> shell scripts totalling
    <b>{num_lines|commas}</b> lines.
  </li>
  {.not_shell?}
    <li>
      <b>{not_shell|commas}</b> files are known not to be shell.
      {.if test top_level_links}
        (<a href="not-shell.html">full list</a>)
      {.end}
    </li>
  {.end}
  {.not_osh?}
    <li>
      <b>{not_osh|commas}</b> files are known not to be OSH.
      {.if test top_level_links}
        (<a href="not-osh.html">full list</a>)
      {.end}
    </li>
  {.end}
  <li>
    Failed to parse <b>{parse_failed|commas}</b> scripts, leaving
    <b>{lines_parsed|commas}</b> lines parsed in <b>{parse_proc_secs}</b>
    seconds (<b>{lines_per_sec}</b> lines/sec).
    {.if test top_level_links}
      (<a href="parse-failed.html">all failures</a>,
       <a href="parse-failed.txt">text</a>)
    {.end}
  </li>
{.or}
  <li>
    Successfully parsed <b>{num_files|commas}</b> shell scripts totalling
    <b>{num_lines|commas}</b> lines
    in <b>{parse_proc_secs}</b> seconds
    (<b>{lines_per_sec}</b> lines/sec).
  </li>
{.end}

<li>
  <b>{osh2oil_failed|commas}</b> OSH-to-Oil translations failed.
  {.if test top_level_links}
    (<a href="osh2oil-failed.html">all failures</a>,
     <a href="osh2oil-failed.txt">text</a>)
  {.end}
</li>
</ul>
</div>

<p></p>
{.end}


{.section dirs}
<table id="dirs">
  <colgroup> <!-- for table-sort.js -->
    <col type="number">
    <col type="number">
    <col type="number">
    <col type="number">
    <col type="number">
    <col type="number">
    <col type="number">
    <col type="case-insensitive">
  </colgroup>
  <thead>
    <tr>
      <td>Files</td>
      <td>Max Lines</td>
      <td>Total Lines</td>
      <!-- <td>Lines Parsed</td> -->
      <td>Parse Failures</td>
      <td>Max Parse Time (secs)</td>
      <td>Total Parse Time (secs)</td>
      <td>Translation Failures</td>
      <td class="name">Directory</td>
    </tr>
  </thead>
  <tbody>
  {.repeated section @}
    <tr>
      <td>{num_files|commas}</td>
      <td>{max_lines|commas}</td>
      <td>{num_lines|commas}</td>
      <!-- <td>{lines_parsed|commas}</td> -->
      {.parse_failed?}
        <td class="fail">{parse_failed|commas}</td>
      {.or}
        <td class="ok">{parse_failed|commas}</td>
      {.end}
      <td>{max_parse_secs}</td>
      <td>{parse_proc_secs}</td>

      {.osh2oil_failed?}
        <!-- <td class="fail">{osh2oil_failed|commas}</td> -->
        <td>{osh2oil_failed|commas}</td>
      {.or}
        <!-- <td class="ok">{osh2oil_failed|commas}</td> -->
        <td>{osh2oil_failed|commas}</td>
      {.end}

      <td class="name">
        <a href="{name|htmltag}/index.html">{name|html}/</a>
      </td>
    </tr>
  {.end}
  </tbody>
</table>
{.end}

<p>
</p>

{.section files}
<table id="files">
  <colgroup> <!-- for table-sort.js -->
    <col type="case-insensitive">
    <col type="number">
    <col type="case-insensitive">
    <col type="number">
    <col type="case-insensitive">
    <col type="case-insensitive">
  </colgroup>
  <thead>
    <tr>
      <td>Side By Side</td>
      <td>Lines</td>
      <td>Parsed?</td>
      <td>Parse Process Time (secs)</td>
      <td>Translated?</td>
      <td class="name">Filename</td>
    </tr>
  </thead>
  <tbody>
  {.repeated section @}
    <tr>
      <td>
        <a href="{base_url}osh-to-oil.html#{rel_path|htmltag}/{name|htmltag}">view</a>
     </td>
      <td>{num_lines|commas}</td>
      <td>
        {.parse_failed?}
          <a class="fail" href="#stderr_parse_{name}">FAIL</a>
          <td>{parse_proc_secs}</td>
        {.or}
          <a class="ok" href="{name}__ast.html">OK</a>
          <td>{parse_proc_secs}</td>
        {.end}
      </td>

      <td>
        {.osh2oil_failed?}
          <a class="fail" href="#stderr_osh2oil_{name}">FAIL</a>
        {.or}
          <a class="ok" href="{name}__oil.txt">OK</a>
        {.end}
      </td>
      <td class="name">
        <a href="{name|htmltag}.txt">{name|html}</a>
      </td>
    </tr>
  {.end}
  </tbody>
</table>
{.end}

{.if test empty}
  <i>(empty dir)</i>
{.end}

{.section stderr}
  <h2>stderr</h2>

  <table id="stderr">

  {.repeated section @}
    <tr>
      <td>
        <a name="stderr_{action}_{name|htmltag}"></a>
        {.if test parsing}
          Parsing {name|html}
        {.or}
          Translating {name|html}
        {.end}
      </td>
      <td>
        <pre>
        {contents|html}
        </pre>
      </td>
    <tr/>
  {.end}

  </table>
{.end}

{.if test top_level_links}
<a href="version-info.txt">Date and OSH version<a>
{.end}

<!-- page globals -->
<script type="text/javascript">
  var gUrlHash = new UrlHash(location.hash);
  var gTableStates = {};
  var kStatusElem = document.getElementById('status');

  var gTables = [];
  var e1 = document.getElementById('dirs');
  var e2 = document.getElementById('files');

  // If no hash, "redirect" to a state where we sort ascending by dir name and
  // filename.  TODO: These column numbers are a bit fragile.
  var params = [];
  if (e1) {
    gTables.push(e1);
    params.push('t:dirs=8a');
  }
  if (e2) {
    gTables.push(e2);
    params.push('t:files=7a');
  }

  function initPage(urlHash, gTables, tableStates, statusElem) {
    makeTablesSortable(urlHash, gTables, tableStates);
    /* Disable for now, this seems odd?  Think about mutability of gUrlHash.
    if (location.hash === '') {
      document.location = '#' + params.join('&');
      gUrlHash = new UrlHash(location.hash);
    }
    */
    updateTables(urlHash, tableStates, statusElem);
  }

  function onHashChange(urlHash, tableStates, statusElem) {
    updateTables(urlHash, tableStates, statusElem);
  }
</script>
""")


def log(msg, *args):
  if msg:
    msg = msg % args
  print(msg, file=sys.stderr)


class DirNode:
  """Entry in the file system tree."""

  def __init__(self):
    self.files = {}  # filename -> stats for success/failure, time, etc.
    self.dirs = {}  # subdir name -> Dir object

    self.subtree_stats = {}  # name -> value

    # show all the non-empty stderr here?
    # __osh2oil.stderr.txt
    # __parse.stderr.txt
    self.stderr = []


def UpdateNodes(node, path_parts, file_stats):
  """
  Create a file node and update the stats of all its descendants in the FS
  tree.
  """
  first = path_parts[0]
  rest = path_parts[1:]

  for name, value in file_stats.iteritems():
    # Sum numerical properties, but not strings
    if isinstance(value, int) or isinstance(value, float):
      if name in node.subtree_stats:
        node.subtree_stats[name] += value
      else:
        # NOTE: Could be int or float!!!
        node.subtree_stats[name] = value

  # Calculate maximums
  m = node.subtree_stats.get('max_parse_secs', 0.0)
  node.subtree_stats['max_parse_secs'] = max(m, file_stats['parse_proc_secs'])

  m = node.subtree_stats.get('max_lines', 0)  # integer
  node.subtree_stats['max_lines'] = max(m, file_stats['num_lines'])

  if rest:  # update an intermediate node
    if first in node.dirs:
      child = node.dirs[first]
    else:
      child = DirNode()
      node.dirs[first] = child

    UpdateNodes(child, rest, file_stats)
  else:
    # TODO: Put these in different sections?  Or least one below the other?

    # Include stderr if non-empty, or if FAILED
    parse_stderr = file_stats.pop('parse_stderr')
    if parse_stderr or file_stats['parse_failed']:
      node.stderr.append({
          'parsing': True,
          'action': 'parse',
          'name': first,
          'contents': parse_stderr,
      })
    osh2oil_stderr = file_stats.pop('osh2oil_stderr')

    # TODO: Could disable this with a flag to concentrate on parse errors.
    # Or just show parse errors all in one file.
    if 1:
      if osh2oil_stderr or file_stats['osh2oil_failed']:
        node.stderr.append({
            'parsing': False,
            'action': 'osh2oil',
            'name': first,
            'contents': osh2oil_stderr,
        })

    # Attach to this dir
    node.files[first] = file_stats


def DebugPrint(node, indent=0):
  """Debug print."""
  ind = indent * '    '
  #print('FILES', node.files.keys())
  for name in node.files:
    print('%s%s - %s' % (ind, name, node.files[name]))
  for name, child in node.dirs.iteritems():
    print('%s%s/ - %s' % (ind, name, child.subtree_stats))
    DebugPrint(child, indent=indent+1)


def WriteJsonFiles(node, out_dir):
  """Write a index.json file for every directory."""
  path = os.path.join(out_dir, 'index.json')
  with open(path, 'w') as f:
    raise AssertionError  # fix dir_totals
    d = {'files': node.files, 'dirs': node.dir_totals}
    json.dump(d, f)

  log('Wrote %s', path)

  for name, child in node.dirs.iteritems():
    WriteJsonFiles(child, os.path.join(out_dir, name))


def _MakeNav(rel_path):
  assert not rel_path.startswith('/'), rel_path
  assert not rel_path.endswith('/'), rel_path
  # Get rid of ['']
  parts = ['WILD'] + [p for p in rel_path.split('/') if p]
  data = []
  n = len(parts)
  for i, p in enumerate(parts):
    if i == n - 1:
      link = None  # Current page shouldn't have link
    else:
      link = '../' * (n - 1 - i) + 'index.html'
    data.append({'anchor': p, 'link': link})
  return data


def _Lower(s):
  return s.lower()


def WriteHtmlFiles(node, out_dir, rel_path='', base_url=''):
  """Write a index.html file for every directory.

  NOTE:
  - osh-to-oil.html lives at $base_url
  - table-sort.js lives at $base_url/../table-sort.js

  wild/
    table-sort.js
    table-sort.css
    www/
      index.html
      osh-to-oil.html

  wild/
    table-sort.js
    table-sort.css
    wild.wwz/  # Zip file
      index.html
      osh-to-oil.html

  wwz latency is subject to caching headers.
  """
  path = os.path.join(out_dir, 'index.html')
  with open(path, 'w') as f:
    files = []
    for name in sorted(node.files, key=_Lower):
      stats = node.files[name]
      entry = dict(stats)
      entry['name'] = name
      # TODO: This should be internal time
      lines_per_sec = entry['lines_parsed'] / entry['parse_proc_secs']
      entry['lines_per_sec'] = '%.1f' % lines_per_sec
      files.append(entry)

    dirs = []
    for name in sorted(node.dirs, key=_Lower):
      entry = dict(node.dirs[name].subtree_stats)
      entry['name'] = name
      # TODO: This should be internal time
      lines_per_sec = entry['lines_parsed'] / entry['parse_proc_secs']
      entry['lines_per_sec'] = '%.1f' % lines_per_sec
      dirs.append(entry)

    # TODO: Is there a way to make this less redundant?
    st = node.subtree_stats
    try:
      lines_per_sec = st['lines_parsed'] / st['parse_proc_secs']
      st['lines_per_sec'] = '%.1f' % lines_per_sec
    except KeyError:
      # This usually there were ZERO files.
      print(node, st, repr(rel_path), file=sys.stderr)
      raise

    data = {
        'rel_path': rel_path,
        'subtree_stats': node.subtree_stats,  # redundant totals
        'files': files,
        'dirs': dirs,
        'base_url': base_url,
        'stderr': node.stderr,
        'nav': _MakeNav(rel_path),
    }
    # Hack to add links for top level page:
    if rel_path == '':
      data['top_level_links'] = True

    group = PAGE_TEMPLATES['LISTING']
    body = BODY_STYLE.expand(data, group=group)
    f.write(body)

  log('Wrote %s', path)

  # Recursive
  for name, child in node.dirs.iteritems():
    child_out = os.path.join(out_dir, name)
    child_rel = os.path.join(rel_path, name)
    child_base = base_url + '../'
    WriteHtmlFiles(child, child_out, rel_path=child_rel, base_url=child_base)


def _ReadTaskFile(path):
  """
  Parses the a file that looks like '0 0.11', for the status code and timing.
  This is output by test/common.sh run-task-with-status.
  """
  try:
    with open(path) as f:
      parts = f.read().split()
      status, secs = parts
  except ValueError as e:
    log('ERROR reading %s: %s', path, e)
    raise
  # Turn it into pass/fail
  num_failed = 1 if int(status) >= 1 else 0
  return num_failed, float(secs)


def _ReadLinesToSet(path):
  """Read blacklist files like not-shell.txt and not-osh.txt.

  TODO: Consider adding globs here?  There are a lot of FreeBSD and illumos
  files we want to get rid of.

  Or we could probably do that in the original 'find' expression.
  """
  result = set()
  if not path:
    return result

  with open(path) as f:
    for line in f:
      # Allow comments.  We assume filenames don't have #
      i = line.find('#')
      if i != -1:
        line = line[:i]

      line = line.strip()
      if not line:  # Lines that are blank or only comments.
        continue

      result.add(line)

  return result


def SumStats(stdin, in_dir, not_shell, not_osh, root_node, failures):
  """Reads pairs of paths from stdin, and updates root_node."""
  # Collect work into dirs
  for line in stdin:
    rel_path, abs_path = line.split()
    #print proj, '-', abs_path, '-', rel_path

    raw_base = os.path.join(in_dir, rel_path)
    st = {}

    st['not_shell'] = 1 if rel_path in not_shell else 0
    st['not_osh'] = 1 if rel_path in not_osh else 0
    if st['not_shell'] and st['not_osh']:
      raise RuntimeError(
          "%r can't be in both not-shell.txt and not-osh.txt" % rel_path)

    expected_failure = bool(st['not_shell'] or st['not_osh'])

    parse_task_path = raw_base + '__parse.task.txt'
    parse_failed, st['parse_proc_secs'] = _ReadTaskFile(
        parse_task_path)
    st['parse_failed'] = 0 if expected_failure else parse_failed 

    with open(raw_base + '__parse.stderr.txt') as f:
      st['parse_stderr'] = f.read()

    if st['not_shell']:
      failures.not_shell.append(
          {'rel_path': rel_path, 'stderr': st['parse_stderr']}
      )
    if st['not_osh']:
      failures.not_osh.append(
          {'rel_path': rel_path, 'stderr': st['parse_stderr']}
      )
    if st['parse_failed']:
      failures.parse_failed.append(
          {'rel_path': rel_path, 'stderr': st['parse_stderr']}
      )

    osh2oil_task_path = raw_base + '__osh2oil.task.txt'
    osh2oil_failed, st['osh2oil_proc_secs'] = _ReadTaskFile(
        osh2oil_task_path)

    # Only count translation failures if the parse suceeded!
    st['osh2oil_failed'] = osh2oil_failed if not parse_failed else 0

    with open(raw_base + '__osh2oil.stderr.txt') as f:
      st['osh2oil_stderr'] = f.read()

    if st['osh2oil_failed']:
      failures.osh2oil_failed.append(
          {'rel_path': rel_path, 'stderr': st['osh2oil_stderr']}
      )

    wc_path = raw_base + '__wc.txt'
    with open(wc_path) as f:
      st['num_lines'] = int(f.read().split()[0])
    # For lines per second calculation
    st['lines_parsed'] = 0 if st['parse_failed'] else st['num_lines']

    st['num_files'] = 1

    path_parts = rel_path.split('/')
    #print path_parts
    UpdateNodes(root_node, path_parts, st)


class Failures(object):
  """Simple object that gets transformed to HTML and text."""
  def __init__(self):
    self.parse_failed = []
    self.osh2oil_failed = []
    self.not_shell = []
    self.not_osh = []

  def Write(self, out_dir):
    with open(os.path.join(out_dir, 'parse-failed.txt'), 'w') as f:
      for failure in self.parse_failed:
        print(failure['rel_path'], file=f)

    with open(os.path.join(out_dir, 'osh2oil-failed.txt'), 'w') as f:
      for failure in self.osh2oil_failed:
        print(failure['rel_path'], file=f)

    base_url = ''

    with open(os.path.join(out_dir, 'not-shell.html'), 'w') as f:
      data = {
          'task': 'not-shell', 'failures': self.not_shell, 'base_url': base_url
      }
      body = BODY_STYLE.expand(data, group=PAGE_TEMPLATES['FAILED'])
      f.write(body)

    with open(os.path.join(out_dir, 'not-osh.html'), 'w') as f:
      data = {
          'task': 'not-osh', 'failures': self.not_osh, 'base_url': base_url
      }
      body = BODY_STYLE.expand(data, group=PAGE_TEMPLATES['FAILED'])
      f.write(body)

    with open(os.path.join(out_dir, 'parse-failed.html'), 'w') as f:
      data = {
          'task': 'parse', 'failures': self.parse_failed, 'base_url': base_url
      }
      body = BODY_STYLE.expand(data, group=PAGE_TEMPLATES['FAILED'])
      f.write(body)

    with open(os.path.join(out_dir, 'osh2oil-failed.html'), 'w') as f:
      data = {
          'task': 'osh2oil', 'failures': self.osh2oil_failed,
          'base_url': base_url
      }
      body = BODY_STYLE.expand(data, group=PAGE_TEMPLATES['FAILED'])
      f.write(body)


def Options():
  """Returns an option parser instance."""
  p = optparse.OptionParser('wild_report.py [options] ACTION...')
  p.add_option(
      '-v', '--verbose', dest='verbose', action='store_true', default=False,
      help='Show details about test execution')
  p.add_option(
      '--not-shell', default=None,
      help="A file that contains a list of files that are known to be invalid "
           "shell")
  p.add_option(
      '--not-osh', default=None,
      help="A file that contains a list of files that are known to be invalid "
           "under the OSH language.")
  return p


def main(argv):
  o = Options()
  (opts, argv) = o.parse_args(argv)

  action = argv[1]

  if action == 'summarize-dirs':
    in_dir = argv[2]
    out_dir = argv[3]

    not_shell = _ReadLinesToSet(opts.not_shell)
    not_osh = _ReadLinesToSet(opts.not_osh)

    # lines and size, oops

    # TODO: Need read the manifest instead, and then go by dirname() I guess
    # I guess it is a BFS so you can just assume?
    # os.path.dirname() on the full path?
    # Or maybe you need the output files?

    root_node = DirNode()
    failures = Failures()
    SumStats(sys.stdin, in_dir, not_shell, not_osh, root_node, failures)

    failures.Write(out_dir)

    # Debug print
    #DebugPrint(root_node)
    #WriteJsonFiles(root_node, out_dir)

    WriteHtmlFiles(root_node, out_dir)

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
