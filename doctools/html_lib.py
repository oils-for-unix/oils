#!/usr/bin/env python2
"""
html_lib.py

Shared between HTML processors.

TODO: Write a "pull parser" API!
"""
from __future__ import print_function

import cgi


def AttrsToString(attrs):
  if not attrs:
    return ''

  # Important: there's a leading space here.
  # TODO: Change href="$help:command" to href="help.html#command"
  return ''.join(' %s="%s"' % (k, cgi.escape(v)) for (k, v) in attrs)
