#!/usr/bin/env python2
"""html_lib.py.

Shared between HTML processors.

TODO: Write a "pull parser" API!
"""
from __future__ import print_function

import cgi
import re
from typing import List


def AttrsToString(attrs):
    # type: (List) -> str
    if not attrs:
        return ''

    # Important: there's a leading space here.
    # TODO: Change href="$help:command" to href="help.html#command"
    return ''.join(' %s="%s"' % (k, cgi.escape(v)) for (k, v) in attrs)


def PrettyHref(s, preserve_anchor_case=False):
    # type: (str, bool) -> str
    """Turn arbitrary heading text into href with no special characters.

    This is modeled after what github does.  It makes everything lower case.
    """
    # Split by whitespace or hyphen
    words = re.split(r'[\s\-]+', s)

    if preserve_anchor_case:
        # doc/ref: Keep only alphanumeric and /, for List/append, cmd/append
        # Note that "preserve_anchor_case" could be renamed
        keep_re = r'[\w/]+'
    else:
        # Keep only alphanumeric
        keep_re = r'\w+'

    keep = [''.join(re.findall(keep_re, w)) for w in words]

    # Join with - and lowercase.  And then remove empty words, unlike Github.
    # This is SIMILAR to what Github does, but there's no need to be 100%
    # compatible.

    pretty = '-'.join(p for p in keep if p)
    if not preserve_anchor_case:
        pretty = pretty.lower()
    return pretty
