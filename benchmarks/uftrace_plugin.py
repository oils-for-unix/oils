#!/usr/bin/env python2
"""
uftrace_plugin.py
"""
from __future__ import print_function

import collections

stack = []
list_callers = collections.Counter()
str_callers = collections.Counter()
slice_callers = collections.Counter()
t2_callers = collections.Counter()
t3_callers = collections.Counter()
t4_callers = collections.Counter()
new_callers = collections.Counter()
malloc_callers = collections.Counter()


def uftrace_begin(ctx):
  pass

def uftrace_entry(ctx):
  # TODO: When function is List::List, get the STACK
  func = ctx["name"]

  if func == 'List::List':
    list_callers[stack[-1]] += 1
    #print('STACK %s' % stack)
  elif func == 'Str::Str':
    str_callers[stack[-1]] += 1
  elif func == 'Str::slice':
    slice_callers[stack[-1]] += 1
  elif func == 'Tuple2::Tuple2':
    t2_callers[stack[-1]] += 1
  elif func == 'Tuple3::Tuple3':
    t3_callers[stack[-1]] += 1
  elif func == 'Tuple4::Tuple4':
    t4_callers[stack[-1]] += 1
  elif func == 'operator new':
    new_callers[stack[-1]] += 1
  elif func == 'malloc':
    malloc_callers[stack[-1]] += 1

  stack.append(func)
  #print("entry : " + func + "()")

def uftrace_exit(ctx):
  func = ctx["name"]
  #print("exit  : " + func + "()")
  stack.pop()


def PrintMostCommon(c, k):
  total = sum(c.values())
  for caller, count in c.most_common(k):
    percent = count * 100.0 / total
    print('%5.2f%% %5d %s' % (percent, count, caller))
  print('         ...')
  print('       %5d TOTAL' % total)


def uftrace_end():
  k = 10
  print('')
  print('List')
  PrintMostCommon(list_callers, k)

  print('')
  print('Str')
  PrintMostCommon(str_callers, k)

  print('')
  print('slice')
  PrintMostCommon(slice_callers, k)

  print('')
  print('Tuple2')
  PrintMostCommon(t2_callers, k)

  print('')
  print('Tuple3')
  PrintMostCommon(t3_callers, k)

  print('')
  print('Tuple4')
  PrintMostCommon(t4_callers, k)

  print('')
  print('operator new')
  PrintMostCommon(new_callers, k)

  print('')
  print('malloc')
  PrintMostCommon(malloc_callers, k)
