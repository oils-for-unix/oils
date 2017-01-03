#!/usr/bin/env python3
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
tokens.py - Old token functions
"""

import json
import re


# TODO: This should be moved to asdl/format.py, for printing strings.

# This is word characters, - and _, as well as path name characters . and /.
_PLAIN_RE = re.compile(r'^[a-zA-Z0-9\-_./]+$')

def EncodeTokenVal(s):
  if '\n' in s:
    return json.dumps(s)  # account for the fact that $ matches the newline
  if _PLAIN_RE.match(s):
    return s
  else:
    return json.dumps(s)


# NOTE: Not used right now.
def SpanValue(span, pool):
  """Given an line_span and a pool of lines, return the string value.
  """
  line = pool.GetLine(span.pool_index)
  c = span.col
  return line[c : c + span.length]


def TokensEqual(left, right):
  # Ignoring location in CompoundObj.__eq__ now, but we might want this later.
  #return left.id == right.id and left.val == right.val
  return left == right


def TokenWordsEqual(left, right):
  # Ignoring location in CompoundObj.__eq__ now, but we might want this later.
  #return TokensEqual(left.token, right.token)
  return left == right
