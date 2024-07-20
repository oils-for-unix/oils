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
from __future__ import print_function

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
        p = os.path.join(out_dir, 'all-untyped.tsv')
        self.untyped = open(p, 'w')
        header = ['obj_len']
        print('\t'.join(header), file=self.untyped)

        p = os.path.join(out_dir, 'typed.tsv')
        self.typed = open(p, 'w')
        header = ['func_name']
        print('\t'.join(header), file=self.typed)

        p = os.path.join(out_dir, 'strings.tsv')
        self.strings = open(p, 'w')
        header = ['func_name', 'str_len']
        print('\t'.join(header), file=self.strings)

        # Note: we could extract Slab type
        p = os.path.join(out_dir, 'slabs.tsv')
        self.slabs = open(p, 'w')
        header = ['func_name', 'slab_len']
        print('\t'.join(header), file=self.slabs)

        # For the actual number of items
        p = os.path.join(out_dir, 'reserve.tsv')
        self.reserve = open(p, 'w')
        header = ['func_name', 'num_items']
        print('\t'.join(header), file=self.reserve)

    def EmitUntyped(self, obj_len):
        print('%d' % (obj_len), file=self.untyped)

    def EmitTyped(self, func):
        print('%s' % (func), file=self.typed)

    def EmitString(self, func, str_len):
        print('%s\t%d' % (func, str_len), file=self.strings)

    def EmitSlab(self, func, slab_len):
        print('%s\t%d' % (func, slab_len), file=self.slabs)

    def EmitReserve(self, func, num_items):
        print('%s\t%d' % (func, num_items), file=self.reserve)

    def Close(self):
        self.untyped.close()
        self.typed.close()
        self.strings.close()
        self.slabs.close()
        self.reserve.close()


gStats = None


def uftrace_begin(ctx):
    """Script begin"""

    #print(ctx)
    args = ctx['cmds']
    #log('args %r', args)
    out_dir = args[0]

    global gStats
    gStats = Stats(out_dir)


def uftrace_entry(ctx):
    """Function entry"""
    global num_allocs

    func_name = ctx["name"]

    #print(ctx)
    #log('f %r', func_name)

    if func_name.startswith('MarkSweepHeap::Allocate'):
        #log("MSW !!")
        num_bytes = ctx['args'][0]
        #log("MSW %r %s", num_bytes, type(num_bytes))
        gStats.EmitUntyped(num_bytes)
        num_allocs += 1
        return

    if 'Alloc<' in func_name:
        # TODO: We don't have the size
        gStats.EmitTyped(func_name)
        return

    if func_name.startswith('NewStr') or func_name.startswith(
            'OverAllocatedStr'):
        #log("Str")
        str_len = ctx['args'][0]
        #log("Str %d", str_len)
        gStats.EmitString(func_name, str_len)
        return

    if 'NewSlab<' in func_name:
        #log('SLAB %r', func_name)
        slab_len = ctx['args'][0]
        #log('len %d', slab_len)
        gStats.EmitSlab(func_name, slab_len)
        return

    if '::reserve(' in func_name:
        num_items = ctx['args'][0]
        gStats.EmitReserve(func_name, num_items)
        return


def uftrace_exit(ctx):
    """Function exit"""
    pass


def uftrace_end():
    log('num MarkSweepHeap::Allocate() = %d', num_allocs)

    gStats.Close()

    #print('zz', file=sys.stderr)


#print('hi')
