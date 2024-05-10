"""
module1.py
"""
from __future__ import print_function

import mylib
from mylib import log
from testpkg import module2

CONST1 = 'CONST module1'


def func1():
  # type: () -> None
  log('func1')
  log(module2.CONST2)


def fortytwo():
  # type: () -> int
  return 42


class Cat(object):

  def __init__(self):
    # type: () -> None
    """Empty constructor for mycpp."""
    pass

  def Speak(self):
    # type: () -> None
    log('cat')

  def ThingThatCollects(self):
    # type: () -> None
    mylib.MaybeCollect()

  def AbstractMethod(self):
    # type: () -> None
    raise NotImplementedError()


def does_collect(s):
    # type: (str) -> None
    print(s)
    module2.func3()
