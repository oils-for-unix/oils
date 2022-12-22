"""
uftrace_allocs.py - Python 3 plugin for uftrace

Count allocations and show sizes.

Annoying thing about uftrace: it swallows ImportError and other errors!

TODO:
  Attribute allocations and sizes to Str, List, Dict, Token, etc.
  How do we do that?  We need the call graph relationship

Structures to catch:

NewStr(12) {
  MarkSweepHeap::Allocate(25)
}

Alloc() {
  MarkSweepHeap::Allocate(24);
  syntax_asdl::Token::Token();
}

Alloc() {
  MarkSweepHeap::Allocate(24)
  List::List()
  # But what type is it?  We don't know
}

// Some stuff missing here
Alloc() {
  MarkSweepHeap::Allocate(32);
  Alloc() {
    MarkSweepHeap::Allocate(24);
    List::List();
  }
}
"""
import collections
import os
import sys


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


num_allocs = 0
num_lists = 0

gOutDir = None

class Stats(object):

  def __init__(self, out_dir):
    p = os.path.join(out_dir, 'strings.tsv')
    self.strings = open(p, 'w')
    header = ['func_name', 'str_len']
    print('\t'.join(header), file=self.strings)

    p = os.path.join(out_dir, 'allocs.tsv')
    self.allocs = open(p, 'w')
    header = ['obj_len']
    print('\t'.join(header), file=self.allocs)

  def EmitString(self, func, str_len):
    print('%s\t%d' % (func, str_len), file=self.strings)

  def EmitAlloc(self, obj_len):
    print('%d' % (obj_len), file=self.allocs)

  def Close(self):
    self.strings.close()


gStats = None


def uftrace_begin(ctx):
  """Script begin"""

  #print(ctx)
  args = ctx['cmds']
  log('args %r', args)
  out_dir = args[0]

  global gStats
  gStats = Stats(out_dir)


def uftrace_entry(ctx):
  """Function entry"""
  global num_allocs

  func_name = ctx["name"]

  #print(ctx)

  if func_name == 'List::List':
    num_lists += 1

  # Get string size is available here
  if func_name in ('NewStr', 'OverAllocatedStr'):
    str_len = ctx['args'][0]
    gStats.EmitString(func_name, str_len)

  if func_name == 'MarkSweepHeap::Allocate':
    num_bytes = ctx['args'][0]
    gStats.EmitAlloc(num_bytes)
    num_allocs += 1


def uftrace_exit(ctx):
  """Function exit"""
  pass


def uftrace_end():
  log('num MarkSweepHeap::Allocate() = %d', num_allocs)

  gStats.Close()

  #print('zz', file=sys.stderr)

#print('hi')
