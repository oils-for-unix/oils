#!/usr/bin/python
"""
modules.py
"""
from __future__ import print_function

import os
from mylib import log

from testpkg import module1
from testpkg.module2 import func2


def run_tests():
  # type: () -> None
  module1.func1()
  func2()

  dog = Dog('white')
  dog.Speak()

  cat = module1.Cat()
  cat.Speak()

  cat2 = Sphinx('brown')
  cat2.Speak()

  # Test inheritance
  cat = cat2
  cat.Speak()

  cat.AbstractMethod()


def run_benchmarks():
  # type: () -> None
  i = 0
  n = 2000000
  result = 0
  while i < n:
    result += module1.fortytwo()
    i = i + 1
  log('result = %d', result)


# This is at the bottom to detect order.
class Dog(object):
  def __init__(self, color):
    # type: (str) -> None
    self.color = color

  def Speak(self):
    # type: () -> None
    log('%s dog: meow', self.color)


class Sphinx(module1.Cat):

  def __init__(self, color):
    # type: (str) -> None
    #module1.Cat.__init__(self)
    self.color = color

  def Speak(self):
    # type: () -> None
    log('%s sphinx', self.color)

  def AbstractMethod(self):
    # type: () -> None
    log('abstract')


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
