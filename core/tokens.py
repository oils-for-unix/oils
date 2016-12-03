#!/usr/bin/env python3
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
tokens.py - Token type
"""

import json
import re

from core import id_kind
from core.base import _Node


class Token(_Node):

  # Should a token really be a PAIR of source locations?  They must all be in
  # the same file?  The "len" is basically "Compression".
  # Or do we need a flat list of tokens and use token IDs?
  # But they might not be on the same line.
  SCHEMA = """
  record Token extends Node {
    loc Ref<SourceLocation>
    val Str
  }
  """
  def __init__(self, id, val):
    _Node.__init__(self, id)
    self.val = val

    # In C++, instead of val, it will be this triple.  Change it to Val()
    # perhaps.
    # Initialize them to invalid values
    self.pool_index = -1
    self.col = -1  # zero-indexed
    self.length = -1

    # Size
    # 1 byte type (maybe, because I'm not sure if we'll have oil tokens in the
    #              same space, because they will appear in nodes)
    # 2 byte col: 64K columns
    # 1 byte length: max 256 char var name, 256 char here doc line?  hm.
    #   Well you could use the lexer to relax this
    # 4 byte pool index (4 B)
    # Or maybe 16 bytes is OK

  def __eq__(self, other):  # for unit tests
    return self.id == other.id and self.val == other.val

  def __repr__(self):
    return '<%s %s>' % (id_kind.IdName(self.id), EncodeTokenVal(self.val))

  def Val(self, pool):
    """Given a pool of lines, return the value of this token.

    NOTE: Not used right now because we haven't threaded 'pool' through
    everything.
    """
    line = pool.GetLine(self.pool_index)
    c = self.col
    return line[c : c+self.length]

  def Kind(self):
    return id_kind.LookupKind(self.id)


# This is word characters, - and _, as well as path name characters . and /.
_PLAIN_RE = re.compile(r'^[a-zA-Z0-9\-_./]+$')

def EncodeTokenVal(s):
  if '\n' in s:
    return json.dumps(s)  # account for the fact that $ matches the newline
  if _PLAIN_RE.match(s):
    return s
  else:
    return json.dumps(s)
