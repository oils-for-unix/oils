#!/usr/bin/env python2
"""
gc_stats_to_tsv.py

Turn a set of files with OILS_GC_STATS output into a TSV file.
"""
from __future__ import print_function

import collections
import os
import sys


def main(argv):
    header = None

    for path in argv[1:]:
        filename = os.path.basename(path)
        join_id, _ = os.path.splitext(filename)

        d = collections.OrderedDict()

        d["join_id"] = join_id

        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip().replace(" ", "_")
                value = value.strip()
                d[key] = value

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
