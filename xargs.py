#!/usr/bin/python2

from __future__ import print_function

import argparse
import collections
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

ArgWithInfo = collections.namedtuple('ArgWithInfo', 'arg, charc, argc, linec')

def str_memsize(*strings):
	"""Calculate the amount of memory required to store the string in an argv."""
	return sum(len(s) + 1 for s in strings)

def read_lines_eof(eof_str, input):
	"""Read lines from input until a line equals eof_str or EOF is reached"""
	eof_str = eof_str + '\n'
	return itertools.takewhile(lambda l: l != eof_str, input)

def is_complete_line(line):
	return len(line) > 1 and line[-2] not in (' ', '\t')

def argsplit_ws(lines):
	"""Split lines into arguments and append metainfo to each argument."""
	charc = 0
	argc = 0
	linec = 0
	for line in lines:
		# TODO this might require some more testing
		for arg in shlex.split(line):
			charc += str_memsize(arg)
			yield ArgWithInfo(arg, charc, argc, linec)
			argc += 1
		if is_complete_line(line):
			linec += 1

def argsplit_delim(delim, lines):
	"""Split lines into arguments and append metainfo to each argument."""
	charc = 0
	argc = 0
	linec = 0
	buf = []
	for c in itertools.chain.from_iterable(lines):
		if c == delim:
			arg = "".join(buf)
			charc += str_memsize(arg)
			yield ArgWithInfo(arg, charc, argc, linec)
			argc += 1
			linec += 1
			buf = []
		else:
			buf.append(c)
	if buf:
		arg = "".join(buf)
		charc += str_memsize(arg)
		yield ArgWithInfo(arg, charc, argc, linec)

def group_args(max_chars, max_args, max_lines, arg_iter):
	"""
	Group arguments from arg_iter, so that no group exceeds either
	max_chars, max_args or max_lines.
	"""
	def kf(a):
		return (
			(a.charc-1) / max_chars if max_chars else None,
			a.argc / max_args if max_args else None,
			a.linec / max_lines if max_lines else None,
		)
	# group args and drop meta-info
	arggroup_iter = ((m.arg for m in g) for _, g in itertools.groupby(arg_iter, kf))
	arggroup = next(arggroup_iter, None)
	yield arggroup if arggroup is not None else []
	for arggroup in arggroup_iter:
		yield arggroup

def replace_args(init_args, replace_str, add_args):
	add_args = list(add_args)
	for arg in init_args:
		if arg == replace_str:
			for x in add_args:
				yield x
		else:
			yield arg

def build_cmdline_replace(command, initial_arguments, replace_str, arggroup_iter):
	"""
	Build command-lines suitable for subprocess.Popen,
	replacing instances of replace_str in initial_arguments.
	"""
	command = [command]
	for additional_arguments in arggroup_iter:
		cmdline = itertools.chain(
			command,
			replace_args(
				initial_arguments,
				replace_str,
				additional_arguments
			)
		)
		yield cmdline

def build_cmdline(command, initial_arguments, arggroup_iter):
	"""Build command-lines suitable for subprocess.Popen."""
	command = [command]
	for additional_arguments in arggroup_iter:
		cmdline = itertools.chain(
			command,
			initial_arguments,
			additional_arguments
		)
		yield cmdline

def prompt_user(interactive, cmdline_iter):
	"""
	Go over each cmdline and print them to stderr.
	If interactive is True, prompt the user for each invocation.
	"""
	for cmdline in cmdline_iter:
		cmdline = list(cmdline)
		if interactive:
			print(*cmdline, end=' ?...', file=sys.stderr)
			with open("/dev/tty", 'r') as tty:
				response = tty.readline()
				if response[0] not in ('y', 'Y'):
					continue
		else:
			print(*cmdline, file=sys.stderr)
		yield cmdline

def map_errcode(rc):
	"""map the returncode of a child-process to the returncode of the main process."""
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
	# phase 1: read input
	if xargs_args.arg_file == '-':
		xargs_input = sys.stdin
		cmd_input = open(os.devnull, 'r')
	else:
		xargs_input = xargs_args.arg_file
		cmd_input = sys.stdin
	
	if xargs_args.eof_str:
		xargs_input = read_lines_eof(xargs_args.eof_str, xargs_input)

	# phase 2: split args
	if xargs_args.delimiter:
		arg_iter = argsplit_delim(xargs_args.delimiter, xargs_input)
	else:
		arg_iter = argsplit_ws(xargs_input)

	if xargs_args.no_run_if_empty:
		ag = next(arg_iter, None)
		if ag is None:
			return 0
		arg_iter = itertools.chain([ag], arg_iter)

	# if -I, max_chars might be 0 at this point, so check against None
	if xargs_args.max_chars is not None and xargs_args.exit:
		arg_iter = list(arg_iter)
		if arg_iter and arg_iter[-1].charc > xargs_args.max_chars:
			return 1

	# phase 3: group args
	arggroup_iter = group_args(
		xargs_args.max_chars,
		xargs_args.max_args,
		xargs_args.max_lines,
		arg_iter
	)

	# phase 4: build command-lines
	if xargs_args.replace_str:
		cmdline_iter = build_cmdline_replace(
			xargs_args.command,
			xargs_args.initial_arguments,
			xargs_args.replace_str,
			arggroup_iter
		)
	else:
		cmdline_iter = build_cmdline(
			xargs_args.command,
			xargs_args.initial_arguments,
			arggroup_iter
		)

	if xargs_args.replace_str and xargs_args.max_chars:
		cmdline = list(cmdline)
		# -I implies -x
		if str_memsize(*cmdline) > xargs_args.max_chars:
			return 1

	if xargs_args.verbose:
		cmdline_iter = prompt_user(xargs_args.interactive, cmdline_iter)

	# phase 5: execute command-lines
	err = 0
	if xargs_args.max_procs > 1:
		subprocs = []
		environ = os.environ.copy()
		for i, cmdline in enumerate(itertools.islice(cmdline_iter, xargs_args.max_procs)):
			if xargs_args.process_slot_var:
				environ[xargs_args.process_slot_var] = str(i)
			p = subprocess.Popen(cmdline, stdin=cmd_input, env=environ)
			subprocs.append(p)
		i = 0
		for cmdline in cmdline_iter:
			os.wait()
			while subprocs[i].poll() is not None:
				i = (i + 1) % len(subprocs)
			if subprocs[i].returncode:
				err = map_errcode(subprocs[i].returncode)
				break
			if xargs_args.process_slot_var:
				environ[xargs_args.process_slot_var] = str(i)
			subprocs[i] = subprocess.Popen(cmdline, stdin=cmd_input, env=environ)
		for p in subprocs:
			if not err:
				err = map_errcode(p.wait())
			else:
				p.wait()
	else:
		for cmdline in cmdline_iter:
			p = subprocess.Popen(cmdline, stdin=cmd_input)
			if p.wait():
				err = map_errcode(p.returncode)
				break
	return err

if __name__ == "__main__":
	xargs_args = xargs.parse_args()

	if xargs_args.delimiter:
		xargs_args.delimiter = xargs_args.delimiter.decode('string_escape')
		if len(xargs_args.delimiter) > 1:
			# TODO error
			sys.exit(1)
	if xargs_args.max_chars and not xargs_args.replace_str:
		base = str_memsize(xargs_args.command, *xargs_args.initial_arguments)
		if base > xargs_args.max_chars:
			# TODO error
			sys.exit(1)
		xargs_args.max_chars -= base

	# TODO warnings when appropriate
	# -d disables -e
	if xargs_args.delimiter and xargs_args.eof_str:
		xargs_args.eof_str = None
	# -I implies -L 1 (and transitively -x)
	# -I implies -d '\n'
	# TODO? -I implies -r (undocumented)
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
