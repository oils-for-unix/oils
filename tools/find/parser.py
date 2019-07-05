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
