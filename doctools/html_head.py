#!/usr/bin/env python2
"""
html_head.py: Emit <html><head> boilerplate.

And make sure it works on mobile!

Note: this file is also run with python3, by the Soil CI, because outside
containers we don't have python2.
"""
from __future__ import print_function

import sys
try:
  import html
except ImportError:
  import cgi as html  # only for cgi.escape -> html.escape
try:
  import cStringIO
except ImportError:
  cStringIO = None
  import io
import optparse

from doctools import doc_html


# Python library.  Also see doctools/doc_html.py.
def Write(f, title, css_urls=None, js_urls=None):
  css_urls = css_urls or []
  js_urls = js_urls or []

  # Note: do lang=en and charset=utf8 matter?  I guess if goes to a different
  # web server?
  f.write('''\
<!DOCTYPE html>
<html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>%s</title>
''' % html.escape(title))

  # Write CSS files first I guess?

  for url in css_urls:
    f.write(doc_html.CSS_FMT % html.escape(url))

  for url in js_urls:
    f.write(doc_html.JS_FMT % html.escape(url))

  f.write('''\
  </head>
''')


  # Not used now
def HtmlHead(title, css_urls=None, js_urls=None):
  if cStringIO:
    f = cStringIO.StringIO()
  else:
    f = io.BytesIO()
  Write(f, title, css_urls=css_urls, js_urls=js_urls)
  return f.getvalue()


def main(argv):
  p = optparse.OptionParser('html_head.py FLAGS? CSS_JS*')
  p.add_option(
      '-t', '--title', dest='title', default='',
      help='The title of the web page')
  opts, argv = p.parse_args(argv[1:])

  # Make it easier to use from shell scripts
  css_urls = []
  js_urls = []
  for arg in argv:
    i = arg.rfind('?')  # account for query param
    if i != -1:
      url = arg[:i]
    else:
      url = arg

    if url.endswith('.js'):
      js_urls.append(arg)
    elif url.endswith('.css'):
      css_urls.append(arg)
    else:
      raise RuntimeError("Expected URL with .js or .css, got %r" % arg)

  Write(sys.stdout, opts.title, css_urls=css_urls, js_urls=js_urls)



if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
