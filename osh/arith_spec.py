#!/usr/bin/env python2
"""
arith_spec.py
"""
from __future__ import print_function

from osh import arith_parse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from frontend.tdop import ParserSpec

_SPEC = arith_parse.MakeShellSpec()

def Spec():
  # type: () -> ParserSpec
  return _SPEC
