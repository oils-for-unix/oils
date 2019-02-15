#!/usr/bin/python
"""
front_end.py: Lexer and parser for the ASDL schema language.
"""
from __future__ import print_function

import re

from asdl import asdl_ as asdl
from asdl import meta
from asdl.asdl_ import Module, Type, Constructor, Field, Sum, Product


# Types for describing tokens in an ASDL specification.
class TokenKind(object):
    """TokenKind is provides a scope for enumerated token kinds."""
    (ConstructorId, TypeId, Equals, Comma, Question, Pipe, Asterisk,
     LParen, RParen, LBrace, RBrace) = xrange(11)

    operator_table = {
        '=': Equals, ',': Comma,    '?': Question, '|': Pipe,    '(': LParen,
        ')': RParen, '*': Asterisk, '{': LBrace,   '}': RBrace}

class Token(object):
    def __init__(self, kind, value, lineno):
        self.kind = kind
        self.value = value
        self.lineno = lineno

class ASDLSyntaxError(Exception):
    def __init__(self, msg, lineno=None):
        self.msg = msg
        self.lineno = lineno or '<unknown>'

    def __str__(self):
        return 'Syntax error on line {0.lineno}: {0.msg}'.format(self)

def _Tokenize(f):
    """Tokenize the given buffer. Yield Token objects."""
    for lineno, line in enumerate(f, 1):
        for m in re.finditer(r'\s*(\w+|--.*|.)', line.strip()):
            c = m.group(1)
            if c[0].isalpha():
                # Some kind of identifier
                if c[0].isupper():
                    yield Token(TokenKind.ConstructorId, c, lineno)
                else:
                    yield Token(TokenKind.TypeId, c, lineno)
            elif c[:2] == '--':
                # Comment
                break
            else:
                # Operators
                try:
                    op_kind = TokenKind.operator_table[c]
                except KeyError:
                    raise ASDLSyntaxError('Invalid operator %s' % c, lineno)
                yield Token(op_kind, c, lineno)

class ASDLParser(object):
    """Parser for ASDL files.

    Create, then call the parse method on a buffer containing ASDL.
    This is a simple recursive descent parser that uses _Tokenize for the
    lexing.
    """
    def __init__(self):
        self._tokenizer = None
        self.cur_token = None

    def parse(self, f):
        """Parse the ASDL in the file and return an AST with a Module root.
        """
        self._tokenizer = _Tokenize(f)
        self._advance()
        return self._parse_module()

    def _parse_module(self):
        if self._at_keyword('module'):
            self._advance()
        else:
            raise ASDLSyntaxError(
                'Expected "module" (found {})'.format(self.cur_token.value),
                self.cur_token.lineno)
        name = self._match(self._id_kinds)
        self._match(TokenKind.LBrace)
        defs = self._parse_definitions()
        self._match(TokenKind.RBrace)
        return Module(name, defs)

    def _parse_definitions(self):
        defs = []
        while self.cur_token.kind == TokenKind.TypeId:
            typename = self._advance()
            self._match(TokenKind.Equals)
            type = self._parse_type()
            defs.append(Type(typename, type))
        return defs

    def _parse_type(self):
        if self.cur_token.kind == TokenKind.LParen:
            # If we see a (, it's a product
            return self._parse_product()
        else:
            # Otherwise it's a sum. Look for ConstructorId
            sumlist = [Constructor(self._match(TokenKind.ConstructorId),
                                   self._parse_optional_fields())]
            while self.cur_token.kind == TokenKind.Pipe:
                # More constructors
                self._advance()
                sumlist.append(Constructor(
                                self._match(TokenKind.ConstructorId),
                                self._parse_optional_fields()))
            return Sum(sumlist, self._parse_optional_attributes())

    def _parse_product(self):
        return Product(self._parse_fields(), self._parse_optional_attributes())

    def _parse_fields(self):
        fields = []
        self._match(TokenKind.LParen)
        while self.cur_token.kind == TokenKind.TypeId:
            typename = self._advance()
            is_seq, is_opt = self._parse_optional_field_quantifier()
            id = (self._advance() if self.cur_token.kind in self._id_kinds
                                  else None)
            fields.append(Field(typename, id, seq=is_seq, opt=is_opt))
            if self.cur_token.kind == TokenKind.RParen:
                break
            elif self.cur_token.kind == TokenKind.Comma:
                self._advance()
        self._match(TokenKind.RParen)
        return fields

    def _parse_optional_fields(self):
        if self.cur_token.kind == TokenKind.LParen:
            return self._parse_fields()
        else:
            return None

    def _parse_optional_attributes(self):
        if self._at_keyword('attributes'):
            self._advance()
            return self._parse_fields()
        else:
            return None

    def _parse_optional_field_quantifier(self):
        is_seq, is_opt = False, False
        if self.cur_token.kind == TokenKind.Asterisk:
            is_seq = True
            self._advance()
        elif self.cur_token.kind == TokenKind.Question:
            is_opt = True
            self._advance()
        return is_seq, is_opt

    def _advance(self):
        """ Return the value of the current token and read the next one into
            self.cur_token.
        """
        cur_val = None if self.cur_token is None else self.cur_token.value
        try:
            self.cur_token = next(self._tokenizer)
        except StopIteration:
            self.cur_token = None
        return cur_val

    _id_kinds = (TokenKind.ConstructorId, TokenKind.TypeId)

    def _match(self, kind):
        """The 'match' primitive of RD parsers.

        * Verifies that the current token is of the given kind (kind can
          be a tuple, in which the kind must match one of its members).
        * Returns the value of the current token
        * Reads in the next token
        """
        if (isinstance(kind, tuple) and self.cur_token.kind in kind or
            self.cur_token.kind == kind
            ):
            value = self.cur_token.value
            self._advance()
            return value
        else:
            raise ASDLSyntaxError(
                'Unmatched {} (found {})'.format(kind, self.cur_token.kind),
                self.cur_token.lineno)

    def _at_keyword(self, keyword):
        return (self.cur_token.kind == TokenKind.TypeId and
                self.cur_token.value == keyword)


# A generic visitor for the meta-AST that describes ASDL. This can be used by
# emitters. Note that this visitor does not provide a generic visit method, so a
# subclass needs to define visit methods from visitModule to as deep as the
# interesting node.
# We also define a Check visitor that makes sure the parsed ASDL is well-formed.

class _VisitorBase(object):
    """Generic tree visitor for ASTs."""
    def __init__(self):
        self.cache = {}

    def visit(self, obj, *args):
        klass = obj.__class__
        meth = self.cache.get(klass)
        if meth is None:
            methname = "visit" + klass.__name__
            meth = getattr(self, methname, None)
            self.cache[klass] = meth
        if meth:
            try:
                meth(obj, *args)
            except Exception as e:
                print("Error visiting %r: %s" % (obj, e))
                raise


class Check(_VisitorBase):
    """A visitor that checks a parsed ASDL tree for correctness.

    Errors are printed and accumulated.
    """
    def __init__(self):
        super(Check, self).__init__()
        self.cons = {}
        self.errors = 0  # No longer used, but maybe in the future?
        self.types = {}  # list of declared field types

    def visitModule(self, mod):
        for dfn in mod.dfns:
            self.visit(dfn)

    def visitType(self, type):
        self.visit(type.value, str(type.name))

    def visitSum(self, sum, name):
        for t in sum.types:
            # Simple sum types can't conflict
            if asdl.is_simple(sum):
                continue
            self.visit(t, name)

    def visitConstructor(self, cons, name):
        for f in cons.fields:
            self.visit(f, cons.name)

    def visitField(self, field, name):
        key = str(field.type)
        l = self.types.setdefault(key, [])
        l.append(name)

    def visitProduct(self, prod, name):
        for f in prod.fields:
            self.visit(f, name)


def _AppendFields(field_ast_nodes, type_lookup, out):
  for field in field_ast_nodes:
    #print(field)
    runtime_type = type_lookup[field.type]

    # TODO: cache these under 'type*' and 'type?'.  Don't want duplicates!
    if field.seq:
      runtime_type = meta.ArrayType(runtime_type)

    if field.opt:
      runtime_type = meta.MaybeType(runtime_type)

    out.append((field.name, runtime_type))


def _MakeReflection(module, app_types):
  # Types that fields are declared with: int, id, word_part, etc.
  # Fields are NOT declared with Constructor names.
  type_lookup  = dict(meta.BUILTIN_TYPES)
  type_lookup.update(app_types)

  # NOTE: We need two passes because types can be mutually recursive, e.g.
  # asdl/arith.asdl.

  # First pass: collect declared types and make entries for them.
  for d in module.dfns:
    ast_node = d.value
    if isinstance(ast_node, asdl.Product):
      type_lookup[d.name] = meta.CompoundType([])

    elif isinstance(ast_node, asdl.Sum):
      is_simple = asdl.is_simple(ast_node)
      type_lookup[d.name] = meta.SumType(is_simple)

    else:
      raise AssertionError(ast_node)

  # Second pass: resolve type declarations in Product and constructor.
  for d in module.dfns:
    ast_node = d.value
    if isinstance(ast_node, asdl.Product):
      runtime_type = type_lookup[d.name] 
      _AppendFields(ast_node.fields, type_lookup, runtime_type.fields)

    elif isinstance(ast_node, asdl.Sum):
      sum_type = type_lookup[d.name]  # the one we just created

      for cons in ast_node.types:
        fields_out = []
        # fully-qualified name.  Use a _ so we can share strings with class
        # name.
        key = '%s__%s' % (d.name, cons.name)
        cons_type = meta.CompoundType(fields_out)
        type_lookup[key] = cons_type
        _AppendFields(cons.fields, type_lookup, fields_out)

        sum_type.cases.append(cons_type)

    else:
      raise AssertionError(ast_node)

  return type_lookup


def LoadSchema(f, app_types):
  """Returns an AST for the schema and a type_lookup dictionary.
  
  Used for code gen and metaprogramming.

  Note: I think app_types is only used for dynamic type checking in
  asdl/py_meta.py.  I guess it could be used for pretty-printing, but that uses
  the actual value and not the type.

  TODO: We should change pretty-printing to also verify the types!
  """
  p = ASDLParser()
  schema_ast = p.parse(f)

  v = Check()
  v.visit(schema_ast)

  if v.errors:
    raise AssertionError('ASDL file is invalid: %s' % v.errors)

  type_lookup = _MakeReflection(schema_ast, app_types)
  return schema_ast, type_lookup
