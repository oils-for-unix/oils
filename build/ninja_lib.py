#!/usr/bin/env python2
"""
ninja_lib.py
"""
from __future__ import print_function

import os


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def ObjPath(src_path, compiler, variant):
  rel_path, _ = os.path.splitext(src_path)
  return '_build/obj/%s-%s/%s.o' % (compiler, variant, rel_path)


def asdl_cpp(n, asdl_path, pretty_print_methods=True):
  # to create _gen/mycpp/examples/expr.asdl.h
  prefix = '_gen/%s' % asdl_path

  if pretty_print_methods:
    outputs = [prefix + '.cc', prefix + '.h']
    asdl_flags = '' 
  else:
    outputs = [prefix + '.h']
    asdl_flags = '--no-pretty-print-methods'

  debug_mod = '%s_debug.py' % prefix 
  outputs.append(debug_mod)

  # NOTE: Generating syntax_asdl.h does NOT depend on hnode_asdl.h, but
  # COMPILING anything that #includes it does.  That is handled elsewhere.

  n.build(outputs, 'asdl-cpp', asdl_path,
          implicit=['_bin/shwrap/asdl_main'],
          variables=[
            ('action', 'cpp'),
            ('out_prefix', prefix),
            ('asdl_flags', asdl_flags),
            ('debug_mod', debug_mod),
          ])
  n.newline()
