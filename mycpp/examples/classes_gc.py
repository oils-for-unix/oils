#!/usr/bin/env python2
"""
classes_gc.py - Test out field masks
"""
from __future__ import print_function

import os

from mycpp import mylib
from mycpp.mylib import log

from typing import List, Dict


class Opaque(object):

  def __init__(self):
    # type: () -> None
    self.i = 0


class OpaqueBase(object):

  def __init__(self):
    # type: () -> None
    self.j = 0


class OpaqueDerived(OpaqueBase):

  def __init__(self):
    # type: () -> None
    OpaqueBase.__init__(self)
    self.k = 0


class Pointers(object):

  def __init__(self):
    # type: () -> None

    # Make sure fields are sorted!
    self.i = 0
    self.s = 'S'
    self.j = 42
    self.t = 'T'


class PointersBase(object):

  def __init__(self):
    # type: () -> None
    self.i = 0
    self.s = 'S'


class PointersDerived(PointersBase):

  def __init__(self):
    # type: () -> None
    PointersBase.__init__(self)
    self.j = 42
    self.t = 'T'


class BaseWithMethod(object):

  def __init__(self):
    # type: () -> None
    self.i = 0
    self.s = 'S'

  def Method(self):
    # type: () -> int
    return 42


class DerivedWithMethod(BaseWithMethod):

  def __init__(self):
    # type: () -> None
    BaseWithMethod.__init__(self)
    self.j = 42
    self.t = 'T'
    self.u = 'U'

  def Method(self):
    # type: () -> int
    return 99


#
# Regression for off-by-one bug in Tag::Scanned
#

class WithDict(object):
  def __init__(self):
    # type: () -> None
    self.s = 'foo'
    self.d = {}  # type: Dict[str, str]



#
# Regression for printf bug -- Tag::Opaque
#

class _Builtin(object):
  def __init__(self):
    # type: () -> None
    pass

  def Run(self):
    # type: () -> None
    print('_Builtin')


class Printf(_Builtin):
  def __init__(self):
    # type: () -> None
    _Builtin.__init__(self)
    self.cache = {}  # type: Dict[str, str]

  def Run(self):
    # type: () -> None
    print('Printf')



def run_tests():
  # type: () -> None

  o1 = Opaque()
  o2 = OpaqueBase()
  o3 = OpaqueDerived()

  p1 = Pointers()
  p2 = PointersBase()
  p3 = PointersDerived()

  m1 = BaseWithMethod()
  m2 = DerivedWithMethod()

  # Reproduce bug found in osh_eval with IfsSplitter and the dict splitter

  c = WithDict()
  c.d['key'] = 'value'

  mylib.MaybeCollect()

  s = 'heap'
  p1.s = s[1:]  # why do we need this to trigger the bug
  # Does not trigger it
  #p1.s = s

  #p1.t = s[2:]
  print(c.d['key'])

  # Reproduce printf bug
  p = Printf()
  mylib.MaybeCollect()

  log("cache length %d", len(p.cache))


def run_benchmarks():
  # type: () -> None

  # Use some memory to test the size of these objects

  op = []  # type: List[OpaqueBase]
  p = []  # type: List[PointersBase]
  m = []  # type: List[BaseWithMethod]

  for i in xrange(1000):
    o1 = Opaque()
    o2 = OpaqueBase()
    o3 = OpaqueDerived()

    op.append(o2)
    op.append(o3)

    p1 = Pointers()

    p2 = PointersBase()
    p3 = PointersDerived()

    p.append(p2)
    p.append(p3)

    m1 = BaseWithMethod()
    m2 = DerivedWithMethod()

    m.append(m1)
    m.append(m2)

    mylib.MaybeCollect()

  log('len(op) = %d', len(op))
  log('len(p) = %d', len(p))
  log('len(m) = %d', len(m))


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
