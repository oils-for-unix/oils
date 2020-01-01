#!/usr/bin/env python2
"""
doc_html.py
"""
from __future__ import print_function

import cgi
import sys

# Used by html_head.py
JS_FMT = '<script type="text/javascript" src="%s"></script>\n'

CSS_FMT = '<link rel="stylesheet" type="text/css" href="%s" />\n'

def Header(meta, f):
  css_files = [x for x in meta['css_files'].split() if x]

  meta['css_links'] = ''.join(CSS_FMT % url for url in css_files)

  # CSS links are NOT escaped
  meta['title'] = cgi.escape(meta['title'])

  # NOTE: 'meta viewport' so it's not small on mobile browsers
  f.write('''\
<!DOCTYPE html>
<html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>%(title)s</title>
    %(css_links)s
  </head>
  <body class="%(body_css_class)s">
    <p id="home-link">
''' % meta)

  compact_title = meta.get('compact_title')
  if compact_title:
    f.write('''\
<span id="compact-title">%(title)s</span>
''' % meta)

  f.write('''\
      <a href="https://github.com/oilshell/oil/blob/master/%(repo_url)s" id="source-link">source</a> |
''' % meta)

  if meta.get('all_docs_url') != '-':
    f.write('''\
      <a href="%(all_docs_url)s">all docs</a>
        for <span id="version-in-header">version %(oil_version)s</span> |
''' % meta)
  elif meta.get('version_url') != '-':
    # The doc/ URL needs to go back
    f.write('''\
      <a href="..">version %(oil_version)s</a> |
''' % meta)

  f.write('''\
      <a href="/releases.html">all versions</a> |
      <a href="/">oilshell.org</a>
    </p>
''' % meta)

  if 'in_progress' in meta:
    f.write('''\
        <p style="background-color: mistyrose; font-size: large;
                  text-align: center; padding: 1em;">

      <b>Warning: Work in progress!</b>  Leave feedback on <a
      href="https://oilshell.zulipchat.com">Zulip</a> or <a
      href="https://github.com/oilshell/oil/issues">Github</a> if you'd like
      this doc to be updated.
    </p>
''')


def Footer(meta, f):
  f.write('''\
    <hr/>
    <div id="build-timestamp"><i>Generated on %(build_timestamp)s</i></div>
  </body>
</html>
''' % meta)
