#!/usr/bin/python
"""A main program for Byterun."""

import argparse
import logging

import execfile

parser = argparse.ArgumentParser(
    prog="byterun",
    description="Run Python programs with a Python bytecode interpreter.",
)
parser.add_argument(
    '-m', dest='module', action='store_true',
    help="prog is a module name, not a file name.",
)
parser.add_argument(
    '-c', dest='compiled', action='store_true',
    help="prog is a compiled .pyc file, not a .py file",
)
parser.add_argument(
    '-v', '--verbose', dest='verbose', action='store_true',
    help="trace the execution of the bytecode.",
)
parser.add_argument(
    'prog',
    help="The program to run.",
)
parser.add_argument(
    'args', nargs=argparse.REMAINDER,
    help="Arguments to pass to the program.",
)
args = parser.parse_args()

# TODO: Add option to run raw bytecode, just like the regular Python
# interpreter.
if args.compiled:
    run_fn = execfile.run_pyc_file
elif args.module:
    run_fn = execfile.run_python_module
else:
    run_fn = execfile.run_python_file

level = logging.DEBUG if args.verbose else logging.WARNING
logging.basicConfig(level=level)

argv = [args.prog] + args.args
run_fn(args.prog, argv)
