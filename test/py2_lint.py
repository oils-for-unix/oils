#!/usr/bin/env python2
from __future__ import print_function
"""
Our wrapper around pyflakes 2.4.0.

Newer versions dropped support for Python 2.

All versions: https://pypi.org/simple/pyflakes/

Change log: https://github.com/PyCQA/pyflakes/blob/main/NEWS.rst
"""

import argparse
import sys

from pyflakes import api
from pyflakes import reporter

from core import ansi

# Our config for flake8
# local fatal_errors='E901,E999,F821,F822,F823,F401'

# From flake8/src/flake8/plugins/pyflakes.py
# "RaiseNotImplemented": "F901",
# "UndefinedName": "F821",
# "UndefinedLocal": "F823",
# "UnusedImport": "F401",

FATAL_CLASS_NAMES = [
    "RaiseNotImplemented",
    "UndefinedName",
    "UndefinedLocal",
    "UnusedImport",
]

# Other useful ones
# "RedefinedWhileUnused": "F811",


class OilsReporter(reporter.Reporter):

    def __init__(self):
        # Warnings and errors both go to stdout
        reporter.Reporter.__init__(self, sys.stdout, sys.stdout)
        self.num_fatal_errors = 0

    def flake(self, message):
        """
        pyflakes found something wrong with the code.

        @param: A L{pyflakes.messages.Message}.
        """
        type_name = type(message).__name__

        # Suppress some errors for now to reducenoise
        if type_name == 'UnusedVariable':
            if message.filename.endswith('_test.py'):
                return

            var_name = message.message_args[0]
            if var_name == 'e':
                return
            if var_name.startswith('unused'):
                return

        if type_name in FATAL_CLASS_NAMES:
            self.num_fatal_errors += 1
            self._stdout.write(ansi.RED + ansi.BOLD)
            self._stdout.write(str(message))
            self._stdout.write(ansi.RESET)
        else:
            self._stdout.write(str(message))

        self._stdout.write('\n')


def main(args):
    parser = argparse.ArgumentParser(
        prog=None, description='Check Python source files for errors')
    #parser.add_argument('-V', '--version', action='version', version=_get_version())
    parser.add_argument(
        'path',
        nargs='*',
        help='Path(s) of Python file(s) to check. STDIN if not given.')
    paths = parser.parse_args(args).path

    rep = OilsReporter()

    api.checkRecursive(paths, rep)
    return 0 if rep.num_fatal_errors == 0 else 1


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt as e:
        print('%s: interrupted with Ctrl-C' % sys.argv[0], file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
