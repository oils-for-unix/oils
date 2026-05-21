#!/usr/bin/env python2
"""
release_history.py
"""
from __future__ import print_function

import os, re, subprocess, sys, zipfile

def log(msg, *args):
  if args:
    msg = msg % args
    print('\t' + msg, file=sys.stderr)

VERSION_RE = re.compile('0\.(\d+)\.(\w+)')
HEADER=('date', 'version', 'spec_wwz', 'osh_py_path', 'osh_cpp_path', 'ysh_py_path', 'ysh_cpp_path')

def main(argv):

  print('\t'.join(HEADER))

  for release_dir in sys.stdin:
    release_dir = release_dir.strip()

    #print(release_dir)
    m = VERSION_RE.search(release_dir)
    assert m is not None

    version = m.group(0)

    p = os.path.join(release_dir, 'release-date.txt')
    with open(p) as f:
      date = f.readline().strip()

    # 0.9.3 is missing
    #print('%s\t%s' % (date, version))
    spec_wwz = os.path.join(release_dir, 'test/spec.wwz')
    if not os.path.exists(spec_wwz):
      log('No spec.wwz; skipping %s %s', date, version)
      print('\t'.join([date, version, '-', '-', '-', '-', '-']))
      continue

    with open(spec_wwz) as f:
      z = zipfile.ZipFile(f)

      osh_py_path = '-'

      p1 = 'survey/osh.html'
      try:
        z.getinfo(p1)
        osh_py_path = p1
      except KeyError:
        pass

      if osh_py_path == '-':
        p2 = 'osh-py/index.html'
        try:
          z.getinfo(p2)
          osh_py_path = p2
        except KeyError:
          pass

      if osh_py_path == '-':
        p3 = 'osh.html'
        try:
          z.getinfo(p3)
          osh_py_path = p3
        except KeyError:
          pass

      if osh_py_path == '-':
        p4 = 'index.html'
        try:
          z.getinfo(p4)
          osh_py_path = p4
        except KeyError:
          pass

      osh_cpp_path = '-'

      # 2023 Example: # https://www.oilshell.org/release/0.14.0/test/spec.wwz/cpp/osh-summary.html
      c1 = 'cpp/osh-summary.html'
      try:
        z.getinfo(c1)
        osh_cpp_path = c1
      except KeyError:
        pass

      # 2023 Example: https://www.oilshell.org/release/0.19.0/test/spec.wwz/osh-cpp/compare.html
      # TODO: the format changed
      if osh_cpp_path == '-':
        c2 = 'osh-cpp/compare.html'
        try:
          z.getinfo(c2)
          osh_cpp_path = c2
        except KeyError:
          pass

      #
      # YSH Python (formerly Oil)
      #
      ysh_py_path = '-'

      p1 = 'oil-language/oil.html'
      try:
        z.getinfo(p1)
        ysh_py_path = p1
      except KeyError:
        pass

      if ysh_py_path == '-':
        p2 = 'ysh-py/index.html'
        try:
          z.getinfo(p2)
          ysh_py_path = p2
        except KeyError:
          pass

      #
      # YSH C++
      #
      ysh_cpp_path = '-'

      c1 = 'ysh-cpp/compare.html'
      try:
        z.getinfo(c1)
        ysh_cpp_path = c1
      except KeyError:
        pass

    print('\t'.join([date, version, spec_wwz, osh_py_path, osh_cpp_path, ysh_py_path, ysh_cpp_path]))


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
