#!/usr/bin/env python2
"""
optview.py
"""
from __future__ import print_function

from frontend import option_def
from frontend import match

from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
  from osh.state import _ErrExit


class _Getter(object):

  def __init__(self, opt_array, opt_name):
    # type: (List[bool], str) -> None
    self.opt_array = opt_array
    self.num = match.MatchOption(opt_name)
    assert self.num != 0, opt_name

  def __call__(self):
    # type: () -> bool
    return self.opt_array[self.num]


class _View(object):
  """Allow read-only access to a subset of options."""

  def __init__(self, opt_array, allowed):
    # type: (List[bool], List[str]) -> None
    self.opt_array = opt_array
    self.allowed = allowed

  def __getattr__(self, opt_name):
    # type: (str) -> bool

    # TODO: Could exclude parse options here?
    if opt_name in self.allowed:
      #return _Getter(self.opt_array, name)
      num = match.MatchOption(opt_name)
      return self.opt_array[num]
    else:
      raise AttributeError(opt_name)


class Parse(_View):
  def __init__(self, opt_array):
    # type: (List[bool]) -> None
    _View.__init__(self, opt_array, option_def.PARSE_OPTION_NAMES)


class Exec(_View):
  def __init__(self, opt_array, errexit):
    # type: (List[bool], _ErrExit) -> None

    # Excludes parse options
    allowed = option_def.SET_OPTION_NAMES + option_def.SHOPT_OPTION_NAMES
    _View.__init__(self, opt_array, allowed)
    self._errexit = errexit

  def errexit(self):
    # type: () -> bool
    return self._errexit.errexit

  def GetDollarHyphen(self):
    # type: () -> str
    chars = []  # type: List[str]
    if self.interactive:
      chars.append('i')

    if self.errexit():
      chars.append('e')
    if self.nounset:
      chars.append('u')
    # NO letter for pipefail?
    if self.xtrace:
      chars.append('x')
    if self.noexec:
      chars.append('n')

    # bash has:
    # - c for sh -c, i for sh -i (mksh also has this)
    # - h for hashing (mksh also has this)
    # - B for brace expansion
    return ''.join(chars)
