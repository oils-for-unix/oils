#!/usr/bin/env python2
"""
optview.py
"""
from __future__ import print_function

from frontend import option_def
from frontend import match

from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
  from core.state import _ErrExit


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
    # type: (str) -> _Getter
    if opt_name in self.allowed:
      return _Getter(self.opt_array, opt_name)
      #num = match.MatchOption(opt_name)
      #return self.opt_array[num]
    else:
      raise AttributeError(opt_name)


class Parse(_View):
  def __init__(self, opt_array):
    # type: (List[bool]) -> None
    _View.__init__(self, opt_array, option_def.ParseOptNames())


class Exec(_View):
  def __init__(self, opt_array, errexit):
    # type: (List[bool], _ErrExit) -> None

    _View.__init__(self, opt_array, option_def.ExecOptNames())
    self._errexit = errexit

  def errexit(self):
    # type: () -> bool
    return self._errexit.value()
