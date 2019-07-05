# Copyright 2019 Wilke Schwiedop. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
ast.py: AST utilities for find.
"""

import stat

from _devbuild.gen import find_asdl as asdl
from _devbuild.gen import find_nt

import tokenizer
import parser

#
# path tests
#
def _name(glob):
	return asdl.expr.PathTest(
		asdl.pathAccessor_e.Filename,
		asdl.predicate.GlobMatch(glob)
	)
def _iname(glob):
	return asdl.expr.PathTest(
		asdl.pathAccessor_e.Filename,
		asdl.predicate.GlobMatch(glob, ignoreCase=True)
	)
def _lname(glob):
	assert False
def _ilname(glob):
	assert False
def _path(glob):
	return asdl.expr.PathTest(
		asdl.pathAccessor_e.FullPath,
		asdl.predicate.GlobMatch(glob)
	)
def _ipath(glob):
	return asdl.expr.PathTest(
		asdl.pathAccessor_e.FullPath,
		asdl.predicate.GlobMatch(glob, ignoreCase=True)
	)
def _regex(re):
	return asdl.expr.PathTest(
		asdl.pathAccessor_e.FullPath,
		asdl.predicate.RegexMatch(re)
	)
def _iregex(re):
	return asdl.expr.PathTest(
		asdl.pathAccessor_e.FullPath,
		asdl.predicate.RegexMatch(re, ignoreCase=True)
	)
def _readable():
	return asdl.expr.PathTest(
		asdl.pathAccessor_e.FullPath,
		asdl.predicate.Readable()
	)
def _writable():
	return asdl.expr.PathTest(
		asdl.pathAccessor_e.FullPath,
		asdl.predicate.Writable()
	)
def _executable():
	return asdl.expr.PathTest(
		asdl.pathAccessor_e.FullPath,
		asdl.predicate.Executable()
	)
#
# stat tests
#
def parse_number_predicate(n_str, factor=1):
	if n_str[0] == '+':
		return asdl.predicate.GE(int(n_str[1:]) * factor)
	if n_str[0] == '-':
		return asdl.predicate.LE(int(n_str[1:]) * factor)
	return asdl.predicate.EQ(int(n_str) * factor)
def _amin(n_str):
	assert False
def _anewer(f):
	assert False
def _atime(n_str):
	return asdl.expr.StatTest(asdl.statAccessor_e.AccessTime, parse_number_predicate(n_str))
def _cmin(n_str):
	assert False
def _cnewer(f):
	assert False
def _ctime(n_str):
	return asdl.expr.StatTest(asdl.statAccessor_e.CreationTime, parse_number_predicate(n_str))
def _mmin(n_str):
	assert False
def _mnewer(f):
	assert False
def _mtime(n_str):
	return asdl.expr.StatTest(asdl.statAccessor_e.ModificationTime, parse_number_predicate(n_str))
def _newerXY(): # TODO: read manpage
	assert False
def _used(n_str):
	assert False
def _empty():
	return asdl.expr.StatTest(
		asdl.statAccessor_e.Size,
		asdl.predicate.EQ(0)
	)
def _size(n_str):
	suffixMap = {
		'b'	: 512, # default
		'c'	: 1,
		'w'	: 2,
		'k'	: 1024**1,
		'M'	: 1024**2,
		'G'	: 1024**3,
	}
	if n_str[-1] in suffixMap:
		factor = suffixMap[n_str[-1]]
		n_str = n_str[:-1]
	else:
		factor = suffixMap['b']
	return asdl.expr.StatTest(asdl.statAccessor_e.Size, parse_number_predicate(n_str, factor=factor))
def _inum(n_str):
	return asdl.expr.StatTest(asdl.statAccessor_e.Inode, parse_number_predicate(n_str))
def _samefile(f):
	assert False
def _links(n_str):
	return asdl.expr.StatTest(asdl.statAccessor_e.LinkCount, parse_number_predicate(n_str))
def _perm(mode): # [+-/]mode
	assert False
def _type(t_str):
	tMap = {
		's'	: stat.S_IFSOCK,
		'l'	: stat.S_IFLNK,
		'f'	: stat.S_IFREG,
		'b'	: stat.S_IFBLK,
		'd'	: stat.S_IFDIR,
		'c'	: stat.S_IFCHR,
		'p'	: stat.S_IFIFO,
	}
	t = tMap[t_str]
	return asdl.expr.StatTest(
		asdl.statAccessor_e.Filetype,
		asdl.predicate.EQ(t)
	)
def _xtype(t_str):
	assert False
def _uid(uid_str):
	uid = int(uid)
	return asdl.expr.StatTest(
		asdl.statAccessor_e.Uid,
		asdl.predicate.EQ(uid)
	)
def _gid(gid_str):
	gid = int(gid)
	return asdl.expr.StatTest(
		asdl.statAccessor_e.Gid,
		asdl.predicate.EQ(gid)
	)
def _user(user):
	return asdl.expr.StatTest(
		asdl.statAccessor_e.Username,
		asdl.predicate.StringMatch(user)
	)
def _group(group):
	return asdl.expr.StatTest(
		asdl.statAccessor_e.Groupname,
		asdl.predicate.StringMatch(group)
	)
def _nouser():
	assert False
def _nogroup():
	assert False
def _fstype(fsType):
	assert False
#
# actions
#
def _print():
	return asdl.expr.PrintAction()
def _print0():
	# TODO verify fmt
	return asdl.expr.PrintAction(format="%P\0")
def _printf(fmt):
	return asdl.expr.PrintAction(format=fmt)
def _fprint(f):
	return asdl.expr.PrintAction(file=f)
def _fprint0(f):
	# TODO verify fmt
	return asdl.expr.PrintAction(file=f, format="%P\0")
def _fprintf(f, fmt):
	return asdl.expr.PrintAction(file=f, format=fmt)
def _ls():
	return asdl.expr.LsAction()
def _fls(f):
	return asdl.expr.LsAction(file=f)
def _exec(*argv):
	argv = list(argv)
	batch = True if argv[-1] == '+' else False if argv[-1] == ';' else None
	if batch is None:
		assert False
	return asdl.expr.ExecAction(batch=batch, dir=False, ok=False, argv=argv[:-1])
def _execdir(*argv):
	argv = list(argv)
	batch = True if argv[-1] == '+' else False if argv[-1] == ';' else None
	if batch is None:
		assert False
	return asdl.expr.ExecAction(batch=batch, dir=True, ok=False, argv=argv[:-1])
def _ok(*argv):
	argv = list(argv)
	batch = True if argv[-1] == '+' else False if argv[-1] == ';' else None
	if batch is None:
		assert False
	return asdl.expr.ExecAction(batch=batch, dir=False, ok=True, argv=argv[:-1])
def _okdir(*argv):
	argv = list(argv)
	batch = True if argv[-1] == '+' else False if argv[-1] == ';' else None
	if batch is None:
		assert False
	return asdl.expr.ExecAction(batch=batch, dir=True, ok=True, argv=argv[:-1])
def _delete():
	return asdl.expr.DeleteAction()
def _prune():
	return asdl.expr.PruneAction()
def _quit():
	return asdl.expr.QuitAction()

exprMap = {
	# atoms
	tokenizer.TRUE		: asdl.expr.True_,
	tokenizer.FALSE	: asdl.expr.False_,
	# path tests
	tokenizer.NAME		: _name,
	tokenizer.INAME	: _iname,
	tokenizer.LNAME	: _lname,
	tokenizer.ILNAME	: _ilname,
	tokenizer.PATH		: _path,
	tokenizer.IPATH	: _ipath,
	tokenizer.REGEX	: _regex,
	tokenizer.IREGEX	: _iregex,
	# stat tests
	tokenizer.AMIN		: _amin,
	tokenizer.ANEWER	: _anewer,
	tokenizer.ATIME	: _atime,
	tokenizer.CMIN		: _cmin,
	tokenizer.CNEWER	: _cnewer,
	tokenizer.CTIME	: _ctime,
	tokenizer.MMIN		: _mmin,
	tokenizer.MNEWER	: _mnewer,
	tokenizer.MTIME	: _mtime,
	tokenizer.NEWERXY	: _newerXY,
#	tokenizer.USED		: _used,
	tokenizer.EMPTY	: _empty,
	tokenizer.SIZE		: _size,
	tokenizer.READABLE	: _readable,
	tokenizer.WRITABLE	: _writable,
	tokenizer.EXECUTABLE	: _executable,
#	tokenizer.INUM		: _inum,
#	tokenizer.SAMEFILE	: _samefile,
#	tokenizer.LINKS	: _links,
	tokenizer.PERM		: _perm,
	tokenizer.TYPE		: _type,
	tokenizer.XTYPE	: _xtype,
	tokenizer.UID		: _uid,
	tokenizer.GID		: _gid,
	tokenizer.USER		: _user,
	tokenizer.GROUP	: _group,
	tokenizer.NOUSER	: _nouser,
	tokenizer.NOGROUP	: _nogroup,
#	tokenizer.FSTYPE	: _fstype,
	# actions
	tokenizer.PRINT	: _print,
	tokenizer.PRINT0	: _print0,
	tokenizer.PRINTF	: _printf,
	tokenizer.FPRINT	: _fprint,
	tokenizer.FPRINT0	: _fprint0,
	tokenizer.FPRINTF	: _fprintf,
	tokenizer.EXEC		: _exec,
	tokenizer.EXECDIR	: _execdir,
	tokenizer.OK		: _ok,
	tokenizer.OKDIR	: _okdir,
	tokenizer.DELETE	: _delete,
	tokenizer.PRUNE	: _prune,
	tokenizer.QUIT		: _quit,
}

def _start(children):
	assert len(children) == 2
	assert tokenizer.is_eof(children[1].typ)
	return AST(children[0])
def _concatenation(children):
	assert len(children) >= 2
	return asdl.expr.Concatenation(
		[AST(c) for c in children if c.typ != tokenizer.COMMA]
	)
def _disjunction(children):
	assert len(children) >= 2
	return asdl.expr.Disjunction(
		[AST(c) for c in children if c.typ != tokenizer.OR]
	)
def _conjunction(children):
	assert len(children) >= 2
	return asdl.expr.Conjunction(
		[AST(c) for c in children if c.typ != tokenizer.AND]
	)
def _negation(children):
	assert len(children) == 2
	assert children[0].typ == tokenizer.BANG
	return asdl.expr.Negation(AST(children[1]))
def _group(children):
	assert len(children) == 3
	assert children[0].typ == tokenizer.LPAR
	assert children[2].typ == tokenizer.RPAR
	return AST(children[1])
def _expr(children):
	f = exprMap[children[0].typ]
	return f(*(c.tok[0] for c in children[1:]))

ntMap = {
	find_nt.start            : _start,
	find_nt.concatenation    : _concatenation,
	find_nt.disjunction      : _disjunction,
	find_nt.conjunction      : _conjunction,
	find_nt.negation         : _negation,
	find_nt.group            : _group,
	find_nt.expr             : _expr,
}

def AST(pnode):
	if tokenizer.is_nonterminal(pnode.typ):
		assert pnode.typ not in exprMap
		return ntMap[pnode.typ](pnode.children)
	else:
		assert pnode.typ not in ntMap
		return exprMap[pnode.typ]()
