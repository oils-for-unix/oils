#!/usr/bin/env python2
from __future__ import print_function

import pickle
import sys


class Base(object):
  def __init__(self, n):
    # IMPORTANT: The pickle has instructions to make
    # self.__dict__ = {'n': # 10042}.
    # It doesn't call the constructor or redo this computation.
    self.n = n + 43

# Note: There are no runtime instructions for inheritance in pickle.
class Foo(Base):

  def __init__(self, n):
    Base.__init__(self, n)
    # look what happens when there are nested objects
    # the graph is walked
    self.m1 = Base(99)
    #self.m2 = Base(99)

  def __repr__(self):
    return '<Foo %d>' % self.n

f = Foo(10000)
print(f)

i = pickle.dumps(f, protocol=pickle.HIGHEST_PROTOCOL)
c = pickle.dumps(Foo, protocol=pickle.HIGHEST_PROTOCOL)
print(len(i))  # 101 in protocol 0, 36 in protocol 2
print(len(c))  # 18 bytes in portocl 0, 19 in protocol 2

print(repr(i))
print(repr(c))


with open(sys.argv[1], 'w') as f:
  f.write(i)
