"""
front_end.py: Lexer and parser for the ASDL schema language.
"""
from __future__ import print_function

import re

from asdl import ast
from asdl.ast import (
    Use, Module, TypeDecl, Constructor, Field, Sum, SimpleSum, Product, TypeExpr
)

from core.pyerror import log
_ = log

_KEYWORDS = ['use', 'module', 'attributes']

_TOKENS = [
    ('Keyword', ''),
    ('Name', ''),

    # For operators, the string matters
    ('Equals', '='),
    ('Comma', ','),
    ('Question', '?'),
    ('Pipe', '|'),
    ('Asterisk', '*'),
    ('LParen', '('),
    ('RParen', ')'),
    ('LBrace', '{'),
    ('RBrace', '}'),
    ('Percent', '%'),

    # Oil addition for parameterized types.
    ('LBracket', '['),
    ('RBracket', ']'),

    # - Start with map[string, bool].  
    # - array[string] is an alias for string*
    #   - do we need set[string] instead of map[string]bool?
    #
    # statically typed: map and array
    # dynamically typed: dict and list
]

_TOKEN_STR = [name for name, _ in _TOKENS]  # integer -> string like LParen
_TOKEN_INT = {}  # string like '(' -> integer


class TokenKind(object):
    """ASDL tokens.

    TokenKind.LBrace = 5, etc.
    """
    pass


for i, (name, val) in enumerate(_TOKENS):
    setattr(TokenKind, name, i)
    _TOKEN_INT[val] = i


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
            if c in _KEYWORDS:
                yield Token(TokenKind.Keyword, c, lineno)
            elif c[0].isalpha():
                yield Token(TokenKind.Name, c, lineno)
            elif c[:2] == '--':
                # Comment
                break
            else:
                # Operators
                try:
                    op_kind = _TOKEN_INT[c]
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
        """
        module = 'module' NAME '{' use* type* '}'
        """
        if not self._at_keyword('module'):
            raise ASDLSyntaxError(
                'Expected "module" (found {})'.format(self.cur_token.value),
                self.cur_token.lineno)
        self._advance()
        name = self._match(TokenKind.Name)
        self._match(TokenKind.LBrace)

        uses = []
        while self._at_keyword('use'):
            uses.append(self._parse_use())

        defs = []
        while self.cur_token.kind == TokenKind.Name:
            typename = self._advance()
            self._match(TokenKind.Equals)
            type_ = self._parse_type_decl()
            defs.append(TypeDecl(typename, type_))

        self._match(TokenKind.RBrace)
        return Module(name, uses, defs)

    def _parse_use(self):
        """
        use = 'use' NAME+ '{' NAME+ '}'

        example: use frontend syntax { Token }

        This means frontend/syntax.asdl.h :: Token
        """
        self._advance()  # past 'use'
        module_parts = []
        while self.cur_token.kind == TokenKind.Name:
          part = self._advance()
          module_parts.append(part)

        self._match(TokenKind.LBrace)

        type_names = []
        while self.cur_token.kind == TokenKind.Name:
            t = self._advance()
            type_names.append(t)
            if self.cur_token.kind == TokenKind.RParen:
                break
            elif self.cur_token.kind == TokenKind.Comma:
                self._advance()

        self._match(TokenKind.RBrace)
        #print('MOD %s' % module_parts)
        return Use(module_parts, type_names)

    def _parse_type_decl(self):
        """
        constructor: Name fields?
        sum: constructor ('|' constructor)*
        type: product | sum
        """
        if self.cur_token.kind == TokenKind.LParen:
            # If we see a (, it's a product
            return self._parse_product()
        else:
            # Otherwise it's a sum. Look for ConstructorId
            sumlist = []
            while True:
                cons_name = self._match(TokenKind.Name)

                shared_type = None
                fields = None
                if self.cur_token.kind == TokenKind.LParen:
                    fields = self._parse_fields()
                elif self.cur_token.kind == TokenKind.Percent:
                    self._advance()
                    shared_type = self._match(TokenKind.Name)
                else:
                    pass

                cons = Constructor(cons_name, shared_type, fields)
                sumlist.append(cons)

                if self.cur_token.kind != TokenKind.Pipe:
                  break
                self._advance()
            attributes = self._parse_optional_attributes()

            if ast.is_simple(sumlist):
              return SimpleSum(sumlist, attributes)
            else:
              return Sum(sumlist, attributes)

    def _parse_type_expr(self):
        """
        We just need these expressions, not arbitrary ones:

        one_param: ('array' | 'maybe') '[' type_expr ']'
        two_params: 'map' '[' type_expr ',' type_expr ']'

        type_expr:
          Name ( '?' | '*' )
        | one_param
        | two_params

        """
        type_name = self._match(TokenKind.Name)
        typ = TypeExpr(type_name)

        if type_name in ('array', 'maybe'):
          self._match(TokenKind.LBracket)
          child = self._parse_type_expr()
          typ = TypeExpr(type_name, [child])
          self._match(TokenKind.RBracket)
          return typ

        if type_name == 'map':
          self._match(TokenKind.LBracket)
          k = self._parse_type_expr()
          self._match(TokenKind.Comma)
          v = self._parse_type_expr()
          typ = TypeExpr(type_name, [k, v])
          self._match(TokenKind.RBracket)
          return typ

        if self.cur_token.kind == TokenKind.Asterisk:
            # string* is equivalent to array[string]
            typ = TypeExpr('array', [typ])
            self._advance()
        elif self.cur_token.kind == TokenKind.Question:
            # string* is equivalent to maybe[string]
            typ = TypeExpr('maybe', [typ])
            self._advance()
        return typ

    def _parse_fields(self):
        """
        fields:
          '('
                   type_expr Name
             ( ',' type_expr Name )*
          ')'

        Name Quantifier?  should be changed to typename.
        """
        fields = []
        self._match(TokenKind.LParen)
        while self.cur_token.kind == TokenKind.Name:
            typ = self._parse_type_expr()
            field_name = self._match(TokenKind.Name)

            fields.append(Field(typ, field_name))

            if self.cur_token.kind == TokenKind.RParen:
                break
            elif self.cur_token.kind == TokenKind.Comma:
                self._advance()

        self._match(TokenKind.RParen)
        return fields

    def _parse_optional_attributes(self):
        if self._at_keyword('attributes'):
            self._advance()
            return self._parse_fields()
        else:
            return None

    def _parse_product(self):
        return Product(self._parse_fields(), self._parse_optional_attributes())

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

    def _match(self, kind):
        """The 'match' primitive of RD parsers.

        * Verifies that the current token is of the given kind (kind can
          be a tuple, in which the kind must match one of its members).
        * Returns the value of the current token
        * Reads in the next token

        Args:
          kind: A TokenKind, or a tuple of TokenKind
        """
        if self.cur_token.kind == kind:
            value = self.cur_token.value
            self._advance()
            return value
        else:
            raise ASDLSyntaxError(
                'Expected token {}, got {}'.format(_TOKEN_STR[kind],
                                                   self.cur_token.value),
                self.cur_token.lineno)

    def _at_keyword(self, keyword):
        return (self.cur_token.kind == TokenKind.Keyword and
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


_PRIMITIVE_TYPES = [
    'string', 'int', 'float', 'bool',

    # 'any' is used:
    # - for value.Obj in the the Oil expression evaluator.  We're not doing any
    #   dynamic or static checking now.
    'any',

    # no 'array' or 'maybe' because TypeName() doesn't return them
    'map',
]


def _ResolveType(typ, type_lookup):
  """
  Recursively attach a 'resolved' field to TypeExpr nodes.
  """
  if typ.children:
    assert typ.name in ('map', 'array', 'maybe'), typ
    for t in typ.children:
      _ResolveType(t, type_lookup)  # recurse
  else:
    if typ.name not in _PRIMITIVE_TYPES:
      ast_node = type_lookup.get(typ.name)
      if ast_node is None:
        raise ASDLSyntaxError("Couldn't find type %r" % typ.name)
      typ.resolved = ast_node
      #log('resolved = %s', typ.resolved)


def _ResolveFields(field_ast_nodes, type_lookup):
  """
  Args:
    type_lookup: Populated by name resolution
  """
  for field in field_ast_nodes:
    _ResolveType(field.typ, type_lookup)

    # TODO: Get rid of resolved_type everywhere

    type_name = field.TypeName()
    assert field.resolved_type is None, field  # it's not initialized yet

    # We only use the resolved type for determining if it's a simple sum?
    if type_name not in _PRIMITIVE_TYPES:
      ast_node = type_lookup.get(type_name)
      if ast_node is None:
        raise ASDLSyntaxError("Couldn't find type %r" % type_name)
      field.resolved_type = ast_node


def _ResolveModule(module, app_types):
  # Types that fields are declared with: int, id, word_part, etc.
  # Fields are NOT declared with Constructor names.
  type_lookup = dict(app_types)

  # TODO: Need to resolve 'imports' to the right descriptor.  Code generation
  # relies on it:
  # - To pick the method to call in AbbreviatedTree etc.
  # - To generate 'value_t' instead of 'value' in type annotations.

  for u in module.uses:
    for type_name in u.type_names:
      type_lookup[type_name] = u  # type: ast.Use()

  # NOTE: We need two passes because types can be mutually recursive, e.g.
  # asdl/arith.asdl.

  # First pass: collect declared types and make entries for them.
  for d in module.dfns:
    type_lookup[d.name] = d.value

  # Second pass: resolve type declarations in Product and constructor.
  #
  # - check that the type of every field is valid 
  #   - fields in products, constructors
  #   - fields in attributes
  #   - parameterized types like map[int, action]   -- TODO
  # - mutations:
  #   - constructors that refer to first-class variants?  For inheritance I
  #     guess.

  for d in module.dfns:
    ast_node = d.value
    if isinstance(ast_node, ast.Product):
      #log('fields %s', ast_node.fields)
      _ResolveFields(ast_node.fields, type_lookup)

    elif isinstance(ast_node, ast.Sum):
      for cons in ast_node.types:
        _ResolveFields(cons.fields, type_lookup)

    else:
      raise AssertionError(ast_node)


def LoadSchema(f, app_types, verbose=False):
  """Returns an AST for the schema."""
  p = ASDLParser()
  schema_ast = p.parse(f)
  if verbose:
    import sys
    schema_ast.Print(sys.stdout, 0)

  v = Check()
  v.visit(schema_ast)

  if v.errors:
    raise AssertionError('ASDL file is invalid: %s' % v.errors)

  # Make sure all the names are valid
  _ResolveModule(schema_ast, app_types)
  return schema_ast
