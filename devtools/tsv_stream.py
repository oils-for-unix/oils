#!/usr/bin/env python2
"""
tsv_stream.py

Turn a log stream into a TSV file.

Commands:

| HEADER status elapsed_secs test test_HREF

| ROW test=asdl/format_test.py test_HREF=asdl/format_test.py.txt

| ADD status=0 elapsed_secs=0.01
  # time-tsv can emit this format


Later the header could be typed YTSV, for justification like

| HEADER (status Int, elapsed_secs Float, test Str, test_HREF Str)


"""
from __future__ import print_function

import sys


def main(argv):
  for i, line in enumerate(sys.stdin):
    if i == 0:
      print('header')

    print(line.strip())

    sys.stdout.flush()


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
