#!/usr/bin/env python2
"""doc_html.py."""
from __future__ import print_function

import cgi

# Used by html_head.py
JS_FMT = '<script type="text/javascript" src="%s"></script>\n'

CSS_FMT = '<link rel="stylesheet" type="text/css" href="%s" />\n'


def Header(meta, f, draft_warning=False):
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
      <span id="why-sponsor"><a href="/why-sponsor.html">Why Sponsor Oils?</a></span> |
      <a href="https://github.com/oilshell/oil/blob/master/%(repo_url)s" id="source-link">source</a> |
''' % meta)

    if meta.get('all_docs_url') != '-':
        f.write('''\
      <span id="all-docs"><a href="%(all_docs_url)s">all docs</a>
        for <span id="version-in-header">version %(oil_version)s</span></span> |
''' % meta)
    elif meta.get('version_url') != '-':
        # The doc/ URL needs to go back
        f.write('''\
      <a href="..">version %(oil_version)s</a> |
''' % meta)

    f.write('''\
      <a href="/releases.html">all versions</a> |
      <a href="/">oilshell.org</a>
''' % meta)

    if draft_warning:
        f.write('''\
      <span id="draft-warning" style="visibility: hidden;"></span>

      <script type="text/javascript">
      function showWarning(el) {
        el.innerHTML = '<br/>This is a DRAFT.  Latest docs are at <a href="/release/latest/doc/">/release/latest/doc/</a> ';
        el.style.visibility = "visible";
      }
      function removeVersion(el) {
        el.innerHTML = '<a href=".">drafts</a>';
      }

      var url = window.location.href;
      if (url.indexOf('/preview/') === -1) {
        console.log("Not a draft");
      } else {
        showWarning(document.querySelector('#draft-warning'));
        removeVersion(document.querySelector('#all-docs'));
      }
      </script>
''')

    f.write('</p>')

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
    <div id="build-timestamp">
      <i>Generated on %(build_timestamp)s</i>
    </div>
  </body>
</html>
''' % meta)
