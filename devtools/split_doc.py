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


# TODO: Should use JSON Template for these variants.
PAGE_TITLE = """\
<h1>%(title)s</h1>
"""

POST_TITLE = """\
<h2>%(title)s</h2>
<div class="date">
  %(year)s-%(month)02d-%(day)02d
</div>
"""

UPDATED_POST_TITLE = """\
<h2>%(title)s</h2>
<div> 
  <span class="date">
    %(year)s-%(month)02d-%(day)02d
  </span>
  <span style="float: right; font-size: medium;">
  (Last updated %(updated_year)s-%(updated_month)02d-%(updated_day)02d)
  </span>
</div>
"""


# COPIED FROM blog.py

def _IsBlog(meta):
  return 'year' in meta


def _GetTags(m):
  tags_str = m.get('tags')
  return tags_str.split() if tags_str else []


def SplitDocument(entry_f, meta_f, content_f):
  """Split a document into metadata JSON and content Markdown.

  Used for blog posts and index.md / cross-ref.md.
  """
  first_line = entry_f.readline().strip()

  # TODO: if first_line is ---, then read metadata in key: value format.
  has_date = False
  has_updated = False

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
        has_date = True

      elif name == 'updated_date':
        m2 = DATE_RE.match(value)
        if not m2:
          raise RuntimeError('Invalid date %r' % value)
        year, month, day = m2.groups()
        meta['updated_year'] = int(year)
        meta['updated_month'] = int(month)
        meta['updated_day'] = int(day)
        has_updated = True

      else:
        meta[name] = value

  else:
    raise AssertionError('Every blog post should now begin with ---')

  json.dump(meta, meta_f)

  # Read the rest of the file
  contents = entry_f.read()

  # TODO: Move this blog stuff into oilshell.org/blog.py?
  # They're not used for Oil docs.

  if has_updated and has_date:
    content_f.write(UPDATED_POST_TITLE % meta)
  elif has_date:
    # Write blog post title and year/month/day
    content_f.write(POST_TITLE % meta)
  else:
    # Just write the title of the page (e.g. cross ref)
    content_f.write(PAGE_TITLE % meta)

  content_f.write(contents)

  # TODO: Write footer after appendix somehow?
  if _IsBlog(meta):
    _WritePostFooter(meta, content_f)


def _WritePostFooter(meta, f):
  comments_url = meta.get('comments_url', '')
  if comments_url:
    f.write("""
[comments-url]: %s

""" % comments_url)

  f.write("""
<div id="post-footer">
<ul>
""" % meta)

  if comments_url:
    f.write('<li><a href="%(comments_url)s">Discuss This Post on Reddit</a>' % meta)

  f.write("""
  <li>Get notified about new posts via
  <a href="https://twitter.com/oilshellblog">@oilshellblog on Twitter</a>
""")

  # Also write tags here
  tags = _GetTags(meta)
  if tags:
    f.write('<li>Read Posts Tagged: ')
    for tag in tags:
      f.write('&nbsp;&nbsp;<span class="blog-tag"><a href="/blog/tags.html?tag=%s#%s">%s</a></span> '
          % (tag, tag, tag))
    f.write('</li>')

  f.write("""
  <li><a href="../..">Back to the Blog Index</a>
</ul>
</div>
""")


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
