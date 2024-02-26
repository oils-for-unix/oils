#!/usr/bin/env python2
"""
test_switch.py
"""
from __future__ import print_function

import os

#from mycpp.mylib import switch, str_switch, log
from mycpp.mylib import switch, log

def TestString(s):
    # type: (str) -> None

    print('''
    with str_switch(s) as case:
        # Problem: if you switch on length, do you duplicate the bogies
        if case('spam', 'different len'):
            print('ONE')
            print('dupe')

        elif case('foo'):
            print('TWO')

        else:
            print('neither')
            ''')


def run_tests():
  # type: () -> None

  TestString('spam')
  TestString('foo')
  TestString('zzz')

  x = 5
  with switch(x) as case:
    if case(0):
      print('zero')
      print('zero')

    elif case(1, 2):
      print('one or two')

    elif case(3, 4):
      print('three or four')

    else:
      print('default')
      print('another')


def run_benchmarks():
  # type: () -> None
  raise NotImplementedError()


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
