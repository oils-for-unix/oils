"""
module1.py
"""
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
  def __init__(self, color):
    # type: (str) -> None
    self.color = color

  def Speak(self):
    # type: () -> None
    log('%s cat: meow', self.color)
