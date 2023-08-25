#!/usr/bin/env python2
"""
mycpp/examples/containers.py
"""
from __future__ import print_function

import os
from mycpp.mylib import log, NewDict, iteritems

from typing import List, Tuple, Dict, Optional


gstr = 'foo'  # type: str
glist_int = [1, 2]  # type: List[int]
glist_str = ['spam', 'eggs']  # type: List[str]

gEmptyDict = {}  # type: Dict[str, str]
gdict = {'a': 42, 'b': 43}  # type: Dict[str, int]
gdict_is = {5: 'foo', 6: 'bar', 7: 'spam'}  # type: Dict[int, str]
gdict_ss = {'foo': 'foo'}


def ListDemo():
  # type: () -> None
  intlist = []  # type: List[int]
  intlist.append(1)
  intlist.append(2)
  intlist.append(3)

  local_list = [1, 2]
  log("local_list = %d", len(local_list))

  # turned into intlist->set(1, 42)
  intlist[1] = 42
  log("len(intlist) = %d", len(intlist))

  for i in intlist:
    log("i = %d", i)

  for i in intlist[0:len(intlist):2]:
    log("stride i = %d", i)

  log('1? %d', 1 in intlist)
  log('42? %d', 42 in intlist)

  del intlist[:]
  log("len() after del = %d", len(intlist))

  strlist = []  # type: List[str]

  strlist.append('a')
  strlist.append('b')
  log("len(strlist) = %d", len(strlist))
  for s in strlist:
    log("s = %s", s)

  log('a? %d', 'a' in strlist)
  log('foo? %d', 'foo' in strlist)

  log("len(strlist) = %d", len(strlist))

  x = strlist.pop()
  log("x = %s", x)

  # repeat string
  no_str = None  # type: Optional[str]
  blank = [no_str] * 3
  log("len(blank) = %d", len(blank))


class Point(object):
  def __init__(self, x, y):
    # type: (int, int) -> None
    self.x = x
    self.y = y


def TupleDemo():
  # type: () -> None

  t2 = (3, 'hello')  # type: Tuple[int, str]

  # Destructuring
  myint, mystr = t2
  log('myint = %d', myint)
  log('mystr = %s', mystr)

  # Does this ever happen?  Or do we always use destructring?
  #log('t2[0] = %d', t2[0])
  #log('t2[1] = %s', t2[1])

  x = 3
  if x in (3, 4, 5):
    print('yes')
  else:
    print('no')

  p = Point(3, 4)
  if p.x in (3, 4, 5):
    print('yes')
  else:
    print('no')

  s = 'foo'
  if s in ('foo', 'bar'):
    print('yes')
  else:
    print('no')

  log("glist_int = %d", len(glist_int))
  log("glist_str = %d", len(glist_str))


def DictDemo():
  # type: () -> None

  # regression
  #nonempty = {'a': 'b'}  # type: Dict[str, str]

  d = {}  # type: Dict[str, int]
  d['foo'] = 42

  # TODO: implement len(Dict) and Dict::remove() and enable this
  if 0:
    log('len(d) = %d', len(d))

    del d['foo']
    log('len(d) = %d', len(d))

  # TODO: fix this
  # log("gdict = %d", len(gdict))

  ordered = NewDict()  # type: Dict[str, int]
  ordered['a'] = 10
  ordered['b'] = 11
  ordered['c'] = 12
  ordered['a'] = 50
  for k, v in iteritems(ordered):
    log("%s %d", k, v)

  # This is a proper type error
  # withargs = NewDict({'s': 42})  # type: Dict[str, int]

  log('len gEmptyDict = %d', len(gEmptyDict))
  log('len gdict = %d', len(gdict))
  log('len gdict_is = %d', len(gdict_is))
  log('len gdict_ss = %d', len(gdict_ss))

  log('gdict["a"] = %d', gdict['a'])
  log('gdict_is[5] = %s', gdict_is[5])
  log('gdict_ss["foo"] = %s', gdict_ss['foo'])

  lit = {'foo': 42, 'bar': 43}
  log('foo = %d', lit['foo'])
  if 'bar' in lit:
    log('bar is a member')


def run_tests():
  # type: () -> None

  ListDemo()
  log('')
  TupleDemo()
  log('')
  DictDemo()
  log('')


def run_benchmarks():
  # type: () -> None
  n = 1000000
  i = 0
  intlist = []  # type: List[int]
  strlist = []  # type: List[str]
  while i < n:
    intlist.append(i)
    strlist.append("foo")
    i += 1

  log('Appended %d items to 2 lists', n)


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()

# vim: sw=2
