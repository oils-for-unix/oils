#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
from __future__ import print_function
"""
id_kind_gen.py - Code generation for id_kind.py.
"""

import sys

from asdl.visitor import FormatLines
from osh.meta import Id, Kind, LookupKind, ID_SPEC


def Emit(s, f, depth=0):
  for line in FormatLines(s, depth):
    f.write(line)


def GenCppCode(kind_names, id_names, f, id_labels=None, kind_labels=None):
  """
  Args:
    kind_names: List of kind name strings, in display order
    id_names: List of list of id name strings, in display order
    f: output file
    id_labels: optional name to integer
    kind_labels: optional name to integer
  """
  Emit('#include <cstdint>', f)
  #Emit('#include "stdio.h"', f)
  Emit('', f)
  Emit('enum class Kind : uint8_t {', f)
  if kind_labels:
    s = ', '.join(['%s=%s' % (k, kind_labels[k]) for k in kind_names]) + ','
    Emit(s, f, 1)
  else:
    Emit(', '.join(kind_names), f, 1)
  Emit('};\n', f)

  Emit('enum class Id : uint8_t {', f)
  for names_in_kind in id_names:
    if id_labels:
      s = ', '.join(['%s=%s' % (i, id_labels[i]) for i in names_in_kind]) + ','
      Emit(s, f, 1)
    else:
      Emit(', '.join(names_in_kind) + ',', f, 1)
    Emit('', f)

  Emit('};\n', f)

  if 0:  # Test for blog post
    f.write(r"""
  Kind LookupKind(Id id) {
    int i = static_cast<int>(id);
    int k = 175 & i & ((i ^ 173) + 11);
    return static_cast<Kind>(k);
  }

  int main() {
  """)
    for names_in_kind in id_names:
      if id_labels:
        for id_name in names_in_kind:
          kind_name = id_name.split('_')[0]
          test = (
              'if (LookupKind(Id::%s) != Kind::%s) return 1;' %
              (id_name, kind_name))
          Emit(test, f, 1)
      else:
        pass
      Emit('', f)

    f.write(r"""
    printf("PASSED\n");
    return 0;
  }
  """)

def main(argv):
  try:
    action = argv[1]
  except IndexError:
    raise RuntimeError('Action required')

  if action == 'c':
    ids = list(ID_SPEC.token_names.iteritems())
    ids.sort(key=lambda pair: pair[0])  # Sort by ID
    for i, name in ids:
      print('#define id__%s %s' % (name, i))

  elif action == 'cpp':
    # For blog post
    try:
      labels = argv[2]
    except IndexError:
      label_lines = []
    else:
      with open(labels) as f:
        label_lines = f.readlines()
     
    from collections import defaultdict

    id_by_kind_index = defaultdict(list)  # Kind name -> [list of Id names]
    for name in dir(Id):
      if name[0].isupper():
        id_ = getattr(Id, name)
        kind_index = LookupKind(id_)
        id_by_kind_index[kind_index].append(name)

    kinds = []
    for name in dir(Kind):
      if name[0].isupper():
        kind_index = getattr(Kind, name)
        #print(kind, name)
        kinds.append((name, kind_index, len(id_by_kind_index[kind_index])))

    # Sort descending by length of ID list
    kinds = sorted(kinds, key=lambda p: p[2], reverse=True)

    id_labels = {}  # Id name -> integer
    kind_labels = {}  # Kind name -> integer

    for k, line in enumerate(label_lines):  # descending order by kind size

      parts = line.split()
      id_list_len, _, actual_len, _, kind_label, _ = parts[:6]
      id_list_len = int(id_list_len)
      kind_label = int(kind_label)
      id_list = [int(id_) for id_ in parts[6:]]

      try:
        kind_name, kind_index, len_id_list = kinds[k]
      except IndexError:
        break
      kind_labels[kind_name] = kind_label

      id_names = id_by_kind_index[kind_index]
      #print(id_names)
      for i, name in enumerate(id_names):
        try:
          id_labels[name] = id_list[i]
        except IndexError:
          raise RuntimeError('%s %s' % (name, i))

    if 0:  # disable labeling
      id_labels = None
      kind_labels = None

    kind_names = [k[0] for k in kinds]

    id_names = []
    for _, kind_index, _ in kinds:
      n = id_by_kind_index[kind_index]
      id_names.append(n)

    GenCppCode(kind_names, id_names, sys.stdout,
               id_labels=id_labels, kind_labels=kind_labels)

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
