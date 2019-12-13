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


def uftrace_begin(ctx):
    print("program begins...")

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

    stack.append(func)
    #print("entry : " + func + "()")

def uftrace_exit(ctx):
    func = ctx["name"]
    #print("exit  : " + func + "()")
    stack.pop()

def uftrace_end():
    k = 10
    print('')
    print('List')
    for caller, count in list_callers.most_common(k):
      print('%5d %s' % (count, caller))

    print('')
    print('Str')
    for caller, count in str_callers.most_common(k):
      print('%5d %s' % (count, caller))

    print('')
    print('slice')
    for caller, count in slice_callers.most_common(k):
      print('%5d %s' % (count, caller))
