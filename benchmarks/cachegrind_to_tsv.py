#!/usr/bin/env python2
"""
cachegrind_to_tsv.py

Turn a set of stdout of valgrind --tool=cachegrind into a TSV file.
"""
from __future__ import print_function

import collections
import os
import re
import sys

EXTRACT_RE = re.compile(r'I[ ]*refs:[ ]*([\d,]+)')


def main(argv):
    header = None

    for path in argv[1:]:
        filename = os.path.basename(path)
        join_id, _ = os.path.splitext(filename)

        d = collections.OrderedDict()

        d['join_id'] = join_id

        with open(path) as f:
            contents = f.read()
        m = EXTRACT_RE.search(contents)
        if not m:
            raise RuntimeError('Expected I refs')

        irefs = m.group(1).replace(',', '')

        d['irefs'] = irefs

        if header is None:
            header = d.keys()
            print("\t".join(header))
        else:
            # Ensure the order
            assert d.keys() == header

        row = d.values()
        print("\t".join(row))


if __name__ == '__main__':
    try:
        main(sys.argv)
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
