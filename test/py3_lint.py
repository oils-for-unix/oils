#!/usr/bin/env python3
"""
py3_lint.py - pyflakes can run in both modes
"""

import sys

from test import py2_lint

if __name__ == '__main__':
    try:
        sys.exit(py2_lint.main(sys.argv[1:]))
    except KeyboardInterrupt as e:
        print('%s: interrupted with Ctrl-C' % sys.argv[0], file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
