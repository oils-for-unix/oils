#!/usr/bin/env python2
# Copyright 2019 Wilke Schwiedop. All rights reserved.
# Copyright 2019 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
tokenizer.py: Tokenizer for find.
"""

_ops = [
	('!', 'BANG'),
	('(', 'LPAR'),
	(')', 'RPAR'),
	('-o', 'OR'),
	('-a', 'AND'),
	(',', 'COMMA'),
	(';', 'SEMI'),
	('+', 'PLUS'),

	('-true', 'TRUE'),
	('-false', 'FALSE'),

	('-name', 'NAME'),
	('-iname', 'INAME'),

	('-lname', 'LNAME'),
	('-ilname', 'ILNAME'),

	('-path', 'PATH'),
	('-ipath', 'IPATH'),

	('-regex', 'REGEX'),
	('-iregex', 'IREGEX'),

	('-executable', 'EXECUTABLE'),
	('-readable', 'READABLE'),
	('-writable', 'WRITABLE'),

	('-empty', 'EMPTY'),

	('-size', 'SIZE'),
	('-type', 'TYPE'),
	('-xtype', 'XTYPE'),
	('-perm', 'PERM'),

	('-group', 'GROUP'),
	('-user', 'USER'),
	('-gid', 'GID'),
	('-uid', 'UID'),
	('-nogroup', 'NOGROUP'),
	('-nouser', 'NOUSER'),

	('-amin', 'AMIN'),
	('-anewer', 'ANEWER'),
	('-atime', 'ATIME'),
	('-cmin', 'CMIN'),
	('-cnewer', 'CNEWER'),
	('-ctime', 'CTIME'),
	('-mmin', 'MMIN'),
	# note -newer not -mnewer
	('-newer', 'MNEWER'),
	('-mtime', 'MTIME'),
	('-newerXY', 'NEWERXY'),

	('-delete', 'DELETE'),
	('-prune', 'PRUNE'),
	('-quit', 'QUIT'),

	('-print', 'PRINT'),
	('-print0', 'PRINT0'),
	('-printf', 'PRINTF'),
	('-ls', 'LS'),
	('-fprint', 'FPRINT'),
	('-fprint0', 'FPRINT0'),
	('-fprintf', 'FPRINTF'),
	('-fls', 'FLS'),

	('-exec', 'EXEC'),
	('-execdir', 'EXECDIR'),
	('-ok', 'OK'),
	('-okdir', 'OKDIR'),
]

# start=100 is pgen voodoo, don't touch
opmap = dict((op, i) for i, (op, name) in enumerate(_ops, start=100))
tok_name = dict((i, name) for i, (op, name) in enumerate(_ops, start=100))
tok_name[0] = 'ENDMARKER'
tok_name[1] = 'STRING'
#tok_name[len(tok_name)] = 'N_TOKENS'
tok_name[256] = 'NT_OFFSET'

import sys
this_module = sys.modules[__name__]
for i, name in tok_name.items():
	setattr(this_module, name, i)

class TokenDef(object):
	def GetTerminalNum(self, label):
		""" e.g. NAME -> 1 """
		itoken = getattr(this_module, label, None)
		assert isinstance(itoken, int), label
		assert itoken in tok_name, label
		return itoken

	def GetOpNum(self, value):
		""" e.g '(' -> LPAR """
		return opmap[value]

	def GetKeywordNum(self, value):
		return None


def tokenize(argv):
	start = end = (1, 0) # dummy location data
	line_text = ''
	for a in argv:
		#log('tok = %r', a)
		typ = opmap.get(a, STRING)
#		print (typ, a, start, end, line_text)
		yield (typ, a, start, end, line_text)
	yield (ENDMARKER, '', start, end, line_text)

def is_terminal(type):
	# type (int) -> bool
	return type < NT_OFFSET

def is_nonterminal(type):
	# type (int) -> bool
	return type >= NT_OFFSET

def is_eof(type):
	# type (int) -> bool
	return type == ENDMARKER
