#!/usr/bin/env python2
"""
split_doc.py
"""
from __future__ import print_function

import json
import re
import sys


DATE_RE = re.compile(
    r'(\d\d\d\d) / (\d\d) / (\d\d)', re.VERBOSE)

META_RE = re.compile(
    r'(\S+): [ ]* (.*)', re.VERBOSE)


def SplitDocument(entry_f, meta_f, content_f):
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
    raise AssertionError('Every blog post should now begin with ---')

  json.dump(meta, meta_f)

  # Read the rest of the file and write it
  contents = entry_f.read()

  content_f.write(contents)

  comments_url = meta.get('comments_url', '')
  if comments_url:
    content_f.write("""
[comments-url]: %s

""" % comments_url)


def main(argv):
  entry_path = argv[1]  # e.g. blog/2016/11/01.md
  out_prefix = argv[2]  # e.g _site/blog/2016/11/01

  meta_path = out_prefix + '_meta.json'
  content_path = out_prefix + '_content.md'

  with \
      open(entry_path) as entry_f, \
      open(meta_path, 'w') as meta_f, \
      open(content_path, 'w') as content_f:
    SplitDocument(entry_f, meta_f, content_f)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
