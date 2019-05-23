#!/usr/bin/python2

from __future__ import print_function

import argparse
import os
# TODO docs.python.org suggests https://pypi.org/project/subprocess32/
#      for POSIX users
import subprocess
import sys

# Note: -s trumps -n
xargs = argparse.ArgumentParser(prog='xargs')
xargs.add_argument('-a', '--arg-file', nargs=1, default='-', metavar='file')
xargs.add_argument('-E',          dest='eof_str', metavar='eof-str')
xargs.add_argument('-e', '--eof', dest='eof_str', metavar='eof-str', nargs='?')
xargs.add_argument('-0', '--null',      dest='delimiter', action='store_const', const='\0')
xargs.add_argument('-d', '--delimiter', dest='delimiter', metavar='delimiter')
xargs.add_argument('-I',              dest='replace_str', metavar='replace-str')
xargs.add_argument('-i', '--replace', dest='replace_str', metavar='replace-str', nargs='?', const='{}')
xargs.add_argument('-L',                dest='max_lines', metavar='max-lines')
xargs.add_argument('-l', '--max-lines', dest='max_lines', metavar='max-lines', nargs='?', const=1)
xargs.add_argument('-n', '--max-args', metavar='max-args')
xargs.add_argument('-s', '--max-chars', metavar='max-chars')
xargs.add_argument('-P', '--max-procs', metavar='max-procs', default=1)
xargs.add_argument('--process-slot-var', metavar='name')
xargs.add_argument('-p', '--interactive', action='store_true')
xargs.add_argument('-t', '--verbose', action='store_true')
xargs.add_argument('-x', '--exit', action='store_true')
xargs.add_argument('-r', '--no-run-if-empty', action='store_true')
xargs.add_argument('--show-limits', action='store_true')
xargs.add_argument('command', nargs='?', default='/bin/echo')
xargs.add_argument('initial_arguments', nargs=argparse.REMAINDER)

xargs_args = xargs.parse_args()

# TODO warnings when appropriate
# -d disables -e
if xargs_args.delimiter and xargs_args.eof_str:
	xargs_args.eof_str = None
# -I implies -L 1 (and transitively -x)
if xargs_args.replace_str and xargs_args.max_lines != 1:
	xargs_args.max_lines = 1
# -L implies -x
if xargs_args.max_lines is not None and not xargs_args.exit:
	xargs_args.exit = True
# -p implies -t
if xargs_args.interactive and not xargs_args.verbose:
	xargs_args.verbose = True

### DEBUGGING ###
#print(xargs_args, file=sys.stderr)
#print("ENABLING -t", file=sys.stderr)
#xargs_args.verbose = True

def read_lines_eof(arg_file, eof_str):
	eof_str = eof_str + '\n'
	for line in arg_file:
		if line == eof_str:
			return
		yield line

# TODO xargs does quoting (' and ")
def read_args_whitespace(lines):
	for line in lines:
		for arg in line.split():
			yield arg
def read_args_delim(lines, delim):
	buf = []
	for line in lines:
		for c in line:
			if c != delim:
				buf += c
			else:
				yield "".join(buf)
				buf = []

def main():
	if xargs_args.arg_file == '-':
		xargs_input = sys.stdin
		cmd_input = open(os.devnull, 'r')
	else:
		xargs_input = xargs_args.arg_file
		cmd_input = sys.stdin
	
	if xargs_args.eof_str:
		line_iter = read_lines_eof(xargs_input, xargs_args.eof_str)
	else:
		line_iter = xargs_input
		
	if xargs_args.delimiter:
		d = xargs_args.delimiter.decode('string_escape')
		if len(d) > 1:
			# TODO error
			return 1
		arg_iter = read_args_delim(line_iter, d)
	else:
		arg_iter = read_args_whitespace(line_iter)

	additional_arguments = [x for x in arg_iter]

	if xargs_args.no_run_if_empty and not additional_arguments:
		return 0

	cmdline = [xargs_args.command] + xargs_args.initial_arguments
	cmdline.extend(additional_arguments)

	if xargs_args.verbose:
		print(*cmdline, file=sys.stderr)
		# if interactive read from /dev/tty
		# set tty CLOEXEC
		# tty = open("/dev/tty", 'r')
	try:
		p = subprocess.Popen(cmdline, stdin=cmd_input)
	except OSError:
		# 126	command cannot be run
		# 127	command cannot be found
		return 127
	p.wait()

	if p.returncode == 0:
		return 0
	if p.returncode >= 0 and p.returncode <= 125:
		return 123
	if p.returncode == 255:
		return 124
	if p.returncode < 0:
		return 125
	return 1

sys.exit(main())

# TODO
# done?	Feature
# [x]	-a --arg-file
# [x]	-E -e --eof
# [x]	-0 --null
# [x]	-d --delimiter
# [ ]	-I -i --replace
# [ ]	-L -l --max-lines
# [ ]	-n --max-args
# [ ]	-s --max-chars
# [ ]	-P --max-procs
# [ ]	--process-slot-var
# [ ]	-p --interactive
# [x]	-t --verbose
# [ ]	-x --exit
# [x]	-r --no-run-if-empty
# [ ]	--show-limits
