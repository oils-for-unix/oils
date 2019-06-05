"""
module1.py
"""
from runtime import log

def func1():
  # type: () -> None
  log('func1')


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
