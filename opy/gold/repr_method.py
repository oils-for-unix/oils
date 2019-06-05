#!/usr/bin/env python2
from __future__ import print_function


class Foo(object):
  def __init__(self, n):
    self.n = n

  def __repr__(self):
    return '<Foo %d>' % self.n


f = Foo(10000)
print(f)
