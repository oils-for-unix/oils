#!/usr/bin/env python2
"""
split_doc.py
"""
from __future__ import print_function

import json
import optparse
import re
import sys


DATE_RE = re.compile(
    r'(\d\d\d\d) / (\d\d) / (\d\d)', re.VERBOSE)

META_RE = re.compile(
    r'(\S+): [ ]* (.*)', re.VERBOSE)


def SplitDocument(default_vals, entry_f, meta_f, content_f, strict=False):
  """Split a document into metadata JSON and content Markdown.

  Used for blog posts and index.md / cross-ref.md.
  """
  first_line = entry_f.readline()
  if strict and first_line.strip() != '---':
    raise RuntimeError("Document should start with --- (got %r)" % first_line)

  meta = {}

  # TODO: if first_line is ---, then read metadata in key: value format.
  if first_line.strip() == '---':
    while True:
      line = entry_f.readline().strip()
      if line == '---':
        break
      m = META_RE.match(line)
      if not m:
        raise RuntimeError('Invalid metadata line %r' % line)
      name, value = m.groups()

      if name == 'date':
        m2 = DATE_RE.match(value)
        if not m2:
          raise RuntimeError('Invalid date %r' % value)
        year, month, day = m2.groups()
        meta['year'] = int(year)
        meta['month'] = int(month)
        meta['day'] = int(day)

      elif name == 'updated_date':
        m2 = DATE_RE.match(value)
        if not m2:
          raise RuntimeError('Invalid date %r' % value)
        year, month, day = m2.groups()
        meta['updated_year'] = int(year)
        meta['updated_month'] = int(month)
        meta['updated_day'] = int(day)

      else:
        meta[name] = value

    #print('line = %r' % line, file=sys.stderr)
    while True:
      first_nonempty = entry_f.readline()
      if first_nonempty.strip() != '':
        break

  else:
    if first_line:
      first_nonempty = first_line
    else:
      while True:
        first_nonempty = entry_f.readline()
        if first_nonempty.strip() != '':
          break

  # Invariant: we've read the first non-empty line here.  Now we need to see if
  # it's the title.

  #print('first_nonempty = %r' % first_nonempty, file=sys.stderr)

  line_two = entry_f.readline()
  if re.match('=+', line_two):
    meta['title'] = first_nonempty.strip()

  # Fill in defaults after parsing all values.
  for name, value in default_vals.iteritems():
    if name not in meta:
      meta[name] = value

  json.dump(meta, meta_f, indent=2)

  # Read the rest of the file and write it
  contents = entry_f.read()

  content_f.write(first_nonempty)
  content_f.write(line_two)

  content_f.write(contents)

  comments_url = meta.get('comments_url', '')
  if comments_url:
    content_f.write("""
[comments-url]: %s

""" % comments_url)



def Options():
  """Returns an option parser instance."""
  p = optparse.OptionParser('split_doc.py [options] input_file out_prefix')
  # Like awk -v
  p.add_option(
      '-v', dest='default_vals', action='append', default=[],
      help="If the doc's own metadata doesn't define 'name', set it to this value")
  p.add_option(
      '-s', '--strict', dest='strict', action='store_true', default=False,
      help="Require metadata")
  return p


def main(argv):
  o = Options()
  opts, argv = o.parse_args(argv)

  entry_path = argv[1]  # e.g. blog/2016/11/01.md
  out_prefix = argv[2]  # e.g _site/blog/2016/11/01

  meta_path = out_prefix + '_meta.json'
  content_path = out_prefix + '_content.md'

  default_vals = {}
  for pair in opts.default_vals:
    name, value = pair.split('=', 1)
    default_vals[name] = value

  with \
      open(entry_path) as entry_f, \
      open(meta_path, 'w') as meta_f, \
      open(content_path, 'w') as content_f:
    SplitDocument(default_vals, entry_f, meta_f, content_f, strict=opts.strict)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
