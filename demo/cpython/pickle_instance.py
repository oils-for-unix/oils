#!/usr/bin/env python3
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


def PickleInstance(protocol, out_f):
  f = Foo(10000)
  print(f)

  i = pickle.dumps(f, protocol=protocol)
  c = pickle.dumps(Foo, protocol=protocol)

  print(len(i))  # 101 in protocol 0, 36 in protocol 2
  print(len(c))  # 18 bytes in portocl 0, 19 in protocol 2

  print(repr(i))
  print(repr(c))


  out_f.write(i)


def PickleData(protocol, out_f):
  d = {'key': 'str', 'k2': ['value1', 42, False], 'bool': True, 'float': 0.1}

  # Test out GRAPH
  d['self'] = d

  i = pickle.dumps(d, protocol=protocol)

  out_f.write(i)



def main(argv):

  action = argv[1]
  protocol = int(argv[2])
  out_path = argv[3]

  if action == 'instance':
    with open(out_path, 'wb') as f:
      PickleInstance(protocol, f)

  elif action == 'pure-data':
    with open(out_path, 'wb') as f:
      PickleData(protocol, f)

  else:
    raise RuntimeError(action)


main(sys.argv)

