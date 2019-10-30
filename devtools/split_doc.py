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


def SplitDocument(default_vals, entry_f, meta_f, content_f):
  """Split a document into metadata JSON and content Markdown.

  Used for blog posts and index.md / cross-ref.md.
  """
  first_line = entry_f.readline().strip()

  # TODO: if first_line is ---, then read metadata in key: value format.
  if first_line == '---':
    meta = {}
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

  else:
    raise AssertionError(
        "Document should start with --- (got %r)" % first_line)


  for name, value in default_vals.iteritems():
    if name not in meta:
      meta[name] = value

  # Parse the title like this:
  # ---
  # repo-url:
  # ---
  #
  # Title
  # =====

  one = entry_f.readline()
  two = entry_f.readline()
  three = entry_f.readline()
  if re.match('=+', three):
    meta['title'] = two.strip()

  json.dump(meta, meta_f, indent=2)

  # Read the rest of the file and write it
  contents = entry_f.read()

  content_f.write(one)
  content_f.write(two)
  content_f.write(three)
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
    SplitDocument(default_vals, entry_f, meta_f, content_f)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
