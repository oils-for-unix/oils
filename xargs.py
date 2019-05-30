#!/usr/bin/python2

from __future__ import print_function

import argparse
import itertools
import os
# TODO docs.python.org suggests https://pypi.org/project/subprocess32/
#      for POSIX users
import shlex
import subprocess
import sys

xargs = argparse.ArgumentParser(prog='xargs')
xargs.add_argument('-a', '--arg-file', metavar='file', nargs=1, default='-', help='read arguments from FILE, not standard input')
xargs.add_argument('-E', metavar='eof-str', dest='eof_str', help='set logical EOF string; if END occurs as a line of input, the rest of the input is ignored (ignored if -0 or -d was specified)')
xargs.add_argument('-e', '--eof', metavar='eof-str', nargs='?', dest='eof_str', help='equivalent to -E END if END is specified; otherwise, there is no end-of-file string')
xargs.add_argument('-0', '--null', dest='delimiter', action='store_const', const='\0', help='items are separated by a null, not whitespace; disables quote and backslash processing and logical EOF processing')
xargs.add_argument('-d', '--delimiter', metavar='delimiter', dest='delimiter', help='items in input stream are separated by CHARACTER, not by whitespace; disables quote and backslash processing and logical EOF processing')
xargs.add_argument('-I', metavar='replace-str', dest='replace_str', help='same as --replace=R')
xargs.add_argument('-i', '--replace', metavar='replace-str', nargs='?', const='{}', dest='replace_str', help='replace R in INITIAL-ARGS with names read from standard input; if R is unspecified, assume {}')
xargs.add_argument('-L', metavar='max-lines', dest='max_lines', type=int, help='use at most MAX-LINES non-blank input lines per command line')
xargs.add_argument('-l', '--max-lines', metavar='max-lines', nargs='?', const=1, dest='max_lines', type=int, help='similar to -L but defaults to at most one non-blank input line if MAX-LINES is not specified')
xargs.add_argument('-n', '--max-args', metavar='max-args', dest='max_args', type=int, help='use at most MAX-ARGS arguments per command line')
xargs.add_argument('-s', '--max-chars', metavar='max-chars', dest='max_chars', type=int, help='limit length of command line to MAX-CHARS')
xargs.add_argument('-P', '--max-procs', metavar='max-procs', default=1, dest='max_procs', type=int, help='run at most MAX-PROCS processes at a time')
xargs.add_argument('--process-slot-var', metavar='name', help='set environment variable VAR in child processes')
xargs.add_argument('-p', '--interactive', action='store_true', help='prompt before running commands')
xargs.add_argument('-t', '--verbose', action='store_true', help='print commands before executing them')
xargs.add_argument('-x', '--exit', action='store_true', help='exit if the size (see -s) is exceeded')
xargs.add_argument('-r', '--no-run-if-empty', action='store_true', help='if there are no arguments, then do not run COMMAND; if this option is not given, COMMAND will be run at least once')
xargs.add_argument('--show-limits', action='store_true', help='show limits on command-line length')
xargs.add_argument('--version', action='version', version='%(prog)s 0.0.1', help='output version information and exit')
xargs.add_argument('command', nargs='?', default='echo')
xargs.add_argument('initial_arguments', nargs=argparse.REMAINDER)

def read_lines_eof(eof_str, input):
	eof_str = eof_str + '\n'
	return itertools.takewhile(lambda l: l != eof_str, input)

def is_complete_line(line):
	return len(line) > 1 and line[-2] not in (' ', '\t')

def argsmeta_ws(lines):
	argc = 0
	linec = 0
	charc = 0
	for line in lines:
		# TODO this might require some more testing
		for arg in shlex.split(line):
			charc += str_memsize(arg)
			yield arg, argc, linec, charc
			argc += 1
		if is_complete_line(line):
			linec += 1

def argsmeta_delim(lines, delim):
	argc = 0
	linec = 0
	charc = 0
	buf = []
	for c in itertools.chain.from_iterable(lines):
		if c == delim:
			arg = "".join(buf)
			charc += str_memsize(arg)
			yield arg, argc, linec, charc
			argc += 1
			linec += 1
			buf = []
		else:
			buf.append(c)
	if buf:
		arg = "".join(buf)
		charc += str_memsize(arg)
		yield arg, argc, linec, charc

def replace_args(init_args, replace_str, add_args):
	add_args = list(add_args)
	for arg in init_args:
		if arg == replace_str:
			for x in add_args:
				yield x
		else:
			yield arg

def str_memsize(*strings):
	return sum(len(s) + 1 for s in strings)

def gen_args_keyfunc(xargs_args):
	base = str_memsize(xargs_args.command, *xargs_args.initial_arguments)
	def kf(a):
		return (
			a[1] / xargs_args.max_args if xargs_args.max_args else None,
			a[2] / xargs_args.max_lines if xargs_args.max_lines else None,
			(a[3]-1) / (xargs_args.max_chars-base) if xargs_args.max_chars else None,
		)
	return kf

def map_errcode(rc):
	if rc == 0:
		return 0
	if rc >= 0 and rc <= 125:
		return 123
	if rc == 255:
		return 124
	if rc < 0:
		return 125
	return 1

def main(xargs_args):
	if xargs_args.arg_file == '-':
		xargs_input = sys.stdin
		cmd_input = open(os.devnull, 'r')
	else:
		xargs_input = xargs_args.arg_file
		cmd_input = sys.stdin
	
	if xargs_args.eof_str:
		xargs_input = read_lines_eof(xargs_args.eof_str, xargs_input)

	if xargs_args.delimiter:
		arg_iter = argsmeta_delim(line_iter, xargs_args.delimiter)
	else:
		arg_iter = argsmeta_ws(line_iter)

	if xargs_args.max_chars and xargs_args.exit:
		base = str_memsize(xargs_args.command, *xargs_args.initial_arguments)
		arg_iter = list(arg_iter)
		if arg_iter and arg_iter[-1][3] > (xargs_args.max_chars - base):
			return 1

	subprocs = []
	for _, g in itertools.groupby(arg_iter, gen_args_keyfunc(xargs_args)):
		additional_arguments = [m[0] for m in g]
		if xargs_args.no_run_if_empty and not additional_arguments:
			return 0

		if xargs_args.replace_str:
			cmdline = itertools.chain(
				[xargs_args.command],
				replace_args(
					xargs_args.initial_arguments,
					xargs_args.replace_str,
					additional_arguments
				)
			)
			# max-chars implies exit
			if xargs_args.max_chars:
				cmdline = list(cmdline)
				if str_memsize(*cmdline) > xargs_args.max_chars:
					return 1
		else:
			cmdline = itertools.chain(
				[xargs_args.command],
				xargs_args.initial_arguments,
				additional_arguments
			)

		if xargs_args.verbose:
			cmdline = list(cmdline)
			print(*cmdline, end=' ', file=sys.stderr)
			if xargs_args.interactive:
				with open("/dev/tty", 'r') as tty:
					print("?...", end='', file=sys.stderr)
					response = tty.readline()
					if response[0] != 'y' and response[0] != 'Y':
						continue
			else:
				print(file=sys.stderr)
		try:
			subprocs.append(subprocess.Popen(cmdline, stdin=cmd_input))
		except OSError:
			# 126	command cannot be run
			# 127	command cannot be found
			return 127

		if xargs_args.max_procs and xargs_args.max_procs > len(subprocs):
			continue

		os.wait()
		for i in reversed(range(len(subprocs))):
			if subprocs[i].poll() is None:
				continue
			err = map_errcode(subprocs[i].returncode)
			if err:
				return err
			del subprocs[i]
	return 0

if __name__ == "__main__":
	xargs_args = xargs.parse_args()

	if xargs_args.delimiter:
		xargs_args.delimiter = xargs_args.delimiter.decode('string_escape')
		if len(xargs_args.delimiter) > 1:
			# TODO error
			sys.exit(1)

	# TODO warnings when appropriate
	# -d disables -e
	if xargs_args.delimiter and xargs_args.eof_str:
		xargs_args.eof_str = None
	# -I implies -L 1 (and transitively -x)
	# -I implies -d '\n'
	if xargs_args.replace_str and xargs_args.max_lines != 1:
		xargs_args.max_lines = 1
		xargs_args.delimiter = '\n'
	# -L implies -x
	if xargs_args.max_lines is not None and not xargs_args.exit:
		xargs_args.exit = True
	# -p implies -t
	if xargs_args.interactive and not xargs_args.verbose:
		xargs_args.verbose = True
	# TODO? if -d then -L equals -n

	sys.exit(main(xargs_args))
