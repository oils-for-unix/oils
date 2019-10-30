#!/usr/bin/env python2
"""
doc_html.py
"""
from __future__ import print_function

import cgi
import sys


CSS_FMT = '<link rel="stylesheet" type="text/css" href="%s" />\n'

def Header(meta, f):
  css_files = [x for x in meta['css_files'].split() if x]

  meta['css_links'] = ''.join(CSS_FMT % url for url in css_files)

  # CSS links are NOT escaped
  meta['title'] = cgi.escape(meta['title'])

  f.write('''\
<!DOCTYPE html>
<html>
  <head>
    <title>%(title)s</title>
    %(css_links)s
  </head>
  <body>
    <p id="home-link">
      <a href="https://github.com/oilshell/oil/blob/master/%(repo_url)s" id="source-link">source</a> |
      <a href="%(all_docs_url)s">all docs</a>
        for <span id="version-in-header">version %(oil_version)s</span> |
      <a href="/">oilshell.org</a>
    </p>
''' % meta)


def Footer(meta, f):
  f.write('''\
    <hr/>
    <i>Generated on %(build_timestamp)s</i>
  </body>
</html>
''' % meta)
