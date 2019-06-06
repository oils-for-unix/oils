#!/usr/bin/python2
# Copyright 2019 Wilke Schwiedop. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0

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

class GNUXargsQuirks(argparse.Action):
	def __init__(self, option_strings, dest, **kwargs):
		super(GNUXargsQuirks, self).__init__(option_strings, dest, **kwargs)
	def __call__(self, parser, namespace, values, option_string=None):
		setattr(namespace, self.dest, values)
		if self.dest == 'replace_str':
			namespace.max_args = None
			namespace.max_lines = None
		elif self.dest == 'max_lines':
			namespace.max_args = None
			namespace.replace_str = None
		elif self.dest == 'max_args':
			namespace.max_lines = None
			if namespace.max_args == 1 and namespace.replace_str:
				namespace.max_args = None
			else:
				namespace.replace_str = None
		elif self.dest == 'max_chars':
			pass
		else:
			assert False, "dest '%s' not handled" % self.dest

xargs = argparse.ArgumentParser(prog='xargs')
xargs.add_argument('-a', '--arg-file', metavar='file', nargs=1, default='-', help='read arguments from FILE, not standard input')
xargs.add_argument('-E', metavar='eof-str', dest='eof_str', help='set logical EOF string; if END occurs as a line of input, the rest of the input is ignored (ignored if -0 or -d was specified)')
xargs.add_argument('-e', '--eof', metavar='eof-str', nargs='?', dest='eof_str', help='equivalent to -E END if END is specified; otherwise, there is no end-of-file string')
xargs.add_argument('-0', '--null', dest='delimiter', action='store_const', const='\0', help='items are separated by a null, not whitespace; disables quote and backslash processing and logical EOF processing')
xargs.add_argument('-d', '--delimiter', metavar='delimiter', dest='delimiter', help='items in input stream are separated by CHARACTER, not by whitespace; disables quote and backslash processing and logical EOF processing')
xargs.add_argument('-I', metavar='replace-str', dest='replace_str', action=GNUXargsQuirks, help='same as --replace=R')
xargs.add_argument('-i', '--replace', metavar='replace-str', nargs='?', const='{}', dest='replace_str', action=GNUXargsQuirks, help='replace R in INITIAL-ARGS with names read from standard input; if R is unspecified, assume {}')
xargs.add_argument('-L', metavar='max-lines', dest='max_lines', type=int, action=GNUXargsQuirks, help='use at most MAX-LINES non-blank input lines per command line')
xargs.add_argument('-l', '--max-lines', metavar='max-lines', nargs='?', const=1, dest='max_lines', type=int, action=GNUXargsQuirks, help='similar to -L but defaults to at most one non-blank input line if MAX-LINES is not specified')
xargs.add_argument('-n', '--max-args', metavar='max-args', dest='max_args', type=int, action=GNUXargsQuirks, help='use at most MAX-ARGS arguments per command line')
xargs.add_argument('-s', '--max-chars', metavar='max-chars', dest='max_chars', type=int, action=GNUXargsQuirks, help='limit length of command line to MAX-CHARS')
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

class PeekableIterator():
	def __init__(self, iterator):
		self.iterator = iterator
		self.peeked = False
		self.item = None
	def peek(self):
		"""
		Return the next item but does not advance the iterator further.
		Raise StopIteration if there is no such item.
		"""
		if not self.peeked:
			self.item = next(self.iterator)
			self.peeked = True
		return self.item
	def next(self):
		"""
		Return the next item and advance the iterator.
		Raise StopIteration if there is no such item.
		"""
		if self.peeked:
			self.peeked = False
			return self.item
		return next(self.iterator)
	def __iter__(self):
		return self

def read_lines_eof(eof_str, input):
	# type (str, Iterable[str]) -> Iterable[str]
	"""Read lines from input until a line equals eof_str or EOF is reached"""
	return iter(input.next, eof_str + '\n')

def str_memsize(*strings):
	# type: (*str) -> int
	"""Calculate the amount of memory required to store the strings in an argv."""
	return sum(len(s) + 1 for s in strings)

def is_complete_line(line):
	# type: (str) -> bool
	return len(line) > 1 and line[-2] not in (' ', '\t')

def argsplit_ws(lines):
	# type: (Iterable[str]) -> Iterator[str]
	"""Split lines into arguments and append metainfo to each argument."""
	for line in lines:
		# TODO this might require some more testing
		for arg in shlex.split(line):
			yield arg

def argsplit_delim(delim, lines):
	# type: (str, Iterable[str]) -> Iterator[str]
	"""Split lines into arguments and append metainfo to each argument."""
	buf = []
	for c in itertools.chain.from_iterable(lines):
		if c == delim:
			yield "".join(buf)
			buf = []
		else:
			buf.append(c)
	if buf:
		yield "".join(buf)

def read_n_xargs_lines(linec, line_iter):
	# type: (int, Iterator[str]) -> Iterator[str]
	while linec > 0:
		line = next(line_iter)
		yield line
		if is_complete_line(line):
			linec -= 1

def take_chars(charc, iterator):
	# type: (int, Iterator[str]) -> Iterator[str]
	charc -= str_memsize(iterator.peek())
	while charc >= 0:
		yield next(iterator)
		charc -= str_memsize(iterator.peek())

def take(n, iterator):
	# type: (int, Iterator[Any]) -> Iterator[Any]
	for _ in range(n):
		yield next(iterator)

def group_args_lines(max_lines, input):
	# type: (int, Iterator[str]) -> Iterator[List[str]]
	while True:
		it = argsplit_ws(read_n_xargs_lines(max_lines, input))
		buf = [next(it)] # raise StopIteration if iterator is empty
		buf.extend(it)
		yield buf

def group_args(max_chars, max_args, arg_iter):
	# type: (Optional[int], Optional[int], Iterator[str]) -> Iterator[List[str]]
	arg_iter = PeekableIterator(arg_iter)
	while arg_iter.peek() or True: # raise StopIteration if iterator is empty
		it = arg_iter
		if max_chars:
			it = take_chars(max_chars, it)
		if max_args:
			it = take(max_args, it)
		yield list(it)

def replace_args(initial_arguments, replace_str, additional_arguments):
	# type: (Sequence[str], str, Iterable[str]) -> Iterator[str]
	additional_arguments = list(additional_arguments)
	for arg in initial_arguments:
		if arg == replace_str:
			for x in additional_arguments:
				yield x
		else:
			yield arg

def build_cmdlines_replace(command, initial_arguments, replace_str, arggroup_iter):
	# type: (str, Sequence[str], str, Iterator[Iterator[str]]) -> Iterator[List[str]]
	"""
	Build command-lines suitable for subprocess.Popen,
	replacing instances of replace_str in initial_arguments.
	"""
	cmdline = [command]
	for additional_arguments in arggroup_iter:
		cmdline.extend(
			replace_args(
				initial_arguments,
				replace_str,
				additional_arguments
			)
		)
		yield cmdline
		cmdline = cmdline[:1]

def build_cmdlines(command, initial_arguments, arggroup_iter):
	# type: (str, Sequence[str], Iterator[Iterator[str]]) -> Iterator[List[str]]
	"""Build command-lines suitable for subprocess.Popen."""
	cmdline = [command]
	cmdline.extend(initial_arguments)
	for additional_arguments in arggroup_iter:
		cmdline.extend(additional_arguments)
		yield cmdline
		cmdline = cmdline[:1+len(initial_arguments)]

def check_items(p, on_false, cmdline_iter):
	for cmdline in cmdline_iter:
		if p(cmdline):
			yield cmdline
		else:
			on_false()

def tee_cmdline(cmdline_iter):
	# type: (Iterator[List[str]]) -> Iterator[List[str]]
	"""Go over each cmdline and print them to stderr."""
	for cmdline in cmdline_iter:
		print(*cmdline, file=sys.stderr)
		yield cmdline

def prompt_user(cmdline_iter):
	# type: (Iterator[List[str]]) -> Iterator[List[str]]
	"""Prompt the user for each cmdline."""
	with open("/dev/tty", 'r') as tty:
		for cmdline in cmdline_iter:
			print(*cmdline, end=' ?...', file=sys.stderr)
			response = tty.readline()
			if response[0] not in ('y', 'Y'):
				continue
			yield cmdline

def wait_open_slot(processes):
	# type: (List[Optional[Any]])-> int
	while processes:
		for i, p in enumerate(processes):
			# process doesn't yet exist or has finished
			if p is None or p.poll() is not None:
				return i
		_pid, _err = os.wait()

def map_errcode(rc):
	# type: int -> int
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

	# phase 2: parse and group args
	if xargs_args.max_lines:
		assert not xargs_args.max_args
		assert not xargs_args.delimiter
		assert xargs_args.exit
		arggroup_iter = group_args_lines(xargs_args.max_lines, xargs_input)
	else:
		if xargs_args.delimiter:
			arg_iter = argsplit_delim(xargs_args.delimiter, xargs_input)
		else:
			arg_iter = argsplit_ws(xargs_input)
		# if exit is True, max_chars is checked later
		arggroup_iter = group_args(
			xargs_args.max_chars if not xargs_args.exit else None,
			xargs_args.max_args,
			arg_iter
		)

	arggroup_iter = PeekableIterator(arggroup_iter)
	if xargs_args.no_run_if_empty:
		try:
			x = arggroup_iter.peek()
			# TODO not even sure how the interaction with -I is supposed to work
			# echo   | xargs -I {} echo {}		: dont run
			# echo   | xargs -I {} echo {} "x"	: dont run
			# echo   | xargs -I {} echo    "x"	: dont run
			# echo x | xargs -I {} echo 		: run
			# echo xx | xargs -I {} -d 'x' echo {}	: run 3 times ('', '', '\n')

#			if not x or not x[0]:
			if not x:
				return 0
		except StopIteration:
			return 0
	else:
		try:
			arggroup_iter.peek()
		except StopIteration:
			arggroup_iter = [[]]

	# phase 3: build command-lines
	if xargs_args.replace_str:
		cmdline_iter = build_cmdlines_replace(
			xargs_args.command,
			xargs_args.initial_arguments,
			xargs_args.replace_str,
			arggroup_iter
		)
	else:
		cmdline_iter = build_cmdlines(
			xargs_args.command,
			xargs_args.initial_arguments,
			arggroup_iter
		)

	if xargs_args.max_chars is not None and xargs_args.exit:
		cmdline_iter = check_items(
			lambda c: str_memsize(*c) < xargs_args.max_chars,
			lambda: sys.exit(1),
			cmdline_iter
		)

	if xargs_args.interactive:
		cmdline_iter = prompt_user(cmdline_iter)
	elif xargs_args.verbose:
		cmdline_iter = tee_cmdline(cmdline_iter)

	# phase 4: execute command-lines
	if xargs_args.max_procs > 1:
		ps = [None] * xargs_args.max_procs
		environ = os.environ.copy()
		for cmdline in cmdline_iter:
			i = wait_open_slot(ps)
			if ps[i] is not None and ps[i].returncode:
				break
			if xargs_args.process_slot_var:
				environ[xargs_args.process_slot_var] = str(i)
			ps[i] = subprocess.Popen(cmdline, stdin=cmd_input, env=environ)
		return max(map_errcode(p.wait()) for p in ps if p is not None)
	else:
		for cmdline in cmdline_iter:
			p = subprocess.Popen(cmdline, stdin=cmd_input)
			if p.wait():
				return map_errcode(p.returncode)
	return 0

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
	if xargs_args.replace_str and xargs_args.max_lines != 1:
		xargs_args.max_lines = 1
	# -I implies -d '\n'
	if xargs_args.replace_str and xargs_args.delimiter != '\n':
		xargs_args.delimiter = '\n'
	# -L implies -x
	if xargs_args.max_lines is not None and not xargs_args.exit:
		xargs_args.exit = True
	# -p implies -t
	if xargs_args.interactive and not xargs_args.verbose:
		xargs_args.verbose = True

	# (undocumented)
	# if -d then -L equals -n
	if xargs_args.delimiter and xargs_args.max_lines:
		xargs_args.max_args = xargs_args.max_lines
		xargs_args.max_lines = None
	# TODO? -I implies -r
	if xargs_args.replace_str and not xargs_args.no_run_if_empty:
		xargs_args.no_run_if_empty = True

	sys.exit(main(xargs_args))
