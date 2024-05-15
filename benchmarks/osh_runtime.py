#!/usr/bin/env python2
"""
osh_runtime.py

Extract and merge results from benchmarks/osh-runtime.sh test-oils-run

Structure:

  http://travis-ci.oilshell.org/uuu/osh-runtime/
    git-96d96a16/
      2024-05-08__16-11-59.andy-VirtualBox.wwz/
        osh-runtime/
          raw/
            times.tsv
            provenance.tsv

      2024-05-08__...

    git-1a.../
      ...
  
Steps:

1. Use zipfile module to extract TSV
2. Merge times.tsv and provenance.tsv
   - clean up sh_path issue -- use sh_label
3. Concatenate all them into one TSV
   - devtools/tsv_concat.py

Optionally use web/table/tsv2html 

But really we want a web spreadsheet that will load this big denormalized file.

Then we want to

- Select say 5 rows for LEFT
- Select say 5 rows for RIGHT

Average the times, maybe throw out outliers

Then show diff as VERTICAL table.

Dimensions that can be compared:

- bash vs. osh, or bash vs. dash
- osh version 1 vs. 2
- machine 1 vs. machine 2
- Linux vs OS X
"""
from __future__ import print_function

import sys


def main(argv):
  print('Hello from osh_runtime.py')


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
