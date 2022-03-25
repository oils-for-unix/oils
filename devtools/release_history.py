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
HEADER=('date', 'version', 'spec_wwz', 'survey_path', 'cpp_summary_path')

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
      print('\t'.join([date, version, '-', '-', '-']))
      continue

    with open(spec_wwz) as f:
      z = zipfile.ZipFile(f)

      survey_path = '-'

      p1 = 'survey/osh.html'
      try:
        z.getinfo(p1)
        survey_path = p1
      except KeyError:
        pass

      if survey_path == '-':
        p2 = 'osh.html'
        try:
          z.getinfo(p2)
          survey_path = p2
        except KeyError:
          pass

      if survey_path == '-':
        p3 = 'index.html'
        try:
          z.getinfo(p3)
          survey_path = p3
        except KeyError:
          pass

      cpp_summary_path = 'cpp/osh-summary.html'
      try:
        h2 = z.getinfo(cpp_summary_path)
      except KeyError:
        cpp_summary_path = '-'

    print('\t'.join([date, version, spec_wwz, survey_path, cpp_summary_path]))


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
