#!/usr/bin/env python2
"""
html_lib.py

Shared between HTML processors.

TODO: Write a "pull parser" API!
"""
from __future__ import print_function

import cgi
import re


def AttrsToString(attrs):
  if not attrs:
    return ''

  # Important: there's a leading space here.
  # TODO: Change href="$help:command" to href="help.html#command"
  return ''.join(' %s="%s"' % (k, cgi.escape(v)) for (k, v) in attrs)


def PrettyHref(s, preserve_anchor_case=False):
  """
  Turn arbitrary heading text into a clickable href with no special characters.

  This is modelled after what github does.  It makes everything lower case.
  """
  # Split by whitespace or hyphen
  words = re.split(r'[\s\-]+', s)

  # Keep only alphanumeric
  keep = [''.join(re.findall(r'\w+', w)) for w in words]

  # Join with - and lowercase.  And then remove empty words, unlike Github.
  # This is SIMILAR to what Github does, but there's no need to be 100%
  # compatible.

  pretty = '-'.join(p for p in keep if p)
  if not preserve_anchor_case:
    pretty = pretty.lower()
  return pretty
