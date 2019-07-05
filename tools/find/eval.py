# Copyright 2019 Wilke Schwiedop. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
eval.py: evaluator for find.
"""

from __future__ import print_function

import fnmatch
import os
import stat
import sys

from _devbuild.gen import find_asdl as asdl

def _path(v):
	return v.path
def _basename(v):
	return os.path.basename(v.path)

pathAccMap = {
	asdl.pathAccessor_e.FullPath.enum_id : _path,
	asdl.pathAccessor_e.Filename.enum_id : _basename,
}

def _accessTime(v):
	assert False
	return stat.ST_ATIME(v.stat.st_mode)
def _creationTime(v):
	assert False
	return stat.ST_CTIME(v.stat.st_mode)
def _modificationTime(v):
	assert False
	return stat.ST_MTIME(v.stat.st_mode)
def _filesystem(v):
	assert False
	return stat.ST_DEV(v.stat.st_mode) # ???
def _inode(v):
	return stat.ST_INO(v.stat.st_mode)
def _linkCount(v):
	return stat.ST_NLINK(v.stat.st_mode)
def _mode(v):
	return stat.S_IMODE(v.stat.st_mode)
def _filetype(v):
	return stat.S_IFMT(v.stat.st_mode)
def _uid(v):
	return stat.ST_UID(v.stat.st_mode)
def _gid(v):
	return stat.ST_GID(v.stat.st_mode)
def _username(v):
	assert False
def _groupname(v):
	assert False
def _size(v):
	return stat.ST_SIZE(v.stat.st_mode)

statAccMap = {
	asdl.statAccessor_e.AccessTime.enum_id		: _accessTime,
	asdl.statAccessor_e.CreationTime.enum_id	: _creationTime,
	asdl.statAccessor_e.ModificationTime.enum_id	: _modificationTime,
	asdl.statAccessor_e.Filesystem.enum_id	: _filesystem,
	asdl.statAccessor_e.Inode.enum_id		: _inode,
#	asdl.statAccessor_e.LinkCount.enum_id	: _linkCount,
	asdl.statAccessor_e.Mode.enum_id		: _mode,
	asdl.statAccessor_e.Filetype.enum_id	: _filetype,
	asdl.statAccessor_e.Uid.enum_id		: _uid,
	asdl.statAccessor_e.Gid.enum_id		: _gid,
	asdl.statAccessor_e.Username.enum_id	: _username,
	asdl.statAccessor_e.Groupname.enum_id	: _groupname,
	asdl.statAccessor_e.Size.enum_id		: _size,
}

def _stringMatch(acc, test):
	string = test.p.str
	return lambda x: acc(x) == string
def _globMatch(acc, test):
	glob = test.p.glob
	return lambda x: fnmatch.fnmatch(acc(x), glob)
def _regexMatch(acc, test):
	assert False
def _eq(acc, test):
	n = test.p.n
	return lambda x: acc(x) == n
def _ge(acc, test):
	n = test.p.n
	return lambda x: acc(x) >= n
def _le(acc, test):
	n = test.p.n
	return lambda x: acc(x) <= n
def _readable(acc, test):
	return lambda x: os.access(acc(x), os.R_OK)
def _writable(acc, test):
	return lambda x: os.access(acc(x), os.W_OK)
def _executable(acc, test):
	return lambda x: os.access(acc(x), os.X_OK)

predicateMap = {
	asdl.predicate_e.StringMatch : _stringMatch,
	asdl.predicate_e.GlobMatch : _globMatch,
	asdl.predicate_e.RegexMatch : _regexMatch,
	asdl.predicate_e.EQ : _eq,
	asdl.predicate_e.GE : _ge,
	asdl.predicate_e.LE : _le,
	asdl.predicate_e.Readable	: _readable,
	asdl.predicate_e.Writable	: _writable,
	asdl.predicate_e.Executable	: _executable,
}

def _true(_):
	return lambda _: True
def _false(_):
	return lambda _: False
def _concatenation(test):
	return lambda x: [EvalExpr(e)(x) for e in test.exprs][-1]
def _disjunction(test):
	return lambda x: any(EvalExpr(e)(x) for e in test.exprs)
def _conjunction(test):
	return lambda x: all(EvalExpr(e)(x) for e in test.exprs)
def _negation(test):
	return lambda x: not EvalExpr(test.expr)(x)
def _pathTest(test):
	pred = predicateMap[test.p.tag]
	acc = pathAccMap[test.a.enum_id]
	return pred(acc, test)
def _statTest(test):
	pred = predicateMap[test.p.tag]
	acc = statAccMap[test.a.enum_id]
	return pred(acc, test)
def _delete(_):
	def __delete(v):
		print("pretend delete", v, file=sys.stderr)
		return True
	return __delete
def _prune(_):
	def __prune(v):
		v.prune = True
		return True
	return __prune
def _quit(_):
	def __quit(v):
		v.quit = True
		return True
	return __quit
def _print(action):
	# TODO handle output-file
	# TODO handle format
	def __print(v):
		print(v.path)
		return True
	return __print
def _ls(action):
	return _true
def _exec(action):
	# TODO return exit status
	return _true

exprMap = {
	asdl.expr_e.True_	: _true,
	asdl.expr_e.False_	: _false,
	asdl.expr_e.Concatenation	: _concatenation,
	asdl.expr_e.Disjunction	: _disjunction,
	asdl.expr_e.Conjunction	: _conjunction,
	asdl.expr_e.Negation		: _negation,
	asdl.expr_e.PathTest	: _pathTest,
	asdl.expr_e.StatTest	: _statTest,
	asdl.expr_e.DeleteAction	: _delete,
	asdl.expr_e.PruneAction	: _prune,
	asdl.expr_e.QuitAction	: _quit,
	asdl.expr_e.PrintAction	: _print,
	asdl.expr_e.LsAction	: _ls,
	asdl.expr_e.ExecAction	: _exec,
}

def EvalExpr(ast):
	return exprMap[ast.tag](ast)

class Thing:
	def __init__(self, path, stat=None):
		self.path = path
		self._stat = stat
		self.prune = False
		self.quit = False
	@property
	def stat(self):
		if self._stat is None:
			# TODO stat for tests that require it?
			self._stat = os.lstat(self.path)
		return self._stat
	def __repr__(self):
		return self.path
