#!/usr/bin/env python2
from __future__ import print_function
"""
class_vs_closure.py

TODO: These should be implemented the same way in the interpreter loop?

Closure is implemented with:

- pyobj.Function.func_closure

Class is implemented with type(), and then the constructor creates a namespace
with __dict__ and so forth.  Access through 'self'.  LOAD_FAST self, where self
is a local variable.

There was one language that made it explicit.  Skew lanaguage?


# {} is for static language of types/data.  : is for language of
# code/algorithms.

class Adder1 {
  init(self.amount):  # auto-init
    pass

  call(x):
    return x + self.amount
}

func Adder2(amount) {
  return func(x) {   # function literal
    # outer means that the variable is captured lexically?
    return x + outer::amount
  }
}

# Shortcut
class Adder1 is Object (self.amount Int) {
  call(x Int):
    return x + self.amount
}

"""

import sys


class Adder1(object):
  def __init__(self, amount):
    self.amount = amount

  def __call__(self, x):
    return x + self.amount


# This one uses a LOAD_CLOSURE bytecode; the other one doesn't.
def Adder2(amount):
  def anon(x):
    return x + amount
  return anon


def main(argv):
  a1 = Adder1(1)
  a2 = Adder2(1)

  print(a1(42))
  print(a2(42))


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
