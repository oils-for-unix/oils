#!/usr/bin/env python2
# Copyright 2019 Wilke Schwiedop. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
find.py: Clone of GNU find.
"""

from __future__ import print_function

import os
import sys

#from typing import TYPE_CHECKING, Dict, IO
#if TYPE_CHECKING:
#	from pgen2.parse import PNode

import tokenizer
import parser
from _devbuild.gen import find_nt
from ast import AST
from eval import EvalExpr, Thing
import eval

def printTree(pnode, nametable, f=sys.stderr, indentChars="\t"):
	def _printTree(pnode, nametable, f, i, depth, indentChars):
		v = pnode.tok[0] if tokenizer.is_terminal(pnode.typ) else ""
		print(indentChars * depth, '#%d' % i, nametable.get(pnode.typ, "UNKNOWN"), v, file=f)
		if not pnode.children:
			return
		for i, c in enumerate(pnode.children):
			_printTree(c, nametable, f, i, depth+1, indentChars)
	_printTree(pnode, nametable, f, 0, 0, indentChars)

def contains_print_blocker(node):
	# all actions except -print and -prune
	XYZActions = [
		tokenizer.DELETE, tokenizer.QUIT,
#		tokenizer.PRUNE,
		tokenizer.PRINT,
		tokenizer.PRINT0, tokenizer.PRINTF,
		tokenizer.FPRINT, tokenizer.FPRINT0, tokenizer.FPRINTF,
		tokenizer.LS,
		tokenizer.FLS, tokenizer.EXEC, tokenizer.EXECDIR, tokenizer.OK, tokenizer.OKDIR,
	]
	return node.typ in XYZActions or (node.children and any(contains_print_blocker(c) for c in node.children))

# find
#	for root, dirs, files in os.walk('.', topdown=True):
#		print(root, *(os.path.join(root, f) for f in files), sep='\n')
# find -depth
#	for root, dirs, files in os.walk('.', topdown=False):
#		print(*(os.path.join(root, f) for f in files), root, sep='\n')
def main(argv):
	i = 1
	while i < len(argv) and argv[i][0] not in ('!', '(', '-'):
		i += 1

	paths = argv[1:i]
	if not paths:
		paths.append('.')

	tokens = tokenizer.tokenize(argv[i:])

	parse_root = parser.ParseTree(tokens)

	names = tokenizer.tok_name.copy()
	names.update(parser.nt_name)
	printTree(parse_root, names)

	ast_root = AST(parse_root)

	ast_root.PrettyPrint(f=sys.stderr)
	print(file=sys.stderr)

	# if ast contains no actions other than -prune or -print:
	# ast_root = Conjunction(ast_root, -print)
	# if ast_root is a Conjunction, append child
	if not contains_print_blocker(parse_root):
#		print("adding '-a -print'", file=sys.stderr)
		from _devbuild.gen import find_asdl as asdl
		if parse_root.children[0].typ == find_nt.conjunction:
			ast_root.exprs.append(asdl.expr.PrintAction())
		else:
			ast_root = asdl.expr.Conjunction([ast_root, asdl.expr.PrintAction()])

	expr = EvalExpr(ast_root)
	for path in paths:
		for root, dirs, files in os.walk(path):
			t = Thing(root)
			b = expr(t)
			if t.quit:
				break
			if t.prune:
				del dirs[:]
				continue
			for fname in files:
				t = Thing(os.path.join(root,fname))
				expr(t)
				# -prune should be ignored for files
		else:
			continue
		# TODO run -exec ... {} +
		break

if __name__ == '__main__':
	try:
		main(sys.argv)
	except RuntimeError as e:
		print('FATAL: %s' % e, file=sys.stderr)
		sys.exit(1)
