#!/usr/bin/env python2
# Copyright 2019 Wilke Schwiedop. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0

import pgen2.driver, pgen2.pgen, pgen2.parse

from oil_lang.expr_parse import NoSingletonAction

from tokenizer import TokenDef, opmap, tok_name

with open('tools/find/find.pgen2') as f:
	_grammar = pgen2.pgen.MakeGrammar(f, tok_def=TokenDef())
_parser = pgen2.parse.Parser(_grammar, convert=NoSingletonAction)

nt_name = _grammar.number2symbol.copy()

def ParseTree(tokens):
	return pgen2.driver.PushTokens(
		_parser,
		tokens,
		_grammar,
		start_symbol='start',
		opmap=opmap
	)
