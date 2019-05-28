#!/usr/bin/python2

from __future__ import print_function

import argparse
import itertools
import os
# TODO docs.python.org suggests https://pypi.org/project/subprocess32/
#      for POSIX users
import subprocess
import sys

xargs = argparse.ArgumentParser(prog='xargs')
xargs.add_argument('-a', '--arg-file', nargs=1, default='-', metavar='file')
xargs.add_argument('-E',          dest='eof_str', metavar='eof-str')
xargs.add_argument('-e', '--eof', dest='eof_str', metavar='eof-str', nargs='?')
xargs.add_argument('-0', '--null',      dest='delimiter', action='store_const', const='\0')
xargs.add_argument('-d', '--delimiter', dest='delimiter', metavar='delimiter')
xargs.add_argument('-I',              dest='replace_str', metavar='replace-str')
xargs.add_argument('-i', '--replace', dest='replace_str', metavar='replace-str', nargs='?', const='{}')
xargs.add_argument('-L',                dest='max_lines', type=int, metavar='max-lines')
xargs.add_argument('-l', '--max-lines', dest='max_lines', type=int, metavar='max-lines', nargs='?', const=1)
xargs.add_argument('-n', '--max-args',  dest='max_args',  type=int, metavar='max-args')
xargs.add_argument('-s', '--max-chars', dest='max_chars', type=int, metavar='max-chars')
xargs.add_argument('-P', '--max-procs', dest='max_procs', type=int, metavar='max-procs', default=1)
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
# -I implies -d '\n'
if xargs_args.replace_str and xargs_args.max_lines != 1:
	xargs_args.max_lines = 1
	xargs_args.delimiter = r'\n'
# -L implies -x
if xargs_args.max_lines is not None and not xargs_args.exit:
	xargs_args.exit = True
# -p implies -t
if xargs_args.interactive and not xargs_args.verbose:
	xargs_args.verbose = True
# TODO? if -d then -L equals -n

def read_lines_eof(arg_file, eof_str):
	eof_str = eof_str + '\n'
	return itertools.takewhile(lambda l: l != eof_str, arg_file)

def is_complete_line(line):
	return len(line) > 1 and line[-2] not in (' ', '\t')

def argsmeta_ws(lines):
	argc = 0
	linec = 0
	charc = 0
	for line in lines:
		# TODO xargs does quoting (' and ")
		for arg in line.split():
			charc += len(arg) + 1
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
			charc += len(arg) + 1
			yield arg, argc, linec, charc
			argc += 1
			linec += 1
			buf = []
		else:
			buf += c
	if buf:
		arg = "".join(buf)
		charc += len(arg) + 1
		yield arg, argc, linec, charc

def replace_args(init_args, replace_str, add_args):
	add_args = list(add_args)
	for arg in init_args:
		if arg == replace_str:
			for x in add_args:
				yield x
		else:
			yield arg

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
		arg_iter = argsmeta_delim(line_iter, d)
	else:
		arg_iter = argsmeta_ws(line_iter)

	def kf(a):
		# TODO max_chars must consider command + initial_arguments
		return (
			a[1] / xargs_args.max_args if xargs_args.max_args else None,
			a[2] / xargs_args.max_lines if xargs_args.max_lines else None,
			a[3] / xargs_args.max_chars if xargs_args.max_chars else None,
		)
	subprocs = []
	for k, g in itertools.groupby(arg_iter, kf):
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
		else:
			cmdline = itertools.chain(
				[xargs_args.command],
				xargs_args.initial_arguments,
				additional_arguments
			)

		if xargs_args.verbose:
			cmdline = list(cmdline)
			print(*cmdline, file=sys.stderr)
			# if interactive read from /dev/tty
			# set tty CLOEXEC
			# tty = open("/dev/tty", 'r')
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
	### DEBUGGING ###
	#print(xargs_args, file=sys.stderr)
	#print("ENABLING -t", file=sys.stderr)
	#xargs_args.verbose = True
	sys.exit(main())

# TODO
# done?	Feature
# [x]	-a --arg-file
# [x]	-E -e --eof
# [x]	-0 --null
# [x]	-d --delimiter
# [x]	-I -i --replace
# [x]	-L -l --max-lines
# [x]	-n --max-args
# [ ]	-s --max-chars
# [x]	-P --max-procs
# [ ]	--process-slot-var
# [ ]	-p --interactive
# [x]	-t --verbose
# [ ]	-x --exit
# [x]	-r --no-run-if-empty
# [ ]	--show-limits
